"""AI Supervisor Service — monitors duration, difficulty, and controls interview flow.

The AI Supervisor is the central intelligence that:
  1. Monitors per-question duration and total interview duration
  2. Tracks question difficulty progression and detects anomalies
  3. Observes candidate performance trends and fatigue signals
  4. Can take control actions (adjust difficulty, change phase, force-close)
  5. Operates in three modes: monitor-only | suggest | auto-control
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
#  Models
# ──────────────────────────────────────────────────────────────────────────────

class SupervisorObservation(BaseModel):
    """A single observation recorded by the supervisor."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    observation_type: str  # "duration_alert", "difficulty_anomaly", "fatigue_signal",
                           # "score_trend", "phase_suggestion", "control_action"
    severity: Literal["info", "warning", "critical"]
    message: str
    details: Optional[Dict[str, Any]] = None
    suggested_action: Optional[str] = None


class DifficultyAnalysis(BaseModel):
    """Analysis of difficulty progression."""
    current_difficulty: Literal["easy", "medium", "hard"] = "medium"
    difficulty_history: List[str] = Field(default_factory=list)
    difficulty_switches: int = 0
    is_stuck_on_easy: bool = False        # not challenging enough
    is_stuck_on_hard: bool = False         # too challenging
    recommended_difficulty: Literal["easy", "medium", "hard"] = "medium"
    confidence: float = 0.0                # 0-1 confidence in recommendation


class DurationAnalysis(BaseModel):
    """Analysis of timing and duration."""
    total_elapsed_seconds: float = 0.0
    current_question_start: Optional[float] = None
    current_question_duration: float = 0.0
    per_question_times: List[float] = Field(default_factory=list)
    avg_time_per_question: float = 0.0
    time_alerts: List[str] = Field(default_factory=list)  # e.g., "question_taking_too_long"
    is_running_overtime: bool = False
    estimated_remaining: float = 0.0


class PerformanceTrend(BaseModel):
    """Trend analysis of candidate performance."""
    score_history: List[float] = Field(default_factory=list)
    trend: Literal["improving", "declining", "stable", "mixed"] = "stable"
    volatility: float = 0.0                # standard deviation of recent scores
    fatigue_detected: bool = False
    diminishing_returns: bool = False       # scores plateauing
    low_quality_streak: int = 0
    high_quality_streak: int = 0


class SupervisorAction(BaseModel):
    """An action taken or suggested by the supervisor."""
    action_type: Literal[
        "adjust_difficulty", "change_phase", "inject_follow_up",
        "suggest_close", "force_close", "pause_interview",
        "override_question", "send_guidance", "no_action"
    ]
    confidence: float = 0.0
    reason: str = ""
    payload: Optional[Dict[str, Any]] = None
    executed: bool = False
    executed_at: Optional[datetime] = None


class SupervisorState(BaseModel):
    """Complete supervisor state for one interview session."""
    session_id: str = ""
    control_mode: Literal["monitor", "suggest", "auto"] = "suggest"
    is_active: bool = True
    observations: List[SupervisorObservation] = Field(default_factory=list)
    difficulty_analysis: DifficultyAnalysis = Field(default_factory=DifficultyAnalysis)
    duration_analysis: DurationAnalysis = Field(default_factory=DurationAnalysis)
    performance_trend: PerformanceTrend = Field(default_factory=PerformanceTrend)
    last_action: Optional[SupervisorAction] = None
    action_history: List[SupervisorAction] = Field(default_factory=list)
    paused: bool = False

    def add_observation(self, obs: SupervisorObservation):
        self.observations.append(obs)
        # Keep last 100 observations
        if len(self.observations) > 100:
            self.observations = self.observations[-100:]


# ──────────────────────────────────────────────────────────────────────────────
#  Difficulty Monitor
# ──────────────────────────────────────────────────────────────────────────────

def analyze_difficulty(
    current_difficulty: str,
    score_history: List[float],
    current_score: float,
    difficulty_history: List[str],
) -> DifficultyAnalysis:
    """Analyze difficulty progression and recommend adjustments.

    Rules:
      - If 3+ consecutive scores >= 7.5 on "easy" or "medium" → escalate
      - If 2+ consecutive scores < 4.0 on "medium" or "hard" → de-escalate
      - If scores oscillate (alternating high/low) → keep current
      - If stuck on "hard" with 3+ scores < 5.0 → de-escalate
      - If stuck on "easy" with 5+ scores >= 8.0 → escalate twice
    """
    analysis = DifficultyAnalysis(
        current_difficulty=current_difficulty,
        difficulty_history=difficulty_history,
        difficulty_switches=len([d for i, d in enumerate(difficulty_history) if i > 0 and d != difficulty_history[i-1]]),
    )

    recent = score_history[-5:] if len(score_history) >= 5 else score_history
    if not recent:
        analysis.recommended_difficulty = current_difficulty
        return analysis

    avg_recent = sum(recent) / len(recent)

    # Check for "stuck on easy" (not challenging enough)
    if current_difficulty in ("easy",) and len(recent) >= 3:
        if all(s >= 7.5 for s in recent[-3:]):
            analysis.is_stuck_on_easy = True
            analysis.recommended_difficulty = "medium"
            analysis.confidence = 0.75
            return analysis
        if len(recent) >= 5 and all(s >= 8.0 for s in recent[-5:]):
            analysis.is_stuck_on_easy = True
            analysis.recommended_difficulty = "hard"
            analysis.confidence = 0.90
            return analysis

    # Check for "stuck on hard" (too challenging)
    if current_difficulty in ("hard", "medium") and len(recent) >= 2:
        if all(s < 4.0 for s in recent[-2:]):
            analysis.is_stuck_on_hard = True
            analysis.recommended_difficulty = "easy" if current_difficulty == "hard" else "medium"
            analysis.confidence = 0.80
            return analysis
        if current_difficulty == "hard" and len(recent) >= 3 and all(s < 5.0 for s in recent[-3:]):
            analysis.is_stuck_on_hard = True
            analysis.recommended_difficulty = "medium"
            analysis.confidence = 0.85
            return analysis

    # Escalate good performance on medium
    if current_difficulty == "medium" and len(recent) >= 3:
        if all(s >= 8.0 for s in recent[-3:]):
            analysis.recommended_difficulty = "hard"
            analysis.confidence = 0.70
            return analysis

    # Oscillation detection — keep current
    if len(recent) >= 4:
        oscillating = all(
            (recent[i] >= 6.0 and recent[i+1] < 6.0) or
            (recent[i] < 6.0 and recent[i+1] >= 6.0)
            for i in range(len(recent)-1)
        )
        if oscillating:
            analysis.recommended_difficulty = current_difficulty
            analysis.confidence = 0.60
            return analysis

    # Default: recommend same difficulty
    analysis.recommended_difficulty = current_difficulty
    analysis.confidence = 0.50
    return analysis


# ──────────────────────────────────────────────────────────────────────────────
#  Duration Monitor
# ──────────────────────────────────────────────────────────────────────────────

def analyze_duration(
    question_index: int,
    session_start_epoch: float,
    question_start_epoch: Optional[float],
    per_question_times: List[float],
    max_questions: int = 15,
) -> DurationAnalysis:
    """Analyze timing and detect duration issues.

    Alerts:
      - question_taking_too_long: single question > 5 min
      - running_overtime: total time > 45 min (typical interview max)
      - too_slow_pace: avg per-question > 4 min before question 5
      - too_fast_pace: avg per-question < 30s with weak scores (suggests gaming)
    """
    now = time.time()
    analysis = DurationAnalysis()

    analysis.total_elapsed_seconds = now - session_start_epoch
    analysis.per_question_times = per_question_times
    analysis.current_question_start = question_start_epoch

    # Current question duration
    if question_start_epoch:
        analysis.current_question_duration = now - question_start_epoch

        # Alert: question taking too long (> 5 minutes)
        if analysis.current_question_duration > 300:
            analysis.time_alerts.append("question_taking_too_long")

    # Average time per question
    if per_question_times:
        analysis.avg_time_per_question = sum(per_question_times) / len(per_question_times)

    # Alert: running overtime (> 45 min total)
    if analysis.total_elapsed_seconds > 2700:  # 45 min
        analysis.is_running_overtime = True
        analysis.time_alerts.append("running_overtime")

    # Alert: too slow pace (avg > 4 min before question 5)
    if question_index < 5 and per_question_times and analysis.avg_time_per_question > 240:
        analysis.time_alerts.append("too_slow_pace")

    # Alert: too fast pace (avg < 30s after question 3)
    if question_index >= 3 and per_question_times and analysis.avg_time_per_question < 30:
        analysis.time_alerts.append("too_fast_pace")

    # Estimate remaining time
    remaining_q = max_questions - question_index
    if per_question_times:
        analysis.estimated_remaining = analysis.avg_time_per_question * remaining_q

    return analysis


# ──────────────────────────────────────────────────────────────────────────────
#  Performance Trend Analyzer
# ──────────────────────────────────────────────────────────────────────────────

def analyze_performance_trend(
    score_history: List[float],
    low_quality_count: int,
    high_quality_count: int,
) -> PerformanceTrend:
    """Analyze score trends, fatigue, and diminishing returns."""
    trend = PerformanceTrend(
        score_history=score_history,
        low_quality_streak=low_quality_count,
        high_quality_streak=high_quality_count,
    )

    if len(score_history) < 3:
        trend.trend = "stable"
        return trend

    recent = score_history[-5:] if len(score_history) >= 5 else score_history

    # Trend direction
    first_half = score_history[:len(score_history)//2]
    second_half = score_history[len(score_history)//2:]

    if first_half and second_half:
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_second - avg_first > 0.5:
            trend.trend = "improving"
        elif avg_first - avg_second > 0.5:
            trend.trend = "declining"
        elif avg_first - avg_second > 2.0:
            trend.trend = "declining"
            trend.fatigue_detected = True
        else:
            trend.trend = "stable"

    # Volatility (standard deviation of recent scores)
    if len(recent) >= 3:
        mean = sum(recent) / len(recent)
        variance = sum((s - mean) ** 2 for s in recent) / len(recent)
        trend.volatility = variance ** 0.5

    # Diminishing returns — scores plateauing in last N
    if len(recent) >= 4:
        max_val = max(recent)
        min_val = min(recent)
        trend.diminishing_returns = (max_val - min_val) <= 0.5

    # Fatigue detection — declining scores AND shortening responses
    if trend.diminishing_returns and low_quality_count >= 2:
        trend.fatigue_detected = True

    return trend


# ──────────────────────────────────────────────────────────────────────────────
#  Action Recommender
# ──────────────────────────────────────────────────────────────────────────────

def recommend_action(
    difficulty_analysis: DifficultyAnalysis,
    duration_analysis: DurationAnalysis,
    performance_trend: PerformanceTrend,
    question_index: int,
    avg_score: float,
    skill_coverage: float,
    control_mode: str,
) -> Optional[SupervisorAction]:
    """Recommend the best action based on all analyses.

    Priority order:
      1. Emergency: running overtime -> suggest close
      2. Difficulty: stuck on easy/hard -> adjust difficulty
      3. Performance: fatigue/dim returns -> suggest close or break
      4. Quality: low quality streak -> simplify
      5. Coverage: high coverage + good scores -> suggest close
      6. Duration: slow pace -> increase difficulty or prompt
    """
    # 1. Running overtime — suggest closing
    if duration_analysis.is_running_overtime and question_index >= 6:
        return SupervisorAction(
            action_type="suggest_close",
            confidence=0.90,
            reason=f"Interview running overtime ({duration_analysis.total_elapsed_seconds/60:.0f} min). Recommend concluding.",
            payload={"reason_category": "time_efficient"},
        )

    # 2. Difficulty stuck on easy — escalate
    if difficulty_analysis.is_stuck_on_easy:
        return SupervisorAction(
            action_type="adjust_difficulty",
            confidence=difficulty_analysis.confidence,
            reason=f"Candidate consistently scoring high (≥7.5×{len(performance_trend.score_history[-3:])}). Escalating to {difficulty_analysis.recommended_difficulty}.",
            payload={"new_difficulty": difficulty_analysis.recommended_difficulty},
        )

    # 3. Difficulty stuck on hard — de-escalate
    if difficulty_analysis.is_stuck_on_hard:
        return SupervisorAction(
            action_type="adjust_difficulty",
            confidence=difficulty_analysis.confidence,
            reason=f"Candidate struggling with {difficulty_analysis.current_difficulty} questions. De-escalating to {difficulty_analysis.recommended_difficulty}.",
            payload={"new_difficulty": difficulty_analysis.recommended_difficulty},
        )

    # 4. Fatigue detected — suggest close if enough data
    if performance_trend.fatigue_detected and question_index >= 8 and avg_score >= 5.0:
        return SupervisorAction(
            action_type="suggest_close",
            confidence=0.75,
            reason="Candidate showing fatigue signals (declining scores and shortening responses). Consider wrapping up.",
            payload={"reason_category": "diminishing_returns"},
        )

    # 5. Low quality streak — simplify
    if performance_trend.low_quality_streak >= 3 and question_index >= 5:
        return SupervisorAction(
            action_type="adjust_difficulty",
            confidence=0.70,
            reason=f"Multiple low-quality responses ({performance_trend.low_quality_streak}). Reducing difficulty to help candidate recover.",
            payload={"new_difficulty": "easy"},
        )

    # 6. High coverage + good scores — suggest close
    if skill_coverage >= 85 and avg_score >= 6.0 and question_index >= 6:
        return SupervisorAction(
            action_type="suggest_close",
            confidence=0.80,
            reason=f"Skill coverage at {skill_coverage:.0f}% with average score {avg_score:.1f}. Sufficient data collected.",
            payload={"reason_category": "skill_coverage_complete"},
        )

    # 7. Slow pace — check if early in interview
    if "too_slow_pace" in duration_analysis.time_alerts:
        return SupervisorAction(
            action_type="send_guidance",
            confidence=0.60,
            reason="Candidate taking unusually long per question. Consider prompting for more concise answers.",
            payload={"guidance": "Encourage concise responses"},
        )

    # 8. Too fast pace (possible gaming) — increase difficulty
    if "too_fast_pace" in duration_analysis.time_alerts and avg_score < 4.0:
        return SupervisorAction(
            action_type="adjust_difficulty",
            confidence=0.65,
            reason="Very fast responses with low scores. May need more challenging questions.",
            payload={"new_difficulty": "hard"},
        )

    # No action needed
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  Supervisor Session Registry
# ──────────────────────────────────────────────────────────────────────────────

class SupervisorRegistry:
    """Global registry of active supervisor sessions.

    Tracks all ongoing interviews with real-time supervisor state.
    Enables the admin dashboard to query live status.
    """

    def __init__(self):
        self._sessions: Dict[str, SupervisorState] = {}

    def register(self, session_id: str, control_mode: str = "suggest") -> SupervisorState:
        """Register a new interview session for supervision."""
        state = SupervisorState(session_id=session_id, control_mode=control_mode)
        self._sessions[session_id] = state
        logger.info(f"Supervisor registered session {session_id} (mode={control_mode})")
        return state

    def unregister(self, session_id: str):
        """Remove a completed/disconnected session."""
        self._sessions.pop(session_id, None)
        logger.info(f"Supervisor unregistered session {session_id}")

    def get(self, session_id: str) -> Optional[SupervisorState]:
        """Get supervisor state for a session."""
        return self._sessions.get(session_id)

    def get_all_active(self) -> List[SupervisorState]:
        """Get all active (non-paused, non-completed) sessions."""
        return [s for s in self._sessions.values() if s.is_active]

    def get_active_count(self) -> int:
        """Number of active sessions being supervised."""
        return len([s for s in self._sessions.values() if s.is_active])

    def record_observation(self, session_id: str, obs: SupervisorObservation):
        """Record an observation for a session."""
        state = self._sessions.get(session_id)
        if state:
            state.add_observation(obs)

    def execute_action(self, session_id: str, action: SupervisorAction) -> bool:
        """Record that an action was taken."""
        state = self._sessions.get(session_id)
        if state:
            action.executed = True
            action.executed_at = datetime.now(timezone.utc)
            state.last_action = action
            state.action_history.append(action)
            return True
        return False

    def set_control_mode(self, session_id: str, mode: str):
        """Change control mode for a session."""
        state = self._sessions.get(session_id)
        if state:
            state.control_mode = mode
            self.record_observation(
                session_id,
                SupervisorObservation(
                    observation_type="control_mode_change",
                    severity="info",
                    message=f"Control mode changed to {mode}",
                )
            )

    def pause_session(self, session_id: str) -> bool:
        """Pause supervision for a session."""
        state = self._sessions.get(session_id)
        if state:
            state.paused = True
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        """Resume supervision."""
        state = self._sessions.get(session_id)
        if state:
            state.paused = False
            return True
        return False


# Global singleton
supervisor_registry = SupervisorRegistry()
