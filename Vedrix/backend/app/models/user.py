from datetime import datetime
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    student_profile: Optional["StudentProfile"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    hr_profile: Optional["HRProfile"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    interview_sessions: List["InterviewSession"] = Relationship(back_populates="candidate")
