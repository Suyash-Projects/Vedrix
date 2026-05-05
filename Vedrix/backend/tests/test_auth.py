import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Vedrix API", "status": "online"}

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register a user
    register_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword",
        "first_name": "Test",
        "last_name": "User",
        "user_type": "student"
    }
    response = await client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    
    # Login
    login_data = {
        "username": "testuser",
        "password": "testpassword"
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    token = response.json()["access_token"]
    
    # Get me
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
