import pytest
from httpx import AsyncClient


class TestInterview:
    """Interview endpoint tests"""

    @pytest.mark.asyncio
    async def test_student_stats(self, client: AsyncClient, auth_headers):
        """Test getting student interview statistics"""
        response = await client.get(
            "/api/v1/student/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_interviews" in data
        assert "completed_interviews" in data

    @pytest.mark.asyncio
    async def test_student_interviews_list(self, client: AsyncClient, auth_headers):
        """Test listing student interview sessions"""
        response = await client.get(
            "/api/v1/student/interviews",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_student_profile(self, client: AsyncClient, auth_headers):
        """Test getting student profile"""
        response = await client.get(
            "/api/v1/profiles/student",
            headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_student_profile(self, client: AsyncClient, auth_headers):
        """Test updating student profile"""
        response = await client.post(
            "/api/v1/profiles/student",
            headers=auth_headers,
            json={
                "university": "MIT",
                "degree": "Computer Science",
                "graduation_year": 2026,
                "skills": "Python, React"
            }
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hr_only_access_to_hr_endpoints(self, client: AsyncClient, auth_headers):
        """Test student cannot access HR endpoints"""
        response = await client.get(
            "/api/v1/hr/drives",
            headers=auth_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_hr_can_access_own_drives(self, client: AsyncClient, db_session, auth_headers):
        """Test HR can access their drives"""
        from app.models.user import User
        from app.core.security import get_password_hash

        hr_user = User(
            email="hr@test.com",
            username="hruser",
            password_hash=get_password_hash("pass123"),
            first_name="HR",
            last_name="User",
            user_type="hr",
            is_active=True
        )
        db_session.add(hr_user)
        await db_session.commit()

        from app.core.security import create_access_token
        hr_token = create_access_token(hr_user.id)
        hr_headers = {"Authorization": f"Bearer {hr_token}"}

        response = await client.get(
            "/api/v1/hr/drives",
            headers=hr_headers
        )
        assert response.status_code == 200