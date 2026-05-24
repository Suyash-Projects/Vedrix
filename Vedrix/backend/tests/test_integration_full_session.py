"""
Integration tests for the complete post-session pipeline.

Tests the full flow: memory merge → coaching plan → match score → orchestrator transition.
All operations are verified against a real SQLite test database.
"""
import pytest
from datetime import datetime, timezone

from app.models.user import User
from app.models.profile import HRProfile
from app.models.interview import JobDrive, InterviewSession
from app.models.longitudinal_profile import LongitudinalProfile
from app.models.coaching_plan import CoachingPlan
from app.models.match_result import MatchResult
from app.models.candidate_workflow import CandidateWorkflow
from app.models.trace_entry import TraceEntry
from app.services.memory_service import memory_service
from app.services.coaching_service import coaching_service
from app.services.matching_service import matching_service
from app.services.orchestrator_service import OrchestratorService
from app.services.observability_service import ObservabilityService
from app.core.security import get_password_hash

from sqlmodel import select


@pytest.fixture
async def full_session_setup(db_session):
    """Create a complete test environment: user, HR, job drive, session, workflow."""
    # Create candidate user
    candidate = User(
        email="candidate_full@test.com",
        username="candidate_full",
        password_hash=get_password_hash("testpass"),
        first_name="Alice",
        last_name="Candidate",
        user_type="student",
        is_active=True,
    )
    db_session.add(candidate)
    await db_session.flush()

    # Create HR user + profile
    hr_user = User(
        email="hr_full@test.com",
        username="hr_full",
        password_hash=get_password_hash("testpass"),
        first_name="Bob",
        last_name="Recruiter",
        user_type="hr",
        is_active=True,
    )
    db_session.add(hr_user)
    await db_session.flush()

    hr_profile = HRProfile(
        user_id=hr_user.id,
        company_name="TestCorp",
    )
    db_session.add(hr_profile)
    await db_session.flush()

    # Create job drive
    job_drive = JobDrive(
        hr_id=hr_profile.id,
        title="Senior Python Engineer",
        job_role="Backend Engineer",
        skills_required="python, database, system_design, testing",
    )
    db_session.add(job_drive)
    await db_session.flush()

    # Create interview session (completed with scores)
    session = InterviewSession(
        candidate_id=candidate.id,
        job_drive_id=job_drive.id,
        session_type="technical",
        status="completed",
        overall_score=7.5,
        skill_matrix={
            "python": 8.5,
            "database": 6.0,
            "system_design": 5.0,
            "testing": 7.0,
        },
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()

    # Create candidate workflow in "in_progress" state
    workflow = CandidateWorkflow(
        candidate_id=candidate.id,
        job_drive_id=job_drive.id,
        current_state="in_progress",
    )
    db_session.add(workflow)
    await db_session.commit()

    return {
        "candidate": candidate,
        "hr_user": hr_user,
        "hr_profile": hr_profile,
        "job_drive": job_drive,
        "session": session,
        "workflow": workflow,
    }


@pytest.mark.asyncio
async def test_memory_merge_creates_longitudinal_profile(db_session, full_session_setup):
    """merge_session_skills() creates/updates LongitudinalProfile with correct data."""
    setup = full_session_setup
    candidate_id = setup["candidate"].id
    session_id = setup["session"].id

    skill_scores = {"python": 8.5, "database": 6.0, "system_design": 5.0}

    profile = await memory_service.merge_session_skills(
        candidate_id=candidate_id,
        session_id=session_id,
        skill_scores=skill_scores,
        db=db_session,
    )

    assert profile is not None
    assert isinstance(profile, LongitudinalProfile)
    assert profile.candidate_id == candidate_id
    assert profile.skill_averages is not None
    assert "python" in profile.skill_averages
    assert profile.skill_averages["python"] == 8.5
    assert profile.skill_history is not None
    assert len(profile.skill_history["python"]) == 1
    assert profile.skill_history["python"][0]["session_id"] == session_id


@pytest.mark.asyncio
async def test_coaching_plan_generated_with_skill_gaps(db_session, full_session_setup):
    """generate_coaching_plan() creates CoachingPlan with identified skill_gaps."""
    setup = full_session_setup
    candidate_id = setup["candidate"].id
    session_id = setup["session"].id

    evaluation_report = {
        "overall_score": 7.5,
        "strengths": ["python"],
        "weaknesses": ["system_design"],
    }
    skill_matrix = {
        "python": 8.5,
        "database": 6.0,
        "system_design": 5.0,
        "testing": 7.0,
    }

    plan = await coaching_service.generate_coaching_plan(
        session_id=session_id,
        candidate_id=candidate_id,
        evaluation_report=evaluation_report,
        skill_matrix=skill_matrix,
        passing_threshold=6.0,
        db=db_session,
    )

    assert plan is not None
    assert isinstance(plan, CoachingPlan)
    assert plan.session_id == session_id
    assert plan.candidate_id == candidate_id
    assert plan.skill_gaps is not None
    # system_design (5.0) is below threshold 6.0 and below 8.0
    gap_skills = [g["skill"] for g in plan.skill_gaps]
    assert "system_design" in gap_skills
    # python (8.5) should be excluded (>= 8.0)
    assert "python" not in gap_skills


@pytest.mark.asyncio
async def test_match_score_computed_in_valid_range(db_session, full_session_setup):
    """compute_match_score() creates MatchResult with score in [0, 100]."""
    setup = full_session_setup
    session_id = setup["session"].id

    result = await matching_service.compute_match_score(
        session_id=session_id,
        db=db_session,
    )

    assert result is not None
    assert isinstance(result, MatchResult)
    assert result.match_score is not None
    assert 0.0 <= result.match_score <= 100.0
    assert result.session_id == session_id
    assert result.candidate_id == setup["candidate"].id
    assert result.job_drive_id == setup["job_drive"].id


@pytest.mark.asyncio
async def test_orchestrator_transition_to_evaluated(db_session, full_session_setup):
    """transition(trigger='complete') moves workflow from in_progress to evaluated."""
    setup = full_session_setup
    orchestrator = OrchestratorService()

    workflow = await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )

    assert workflow.current_state == "evaluated"
    assert workflow.transition_history is not None
    assert len(workflow.transition_history) == 1
    assert workflow.transition_history[0]["from_state"] == "in_progress"
    assert workflow.transition_history[0]["to_state"] == "evaluated"


@pytest.mark.asyncio
async def test_all_operations_produce_trace_entries(db_session, full_session_setup):
    """Every service operation produces TraceEntry records in the database."""
    setup = full_session_setup
    candidate_id = setup["candidate"].id
    session_id = setup["session"].id

    # Run memory merge
    await memory_service.merge_session_skills(
        candidate_id=candidate_id,
        session_id=session_id,
        skill_scores={"python": 8.5},
        db=db_session,
    )

    # Run match score
    await matching_service.compute_match_score(
        session_id=session_id,
        db=db_session,
    )

    # Run orchestrator transition
    orchestrator = OrchestratorService()
    await orchestrator.transition(
        candidate_id=candidate_id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )

    # Query all trace entries
    stmt = select(TraceEntry)
    result = await db_session.execute(stmt)
    entries = result.scalars().all()

    assert len(entries) > 0

    # Verify we have entries from different agents
    agent_names = {e.agent_name for e in entries}
    assert "memory_agent" in agent_names
    assert "matching_engine" in agent_names
    assert "orchestrator" in agent_names
