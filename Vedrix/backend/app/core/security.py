from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    expire = (
        datetime.now(timezone.utc) + expires_delta
        if expires_delta
        else datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    encoded_jwt = jwt.encode(
        {"exp": expire, "sub": str(subject)},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """Create a refresh token with longer expiry."""
    expire = (
        datetime.now(timezone.utc) + expires_delta
        if expires_delta
        else datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    encoded_jwt = jwt.encode(
        {"exp": expire, "sub": str(subject), "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def decode_token(token: str) -> Optional[int]:
    """Decodes a JWT and returns the user ID, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except Exception:
        return None


def decode_refresh_token(token: str) -> Optional[int]:
    """Decodes a refresh token and returns the user ID, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return int(payload.get("sub"))
    except Exception:
        return None


def generate_verification_token(session_id: int, candidate_name: str, expires_days: int = 365) -> str:
    """Generate a verification token for certificate sharing. Valid for 1 year by default."""
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    encoded_jwt = jwt.encode(
        {
            "exp": expire,
            "sub": str(session_id),
            "name": candidate_name,
            "type": "certificate_verify",
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def decode_verification_token(token: str) -> tuple[int, str]:
    """Decode a certificate verification token. Returns (session_id, candidate_name)."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != "certificate_verify":
        raise ValueError("Invalid token type")
    session_id = int(payload.get("sub"))
    candidate_name = payload.get("name", "Unknown")
    return session_id, candidate_name
