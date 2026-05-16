from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .profile import StudentProfile, HRProfile
    from .interview import InterviewSession

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    username: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    user_type: str = Field(nullable=False)  # 'student', 'hr', 'admin'
    role: str = Field(default="user")
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    phone: Optional[str] = None
    profile_photo: Optional[str] = None
    is_active: bool = Field(default=True)

    # Account security — failed login tracking and lockout
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None)

    # Phase 1.5: Soft delete support
    deleted_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    student_profile: Optional["StudentProfile"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    hr_profile: Optional["HRProfile"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    # back_populates must match the relationship name on InterviewSession
    interview_sessions: List["InterviewSession"] = Relationship(back_populates="candidate")
