"""Circuit breaker pattern implementation for handling service failures."""
import asyncio
from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from utility import logprovider
import httpx

logger = logprovider.get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold exceeded, requests are rejected
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = (httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError),
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery (half-open state)
            expected_exception: Exceptions that count as failures
            name: Optional name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or "CircuitBreaker"
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        return (
            self.state == CircuitState.OPEN
            and self.last_failure_time is not None
            and datetime.now() >= self.last_failure_time + timedelta(seconds=self.recovery_timeout)
        )
    
    def _record_success(self):
        """Record successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"{self.name}: Service recovered, closing circuit")
        self.state = CircuitState.CLOSED
        
    def _record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(
                    f"{self.name}: Failure threshold ({self.failure_threshold}) reached. "
                    f"Opening circuit for {self.recovery_timeout}s"
                )
            self.state = CircuitState.OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self._should_attempt_reset():
            logger.info(f"{self.name}: Attempting recovery (half-open state)")
            self.state = CircuitState.HALF_OPEN
        
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"{self.name}: Circuit breaker is OPEN. "
                f"Service unavailable until {self.last_failure_time + timedelta(seconds=self.recovery_timeout)}"
            )
        
        try:
            result = await func(*args, **kwargs)
            
            # Check for HTTP error status codes
            if hasattr(result, 'status_code') and result.status_code >= 500:
                self._record_failure()
            else:
                self._record_success()
                
            return result
            
        except self.expected_exception as e:
            self._record_failure()
            raise
        except Exception as e:
            # Unexpected exceptions don't count towards circuit breaker
            logger.warning(f"{self.name}: Unexpected exception (not counted): {type(e).__name__}: {str(e)}")
            raise


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: tuple = (httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError),
    name: Optional[str] = None
):
    """
    Decorator that applies circuit breaker pattern to async functions.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exceptions that count as failures
        name: Optional name for logging
        
    Usage:
        @with_circuit_breaker(failure_threshold=5, recovery_timeout=60)
        async def my_http_call():
            ...
    """
    # Create circuit breaker instance that persists across calls
    circuit_breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
        name=name
    )
    
    def decorator(func: Callable) -> Callable:
        # Set name if not provided
        if not name:
            circuit_breaker.name = func.__name__
            
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await circuit_breaker.call(func, *args, **kwargs)
        
        # Expose circuit breaker for testing/monitoring
        wrapper.circuit_breaker = circuit_breaker
        return wrapper
        
    return decorator
