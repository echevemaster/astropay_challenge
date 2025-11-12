"""Circuit breaker pattern implementation."""
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
import time
import structlog
from threading import Lock

logger = structlog.get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "circuit_breaker"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self.lock = Lock()
        self.success_count = 0
        self.half_open_success_threshold = 2  # Need 2 successes to close circuit
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout
    
    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_success_threshold:
                    logger.info(
                        "Circuit breaker closed",
                        circuit=self.name,
                        state="closed"
                    )
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def _on_failure(self, error: Exception):
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                # Failed during half-open, go back to open
                logger.warning(
                    "Circuit breaker reopened",
                    circuit=self.name,
                    error=str(error)
                )
                self.state = CircuitState.OPEN
                self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    logger.warning(
                        "Circuit breaker opened",
                        circuit=self.name,
                        failures=self.failure_count,
                        threshold=self.failure_threshold
                    )
                    self.state = CircuitState.OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        # Check if circuit breaker is enabled
        from app.config import settings
        if not settings.circuit_breaker_enabled:
            # Circuit breaker disabled, execute function directly
            return func(*args, **kwargs)
        
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(
                        "Circuit breaker entering half-open state",
                        circuit=self.name
                    )
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker {self.name} is OPEN. "
                        f"Service unavailable. Retry after {self.timeout}s"
                    )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise
        except Exception as e:
            # Unexpected exception, don't count as circuit breaker failure
            logger.error(
                "Unexpected exception in circuit breaker",
                circuit=self.name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        # Check if circuit breaker is enabled
        from app.config import settings
        if not settings.circuit_breaker_enabled:
            # Circuit breaker disabled, execute function directly
            return await func(*args, **kwargs)
        
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(
                        "Circuit breaker entering half-open state",
                        circuit=self.name
                    )
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker {self.name} is OPEN. "
                        f"Service unavailable. Retry after {self.timeout}s"
                    )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise
        except Exception as e:
            logger.error(
                "Unexpected exception in circuit breaker",
                circuit=self.name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        with self.lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
                "threshold": self.failure_threshold,
                "timeout": self.timeout
            }
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self.lock:
            logger.info(
                "Circuit breaker manually reset",
                circuit=self.name,
                previous_state=self.state.value
            )
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breakers for external services
_elasticsearch_breaker: Optional[CircuitBreaker] = None
_redis_breaker: Optional[CircuitBreaker] = None
_kafka_breaker: Optional[CircuitBreaker] = None


def get_elasticsearch_breaker() -> CircuitBreaker:
    """Get Elasticsearch circuit breaker."""
    global _elasticsearch_breaker
    if _elasticsearch_breaker is None:
        from app.config import settings
        _elasticsearch_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            timeout=settings.circuit_breaker_timeout,
            name="elasticsearch"
        )
    return _elasticsearch_breaker


def get_redis_breaker() -> CircuitBreaker:
    """Get Redis circuit breaker."""
    global _redis_breaker
    if _redis_breaker is None:
        from app.config import settings
        _redis_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            timeout=settings.circuit_breaker_timeout,
            name="redis"
        )
    return _redis_breaker


def get_kafka_breaker() -> CircuitBreaker:
    """Get Kafka circuit breaker."""
    global _kafka_breaker
    if _kafka_breaker is None:
        from app.config import settings
        _kafka_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            timeout=settings.circuit_breaker_timeout,
            name="kafka"
        )
    return _kafka_breaker

