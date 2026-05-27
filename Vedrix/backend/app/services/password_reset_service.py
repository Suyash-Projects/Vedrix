import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.services.email_service import send_password_reset_email
from app.core.config import settings
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

class PasswordResetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def request_reset(self, email: str) -> bool:
        """
        Generates a secure password reset token, saves its hash,
        and triggers a reset email. Always returns True (for enumeration prevention).
        """
        # Normalize email
        email = email.strip().lower()
        
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user or not user.is_active or user.deleted_at is not None:
            logger.info(f"Password reset requested for non-existent or inactive email: {email}")
            return True

        # Generate secure random token
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Create record
        reset_token = PasswordResetToken(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=expires_at,
        )
        self.db.add(reset_token)
        await self.db.commit()

        # Send email asynchronously
        try:
            await send_password_reset_email(
                to=user.email,
                first_name=user.first_name,
                reset_token=token,
                frontend_url=settings.FRONTEND_URL,
            )
            logger.info(f"Password reset email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}")

        return True

    async def execute_reset(self, token: str, new_password: str) -> bool:
        """
        Validates the token, updates the user's password,
        and invalidates the token. Returns True on success, False on failure.
        """
        token_hash = self._hash_token(token)

        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        reset_token = result.scalars().first()
        if not reset_token:
            logger.warning("Password reset failed: Token hash not found.")
            return False

        if reset_token.used_at is not None:
            logger.warning(f"Password reset failed: Token already used at {reset_token.used_at}")
            return False

        # Make sure expires_at is timezone-aware
        expires = reset_token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if expires < datetime.now(timezone.utc):
            logger.warning(f"Password reset failed: Token expired at {expires}")
            return False

        user_result = await self.db.execute(select(User).where(User.id == reset_token.user_id))
        user = user_result.scalars().first()
        if not user or not user.is_active or user.deleted_at is not None:
            logger.warning(f"Password reset failed: User not found or inactive for user ID {reset_token.user_id}")
            return False

        # Update password
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        self.db.add(user)

        # Invalidate token
        reset_token.used_at = datetime.now(timezone.utc)
        self.db.add(reset_token)

        await self.db.commit()
        logger.info(f"Password reset successful for user {user.email}")
        return True
