# Message Consumer - Complete Guide

## Description

The **Message Consumer** is an enhanced worker that consumes messages from Kafka and processes them to index transactions in Elasticsearch. It includes advanced production features:

- ✅ **Idempotency**: Prevents processing duplicate messages
- ✅ **Batch Processing**: Processes messages in batches for better performance
- ✅ **Dead Letter Queue (DLQ)**: Handles failed messages
- ✅ **Data Enrichment**: Uses strategies to enrich transactions
- ✅ **Document Versioning**: Tracks document versions in Elasticsearch
- ✅ **Audit/Backup DB**: Writes to PostgreSQL for auditing (optional)

## Architecture

```
Microservices → Kafka → Consumer → Elasticsearch (primary)
                                  ↓
                            PostgreSQL (audit/backup)
```

## Detailed Features

### 1. Idempotency

The consumer implements idempotency at two levels:

- **In-memory**: Fast set for recent messages
- **Redis**: Distributed persistence for idempotency between instances

Each message generates a unique ID based on:
- `transaction_id`
- `event_type`
- `timestamp`

Processed messages are marked with 24-hour TTL.

### 2. Batch Processing

Processes messages in batches to improve performance:

- **Batch size**: Configurable (default: 10)
- **Batch timeout**: Configurable (default: 5.0 seconds)
- Processes when:
  - Buffer reaches maximum size
  - Or timeout is reached

### 3. Dead Letter Queue (DLQ)

Messages that fail after 3 retries are sent to DLQ:

- **Topic**: `transactions.dlq`
- **Consumer Group**: `transaction_indexer`

Messages in DLQ can be inspected and reprocessed manually.

### 4. Data Enrichment

Uses Strategy pattern to enrich transactions by type:

- **Card Payments**: Card metadata enrichment
- **P2P Transfers**: Peer metadata enrichment
- **Crypto**: Cryptocurrency metadata enrichment
- **Search Content**: Automatic construction of searchable content

### 5. Document Versioning

Each document in Elasticsearch includes:

- `_version`: Incremental version number
- `_updated_at`: Last update timestamp
- `_enriched`: Flag indicating if it was enriched
- `_enriched_at`: Enrichment timestamp

### 6. Audit/Backup DB

Optionally writes to PostgreSQL for auditing:

- **Create**: Inserts new transaction
- **Update**: Updates existing transaction
- **Delete**: Deletes transaction

DB writing is **non-blocking** and does not affect main processing.

## Configuration

### Environment Variables

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9093
KAFKA_TRANSACTIONS_TOPIC=transactions
KAFKA_CONSUMER_GROUP=transaction_indexer

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200

# Redis (for idempotency)
REDIS_URL=redis://redis:6379/0

# PostgreSQL (for auditing)
DATABASE_URL=postgresql://astropay:astropay@postgres:5432/activity_feed

# Consumer Configuration
CONSUMER_BATCH_SIZE=10              # Batch size
CONSUMER_BATCH_TIMEOUT=5.0          # Batch timeout (seconds)
CONSUMER_ENABLE_AUDIT_DB=true        # Enable DB writing
```

### Docker Compose

The consumer is configured in `docker-compose.yml`:

```yaml
consumer:
  build:
    context: .
    dockerfile: Dockerfile
  command: python3 consumer_worker.py
  environment:
    CONSUMER_BATCH_SIZE: "10"
    CONSUMER_BATCH_TIMEOUT: "5.0"
    CONSUMER_ENABLE_AUDIT_DB: "true"
  depends_on:
    - postgres
    - redis
    - elasticsearch
    - kafka
    - zookeeper
  restart: unless-stopped
```

## Usage

### Start the Consumer

#### Locally

```bash
python consumer_worker.py
```

#### In Docker

```bash
# Start all services including consumer
docker-compose up -d

# View consumer logs
docker-compose logs -f consumer
```

### Publish Synthetic Data

To simulate microservice events, use the publishing script:

#### Locally

```bash
# Publish 1000 transactions
python publish_test_data_to_kafka.py --count 1000

# Publish with custom options
python publish_test_data_to_kafka.py \
  --count 500 \
  --user-id "user_456" \
  --update-ratio 0.2
```

#### In Docker

```bash
# Publish synthetic data
docker-compose run --rm --profile publish-data publish_test_data

# Or with custom options
docker-compose run --rm publish_test_data \
  python publish_test_data_to_kafka.py --count 2000 --user-id "user_789"
```

### Publishing Script Options

```bash
python publish_test_data_to_kafka.py --help

Options:
  --count N              Number of transactions (default: 1000)
  --user-id USER_ID      User ID for transactions (default: test_user_123)
  --kafka-servers SERVERS  Kafka bootstrap servers (default: from env)
  --update-ratio RATIO   Ratio of updates vs creates (default: 0.1)
```

## Message Format

### Message Structure

```json
{
  "event_type": "transaction.created",
  "transaction": {
    "id": "uuid",
    "user_id": "user_123",
    "transaction_type": "card",
    "product": "Card",
    "status": "completed",
    "currency": "USD",
    "amount": 100.50,
    "created_at": "2024-01-01T12:00:00Z",
    "metadata": {
      "merchant_name": "Starbucks",
      "card_last_four": "1234"
    }
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "source": "synthetic_data_generator"
}
```

### Event Types

- `transaction.created`: New transaction created
- `transaction.updated`: Transaction updated
- `transaction.deleted`: Transaction deleted

### Partitioning

Messages are partitioned by `user_id` to guarantee order within each user:

- All messages from the same `user_id` go to the same partition
- This ensures processing order for transactions from the same user

## Monitoring

### Logs

The consumer generates structured JSON logs:

```json
{
  "event": "Processing transaction message",
  "event_type": "transaction.created",
  "transaction_id": "uuid",
  "message_id": "hash",
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "info"
}
```

### Key Metrics

- Messages processed per second
- Processed batch sizes
- Failed messages (sent to DLQ)
- Processing time per batch

### Dead Letter Queue

Inspect messages in DLQ:

```bash
# View messages in DLQ topic
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic transactions.dlq \
  --from-beginning
```

## Troubleshooting

### Consumer doesn't start

1. Verify Kafka is running:
   ```bash
   docker-compose ps kafka zookeeper
   ```

2. Check logs:
   ```bash
   docker-compose logs consumer
   ```

### Messages not processing

1. Verify Kafka connection:
   ```bash
   docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
   ```

2. Verify topics:
   ```bash
   docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
   ```

3. Verify consumer group:
   ```bash
   docker-compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group transaction_indexer --describe
   ```

### Messages in DLQ

1. Inspect messages:
   ```bash
   docker-compose exec kafka kafka-console-consumer \
     --bootstrap-server localhost:9092 \
     --topic transactions.dlq \
     --from-beginning
   ```

2. Reprocess manually:
   - Resend messages from DLQ topic
   - Or fix the issue and resend to main topic

### Elasticsearch not indexing

1. Verify connection:
   ```bash
   curl http://localhost:9200/_cluster/health
   ```

2. Check consumer logs:
   ```bash
   docker-compose logs consumer | grep -i elasticsearch
   ```

### Audit DB not writing

1. Verify PostgreSQL connection:
   ```bash
   docker-compose exec postgres psql -U astropay -d activity_feed -c "SELECT COUNT(*) FROM transactions;"
   ```

2. Verify environment variable:
   ```bash
   docker-compose exec consumer env | grep CONSUMER_ENABLE_AUDIT_DB
   ```

## Best Practices

1. **Scalability**: Run multiple consumer instances to process more messages
2. **Monitoring**: Monitor logs and metrics regularly
3. **DLQ**: Review messages in DLQ periodically
4. **Idempotency**: Ensure messages have unique IDs
5. **Batch Size**: Adjust based on load (larger = more performance, more latency)
6. **Auditing**: Maintain audit DB for compliance and debugging

## Complete Example

```bash
# 1. Start services
docker-compose up -d

# 2. Wait for everything to be ready
docker-compose ps

# 3. Publish synthetic data
docker-compose run --rm --profile publish-data publish_test_data

# 4. View consumer logs processing
docker-compose logs -f consumer

# 5. Verify in Elasticsearch
curl "http://localhost:9200/transactions/_search?q=user_id:test_user_123&size=10"

# 6. Verify in audit DB
docker-compose exec postgres psql -U astropay -d activity_feed -c "SELECT COUNT(*) FROM transactions;"
```

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Message Consumer Code](../app/services/message_consumer.py)
- [Consumer Worker](../consumer_worker.py)
- [Publish Script](../publish_test_data_to_kafka.py)
