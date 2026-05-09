import os
import pytest
from fastapi.testclient import TestClient

# The application uses the database URL from environment. For tests we use a local SQLite DB.
TEST_DB = os.path.abspath("vedrix_test.db")

@pytest.fixture(scope="session")
async def client():
    # Ensure a clean database for tests
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./vedrix_test.db"
    
    from app.db.session import init_db
    await init_db()
    
    from main import app  # import here to ensure env var is read before app creation
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
