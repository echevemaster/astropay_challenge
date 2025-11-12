#!/usr/bin/env python3
"""
Enhanced worker to consume messages from Kafka and index in Elasticsearch.

Features:
- Idempotency
- Batch processing
- Dead Letter Queue
- Data enrichment
- Document versioning
- Database writing for audit/backup

Run:
    python consumer_worker.py

Or in Docker:
    docker-compose up consumer
"""
import signal
import sys
import os
from app.services.search_service import SearchService
from app.services.cache_service import CacheService
from app.services.message_consumer import MessageConsumer
from app.config import settings
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Global consumer instance for signal handler
consumer = None


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal, stopping consumer...")
    global consumer
    if consumer:
        consumer.close()
    sys.exit(0)


def main():
    """Main function to start the consumer."""
    global consumer
    
    logger.info("Starting enhanced transaction message consumer...")
    
    # Initialize services
    try:
        search_service = SearchService()
        if not search_service.enabled:
            logger.warning("Elasticsearch is not available. Consumer will start but messages will only be saved to DB.")
            logger.warning("Messages will be saved to database for later indexing when Elasticsearch is available.")
        
        cache_service = CacheService()
        if not cache_service.enabled:
            logger.warning("Redis is not available. Idempotency will be limited to in-memory.")
        
        # Get configuration from environment or use defaults
        batch_size = int(os.getenv("CONSUMER_BATCH_SIZE", "10"))
        batch_timeout = float(os.getenv("CONSUMER_BATCH_TIMEOUT", "5.0"))
        enable_audit_db = os.getenv("CONSUMER_ENABLE_AUDIT_DB", "true").lower() == "true"
        
        consumer = MessageConsumer(
            search_service=search_service,
            cache_service=cache_service,
            batch_size=batch_size,
            batch_timeout=batch_timeout,
            enable_audit_db=enable_audit_db
        )
        
        if not consumer.enabled:
            logger.error("Kafka is not available. Cannot start consumer.")
            sys.exit(1)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info(
            "Consumer initialized successfully",
            batch_size=batch_size,
            batch_timeout=batch_timeout,
            audit_db_enabled=enable_audit_db
        )
        logger.info("Starting to consume messages...")
        
        # Start consuming (this blocks)
        consumer.start_consuming()
        
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error("Fatal error in consumer", error=str(e), exc_info=True)
        sys.exit(1)
    finally:
        if consumer:
            consumer.close()
        logger.info("Consumer shutdown complete")


if __name__ == "__main__":
    main()

