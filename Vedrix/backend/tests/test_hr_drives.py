import pytest


async def _login_and_get_headers(client, username, password):
    """Helper: login and return headers with CSRF token for cookie-based auth."""
    resp = await client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200
    csrf_token = resp.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf_token}


@pytest.mark.asyncio
async def test_hr_drive_happy_path(client):
    hr = {
        "email": "hr_test2@example.com",
        "username": "hr_test2",
        "password": "TestP@ss2",
        "first_name": "Test2",
        "last_name": "HR2",
        "user_type": "hr",
        "company_name": "TestCo2"
    }
    resp = await client.post("/api/v1/auth/register", json=hr)
    assert resp.status_code == 200, resp.text

    headers = await _login_and_get_headers(client, hr["username"], hr["password"])

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
    assert data.get("id") is not None


@pytest.mark.asyncio
async def test_hr_drive_unauthorized_by_student(client):
    # Register a student
    student = {
        "email": "student1@example.com",
        "username": "student1",
        "password": "StudP@ss1",
        "first_name": "Student",
        "last_name": "One",
        "user_type": "student",
    }
    resp = await client.post("/api/v1/auth/register", json=student)
    assert resp.status_code == 200, resp.text

    headers = await _login_and_get_headers(client, student["username"], student["password"])

    drive = {
        "title": "Frontend Engineer",
        "description": "Frontend drive",
        "job_role": "Frontend Dev",
        "experience_required": "1+ years",
        "skills_required": "React, TS",
        "is_active": True,
    }
    resp = await client.post("/api/v1/hr/drives", json=drive, headers=headers)
    assert resp.status_code == 403  # HR endpoints require HR auth


@pytest.mark.asyncio
async def test_hr_drive_missing_title_422(client):
    # Register and login HR
    hr = {
        "email": "hr_edge@example.com",
        "username": "hr_edge",
        "password": "EdgeP@ss1",
        "first_name": "Edge",
        "last_name": "Case",
        "user_type": "hr",
        "company_name": "EdgeCo"
    }
    await client.post("/api/v1/auth/register", json=hr)
    headers = await _login_and_get_headers(client, hr["username"], hr["password"])

    # Missing required field: title
    drive = {
        "description": "No title drive",
        "job_role": "DevOps",
        "experience_required": "2+ years",
        "skills_required": "Docker, Kubernetes",
        "is_active": True,
    }
    resp = await client.post("/api/v1/hr/drives", json=drive, headers=headers)
    assert resp.status_code == 422  # Unprocessable Entity due to validation


@pytest.mark.asyncio
async def test_voice_capabilities_endpoint(client):
    resp = await client.get("/api/v1/voice/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "voice_available" in data


@pytest.mark.asyncio
async def test_hr_drive_lifecycle(client):
    # 1. Register & Login HR
    hr = {
        "email": "hr_lifecycle@example.com",
        "username": "hr_lifecycle",
        "password": "LifeP@ss1",
        "first_name": "Life",
        "last_name": "Cycle",
        "user_type": "hr",
        "company_name": "LifeCo"
    }
    await client.post("/api/v1/auth/register", json=hr)
    headers = await _login_and_get_headers(client, hr["username"], hr["password"])

    # 2. Create Drive
    drive_data = {"title": "Initial Title", "job_role": "Tester", "is_active": True}
    resp = await client.post("/api/v1/hr/drives", json=drive_data, headers=headers)
    drive_id = resp.json()["id"]

    # 3. Update Drive
    update_data = {"title": "Updated Title"}
    resp = await client.put(f"/api/v1/hr/drives/{drive_id}", json=update_data, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"

    # 4. Toggle Drive (Close)
    resp = await client.patch(f"/api/v1/hr/drives/{drive_id}/toggle", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # 5. Toggle Drive (Open)
    resp = await client.patch(f"/api/v1/hr/drives/{drive_id}/toggle", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    # 6. List Candidates
    resp = await client.get(f"/api/v1/hr/drives/{drive_id}/candidates", headers=headers)
    assert resp.status_code == 200
    assert "candidates" in resp.json()

    # 7. Delete Drive
    resp = await client.delete(f"/api/v1/hr/drives/{drive_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
