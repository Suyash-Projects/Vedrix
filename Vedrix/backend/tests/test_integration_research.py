"""
Integration tests for the Research Agent service.

Tests GitHub indexing, skill claim verification, re-indexing skip logic,
and enrichment summary — all with mocked external APIs.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from app.models.user import User
from app.models.longitudinal_profile import LongitudinalProfile
from app.services.research_service import ResearchService
from app.core.security import get_password_hash

from sqlmodel import select


@pytest.fixture
async def research_setup(db_session):
    """Create test environment for research tests: user + longitudinal profile."""
    candidate = User(
        email="candidate_research@test.com",
        username="candidate_research",
        password_hash=get_password_hash("testpass"),
        first_name="Eve",
        last_name="Researcher",
        user_type="student",
        is_active=True,
    )
    db_session.add(candidate)
    await db_session.flush()

    # Create a longitudinal profile for the candidate
    profile = LongitudinalProfile(
        candidate_id=candidate.id,
        skill_history={},
        skill_averages={},
        skill_trends={},
        enrichment_sources={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(profile)
    await db_session.commit()

    return {
        "candidate": candidate,
        "profile": profile,
    }


@pytest.fixture
def mock_github_responses():
    """Mock GitHub API responses for repos endpoint."""
    user_response = MagicMock()
    user_response.status_code = 200
    user_response.json.return_value = {
        "login": "testuser",
        "updated_at": "2025-01-15T10:00:00Z",
    }

    repos_response = MagicMock()
    repos_response.status_code = 200
    repos_response.json.return_value = [
        {
            "name": "python-ml-project",
            "description": "Machine learning project using Python and scikit-learn",
            "language": "Python",
            "topics": ["machine-learning", "python", "scikit-learn"],
            "stargazers_count": 42,
            "forks_count": 5,
            "updated_at": "2025-01-10T08:00:00Z",
            "fork": False,
        },
        {
            "name": "react-dashboard",
            "description": "Admin dashboard built with React and TypeScript",
            "language": "TypeScript",
            "topics": ["react", "typescript", "dashboard"],
            "stargazers_count": 15,
            "forks_count": 2,
            "updated_at": "2025-01-05T12:00:00Z",
            "fork": False,
        },
        {
            "name": "forked-repo",
            "description": "A forked repository",
            "language": "JavaScript",
            "topics": [],
            "stargazers_count": 0,
            "forks_count": 0,
            "updated_at": "2024-12-01T00:00:00Z",
            "fork": True,
        },
    ]

    return user_response, repos_response


@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection for testing."""
    collection = MagicMock()
    collection.count.return_value = 2
    collection.upsert = MagicMock()
    collection.query.return_value = {
        "documents": [
            ["Repository: python-ml-project\nDescription: Machine learning project using Python"],
        ],
        "distances": [[0.3]],
        "metadatas": [[{"candidate_id": "1", "source": "github", "language": "python", "topics": "machine-learning, python"}]],
    }
    return collection


@pytest.mark.asyncio
async def test_index_github_populates_chromadb(
    db_session, research_setup, mock_github_responses, mock_chroma_collection
):
    """index_github() fetches repos and upserts into ChromaDB collection."""
    setup = research_setup
    candidate_id = setup["candidate"].id
    user_resp, repos_resp = mock_github_responses

    research_service = ResearchService()

    # Mock httpx.AsyncClient as an async context manager
    mock_client = AsyncMock()
    # When force=True, only repos endpoint is called (no user check)
    mock_client.get = AsyncMock(return_value=repos_resp)

    with patch("app.services.research_service.httpx.AsyncClient") as mock_async_client, \
         patch.object(research_service, "_get_profile_collection", return_value=mock_chroma_collection), \
         patch.object(research_service, "_embed_texts", return_value=[[0.1] * 384, [0.2] * 384]), \
         patch.object(research_service, "_rate_limiter") as mock_limiter:

        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_limiter.acquire = AsyncMock()

        result = await research_service.index_github(
            candidate_id=candidate_id,
            github_url="https://github.com/testuser",
            force=True,
            db=db_session,
        )

    assert result is not None
    assert result["repos_indexed"] == 2  # Forked repo should be skipped
    assert result["skipped"] is False
    assert result["indexed_at"] is not None

    # Verify ChromaDB upsert was called
    mock_chroma_collection.upsert.assert_called_once()
    call_kwargs = mock_chroma_collection.upsert.call_args
    # Should have 2 documents (fork excluded)
    if call_kwargs.kwargs:
        assert len(call_kwargs.kwargs["documents"]) == 2
    else:
        # positional args
        assert len(call_kwargs[1]["documents"]) == 2


@pytest.mark.asyncio
async def test_verify_skill_claim_returns_confidence(
    db_session, research_setup, mock_chroma_collection
):
    """verify_skill_claim() returns a confidence score between 0.0 and 1.0."""
    setup = research_setup
    candidate_id = setup["candidate"].id

    research_service = ResearchService()

    # Configure mock collection to return relevant results
    mock_chroma_collection.query.return_value = {
        "documents": [
            ["Repository: python-ml-project\nDescription: Machine learning with Python\nPrimary Language: Python"],
        ],
        "distances": [[0.2]],
        "metadatas": [[{
            "candidate_id": str(candidate_id),
            "source": "github",
            "language": "python",
            "topics": "machine-learning, python",
        }]],
    }

    with patch.object(research_service, "_get_profile_collection", return_value=mock_chroma_collection), \
         patch.object(research_service, "_embed_texts", return_value=[[0.1] * 384]):

        confidence = await research_service.verify_skill_claim(
            candidate_id=candidate_id,
            claimed_skill="Python",
            db=db_session,
        )

    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    # Python is the primary language in the mock data, so confidence should be high
    assert confidence >= 0.7


@pytest.mark.asyncio
async def test_index_github_skips_reindexing_when_timestamps_match(
    db_session, research_setup
):
    """index_github() skips re-indexing when github_last_indexed >= GitHub updated_at."""
    setup = research_setup
    candidate_id = setup["candidate"].id

    # Set github_last_indexed to a future date so it's >= GitHub updated_at
    stmt = select(LongitudinalProfile).where(
        LongitudinalProfile.candidate_id == candidate_id
    )
    result = await db_session.execute(stmt)
    profile = result.scalars().first()
    profile.github_last_indexed = datetime(2025, 12, 31, tzinfo=timezone.utc)
    db_session.add(profile)
    await db_session.commit()

    research_service = ResearchService()

    # Mock GitHub user API to return an older updated_at
    user_resp = MagicMock()
    user_resp.status_code = 200
    user_resp.json.return_value = {
        "login": "testuser",
        "updated_at": "2025-01-15T10:00:00Z",
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=user_resp)

    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch.object(research_service, "_rate_limiter") as mock_limiter:

        mock_limiter.acquire = AsyncMock()

        result = await research_service.index_github(
            candidate_id=candidate_id,
            github_url="https://github.com/testuser",
            force=False,
            db=db_session,
        )

    assert result["skipped"] is True
    assert result["repos_indexed"] == 0
    assert "github_last_indexed >= GitHub updated_at" in result["reason"]


@pytest.mark.asyncio
async def test_get_enrichment_summary_returns_sources(db_session, research_setup):
    """get_enrichment_summary() returns a list of enrichment sources."""
    setup = research_setup
    candidate_id = setup["candidate"].id

    # Set github_last_indexed to simulate a previous enrichment
    stmt = select(LongitudinalProfile).where(
        LongitudinalProfile.candidate_id == candidate_id
    )
    result = await db_session.execute(stmt)
    profile = result.scalars().first()
    profile.github_last_indexed = datetime(2025, 1, 15, tzinfo=timezone.utc)
    profile.enrichment_sources = {"github_status": "success"}
    db_session.add(profile)
    await db_session.commit()

    research_service = ResearchService()

    summary = await research_service.get_enrichment_summary(
        candidate_id=candidate_id,
        db=db_session,
    )

    assert summary is not None
    assert summary["candidate_id"] == candidate_id
    assert isinstance(summary["sources"], list)
    assert len(summary["sources"]) >= 1

    github_source = next(
        (s for s in summary["sources"] if s["source"] == "github"), None
    )
    assert github_source is not None
    assert github_source["status"] == "success"
    assert github_source["timestamp"] is not None
    assert summary["last_enriched_at"] is not None


@pytest.mark.asyncio
async def test_verify_skill_claim_no_evidence_returns_zero(
    db_session, research_setup
):
    """verify_skill_claim() returns 0.0 when no evidence exists in ChromaDB."""
    setup = research_setup
    candidate_id = setup["candidate"].id

    research_service = ResearchService()

    # Empty collection
    empty_collection = MagicMock()
    empty_collection.count.return_value = 0

    with patch.object(research_service, "_get_profile_collection", return_value=empty_collection):
        confidence = await research_service.verify_skill_claim(
            candidate_id=candidate_id,
            claimed_skill="Rust",
            db=db_session,
        )

    assert confidence == 0.0
