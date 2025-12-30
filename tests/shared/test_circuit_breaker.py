"""
Tests for shared circuit breaker module.
"""

import pytest
import time
from unittest.mock import MagicMock

from shared.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    get_or_create_circuit,
    get_all_circuit_status,
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_initial_state_is_closed(self):
        """Circuit should start in closed state."""
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed
    
    def test_call_success(self):
        """Successful calls should pass through."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        def success_fn():
            return "success"
        
        result = cb.call(success_fn)
        assert result == "success"
        assert cb.failure_count == 0
    
    def test_call_failure_increments_count(self):
        """Failed calls should increment failure count."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        def fail_fn():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            cb.call(fail_fn)
        
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_opens_after_threshold(self):
        """Circuit should open after failure threshold reached."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        def fail_fn():
            raise ValueError("test error")
        
        # Trigger failures
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(fail_fn)
        
        assert cb.state == CircuitState.OPEN
        assert not cb.is_closed
    
    def test_open_circuit_blocks_calls(self):
        """Open circuit should block new calls."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60)
        
        def fail_fn():
            raise ValueError("test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail_fn)
        
        # Next call should be blocked
        with pytest.raises(CircuitOpenError) as exc_info:
            cb.call(lambda: "should not run")
        
        assert "test" in exc_info.value.circuit_name
        assert exc_info.value.retry_after > 0
    
    def test_circuit_transitions_to_half_open(self):
        """Circuit should transition to half-open after recovery timeout."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        
        def fail_fn():
            raise ValueError("test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail_fn)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery
        time.sleep(0.15)
        
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_half_open_success_closes_circuit(self):
        """Successful call in half-open should close circuit."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        
        def fail_fn():
            raise ValueError("test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail_fn)
        
        # Wait for recovery
        time.sleep(0.15)
        
        # Successful call should close
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
    
    def test_half_open_failure_reopens_circuit(self):
        """Failed call in half-open should reopen circuit."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        
        def fail_fn():
            raise ValueError("test error")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail_fn)
        
        # Wait for recovery
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        
        # Fail again
        with pytest.raises(ValueError):
            cb.call(fail_fn)
        
        assert cb.state == CircuitState.OPEN
    
    def test_decorator_usage(self):
        """Circuit breaker should work as decorator."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        @cb
        def decorated_fn(x):
            return x * 2
        
        result = decorated_fn(5)
        assert result == 10
    
    def test_context_manager_usage(self):
        """Circuit breaker should work as context manager."""
        cb = CircuitBreaker("test", failure_threshold=3)
        
        with cb:
            result = 5 * 2
        
        assert result == 10
        assert cb.failure_count == 0
    
    def test_manual_reset(self):
        """Manual reset should close circuit."""
        cb = CircuitBreaker("test", failure_threshold=2)
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        
        assert cb.state == CircuitState.OPEN
        
        # Manual reset
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_get_status(self):
        """Status should return current state info."""
        cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
        
        status = cb.get_status()
        
        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["failure_threshold"] == 3


class TestCircuitRegistry:
    """Test circuit breaker registry."""
    
    def test_get_or_create_circuit(self):
        """Should create new circuit or return existing."""
        cb1 = get_or_create_circuit("registry_test_1", failure_threshold=5)
        cb2 = get_or_create_circuit("registry_test_1", failure_threshold=10)
        
        # Should return same instance
        assert cb1 is cb2
        assert cb1.failure_threshold == 5  # Original value
    
    def test_get_all_status(self):
        """Should return status of all circuits."""
        get_or_create_circuit("registry_test_2")
        
        statuses = get_all_circuit_status()
        
        assert isinstance(statuses, list)
        names = [s["name"] for s in statuses]
        assert "registry_test_2" in names
