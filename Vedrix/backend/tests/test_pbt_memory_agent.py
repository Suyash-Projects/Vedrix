import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from app.services.memory_service import memory_service
from app.models.longitudinal_profile import LongitudinalProfile
from app.core.encryption import EncryptedJSON

# ── Property 3: Skill Trend Direction Consistency ─────────────────────────────
@given(st.lists(st.floats(min_value=0.0, max_value=10.0), min_size=2, max_size=20))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_property_3_skill_trend_consistency(scores):
    """Feature: agentic-platform-evolution, Property 3: Skill Trend Direction Consistency"""
    # 1. Monotonically increasing (strictly increasing)
    inc_scores = sorted(list(set(scores)))
    if len(inc_scores) >= 2:
        assert memory_service.compute_trend(inc_scores) == "improving"

    # 2. Monotonically decreasing (strictly decreasing)
    dec_scores = sorted(list(set(scores)), reverse=True)
    if len(dec_scores) >= 2:
        assert memory_service.compute_trend(dec_scores) == "declining"

    # 3. All equal
    eq_scores = [scores[0]] * len(scores)
    assert memory_service.compute_trend(eq_scores) == "stable"


# ── Property 2: Skill Score History Round-Trip ─────────────────────────────────
@given(
    skill_history=st.dictionaries(
        st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
        st.lists(
            st.fixed_dictionaries({
                "score": st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
                "session_id": st.integers(min_value=1, max_value=10000),
                "timestamp": st.text(min_size=1, max_size=30)
            }),
            min_size=1,
            max_size=10
        )
    )
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_property_2_skill_score_history_round_trip(skill_history):
    """Feature: agentic-platform-evolution, Property 2: Skill Score History Round-Trip"""
    # Simulate DB serialization
    decorator = EncryptedJSON()
    # Mock dialect
    dialect = None
    
    # Process bind param (serialize/encrypt)
    db_value = decorator.process_bind_param(skill_history, dialect)
    assert db_value is not None
    assert isinstance(db_value, str)

    # Process result value (decrypt/deserialize)
    loaded_value = decorator.process_result_value(db_value, dialect)
    assert loaded_value == skill_history


# ── Property 1: Longitudinal Profile Merge Preserves Union ─────────────────────
@pytest.mark.asyncio
async def test_property_1_longitudinal_profile_merge_preserves_union(db_session, test_user):
    """Feature: agentic-platform-evolution, Property 1: Longitudinal Profile Merge Preserves Union"""
    # Create profile
    profile = await memory_service.get_or_create_profile(candidate_id=test_user.id, db=db_session)
    
    # Step 1: Merge session 1 with first skill set
    skills_s1 = {"python": 8.0, "fastapi": 7.5}
    profile = await memory_service.merge_session_skills(
        candidate_id=test_user.id,
        session_id=101,
        skill_scores=skills_s1,
        db=db_session
    )
    
    # Step 2: Merge session 2 with second skill set
    skills_s2 = {"postgres": 9.0, "fastapi": 8.5}
    profile = await memory_service.merge_session_skills(
        candidate_id=test_user.id,
        session_id=102,
        skill_scores=skills_s2,
        db=db_session
    )
    
    # Verify union of both sets is preserved
    assert "python" in profile.skill_averages
    assert "fastapi" in profile.skill_averages
    assert "postgres" in profile.skill_averages
    
    # Averages should reflect the merged scores
    assert profile.skill_averages["python"] == 8.0
    assert profile.skill_averages["postgres"] == 9.0
    assert profile.skill_averages["fastapi"] == 8.0 # (7.5 + 8.5) / 2
