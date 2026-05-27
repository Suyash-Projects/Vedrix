"""
Integration tests for the Proctor Agent service.

Tests browser event handling, consent enforcement, session finalization,
and typing cadence anomaly detection against a real SQLite test database.
"""
import pytest
from datetime import datetime, timezone

from app.models.user import User
from app.models.profile import HRProfile
from app.models.interview import JobDrive, InterviewSession
from app.models.violation_record import ViolationRecord
from app.services.proctor_service import proctor_service
from app.core.security import get_password_hash

from sqlmodel import select


@pytest.fixture
async def proctor_setup(db_session):
    """Create test environment for proctor tests: user, job drive, session."""
    candidate = User(
        email="candidate_proctor@test.com",
        username="candidate_proctor",
        password_hash=get_password_hash("testpass"),
        first_name="Charlie",
        last_name="Proctor",
        user_type="student",
        is_active=True,
    )
    db_session.add(candidate)
    await db_session.flush()

    hr_user = User(
        email="hr_proctor@test.com",
        username="hr_proctor",
        password_hash=get_password_hash("testpass"),
        first_name="Diana",
        last_name="HR",
        user_type="hr",
        is_active=True,
    )
    db_session.add(hr_user)
    await db_session.flush()

    hr_profile = HRProfile(
        user_id=hr_user.id,
        company_name="ProctorCorp",
    )
    db_session.add(hr_profile)
    await db_session.flush()

    job_drive = JobDrive(
        hr_id=hr_profile.id,
        title="QA Engineer",
        job_role="QA Engineer",
        skills_required="testing, automation",
    )
    db_session.add(job_drive)
    await db_session.flush()

    session = InterviewSession(
        candidate_id=candidate.id,
        job_drive_id=job_drive.id,
        session_type="technical",
        status="in_progress",
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()

    return {
        "candidate": candidate,
        "session": session,
        "job_drive": job_drive,
    }


@pytest.mark.asyncio
async def test_tab_switch_creates_violation_record(db_session, proctor_setup):
    """handle_browser_event() with tab_switch creates a ViolationRecord."""
    setup = proctor_setup
    session_id = setup["session"].id

    violation = await proctor_service.handle_browser_event(
        session_id=session_id,
        event_type="tab_switch",
        payload={"target_url": "https://google.com"},
        session_status="in_progress",
        consent_granted=True,
        db=db_session,
    )

    assert violation is not None
    assert isinstance(violation, ViolationRecord)
    assert violation.session_id == session_id
    assert violation.violation_type == "tab_switch"
    assert violation.consent_granted is True
    assert violation.detected_at is not None


@pytest.mark.asyncio
async def test_multiple_tab_switches_create_multiple_records(db_session, proctor_setup):
    """Multiple tab_switch events create separate ViolationRecords."""
    setup = proctor_setup
    session_id = setup["session"].id

    for i in range(3):
        await proctor_service.handle_browser_event(
            session_id=session_id,
            event_type="tab_switch",
            payload={"switch_number": i + 1},
            session_status="in_progress",
            consent_granted=True,
            db=db_session,
        )

    stmt = select(ViolationRecord).where(
        ViolationRecord.session_id == session_id,
        ViolationRecord.violation_type == "tab_switch",
    )
    result = await db_session.execute(stmt)
    violations = result.scalars().all()

    assert len(violations) == 3


@pytest.mark.asyncio
async def test_no_record_when_session_not_in_progress(db_session, proctor_setup):
    """No ViolationRecord created when session_status != 'in_progress'."""
    setup = proctor_setup
    session_id = setup["session"].id

    violation = await proctor_service.handle_browser_event(
        session_id=session_id,
        event_type="tab_switch",
        payload={"target_url": "https://google.com"},
        session_status="completed",
        consent_granted=True,
        db=db_session,
    )

    assert violation is None

    # Verify no records in DB
    stmt = select(ViolationRecord).where(ViolationRecord.session_id == session_id)
    result = await db_session.execute(stmt)
    violations = result.scalars().all()
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_no_paste_record_without_consent(db_session, proctor_setup):
    """Without consent, paste events are not recorded (only tab_switch allowed)."""
    setup = proctor_setup
    session_id = setup["session"].id

    violation = await proctor_service.handle_browser_event(
        session_id=session_id,
        event_type="paste_detected",
        payload={"character_count": 150},
        session_status="in_progress",
        consent_granted=False,
        db=db_session,
    )

    assert violation is None


@pytest.mark.asyncio
async def test_tab_switch_allowed_without_consent(db_session, proctor_setup):
    """Tab switch events ARE recorded even without consent."""
    setup = proctor_setup
    session_id = setup["session"].id

    violation = await proctor_service.handle_browser_event(
        session_id=session_id,
        event_type="tab_switch",
        payload={"target_url": "https://stackoverflow.com"},
        session_status="in_progress",
        consent_granted=False,
        db=db_session,
    )

    assert violation is not None
    assert violation.violation_type == "tab_switch"
    assert violation.consent_granted is False


@pytest.mark.asyncio
async def test_finalize_session_populates_evidence_log(db_session, proctor_setup):
    """finalize_session() attaches violations to the session's evidence_log."""
    setup = proctor_setup
    session_id = setup["session"].id

    # Create some violations first
    await proctor_service.handle_browser_event(
        session_id=session_id,
        event_type="tab_switch",
        payload={"target_url": "https://google.com"},
        session_status="in_progress",
        consent_granted=True,
        db=db_session,
    )
    await proctor_service.handle_browser_event(
        session_id=session_id,
        event_type="paste_detected",
        payload={"character_count": 200},
        session_status="in_progress",
        consent_granted=True,
        db=db_session,
    )

    # Finalize the session
    await proctor_service.finalize_session(
        session_id=session_id,
        db=db_session,
    )

    # Verify evidence_log is populated on the session
    stmt = select(InterviewSession).where(InterviewSession.id == session_id)
    result = await db_session.execute(stmt)
    session_rec = result.scalars().first()

    assert session_rec.evidence_log is not None
    assert "violations" in session_rec.evidence_log
    assert session_rec.evidence_log["violation_count"] == 2
    assert "finalized_at" in session_rec.evidence_log

    # Verify violation details
    violations_log = session_rec.evidence_log["violations"]
    assert len(violations_log) == 2
    violation_types = [v["violation_type"] for v in violations_log]
    assert "tab_switch" in violation_types
    assert "paste_detected" in violation_types


@pytest.mark.asyncio
async def test_analyze_typing_cadence_anomalous(db_session, proctor_setup):
    """analyze_typing_cadence() flags anomalous typing (>3 std devs from baseline)."""
    setup = proctor_setup
    session_id = setup["session"].id

    # Baseline: mean=100ms, std=10ms
    # Anomalous sample: intervals averaging ~200ms (10 std devs away)
    anomalous_timestamps = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]  # 200ms intervals

    violation = await proctor_service.analyze_typing_cadence(
        keystroke_timestamps=anomalous_timestamps,
        baseline_mean=0.1,   # 100ms baseline mean
        baseline_std=0.01,   # 10ms baseline std
        db=db_session,
        session_id=session_id,
        consent_granted=True,
    )

    assert violation is not None
    assert isinstance(violation, ViolationRecord)
    assert violation.violation_type == "anomalous_typing"
    assert violation.payload is not None
    assert violation.payload["deviation_std_devs"] > 3.0


@pytest.mark.asyncio
async def test_analyze_typing_cadence_normal(db_session, proctor_setup):
    """analyze_typing_cadence() returns None for normal typing patterns."""
    setup = proctor_setup
    session_id = setup["session"].id

    # Normal sample: intervals averaging ~100ms (within 1 std dev of baseline)
    normal_timestamps = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]  # 100ms intervals

    violation = await proctor_service.analyze_typing_cadence(
        keystroke_timestamps=normal_timestamps,
        baseline_mean=0.1,   # 100ms baseline mean
        baseline_std=0.02,   # 20ms baseline std
        db=db_session,
        session_id=session_id,
        consent_granted=True,
    )

    assert violation is None


@pytest.mark.asyncio
async def test_multimodal_video_proctoring_events(db_session, proctor_setup):
    """Test that multiple_faces, no_face, and gaze_deviation events are registered as violations."""
    setup = proctor_setup
    session_id = setup["session"].id

    for event in ("multiple_faces", "no_face", "gaze_deviation"):
        violation = await proctor_service.handle_browser_event(
            session_id=session_id,
            event_type=event,
            payload={"confidence": 0.88, "duration_seconds": 1.5},
            session_status="in_progress",
            consent_granted=True,
            db=db_session,
        )
        assert violation is not None
        assert violation.violation_type == event
        assert violation.payload["confidence"] == 0.88
