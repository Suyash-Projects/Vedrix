from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Text
from app.core.encryption import EncryptedString

if TYPE_CHECKING:
    from .user import User
    from .interview import JobDrive

class StudentProfile(SQLModel, table=True):
    __tablename__ = "student_profile"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, nullable=False)

    # Academic
    university: Optional[str] = None
    degree: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None
    major: Optional[str] = None  # e.g., Computer Science
    minor: Optional[str] = None  # e.g., Mathematics

    # Skills & Experience
    skills: Optional[str] = Field(default=None, sa_column=Column(EncryptedString))
    experience_level: Optional[str] = None  # entry/mid/senior
    work_experience: Optional[str] = Field(default=None, sa_column=Column(EncryptedString))
    internships: Optional[str] = Field(default=None, sa_column=Column(EncryptedString))

    # Resume
    resume_file: Optional[str] = None
    resume_text: Optional[str] = Field(default=None, sa_column=Column(EncryptedString))

    # Additional Profile Fields
    projects: Optional[str] = Field(default=None, sa_column=Column(EncryptedString))
    certifications: Optional[str] = Field(default=None, sa_column=Column(EncryptedString))
    languages: Optional[str] = None  # JSON string e.g., ["English-Native", "Spanish-Conversational"]
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    hackathons: Optional[str] = Field(default=None, sa_column=Column(EncryptedString))

    # Additional Info
    expected_salary: Optional[str] = None
    preferred_locations: Optional[str] = None  # JSON string of locations
    availability: Optional[str] = None  # e.g., "Immediately", "2 weeks notice"
    interests: Optional[str] = None  # JSON string of interest areas

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Phase 1.5: Soft delete support
    deleted_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: "User" = Relationship(back_populates="student_profile")

class HRProfile(SQLModel, table=True):
    __tablename__ = "hr_profile"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, nullable=False)

    # Company Info
    company_name: str = Field(nullable=False)
    company_website: Optional[str] = None
    company_size: Optional[str] = None  # e.g., "1-10", "11-50", "51-200", "201-500", "500+"
    company_industry: Optional[str] = None  # e.g., "Technology", "Finance", "Healthcare"

    # HR Info
    department: Optional[str] = None
    position: Optional[str] = None
    hr_code: Optional[str] = Field(default=None, unique=True)

    # LinkedIn & Social
    linkedin_url: Optional[str] = None

    # Recruiting Info
    hiring_volume: Optional[str] = None  # e.g., "1-5", "5-20", "20+ per month"
    common_roles: Optional[str] = None  # JSON string of roles they typically hire for
    tech_stack: Optional[str] = None  # JSON string of technologies they use

    # Interview Preferences
    interview_duration: Optional[int] = None  # in minutes
    include_coding_challenge: Optional[bool] = True

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Phase 1.5: Soft delete support
    deleted_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: "User" = Relationship(back_populates="hr_profile")
    job_drives: List["JobDrive"] = Relationship(back_populates="hr")
