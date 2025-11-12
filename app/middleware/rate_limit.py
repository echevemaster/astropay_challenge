"""Rate limiting middleware using Redis."""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import redis
from urllib.parse import urlparse
from app.config import settings
import structlog

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm."""
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client or self._init_redis()
        # Rate limits: requests per window (default: 100 req/min per IP)
        self.default_limit = 100
        self.default_window = 60  # seconds
        # Per-endpoint limits
        self.endpoint_limits = {
            "/api/v1/transactions": {"limit": 200, "window": 60},  # 200 req/min
            "/api/v1/auth/token": {"limit": 10, "window": 60},  # 10 req/min (login)
            "/api/v1/health": {"limit": 1000, "window": 60},  # Health checks
        }
    
    def _init_redis(self):
        """Initialize Redis client for rate limiting."""
        try:
            parsed = urlparse(settings.redis_url)
            client = redis.Redis(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                db=int(parsed.path.lstrip("/")) if parsed.path else 0,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            client.ping()
            return client
        except Exception as e:
            logger.warning("Rate limiting disabled: Redis unavailable", error=str(e))
            return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key for request."""
        ip = self._get_client_ip(request)
        path = request.url.path
        # Try to get user_id from request state (set by auth middleware)
        # Note: This requires auth middleware to run before rate limiting
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"rate_limit:user:{user_id}:{path}"
        return f"rate_limit:ip:{ip}:{path}"
    
    def _check_rate_limit(self, request: Request) -> tuple:
        """Check if request is within rate limit."""
        if not self.redis_client:
            return True, {}  # Allow if Redis unavailable
        
        try:
            key = self._get_rate_limit_key(request)
            path = request.url.path
            
            # Get limits for this endpoint
            limits = self.endpoint_limits.get(path, {})
            limit = limits.get("limit", self.default_limit)
            window = limits.get("window", self.default_window)
            
            # Token bucket algorithm
            current = self.redis_client.get(key)
            if current is None:
                # First request in window
                self.redis_client.setex(key, window, limit - 1)
                remaining = limit - 1
                reset_time = int(time.time()) + window
            else:
                remaining = int(current)
                if remaining <= 0:
                    # Rate limit exceeded
                    ttl = self.redis_client.ttl(key)
                    reset_time = int(time.time()) + (ttl if ttl > 0 else window)
                    return False, {
                        "limit": limit,
                        "remaining": 0,
                        "reset": reset_time
                    }
                # Decrement counter
                remaining = self.redis_client.decr(key)
                ttl = self.redis_client.ttl(key)
                reset_time = int(time.time()) + (ttl if ttl > 0 else window)
            
            return True, {
                "limit": limit,
                "remaining": max(0, remaining),
                "reset": reset_time
            }
        except Exception as e:
            logger.warning("Rate limit check failed", error=str(e))
            # Fail open: allow request if rate limit check fails
            return True, {}
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks in some cases
        if request.url.path == "/api/v1/health" and request.method == "GET":
            # Health checks have higher limits, but still check
            pass
        
        allowed, rate_info = self._check_rate_limit(request)
        
        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                ip=self._get_client_ip(request),
                path=request.url.path,
                limit=rate_info.get("limit")
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": rate_info.get("reset", 60),
                    "limit": rate_info.get("limit"),
                    "reset": rate_info.get("reset")
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info.get("reset", 0)),
                    "Retry-After": str(rate_info.get("reset", 60))
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(rate_info.get("reset", 0))
        
        return response

