from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core import security
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,  # Don't auto-raise — we'll check cookies first
)


async def get_current_user(
    db: AsyncSession = Depends(get_session),
    token_from_header: Optional[str] = Depends(reusable_oauth2),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
) -> User:
    """
    Authenticate user via httpOnly cookie (primary) or Authorization header (fallback).

    Priority:
    1. httpOnly access_token cookie (browser-based requests)
    2. Authorization: Bearer <token> header (WebSocket, API clients, tests)
    """
    token = access_token_cookie or token_from_header

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_user_from_request(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """
    Alternative: extract token directly from request cookies or headers.
    Useful for WebSocket authentication where Depends(Cookie) doesn't work.
    """
    # Try cookie first
    token = request.cookies.get("access_token")

    # Fall back to Authorization header
    if not token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user


async def get_current_hr_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allows both HR managers and admins (ultimate authority)."""
    if current_user.user_type not in ("hr", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must have HR or Admin privileges",
        )
    return current_user


async def get_current_hr(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.user_type not in ["hr", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must have HR or Admin privileges",
        )
    return current_user
