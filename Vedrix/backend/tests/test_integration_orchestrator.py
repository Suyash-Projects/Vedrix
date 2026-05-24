"""
Integration tests for the Orchestrator state machine.

Tests the full workflow lifecycle: invited → scheduled → in_progress →
evaluated → shortlisted → decided. Also tests invalid transitions,
bulk operations, and trace entry generation.
"""
import pytest
from datetime import datetime, timezone

from app.models.user import User
from app.models.profile import HRProfile
from app.models.interview import JobDrive
from app.models.candidate_workflow import CandidateWorkflow
from app.models.trace_entry import TraceEntry
from app.services.orchestrator_service import (
    OrchestratorService,
    InvalidTransitionError,
    WORKFLOW_TRANSITIONS,
)
from app.core.security import get_password_hash

from sqlmodel import select


@pytest.fixture
async def orchestrator_setup(db_session):
    """Create test environment for orchestrator tests."""
    # Create candidate
    candidate = User(
        email="candidate_orch@test.com",
        username="candidate_orch",
        password_hash=get_password_hash("testpass"),
        first_name="Frank",
        last_name="Workflow",
        user_type="student",
        is_active=True,
    )
    db_session.add(candidate)
    await db_session.flush()

    # Create HR user + profile
    hr_user = User(
        email="hr_orch@test.com",
        username="hr_orch",
        password_hash=get_password_hash("testpass"),
        first_name="Grace",
        last_name="HR",
        user_type="hr",
        is_active=True,
    )
    db_session.add(hr_user)
    await db_session.flush()

    hr_profile = HRProfile(
        user_id=hr_user.id,
        company_name="OrchCorp",
    )
    db_session.add(hr_profile)
    await db_session.flush()

    # Create job drive
    job_drive = JobDrive(
        hr_id=hr_profile.id,
        title="Full Stack Developer",
        job_role="Full Stack Developer",
        skills_required="python, react, database",
    )
    db_session.add(job_drive)
    await db_session.flush()

    # Create workflow in "invited" state
    workflow = CandidateWorkflow(
        candidate_id=candidate.id,
        job_drive_id=job_drive.id,
        current_state="invited",
    )
    db_session.add(workflow)
    await db_session.commit()

    return {
        "candidate": candidate,
        "hr_user": hr_user,
        "job_drive": job_drive,
        "workflow": workflow,
    }


@pytest.fixture
def orchestrator():
    """Create an OrchestratorService instance."""
    return OrchestratorService()


@pytest.mark.asyncio
async def test_transition_invited_to_scheduled(db_session, orchestrator_setup, orchestrator):
    """transition(trigger='schedule') moves from 'invited' to 'scheduled'."""
    setup = orchestrator_setup

    workflow = await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )

    assert workflow.current_state == "scheduled"


@pytest.mark.asyncio
async def test_transition_scheduled_to_in_progress(db_session, orchestrator_setup, orchestrator):
    """transition(trigger='start') moves from 'scheduled' to 'in_progress'."""
    setup = orchestrator_setup

    # First: invited → scheduled
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )

    # Then: scheduled → in_progress
    workflow = await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="start",
        db=db_session,
    )

    assert workflow.current_state == "in_progress"


@pytest.mark.asyncio
async def test_transition_in_progress_to_evaluated(db_session, orchestrator_setup, orchestrator):
    """transition(trigger='complete') moves from 'in_progress' to 'evaluated'."""
    setup = orchestrator_setup

    # invited → scheduled → in_progress
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="start",
        db=db_session,
    )

    # in_progress → evaluated
    workflow = await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )

    assert workflow.current_state == "evaluated"


@pytest.mark.asyncio
async def test_transition_evaluated_to_shortlisted(db_session, orchestrator_setup, orchestrator):
    """transition(trigger='shortlist') moves from 'evaluated' to 'shortlisted'."""
    setup = orchestrator_setup

    # Walk through: invited → scheduled → in_progress → evaluated
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="start",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )

    # evaluated → shortlisted
    workflow = await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="shortlist",
        db=db_session,
    )

    assert workflow.current_state == "shortlisted"


@pytest.mark.asyncio
async def test_transition_shortlisted_to_decided_hire(db_session, orchestrator_setup, orchestrator):
    """transition(trigger='hire') moves from 'shortlisted' to 'decided' with decision='hired'."""
    setup = orchestrator_setup

    # Walk through full pipeline
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="start",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="shortlist",
        db=db_session,
    )

    # shortlisted → decided (hire)
    workflow = await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="hire",
        actor_id=setup["hr_user"].id,
        db=db_session,
    )

    assert workflow.current_state == "decided"
    assert workflow.decision == "hired"
    assert workflow.decided_by == setup["hr_user"].id
    assert workflow.decided_at is not None


@pytest.mark.asyncio
async def test_transition_from_decided_raises_error(db_session, orchestrator_setup, orchestrator):
    """transition(trigger='reject') on 'decided' state raises InvalidTransitionError."""
    setup = orchestrator_setup

    # Walk to decided state
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="start",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="shortlist",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="hire",
        db=db_session,
    )

    # Attempt transition from "decided" — should raise
    with pytest.raises(InvalidTransitionError) as exc_info:
        await orchestrator.transition(
            candidate_id=setup["candidate"].id,
            job_drive_id=setup["job_drive"].id,
            trigger="reject",
            db=db_session,
        )

    assert exc_info.value.current_state == "decided"
    assert exc_info.value.trigger == "reject"


@pytest.mark.asyncio
async def test_invalid_trigger_raises_error(db_session, orchestrator_setup, orchestrator):
    """An invalid trigger for the current state raises InvalidTransitionError."""
    setup = orchestrator_setup

    # "invited" state does not accept "complete" trigger
    with pytest.raises(InvalidTransitionError) as exc_info:
        await orchestrator.transition(
            candidate_id=setup["candidate"].id,
            job_drive_id=setup["job_drive"].id,
            trigger="complete",
            db=db_session,
        )

    assert exc_info.value.current_state == "invited"
    assert exc_info.value.trigger == "complete"


@pytest.mark.asyncio
async def test_bulk_transition_independent(db_session, orchestrator):
    """bulk_transition() applies transitions independently to each candidate."""
    # Create multiple candidates with workflows
    candidates = []
    job_drive_id = None

    # Create HR + drive
    hr_user = User(
        email="hr_bulk@test.com",
        username="hr_bulk",
        password_hash=get_password_hash("testpass"),
        first_name="Bulk",
        last_name="HR",
        user_type="hr",
        is_active=True,
    )
    db_session.add(hr_user)
    await db_session.flush()

    hr_profile = HRProfile(user_id=hr_user.id, company_name="BulkCorp")
    db_session.add(hr_profile)
    await db_session.flush()

    job_drive = JobDrive(
        hr_id=hr_profile.id,
        title="Bulk Test Drive",
        job_role="Engineer",
        skills_required="python",
    )
    db_session.add(job_drive)
    await db_session.flush()
    job_drive_id = job_drive.id

    # Create 3 candidates in "evaluated" state
    for i in range(3):
        candidate = User(
            email=f"bulk_candidate_{i}@test.com",
            username=f"bulk_candidate_{i}",
            password_hash=get_password_hash("testpass"),
            first_name=f"Bulk{i}",
            last_name="Candidate",
            user_type="student",
            is_active=True,
        )
        db_session.add(candidate)
        await db_session.flush()
        candidates.append(candidate)

        workflow = CandidateWorkflow(
            candidate_id=candidate.id,
            job_drive_id=job_drive_id,
            current_state="evaluated",
        )
        db_session.add(workflow)

    await db_session.commit()

    # Bulk transition: shortlist all
    candidate_ids = [c.id for c in candidates]
    results = await orchestrator.bulk_transition(
        candidate_ids=candidate_ids,
        job_drive_id=job_drive_id,
        trigger="shortlist",
        actor_id=hr_user.id,
        db=db_session,
    )

    assert len(results) == 3
    for result in results:
        assert result.success is True
        assert result.new_state == "shortlisted"


@pytest.mark.asyncio
async def test_bulk_transition_partial_failure(db_session, orchestrator):
    """bulk_transition() handles individual failures without blocking others."""
    # Create HR + drive
    hr_user = User(
        email="hr_partial@test.com",
        username="hr_partial",
        password_hash=get_password_hash("testpass"),
        first_name="Partial",
        last_name="HR",
        user_type="hr",
        is_active=True,
    )
    db_session.add(hr_user)
    await db_session.flush()

    hr_profile = HRProfile(user_id=hr_user.id, company_name="PartialCorp")
    db_session.add(hr_profile)
    await db_session.flush()

    job_drive = JobDrive(
        hr_id=hr_profile.id,
        title="Partial Test Drive",
        job_role="Engineer",
        skills_required="python",
    )
    db_session.add(job_drive)
    await db_session.flush()

    # Candidate 1: in "evaluated" (valid for shortlist)
    candidate1 = User(
        email="partial_c1@test.com",
        username="partial_c1",
        password_hash=get_password_hash("testpass"),
        first_name="C1",
        last_name="Test",
        user_type="student",
        is_active=True,
    )
    db_session.add(candidate1)
    await db_session.flush()

    workflow1 = CandidateWorkflow(
        candidate_id=candidate1.id,
        job_drive_id=job_drive.id,
        current_state="evaluated",
    )
    db_session.add(workflow1)

    # Candidate 2: in "invited" (invalid for shortlist)
    candidate2 = User(
        email="partial_c2@test.com",
        username="partial_c2",
        password_hash=get_password_hash("testpass"),
        first_name="C2",
        last_name="Test",
        user_type="student",
        is_active=True,
    )
    db_session.add(candidate2)
    await db_session.flush()

    workflow2 = CandidateWorkflow(
        candidate_id=candidate2.id,
        job_drive_id=job_drive.id,
        current_state="invited",
    )
    db_session.add(workflow2)
    await db_session.commit()

    results = await orchestrator.bulk_transition(
        candidate_ids=[candidate1.id, candidate2.id],
        job_drive_id=job_drive.id,
        trigger="shortlist",
        actor_id=hr_user.id,
        db=db_session,
    )

    assert len(results) == 2

    # Candidate 1 should succeed
    result1 = next(r for r in results if r.candidate_id == candidate1.id)
    assert result1.success is True
    assert result1.new_state == "shortlisted"

    # Candidate 2 should fail (invalid transition)
    result2 = next(r for r in results if r.candidate_id == candidate2.id)
    assert result2.success is False
    assert result2.error is not None


@pytest.mark.asyncio
async def test_every_transition_produces_trace_entry(db_session, orchestrator_setup, orchestrator):
    """Every state transition produces a TraceEntry in the database."""
    setup = orchestrator_setup

    # Clear existing trace entries
    from sqlalchemy import text
    await db_session.execute(text("DELETE FROM trace_entries"))
    await db_session.commit()

    # Perform transitions
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="start",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )

    # Query trace entries for the orchestrator
    stmt = select(TraceEntry).where(
        TraceEntry.agent_name == "orchestrator",
        TraceEntry.action_type == "state_transition",
    )
    result = await db_session.execute(stmt)
    entries = result.scalars().all()

    # Each transition should produce at least one trace entry
    # (the @trace_agent_action decorator also records, so we may have more)
    assert len(entries) >= 3

    # Verify entries contain transition details
    output_summaries = [e.output_summary for e in entries]
    assert any("scheduled" in (s or "") for s in output_summaries)
    assert any("in_progress" in (s or "") for s in output_summaries)
    assert any("evaluated" in (s or "") for s in output_summaries)


@pytest.mark.asyncio
async def test_transition_history_accumulates(db_session, orchestrator_setup, orchestrator):
    """Each transition appends to the workflow's transition_history."""
    setup = orchestrator_setup

    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="start",
        db=db_session,
    )
    workflow = await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )

    assert workflow.transition_history is not None
    assert len(workflow.transition_history) == 3

    # Verify order
    assert workflow.transition_history[0]["from_state"] == "invited"
    assert workflow.transition_history[0]["to_state"] == "scheduled"
    assert workflow.transition_history[1]["from_state"] == "scheduled"
    assert workflow.transition_history[1]["to_state"] == "in_progress"
    assert workflow.transition_history[2]["from_state"] == "in_progress"
    assert workflow.transition_history[2]["to_state"] == "evaluated"


@pytest.mark.asyncio
async def test_decided_state_with_reject(db_session, orchestrator_setup, orchestrator):
    """transition(trigger='reject') from 'evaluated' sets decision='rejected'."""
    setup = orchestrator_setup

    # Walk to evaluated
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="schedule",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="start",
        db=db_session,
    )
    await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="complete",
        db=db_session,
    )

    # evaluated → decided (reject)
    workflow = await orchestrator.transition(
        candidate_id=setup["candidate"].id,
        job_drive_id=setup["job_drive"].id,
        trigger="reject",
        actor_id=setup["hr_user"].id,
        db=db_session,
    )

    assert workflow.current_state == "decided"
    assert workflow.decision == "rejected"
    assert workflow.decided_by == setup["hr_user"].id
