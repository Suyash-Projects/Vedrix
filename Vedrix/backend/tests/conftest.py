"""
Pytest configuration and fixtures for Vedrix backend E2E tests.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from main import app
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.profile import StudentProfile, HRProfile
from app.models.interview import JobDrive, InterviewSession, DriveInviteToken, ScenarioTemplate


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    return engine


@pytest.fixture(scope="session")
async def test_session_factory(test_engine):
    """Create session factory for tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    # Cleanup: drop all tables after test session
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture
async def db_session(test_session_factory):
    """Create a fresh database session for each test."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()
        # Clean up test data after each test
        await session.execute(__import__('sqlalchemy').text("DELETE FROM interview_session"))
        await session.execute(__import__('sqlalchemy').text("DELETE FROM drive_invite_token"))
        await session.execute(__import__('sqlalchemy').text("DELETE FROM job_drive"))
        await session.execute(__import__('sqlalchemy').text("DELETE FROM hr_profile"))
        await session.execute(__import__('sqlalchemy').text("DELETE FROM student_profile"))
        await session.execute(__import__('sqlalchemy').text("DELETE FROM user"))
        await session.commit()


@pytest.fixture
async def client(db_session):
    """Create an async test client with overridden DB dependency."""
    from app.db.session import get_session

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session):
    """Create a test student user."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=get_password_hash("testpass123"),
        first_name="Test",
        last_name="User",
        user_type="student",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session):
    """Create a test admin user."""
    user = User(
        email="admin@example.com",
        username="adminuser",
        password_hash=get_password_hash("adminpass123"),
        first_name="Admin",
        last_name="User",
        user_type="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Auth headers for test student user."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """Auth headers for test admin user."""
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_groq_stt():
    """Mock Groq Whisper STT to return test transcript."""
    with patch('app.services.voice_service.Groq') as mock:
        instance = MagicMock()
        result = MagicMock()
        result.text = "I've been working as a Python developer for 3 years."
        instance.audio.transcriptions.create.return_value = result
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_groq_llm():
    """Mock Groq LLM for interview engine."""
    with patch('app.services.interview_engine.providers.ChatOpenAI') as mock:
        instance = AsyncMock()
        response = MagicMock()
        response.content = '{"id": 1, "question": "Tell me about your Python experience", "category": "technical", "difficulty": "medium", "time_limit": 120, "skill_tested": "python", "follow_up_topic": "frameworks"}'
        instance.ainvoke = AsyncMock(return_value=response)
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_strong_llm():
    """Mock strong LLM for evaluation."""
    with patch('app.services.interview_engine.providers.ChatOpenAI') as mock:
        instance = AsyncMock()
        response = MagicMock()
        response.content = '{"score": 7.5, "metrics": {"accuracy": 8.0, "clarity": 7.5, "depth": 7.0, "communication": 7.5}, "feedback": "Good technical answer", "topic": "python", "skill_category": "technical", "should_deep_dive": true, "is_coding_challenge": false, "needs_easier": false, "low_effort": false, "skill_identified": "python"}'
        instance.ainvoke = AsyncMock(return_value=response)
        mock.return_value = instance
        yield mock


@pytest.fixture
def sample_interview_state():
    """Sample interview state for testing."""
    return {
        "messages": [],
        "resume_text": "Python developer with 3 years experience in Django and FastAPI.",
        "job_role": "Python Backend Engineer",
        "current_question_index": 0,
        "max_questions": 5,
        "interview_complete": False,
        "completion_reason": None,
        "current_phase": "greeting",
        "phase_transition": False,
        "previous_phase": None,
        "difficulty": "medium",
        "latest_score": 0.0,
        "metrics": {"accuracy": 0, "clarity": 0, "depth": 0, "communication": 0},
        "avg_score": 0.0,
        "covered_skills": [],
        "skills_to_cover": ["programming", "database", "backend"],
        "pending_skills": ["programming", "database", "backend"],
        "skill_coverage_percentage": 0.0,
        "topic_scores": {},
        "topic_strengths": {},
        "total_responses": 0,
        "low_quality_count": 0,
        "high_quality_count": 0,
        "interviewer_mode": "ai",
        "hr_instructions": None,
        "last_evaluation": None,
        "next_question": None,
        "code_snippet": None,
        "code_language": None,
        "is_coding_mode": False,
        "follow_up_requested": False,
        "previous_topic": None,
    }


@pytest.fixture
def sample_answer_state(sample_interview_state):
    """Interview state after first answer."""
    state = sample_interview_state.copy()
    state["messages"] = [
        {"role": "assistant", "content": "Hello! I'm glad you could join today."},
        {"role": "user", "content": "I've been working as a Python developer for 3 years."}
    ]
    state["current_question_index"] = 1
    state["last_evaluation"] = {
        "score": 7.5,
        "metrics": {"accuracy": 8.0, "clarity": 7.5, "depth": 7.0, "communication": 7.5},
        "topic": "python",
        "skill_category": "technical",
        "should_deep_dive": True,
        "needs_easier": False,
        "low_effort": False,
        "skill_identified": "programming"
    }
    return state


@pytest.fixture
def sample_report():
    """Sample evaluation report for testing."""
    return {
        "overall_score": 7.5,
        "hire_recommendation": "Hire",
        "technical_accuracy": 8.0,
        "communication_clarity": 7.5,
        "depth_of_knowledge": 7.0,
        "strengths": [
            "Strong Python fundamentals",
            "Good problem-solving approach",
            "Clear communication of technical concepts"
        ],
        "weaknesses": [
            "Could improve knowledge of distributed systems",
            "Limited exposure to Kubernetes"
        ],
        "summary": "A solid candidate with strong Python skills and good communication ability."
    }