import pytest
from httpx import AsyncClient


class TestAuth:
    """Authentication endpoint tests"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login with valid credentials — returns httpOnly cookies."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        # Cookies are set on the response (httpOnly, not visible in JSON body)
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert "csrf_token" in response.cookies
        # CSRF token is also returned in body for initial use
        assert "csrf_token" in data
        assert data["status"] == "ok"

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
        from app.models.user import User
        from app.core.security import get_password_hash

        user = User(
            email="inactive@example.com",
            username="inactiveuser",
            password_hash=get_password_hash("testpass123"),
            first_name="Inactive",
            last_name="User",
            user_type="student",
            is_active=False,
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "inactiveuser", "password": "testpass123"}
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
                "password": "SecureP@ss123",
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
                "password": "SecureP@ss123",
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
                "password": "SecureP@ss123",
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
                "password": "SecureP@ss123",
                "first_name": "HR",
                "last_name": "Manager",
                "user_type": "hr",
                "company_name": "Tech Corp"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_type"] == "hr"


class TestPasswordSecurity:
    """Password strength validation tests."""

    @pytest.mark.asyncio
    async def test_weak_password_too_short(self, client: AsyncClient):
        """Registration rejects passwords shorter than 8 characters."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "username": "weakuser",
                "password": "Ab1!",
                "first_name": "Weak",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 422
        assert "8 characters" in response.json()["detail"][0]["msg"]

    @pytest.mark.asyncio
    async def test_weak_password_no_uppercase(self, client: AsyncClient):
        """Registration rejects passwords without uppercase."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak2@example.com",
                "username": "weakuser2",
                "password": "password1!",
                "first_name": "Weak",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 422
        assert "uppercase" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_weak_password_no_lowercase(self, client: AsyncClient):
        """Registration rejects passwords without lowercase."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak3@example.com",
                "username": "weakuser3",
                "password": "PASSWORD1!",
                "first_name": "Weak",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 422
        assert "lowercase" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_weak_password_no_number(self, client: AsyncClient):
        """Registration rejects passwords without a number."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak4@example.com",
                "username": "weakuser4",
                "password": "Password!",
                "first_name": "Weak",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 422
        assert "number" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_weak_password_no_special(self, client: AsyncClient):
        """Registration rejects passwords without a special character."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak5@example.com",
                "username": "weakuser5",
                "password": "Password1",
                "first_name": "Weak",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 422
        assert "special" in response.json()["detail"][0]["msg"].lower()

    @pytest.mark.asyncio
    async def test_strong_password_accepted(self, client: AsyncClient):
        """Registration accepts strong passwords."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "strong@example.com",
                "username": "stronguser",
                "password": "Str0ng!Pass",
                "first_name": "Strong",
                "last_name": "User",
                "user_type": "student"
            }
        )
        assert response.status_code == 200


class TestAccountLockout:
    """Account lockout after failed login attempts."""

    @pytest.mark.asyncio
    async def test_account_locks_after_5_failures(self, client: AsyncClient, db_session):
        """Account locks after 5 failed login attempts."""
        from app.models.user import User
        from app.core.security import get_password_hash

        user = User(
            email="lockout@example.com",
            username="lockoutuser",
            password_hash=get_password_hash("Str0ng!Pass"),
            first_name="Lockout",
            last_name="User",
            user_type="student",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()

        # 5 failed attempts
        for _ in range(5):
            response = await client.post(
                "/api/v1/auth/login",
                data={"username": "lockoutuser", "password": "WrongP@ss1"}
            )
            assert response.status_code == 400

        # 6th attempt should be locked
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "lockoutuser", "password": "WrongP@ss1"}
        )
        assert response.status_code == 429
        assert "locked" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_successful_login_resets_counter(self, client: AsyncClient, test_user):
        """Successful login resets failed attempt counter."""
        # First, make a few failed attempts
        for _ in range(3):
            await client.post(
                "/api/v1/auth/login",
                data={"username": "testuser", "password": "WrongP@ss1"}
            )

        # Now login with correct password
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 200

        # Verify counter was reset — should still be able to login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpass123"}
        )
        assert response.status_code == 200