"""Prometheus metrics middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from prometheus_client import Counter, Histogram, Gauge
import time

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"]
)

# Business metrics
transactions_created_total = Counter(
    "transactions_created_total",
    "Total transactions created",
    ["transaction_type", "product", "status"]
)

transactions_retrieved_total = Counter(
    "transactions_retrieved_total",
    "Total transactions retrieved",
    ["user_id"]
)

# External service metrics
external_service_calls_total = Counter(
    "external_service_calls_total",
    "Total external service calls",
    ["service", "status"]
)

external_service_duration_seconds = Histogram(
    "external_service_duration_seconds",
    "External service call duration",
    ["service"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0)
)

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half-open, 2=open)",
    ["service"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics."""
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics (remove IDs, etc.)."""
        # Replace UUIDs and IDs with placeholders
        import re
        # Replace UUIDs
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        return path
    
    async def dispatch(self, request: Request, call_next):
        """Collect metrics for request."""
        method = request.method
        path = self._normalize_path(request.url.path)
        
        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=path).inc()
        
        start_time = time.time()
        try:
            response = await call_next(request)
            status_code = response.status_code
            duration = time.time() - start_time
            
            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            status_code = 500
            
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)
            
            raise
        finally:
            http_requests_in_progress.labels(method=method, endpoint=path).dec()

