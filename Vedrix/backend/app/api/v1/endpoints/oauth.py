import logging
from typing import Any, Optional
from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi_sso.sso.google import GoogleSSO
from fastapi_sso.sso.github import GithubSSO
from fastapi_sso.sso.linkedin import LinkedInSSO

from app.db.session import get_session
from app.models.user import User
from app.models.profile import StudentProfile
from app.core import security
from app.core.config import settings
from app.core.csrf import generate_csrf_token
from app.api.v1.endpoints.auth import _set_auth_cookies

logger = logging.getLogger(__name__)
router = APIRouter()

# ── SSO Clients ─────────────────────────────────────────────────────────────

google_sso = GoogleSSO(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=f"{settings.API_V1_STR}/auth/google/callback",
    allow_insecure_http=True if settings.ENVIRONMENT == "development" else False,
)

github_sso = GithubSSO(
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    redirect_uri=f"{settings.API_V1_STR}/auth/github/callback",
    allow_insecure_http=True if settings.ENVIRONMENT == "development" else False,
    scope=["user:email"],
)

linkedin_sso = LinkedInSSO(
    client_id=settings.LINKEDIN_CLIENT_ID,
    client_secret=settings.LINKEDIN_CLIENT_SECRET,
    redirect_uri=f"{settings.API_V1_STR}/auth/linkedin/callback",
    allow_insecure_http=True if settings.ENVIRONMENT == "development" else False,
)

# ── Google OAuth ────────────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login():
    """Redirect to Google login page."""
    with google_sso:
        return await google_sso.get_login_redirect()


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_session)):
    """Handle Google login callback."""
    with google_sso:
        user_info = await google_sso.verify_and_process(request)
    
    if not user_info:
        raise HTTPException(status_code=400, detail="Google authentication failed")
    
    return await _process_oauth_user(user_info, "google", db)


# ── GitHub OAuth ────────────────────────────────────────────────────────────

@router.get("/github/login")
async def github_login():
    """Redirect to GitHub login page."""
    with github_sso:
        return await github_sso.get_login_redirect()


@router.get("/github/callback")
async def github_callback(request: Request, db: AsyncSession = Depends(get_session)):
    """Handle GitHub login callback."""
    with github_sso:
        user_info = await github_sso.verify_and_process(request)
    
    if not user_info:
        raise HTTPException(status_code=400, detail="GitHub authentication failed")
    
    return await _process_oauth_user(user_info, "github", db)


# ── LinkedIn OAuth ──────────────────────────────────────────────────────────

@router.get("/linkedin/login")
async def linkedin_login():
    """Redirect to LinkedIn login page."""
    with linkedin_sso:
        return await linkedin_sso.get_login_redirect()


@router.get("/linkedin/callback")
async def linkedin_callback(request: Request, db: AsyncSession = Depends(get_session)):
    """Handle LinkedIn login callback."""
    with linkedin_sso:
        user_info = await linkedin_sso.verify_and_process(request)
    
    if not user_info:
        raise HTTPException(status_code=400, detail="LinkedIn authentication failed")
    
    return await _process_oauth_user(user_info, "linkedin", db)


# ── Internal Helper ─────────────────────────────────────────────────────────

async def _process_oauth_user(user_info: Any, provider: str, db: AsyncSession) -> RedirectResponse:
    """
    Common logic to find or create user from OAuth info and redirect to frontend.
    """
    email = user_info.email
    provider_id = user_info.id
    
    # 1. Check if user already exists by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        # Create new user (default to student)
        # Generate a unique username from email or provider info
        username = email.split('@')[0]
        # Ensure username uniqueness
        base_username = username
        counter = 1
        while True:
            existing_user = await db.execute(select(User).where(User.username == username))
            if not existing_user.scalars().first():
                break
            username = f"{base_username}{counter}"
            counter += 1
            
        user = User(
            email=email,
            username=username,
            first_name=user_info.first_name or "User",
            last_name=user_info.last_name or "",
            user_type="student",
            provider=provider,
            provider_id=provider_id,
            is_active=True,
            password_hash=None, # No local password for social users
        )
        db.add(user)
        await db.flush()
        
        # Create student profile
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        
    else:
        # User exists — update provider info if not already set
        if not user.provider_id:
            user.provider = provider
            user.provider_id = provider_id
            db.add(user)
            
    await db.commit()
    await db.refresh(user)
    
    # 2. Generate Vedrix tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(user.id, expires_delta=access_token_expires)
    refresh_token = security.create_refresh_token(user.id)
    csrf_token = generate_csrf_token()
    
    # 3. Redirect back to frontend dashboard with cookies set
    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard")
    
    # Set cookies on the redirect response
    _set_auth_cookies(response, access_token, refresh_token, csrf_token)
    
    return response
