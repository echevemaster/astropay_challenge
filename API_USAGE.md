# API Usage Guide

## Available Endpoints

### 1. GET `/api/v1/transactions` - Get Transactions

**Authentication:**
- **With JWT (Recommended)**: The `user_id` is automatically extracted from the JWT token in the `Authorization: Bearer <token>` header. You don't need to pass `user_id` as a parameter.
- **Without JWT (Development/testing only)**: You must pass `user_id` as a query parameter.

**Optional parameters:**
- `transaction_type`: card, p2p, crypto, top_up, withdrawal, bill_payment, earnings
- `product`: Card, P2P, Crypto, Earnings
- `status`: completed, pending, failed, cancelled
- `currency`: USD, EUR, etc.
- `start_date`: Start date (ISO format: 2024-01-01T00:00:00Z)
- `end_date`: End date (ISO format: 2024-01-31T23:59:59Z)
- `min_amount`: Minimum amount
- `max_amount`: Maximum amount
- `search_query`: Free text search
- `direction`: P2P direction - 'sent' or 'received' (only for P2P)
- `merchant_name`: Merchant name (only for Card)
- `card_last_four`: Last 4 digits of the card (only for Card, e.g., '5678')
- `peer_name`: Peer name (only for P2P)
- `page`: Page number (default: 1)
- `page_size`: Page size (default: 20, max: 100)

**Examples with JWT (Recommended):**

```bash
# 1. Get JWT token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}' | jq -r '.access_token')

# 2. Get all transactions (user_id comes from token)
curl "http://localhost:8000/api/v1/transactions" \
  -H "Authorization: Bearer $TOKEN"

# 3. Date filter - full range (without passing user_id)
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"

# 4. Start date only (from a date onwards)
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN"

# 5. End date only (up to a date)
curl "http://localhost:8000/api/v1/transactions?end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"

# 6. Date + text search
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&search_query=Starbucks" \
  -H "Authorization: Bearer $TOKEN"

# 7. Date + other filters
curl "http://localhost:8000/api/v1/transactions?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&product=Card&status=completed" \
  -H "Authorization: Bearer $TOKEN"

# 8. P2P transfers sent
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent" \
  -H "Authorization: Bearer $TOKEN"

# 9. P2P transfers received
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=received" \
  -H "Authorization: Bearer $TOKEN"

# 10. P2P sent with additional filters
curl "http://localhost:8000/api/v1/transactions?transaction_type=p2p&direction=sent&status=completed&currency=USD" \
  -H "Authorization: Bearer $TOKEN"

# 11. Card payments
curl "http://localhost:8000/api/v1/transactions?transaction_type=card" \
  -H "Authorization: Bearer $TOKEN"

# 12. Completed card payments
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&status=completed" \
  -H "Authorization: Bearer $TOKEN"

# 13. Card payments by merchant
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&merchant_name=Starbucks" \
  -H "Authorization: Bearer $TOKEN"

# 14. Card payments with text search
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&search_query=Starbucks" \
  -H "Authorization: Bearer $TOKEN"

# 15. Card payments by last 4 digits of card
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&card_last_four=5678" \
  -H "Authorization: Bearer $TOKEN"

# 16. Card payments by card and merchant
curl "http://localhost:8000/api/v1/transactions?transaction_type=card&card_last_four=5678&merchant_name=Starbucks" \
  -H "Authorization: Bearer $TOKEN"
```

**Examples without JWT (Development/testing only):**

```bash
# Date filter - full range
curl "http://localhost:8000/api/v1/transactions?user_id=user123&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z"

# Start date only
curl "http://localhost:8000/api/v1/transactions?user_id=user123&start_date=2024-01-01T00:00:00Z"

# End date only
curl "http://localhost:8000/api/v1/transactions?user_id=user123&end_date=2024-01-31T23:59:59Z"

# Date + other filters
curl "http://localhost:8000/api/v1/transactions?user_id=user123&start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z&product=Card&status=completed"
```

> **📅 For more details on date search, see [DATE_FILTER_GUIDE.md](DATE_FILTER_GUIDE.md)**

> **📖 For more details on free text search, see [SEARCH_GUIDE.md](SEARCH_GUIDE.md)**

> **🔍 For more details on metadata filters (direction, merchant_name, peer_name), see [METADATA_FILTERS_GUIDE.md](METADATA_FILTERS_GUIDE.md)**

> **💳 For more details on card payment search, see [CARD_PAYMENT_GUIDE.md](CARD_PAYMENT_GUIDE.md)**

**⚠️ IMPORTANT:** 
- **With JWT**: The `user_id` is extracted from the token automatically. DO NOT pass it as a query parameter.
- **Without JWT**: The `user_id` parameter is **REQUIRED** as a query parameter (development/testing only).

### 2. POST `/api/v1/transactions` - Create Transaction

**Request Body:**
```json
{
  "user_id": "user123",
  "transaction_type": "card",
  "product": "Card",
  "status": "completed",
  "currency": "USD",
  "amount": 150.00,
  "metadata": {
    "merchant_name": "Starbucks",
    "merchant_category": "Food & Beverage",
    "card_last_four": "5678",
    "location": "San Francisco, CA"
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/transactions" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "transaction_type": "card",
    "product": "Card",
    "status": "completed",
    "currency": "USD",
    "amount": 150.00,
    "metadata": {
      "merchant_name": "Starbucks",
      "merchant_category": "Food & Beverage"
    }
  }'
```

### 3. GET `/api/v1/transactions/{transaction_id}` - Get Transaction by ID

**Example:**
```bash
curl "http://localhost:8000/api/v1/transactions/550e8400-e29b-41d4-a716-446655440000"
```

### 4. GET `/api/v1/health` - Health Check

**Example:**
```bash
curl "http://localhost:8000/api/v1/health"
```

## Common Errors

### Error: "Field required" for user_id

**Problem:** You're not including the `user_id` parameter in the query string.

**Solution:** Make sure to include `user_id` in the URL:
```
❌ Incorrect: GET /api/v1/transactions
✅ Correct: GET /api/v1/transactions?user_id=user123
```

### Error: "user_id is required and cannot be empty"

**Problem:** The `user_id` parameter is empty or only contains spaces.

**Solution:** Provide a valid `user_id` (not empty).

## Examples with Different Tools

### With curl
```bash
curl "http://localhost:8000/api/v1/transactions?user_id=user123&page=1&page_size=20"
```

### With Python requests
```python
import requests

url = "http://localhost:8000/api/v1/transactions"
params = {
    "user_id": "user123",
    "page": 1,
    "page_size": 20
}
response = requests.get(url, params=params)
print(response.json())
```

### With JavaScript fetch
```javascript
const url = new URL('http://localhost:8000/api/v1/transactions');
url.searchParams.append('user_id', 'user123');
url.searchParams.append('page', '1');
url.searchParams.append('page_size', '20');

fetch(url)
  .then(response => response.json())
  .then(data => console.log(data));
```

### With Postman
1. Method: GET
2. URL: `http://localhost:8000/api/v1/transactions`
3. In the "Params" tab, add:
   - Key: `user_id`, Value: `user123`
   - Key: `page`, Value: `1`
   - Key: `page_size`, Value: `20`

## Interactive Documentation

Once the API is running, you can access the interactive documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to test the API directly from the browser.
