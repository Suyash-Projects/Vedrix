import pytest
from httpx import AsyncClient


class TestAuth:
    """Authentication endpoint tests"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login with valid credentials"""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user):
        """Test login fails with wrong password"""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "wrongpassword"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login fails with non-existent user"""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent", "password": "password123"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session):
        """Test login fails for inactive user"""
        test_user.is_active = False
        db_session.add(test_user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration fails with duplicate email"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "differentuser",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        """Test registration fails with duplicate username"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@example.com",
                "username": "testuser",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_hr_user(self, client: AsyncClient):
        """Test HR user registration creates HR profile"""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hr@example.com",
                "username": "hruser",
                "password": "password123",
                "first_name": "HR",
                "last_name": "Manager",
                "user_type": "hr",
                "company_name": "Tech Corp"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_type"] == "hr"