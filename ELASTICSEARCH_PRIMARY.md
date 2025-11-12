# Elasticsearch as Primary Data Source

This guide explains how to use Elasticsearch as the primary data source instead of PostgreSQL, receiving transactions from Kafka.

## 🏗️ Architecture

```
┌─────────────┐
│  Kafka      │  ← Transactions from external systems
└──────┬──────┘
       │
       │ Messages (transaction.created, transaction.updated, etc.)
       │
       ▼
┌─────────────────────┐
│ Message Consumer     │  ← Consumes messages and indexes in Elasticsearch
│ (message_consumer.py)│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Elasticsearch       │  ← Primary data source
│  (transactions)      │
└──────┬──────────────┘
       │
       │ Direct queries
       │
       ▼
┌─────────────────────┐
│  API Endpoints       │  ← Returns data from Elasticsearch
│  (FastAPI)           │
└─────────────────────┘
```

## 📦 Components

### 1. Message Consumer (`app/services/message_consumer.py`)

Kafka consumer that receives transactions and indexes them in Elasticsearch.

**Features:**
- Listens to events: `transaction.created`, `transaction.updated`, `transaction.deleted`
- Normalizes data before indexing
- Error handling and retry
- Message acknowledgment

### 2. Elasticsearch Transaction Service (`app/services/elasticsearch_transaction_service.py`)

Service that gets data directly from Elasticsearch (without PostgreSQL).

**Methods:**
- `get_transactions()`: Gets transactions with offset pagination
- `get_transactions_cursor()`: Gets transactions with cursor pagination
- `get_transaction()`: Gets a transaction by ID

### 3. Enhanced Search Service

The `SearchService` now supports:
- `return_documents=True`: Returns complete documents instead of just IDs
- Metadata filters in Elasticsearch
- Searches without query (filters only)

## 🚀 Usage

### Option 1: Use Elasticsearch as Primary Source

Modify `app/api/dependencies.py` to use `ElasticsearchTransactionService`:

```python
from app.services.elasticsearch_transaction_service import ElasticsearchTransactionService

def get_transaction_service(
    db: Session = Depends(get_db),
    cache_service: CacheService = Depends(get_cache_service),
    search_service: SearchService = Depends(get_search_service)
) -> ElasticsearchTransactionService:
    """Get transaction service using Elasticsearch as primary source."""
    return ElasticsearchTransactionService(
        search_service=search_service,
        cache_service=cache_service
    )
```

### Option 2: Start the Message Consumer

Create a script to start the consumer:

```python
# consumer_worker.py
from app.services.search_service import SearchService
from app.services.message_consumer import MessageConsumer
import signal
import sys

def signal_handler(sig, frame):
    print('Stopping consumer...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Initialize services
search_service = SearchService()
consumer = MessageConsumer(search_service)

# Start consuming
consumer.start_consuming()
```

Run the worker:

```bash
python consumer_worker.py
```

Or in Docker:

```yaml
# docker-compose.yml
consumer:
  build:
    context: .
    dockerfile: Dockerfile
  command: python consumer_worker.py
  environment:
    ELASTICSEARCH_URL: http://elasticsearch:9200
    KAFKA_BOOTSTRAP_SERVERS: kafka:9093
    KAFKA_TRANSACTIONS_TOPIC: transactions
    KAFKA_CONSUMER_GROUP: transaction_indexer
  depends_on:
    - elasticsearch
    - kafka
    - zookeeper
```

## 📨 Message Format

### Kafka

Messages must have this format:

```json
{
  "event_type": "transaction.created",
  "transaction": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user123",
    "transaction_type": "card",
    "product": "Card",
    "status": "completed",
    "currency": "USD",
    "amount": 150.00,
    "created_at": "2024-01-15T10:30:00Z",
    "search_content": "Card 150.00 USD completed Starbucks Food & Beverage San Francisco, CA",
    "metadata": {
      "merchant_name": "Starbucks",
      "merchant_category": "Food & Beverage",
      "card_last_four": "5678",
      "location": "San Francisco, CA"
    }
  }
}
```

### Supported Events

- `transaction.created`: New transaction (indexed in Elasticsearch)
- `transaction.updated`: Transaction updated (updated in Elasticsearch)
- `transaction.deleted`: Transaction deleted (deleted from Elasticsearch)

## 🔍 Queries

### With Elasticsearch as Primary Source

All queries go directly to Elasticsearch:

```python
# GET /api/v1/transactions?user_id=user123
# → Searches directly in Elasticsearch

# GET /api/v1/transactions?user_id=user123&card_last_four=5678
# → Filters by metadata in Elasticsearch

# GET /api/v1/transactions?user_id=user123&search_query=Starbucks
# → Full-text search in Elasticsearch
```

### Metadata Filters in Elasticsearch

The `SearchService` now supports metadata filters:

```python
filters = {
    "transaction_type": "card",
    "metadata_filters": {
        "card_last_four": "5678",
        "merchant_name": "Starbucks"
    }
}
```

## ⚙️ Configuration

### Environment Variables

```bash
# Elasticsearch (required)
ELASTICSEARCH_URL=http://elasticsearch:9200

# Kafka (for consumer)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TRANSACTIONS_TOPIC=transactions
KAFKA_CONSUMER_GROUP=transaction_indexer

# Redis (for cache)
REDIS_URL=redis://redis:6379/0
```

### Elasticsearch Mapping

The `transactions` index must have this mapping:

```json
{
  "mappings": {
    "properties": {
      "id": {"type": "keyword"},
      "user_id": {"type": "keyword"},
      "transaction_type": {"type": "keyword"},
      "product": {"type": "keyword"},
      "status": {"type": "keyword"},
      "currency": {"type": "keyword"},
      "amount": {"type": "float"},
      "created_at": {"type": "date"},
      "search_content": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "keyword": {"type": "keyword"}
        }
      },
      "metadata": {
        "type": "object",
        "enabled": true
      }
    }
  }
}
```

## 🔄 Complete Flow

### 1. Transaction Reception

```
External System → Kafka → Message Consumer → Elasticsearch
```

### 2. Queries

```
Client → API → ElasticsearchTransactionService → Elasticsearch → Response
```

### 3. Cache

```
Client → API → Redis (cache) → Elasticsearch (if not in cache) → Response
```

## 📊 Advantages

1. **Performance**: Faster queries in Elasticsearch
2. **Scalability**: Elasticsearch scales horizontally
3. **Advanced Search**: Native full-text search
4. **Decoupling**: External systems only publish events
5. **Resilience**: If Elasticsearch fails, you can have fallback to PostgreSQL

## ⚠️ Considerations

1. **Consistency**: Elasticsearch is eventually consistent (not ACID)
2. **Durability**: Consider replication and backups
3. **Fallback**: Keep PostgreSQL as backup if critical
4. **Synchronization**: If you use both, keep them synchronized

## 🔧 Integration Example

### Publish Transaction from External System

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

message = {
    "event_type": "transaction.created",
    "transaction": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user123",
        "transaction_type": "card",
        "product": "Card",
        "status": "completed",
        "currency": "USD",
        "amount": 150.00,
        "created_at": "2024-01-15T10:30:00Z",
        "search_content": "Card 150.00 USD completed Starbucks",
        "metadata": {
            "merchant_name": "Starbucks",
            "card_last_four": "5678"
        }
    }
}

producer.send('transactions', value=message)
producer.flush()
```

## 🧪 Testing

To test the consumer:

```bash
# 1. Start services
docker-compose up -d elasticsearch kafka zookeeper

# 2. Start the consumer
python consumer_worker.py

# 3. Publish a test message
python -c "
from kafka import KafkaProducer
import json
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
producer.send('transactions', value={
    'event_type': 'transaction.created',
    'transaction': {
        'id': 'test-123',
        'user_id': 'user123',
        'transaction_type': 'card',
        'product': 'Card',
        'status': 'completed',
        'currency': 'USD',
        'amount': 100.0,
        'created_at': '2024-01-15T10:30:00Z',
        'search_content': 'Test transaction',
        'metadata': {}
    }
})
producer.flush()
"

# 4. Verify in Elasticsearch
curl "http://localhost:9200/transactions/_search?q=user_id:user123"
```

## 📚 References

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kafka Tutorials](https://kafka.apache.org/documentation/)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
