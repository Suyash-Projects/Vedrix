from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import SQLModel, Field, Column, JSON

class InterviewPlan(SQLModel, table=True):
    __tablename__ = "interview_plan"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="interview_session.id", unique=True, nullable=False, index=True)
    job_drive_id: Optional[int] = Field(default=None, foreign_key="job_drive.id")
    candidate_id: int = Field(foreign_key="user.id", nullable=False)

    # Plan structure: [{phase, skill, difficulty, question_count, topics}]
    phases: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    # Revision history
    revision_count: int = Field(default=0)
    revisions: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    # Generation metadata
    generated_by: str = Field(default="planner_agent")  # "planner_agent" | "fallback"
    generation_time_ms: Optional[int] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
