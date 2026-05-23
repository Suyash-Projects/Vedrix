import pytest
from httpx import AsyncClient
from fastapi import status
from main import app
from app.core import security
from app.core.config import settings

@pytest.mark.asyncio
async def test_video_signaling_unauthenticated(client: AsyncClient):
    """Verify that video signaling requires a valid token."""
    from app.api.v1.endpoints.interview import _verify_ws_token
    assert _verify_ws_token("invalid-token") is None

@pytest.mark.asyncio
async def test_encryption_at_rest(client: AsyncClient, db_session):
    """Verify that sensitive fields are actually encrypted in the database."""
    from app.models.interview import InterviewSession
    from app.models.user import User
    from sqlalchemy import text
    import json
    
    db = db_session
    
    # 1. Ensure we have a user
    user = User(
        email="test_encrypt@example.com",
        username="test_encrypt",
        password_hash="...",
        first_name="Test",
        last_name="Encrypt",
        user_type="student"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # 2. Create a session with sensitive data
    sensitive_responses = [{"role": "user", "content": "My secret password is 12345"}]
    session = InterviewSession(
        candidate_id=user.id,
        session_type="practice",
        responses=sensitive_responses
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # 3. Query the database using RAW SQL to see if it's plaintext
    # We use raw SQL to bypass the ORM TypeDecorator
    result = await db.execute(text(f"SELECT responses FROM interview_session WHERE id = {session.id}"))
    raw_value = result.scalar()
    
    # 4. Verify it's encrypted (not a JSON string containing our secret)
    assert raw_value is not None
    assert "My secret password" not in raw_value
    
    # 5. Verify the ORM decrypts it correctly
    res_session = await db.get(InterviewSession, session.id)
    assert res_session.responses == sensitive_responses
