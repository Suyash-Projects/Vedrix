def test_hr_drive_happy_path(client):
    hr = {
        "email": "hr_test2@example.com",
        "username": "hr_test2",
        "password": "testpass2",
        "first_name": "Test2",
        "last_name": "HR2",
        "user_type": "hr",
        "company_name": "TestCo2"
    }
    resp = client.post("/api/v1/auth/register", json=hr)
    assert resp.status_code == 200, resp.text

    login = {"username": hr["username"], "password": hr["password"]}
    resp = client.post("/api/v1/auth/login", data=login)
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}

    drive = {
        "title": "Backend Systems Engineer",
        "description": "Drive for backend system improvements",
        "job_role": "Backend Engineer",
        "experience_required": "3+ years",
        "skills_required": "Python, FastAPI, Postgres",
        "is_active": True,
    }
    resp = client.post("/api/v1/hr/drives", json=drive, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("title") == drive["title"]
    assert data.get("id") is not None


def test_hr_drive_unauthorized_by_student(client):
    # Register a student
    student = {
        "email": "student1@example.com",
        "username": "student1",
        "password": "studpass",
        "first_name": "Student",
        "last_name": "One",
        "user_type": "student",
    }
    resp = client.post("/api/v1/auth/register", json=student)
    assert resp.status_code == 200, resp.text
    login = {"username": student["username"], "password": student["password"]}
    resp = client.post("/api/v1/auth/login", data=login)
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    drive = {
        "title": "Frontend Engineer",
        "description": "Frontend drive",
        "job_role": "Frontend Dev",
        "experience_required": "1+ years",
        "skills_required": "React, TS",
        "is_active": True,
    }
    resp = client.post("/api/v1/hr/drives", json=drive, headers=headers)
    assert resp.status_code == 403  # HR endpoints require HR auth


def test_hr_drive_missing_title_422(client):
    # Register and login HR
    hr = {
        "email": "hr_edge@example.com",
        "username": "hr_edge",
        "password": "edgepass",
        "first_name": "Edge",
        "last_name": "Case",
        "user_type": "hr",
        "company_name": "EdgeCo"
    }
    client.post("/api/v1/auth/register", json=hr)
    login = {"username": hr["username"], "password": hr["password"]}
    resp = client.post("/api/v1/auth/login", data=login)
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Missing required field: title
    drive = {
        "description": "No title drive",
        "job_role": "DevOps",
        "experience_required": "2+ years",
        "skills_required": "Docker, Kubernetes",
        "is_active": True,
    }
    resp = client.post("/api/v1/hr/drives", json=drive, headers=headers)
    assert resp.status_code == 422  # Unprocessable Entity due to validation


def test_voice_capabilities_endpoint(client):
    resp = client.get("/api/v1/voice/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "voice_available" in data
