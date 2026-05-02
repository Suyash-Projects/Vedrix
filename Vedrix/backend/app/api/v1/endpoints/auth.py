from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead
from app.core import security
from app.core.config import settings
from app.services.email_service import send_welcome_email

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserRead)
async def register(
    *,
    db: AsyncSession = Depends(get_session),
    user_in: UserCreate,
    background_tasks: BackgroundTasks
) -> Any:
    """Create new user."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="The user with this email already exists in the system.")
    
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="The username already exists.")
    
    user = User(
        email=user_in.email,
        username=user_in.username,
        password_hash=security.get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        user_type=user_in.user_type,
    )
    db.add(user)
    await db.flush()  # get user.id before commit

    # Auto-create profile based on user type
    if user_in.user_type == 'hr':
        from app.models.profile import HRProfile
        hr_profile = HRProfile(
            user_id=user.id,
            company_name=user_in.company_name or "Not specified"
        )
        db.add(hr_profile)
    elif user_in.user_type == 'student':
        from app.models.profile import StudentProfile
        student_profile = StudentProfile(user_id=user.id)
        db.add(student_profile)

    await db.commit()
    await db.refresh(user)

    # Send welcome email in background
    background_tasks.add_task(send_welcome_email, user.email, user.first_name, user.user_type)

    return user
