#!/usr/bin/env python3
"""
Script to publish synthetic data to Kafka simulating microservice events.

This script generates synthetic transactions and publishes them to Kafka as events,
simulating that they come from different microservices (Card, P2P, Crypto, etc.).

Usage:
    python publish_test_data_to_kafka.py [--count N] [--user-id USER_ID]

Or in Docker:
    docker-compose run --rm --profile publish-data publish_test_data
"""
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import random
import uuid
import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

# Import generation functions from the original script
# (We copy the constants and generation functions)
MERCHANTS = [
    "Starbucks", "McDonald's", "Amazon", "Walmart", "Target", "Best Buy",
    "Home Depot", "Costco", "CVS Pharmacy", "Walgreens", "Whole Foods",
    "Trader Joe's", "Subway", "Pizza Hut", "Domino's", "Uber", "Lyft",
    "Netflix", "Spotify", "Apple Store", "Google Play", "Steam",
    "Nike", "Adidas", "Zara", "H&M", "Macy's", "Nordstrom", "Sephora",
    "Shell", "Exxon", "BP", "Chevron", "7-Eleven", "Circle K"
]

MERCHANT_CATEGORIES = [
    "Food & Beverage", "Retail", "Gas Station", "Entertainment",
    "Shopping", "Transportation", "Subscription", "Electronics",
    "Clothing", "Pharmacy", "Grocery", "Restaurant", "Coffee Shop"
]

LOCATIONS = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
    "Dallas, TX", "San Jose, CA", "Austin, TX", "Jacksonville, FL",
    "San Francisco, CA", "Columbus, OH", "Fort Worth, TX", "Charlotte, NC",
    "Seattle, WA", "Denver, CO", "Boston, MA", "Miami, FL"
]

PEER_NAMES = [
    "John Doe", "Jane Smith", "Bob Johnson", "Alice Williams",
    "Charlie Brown", "Diana Prince", "Edward Norton", "Fiona Apple",
    "George Washington", "Hannah Montana", "Isaac Newton", "Julia Roberts",
    "Kevin Hart", "Laura Palmer", "Michael Jackson", "Nancy Drew",
    "Oliver Twist", "Patricia Smith", "Quentin Tarantino", "Rachel Green"
]

PEER_EMAILS = [
    "john@example.com", "jane@example.com", "bob@example.com",
    "alice@example.com", "charlie@example.com", "diana@example.com",
    "edward@example.com", "fiona@example.com", "george@example.com",
    "hannah@example.com"
]

CRYPTO_TYPES = ["Bitcoin", "Ethereum", "USDC", "USDT", "Litecoin", "Bitcoin Cash"]
CRYPTO_CURRENCY_CODES = {
    "Bitcoin": "BTC",
    "Ethereum": "ETH",
    "USDC": "USDC",
    "USDT": "USDT",
    "Litecoin": "LTC",
    "Bitcoin Cash": "BCH"
}

CURRENCIES = ["USD", "EUR", "GBP", "BRL", "MXN", "ARS"]
TRANSACTION_TYPES = ["card", "p2p", "crypto", "top_up", "withdrawal", "bill_payment", "earnings"]
PRODUCTS = ["Card", "P2P", "Crypto", "Earnings"]
STATUSES = ["completed", "pending", "failed", "cancelled"]
DIRECTIONS = ["sent", "received"]


def generate_card_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a card transaction."""
    merchant = random.choice(MERCHANTS)
    category = random.choice(MERCHANT_CATEGORIES)
    location = random.choice(LOCATIONS)
    card_last_four = f"{random.randint(1000, 9999):04d}"
    
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "transaction_type": "card",
        "product": "Card",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(5.00, 500.00), 2),
        "created_at": date.isoformat(),
        "metadata": {
            "merchant_name": merchant,
            "merchant_category": category,
            "card_last_four": card_last_four,
            "location": location
        }
    }


def generate_p2p_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a P2P transaction."""
    direction = random.choice(DIRECTIONS)
    peer_name = random.choice(PEER_NAMES)
    peer_email = random.choice(PEER_EMAILS)
    
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "transaction_type": "p2p",
        "product": "P2P",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(10.00, 1000.00), 2),
        "created_at": date.isoformat(),
        "metadata": {
            "direction": direction,
            "peer_name": peer_name,
            "peer_email": peer_email,
            "description": f"P2P transfer {direction} to {peer_name}"
        }
    }


def generate_crypto_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a crypto transaction."""
    crypto_type = random.choice(CRYPTO_TYPES)
    currency_code = CRYPTO_CURRENCY_CODES.get(crypto_type, "BTC")
    
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "transaction_type": "crypto",
        "product": "Crypto",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": currency_code,
        "amount": round(random.uniform(0.001, 10.0), 6),
        "created_at": date.isoformat(),
        "metadata": {
            "crypto_type": crypto_type,
            "wallet_address": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
            "transaction_hash": f"0x{''.join(random.choices('0123456789abcdef', k=64))}"
        }
    }


def generate_top_up_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a top-up transaction."""
    payment_method = random.choice(["card", "bank_transfer", "crypto"])
    card_last_four = f"{random.randint(1000, 9999):04d}" if payment_method == "card" else None
    
    metadata = {
        "payment_method": payment_method
    }
    if card_last_four:
        metadata["card_last_four"] = card_last_four
    
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "transaction_type": "top_up",
        "product": "Card",
        "status": random.choice(["completed", "pending"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(50.00, 1000.00), 2),
        "created_at": date.isoformat(),
        "metadata": metadata
    }


def generate_withdrawal_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a withdrawal transaction."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "transaction_type": "withdrawal",
        "product": "Card",
        "status": random.choice(["completed", "pending", "failed"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(20.00, 500.00), 2),
        "created_at": date.isoformat(),
        "metadata": {
            "bank_account": f"****{random.randint(1000, 9999)}",
            "bank_name": random.choice(["Chase", "Bank of America", "Wells Fargo", "Citibank"])
        }
    }


def generate_bill_payment_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a bill payment transaction."""
    billers = ["Electric Company", "Water Company", "Internet Provider", "Phone Company", "Credit Card"]
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "transaction_type": "bill_payment",
        "product": "Card",
        "status": random.choice(["completed", "pending"]),
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(30.00, 300.00), 2),
        "created_at": date.isoformat(),
        "metadata": {
            "biller_name": random.choice(billers),
            "account_number": f"****{random.randint(1000, 9999)}"
        }
    }


def generate_earnings_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates an earnings transaction."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "transaction_type": "earnings",
        "product": "Earnings",
        "status": "completed",
        "currency": random.choice(CURRENCIES),
        "amount": round(random.uniform(5.00, 200.00), 2),
        "created_at": date.isoformat(),
        "metadata": {
            "source": random.choice(["Referral", "Cashback", "Rewards", "Bonus"])
        }
    }


def generate_transaction(user_id: str, date: datetime) -> Dict[str, Any]:
    """Generates a random transaction."""
    transaction_type = random.choice(TRANSACTION_TYPES)
    generators = {
        "card": generate_card_transaction,
        "p2p": generate_p2p_transaction,
        "crypto": generate_crypto_transaction,
        "top_up": generate_top_up_transaction,
        "withdrawal": generate_withdrawal_transaction,
        "bill_payment": generate_bill_payment_transaction,
        "earnings": generate_earnings_transaction
    }
    return generators[transaction_type](user_id, date)


def publish_message(producer: KafkaProducer, topic: str, transaction: Dict[str, Any], event_type: str = "transaction.created"):
    """Publishes a message to Kafka."""
    message = {
        "event_type": event_type,
        "transaction": transaction,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "synthetic_data_generator"
    }
    
    # Use user_id as partition key for better distribution
    partition_key = transaction.get("user_id", "").encode('utf-8') if transaction.get("user_id") else None
    
    try:
        future = producer.send(
            topic=topic,
            value=message,
            key=partition_key
        )
        # Wait for the message to be sent
        future.get(timeout=10)
        return True
    except KafkaError as e:
        print(f"❌ Error publishing message: {e}")
        return False


def main():
    """Main function to publish synthetic data to Kafka."""
    parser = argparse.ArgumentParser(description="Publish synthetic data to Kafka")
    parser.add_argument("--count", type=int, default=1000, help="Number of transactions to generate (default: 1000)")
    parser.add_argument("--user-id", type=str, default="test_user_123", help="User ID for transactions")
    parser.add_argument("--kafka-servers", type=str, help="Kafka bootstrap servers (default: from env or config)")
    parser.add_argument("--topic", type=str, help="Kafka topic (default: from env or config)")
    parser.add_argument("--update-ratio", type=float, default=0.1, help="Ratio of updates vs creates (default: 0.1)")
    
    args = parser.parse_args()
    
    # Get Kafka configuration
    if os.getenv("DOCKER_CONTAINER"):
        kafka_servers = args.kafka_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093")
    else:
        kafka_servers = args.kafka_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    topic = args.topic or os.getenv("KAFKA_TRANSACTIONS_TOPIC", "transactions")
    
    print(f"🚀 Publishing {args.count} synthetic transactions to Kafka...")
    print(f"   User ID: {args.user_id}")
    print(f"   Kafka Servers: {kafka_servers}")
    print(f"   Topic: {topic}")
    print("-" * 60)
    
    # Connect to Kafka
    try:
        producer = KafkaProducer(
            bootstrap_servers=kafka_servers.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1
            # Note: kafka-python doesn't support enable_idempotence parameter
            # Idempotence is handled at the application level
        )
        
        print("✅ Connected to Kafka")
        print(f"✅ Topic: '{topic}'")
        print()
        
        # Generate transactions
        base_date = datetime.now()
        dates = [base_date - timedelta(days=random.randint(0, 90)) for _ in range(args.count)]
        dates.sort()
        
        created_transactions = {}  # Store for potential updates
        success_count = 0
        error_count = 0
        
        for i, date in enumerate(dates, 1):
            try:
                # Decide if this is a create or update
                is_update = random.random() < args.update_ratio and created_transactions
                
                if is_update and created_transactions:
                    # Update an existing transaction
                    existing_id = random.choice(list(created_transactions.keys()))
                    transaction = created_transactions[existing_id].copy()
                    transaction["status"] = random.choice(["completed", "pending", "failed"])
                    transaction["updated_at"] = datetime.utcnow().isoformat()
                    event_type = "transaction.updated"
                else:
                    # Create new transaction
                    transaction = generate_transaction(args.user_id, date)
                    created_transactions[transaction["id"]] = transaction
                    event_type = "transaction.created"
                
                # Publish message
                if publish_message(producer, topic, transaction, event_type):
                    success_count += 1
                else:
                    error_count += 1
                
                if i % 100 == 0:
                    print(f"✅ Progress: {i}/{args.count} messages published ({success_count} successful, {error_count} errors)")
                
                # Small delay to avoid overwhelming Kafka
                if i % 50 == 0:
                    import time
                    time.sleep(0.1)
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Error publishing message {i}: {e}")
        
        # Flush remaining messages
        producer.flush(timeout=30)
        producer.close()
        
        print("-" * 60)
        print(f"✅ Completed!")
        print(f"   Total: {success_count + error_count}")
        print(f"   Successful: {success_count}")
        print(f"   Errors: {error_count}")
        print(f"\n📊 Messages published for user_id: {args.user_id}")
        print(f"🔍 The consumer should be processing these messages automatically")
        print(f"💡 Check the consumer logs to see the processing")
        
    except KafkaError as e:
        print(f"❌ Error connecting to Kafka: {e}")
        print(f"   Servers: {kafka_servers}")
        print(f"\n   Make sure Kafka is running:")
        print(f"   docker-compose up -d kafka zookeeper")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

