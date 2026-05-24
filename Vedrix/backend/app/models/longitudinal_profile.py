from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import SQLModel, Field, Column, JSON
from app.core.encryption import EncryptedJSON

class LongitudinalProfile(SQLModel, table=True):
    __tablename__ = "longitudinal_profile"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="user.id", unique=True, nullable=False, index=True)

    # Encrypted skill score history: {skill: [{score, session_id, timestamp}]}
    skill_history: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))

    # Encrypted aggregated skill scores: {skill: avg_score}
    skill_averages: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))

    # Trend directions: {skill: "improving"|"stable"|"declining"}
    skill_trends: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    # External enrichment metadata
    github_last_indexed: Optional[datetime] = None
    linkedin_last_indexed: Optional[datetime] = None
    enrichment_sources: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    # Coaching effectiveness: {skill: delta_score}
    coaching_effectiveness: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    # GDPR
    deletion_requested_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
