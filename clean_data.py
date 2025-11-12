"""
Script to clean all data from the database and Elasticsearch.
"""
import os
import sys
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from elasticsearch import Elasticsearch
from app.config import settings
from app.database import Base
import structlog

logger = structlog.get_logger()

# Detect if we're in Docker
if os.getenv("DOCKER_CONTAINER"):
    ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
else:
    ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")


def clean_database():
    """Deletes all transactions from the database."""
    try:
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with SessionLocal() as session:
            # Delete all transactions
            result = session.execute(text("DELETE FROM transactions"))
            session.commit()
            deleted_count = result.rowcount
            
            logger.info(f"✅ Deleted {deleted_count} transactions from database")
            return deleted_count
    except Exception as e:
        logger.error(f"❌ Error cleaning database: {e}")
        return 0


def clean_elasticsearch():
    """Deletes all documents from the Elasticsearch index."""
    try:
        es_client = Elasticsearch(
            [ELASTICSEARCH_URL],
            request_timeout=10,
            max_retries=3,
            retry_on_timeout=True,
        )
        
        # Verify connection
        if not es_client.ping():
            logger.warning("⚠️  Elasticsearch is not available")
            return 0
        
        index_name = "transactions"
        
        # Check if index exists
        if not es_client.indices.exists(index=index_name):
            logger.info("ℹ️  Elasticsearch index does not exist")
            return 0
        
        # Delete all documents from index using delete_by_query
        # Use same syntax as in search_service.py (with 'body')
        query_body = {
            "query": {
                "match_all": {}
            }
        }
        
        response = es_client.delete_by_query(
            index=index_name,
            body=query_body,
            refresh=True
        )
        
        deleted_count = response.get("deleted", 0)
        logger.info(f"✅ Deleted {deleted_count} documents from Elasticsearch")
        return deleted_count
    except Exception as e:
        logger.error(f"❌ Error cleaning Elasticsearch: {e}")
        return 0


def clean_redis():
    """Cleans Redis cache and idempotency keys."""
    try:
        import redis
        from urllib.parse import urlparse
        
        # Parse Redis URL
        parsed = urlparse(settings.redis_url)
        redis_client = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=int(parsed.path.lstrip("/")) if parsed.path else 0,
            decode_responses=True
        )
        
        total_deleted = 0
        
        # Delete all transaction-related keys
        transaction_keys = redis_client.keys("transactions:*")
        if transaction_keys:
            deleted = redis_client.delete(*transaction_keys)
            total_deleted += deleted
            logger.info(f"✅ Deleted {deleted} transaction cache keys")
        
        # Delete consumer idempotency keys
        message_keys = redis_client.keys("message:processed:*")
        if message_keys:
            deleted = redis_client.delete(*message_keys)
            total_deleted += deleted
            logger.info(f"✅ Deleted {deleted} idempotency keys")
        
        if total_deleted > 0:
            logger.info(f"✅ Total deleted {total_deleted} Redis keys")
            return total_deleted
        else:
            logger.info("ℹ️  No cache keys to delete")
            return 0
    except Exception as e:
        logger.warning(f"⚠️  Error cleaning Redis (may not be available): {e}")
        return 0


def clean_kafka():
    """Cleans Kafka topics (optional)."""
    try:
        try:
            from kafka.admin import KafkaAdminClient, NewTopic
            from kafka.errors import KafkaError
        except ImportError:
            logger.warning("⚠️  kafka-python is not installed. Cannot clean Kafka.")
            logger.warning("💡 Install kafka-python or run script in Docker where it's available")
            return 0
        
        # Detect if we're in Docker
        if os.getenv("DOCKER_CONTAINER"):
            bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093").split(',')
        else:
            bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", settings.kafka_bootstrap_servers).split(',')
        
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='clean_data_admin'
        )
        
        topics_to_clean = [
            settings.kafka_transactions_topic,  # Main topic
            f"{settings.kafka_transactions_topic}.dlq"  # Dead Letter Topic
        ]
        
        total_deleted = 0
        
        for topic_name in topics_to_clean:
            try:
                # Check if topic exists and delete it
                try:
                    metadata = admin_client.describe_topics([topic_name])
                    if topic_name in metadata:
                        # Delete topic (kafka-python uses delete_topics with list of topic names)
                        admin_client.delete_topics([topic_name])
                        total_deleted += 1
                        logger.info(f"✅ Deleted topic '{topic_name}'")
                    else:
                        logger.info(f"ℹ️  Topic '{topic_name}' does not exist")
                except Exception as e:
                    error_str = str(e)
                    if "UnknownTopicOrPartition" in error_str or "does not exist" in error_str or "TopicDoesNotExist" in error_str:
                        logger.info(f"ℹ️  Topic '{topic_name}' does not exist")
                    else:
                        # Try to delete anyway
                        try:
                            admin_client.delete_topics([topic_name])
                            total_deleted += 1
                            logger.info(f"✅ Deleted topic '{topic_name}' (forced)")
                        except:
                            logger.warning(f"⚠️  Could not delete topic '{topic_name}': {e}")
                        
            except Exception as e:
                logger.warning(f"⚠️  Error cleaning topic '{topic_name}': {e}")
        
        admin_client.close()
        
        if total_deleted > 0:
            logger.info(f"✅ Total: {total_deleted} topics deleted")
            return total_deleted
        else:
            return 0
    except ImportError as e:
        logger.warning(f"⚠️  kafka-python is not installed: {e}")
        logger.warning("💡 Install kafka-python or run script in Docker where it's available")
        logger.warning("💡 Note: In Kafka, messages are automatically deleted according to retention configuration")
        return 0
    except Exception as e:
        logger.warning(f"⚠️  Error cleaning Kafka (may not be available): {e}")
        logger.warning("💡 Note: In Kafka, messages are automatically deleted according to retention configuration")
        return 0


def main():
    """Main function to clean all data."""
    print("🧹 Cleaning application data...")
    print("-" * 60)
    
    # Clean database
    print("📊 Cleaning PostgreSQL database...")
    db_count = clean_database()
    
    # Clean Elasticsearch
    print("🔍 Cleaning Elasticsearch...")
    es_count = clean_elasticsearch()
    
    # Clean Redis (optional, not critical if it fails)
    print("💾 Cleaning Redis cache...")
    redis_count = clean_redis()
    
    # Clean Kafka (optional, not critical if it fails)
    print("📨 Cleaning Kafka topics...")
    kafka_count = clean_kafka()
    
    print("-" * 60)
    print("✅ Cleanup completed!")
    print(f"   - Database: {db_count} transactions deleted")
    print(f"   - Elasticsearch: {es_count} documents deleted")
    print(f"   - Redis: {redis_count} keys deleted")
    print(f"   - Kafka: {kafka_count} topics deleted")
    print()
    print("💡 You can now load new data with:")
    print("   ./load_test_data_docker.sh")
    print("   or")
    print("   docker-compose --profile test-data run --rm load_test_data")
    print()
    print("💡 Or publish data to Kafka with:")
    print("   python publish_test_data_to_kafka.py --count 1000")
    print("   or")
    print("   docker-compose run --rm --profile publish-data publish_test_data")


if __name__ == "__main__":
    main()
