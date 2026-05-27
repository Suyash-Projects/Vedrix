from datetime import timedelta, datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead
from app.core import security
from app.core.config import settings
from app.core.csrf import generate_csrf_token
from app.services.email_service import send_welcome_email

router = APIRouter()

# Account lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def _set_auth_cookies(
    response: JSONResponse,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> JSONResponse:
    """Set httpOnly auth cookies and CSRF token cookie on the response."""
    is_prod = settings.ENVIRONMENT == "production"

    # Access token — httpOnly, short-lived
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    # Refresh token — httpOnly, long-lived
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )

    # CSRF token — readable by JS, sent in X-CSRF-Token header
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # Must be readable by JavaScript
        secure=is_prod,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return response


def _clear_auth_cookies(response: JSONResponse) -> JSONResponse:
    """Clear all auth cookies on logout."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    response.delete_cookie(key="csrf_token", path="/")
    return response


@router.post("/login")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login.
    Sets httpOnly cookies for access_token, refresh_token, and csrf_token.
    JWT is never exposed to JavaScript — only the CSRF token is readable.

    Security features:
    - Account lockout after {MAX_FAILED_ATTEMPTS} failed attempts
    - Lockout duration: {LOCKOUT_DURATION_MINUTES} minutes
    - Failed attempt counter resets on successful login
    """
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        raise HTTPException(
            status_code=429,
            detail=f"Account locked due to too many failed attempts. Try again in {remaining} minutes."
        )

    # Check password
    if not security.verify_password(form_data.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        await db.commit()
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Reset failed attempts on successful login
    if user.failed_login_attempts > 0 or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        await db.commit()

    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(user.id, expires_delta=access_token_expires)
    refresh_token = security.create_refresh_token(user.id)
    csrf_token = generate_csrf_token()

    # Build response with cookies
    response = JSONResponse(content={
        "status": "ok",
        "user_id": user.id,
        "csrf_token": csrf_token,  # Return CSRF token in body for initial login
    })
    _set_auth_cookies(response, access_token, refresh_token, csrf_token)

    return response


@router.post("/refresh")
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """
    Refresh an access token using the refresh token cookie.
    Returns new access token and CSRF token cookies.
    """
    refresh_token_value = request.cookies.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    user_id = security.decode_refresh_token(refresh_token_value)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Generate new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(user.id, expires_delta=access_token_expires)
    new_refresh_token = security.create_refresh_token(user.id)
    csrf_token = generate_csrf_token()

    response = JSONResponse(content={
        "status": "ok",
        "user_id": user.id,
        "csrf_token": csrf_token,
    })
    _set_auth_cookies(response, access_token, new_refresh_token, csrf_token)

    return response


@router.post("/logout")
async def logout() -> Any:
    """Clear all auth cookies."""
    response = JSONResponse(content={"status": "ok"})
    _clear_auth_cookies(response)
    return response


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """
    Request a password reset email.
    Body: {"email": "user@example.com"}
    Always returns 200 to prevent email enumeration.
    """
    from app.services.password_reset_service import PasswordResetService

    body = await request.json()
    email = body.get("email", "")

    reset_service = PasswordResetService(db)
    await reset_service.request_reset(email)

    # Always return 200 — don't reveal if email exists
    return {"status": "ok", "message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """
    Reset password using a valid reset token.
    Body: {"token": "...", "new_password": "..."}
    """
    from app.services.password_reset_service import PasswordResetService

    body = await request.json()
    token = body.get("token", "")
    new_password = body.get("new_password", "")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and new password are required")

    # Validate password strength (reuse schema validation)
    try:
        UserCreate.validate_password_strength(new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    reset_service = PasswordResetService(db)
    success = await reset_service.execute_reset(token, new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    return {"status": "ok", "message": "Password reset successfully."}


@router.post("/register", response_model=UserRead)
async def register(
    *,
    db: AsyncSession = Depends(get_session),
    user_in: UserCreate,
    background_tasks: BackgroundTasks
) -> Any:
    """Create new user."""
    # Check email and username first (warn user before attempting insert)
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

    try:
        await db.flush()  # get user.id before commit
    except Exception as e:
        await db.rollback()
        # Re-check which constraint failed
        result = await db.execute(select(User).where(User.email == user_in.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="The user with this email already exists in the system.")
        result = await db.execute(select(User).where(User.username == user_in.username))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="The username already exists.")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

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
