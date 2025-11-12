# Card Payment Search Guide

The API allows searching and filtering card payment transactions in multiple ways.

## Basic Filters for Card Payments

### By Transaction Type

Use `transaction_type=card` to filter all transactions of type "card":

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?transaction_type=card" \
  -H "Authorization: Bearer $TOKEN"

# Without JWT
curl "http://localhost:8000/api/v1/transactions?user_id=user123&transaction_type=card"
```

### By Product

Use `product=Card` to filter by the Card product:

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?product=Card" \
  -H "Authorization: Bearer $TOKEN"
```

### Combine Both

```bash
# With JWT - More specific
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&product=Card" \
  -H "Authorization: Bearer $TOKEN"
```

## Complete Examples

### 1. Get JWT Token

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}' | jq -r '.access_token')
```

### 2. All Card Transactions

```bash
curl "http://localhost:8000/api/v1/transactions?transaction_type=card" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Completed Card Payments

```bash
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&status=completed" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Card Payments by Merchant

```bash
# Search payments at Starbucks
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&merchant_name=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

### 4.1. Card Payments by Last 4 Digits

```bash
# Search payments with a specific card (last 4 digits)
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&card_last_four=5678" \
  -H "Authorization: Bearer $TOKEN"

# Combine with other filters
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&card_last_four=5678&status=completed" \
  -H "Authorization: Bearer $TOKEN"

# By card and merchant
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&card_last_four=5678&merchant_name=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Card Payments by Currency

```bash
# Payments in USD
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&currency=USD" \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Card Payments in a Date Range

```bash
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

### 7. Card Payments with Text Search

```bash
# Search by free text (searches in merchant_name, location, etc.)
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&search_query=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

### 8. Complete Combination

```bash
# Card payments completed in USD at Starbucks during January 2024
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&status=completed&currency=USD&merchant_name=Starbucks&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

## Available Filters for Card Payments

| Parameter | Description | Example |
|-----------|-------------|---------|
| `transaction_type=card` | Filter by transaction type | `card` |
| `product=Card` | Filter by product | `Card` |
| `status` | Transaction status | `completed`, `pending`, `failed`, `cancelled` |
| `currency` | Currency | `USD`, `EUR`, etc. |
| `merchant_name` | Merchant name | `Starbucks`, `Amazon`, etc. |
| `card_last_four` | Last 4 digits of card | `5678`, `1234`, etc. |
| `start_date` | Start date | `2024-01-01T00:00:00Z` |
| `end_date` | End date | `2024-01-31T23:59:59Z` |
| `min_amount` | Minimum amount | `10.00` |
| `max_amount` | Maximum amount | `1000.00` |
| `search_query` | Free text search | `Starbucks`, `San Francisco`, etc. |

## Examples with Python

```python
import requests

# Get token
token_response = requests.post(
    "http://localhost:8000/api/v1/auth/token",
    json={"user_id": "user123"}
)
token = token_response.json()["access_token"]

# Search card payments
url = "http://localhost:8000/api/v1/transactions"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "transaction_type": "card",
    "status": "completed",
    "page": 1,
    "page_size": 20
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

### Card Payments by Merchant

```python
params = {
    "transaction_type": "card",
    "merchant_name": "Starbucks",
    "status": "completed"
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

### Card Payments by Last 4 Digits

```python
params = {
    "transaction_type": "card",
    "card_last_four": "5678",
    "status": "completed"
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

### Card Payments in a Date Range

```python
from datetime import datetime

params = {
    "transaction_type": "card",
    "start_date": datetime(2024, 1, 1).isoformat() + "Z",
    "end_date": datetime(2024, 1, 31, 23, 59, 59).isoformat() + "Z"
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

## Examples with JavaScript

```javascript
// Search card payments
const url = new URL('http://localhost:8000/api/v1/transactions');
url.searchParams.append('transaction_type', 'card');
url.searchParams.append('status', 'completed');

fetch(url, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
  .then(response => response.json())
  .then(data => console.log(data));
```

### Card Payments by Merchant

```javascript
const url = new URL('http://localhost:8000/api/v1/transactions');
url.searchParams.append('transaction_type', 'card');
url.searchParams.append('merchant_name', 'Starbucks');

fetch(url, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
  .then(response => response.json())
  .then(data => console.log(data));
```

## Common Use Cases

### 1. View All Card Payments for the Month

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}' | jq -r '.access_token')

curl "http://localhost:8000/api/v1/transactions?transaction_type=card&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Search Payments at a Specific Merchant

```bash
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&merchant_name=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

### 2.1. Search Payments by Last 4 Digits

```bash
# All payments with a specific card
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&card_last_four=5678" \
  -H "Authorization: Bearer $TOKEN"

# Completed payments with a specific card
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&card_last_four=5678&status=completed" \
  -H "Authorization: Bearer $TOKEN"

# Payments with a card at a specific merchant
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&card_last_four=5678&merchant_name=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Completed Payments in USD

```bash
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&status=completed&currency=USD" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Pending Payments

```bash
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&status=pending" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Failed Payments

```bash
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&status=failed" \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Search by Location

```bash
# Search payments at a specific location using text search
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&search_query=San%20Francisco" \
  -H "Authorization: Bearer $TOKEN"
```

### 7. Payments by Amount Range

```bash
# Payments between $10 and $100
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&min_amount=10&max_amount=100" \
  -H "Authorization: Bearer $TOKEN"
```

## Response Structure

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
      "amount": 15.50,
      "metadata": {
        "merchant_name": "Starbucks",
        "merchant_category": "Food & Beverage",
        "card_last_four": "5678",
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

## Important Notes

1. **`transaction_type=card` vs `product=Card`**: 
   - `transaction_type=card` filters by transaction type
   - `product=Card` filters by product
   - You can use both to be more specific

2. **Text Search**: The `search_query` parameter searches in:
   - `merchant_name`
   - `merchant_category`
   - `location`
   - And other text fields in metadata

3. **Merchant Filter**: Use `merchant_name` to search payments at a specific merchant. It is case-sensitive.

4. **Filter Combination**: You can combine multiple filters to get more specific results.

## Troubleshooting

### No card payments found

**Verify:**
1. That you use `transaction_type=card` (lowercase)
2. That the user has card type transactions
3. That there are no other filters excluding results

### Merchant name search doesn't work

**Verify:**
1. That the merchant name matches exactly (case-sensitive)
2. That you use the full name as stored
3. Consider using `search_query` instead of `merchant_name` for more flexible searches
