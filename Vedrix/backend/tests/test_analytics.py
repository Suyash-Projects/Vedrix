"""
Tests for Phase 3: Analytics & Reporting endpoints.
"""
import pytest
import json
from datetime import datetime, timezone

from app.models.interview import InterviewSession, JobDrive
from app.models.profile import HRProfile


async def _login_and_get_headers(client, username, password):
    """Helper: login and return headers with CSRF token for cookie-based auth."""
    resp = await client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200
    csrf_token = resp.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf_token}


@pytest.mark.asyncio
async def test_hr_skill_gap_analysis(client):
    """Test HR skill gap endpoint returns 404 for non-existent session."""
    # Register & login HR
    hr = {
        "email": "hr_skillgap@example.com",
        "username": "hr_skillgap",
        "password": "SkillP@ss1",
        "first_name": "Skill",
        "last_name": "Gap",
        "user_type": "hr",
        "company_name": "SkillCo"
    }
    await client.post("/api/v1/auth/register", json=hr)
    headers = await _login_and_get_headers(client, hr["username"], hr["password"])

    # Non-existent session should return 404
    resp = await client.get("/api/v1/hr/interviews/99999/skill-gap", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hr_replay_nonexistent(client):
    """Test replay endpoint returns 404 for non-existent session."""
    hr = {
        "email": "hr_replay@example.com",
        "username": "hr_replay",
        "password": "ReplayP@ss1",
        "first_name": "Replay",
        "last_name": "Test",
        "user_type": "hr",
        "company_name": "ReplayCo"
    }
    await client.post("/api/v1/auth/register", json=hr)
    headers = await _login_and_get_headers(client, hr["username"], hr["password"])

    resp = await client.get("/api/v1/hr/interviews/99999/replay", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hr_csv_export(client):
    """Test HR can export interview data as CSV."""
    hr = {
        "email": "hr_csv@example.com",
        "username": "hr_csv",
        "password": "CsvP@ss1",
        "first_name": "CSV",
        "last_name": "Export",
        "user_type": "hr",
        "company_name": "CsvCo"
    }
    await client.post("/api/v1/auth/register", json=hr)
    headers = await _login_and_get_headers(client, hr["username"], hr["password"])

    resp = await client.get("/api/v1/hr/analytics/export/csv", headers=headers)
    # Should return CSV content (even if empty)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    # CSV should have headers
    content = resp.text
    assert "session_id" in content or "candidate_email" in content


@pytest.mark.asyncio
async def test_admin_team_analytics(client):
    """Test admin can get team analytics."""
    admin = {
        "email": "admin_analytics@example.com",
        "username": "admin_analytics",
        "password": "AnalyticsP@ss1",
        "first_name": "Analytics",
        "last_name": "Admin",
        "user_type": "admin",
    }
    await client.post("/api/v1/auth/register", json=admin)
    headers = await _login_and_get_headers(client, admin["username"], admin["password"])

    resp = await client.get("/api/v1/admin/analytics/team", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "funnel" in data
    assert "score_distribution" in data
    assert "role_breakdown" in data
    assert "daily_trend" in data
    assert "pass_fail" in data


@pytest.mark.asyncio
async def test_admin_team_analytics_unauthorized(client):
    """Test non-admin cannot access team analytics."""
    student = {
        "email": "student_analytics@example.com",
        "username": "student_analytics",
        "password": "AnalyticsP@ss1",
        "first_name": "Analytics",
        "last_name": "Student",
        "user_type": "student",
    }
    await client.post("/api/v1/auth/register", json=student)
    headers = await _login_and_get_headers(client, student["username"], student["password"])

    resp = await client.get("/api/v1/admin/analytics/team", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_csv_export(client):
    """Test admin can export platform data as CSV."""
    admin = {
        "email": "admin_csv@example.com",
        "username": "admin_csv",
        "password": "CsvP@ss2",
        "first_name": "CSV",
        "last_name": "Admin",
        "user_type": "admin",
    }
    await client.post("/api/v1/auth/register", json=admin)
    headers = await _login_and_get_headers(client, admin["username"], admin["password"])

    resp = await client.get("/api/v1/admin/analytics/export/csv", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_student_skill_gap(client):
    """Test student can get skill gap for their own session."""
    student = {
        "email": "student_sg2@example.com",
        "username": "student_sg2",
        "password": "SgP@ss12",
        "first_name": "SG",
        "last_name": "Student",
        "user_type": "student",
    }
    resp = await client.post("/api/v1/auth/register", json=student)
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    headers = await _login_and_get_headers(client, student["username"], student["password"])

    # Non-existent session
    resp = await client.get("/api/v1/users/sessions/99999/skill-gap", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_student_replay(client):
    """Test student can get replay for their own session."""
    student = {
        "email": "student_replay2@example.com",
        "username": "student_replay2",
        "password": "ReplayP@ss22",
        "first_name": "Replay",
        "last_name": "Student",
        "user_type": "student",
    }
    resp = await client.post("/api/v1/auth/register", json=student)
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    headers = await _login_and_get_headers(client, student["username"], student["password"])

    # Non-existent session
    resp = await client.get("/api/v1/users/sessions/99999/replay", headers=headers)
    assert resp.status_code == 404
