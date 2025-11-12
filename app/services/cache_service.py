"""Caching service using Redis."""
import json
import redis
from typing import Optional, Any
from app.config import settings
from app.middleware.circuit_breaker import get_redis_breaker, CircuitBreakerOpenError
import structlog

logger = structlog.get_logger()


class CacheService:
    """Service for caching operations."""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
        except Exception as e:
            logger.warning("Redis connection failed, caching disabled", error=str(e))
            self.redis_client = None
            self.enabled = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        try:
            breaker = get_redis_breaker()
            value = breaker.call(self.redis_client.get, key)
            if value:
                return json.loads(value)
            return None
        except CircuitBreakerOpenError:
            logger.warning("Cache get skipped: circuit breaker open", key=key)
            return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self.enabled:
            return False
        try:
            breaker = get_redis_breaker()
            ttl = ttl or settings.cache_ttl
            serialized = json.dumps(value, default=str)
            return breaker.call(self.redis_client.setex, key, ttl, serialized)
        except CircuitBreakerOpenError:
            logger.warning("Cache set skipped: circuit breaker open", key=key)
            return False
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enabled:
            return False
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        if not self.enabled:
            return 0
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("Cache delete pattern failed", pattern=pattern, error=str(e))
            return 0
    
    def health_check(self) -> bool:
        """Check if cache service is healthy."""
        if not self.enabled:
            return False
        try:
            return self.redis_client.ping()
        except Exception:
            return False

