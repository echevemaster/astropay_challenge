# Load Test Data with Docker

This guide explains how to load the 1000 synthetic test data points using Docker.

## Available Options

### Option 1: Automatic Script (Recommended) ⭐

```bash
./load_test_data_docker.sh
```

This script:
- Verifies Docker is running
- Verifies necessary services are active
- Starts services if they're not running
- Executes the data generation script
- Shows query examples when finished

### Option 2: Docker Compose with Profile

```bash
# Make sure the API is running first
docker-compose up -d api

# Rebuild the image (if there are new dependencies)
docker-compose build load_test_data

# Run the data loading service
docker-compose --profile test-data run --rm load_test_data
```

### Option 3: Run Inside the API Container

```bash
# Make sure the API is running
docker-compose up -d api

# Run the script inside the container
docker-compose exec api python3 generate_test_data.py
```

### Option 4: Temporary Container

```bash
# Run a temporary container just to load data
docker-compose run --rm \
  -e API_URL=http://api:8000/api/v1 \
  -e DOCKER_CONTAINER=true \
  api \
  python3 generate_test_data.py
```

## Prerequisites

1. **Docker and Docker Compose installed**
2. **Infrastructure services running:**
   ```bash
   docker-compose up -d postgres redis elasticsearch kafka zookeeper
   ```
3. **API running:**
   ```bash
   docker-compose up -d api
   ```

## Recommended Complete Flow

```bash
# 1. Start all services
docker-compose up -d

# 2. Wait for everything to be ready (optional)
sleep 10

# 3. Run migrations (if not already run)
docker-compose --profile migrate run --rm migrations

# 4. Rebuild images if there are new dependencies
docker-compose build

# 5. Load test data
./load_test_data_docker.sh
```

## Verification

After loading data, you can verify with:

```bash
# View all transactions
curl "http://localhost:8000/api/v1/transactions?user_id=test_user_123&page_size=5"

# Count transactions (approximate)
curl "http://localhost:8000/api/v1/transactions?user_id=test_user_123" | jq '.total'

# Search by merchant
curl "http://localhost:8000/api/v1/transactions?user_id=test_user_123&search_query=Starbucks"
```

## Troubleshooting

### Error: "Could not connect to API"

**Problem:** The `api` service is not running or not ready.

**Solution:**
```bash
# Check service status
docker-compose ps

# Start the API
docker-compose up -d api

# View logs to diagnose
docker-compose logs api
```

### Error: "Connection refused"

**Problem:** The API is not ready to receive connections yet.

**Solution:** The script automatically waits up to 60 seconds. If the problem persists:
```bash
# Check health manually
curl http://localhost:8000/api/v1/health

# View API logs
docker-compose logs -f api
```

### Error: "Database connection failed"

**Problem:** PostgreSQL is not available.

**Solution:**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Restart if necessary
docker-compose restart postgres
```

### Data is not loading

**Problem:** There may be silent errors.

**Solution:**
```bash
# Run with visible logs
docker-compose --profile test-data run --rm load_test_data

# Or run inside the container to see errors
docker-compose exec api python3 generate_test_data.py
```

## Important Notes

- The script generates data for `user_id: test_user_123`
- Transactions are distributed over the last 90 days
- The process may take several minutes (depends on API speed)
- The script shows progress every 100 transactions
- If there are errors, the script continues and tries to load the rest

## Clean Test Data

### Option 1: Automatic Script (Recommended) ⭐

```bash
# Clean all data (PostgreSQL, Elasticsearch, Redis)
./clean_data_docker.sh
```

This script removes:
- All transactions from PostgreSQL
- All documents from Elasticsearch
- All cache keys from Redis

### Option 2: Clean and Reload in One Step

```bash
# Clean data and load new data automatically
./clean_and_reload_data.sh
```

This script:
1. Cleans all existing data
2. Loads 1000 new synthetic transactions

### Option 3: Docker Compose with Profile

```bash
# Only clean data
docker-compose --profile clean run --rm clean_data
```

### Option 4: Manual Cleanup

#### Clean PostgreSQL

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U astropay -d activity_feed

# Inside PostgreSQL, run:
DELETE FROM transactions;
```

Or from the command line:

```bash
docker-compose exec postgres psql -U astropay -d activity_feed -c "DELETE FROM transactions;"
```

#### Clean Elasticsearch

```bash
# Delete all documents from the index
curl -X POST "http://localhost:9200/transactions/_delete_by_query" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}}'
```

#### Clean Redis

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Inside Redis, run:
KEYS transactions:*
DEL transactions:*
```

Or from the command line:

```bash
docker-compose exec redis redis-cli --scan --pattern "transactions:*" | xargs docker-compose exec -T redis redis-cli DEL
```

### Clean Everything (PostgreSQL + Elasticsearch + Redis)

```bash
# Use the cleanup script
./clean_data_docker.sh
```
