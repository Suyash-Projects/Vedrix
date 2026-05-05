import os
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_end_to_end_hr_drive_invite(client: AsyncClient):
    # 1) Register HR
    hr = {
        "email": "hr_test@example.com",
        "username": "hr_test",
        "password": "testpass",
        "first_name": "Test",
        "last_name": "HR",
        "user_type": "hr",
        "company_name": "TestCo"
    }
    resp = await client.post("/api/v1/auth/register", json=hr)
    assert resp.status_code == 200, resp.text

    # 2) Login HR
    # OAuth2 login uses form data
    login_data = {"username": hr["username"], "password": hr["password"]}
    resp = await client.post("/api/v1/auth/login", data=login_data)
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # 3) Create Drive
    drive = {
        "title": "Backend Systems Engineer",
        "description": "Drive for backend system improvements",
        "job_role": "Backend Engineer",
        "experience_required": "3+ years",
        "skills_required": "Python, FastAPI, Postgres",
        "is_active": True,
    }
    resp = await client.post("/api/v1/hr/drives", json=drive, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("title") == drive["title"]
    drive_id = data.get("id")
    assert drive_id is not None

    # 4) Magic Link Invite
    invite = {"candidate_email": "candidate@example.com", "expires_in_hours": 24}
    resp = await client.post(f"/api/v1/hr/drives/{drive_id}/magic-link", json=invite, headers=headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "link" in payload and "token" in payload
