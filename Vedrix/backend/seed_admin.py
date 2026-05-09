import asyncio
import sys
import os

# Add the current directory to sys.path to allow importing 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import async_session, init_db
from app.models.user import User
from app.core import security
from sqlalchemy import select

async def seed_admin():
    print("Initializing database...")
    await init_db()
    
    async with async_session() as db:
        # Check if admin already exists
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalars().first()
        
        if not admin:
            print("Creating default admin user...")
            admin = User(
                email="admin@vedrix.ai",
                username="admin",
                password_hash=security.get_password_hash("admin123"),
                first_name="System",
                last_name="Administrator",
                user_type="admin",
                is_active=True
            )
            db.add(admin)
            await db.commit()
            print("Admin user created successfully!")
            print("Username: admin")
            print("Password: admin123")
        else:
            print("Admin user already exists.")

if __name__ == "__main__":
    asyncio.run(seed_admin())
