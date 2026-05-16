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
    async def test_update_username(self, client: AsyncClient, auth_headers):
        """Test updating current user username"""
        response = await client.put(
            "/api/v1/users/username",
            headers=auth_headers,
            json={"new_username": "updateduser"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers):
        """Test changing user password"""
        response = await client.post(
            "/api/v1/users/change-password",
            headers=auth_headers,
            json={"current_password": "testpass123", "new_password": "newpassword123"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_clear_interviews(self, client: AsyncClient, auth_headers):
        """Test clearing user interviews"""
        response = await client.delete(
            "/api/v1/users/clear-interviews",
            headers=auth_headers
        )
        assert response.status_code == 200