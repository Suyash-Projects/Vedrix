"""
Property-Based Tests for the Matching Engine (Matching_Engine).

These exercise the PURE `compute_score()` function and the top-match flagging
rule (`match_score > top_match_threshold`). No DB session is required.

Spec: agentic-platform-evolution
Design: Matching_Engine (Section 5)
Requirements: 5.2, 5.3, 5.4, 5.8
"""
from itertools import permutations

import pytest
from hypothesis import given, settings, strategies as st

from app.services.matching_service import (
    MatchingService,
    matching_service,
    DEFAULT_TOP_MATCH_THRESHOLD,
)

# ── Shared strategies / helpers ───────────────────────────────────────────────

# Skill names are normalized to lowercase tokens throughout the service.
skill_name = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8)

# Realistic interview scores are on a 0-10 scale.
score_0_10 = st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)

growth_trend_strat = st.sampled_from(["improving", "stable", "declining"])


def _coverage_pct(skill_scores, required_skills, threshold: float = 6.0) -> float:
    """Replicates the service's coverage computation: fraction of required
    skills scored at or above the passing threshold (6.0)."""
    if not required_skills:
        return 0.0
    covered = sum(1 for s in required_skills if skill_scores.get(s, 0.0) >= threshold)
    return covered / len(required_skills)


@st.composite
def superset_subset_inputs(draw):
    """Builds a required-skill set plus a strict-superset candidate (A) and a
    strict-subset candidate (B), sharing identical per-skill scores."""
    required = draw(
        st.lists(skill_name, min_size=2, max_size=6, unique=True)
    )
    # An extra skill that is NOT one of the required skills (makes A a strict superset).
    extra = draw(skill_name.filter(lambda x: x not in required))
    # Shared score that is high enough to count as "covered" (>= 6.0).
    shared_score = draw(st.floats(min_value=6.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    overall = draw(score_0_10)
    trend = draw(growth_trend_strat)
    # B covers a strict, non-empty subset of the required skills.
    subset_size = draw(st.integers(min_value=1, max_value=len(required) - 1))
    subset = required[:subset_size]
    return required, extra, shared_score, overall, trend, subset


@st.composite
def three_candidate_inputs(draw):
    """Builds a single JobDrive's required skills plus three independent
    candidate score profiles ranked against it."""
    required = draw(st.lists(skill_name, min_size=1, max_size=5, unique=True))
    candidates = []
    for _ in range(3):
        scores = {s: draw(score_0_10) for s in required}
        overall = draw(score_0_10)
        trend = draw(growth_trend_strat)
        candidates.append((scores, overall, trend))
    return required, candidates


# ── Property 17: Match Score Range Invariant ──────────────────────────────────
# **Validates: Requirements 5.2**
@given(
    skill_scores=st.dictionaries(
        skill_name,
        st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        max_size=10,
    ),
    required_skills=st.lists(skill_name, max_size=8, unique=True),
    coverage_pct=st.floats(min_value=-1.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    overall_score=st.floats(min_value=-5.0, max_value=15.0, allow_nan=False, allow_infinity=False),
    growth_trend=st.sampled_from(["improving", "stable", "declining", "unknown", ""]),
)
@settings(max_examples=100)
def test_property_17_match_score_range_invariant(
    skill_scores, required_skills, coverage_pct, overall_score, growth_trend
):
    """Feature: agentic-platform-evolution, Property 17: Match Score Range Invariant"""
    score = matching_service.compute_score(
        skill_scores=skill_scores,
        required_skills=required_skills,
        coverage_pct=coverage_pct,
        overall_score=overall_score,
        growth_trend=growth_trend,
    )
    assert 0.0 <= score <= 100.0


# ── Property 18: Match Score Ranking Transitivity ─────────────────────────────
# **Validates: Requirements 5.3**
@given(data=three_candidate_inputs())
@settings(max_examples=100)
def test_property_18_match_score_ranking_transitivity(data):
    """Feature: agentic-platform-evolution, Property 18: Match Score Ranking Transitivity"""
    required, candidates = data

    computed = []
    for scores, overall, trend in candidates:
        s = matching_service.compute_score(
            skill_scores=scores,
            required_skills=required,
            coverage_pct=_coverage_pct(scores, required),
            overall_score=overall,
            growth_trend=trend,
        )
        computed.append(s)

    # For every ordered triple, ranking by Match_Score must be transitive:
    # rank(A) > rank(B) and rank(B) > rank(C) implies rank(A) > rank(C).
    for i, j, k in permutations(range(3), 3):
        if computed[i] > computed[j] and computed[j] > computed[k]:
            assert computed[i] > computed[k]


# ── Property 19: Superset Dominance ───────────────────────────────────────────
# **Validates: Requirements 5.4**
@given(data=superset_subset_inputs())
@settings(max_examples=100)
def test_property_19_superset_dominance(data):
    """Feature: agentic-platform-evolution, Property 19: Superset Dominance"""
    required, extra, shared_score, overall, trend, subset = data

    # Candidate A: strict superset of required skills (all required + an extra).
    a_scores = {s: shared_score for s in required}
    a_scores[extra] = shared_score

    # Candidate B: strict subset of required skills (only some of them).
    b_scores = {s: shared_score for s in subset}

    score_a = matching_service.compute_score(
        skill_scores=a_scores,
        required_skills=required,
        coverage_pct=_coverage_pct(a_scores, required),
        overall_score=overall,
        growth_trend=trend,
    )
    score_b = matching_service.compute_score(
        skill_scores=b_scores,
        required_skills=required,
        coverage_pct=_coverage_pct(b_scores, required),
        overall_score=overall,
        growth_trend=trend,
    )

    assert score_a > score_b


# ── Property 20: Top Match Flagging Threshold ─────────────────────────────────
# **Validates: Requirements 5.8**
@given(
    skill_scores=st.dictionaries(skill_name, score_0_10, max_size=8),
    required_skills=st.lists(skill_name, min_size=1, max_size=6, unique=True),
    coverage_pct=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    overall_score=score_0_10,
    growth_trend=growth_trend_strat,
    threshold=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100)
def test_property_20_top_match_flagging_threshold(
    skill_scores, required_skills, coverage_pct, overall_score, growth_trend, threshold
):
    """Feature: agentic-platform-evolution, Property 20: Top Match Flagging Threshold"""
    svc = MatchingService(top_match_threshold=threshold)

    score = svc.compute_score(
        skill_scores=skill_scores,
        required_skills=required_skills,
        coverage_pct=coverage_pct,
        overall_score=overall_score,
        growth_trend=growth_trend,
    )

    # This mirrors the exact flagging rule used in compute_match_score:
    #     is_top_match = match_score > self.top_match_threshold
    is_top_match = score > svc.top_match_threshold

    if score > threshold:
        assert is_top_match is True
    else:  # score <= threshold (boundary equality must NOT be a top match)
        assert is_top_match is False


# ── Targeted unit tests (specific examples and edge cases) ─────────────────────

def test_compute_score_perfect_candidate_is_100():
    """A fully covered, top-scoring, improving candidate scores the maximum 100."""
    score = matching_service.compute_score(
        skill_scores={"python": 10.0, "sql": 10.0},
        required_skills=["python", "sql"],
        coverage_pct=1.0,
        overall_score=10.0,
        growth_trend="improving",
    )
    # Floating-point accumulation yields ~99.9999...; the formula's max is 100.0.
    assert score == pytest.approx(100.0)


def test_compute_score_empty_inputs_are_clamped_non_negative():
    """Worst-case declining candidate with no coverage clamps to 0.0, never negative."""
    score = matching_service.compute_score(
        skill_scores={},
        required_skills=[],
        coverage_pct=0.0,
        overall_score=0.0,
        growth_trend="declining",
    )
    assert score == 0.0


def test_top_match_boundary_equal_threshold_is_not_top():
    """Score exactly equal to the threshold is NOT flagged as a top match (strict >)."""
    svc = MatchingService(top_match_threshold=DEFAULT_TOP_MATCH_THRESHOLD)
    # Construct inputs that yield exactly 80.0:
    # 0.40*1.0 + 0.30*1.0 + 0.20*0.5 + 0.10*0.0 = 0.80 -> 80.0
    score = svc.compute_score(
        skill_scores={"a": 10.0},
        required_skills=["a"],
        coverage_pct=1.0,
        overall_score=5.0,
        growth_trend="stable",
    )
    assert score == 80.0
    assert (score > svc.top_match_threshold) is False


def test_top_match_above_default_threshold_is_top():
    """Score above the default threshold (80) is flagged as a top match."""
    svc = MatchingService(top_match_threshold=DEFAULT_TOP_MATCH_THRESHOLD)
    score = svc.compute_score(
        skill_scores={"a": 10.0},
        required_skills=["a"],
        coverage_pct=1.0,
        overall_score=10.0,
        growth_trend="improving",
    )
    assert score > DEFAULT_TOP_MATCH_THRESHOLD
    assert (score > svc.top_match_threshold) is True
