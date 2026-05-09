from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .user import User
    from .interview import JobDrive

class StudentProfile(SQLModel, table=True):
    __tablename__ = "student_profile"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, nullable=False)
    university: Optional[str] = None
    degree: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None
    skills: Optional[str] = None  # JSON string
    resume_file: Optional[str] = None
    resume_text: Optional[str] = None
    experience_level: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    user: "User" = Relationship(back_populates="student_profile")

class HRProfile(SQLModel, table=True):
    __tablename__ = "hr_profile"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, nullable=False)
    company_name: str = Field(nullable=False)
    department: Optional[str] = None
    position: Optional[str] = None
    hr_code: Optional[str] = Field(default=None, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    user: "User" = Relationship(back_populates="hr_profile")
    job_drives: List["JobDrive"] = Relationship(back_populates="hr")
