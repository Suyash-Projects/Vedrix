import pytest
from httpx import AsyncClient


class TestUsers:
    """User management endpoint tests"""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """Test getting current user info"""
        response = await client.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting user without authentication fails"""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_current_user(self, client: AsyncClient, auth_headers):
        """Test updating current user profile"""
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"first_name": "Updated", "last_name": "Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"

    @pytest.mark.asyncio
    async def test_update_password(self, client: AsyncClient, auth_headers):
        """Test updating user password"""
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"password": "newpassword123"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cannot_change_email_to_existing(self, client: AsyncClient, db_session, auth_headers):
        """Test cannot change email to one that already exists"""
        from app.models.user import User
        from app.core.security import get_password_hash

        other_user = User(
            email="other@example.com",
            username="otheruser",
            password_hash=get_password_hash("pass123"),
            first_name="Other",
            last_name="User",
            user_type="student",
            is_active=True
        )
        db_session.add(other_user)
        await db_session.commit()

        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"email": "other@example.com"}
        )
        assert response.status_code == 400