"""
Circuit Breaker implementation for LMSilo services.

Prevents cascading failures when ML models fail to load or external services are unavailable.
"""

import time
import logging
import threading
from enum import Enum
from typing import Callable, Optional, Any, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failures exceeded threshold, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is blocked."""
    
    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit '{circuit_name}' is open. Retry after {retry_after:.1f} seconds."
        )


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.
    
    Example usage:
        # Create breaker for model loading
        model_breaker = CircuitBreaker("model_loader", failure_threshold=3, recovery_timeout=60)
        
        # Use as decorator
        @model_breaker
        def load_model():
            return Model.load()
        
        # Or use as context manager
        with model_breaker:
            model = Model.load()
        
        # Or call explicitly
        try:
            result = model_breaker.call(load_model)
        except CircuitOpenError as e:
            return {"error": "Service temporarily unavailable", "retry_after": e.retry_after}
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
        exception_types: tuple = (Exception,),
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit identifier for logging and metrics
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open state
            half_open_max_calls: Number of test calls allowed in half-open state
            exception_types: Exception types that count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.exception_types = exception_types
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()
        
        # Metrics hooks (can be replaced with actual metrics)
        self._on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None
        self._on_failure: Optional[Callable[[Exception], None]] = None
        self._on_success: Optional[Callable[[], None]] = None
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery timeout."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is allowing requests."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count
    
    @property
    def time_until_retry(self) -> float:
        """Get seconds until circuit might close (0 if not open)."""
        with self._lock:
            if self._state != CircuitState.OPEN or self._last_failure_time is None:
                return 0.0
            elapsed = time.time() - self._last_failure_time
            remaining = self.recovery_timeout - elapsed
            return max(0.0, remaining)
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if self._last_failure_time is None:
            return True
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.recovery_timeout
    
    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state with logging."""
        old_state = self._state
        self._state = new_state
        
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._last_failure_time = None
        
        logger.info(f"Circuit '{self.name}' transitioned: {old_state.value} -> {new_state.value}")
        
        if self._on_state_change:
            try:
                self._on_state_change(old_state, new_state)
            except Exception:
                pass
    
    def _record_failure(self, error: Exception):
        """Record a failure and potentially open circuit."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._on_failure:
                try:
                    self._on_failure(error)
                except Exception:
                    pass
            
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                logger.warning(
                    f"Circuit '{self.name}' reopening after half-open failure: {error}"
                )
                self._transition_to(CircuitState.OPEN)
            elif self._failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit '{self.name}' opening after {self._failure_count} failures"
                )
                self._transition_to(CircuitState.OPEN)
    
    def _record_success(self):
        """Record a success and potentially close circuit."""
        with self._lock:
            if self._on_success:
                try:
                    self._on_success()
                except Exception:
                    pass
            
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.half_open_max_calls:
                    logger.info(f"Circuit '{self.name}' closing after successful half-open test")
                    self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0
    
    def _check_state(self):
        """Check if request can proceed, raise if circuit open."""
        state = self.state  # This also checks for recovery timeout
        
        if state == CircuitState.OPEN:
            raise CircuitOpenError(self.name, self.time_until_retry)
        
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitOpenError(self.name, self.time_until_retry)
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitOpenError: If circuit is open
            Exception: If function raises and circuit doesn't catch it
        """
        self._check_state()
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.exception_types as e:
            self._record_failure(e)
            raise
    
    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitOpenError: If circuit is open
        """
        self._check_state()
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.exception_types as e:
            self._record_failure(e)
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for protecting functions with circuit breaker."""
        import asyncio
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)
            return sync_wrapper
    
    def __enter__(self):
        """Context manager entry - check if circuit allows request."""
        self._check_state()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - record success or failure."""
        if exc_type is None:
            self._record_success()
        elif issubclass(exc_type, self.exception_types):
            self._record_failure(exc_val)
        return False  # Don't suppress exceptions
    
    def reset(self):
        """Manually reset circuit to closed state."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            logger.info(f"Circuit '{self.name}' manually reset")
    
    def force_open(self):
        """Manually open circuit (for testing or maintenance)."""
        with self._lock:
            self._last_failure_time = time.time()
            self._transition_to(CircuitState.OPEN)
            logger.info(f"Circuit '{self.name}' manually opened")
    
    def get_status(self) -> dict:
        """Get circuit status for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "time_until_retry": self.time_until_retry,
            "recovery_timeout": self.recovery_timeout,
        }


# Global registry of circuit breakers for monitoring
_circuit_registry: dict[str, CircuitBreaker] = {}


def get_or_create_circuit(
    name: str,
    failure_threshold: int = 3,
    recovery_timeout: float = 60.0,
    **kwargs
) -> CircuitBreaker:
    """
    Get existing circuit breaker or create new one.
    
    Args:
        name: Circuit identifier
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before retry
        **kwargs: Additional CircuitBreaker arguments
    
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_registry:
        _circuit_registry[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            **kwargs
        )
    return _circuit_registry[name]


def get_all_circuit_status() -> list[dict]:
    """Get status of all registered circuit breakers."""
    return [cb.get_status() for cb in _circuit_registry.values()]
