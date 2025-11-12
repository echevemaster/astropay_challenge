# Metadata Filters Guide

The API allows filtering transactions by specific fields within metadata using dedicated query parameters.

## Available Metadata Filters

### For P2P Transactions

#### `direction` - Transfer Direction

Filters P2P transfers by direction: `sent` (sent) or `received` (received).

**Examples:**

```bash
# With JWT - P2P transfers sent
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent" \
  -H "Authorization: Bearer $TOKEN"

# With JWT - P2P transfers received
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=received" \
  -H "Authorization: Bearer $TOKEN"

# Without JWT
curl "http://localhost:8000/api/v1/transactions?user_id=user123&product=P2P&direction=sent"
```

#### `peer_name` - Peer Name

Filters by peer name in P2P transfers.

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&peer_name=John%20Doe" \
  -H "Authorization: Bearer $TOKEN"
```

### For Card Transactions

#### `merchant_name` - Merchant Name

Filters card payments by merchant name.

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&merchant_name=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

## Complete Examples

### P2P Transfer Sent

```bash
# 1. Get token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}' | jq -r '.access_token')

# 2. Search P2P transfers sent
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent" \
  -H "Authorization: Bearer $TOKEN"

# 3. With pagination
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent&page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

# 4. With additional filters
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent&status=completed&currency=USD" \
  -H "Authorization: Bearer $TOKEN"

# 5. With date
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

### P2P Transfer Received

```bash
# With JWT
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=received" \
  -H "Authorization: Bearer $TOKEN"
```

### Useful Combinations

```bash
# P2P sent completed in USD
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent&status=completed&currency=USD" \
  -H "Authorization: Bearer $TOKEN"

# P2P sent to a specific peer
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent&peer_name=John%20Doe" \
  -H "Authorization: Bearer $TOKEN"

# P2P sent in a date range
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

## With Python

```python
import requests

# Get token
token_response = requests.post(
    "http://localhost:8000/api/v1/auth/token",
    json={"user_id": "user123"}
)
token = token_response.json()["access_token"]

# Search P2P transfers sent
url = "http://localhost:8000/api/v1/transactions"
headers = {"Authorization": f"Bearer {token}"}
params = {
    "transaction_type": "p2p",
    "direction": "sent",
    "page": 1,
    "page_size": 20
}

response = requests.get(url, headers=headers, params=params)
print(response.json())
```

## With JavaScript

```javascript
const url = new URL('http://localhost:8000/api/v1/transactions');
url.searchParams.append('transaction_type', 'p2p');
url.searchParams.append('direction', 'sent');

fetch(url, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
  .then(response => response.json())
  .then(data => console.log(data));
```

## Valid Values for `direction`

- `sent`: Transfers sent by the user
- `received`: Transfers received by the user

## Notes

1. **Combination with other filters**: You can combine `direction` with other filters like `status`, `currency`, `start_date`, etc.
2. **Only for P2P**: The `direction` filter only applies to transactions of type `p2p` or product `P2P`
3. **Case-sensitive**: Values are case-sensitive. Use `sent` or `received` in lowercase.

## Response Examples

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user123",
      "transaction_type": "p2p",
      "product": "P2P",
      "status": "completed",
      "currency": "USD",
      "amount": 50.00,
      "metadata": {
        "peer_name": "John Doe",
        "peer_email": "john@example.com",
        "direction": "sent"
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
