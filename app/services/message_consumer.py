"""Enhanced message consumer for Kafka with idempotency, batch processing, and versioning."""
import json
import hashlib
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import deque
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from kafka.admin import KafkaAdminClient, NewTopic
from app.config import settings
from app.services.search_service import SearchService
from app.services.cache_service import CacheService
from app.middleware.circuit_breaker import get_kafka_breaker, CircuitBreakerOpenError
from app.strategies.transaction_strategy import TransactionStrategyFactory
from app.schemas import TransactionCreate, TransactionType, Product, TransactionStatus
from app.database import SessionLocal
from app.models import Transaction
from app.repositories.transaction_repository import TransactionRepository
import structlog

logger = structlog.get_logger()


class MessageConsumer:
    """Enhanced consumer for transaction messages from Kafka."""
    
    def __init__(
        self,
        search_service: SearchService,
        cache_service: CacheService,
        batch_size: int = 10,
        batch_timeout: float = 5.0,
        enable_audit_db: bool = True
    ):
        self.search_service = search_service
        self.cache_service = cache_service
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.enable_audit_db = enable_audit_db
        self.consumer = None
        self.producer = None
        self.enabled = False
        self.message_buffer: deque = deque()
        self.last_batch_time = time.time()
        self.processed_messages: set = set()  # In-memory set for idempotency
        self._init_kafka()
    
    def _init_kafka(self):
        """Initialize Kafka connection and topics."""
        try:
            bootstrap_servers = settings.kafka_bootstrap_servers.split(',')
            topic = settings.kafka_transactions_topic
            
            # Create admin client to ensure topic exists
            admin_client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id='transaction_indexer_admin'
            )
            
            # Check if topic exists, create if not
            try:
                from kafka.admin import ConfigResource, ConfigResourceType
                metadata = admin_client.describe_topics([topic])
                logger.info("Kafka topic exists", topic=topic)
            except Exception:
                # Topic doesn't exist, create it
                topic_list = [
                    NewTopic(
                        name=topic,
                        num_partitions=3,
                        replication_factor=1,
                        topic_configs={
                            'retention.ms': '604800000',  # 7 days
                            'compression.type': 'snappy'
                        }
                    )
                ]
                admin_client.create_topics(new_topics=topic_list, validate_only=False)
                logger.info("Created Kafka topic", topic=topic, partitions=3)
            
            admin_client.close()
            
            # Create consumer
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap_servers,
                group_id=settings.kafka_consumer_group,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                enable_auto_commit=settings.kafka_enable_auto_commit,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=int(self.batch_timeout * 1000),  # Convert to milliseconds
                max_poll_records=self.batch_size,
                fetch_min_bytes=1,
                fetch_max_wait_ms=500
            )
            
            # Create producer for DLQ (dead letter topic)
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',  # Wait for all replicas
                retries=3
            )
            
            self.enabled = True
            logger.info(
                "Kafka consumer initialized",
                topic=topic,
                consumer_group=settings.kafka_consumer_group,
                batch_size=self.batch_size
            )
        except Exception as e:
            logger.warning("Kafka consumer initialization failed", error=str(e))
            self.enabled = False
    
    def _generate_message_id(self, message: Dict[str, Any]) -> str:
        """Generate a unique message ID for idempotency."""
        transaction_id = message.get("transaction", {}).get("id", "")
        event_type = message.get("event_type", "")
        timestamp = message.get("timestamp", "")
        
        content = f"{transaction_id}:{event_type}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _is_duplicate(self, message_id: str) -> bool:
        """Check if message was already processed (idempotency)."""
        if message_id in self.processed_messages:
            return True
        
        if self.cache_service.enabled:
            cache_key = f"message:processed:{message_id}"
            if self.cache_service.get(cache_key):
                return True
        
        return False
    
    def _mark_as_processed(self, message_id: str, ttl: int = 86400):
        """Mark message as processed (24 hours TTL by default)."""
        self.processed_messages.add(message_id)
        
        if self.cache_service.enabled:
            cache_key = f"message:processed:{message_id}"
            self.cache_service.set(cache_key, {"processed_at": datetime.utcnow().isoformat()}, ttl=ttl)
    
    def _enrich_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich transaction data using strategy pattern."""
        try:
            transaction_type = transaction.get("transaction_type", "")
            strategy = TransactionStrategyFactory.get_strategy(transaction_type)
            
            metadata = transaction.get("metadata", {})
            
            if metadata:
                enriched_metadata = strategy.enrich_metadata(metadata)
                transaction["metadata"] = enriched_metadata
            
            if not transaction.get("search_content"):
                from app.schemas import TransactionCreate, TransactionType, Product, TransactionStatus
                try:
                    tx_create = TransactionCreate(
                        user_id=transaction.get("user_id", ""),
                        transaction_type=TransactionType(transaction.get("transaction_type", "card")),
                        product=Product(transaction.get("product", "Card")),
                        status=TransactionStatus(transaction.get("status", "completed")),
                        currency=transaction.get("currency", "USD"),
                        amount=float(transaction.get("amount", 0)),
                        metadata=transaction.get("metadata", {})
                    )
                    search_content = strategy.build_search_content(tx_create)
                    transaction["search_content"] = search_content
                except Exception as e:
                    logger.warning("Failed to build search content", error=str(e))
                    transaction["search_content"] = (
                        f"{transaction_type} {transaction.get('amount', 0)} "
                        f"{transaction.get('currency', 'USD')} {transaction.get('status', 'completed')}"
                    )
            
            transaction["_enriched"] = True
            transaction["_enriched_at"] = datetime.utcnow().isoformat()
            
            return transaction
        except Exception as e:
            logger.warning("Failed to enrich transaction", error=str(e), transaction_id=transaction.get("id"))
            return transaction
    
    def _add_version(self, transaction: Dict[str, Any], version: Optional[int] = None) -> Dict[str, Any]:
        """Add versioning to transaction document."""
        if version is None:
            try:
                if self.search_service.enabled:
                    response = self.search_service.es_client.get(
                        index="transactions",
                        id=str(transaction.get("id", ""))
                    )
                    current_version = response.get("_version", 0)
                    doc_version = response.get("_source", {}).get("_version", 0)
                    version = max(current_version, doc_version) + 1
                else:
                    version = 1
            except Exception:
                version = 1
        
        transaction["_version"] = version
        transaction["_updated_at"] = datetime.utcnow().isoformat()
        return transaction
    
    def _write_to_audit_db(self, transaction: Dict[str, Any], event_type: str):
        """Write transaction to database for audit/backup purposes."""
        if not self.enable_audit_db:
            return
        
        db = SessionLocal()
        try:
            repository = TransactionRepository(db)
            existing = repository.get_by_id(str(transaction.get("id", "")))
            
            if event_type == "transaction.deleted":
                if existing:
                    repository.delete(existing)
                    logger.info("Transaction deleted from audit DB", transaction_id=transaction.get("id"))
            else:
                db_transaction_data = {
                    "id": transaction.get("id"),
                    "user_id": transaction.get("user_id", ""),
                    "transaction_type": transaction.get("transaction_type", ""),
                    "product": transaction.get("product", ""),
                    "status": transaction.get("status", ""),
                    "currency": transaction.get("currency", ""),
                    "amount": transaction.get("amount", 0),
                    "custom_metadata": transaction.get("metadata", {}),
                    "search_content": transaction.get("search_content", ""),
                }
                
                if existing:
                    repository.update(existing, db_transaction_data)
                    logger.debug("Transaction updated in audit DB", transaction_id=transaction.get("id"))
                else:
                    repository.create(db_transaction_data)
                    logger.debug("Transaction written to audit DB", transaction_id=transaction.get("id"))
        except Exception as e:
            logger.warning("Failed to write to audit DB", error=str(e), transaction_id=transaction.get("id"))
        finally:
            db.close()
    
    def _process_batch(self, messages: List[Any]):
        """Process a batch of Kafka messages."""
        if not messages:
            return
        
        logger.info("Processing batch", batch_size=len(messages))
        
        successful = []
        failed = []
        
        for message in messages:
            try:
                msg_value = message.value
                message_id = self._generate_message_id(msg_value)
                event_type = msg_value.get("event_type")
                transaction = msg_value.get("transaction")
                
                if not transaction:
                    logger.warning("Message missing transaction data", event_type=event_type)
                    successful.append(message)  # Ack to avoid reprocessing
                    continue
                
                # Check idempotency
                if self._is_duplicate(message_id):
                    logger.info("Duplicate message detected, skipping", message_id=message_id, transaction_id=transaction.get("id"))
                    successful.append(message)  # Ack duplicate
                    continue
                
                logger.info(
                    "Processing transaction message",
                    event_type=event_type,
                    transaction_id=transaction.get("id"),
                    message_id=message_id
                )
                
                # Enrich transaction
                enriched_transaction = self._enrich_transaction(transaction)
                
                # Add versioning
                version = msg_value.get("version")
                versioned_transaction = self._add_version(enriched_transaction, version)
                
                # Normalize for Elasticsearch
                es_transaction = self._normalize_transaction(versioned_transaction)
                
                # Index in Elasticsearch
                if event_type in ["transaction.created", "transaction.updated"]:
                    # Extract version from transaction if present, pass as separate parameter
                    version = es_transaction.pop("_version", None)
                    success = self.search_service.index_transaction(es_transaction, version=version)
                    
                    # Write to audit DB regardless
                    try:
                        self._write_to_audit_db(es_transaction, event_type)
                    except Exception as e:
                        logger.warning("Audit DB write failed", error=str(e))
                    
                    if success:
                        self._mark_as_processed(message_id)
                        successful.append(message)
                        logger.info(
                            "Transaction indexed successfully",
                            transaction_id=es_transaction.get("id"),
                            event_type=event_type
                        )
                    else:
                        # Elasticsearch failed but saved to DB
                        self._mark_as_processed(message_id)
                        successful.append(message)  # Still ack to avoid blocking
                        logger.warning(
                            "Transaction saved to DB but not indexed in Elasticsearch (circuit breaker open)",
                            transaction_id=es_transaction.get("id"),
                            event_type=event_type
                        )
                elif event_type == "transaction.deleted":
                    transaction_id = es_transaction.get("id")
                    if transaction_id:
                        self.search_service.delete_transaction(str(transaction_id))
                        try:
                            self._write_to_audit_db(es_transaction, event_type)
                        except Exception as e:
                            logger.warning("Audit DB write failed", error=str(e))
                        
                        self._mark_as_processed(message_id)
                        successful.append(message)
                        logger.info("Transaction deleted", transaction_id=transaction_id)
                    else:
                        failed.append(message)
                else:
                    logger.warning("Unknown event type", event_type=event_type)
                    failed.append(message)
                    
            except Exception as e:
                logger.error("Error processing message", error=str(e), exc_info=True)
                failed.append(message)
        
        # Commit successful messages
        if successful:
            try:
                # Manual commit for successful messages
                if not settings.kafka_enable_auto_commit:
                    offsets = {msg.partition: {msg.offset + 1: None} for msg in successful}
                    self.consumer.commit(offsets=offsets)
                logger.info("Committed successful messages", count=len(successful))
            except Exception as e:
                logger.warning("Failed to commit messages", error=str(e))
        
        # Handle failed messages - send to DLQ topic
        if failed:
            dlq_topic = f"{settings.kafka_transactions_topic}.dlq"
            for message in failed:
                try:
                    from app.middleware.circuit_breaker import get_elasticsearch_breaker
                    es_breaker = get_elasticsearch_breaker()
                    breaker_state = es_breaker.get_state()
                    
                    if breaker_state["state"] == "open":
                        # Circuit breaker open, don't send to DLQ, will retry later
                        logger.info("Message not sent to DLQ due to circuit breaker being open")
                    else:
                        # Send to DLQ
                        dlq_message = {
                            "original_message": message.value,
                            "error": str(e) if 'e' in locals() else "Unknown error",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        self.producer.send(dlq_topic, value=dlq_message)
                        logger.warning("Message sent to DLQ", dlq_topic=dlq_topic)
                except Exception as dlq_error:
                    logger.error("Failed to send message to DLQ", error=str(dlq_error))
        
        logger.info(
            "Batch processed",
            total=len(messages),
            successful=len(successful),
            failed=len(failed)
        )
    
    def _normalize_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize transaction data for Elasticsearch indexing."""
        normalized = {
            "id": str(transaction.get("id", "")),
            "user_id": transaction.get("user_id", ""),
            "transaction_type": transaction.get("transaction_type", ""),
            "product": transaction.get("product", ""),
            "status": transaction.get("status", ""),
            "currency": transaction.get("currency", ""),
            "amount": float(transaction.get("amount", 0)),
            "metadata": transaction.get("metadata", {}),
        }
        
        created_at = transaction.get("created_at")
        if isinstance(created_at, datetime):
            normalized["created_at"] = created_at.isoformat()
        elif isinstance(created_at, str):
            normalized["created_at"] = created_at
        else:
            normalized["created_at"] = datetime.utcnow().isoformat()
        
        normalized["search_content"] = transaction.get("search_content", "")
        
        # Store _version separately (will be passed as API parameter, not in document)
        if "_version" in transaction:
            normalized["_version"] = transaction["_version"]
        if "_updated_at" in transaction:
            normalized["_updated_at"] = transaction["_updated_at"]
        if "_enriched" in transaction:
            normalized["_enriched"] = transaction["_enriched"]
        if "_enriched_at" in transaction:
            normalized["_enriched_at"] = transaction["_enriched_at"]
        
        return normalized
    
    def _check_and_reset_circuit_breaker(self):
        """Periodically check if Elasticsearch is available and reset circuit breaker if so."""
        try:
            from app.middleware.circuit_breaker import get_elasticsearch_breaker
            es_breaker = get_elasticsearch_breaker()
            breaker_state = es_breaker.get_state()
            
            # Only try to reset if circuit breaker is open
            if breaker_state["state"] == "open":
                # Try to ping Elasticsearch
                if self.search_service.enabled and self.search_service.es_client:
                    try:
                        if self.search_service.es_client.ping():
                            # Elasticsearch is available, reset circuit breaker
                            es_breaker.reset()
                            logger.info("Circuit breaker reset: Elasticsearch is now available")
                            return True
                    except Exception as e:
                        logger.debug("Elasticsearch still unavailable", error=str(e))
        except Exception as e:
            logger.debug("Error checking circuit breaker", error=str(e))
        return False
    
    def start_consuming(self):
        """Start consuming messages from Kafka."""
        if not self.enabled:
            logger.error("Cannot start consuming: Kafka not initialized")
            return
        
        logger.info(
            "Starting to consume messages",
            topic=settings.kafka_transactions_topic,
            consumer_group=settings.kafka_consumer_group,
            batch_size=self.batch_size
        )
        
        # Track last circuit breaker check
        import time
        last_circuit_check = time.time()
        circuit_check_interval = 30  # Check every 30 seconds
        
        try:
            while True:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=int(self.batch_timeout * 1000))
                
                # Periodically check and reset circuit breaker if Elasticsearch is available
                current_time = time.time()
                if current_time - last_circuit_check >= circuit_check_interval:
                    self._check_and_reset_circuit_breaker()
                    last_circuit_check = current_time
                
                if message_batch:
                    # Flatten messages from all partitions
                    all_messages = []
                    for partition_messages in message_batch.values():
                        all_messages.extend(partition_messages)
                    
                    if all_messages:
                        # Process batch
                        self._process_batch(all_messages)
                else:
                    # No messages, check if we should process buffered messages
                    if self.message_buffer:
                        logger.debug("Timeout reached, processing buffered messages", buffer_size=len(self.message_buffer))
                        # Process any buffered messages (not used in Kafka, but kept for compatibility)
                        pass
                
        except KeyboardInterrupt:
            logger.info("Stopping message consumer")
        except Exception as e:
            logger.error("Error in consumer loop", error=str(e), exc_info=True)
        finally:
            self.close()
    
    def close(self):
        """Close Kafka connections."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")
