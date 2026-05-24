from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import Index

class CandidateWorkflow(SQLModel, table=True):
    __tablename__ = "candidate_workflow"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    job_drive_id: int = Field(foreign_key="job_drive.id", nullable=False, index=True)

    current_state: str = Field(default="invited", index=True)
    # invited | scheduled | in_progress | evaluated | shortlisted | decided

    # Transition history: [{from_state, to_state, trigger, actor_id, timestamp}]
    transition_history: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    # Reminder tracking
    last_reminder_sent_at: Optional[datetime] = None
    reminder_count: int = Field(default=0)

    # Decision outcome (when state = "decided")
    decision: Optional[str] = None  # "hired" | "rejected"
    decided_by: Optional[int] = Field(default=None, foreign_key="user.id")
    decided_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_workflow_candidate_drive", "candidate_id", "job_drive_id", unique=True),
    )
