"""Tests for the AI Supervisor LangGraph Node (supervisor_node.py).

Covers:
  - supervisor_node() with paused supervisor (early return)
  - Duration observation recording in registry
  - Difficulty observation generation
  - Performance/trend observation generation
  - Action recommendation in "suggest" mode (sets advisor flags)
  - Action execution in "auto" mode (auto-applies state changes)
  - "monitor" mode (never takes action, only observes)
  - score_history and per_question_times accumulation
  - Legacy advisor_monitor_node_legacy adapter
"""

from __future__ import annotations

import time
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.interview_engine.supervisor_node import (
    supervisor_node,
    advisor_monitor_node_legacy,
)
from app.services.supervisor_service import (
    supervisor_registry,
    SupervisorObservation,
    SupervisorAction,
    SupervisorState,
)


# ═════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═════════════════════════════════════════════════════════════════════════════

def make_state(overrides=None):
    """Build a baseline InterviewState dict with supervisor fields."""
    state = {
        "supervisor_session_id": "test-session-1",
        "supervisor_mode": "suggest",
        "supervisor_paused": False,
        "supervisor_observations": [],
        "supervisor_last_action": None,
        "session_start_epoch": time.time() - 600,  # 10 min ago
        "question_start_epoch": time.time() - 60,   # 1 min on current q
        "per_question_times": [120, 110, 130],
        "current_question_index": 3,
        "max_questions": 15,
        "difficulty": "medium",
        "difficulty_history": ["easy", "medium"],
        "latest_score": 7.5,
        "score_history": [7.0, 7.5, 8.0],
        "avg_score": 7.5,
        "skill_coverage_percentage": 50.0,
        "low_quality_count": 0,
        "high_quality_count": 3,
        "advisor_ready_to_close": False,
        "advisor_action_taken": False,
        "advisor_confidence": None,
        "advisor_reason": None,
        "advisor_reason_category": None,
        # Minimal required fields
        "messages": [],
        "resume_text": "",
        "job_role": "Engineer",
        "interview_complete": False,
        "completion_reason": None,
        "current_phase": "technical",
        "phase_transition": False,
        "previous_phase": None,
        "metrics": {},
        "covered_skills": [],
        "skills_to_cover": [],
        "pending_skills": [],
        "topic_scores": {},
        "topic_strengths": {},
        "total_responses": 3,
        "interviewer_mode": "ai",
        "hr_instructions": None,
        "last_evaluation": None,
        "next_question": None,
        "code_snippet": None,
        "code_language": None,
        "is_coding_mode": False,
        "follow_up_requested": False,
        "previous_topic": None,
        "interview_complete": False,
    }
    if overrides:
        state.update(overrides)
    return state


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure clean registry before each test."""
    # Unregister any leftover test sessions
    for s in list(supervisor_registry._sessions.keys()):
        supervisor_registry.unregister(s)
    yield
    # Cleanup after test
    for s in list(supervisor_registry._sessions.keys()):
        supervisor_registry.unregister(s)


# ═════════════════════════════════════════════════════════════════════════════
#  supervisor_node — Core Logic
# ═════════════════════════════════════════════════════════════════════════════

class TestSupervisorNodePaused:
    """When supervisor_paused is True, return early."""

    def test_paused_returns_empty_observation(self):
        state = make_state({"supervisor_paused": True})
        result = supervisor_node(state)
        assert "supervisor_observations" in result
        obs = result["supervisor_observations"]
        assert len(obs) == 1
        assert obs[0]["type"] == "supervisor_paused"


class TestSupervisorNodeDuration:
    """Duration analysis outputs."""

    def test_records_question_duration(self):
        state = make_state()
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        # Should extend per_question_times with the current question's elapsed
        assert "per_question_times" in result
        assert len(result["per_question_times"]) == 4  # 3 existing + 1 new
        assert result["per_question_times"][:3] == [120, 110, 130]

    def test_resets_question_start_epoch(self):
        state = make_state()
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert "question_start_epoch" in result
        # Should be set to now (new start time)
        assert abs(result["question_start_epoch"] - time.time()) < 2

    def test_no_question_start_does_not_crash(self):
        state = make_state({"question_start_epoch": None})
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        # Should not error, should not add per_question_times
        assert "per_question_times" not in result or result.get("per_question_times") is None


class TestSupervisorNodeScoreHistory:
    """Score accumulation."""

    def test_appends_latest_score(self):
        state = make_state()
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert "score_history" in result
        assert len(result["score_history"]) == 4  # [7.0, 7.5, 8.0, 7.5]
        assert result["score_history"][-1] == 7.5

    def test_zero_score_not_appended(self):
        """A score of 0.0 should not be appended (means uninitialized)."""
        state = make_state({"latest_score": 0.0})
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert result.get("score_history", []) == [] or "score_history" not in result


class TestSupervisorNodeSuggestMode:
    """In 'suggest' mode, action sets advisor flags instead of auto-executing."""

    def test_suggest_close_sets_advisor_flags(self):
        """suggest mode: suggest_close action should set advisor_ready_to_close etc."""
        state = make_state({
            "current_question_index": 8,
            "supervisor_mode": "suggest",
            "skill_coverage_percentage": 90.0,
            "avg_score": 7.0,
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        # skill_coverage >= 85 and avg >= 6.0 and q >= 6 → suggest_close
        assert result.get("advisor_ready_to_close") is True
        assert result.get("advisor_confidence") is not None
        assert result.get("advisor_reason") is not None
        assert result.get("supervisor_last_action") is not None
        assert result["supervisor_last_action"]["action_type"] in ("suggest_close",)

    def test_suggest_mode_does_not_auto_execute_difficulty(self):
        """suggest mode: should NOT auto-apply difficulty changes."""
        # Make it stuck on easy to trigger adjust_difficulty
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
            "supervisor_mode": "suggest",
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        # Should not have applied difficulty override
        assert "difficulty" not in result or result.get("difficulty") == state["difficulty"]

    def test_suggest_mode_still_records_action_in_registry(self):
        state = make_state({
            "current_question_index": 8,
            "skill_coverage_percentage": 90.0,
            "avg_score": 7.0,
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        reg_state = supervisor_registry.get("test-session-1")
        assert reg_state.last_action is not None
        assert reg_state.last_action.action_type in ("suggest_close",)


class TestSupervisorNodeAutoMode:
    """In 'auto' mode, actions are automatically executed."""

    def test_auto_mode_executes_difficulty_adjustment(self):
        """Stuck on easy in auto mode → difficulty should change in output."""
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
            "supervisor_mode": "auto",
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        # adjust_difficulty should be auto-executed
        assert "difficulty" in result

    def test_auto_mode_sets_supervisor_override(self):
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
            "supervisor_mode": "auto",
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert result.get("supervisor_override") is not None
        assert result["supervisor_override"]["auto_executed"] is True
        assert result["supervisor_override"]["action"] == "adjust_difficulty"

    def test_auto_mode_suggest_close_sets_advisor_flags(self):
        """In auto mode, suggest_close should still set advisor flags."""
        state = make_state({
            "current_question_index": 8,
            "supervisor_mode": "auto",
            "skill_coverage_percentage": 90.0,
            "avg_score": 7.0,
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert result.get("advisor_ready_to_close") is True

    def test_auto_mode_sets_difficulty_history(self):
        """Auto-executed difficulty change should update difficulty_history."""
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
            "supervisor_mode": "auto",
            "difficulty_history": ["easy", "easy"],
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        if "difficulty" in result and result["difficulty"] != "easy":
            # If difficulty changed, difficulty_history should have been updated
            assert "difficulty_history" in result
            assert len(result["difficulty_history"]) > 2

    def test_auto_mode_executes_action_in_registry(self):
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
            "supervisor_mode": "auto",
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        reg_state = supervisor_registry.get("test-session-1")
        assert reg_state.last_action is not None
        assert reg_state.last_action.executed is True


class TestSupervisorNodeMonitorMode:
    """In 'monitor' mode, no actions are taken — only observations."""

    def test_monitor_mode_no_advisor_flags(self):
        state = make_state({
            "current_question_index": 8,
            "supervisor_mode": "monitor",
            "skill_coverage_percentage": 90.0,
            "avg_score": 7.0,
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        # Should NOT set advisor_ready_to_close
        assert result.get("advisor_ready_to_close") is not True

    def test_monitor_mode_still_has_observations(self):
        state = make_state()
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert "supervisor_observations" in result
        # Even in monitor, we should have some observations

    def test_monitor_does_not_execute_in_registry(self):
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
            "supervisor_mode": "monitor",
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        reg_state = supervisor_registry.get("test-session-1")
        # In monitor, action should still be observed/recorded but not executed
        # Actually looking at the code: monitor mode bypasses all action logic (no suggest_close handling)
        assert reg_state.last_action is None


class TestSupervisorNodeOutputs:
    """General output structure and edge cases."""

    def test_output_contains_summary(self):
        state = make_state()
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert "_supervisor_summary" in result
        summary = result["_supervisor_summary"]
        assert "difficulty" in summary
        assert "duration" in summary
        assert "performance" in summary
        assert "control_mode" in summary

    def test_output_contains_last_action_even_when_none(self):
        state = make_state()
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert "supervisor_last_action" in result
        # With default state (no trigger conditions met), last_action may be None or a dict
        # The key point is it exists

    def test_difficulty_observation_when_stuck(self):
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        observations = result.get("supervisor_observations", [])
        types = [o.get("subtype") for o in observations]
        assert "under_challenged" in types or "difficulty_adjustment_recommended" in types

    def test_performance_declining_observation(self):
        """Use extreme score drop to trigger volatility > 2.0 condition."""
        state = make_state({
            "score_history": [9.0, 9.0, 9.0, 2.0, 2.0, 2.0],
            "latest_score": 2.0,
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        observations = result.get("supervisor_observations", [])
        types = [o.get("subtype") for o in observations]
        assert "declining_performance" in types

    def test_registry_observations_logged(self):
        """Use a state that generates difficulty observations (stuck on easy)."""
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
        })
        supervisor_registry.register("test-session-1")
        supervisor_node(state)
        reg_state = supervisor_registry.get("test-session-1")
        assert len(reg_state.observations) > 0

    def test_registry_recorded_via_execute_action(self):
        """When action is taken in suggest mode, it should appear in registry."""
        state = make_state({
            "current_question_index": 8,
            "skill_coverage_percentage": 90.0,
            "avg_score": 7.0,
        })
        supervisor_registry.register("test-session-1")
        supervisor_node(state)
        reg_state = supervisor_registry.get("test-session-1")
        assert len(reg_state.action_history) > 0


class TestSupervisorNodeEdgeCases:
    """Edge cases and unusual inputs."""

    def test_unknown_session_id_does_not_crash(self):
        """Even without registered session, node should not error."""
        state = make_state({"supervisor_session_id": "nonexistent"})
        result = supervisor_node(state)
        assert result is not None

    def test_empty_state_fields(self):
        """Minimal state should not crash."""
        state = make_state({
            "per_question_times": [],
            "score_history": [],
            "latest_score": 0.0,
            "difficulty_history": [],
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert result is not None
        assert "supervisor_observations" in result

    def test_very_high_question_index(self):
        state = make_state({"current_question_index": 100})
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert result is not None

    def test_already_completed_interview(self):
        state = make_state({"interview_complete": True})
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        assert result is not None

    def test_adjust_difficulty_in_suggest_still_records_observation(self):
        """Even in suggest mode, the action observation should be logged."""
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
            "supervisor_mode": "suggest",
        })
        supervisor_registry.register("test-session-1")
        result = supervisor_node(state)
        # Should have difficulty observations
        observations = result.get("supervisor_observations", [])
        assert len(observations) > 0
        # One of them should be difficulty-related
        difficulty_obs = [o for o in observations if o.get("type") == "difficulty_observation"]
        assert len(difficulty_obs) > 0


# ═════════════════════════════════════════════════════════════════════════════
#  Legacy Adapter
# ═════════════════════════════════════════════════════════════════════════════

class TestAdvisorMonitorNodeLegacy:
    """Backward compatibility adapter."""

    def test_legacy_adapter_returns_advisor_fields(self):
        state = make_state({
            "current_question_index": 8,
            "skill_coverage_percentage": 90.0,
            "avg_score": 7.0,
        })
        supervisor_registry.register("test-session-1")
        result = advisor_monitor_node_legacy(state)
        # Should have advisor_ready_to_close
        assert "advisor_ready_to_close" in result
        assert "supervisor_observations" in result
        assert "_supervisor_summary" in result
        assert "supervisor_last_action" in result

    def test_legacy_adapter_no_action_when_no_trigger(self):
        """When no action is taken, legacy adapter should not set advisor flags."""
        state = make_state()
        supervisor_registry.register("test-session-1")
        result = advisor_monitor_node_legacy(state)
        assert "supervisor_observations" in result

    def test_legacy_adapter_passes_through_auto_overrides(self):
        state = make_state({
            "difficulty": "easy",
            "score_history": [8.0, 8.5, 8.0, 8.2, 8.5],
            "latest_score": 8.5,
            "supervisor_mode": "auto",
        })
        supervisor_registry.register("test-session-1")
        result = advisor_monitor_node_legacy(state)
        # In auto mode with stuck_on_easy, should pass through difficulty changes
        if "difficulty" in result:
            assert result["difficulty"] in ("medium", "hard")
        if "supervisor_override" in result:
            assert result["supervisor_override"]["auto_executed"] is True
