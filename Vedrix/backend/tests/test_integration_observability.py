"""
Integration tests for the Observability Layer.

Tests append-only recording, role-based redaction, chronological export,
and runaway loop detection against a real SQLite test database.
"""
import pytest
from datetime import datetime, timezone

from app.models.trace_entry import TraceEntry, TraceEntryCreate
from app.services.observability_service import (
    ObservabilityService,
    is_session_paused,
    clear_session_pause,
    _session_pause_flags,
    RUNAWAY_LOOP_THRESHOLD,
)

from sqlmodel import select


@pytest.fixture
async def obs_service(db_session):
    """Create an ObservabilityService instance with the test DB session."""
    return ObservabilityService(db_session)


@pytest.fixture(autouse=True)
def clear_pause_flags():
    """Clear all session pause flags before and after each test."""
    _session_pause_flags.clear()
    yield
    _session_pause_flags.clear()


@pytest.mark.asyncio
async def test_record_creates_trace_entry(db_session, obs_service):
    """record() persists a new TraceEntry to the database."""
    entry_data = TraceEntryCreate(
        agent_name="test_agent",
        action_type="test_action",
        session_id=1,
        input_summary="Test input",
        output_summary="Test output",
        reasoning_summary="Test reasoning",
        confidence_score=0.95,
        raw_input={"key": "value"},
        raw_output={"result": "success"},
        duration_ms=150,
    )

    result = await obs_service.record(entry_data)

    assert result is not None
    assert result.id is not None
    assert result.agent_name == "test_agent"
    assert result.action_type == "test_action"
    assert result.session_id == 1
    assert result.input_summary == "Test input"
    assert result.timestamp is not None


@pytest.mark.asyncio
async def test_record_multiple_entries(db_session, obs_service):
    """Multiple record() calls create separate entries."""
    for i in range(5):
        await obs_service.record(TraceEntryCreate(
            agent_name=f"agent_{i}",
            action_type="action",
            session_id=100,
            input_summary=f"Input {i}",
            output_summary=f"Output {i}",
        ))

    stmt = select(TraceEntry).where(TraceEntry.session_id == 100)
    result = await db_session.execute(stmt)
    entries = result.scalars().all()

    assert len(entries) == 5


@pytest.mark.asyncio
async def test_query_admin_sees_raw_fields(db_session, obs_service):
    """query(requester_role='admin') returns raw_input and raw_output."""
    await obs_service.record(TraceEntryCreate(
        agent_name="qa_agent",
        action_type="bias_check",
        session_id=200,
        input_summary="Checking bias",
        raw_input={"transcript": "sensitive data"},
        raw_output={"bias_score": 0.1},
    ))

    entries = await obs_service.query(
        session_id=200,
        requester_role="admin",
    )

    assert len(entries) == 1
    assert entries[0].raw_input is not None
    assert entries[0].raw_input == {"transcript": "sensitive data"}
    assert entries[0].raw_output is not None
    assert entries[0].raw_output == {"bias_score": 0.1}


@pytest.mark.asyncio
async def test_query_hr_redacts_raw_fields(db_session, obs_service):
    """query(requester_role='hr') redacts raw_input and raw_output to None."""
    await obs_service.record(TraceEntryCreate(
        agent_name="qa_agent",
        action_type="bias_check",
        session_id=201,
        input_summary="Checking bias",
        raw_input={"transcript": "sensitive data"},
        raw_output={"bias_score": 0.1},
    ))

    entries = await obs_service.query(
        session_id=201,
        requester_role="hr",
    )

    assert len(entries) == 1
    assert entries[0].raw_input is None
    assert entries[0].raw_output is None
    # Non-sensitive fields should still be present
    assert entries[0].input_summary == "Checking bias"
    assert entries[0].agent_name == "qa_agent"


@pytest.mark.asyncio
async def test_export_session_chronological_order(db_session, obs_service):
    """export_session() returns entries in chronological order."""
    import asyncio

    session_id = 300

    # Create entries with slight time gaps to ensure ordering
    for i in range(5):
        await obs_service.record(TraceEntryCreate(
            agent_name="test_agent",
            action_type=f"action_{i}",
            session_id=session_id,
            input_summary=f"Step {i}",
        ))
        # Small delay to ensure distinct timestamps
        await asyncio.sleep(0.01)

    exported = await obs_service.export_session(session_id)

    assert len(exported) == 5
    # Verify chronological order
    for i in range(len(exported) - 1):
        assert exported[i]["timestamp"] <= exported[i + 1]["timestamp"]

    # Verify all entries belong to the correct session
    for entry in exported:
        assert entry["session_id"] == session_id


@pytest.mark.asyncio
async def test_export_session_includes_raw_fields(db_session, obs_service):
    """export_session() is admin-level and includes raw fields."""
    session_id = 301

    await obs_service.record(TraceEntryCreate(
        agent_name="memory_agent",
        action_type="merge_skills",
        session_id=session_id,
        raw_input={"skills": {"python": 8.0}},
        raw_output={"profile_updated": True},
    ))

    exported = await obs_service.export_session(session_id)

    assert len(exported) == 1
    assert exported[0]["raw_input"] is not None
    assert exported[0]["raw_output"] is not None


@pytest.mark.asyncio
async def test_runaway_loop_detection_pauses_session(db_session):
    """Inserting >10,000 entries triggers is_session_paused() to return True."""
    session_id = 999

    # We need to insert entries exceeding the threshold.
    # For test performance, we'll insert in bulk using direct DB operations.
    entries = []
    for i in range(RUNAWAY_LOOP_THRESHOLD + 1):
        entry = TraceEntry(
            agent_name="runaway_agent",
            action_type="loop_action",
            session_id=session_id,
            input_summary=f"Iteration {i}",
            timestamp=datetime.now(timezone.utc),
        )
        entries.append(entry)

    # Bulk insert for performance
    db_session.add_all(entries)
    await db_session.commit()

    # Verify the count
    from sqlalchemy import func
    stmt = select(func.count(TraceEntry.id)).where(TraceEntry.session_id == session_id)
    result = await db_session.execute(stmt)
    count = result.scalar_one()
    assert count >= RUNAWAY_LOOP_THRESHOLD

    # Now trigger the runaway check via a new record
    obs_service = ObservabilityService(db_session)
    await obs_service.record(TraceEntryCreate(
        agent_name="runaway_agent",
        action_type="trigger_check",
        session_id=session_id,
    ))

    # Verify session is paused
    assert is_session_paused(session_id) is True


@pytest.mark.asyncio
async def test_clear_session_pause_resets_flag(db_session):
    """clear_session_pause() resets the pause flag for a session."""
    session_id = 888

    # Manually set the pause flag
    _session_pause_flags[session_id] = True
    assert is_session_paused(session_id) is True

    # Clear it
    clear_session_pause(session_id)
    assert is_session_paused(session_id) is False


@pytest.mark.asyncio
async def test_query_filters_by_agent_name(db_session, obs_service):
    """query() correctly filters by agent_name."""
    session_id = 400

    await obs_service.record(TraceEntryCreate(
        agent_name="memory_agent",
        action_type="merge",
        session_id=session_id,
    ))
    await obs_service.record(TraceEntryCreate(
        agent_name="proctor_agent",
        action_type="detect",
        session_id=session_id,
    ))

    memory_entries = await obs_service.query(
        agent_name="memory_agent",
        session_id=session_id,
        requester_role="admin",
    )

    assert len(memory_entries) == 1
    assert memory_entries[0].agent_name == "memory_agent"


@pytest.mark.asyncio
async def test_query_filters_by_time_range(db_session, obs_service):
    """query() correctly filters by start_time and end_time."""
    import asyncio

    session_id = 500
    now = datetime.now(timezone.utc)

    await obs_service.record(TraceEntryCreate(
        agent_name="test_agent",
        action_type="early_action",
        session_id=session_id,
    ))

    await asyncio.sleep(0.05)
    mid_time = datetime.now(timezone.utc)
    await asyncio.sleep(0.05)

    await obs_service.record(TraceEntryCreate(
        agent_name="test_agent",
        action_type="late_action",
        session_id=session_id,
    ))

    # Query only entries after mid_time
    entries = await obs_service.query(
        session_id=session_id,
        start_time=mid_time,
        requester_role="admin",
    )

    assert len(entries) == 1
    assert entries[0].action_type == "late_action"
