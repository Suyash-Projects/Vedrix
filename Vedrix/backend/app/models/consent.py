"""
Consent model for GDPR compliance.
Tracks user consent for different data processing purposes.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class UserConsent(SQLModel, table=True):
    """Tracks user consent for different data processing purposes."""
    __tablename__ = "user_consent"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(nullable=False, index=True)
    purpose: str = Field(nullable=False, index=True)  # interview, analytics, marketing, cookies
    granted: bool = Field(nullable=False)
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    withdrawn_at: Optional[datetime] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
