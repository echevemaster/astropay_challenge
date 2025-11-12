#!/usr/bin/env python3
"""
Quick diagnostic script to check Kafka consumer status.

Usage:
    python check_consumer.py
"""
import os
import sys

try:
    from kafka import KafkaConsumer
    from kafka.admin import KafkaAdminClient
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False

# Detect if we're in Docker
if os.getenv("DOCKER_CONTAINER"):
    kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093").split(',')
else:
    from app.config import settings
    kafka_servers = settings.kafka_bootstrap_servers.split(',')


def check_consumer_status():
    """Checks consumer status and Kafka topics."""
    print("🔍 Checking Kafka consumer status...")
    print("-" * 60)
    
    if not HAS_KAFKA:
        print("❌ kafka-python is not installed")
        print("   Install with: pip install kafka-python")
        print("   Or run in Docker where it's available")
        return
    
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=kafka_servers,
            client_id='check_consumer_admin'
        )
        
        topic_name = "transactions"
        
        # Check topic
        try:
            metadata = admin_client.describe_topics([topic_name])
            if topic_name in metadata:
                topic_metadata = metadata[topic_name]
                partitions = len(topic_metadata.partitions)
                
                print(f"📬 Topic: {topic_name}")
                print(f"   Partitions: {partitions}")
                print()
                
                # Check consumer group
                try:
                    consumer = KafkaConsumer(
                        bootstrap_servers=kafka_servers,
                        group_id="transaction_indexer",
                        consumer_timeout_ms=1000
                    )
                    
                    # Get consumer group information
                    print("👥 Consumer Group: transaction_indexer")
                    print("   ✅ Consumer can connect to Kafka")
                    consumer.close()
                except Exception as e:
                    print(f"   ⚠️  Error checking consumer group: {e}")
                
                print()
                print("💡 For more details:")
                print("   1. View consumer logs:")
                print("      docker-compose logs -f consumer")
                print("   2. Check Kafka status:")
                print("      docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092")
                print("   3. Check consumer group offsets:")
                print("      docker-compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group transaction_indexer --describe")
            else:
                print(f"⚠️  Topic '{topic_name}' does not exist")
                print("   Consumer should create it automatically on startup")
                
        except Exception as e:
            error_str = str(e)
            if "UnknownTopicOrPartition" in error_str or "does not exist" in error_str:
                print(f"⚠️  Topic '{topic_name}' does not exist")
                print("   Consumer should create it automatically on startup")
            else:
                print(f"❌ Error checking topic: {e}")
        
        admin_client.close()
        
    except Exception as e:
        print(f"❌ Error connecting to Kafka: {e}")
        print(f"   Servers: {', '.join(kafka_servers)}")
        print()
        print("   Make sure Kafka is running:")
        print("   docker-compose up -d kafka zookeeper")


if __name__ == "__main__":
    check_consumer_status()
