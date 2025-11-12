# Date Filter Guide

The API allows filtering transactions by date range using the `start_date` and `end_date` parameters.

## Date Parameters

- **`start_date`**: Start date of the range (inclusive)
- **`end_date`**: End date of the range (inclusive)

Both parameters use **ISO 8601** format: `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS+00:00`

## Basic Examples

### 1. Complete Date Range

```bash
# With JWT (Recommended)
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"

# Without JWT (development)
curl "http://localhost:8000/api/v1/transactions?user_id=user123&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z"
```

### 2. Start Date Only

```bash
# Transactions from a date onwards
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. End Date Only

```bash
# Transactions up to a date
curl "http://localhost:8000/api/v1/transactions?end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Specific Day

```bash
# Transactions for a full day
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-15T00:00:00Z&end_date=2024-01-15T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

## Supported Date Formats

### Complete ISO 8601 Format (Recommended)

```bash
# With UTC timezone
start_date=2024-01-01T00:00:00Z
end_date=2024-01-31T23:59:59Z

# With explicit timezone
start_date=2024-01-01T00:00:00+00:00
end_date=2024-01-31T23:59:59+00:00
```

### Simplified Format (FastAPI converts automatically)

```bash
# Date only (assumes 00:00:00)
start_date=2024-01-01
end_date=2024-01-31
```

## Practical Examples

### Current Month Transactions

```bash
# Get current date and calculate start/end of month
CURRENT_MONTH_START=$(date -u +"%Y-%m-01T00:00:00Z")
CURRENT_MONTH_END=$(date -u +"%Y-%m-%dT23:59:59Z")

curl "http://localhost:8000/api/v1/transactions?start_date=${CURRENT_MONTH_START}&end_date=${CURRENT_MONTH_END}" \
  -H "Authorization: Bearer $TOKEN"
```

### Last Week Transactions

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-07T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

### Last Month Transactions

```bash
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

## Combine with Other Filters

### Date + Transaction Type

```bash
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&transaction_type=card" \
  -H "Authorization: Bearer $TOKEN"
```

### Date + Product

```bash
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&product=Card" \
  -H "Authorization: Bearer $TOKEN"
```

### Date + Status

```bash
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&status=completed" \
  -H "Authorization: Bearer $TOKEN"
```

### Date + Text Search

```bash
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&search_query=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

### Date + Multiple Filters

```bash
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&product=Card&status=completed&currency=USD&search_query=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

## Examples with Python

```python
import requests
from datetime import datetime, timedelta

# Get token
token_response = requests.post(
    "http://localhost:8000/api/v1/auth/token",
    json={"user_id": "user123"}
)
token = token_response.json()["access_token"]

# Dates
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 1, 31, 23, 59, 59)

# Search with date range
url = "http://localhost:8000/api/v1/transactions"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "start_date": start_date.isoformat() + "Z",
    "end_date": end_date.isoformat() + "Z",
    "page": 1,
    "page_size": 20
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

### Last 30 Days

```python
import requests
from datetime import datetime, timedelta

token = "your_token_here"
headers = {"Authorization": f"Bearer {token}"}

# Calculate dates
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=30)

params = {
    "start_date": start_date.isoformat() + "Z",
    "end_date": end_date.isoformat() + "Z"
}

response = requests.get(
    "http://localhost:8000/api/v1/transactions",
    headers=headers,
    params=params
)
print(response.json())
```

## Examples with JavaScript

```javascript
// Date range
const startDate = new Date('2024-01-01T00:00:00Z');
const endDate = new Date('2024-01-31T23:59:59Z');

const url = new URL('http://localhost:8000/api/v1/transactions');
url.searchParams.append('start_date', startDate.toISOString());
url.searchParams.append('end_date', endDate.toISOString());

fetch(url, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
  .then(response => response.json())
  .then(data => console.log(data));
```

### Last 7 Days

```javascript
const endDate = new Date();
const startDate = new Date();
startDate.setDate(startDate.getDate() - 7);

const url = new URL('http://localhost:8000/api/v1/transactions');
url.searchParams.append('start_date', startDate.toISOString());
url.searchParams.append('end_date', endDate.toISOString());

fetch(url, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
  .then(response => response.json())
  .then(data => console.log(data));
```

## Time Zones

Dates are interpreted in **UTC** by default. If you need to use another timezone:

```bash
# UTC (recommended)
start_date=2024-01-01T00:00:00Z

# With specific timezone
start_date=2024-01-01T00:00:00-05:00  # EST
start_date=2024-01-01T00:00:00+01:00  # CET
```

## Common Use Cases

### 1. Today's Transactions

```bash
TODAY_START=$(date -u +"%Y-%m-%dT00:00:00Z")
TODAY_END=$(date -u +"%Y-%m-%dT23:59:59Z")

curl "http://localhost:8000/api/v1/transactions?start_date=${TODAY_START}&end_date=${TODAY_END}" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. This Week's Transactions

```bash
# Monday of this week
WEEK_START=$(date -u -v-mon +"%Y-%m-%dT00:00:00Z" 2>/dev/null || date -u -d "last monday" +"%Y-%m-%dT00:00:00Z")
# Sunday of this week
WEEK_END=$(date -u +"%Y-%m-%dT23:59:59Z")

curl "http://localhost:8000/api/v1/transactions?start_date=${WEEK_START}&end_date=${WEEK_END}" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Year Transactions

```bash
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Recent Transactions (Last 24 hours)

```bash
# With JWT
YESTERDAY=$(date -u -v-1d +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d "1 day ago" +"%Y-%m-%dT%H:%M:%SZ")
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

curl "http://localhost:8000/api/v1/transactions?start_date=${YESTERDAY}&end_date=${NOW}" \
  -H "Authorization: Bearer $TOKEN"
```

## Important Notes

1. **Date Format**: Use ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`)
2. **Timezone**: Dates are interpreted in UTC if you don't specify timezone
3. **Inclusive**: Both `start_date` and `end_date` are inclusive
4. **Filtered Field**: Filtered by `created_at` (transaction creation date)
5. **Combination**: You can combine date filters with other filters and text search

## Complete Examples

### Complete Search: Date + Text + Filters

```bash
# With JWT
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}' | jq -r '.access_token')

curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&search_query=Starbucks&product=Card&status=completed&page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

### Without JWT (Development)

```bash
curl "http://localhost:8000/api/v1/transactions?user_id=user123&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&product=Card&status=completed"
```

## Troubleshooting

### Error: "Invalid date format"

**Problem:** The date format is not valid.

**Solution:** Use ISO 8601 format:
```
✅ Correct: 2024-01-01T00:00:00Z
❌ Incorrect: 2024/01/01
❌ Incorrect: 01-01-2024
```

### No transactions found in range

**Verify:**
1. That dates are in the correct format
2. That the range includes transaction dates
3. That you use UTC timezone or the correct one
4. That `start_date` is before `end_date`

### Dates in simplified format

FastAPI accepts dates without time, but they are interpreted as UTC midnight:
```bash
# This is equivalent to 2024-01-01T00:00:00Z
start_date=2024-01-01
```
