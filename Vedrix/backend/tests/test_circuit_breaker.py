"""
Tests for Circuit Breaker and Fallback Questions.
"""
import pytest
import time
from app.services.interview_engine.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError,
    execute_with_circuit_breaker,
    get_circuit_breaker,
    get_all_circuit_breaker_statuses,
    reset_circuit_breakers,
)
from app.services.interview_engine.fallback_questions import (
    get_fallback_question,
    TECHNICAL_QUESTIONS,
    BEHAVIORAL_QUESTIONS,
)


@pytest.fixture(autouse=True)
def reset_cbs():
    """Reset circuit breakers before each test."""
    reset_circuit_breakers()
    yield


class TestCircuitBreaker:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self):
        """New circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        """Circuit opens after failure_threshold consecutive failures."""
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        """A success resets the failure counter."""
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        # Need 3 more failures to open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_opens_to_half_open_after_timeout(self):
        """Circuit transitions from OPEN to HALF_OPEN after recovery_timeout."""
        cb = CircuitBreaker(name="test_timeout", failure_threshold=2, recovery_timeout=0)
        cb.record_failure()
        cb.record_failure()
        # With timeout=0, accessing .state triggers auto-transition to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self):
        """HALF_OPEN transitions to CLOSED on success."""
        cb = CircuitBreaker(name="test_half_open_success", failure_threshold=2, recovery_timeout=0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.HALF_OPEN  # auto-transition
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self):
        """HALF_OPEN transitions back to OPEN on failure."""
        cb = CircuitBreaker(name="test_half_open_fail", failure_threshold=2, recovery_timeout=0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.HALF_OPEN  # auto-transition
        cb.record_failure()
        # After failure in HALF_OPEN, it goes to OPEN, but with timeout=0
        # accessing .state immediately transitions back to HALF_OPEN
        # So we check _state directly
        assert cb._state == CircuitState.OPEN

    def test_can_execute_closed(self):
        """Can execute when CLOSED."""
        cb = CircuitBreaker(name="test_can_exec_closed")
        assert cb.can_execute() is True

    def test_cannot_execute_open(self):
        """Cannot execute when OPEN."""
        cb = CircuitBreaker(name="test_cannot_exec", failure_threshold=1, recovery_timeout=999)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_can_execute_half_open(self):
        """Can execute when HALF_OPEN (testing recovery)."""
        cb = CircuitBreaker(name="test_can_exec_half", failure_threshold=1, recovery_timeout=0)
        cb.record_failure()
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True

    def test_status_dict(self):
        """Status returns a dict with expected keys."""
        cb = CircuitBreaker(name="test", failure_threshold=5, recovery_timeout=120)
        status = cb.status
        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["failure_threshold"] == 5
        assert status["recovery_timeout"] == 120


class TestExecuteWithCircuitBreaker:
    """Test execute_with_circuit_breaker function."""

    @pytest.mark.asyncio
    async def test_success_records_success(self):
        """Successful execution records success."""
        async def success_func():
            return "ok"

        result = await execute_with_circuit_breaker("test_exec_cb", success_func)
        assert result == "ok"
        cb = get_circuit_breaker("test_exec_cb")
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failure_records_failure(self):
        """Failed execution records failure."""
        reset_circuit_breakers()
        cb = get_circuit_breaker("test_exec_cb2")
        cb.failure_threshold = 1
        cb.recovery_timeout = 999

        async def fail_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await execute_with_circuit_breaker("test_exec_cb2", fail_func)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_uses_fallback(self):
        """When circuit is OPEN, fallback is used."""
        reset_circuit_breakers()
        cb = get_circuit_breaker("test_exec_cb3")
        cb.failure_threshold = 1
        cb.recovery_timeout = 999

        async def fail_func():
            raise ValueError("test error")

        async def fallback_func():
            return "fallback"

        # First call fails and opens circuit
        with pytest.raises(ValueError):
            await execute_with_circuit_breaker("test_exec_cb3", fail_func)

        # Second call uses fallback
        result = await execute_with_circuit_breaker(
            "test_exec_cb3", fail_func, fallback=fallback_func
        )
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_open_circuit_raises_without_fallback(self):
        """When circuit is OPEN with no fallback, raises error."""
        reset_circuit_breakers()
        cb = get_circuit_breaker("test_exec_cb4")
        cb.failure_threshold = 1
        cb.recovery_timeout = 999

        async def fail_func():
            raise ValueError("test error")

        # First call fails and opens circuit
        with pytest.raises(ValueError):
            await execute_with_circuit_breaker("test_exec_cb4", fail_func)

        # Second call raises CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await execute_with_circuit_breaker("test_exec_cb4", fail_func)


class TestFallbackQuestions:
    """Test fallback question generation."""

    def test_python_fallback(self):
        """Python job role returns Python questions."""
        q = get_fallback_question(job_role="Python Developer", question_index=0)
        assert q["category"] == "technical"
        assert q["skill_tested"] == "python"

    def test_database_fallback(self):
        """Database job role returns database questions."""
        q = get_fallback_question(job_role="Database Engineer", question_index=0)
        assert q["skill_tested"] == "database"

    def test_frontend_fallback(self):
        """Frontend job role returns frontend questions."""
        q = get_fallback_question(job_role="React Developer", question_index=0)
        assert q["skill_tested"] == "frontend"

    def test_behavioral_phase(self):
        """Behavioral phase returns behavioral questions."""
        q = get_fallback_question(phase="behavioral")
        assert q["category"] == "behavioral"

    def test_default_fallback(self):
        """Unknown job role returns a default technical question."""
        q = get_fallback_question(job_role="Unknown Role", question_index=0)
        assert q["category"] == "technical"
        assert "question" in q
        assert "difficulty" in q

    def test_question_has_required_fields(self):
        """Fallback questions have all required fields."""
        q = get_fallback_question(job_role="Python Developer", question_index=0)
        required_fields = ["question", "category", "difficulty", "time_limit", "skill_tested", "follow_up_topic"]
        for field in required_fields:
            assert field in q, f"Missing field: {field}"

    def test_variety_across_indices(self):
        """Different indices return different questions."""
        q1 = get_fallback_question(job_role="Python Developer", question_index=0)
        q2 = get_fallback_question(job_role="Python Developer", question_index=1)
        assert q1["question"] != q2["question"]
