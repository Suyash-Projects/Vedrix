from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import SQLModel, Field, Column, JSON
from app.core.encryption import EncryptedJSON

class CoachingPlan(SQLModel, table=True):
    __tablename__ = "coaching_plan"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="interview_session.id", unique=True, nullable=False, index=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)

    # Prioritized skill gaps: [{skill, score, gap_magnitude, resources: [{title, url, type}]}]
    skill_gaps: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))

    # Summary for email notification
    top_3_gaps: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    # Generation metadata
    generation_time_ms: Optional[int] = None
    notification_sent_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
