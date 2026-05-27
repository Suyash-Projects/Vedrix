"""
Circuit Breaker Pattern for AI API Providers.

Prevents cascading failures when an AI provider is down.

States:
  CLOSED → (normal operation, requests pass through)
  OPEN   → (provider is failing, requests fail fast)
  HALF_OPEN → (testing if provider recovered)

Transitions:
  CLOSED → OPEN: After `failure_threshold` consecutive failures
  OPEN → HALF_OPEN: After `recovery_timeout` seconds
  HALF_OPEN → CLOSED: After 1 successful request
  HALF_OPEN → OPEN: After 1 failed request
"""
import time
import asyncio
import logging
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for a single AI provider."""

    name: str
    failure_threshold: int = 3
    recovery_timeout: int = 60  # seconds

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _last_success_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        """Get current state, auto-transitioning from OPEN to HALF_OPEN if timeout elapsed."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info(f"Circuit breaker '{self.name}': OPEN → HALF_OPEN (timeout elapsed)")
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self):
        """Record a successful request."""
        self._failure_count = 0
        self._last_success_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}': HALF_OPEN → CLOSED (success)")
            self._state = CircuitState.CLOSED

    def record_failure(self):
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}': HALF_OPEN → OPEN (failure)")
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker '{self.name}': CLOSED → OPEN "
                f"({self._failure_count} consecutive failures)"
            )
            self._state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        state = self.state  # Trigger auto-transition
        return state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    @property
    def status(self) -> dict:
        """Get current status for health checks."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


# ── Global Circuit Breakers for AI Providers ───────────────────────────────────

# One circuit breaker per provider
circuit_breakers: dict[str, CircuitBreaker] = {
    "groq": CircuitBreaker(name="groq", failure_threshold=3, recovery_timeout=60),
    "nvidia": CircuitBreaker(name="nvidia", failure_threshold=3, recovery_timeout=60),
    "openrouter": CircuitBreaker(name="openrouter", failure_threshold=3, recovery_timeout=60),
    "openai": CircuitBreaker(name="openai", failure_threshold=3, recovery_timeout=60),
    "apifree": CircuitBreaker(name="apifree", failure_threshold=3, recovery_timeout=60),
}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a provider."""
    if provider not in circuit_breakers:
        circuit_breakers[provider] = CircuitBreaker(name=provider)
    return circuit_breakers[provider]


def get_all_circuit_breaker_statuses() -> list[dict]:
    """Get status of all circuit breakers."""
    return [cb.status for cb in circuit_breakers.values()]


def reset_circuit_breakers():
    """Reset all circuit breakers to CLOSED state (for testing)."""
    for cb in circuit_breakers.values():
        cb._state = CircuitState.CLOSED
        cb._failure_count = 0
        cb._last_failure_time = 0.0
        cb._last_success_time = 0.0


async def execute_with_circuit_breaker(
    provider: str,
    func: Callable,
    *args,
    fallback: Optional[Callable] = None,
    timeout: Optional[float] = None,
    **kwargs,
) -> Any:
    """
    Execute a function with circuit breaker protection.

    If the circuit is OPEN, raises CircuitBreakerOpenError immediately.
    If the function fails, records the failure and tries fallback.
    If the function succeeds, records the success.
    """
    cb = get_circuit_breaker(provider)

    if not cb.can_execute():
        logger.warning(f"Circuit breaker '{provider}' is OPEN — failing fast")
        if fallback:
            logger.info(f"Using fallback for '{provider}'")
            return await fallback(*args, **kwargs)
        raise CircuitBreakerOpenError(f"Circuit breaker '{provider}' is OPEN")

    try:
        if timeout is not None:
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        else:
            result = await func(*args, **kwargs)
        cb.record_success()
        return result
    except Exception as e:
        cb.record_failure()
        logger.error(f"Circuit breaker '{provider}' recorded failure: {e}")
        if fallback:
            logger.info(f"Using fallback for '{provider}' after failure")
            return await fallback(*args, **kwargs)
        raise


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is OPEN and request is rejected."""
    pass
