"""
Property-based tests for the Planner Agent.

Feature: agentic-platform-evolution
Covers Requirements 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.11.

These tests target the deterministic / pure logic of ``PlannerNode`` so they
never hit the LLM (``generate_plan`` makes a real Groq call behind a circuit
breaker). Specifically:

* ``assign_difficulty`` — the pure profile-score -> difficulty mapping.
* ``get_default_plan`` — the deterministic plan-construction logic that
  guarantees a phase per required skill.
* ``revise_plan`` — the difficulty-reduction routine (called with ``db=None``
  and no session id so it exercises the in-memory revision path only).
"""
import asyncio

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

from app.services.interview_engine.planner_node import planner_node, PlannerNode


# ── Strategy helpers ──────────────────────────────────────────────────────────

# Actual prior scores live in (0.0, 10.0]. 0.0 and "absent" are a special
# "no prior data" sentinel handled separately (Requirement 2.6).
_real_score = st.floats(
    min_value=0.0, max_value=10.0, exclude_min=True,
    allow_nan=False, allow_infinity=False,
)
_skill_name = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=12,
)
_phase_name = st.sampled_from(
    ["greeting", "welcome", "warmup", "technical", "stress", "behavioral", "closing"]
)
_difficulty = st.sampled_from(["easy", "medium", "hard"])


def _avg_difficulty_rank(phases):
    """Mean ordinal difficulty rank across a list of phase dicts."""
    if not phases:
        return 0.0
    ranks = [PlannerNode._difficulty_rank(p.get("difficulty", "medium")) for p in phases]
    return sum(ranks) / len(ranks)


# ── Property 5: Planner Difficulty Assignment from Profile ────────────────────
@given(score=st.one_of(st.none(), _real_score, st.just(0.0)))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_5_difficulty_assignment_from_profile(score):
    """Feature: agentic-platform-evolution, Property 5: Planner Difficulty Assignment from Profile"""
    result = PlannerNode.assign_difficulty(score)

    # Expected mapping derived directly from acceptance criteria 2.4/2.5/2.6.
    if score is None or score == 0.0:
        expected = "medium"          # no prior data
    elif score > 8.0:
        expected = "hard"
    elif 0.0 < score < 5.0:
        expected = "easy"
    else:                             # 5.0 <= score <= 8.0
        expected = "medium"

    assert result == expected
    assert result in {"easy", "medium", "hard"}


# ── Property 4: Interview Plan Skill Completeness ─────────────────────────────
@given(
    job_role=st.text(min_size=1, max_size=40),
    skills_required=st.lists(_skill_name, min_size=1, max_size=8, unique=True),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_4_plan_skill_completeness(job_role, skills_required):
    """Feature: agentic-platform-evolution, Property 4: Interview Plan Skill Completeness"""
    # Compute per-skill difficulties via the real mapping (no prior data -> medium).
    difficulties = {s: PlannerNode.assign_difficulty(None) for s in skills_required}

    plan = planner_node.get_default_plan(skills_required, difficulties)
    phases = plan.get("phases", [])

    covered_skills = {p.get("skill") for p in phases}

    # Every required skill must be covered by at least one phase.
    for skill in skills_required:
        assert skill in covered_skills, (
            f"skill {skill!r} not covered by any phase; covered={covered_skills}"
        )

    # Each required skill must have at least one dedicated technical phase.
    technical_skills = {
        p.get("skill") for p in phases if p.get("phase") in ("technical", "stress")
    }
    for skill in skills_required:
        assert skill in technical_skills


# ── Property 6: Metamorphic Difficulty Ordering ───────────────────────────────
@given(
    # Each tuple: (candidate B's prior score, non-negative delta applied to A).
    # Constrained to real prior scores (0, 10] so the score->difficulty mapping
    # is monotonic; 0.0/absent is a special "no data" sentinel handled by Prop 5.
    pairs=st.lists(
        st.tuples(
            _real_score,
            st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        ),
        min_size=1,
        max_size=8,
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_6_metamorphic_difficulty_ordering(pairs):
    """Feature: agentic-platform-evolution, Property 6: Metamorphic Difficulty Ordering"""
    # Candidate A has, per skill, an equal-or-higher prior score than candidate B,
    # therefore A's average prior score >= B's.
    b_scores = [b for (b, _) in pairs]
    a_scores = [min(b + delta, 10.0) for (b, delta) in pairs]

    assert (sum(a_scores) / len(a_scores)) >= (sum(b_scores) / len(b_scores))

    a_phases = [{"difficulty": PlannerNode.assign_difficulty(s)} for s in a_scores]
    b_phases = [{"difficulty": PlannerNode.assign_difficulty(s)} for s in b_scores]

    # A (higher avg prior score) gets an equal-or-higher average difficulty.
    assert _avg_difficulty_rank(a_phases) >= _avg_difficulty_rank(b_phases)


# ── Property 7: Plan Revision Reduces Difficulty ──────────────────────────────
_phase_strategy = st.fixed_dictionaries({
    "phase": _phase_name,
    "skill": _skill_name,
    "difficulty": _difficulty,
    "question_count": st.integers(min_value=1, max_value=3),
    "topics": st.lists(_skill_name, min_size=0, max_size=3),
})


@given(
    phases=st.lists(_phase_strategy, min_size=1, max_size=10),
    phase_index_seed=st.integers(min_value=0, max_value=20),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_7_plan_revision_reduces_difficulty(phases, phase_index_seed):
    """Feature: agentic-platform-evolution, Property 7: Plan Revision Reduces Difficulty"""
    plan_phase_index = phase_index_seed % len(phases)
    original_avg = _avg_difficulty_rank(phases)

    state = {
        "interview_plan": {"phases": [dict(p) for p in phases]},
        "plan_phase_index": plan_phase_index,
        "consecutive_low_quality": 2,  # trigger condition: 2+ low-quality responses
        "supervisor_session_id": None,  # skip DB persistence in revise_plan
    }

    # Call the real revise_plan; db=None so the @trace_agent_action decorator
    # gracefully skips recording and the in-memory revision path is exercised.
    result = asyncio.run(planner_node.revise_plan(state, None))

    revised_phases = result.get("interview_plan", {}).get("phases", phases)
    revised_avg = _avg_difficulty_rank(revised_phases)

    # The revised plan's average difficulty must not exceed the original.
    assert revised_avg <= original_avg + 1e-9
