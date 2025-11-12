# Configure Elasticsearch as Primary Source

This guide explains how to activate Elasticsearch as the primary data source instead of PostgreSQL.

## 🚀 Quick Activation

### Option 1: Environment Variable (Recommended)

```bash
# In docker-compose.yml or .env
USE_ELASTICSEARCH_AS_PRIMARY=true
```

Or in `docker-compose.yml`:

```yaml
api:
  environment:
    USE_ELASTICSEARCH_AS_PRIMARY: "true"
```

### Option 2: .env File

Create a `.env` file in the project root:

```bash
USE_ELASTICSEARCH_AS_PRIMARY=true
```

## 📋 Complete Steps

### 1. Make sure Elasticsearch is running

```bash
docker-compose up -d elasticsearch
```

### 2. Verify Elasticsearch is available

```bash
curl http://localhost:9200/_cluster/health
```

### 3. Activate Elasticsearch as primary source

**Option A: Environment variable in docker-compose.yml**

```yaml
api:
  environment:
    USE_ELASTICSEARCH_AS_PRIMARY: "true"
    # ... other variables
```

**Option B: .env file**

```bash
echo "USE_ELASTICSEARCH_AS_PRIMARY=true" >> .env
```

### 4. Restart the API service

```bash
docker-compose restart api
```

Or if it's not running:

```bash
docker-compose up -d api
```

## ✅ Verification

### Verify it's using Elasticsearch

Check logs:

```bash
docker-compose logs api | grep -i elasticsearch
```

You should see messages like:
- `"Using Elasticsearch for search"`
- `"Elasticsearch search successful (returning documents)"`

### Test a query

```bash
# Without search_query - should use Elasticsearch directly
curl "http://localhost:8000/api/v1/transactions?user_id=test_user_123"

# With search_query - also uses Elasticsearch
curl "http://localhost:8000/api/v1/transactions?user_id=test_user_123&search_query=Starbucks"
```

## 🔄 Return to PostgreSQL

If you want to use PostgreSQL as primary source again:

```bash
# Disable in docker-compose.yml
USE_ELASTICSEARCH_AS_PRIMARY: "false"

# Or remove the variable
# And restart
docker-compose restart api
```

## ⚠️ Important

1. **Data in Elasticsearch**: Make sure data is indexed in Elasticsearch before activating this option.

2. **Synchronization**: If you use both systems, keep data synchronized.

3. **Fallback**: If Elasticsearch is not available and `use_elasticsearch_as_primary=True`, the API will return an error. Consider implementing fallback to PostgreSQL.

## 📊 Behavior

### With `USE_ELASTICSEARCH_AS_PRIMARY=true`:

- ✅ All queries go to Elasticsearch
- ✅ PostgreSQL is not queried for reading data
- ✅ Metadata filters work in Elasticsearch
- ✅ Native Elasticsearch full-text searches
- ⚠️ Requires data to be in Elasticsearch

### With `USE_ELASTICSEARCH_AS_PRIMARY=false` (default):

- ✅ PostgreSQL is the primary source
- ✅ Elasticsearch is only used for searches with `search_query`
- ✅ Data always available in PostgreSQL
- ✅ Automatic fallback if Elasticsearch fails

## 🧪 Testing

To test that it works:

```bash
# 1. Activate Elasticsearch mode
export USE_ELASTICSEARCH_AS_PRIMARY=true

# 2. Restart API
docker-compose restart api

# 3. Make a query
curl "http://localhost:8000/api/v1/transactions?user_id=test_user_123&currency=USD"

# 4. Check logs
docker-compose logs api | tail -20
```

You should see in the logs that it's querying Elasticsearch directly without going through PostgreSQL.
