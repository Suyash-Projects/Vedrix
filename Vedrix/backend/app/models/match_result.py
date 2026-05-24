from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import Index

class MatchResult(SQLModel, table=True):
    __tablename__ = "match_result"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    job_drive_id: int = Field(foreign_key="job_drive.id", nullable=False, index=True)
    session_id: int = Field(foreign_key="interview_session.id", nullable=False)

    match_score: Optional[float] = None  # 0.0 to 100.0; null = pending
    is_top_match: bool = Field(default=False)

    # Natural language explanation
    explanation: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    # {contributing_factors: [...], disqualifying_factors: [...]}

    # Score breakdown
    score_breakdown: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    computed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_match_drive_score", "job_drive_id", "match_score"),
    )
