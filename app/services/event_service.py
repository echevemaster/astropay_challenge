"""Event service for publishing transaction events to Kafka."""
import json
from typing import Dict, Any, Optional
from app.config import settings
import structlog

logger = structlog.get_logger()

# Optional Kafka imports - handle case when kafka-python is not installed
try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False
    KafkaProducer = None  # type: ignore
    KafkaError = Exception  # type: ignore

try:
    from app.middleware.circuit_breaker import get_kafka_breaker, CircuitBreakerOpenError
    HAS_CIRCUIT_BREAKER = True
except ImportError:
    HAS_CIRCUIT_BREAKER = False
    CircuitBreakerOpenError = Exception  # type: ignore
    
    def get_kafka_breaker():
        """Mock circuit breaker when not available."""
        class MockBreaker:
            def call(self, func, *args, **kwargs):
                return func(*args, **kwargs)
        return MockBreaker()


class EventService:
    """Service for publishing events to Kafka."""
    
    def __init__(self):
        if not HAS_KAFKA:
            logger.warning("kafka-python not installed, events disabled")
            self.producer = None
            self.enabled = False
            self.topic = ""
            return
        
        try:
            bootstrap_servers = settings.kafka_bootstrap_servers.split(',')
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1  # Ensure ordering
                # Note: kafka-python doesn't support enable_idempotence parameter
                # Idempotence is handled at the application level via message IDs
            )
            self.topic = settings.kafka_transactions_topic
            self.enabled = True
            logger.info("Kafka producer initialized", topic=self.topic)
        except Exception as e:
            logger.warning("Kafka connection failed, events disabled", error=str(e))
            self.producer = None
            self.enabled = False
            self.topic = ""
    
    def _publish_event(self, event_type: str, transaction: Dict[str, Any]) -> bool:
        """Publish an event to Kafka."""
        if not self.enabled or not HAS_KAFKA:
            return False
        try:
            breaker = get_kafka_breaker()
            message = {
                "event_type": event_type,
                "transaction": transaction,
                "timestamp": transaction.get("created_at") or transaction.get("updated_at")
            }
            
            # Determine partition key (use user_id for partitioning)
            partition_key = transaction.get("user_id", "").encode('utf-8') if transaction.get("user_id") else None
            
            breaker.call(
                self.producer.send,
                topic=self.topic,
                value=message,
                key=partition_key
            )
            
            # Flush to ensure message is sent
            self.producer.flush(timeout=5)
            return True
        except CircuitBreakerOpenError:
            logger.warning("Kafka publish skipped: circuit breaker open")
            return False
        except (KafkaError if HAS_KAFKA else Exception) as e:
            logger.warning("Failed to publish event to Kafka", error=str(e), event_type=event_type)
            return False
        except Exception as e:
            logger.warning("Failed to publish event", error=str(e), event_type=event_type)
            return False
    
    def publish_transaction_created(self, transaction: Dict[str, Any]) -> bool:
        """Publish transaction created event."""
        return self._publish_event("transaction.created", transaction)
    
    def publish_transaction_updated(self, transaction: Dict[str, Any]) -> bool:
        """Publish transaction updated event."""
        return self._publish_event("transaction.updated", transaction)
    
    def publish_transaction_deleted(self, transaction_id: str) -> bool:
        """Publish transaction deleted event."""
        transaction = {"id": transaction_id}
        return self._publish_event("transaction.deleted", transaction)
    
    def health_check(self) -> bool:
        """Check if event service is healthy."""
        if not self.enabled:
            return False
        try:
            # Try to get metadata to verify connection
            if self.producer:
                metadata = self.producer.list_topics(timeout=5)
                return metadata is not None
            return False
        except Exception:
            return False
    
    def close(self):
        """Close producer connection."""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")
