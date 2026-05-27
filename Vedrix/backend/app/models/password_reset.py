from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .user import User

class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_token"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, index=True, nullable=False)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    expires_at: datetime = Field(nullable=False)
    used_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship to user
    user: "User" = Relationship()
