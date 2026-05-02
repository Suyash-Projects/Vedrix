from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

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
    created_at: datetime = Field(default_factory=datetime.utcnow)

class JobDrive(SQLModel, table=True):
    __tablename__ = "job_drive"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hr_id: int = Field(foreign_key="hr_profile.id", nullable=False)
    title: str = Field(nullable=False)
    description: Optional[str] = None
    job_role: str = Field(nullable=False)
    experience_required: Optional[str] = None
    skills_required: Optional[str] = None  # JSON string
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    hr: "HRProfile" = Relationship(back_populates="job_drives")
    interview_sessions: List["InterviewSession"] = Relationship(back_populates="job_drive")

class InterviewSession(SQLModel, table=True):
    __tablename__ = "interview_session"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False)
    job_drive_id: Optional[int] = Field(default=None, foreign_key="job_drive.id")
    session_type: str = Field(nullable=False)  # 'practice', 'actual'
    status: str = Field(default="scheduled")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    questions: Optional[str] = None  # JSON
    responses: Optional[str] = None  # JSON
    ai_feedback: Optional[str] = None  # JSON
    overall_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    candidate: "User" = Relationship(back_populates="interview_sessions")
    job_drive: Optional["JobDrive"] = Relationship(back_populates="interview_sessions")
