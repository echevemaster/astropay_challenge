# JWT Authentication

The API now supports JWT authentication to extract `user_id` from the token instead of requiring it as a parameter. This improves security by ensuring users can only access their own transactions.

## Features

- ✅ **JWT Token Authentication**: Extracts `user_id` from JWT token
- ✅ **Security**: Users can only access their own transactions
- ✅ **Hybrid Mode**: Works with or without authentication (for development/testing)
- ✅ **Automatic Validation**: Validates that authenticated users only access their data

## Usage

### 1. Generate a JWT Token

```bash
# Generate token for a user
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 2. Use the Token in Requests

#### Get Transactions (with JWT)

```bash
# With JWT token - you don't need to pass user_id
curl "http://localhost:8000/api/v1/transactions" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Create Transaction (with JWT)

```bash
# The user_id from the token overrides the one in the body
curl -X POST "http://localhost:8000/api/v1/transactions" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_type": "card",
    "product": "Card",
    "status": "completed",
    "currency": "USD",
    "amount": 100.00,
    "metadata": {
      "merchant_name": "Starbucks"
    }
  }'
```

### 3. Mode Without Authentication (Development)

If you don't provide a token, you can still use `user_id` as a parameter:

```bash
# Without token - use user_id as parameter
curl "http://localhost:8000/api/v1/transactions?user_id=user123"
```

## Security

### Implemented Protections

1. **User Authorization**: If you're authenticated, you can only access your own transactions
2. **Token Validation**: Tokens are validated before processing requests
3. **Cross-Access Prevention**: If you try to access another user's data, you'll receive a 403 error

### Protection Example

```bash
# User A gets token
TOKEN_A=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_a"}' | jq -r '.access_token')

# User A tries to access user B's data (will be blocked)
curl "http://localhost:8000/api/v1/transactions?user_id=user_b" \
  -H "Authorization: Bearer $TOKEN_A"
# Response: 403 Forbidden - "You can only access your own transactions"
```

## Configuration

### Environment Variables

```bash
# .env
SECRET_KEY=your-super-secret-key-change-in-production
JWT_EXPIRE_MINUTES=30
REQUIRE_AUTH=false  # Set to true to require JWT for all endpoints
```

### Code Configuration

In `app/config.py`:
- `secret_key`: Secret key to sign tokens
- `jwt_expire_minutes`: Token expiration time (default: 30 minutes)
- `require_auth`: If `True`, all endpoints require authentication

## Authentication Endpoints

### POST `/api/v1/auth/token`

Generates a JWT token for a user.

**Request:**
```json
{
  "user_id": "user123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### GET `/api/v1/auth/me`

Gets information about the authenticated user.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "user123"
}
```

## Complete Example Flow

```bash
# 1. Generate token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user_123"}' | jq -r '.access_token')

# 2. Get transactions (without passing user_id)
curl "http://localhost:8000/api/v1/transactions" \
  -H "Authorization: Bearer $TOKEN"

# 3. Create transaction (user_id comes from token)
curl -X POST "http://localhost:8000/api/v1/transactions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_type": "card",
    "product": "Card",
    "status": "completed",
    "currency": "USD",
    "amount": 50.00,
    "metadata": {
      "merchant_name": "Starbucks"
    }
  }'
```

## Production Notes

⚠️ **Important for Production:**

1. **Change SECRET_KEY**: Use a strong secret key and store it in environment variables
2. **Validate Credentials**: The `/auth/token` endpoint currently accepts any `user_id`. In production, validate real credentials
3. **HTTPS**: Always use HTTPS in production to protect tokens
4. **Refresh Tokens**: Consider implementing refresh tokens for better UX
5. **Rate Limiting**: Implement rate limiting on the authentication endpoint
6. **Token Revocation**: Consider implementing a token revocation system

## Migration from Previous System

The system is **backward compatible**. If you don't provide a JWT token, you can still use `user_id` as a query parameter. This facilitates gradual migration.

To force authentication on all endpoints, configure:
```python
REQUIRE_AUTH=true
```
