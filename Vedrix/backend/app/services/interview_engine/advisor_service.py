"""
AI-Powered Interview Advisor Service.

Monitors interview progress and notifies HR interviewer when
the candidate has demonstrated sufficient skills to close the interview.
The interviewer always retains control over when to end.

Design Philosophy:
- AI NEVER ends the interview — only SUGGESTS
- Interviewer ALWAYS in control — can ignore, delay, or act
- Natural closing — smooth transition, not abrupt cutoff
- Silent monitoring — candidate doesn't know AI is advising
- Explainable suggestions — interviewer sees WHY
"""
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .model_router import get_llm, TaskType
from .state import InterviewState

logger = logging.getLogger(__name__)


class AdvisorDecision(BaseModel):
    """Advisor suggestion to the interviewer."""
    ready_to_close: bool = Field(description="Suggest closing the interview")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in suggestion")
    reason: str = Field(description="Human-readable explanation for interviewer")
    reason_category: str = Field(
        description="Category: strong_performance, skill_coverage_complete, "
        "diminishing_returns, time_efficient, insufficient_data, needs_more_time"
    )
    recommended_closing_message: str = Field(
        description="Suggested natural closing message for interviewer"
    )
    signals_summary: str = Field(description="Brief summary of key signals")


# ── Signal Analysis Helpers ─────────────────────────────────────────────────────

def compute_score_trend(scores: List[float]) -> str:
    """
    Analyze score trajectory.
    Returns: 'improving', 'declining', 'stable', 'insufficient_data'
    """
    if len(scores) < 3:
        return "insufficient_data"
    recent = scores[-3:]
    # Improving: each score >= previous (within 0.3 tolerance)
    if all(recent[i] <= recent[i + 1] + 0.3 for i in range(len(recent) - 1)):
        return "improving"
    # Declining: each score >= next (within 0.3 tolerance)
    if all(recent[i] >= recent[i + 1] - 0.3 for i in range(len(recent) - 1)):
        return "declining"
    return "stable"


def compute_diminishing_returns(
    scores: List[float], window: int = 3, threshold: float = 0.5
) -> bool:
    """
    Check if recent scores show diminishing returns (little new information).
    Returns True if last N scores are within threshold of each other.
    """
    if len(scores) < window:
        return False
    recent = scores[-window:]
    return max(recent) - min(recent) <= threshold


def detect_fatigue(
    scores: List[float], messages: List[Dict], window: int = 4
) -> bool:
    """
    Detect candidate fatigue: declining scores + shorter responses.
    Returns True if both patterns are detected.
    """
    if len(scores) < window:
        return False
    recent_scores = scores[-window:]
    recent_messages = [m for m in messages if m.get("role") == "user"][-window:]

    # Check declining scores
    declining = all(
        recent_scores[i] >= recent_scores[i + 1]
        for i in range(len(recent_scores) - 1)
    )

    # Check shorter responses
    if len(recent_messages) >= 2:
        lengths = [len(m.get("content", "")) for m in recent_messages]
        shortening = all(
            lengths[i] >= lengths[i + 1] for i in range(len(lengths) - 1)
        )
        return declining and shortening

    return declining


# ── AI-Powered Assessment ───────────────────────────────────────────────────────

async def assess_interview_advisor(state: InterviewState) -> AdvisorDecision:
    """
    AI-powered assessment that suggests to interviewer when to close.
    Never forces closure — only recommends.
    """
    idx = state.get("current_question_index", 0)
    max_q = state.get("max_questions", 150)
    avg_score = state.get("avg_score", 0)
    coverage = state.get("skill_coverage_percentage", 0)
    high_q = state.get("high_quality_count", 0)
    low_q = state.get("low_quality_count", 0)
    topic_scores = state.get("topic_scores", {})
    covered = state.get("covered_skills", [])
    pending = state.get("pending_skills", [])
    messages = state.get("messages", [])

    # Compute helper signals
    score_history = [
        m.get("score") for m in messages if "score" in m
    ]
    trend = (
        compute_score_trend(score_history)
        if score_history
        else "insufficient_data"
    )
    diminishing = compute_diminishing_returns(score_history)
    fatigue = detect_fatigue(score_history, messages)

    # Build recent history for context
    recent = messages[-6:] if len(messages) > 6 else messages
    history_text = "\n".join(
        f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: "
        f"{m.get('content', '')[:200]}"
        for m in recent
    )

    # Use the report generation model (analytical reasoning)
    llm = get_llm(TaskType.REPORT_GEN)

    system_prompt = f"""You are an expert interview assessment advisor. Your role is to monitor an ongoing AI interview and advise the HR interviewer when the candidate has demonstrated sufficient skills to close the interview naturally.

IMPORTANT: You NEVER force the interview to end. You only SUGGEST to the interviewer. The interviewer always retains control.

## INTERVIEW CONTEXT
- Current Question: {idx} of {max_q}
- Average Score: {avg_score}/10.0
- Skill Coverage: {coverage}%
- High Quality Responses: {high_q}
- Low Quality Responses: {low_q}
- Score Trend: {trend}
- Diminishing Returns: {'Yes' if diminishing else 'No'}
- Candidate Fatigue: {'Yes' if fatigue else 'No'}

## SKILL COVERAGE
- Covered Skills: {', '.join(covered) if covered else 'None'}
- Pending Skills: {', '.join(pending) if pending else 'None'}

## TOPIC SCORES
{topic_scores}

## RECENT EXCHANGES
{history_text}

## ADVISORY FRAMEWORK
Consider these factors:

1. ASSESSMENT CONFIDENCE: Do we have enough reliable data to form a solid assessment?
2. SKILL COVERAGE: Have we tested the critical skills for this role with sufficient depth?
3. DIMINISHING RETURNS: Are new questions still revealing new information?
4. CANDIDATE STATE: Is the candidate engaged, or showing signs of fatigue?
5. TIME EFFICIENCY: Has the candidate proven themselves quickly?

## OUTPUT
Return a JSON advisory decision:
- ready_to_close: true/false (suggest closing to interviewer)
- confidence: 0.0-1.0 (how confident you are in this suggestion)
- reason: Human-readable explanation FOR THE INTERVIEWER (professional, clear)
- reason_category: One of [strong_performance, skill_coverage_complete, diminishing_returns, time_efficient, insufficient_data, needs_more_time]
- recommended_closing_message: A natural, professional closing message the interviewer can use
- signals_summary: Brief summary of key signals that drove your suggestion

Return JSON only.
"""

    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        from langchain_core.output_parsers import JsonOutputParser
        import json

        parser = JsonOutputParser(pydantic_object=AdvisorDecision)
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content="Assess whether to suggest closing this interview to the HR interviewer."
            ),
        ])

        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return AdvisorDecision(**json.loads(content))

    except Exception as e:
        logger.error(f"Advisor assessment failed: {e}")
        # Fallback: rule-based suggestion
        return rule_based_advisor(state, trend, diminishing, fatigue)


# ── Rule-Based Fallback ─────────────────────────────────────────────────────────

def rule_based_advisor(
    state: InterviewState, trend: str, diminishing: bool, fatigue: bool
) -> AdvisorDecision:
    """Rule-based fallback if AI fails."""
    idx = state.get("current_question_index", 0)
    avg = state.get("avg_score", 0)
    coverage = state.get("skill_coverage_percentage", 0)
    high_q = state.get("high_quality_count", 0)

    # Strong candidate: high scores, good coverage
    if idx >= 8 and avg >= 7.5 and coverage >= 70 and high_q >= 4:
        return AdvisorDecision(
            ready_to_close=True,
            confidence=0.85,
            reason=(
                "Candidate has demonstrated strong performance across multiple skills. "
                "Assessment confidence is high."
            ),
            reason_category="strong_performance",
            recommended_closing_message=(
                "You've done an excellent job today. I think we have a very clear picture "
                "of your abilities. Do you have any questions for me before we wrap up?"
            ),
            signals_summary=(
                f"Q{idx}, avg {avg:.1f}, {coverage}% coverage, {high_q} high-quality responses"
            ),
        )

    # Diminishing returns
    if idx >= 10 and diminishing and avg >= 5.0:
        return AdvisorDecision(
            ready_to_close=True,
            confidence=0.75,
            reason=(
                "Recent questions aren't revealing new information. "
                "We have sufficient data for assessment."
            ),
            reason_category="diminishing_returns",
            recommended_closing_message=(
                "Thank you for your thoughtful responses. I believe we have enough "
                "information to complete our evaluation. Any final questions?"
            ),
            signals_summary=f"Q{idx}, diminishing returns detected, stable assessment",
        )

    # Fatigue
    if idx >= 8 and fatigue:
        return AdvisorDecision(
            ready_to_close=True,
            confidence=0.70,
            reason=(
                "Candidate appears to be showing signs of fatigue. "
                "Consider wrapping up to maintain assessment quality."
            ),
            reason_category="time_efficient",
            recommended_closing_message=(
                "I appreciate your time and effort today. Let's wrap up — "
                "do you have any questions for me?"
            ),
            signals_summary=f"Q{idx}, fatigue detected, declining engagement",
        )

    # Not ready
    return AdvisorDecision(
        ready_to_close=False,
        confidence=0.80,
        reason=(
            "Insufficient data yet. Continue gathering more information "
            "about the candidate's abilities."
        ),
        reason_category="needs_more_time",
        recommended_closing_message="",
        signals_summary=(
            f"Q{idx}, avg {avg:.1f}, {coverage}% coverage — continue interviewing"
        ),
    )
