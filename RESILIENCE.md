# Resilience and High Traffic Preparation

This document describes all the improvements implemented to strengthen the API and prepare it to handle high traffic.

## 🛡️ Implemented Features

### 1. Rate Limiting

**Implementation**: `app/middleware/rate_limit.py`

- **Algorithm**: Token Bucket using Redis
- **Default limits**: 100 requests/minute per IP
- **Per-endpoint limits**:
  - `/api/v1/transactions`: 200 req/min
  - `/api/v1/auth/token`: 10 req/min (login)
  - `/api/v1/health`: 1000 req/min
- **Tracking**: By IP or by user (if authenticated)
- **Response headers**:
  - `X-RateLimit-Limit`: Total limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp
  - `Retry-After`: Seconds until more requests can be made

**Configuration**:
```python
# app/config.py
rate_limit_enabled: bool = True
rate_limit_default: int = 100
rate_limit_window: int = 60  # seconds
```

### 2. Circuit Breaker

**Implementation**: `app/middleware/circuit_breaker.py`

Protects against cascading failures of external services:

- **States**:
  - `CLOSED`: Normal operation
  - `OPEN`: Service failing, rejects requests
  - `HALF_OPEN`: Testing if service recovered

- **Configuration**:
  - `failure_threshold`: 5 consecutive failures open the circuit
  - `timeout`: 60 seconds before attempting reset
  - `half_open_success_threshold`: 2 successes to close the circuit

- **Protected services**:
  - Elasticsearch
  - Redis (cache)
  - Kafka (events)

**Behavior**:
- When a service fails repeatedly, the circuit breaker opens
- Requests are rejected immediately without attempting to call the service
- After timeout, enters `HALF_OPEN` state to test
- If successful, returns to `CLOSED`

### 3. Request ID Tracking

**Implementation**: `app/middleware/request_id.py`

- Generates a unique ID for each request
- Included in response headers: `X-Request-ID`
- Added to logging context for traceability
- Allows tracking requests throughout the entire application

**Usage**:
```bash
# Client can send its own request ID
curl -H "X-Request-ID: my-custom-id" http://localhost:8000/api/v1/transactions

# Or the API will generate one automatically
```

### 4. Enhanced Logging

**Implementation**: `app/middleware/logging.py`

- Structured logging of all requests
- Includes:
  - HTTP method
  - Path and query params
  - Client IP
  - User-Agent
  - Request ID
  - User ID (if authenticated)
  - Processing time
  - Response status code

- **Response headers**:
  - `X-Process-Time`: Processing time in seconds

### 5. Timeout Middleware

**Implementation**: `app/middleware/timeout.py`

- Configurable timeouts per endpoint:
  - `/api/v1/transactions`: 10 seconds
  - `/api/v1/auth/token`: 5 seconds
  - `/api/v1/health`: 2 seconds
  - Default: 30 seconds

- Returns `504 Gateway Timeout` if timeout is exceeded

### 6. Prometheus Metrics

**Implementation**: `app/middleware/metrics.py` and `app/api/routes/metrics.py`

**Endpoint**: `GET /api/v1/metrics`

**Available metrics**:

1. **HTTP Metrics**:
   - `http_requests_total`: Total requests by method, endpoint and status
   - `http_request_duration_seconds`: Request duration (histogram)
   - `http_requests_in_progress`: Currently processing requests

2. **Business Metrics**:
   - `transactions_created_total`: Transactions created by type, product and status
   - `transactions_retrieved_total`: Transactions retrieved by user

3. **External Service Metrics**:
   - `external_service_calls_total`: External service calls
   - `external_service_duration_seconds`: External call duration
   - `circuit_breaker_state`: Circuit breaker states

**Usage example**:
```bash
# Get metrics
curl http://localhost:8000/api/v1/metrics

# Integrate with Prometheus
# prometheus.yml
scrape_configs:
  - job_name: 'astropay-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/metrics'
```

### 7. Enhanced Health Checks

**Endpoint**: `GET /api/v1/health`

- Verifies status of all services
- Includes circuit breaker status
- Returns:
  - `healthy`: All services functioning
  - `degraded`: Some services degraded but critical ones OK
  - `unhealthy`: Critical services (DB) unavailable

**Response**:
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "elasticsearch": "healthy",
  "kafka": "healthy"
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100
RATE_LIMIT_WINDOW=60

# Circuit Breakers
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60

# Timeouts
REQUEST_TIMEOUT=30
EXTERNAL_SERVICE_TIMEOUT=5
```

### Middleware Order

Order matters. Middlewares execute in reverse order:

1. **RequestIDMiddleware**: First to track everything
2. **LoggingMiddleware**: To log all requests
3. **MetricsMiddleware**: To collect metrics
4. **TimeoutMiddleware**: To apply timeouts
5. **RateLimitMiddleware**: To limit rate (rejects early)
6. **CORSMiddleware**: Last (handles CORS)

## 📊 Monitoring

### Key Metrics to Monitor

1. **Rate Limiting**:
   - `http_requests_total{status="429"}`: Requests rejected by rate limit
   - `X-RateLimit-Remaining`: Remaining requests per user/IP

2. **Circuit Breakers**:
   - `circuit_breaker_state{service="elasticsearch"}`: Breaker state
   - `external_service_calls_total{status="failure"}`: Service failures

3. **Performance**:
   - `http_request_duration_seconds`: Request latency
   - `http_requests_in_progress`: Current load

4. **Errors**:
   - `http_requests_total{status="5xx"}`: Server errors
   - `http_requests_total{status="504"}`: Timeouts

### Recommended Alerts

```yaml
# Example Prometheus alerts
groups:
  - name: astropay_api
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state{state="2"} == 1
        for: 1m
        
      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
        for: 5m
        
      - alert: RateLimitExceeded
        expr: rate(http_requests_total{status="429"}[5m]) > 10
        for: 5m
```

## 🚀 Best Practices

### For Development

1. **Disable rate limiting in development**:
   ```python
   RATE_LIMIT_ENABLED=false
   ```

2. **Adjust timeouts for debugging**:
   ```python
   REQUEST_TIMEOUT=60  # More time for debugging
   ```

### For Production

1. **Configure appropriate rate limits**:
   - Based on actual server capacity
   - Consider limits per user vs per IP
   - Implement whitelist for internal services

2. **Monitor circuit breakers**:
   - Alert when they open
   - Investigate root causes of failures

3. **Adjust timeouts**:
   - Based on actual latency percentiles
   - Consider SLA of external services

4. **Configure CORS appropriately**:
   ```python
   allow_origins=["https://app.astropay.com"]  # Don't use "*" in production
   ```

## 🔍 Troubleshooting

### Rate Limit Exceeded

**Symptom**: `429 Too Many Requests`

**Solution**:
- Verify limits in `app/middleware/rate_limit.py`
- Review logs to identify problematic IPs/users
- Consider increasing limits if legitimate

### Circuit Breaker Open

**Symptom**: External services don't respond, but no errors in logs

**Solution**:
- Verify status: `GET /api/v1/health`
- Review external service logs
- Wait for timeout or restart external service
- Breaker will close automatically when service recovers

### High Latency

**Symptom**: Slow requests, frequent timeouts

**Solution**:
- Review metrics: `http_request_duration_seconds`
- Identify slow endpoints
- Optimize database queries
- Review cache usage
- Consider increasing timeouts if necessary

## 📚 References

- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Rate Limiting Strategies](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [FastAPI Middleware](https://fastapi.tiangolo.com/advanced/middleware/)
