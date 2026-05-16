"""
Tests for the AI Interview Advisor Service.

Covers:
- Signal analysis helpers (trend, diminishing returns, fatigue)
- Rule-based advisor logic
- AdvisorDecision model validation
"""
import pytest
from app.services.interview_engine.advisor_service import (
    compute_score_trend,
    compute_diminishing_returns,
    detect_fatigue,
    rule_based_advisor,
    AdvisorDecision,
)


class TestScoreTrend:
    """Test compute_score_trend function."""

    def test_insufficient_data(self):
        """Less than 3 scores returns insufficient_data."""
        assert compute_score_trend([5.0, 6.0]) == "insufficient_data"
        assert compute_score_trend([5.0]) == "insufficient_data"
        assert compute_score_trend([]) == "insufficient_data"

    def test_improving_trend(self):
        """Scores that increase return improving."""
        assert compute_score_trend([5.0, 6.5, 8.0]) == "improving"
        assert compute_score_trend([4.0, 5.0, 6.0, 7.0]) == "improving"

    def test_declining_trend(self):
        """Scores that decrease return declining."""
        assert compute_score_trend([8.0, 6.5, 5.0]) == "declining"
        assert compute_score_trend([9.0, 8.0, 7.0, 6.0]) == "declining"

    def test_stable_trend(self):
        """Scores that fluctuate return stable."""
        assert compute_score_trend([5.0, 8.0, 5.0]) == "stable"
        assert compute_score_trend([6.0, 4.0, 7.0]) == "stable"

    def test_tolerance_boundary(self):
        """Within 0.3 tolerance should still count as improving/declining."""
        # 6.2 -> 6.4 -> 6.6 (each step +0.2, within tolerance)
        assert compute_score_trend([6.2, 6.4, 6.6]) == "improving"


class TestDiminishingReturns:
    """Test compute_diminishing_returns function."""

    def test_insufficient_scores(self):
        """Less than window size returns False."""
        assert compute_diminishing_returns([5.0, 6.0], window=3) is False

    def test_diminishing_detected(self):
        """Scores within threshold return True."""
        # All within 0.5 of each other
        assert compute_diminishing_returns([7.0, 7.2, 7.4]) is True
        assert compute_diminishing_returns([6.5, 6.8, 6.6, 6.9]) is True

    def test_no_diminishing(self):
        """Scores with large variance return False."""
        assert compute_diminishing_returns([5.0, 8.0, 6.0]) is False
        assert compute_diminishing_returns([4.0, 9.0, 5.0, 8.0]) is False

    def test_custom_window(self):
        """Custom window size works correctly."""
        scores = [5.0, 6.0, 7.0, 7.1, 7.2, 7.3]
        # Last 3 are within 0.5
        assert compute_diminishing_returns(scores, window=3) is True
        # Last 4: [7.0, 7.1, 7.2, 7.3] -> max-min = 0.3 <= 0.5, still True
        assert compute_diminishing_returns(scores, window=4) is True
        # Last 5: [6.0, 7.0, 7.1, 7.2, 7.3] -> max-min = 1.3 > 0.5, False
        assert compute_diminishing_returns(scores, window=5) is False


class TestFatigueDetection:
    """Test detect_fatigue function."""

    def test_insufficient_scores(self):
        """Less than window size returns False."""
        assert detect_fatigue([5.0, 6.0], [], window=4) is False

    def test_declining_scores_only(self):
        """Declining scores without shorter responses returns False."""
        scores = [8.0, 7.0, 6.0, 5.0]
        messages = [
            {"role": "user", "content": "Long answer with lots of detail"},
            {"role": "user", "content": "Another long answer"},
            {"role": "user", "content": "Still detailed"},
            {"role": "user", "content": "Full response here"},
        ]
        # Scores declining but responses not shortening
        assert detect_fatigue(scores, messages, window=4) is False

    def test_fatigue_detected(self):
        """Both declining scores and shorter responses returns True."""
        scores = [8.0, 7.0, 6.0, 5.0]
        messages = [
            {"role": "user", "content": "Very long detailed answer"},
            {"role": "user", "content": "Shorter answer"},
            {"role": "user", "content": "Even shorter"},
            {"role": "user", "content": "Brief"},
        ]
        assert detect_fatigue(scores, messages, window=4) is True

    def test_no_fatigue(self):
        """Stable scores with varying responses returns False."""
        scores = [7.0, 7.5, 7.0, 7.5]
        messages = [
            {"role": "user", "content": "Long answer"},
            {"role": "user", "content": "Short answer"},
            {"role": "user", "content": "Long answer"},
            {"role": "user", "content": "Short answer"},
        ]
        assert detect_fatigue(scores, messages, window=4) is False


class TestRuleBasedAdvisor:
    """Test rule_based_advisor function."""

    def _make_state(self, **kwargs):
        """Helper to create a minimal state dict."""
        state = {
            "current_question_index": kwargs.get("idx", 5),
            "avg_score": kwargs.get("avg", 5.0),
            "skill_coverage_percentage": kwargs.get("coverage", 30),
            "high_quality_count": kwargs.get("high_q", 1),
            "low_quality_count": kwargs.get("low_q", 0),
            "messages": kwargs.get("messages", []),
            "topic_scores": kwargs.get("topic_scores", {}),
            "covered_skills": kwargs.get("covered", []),
            "pending_skills": kwargs.get("pending", []),
        }
        return state

    def test_strong_performance_suggestion(self):
        """High scores + good coverage suggests closing."""
        state = self._make_state(
            idx=10, avg=8.0, coverage=75, high_q=5
        )
        decision = rule_based_advisor(state, "improving", False, False)
        assert decision.ready_to_close is True
        assert decision.reason_category == "strong_performance"
        assert decision.confidence >= 0.8

    def test_diminishing_returns_suggestion(self):
        """Many questions + diminishing returns suggests closing."""
        state = self._make_state(
            idx=12, avg=6.0, coverage=50, high_q=3
        )
        decision = rule_based_advisor(state, "stable", True, False)
        assert decision.ready_to_close is True
        assert decision.reason_category == "diminishing_returns"

    def test_fatigue_suggestion(self):
        """Fatigue detected suggests closing."""
        state = self._make_state(
            idx=10, avg=5.5, coverage=40, high_q=2
        )
        decision = rule_based_advisor(state, "declining", False, True)
        assert decision.ready_to_close is True
        assert decision.reason_category == "time_efficient"

    def test_not_ready_continues(self):
        """Early interview with low scores does not suggest closing."""
        state = self._make_state(
            idx=4, avg=4.0, coverage=20, high_q=0
        )
        decision = rule_based_advisor(state, "insufficient_data", False, False)
        assert decision.ready_to_close is False
        assert decision.reason_category == "needs_more_time"

    def test_minimum_questions_not_met(self):
        """Even with high scores, before Q8 does not suggest closing."""
        state = self._make_state(
            idx=6, avg=9.0, coverage=80, high_q=5
        )
        decision = rule_based_advisor(state, "improving", False, False)
        # Rule-based requires idx >= 8 for strong performance
        assert decision.ready_to_close is False


class TestAdvisorDecision:
    """Test AdvisorDecision model validation."""

    def test_valid_decision(self):
        """Valid decision creates successfully."""
        decision = AdvisorDecision(
            ready_to_close=True,
            confidence=0.85,
            reason="Good performance",
            reason_category="strong_performance",
            recommended_closing_message="Great job!",
            signals_summary="High scores",
        )
        assert decision.ready_to_close is True
        assert decision.confidence == 0.85

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(Exception):
            AdvisorDecision(
                ready_to_close=True,
                confidence=1.5,
                reason="test",
                reason_category="strong_performance",
                recommended_closing_message="test",
                signals_summary="test",
            )

        with pytest.raises(Exception):
            AdvisorDecision(
                ready_to_close=True,
                confidence=-0.1,
                reason="test",
                reason_category="strong_performance",
                recommended_closing_message="test",
                signals_summary="test",
            )

    def test_model_dump(self):
        """Decision can be serialized to dict."""
        decision = AdvisorDecision(
            ready_to_close=True,
            confidence=0.9,
            reason="Excellent candidate",
            reason_category="skill_coverage_complete",
            recommended_closing_message="Thank you!",
            signals_summary="All skills covered",
        )
        data = decision.model_dump()
        assert data["ready_to_close"] is True
        assert data["confidence"] == 0.9
        assert "reason" in data
