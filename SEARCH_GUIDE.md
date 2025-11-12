# Free Text Search Guide

The API supports free text search that searches across multiple transaction fields, including merchant names, locations, peer information, and other metadata.

## How It Works

The search uses:
1. **Elasticsearch** (if available): Advanced full-text search with fuzzy matching
2. **PostgreSQL** (fallback): ILIKE search if Elasticsearch is not available

### Fields Searched

- **search_content**: Denormalized field containing:
  - Transaction type
  - Amount and currency
  - Status
  - Merchant name (for card payments)
  - Merchant category
  - Location
  - Peer name (for P2P transfers)
  - Peer email
  - Direction (sent/received)
  - And other relevant fields depending on transaction type

- **metadata**: All fields within the JSON metadata object

## Basic Usage

### Simple Example with JWT (Recommended)

```bash
# 1. Get token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}' | jq -r '.access_token')

# 2. Search for "Starbucks" (user_id comes from token, don't pass it as parameter)
curl "http://localhost:8000/api/v1/transactions?search_query=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

### Simple Example without JWT (Development only)

```bash
# Search for "Starbucks" in all user transactions
curl "http://localhost:8000/api/v1/transactions?user_id=user123&search_query=Starbucks"
```

### With Python (JWT)

```python
import requests

# Get token
token_response = requests.post(
    "http://localhost:8000/api/v1/auth/token",
    json={"user_id": "user123"}
)
token = token_response.json()["access_token"]

# Search transactions (without passing user_id)
url = "http://localhost:8000/api/v1/transactions"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "search_query": "Starbucks",
    "page": 1,
    "page_size": 20
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

### With Python (Without JWT - Development only)

```python
import requests

url = "http://localhost:8000/api/v1/transactions"
params = {
    "user_id": "user123",  # Required only without JWT
    "search_query": "Starbucks",
    "page": 1,
    "page_size": 20
}

response = requests.get(url, params=params)
print(response.json())
```

### With JavaScript

```javascript
const url = new URL('http://localhost:8000/api/v1/transactions');
url.searchParams.append('user_id', 'user123');
url.searchParams.append('search_query', 'Starbucks');

fetch(url)
  .then(response => response.json())
  .then(data => console.log(data));
```

## Search Examples

### 1. Search by Merchant Name (With JWT)

```bash
# With JWT - user_id comes from token
curl "http://localhost:8000/api/v1/transactions?search_query=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Search by Location

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?search_query=San%20Francisco" \
  -H "Authorization: Bearer $TOKEN"

# Without JWT (development)
curl "http://localhost:8000/api/v1/transactions?user_id=user123&search_query=San%20Francisco"
```

### 3. Search by Peer Name (P2P)

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?search_query=John%20Doe" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Search by Email

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?search_query=john@example.com" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Search by Category

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?search_query=Food" \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Combined Search with Filters

```bash
# With JWT - Search "Starbucks" only in completed transactions
curl "http://localhost:8000/api/v1/transactions?search_query=Starbucks&status=completed" \
  -H "Authorization: Bearer $TOKEN"

# With JWT - Search in card payments only
curl "http://localhost:8000/api/v1/transactions?search_query=Starbucks&product=Card" \
  -H "Authorization: Bearer $TOKEN"

# With JWT - Search with multiple filters
curl "http://localhost:8000/api/v1/transactions?search_query=Starbucks&product=Card&status=completed&currency=USD" \
  -H "Authorization: Bearer $TOKEN"
```

## Search Features

### With Elasticsearch (Recommended)

- **Fuzzy Matching**: Finds results even with small spelling errors
  - Example: "Starbuks" will find "Starbucks"
- **Multi-Field Search**: Searches simultaneously in `search_content` and `metadata`
- **Relevance**: Results are sorted by relevance
- **Partial Search**: Finds partial words

### With PostgreSQL (Fallback)

- **Case-Insensitive Search**: Doesn't distinguish uppercase/lowercase
- **Partial Search**: Uses `ILIKE` with wildcards
- **Search in search_content**: Searches in the denormalized field

## Search Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `user_id` | string (required) | User ID | `user123` |
| `search_query` | string (optional) | Text to search | `Starbucks` |
| `page` | integer | Page number | `1` |
| `page_size` | integer | Results per page (max 100) | `20` |

### Additional Filters (can be combined)

- `transaction_type`: card, p2p, crypto, etc.
- `product`: Card, P2P, Crypto, Earnings
- `status`: completed, pending, failed, cancelled
- `currency`: USD, EUR, etc.
- `start_date`: Start date (ISO format)
- `end_date`: End date (ISO format)
- `min_amount`: Minimum amount
- `max_amount`: Maximum amount

## Complete Examples

### Example 1: Simple Search

```bash
curl -X GET "http://localhost:8000/api/v1/transactions?user_id=user123&search_query=coffee" \
  -H "Accept: application/json"
```

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user123",
      "transaction_type": "card",
      "product": "Card",
      "status": "completed",
      "currency": "USD",
      "amount": 5.50,
      "metadata": {
        "merchant_name": "Starbucks",
        "merchant_category": "Food & Beverage",
        "location": "San Francisco, CA"
      },
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### Example 2: Search with Filters

```bash
curl -X GET "http://localhost:8000/api/v1/transactions?user_id=user123&search_query=John&product=P2P&status=completed" \
  -H "Accept: application/json"
```

### Example 3: Search with Pagination

```bash
curl -X GET "http://localhost:8000/api/v1/transactions?user_id=user123&search_query=Starbucks&page=2&page_size=10" \
  -H "Accept: application/json"
```

## Tips and Best Practices

1. **Use specific terms**: "Starbucks" is better than "coffee"
2. **Combine with filters**: Use additional filters to refine results
3. **Pagination**: For many results, use pagination
4. **Elasticsearch**: Make sure Elasticsearch is running for better experience
5. **Case-insensitive**: You don't need to worry about uppercase/lowercase

## Verify Search Status

To verify if Elasticsearch is available:

```bash
curl "http://localhost:8000/api/v1/health"
```

The response will include Elasticsearch status:
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "elasticsearch": "healthy",
  "kafka": "healthy"
}
```

## Troubleshooting

### No results found

1. Verify that transactions are indexed in Elasticsearch
2. Verify that `search_content` contains the searched text
3. Try with more general terms

### Slow search

1. Verify that Elasticsearch is running
2. Use additional filters to reduce the result set
3. Limit the `page_size`

### Elasticsearch not available

- Search automatically falls back to PostgreSQL
- Search will be more basic but will continue to work

## Technical Notes

- The `search_content` field is automatically generated when a transaction is created
- It is indexed in Elasticsearch when a transaction is created/updated
- Search is user-specific (always filters by `user_id`)
- Results are sorted by creation date (most recent first)
