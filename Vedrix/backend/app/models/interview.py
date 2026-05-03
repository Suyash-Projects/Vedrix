from datetime import datetime, timezone
from typing import Optional, List, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, Text

if TYPE_CHECKING:
    from .user import User
    from .profile import HRProfile


class DriveInviteToken(SQLModel, table=True):
    __tablename__ = "drive_invite_token"

    id: Optional[int] = Field(default=None, primary_key=True)
    drive_id: int = Field(foreign_key="job_drive.id", nullable=False)
    token: str = Field(unique=True, index=True, nullable=False)
    candidate_email: Optional[str] = None
    is_used: bool = Field(default=False)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobDrive(SQLModel, table=True):
    __tablename__ = "job_drive"

    id: Optional[int] = Field(default=None, primary_key=True)
    hr_id: int = Field(foreign_key="hr_profile.id", nullable=False)
    title: str = Field(nullable=False)
    description: Optional[str] = None
    job_role: str = Field(nullable=False)
    experience_required: Optional[str] = None
    skills_required: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    hr: "HRProfile" = Relationship(back_populates="job_drives")
    interview_sessions: List["InterviewSession"] = Relationship(back_populates="job_drive")


class InterviewSession(SQLModel, table=True):
    __tablename__ = "interview_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False)
    job_drive_id: Optional[int] = Field(default=None, foreign_key="job_drive.id")
    session_type: str = Field(nullable=False)
    status: str = Field(default="scheduled")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    overall_score: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Native JSON columns — no more manual json.dumps/loads
    questions: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    responses: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    ai_feedback: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    candidate: "User" = Relationship(back_populates="interview_sessions")
    job_drive: Optional["JobDrive"] = Relationship(back_populates="interview_sessions")
