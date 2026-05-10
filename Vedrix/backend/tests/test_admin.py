import pytest
from httpx import AsyncClient


class TestAdmin:
    """Admin endpoint tests"""

    @pytest.mark.asyncio
    async def test_admin_stats(self, client: AsyncClient, admin_headers):
        """Test getting admin system statistics"""
        response = await client.get(
            "/api/v1/admin/stats",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "system_status" in data

    @pytest.mark.asyncio
    async def test_admin_list_users(self, client: AsyncClient, admin_headers):
        """Test listing all users"""
        response = await client.get(
            "/api/v1/admin/users",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_admin_create_user(self, client: AsyncClient, admin_headers):
        """Test admin can create users"""
        response = await client.post(
            "/api/v1/admin/users",
            headers=admin_headers,
            json={
                "email": "created@example.com",
                "username": "createduser",
                "password": "password123",
                "first_name": "Created",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_admin_get_user(self, client: AsyncClient, admin_headers, test_user):
        """Test admin can get specific user"""
        response = await client.get(
            f"/api/v1/admin/users/{test_user.id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_admin_update_user(self, client: AsyncClient, admin_headers, test_user):
        """Test admin can update user"""
        response = await client.patch(
            f"/api/v1/admin/users/{test_user.id}",
            headers=admin_headers,
            json={"first_name": "AdminUpdated"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_deactivate_user(self, client: AsyncClient, admin_headers, db_session):
        """Test admin can deactivate users"""
        from app.models.user import User
        from app.core.security import get_password_hash

        user = User(
            email="deact@example.com",
            username="deactuser",
            password_hash=get_password_hash("pass123"),
            first_name="Deact",
            last_name="User",
            user_type="student",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        response = await client.patch(
            f"/api/v1/admin/users/{user.id}/deactivate",
            headers=admin_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_cannot_deactivate_self(self, client: AsyncClient, admin_headers, admin_user):
        """Test admin cannot deactivate their own account"""
        response = await client.patch(
            f"/api/v1/admin/users/{admin_user.id}/deactivate",
            headers=admin_headers
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_admin(self, client: AsyncClient, auth_headers):
        """Test non-admin cannot access admin endpoints"""
        response = await client.get(
            "/api/v1/admin/stats",
            headers=auth_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_list_all_interviews(self, client: AsyncClient, admin_headers):
        """Test admin can list all interviews"""
        response = await client.get(
            "/api/v1/admin/interviews",
            headers=admin_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_list_drives(self, client: AsyncClient, admin_headers):
        """Test admin can list all job drives"""
        response = await client.get(
            "/api/v1/admin/drives",
            headers=admin_headers
        )
        assert response.status_code == 200