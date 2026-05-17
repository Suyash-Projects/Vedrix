"""
Feedback models for candidate and HR feedback.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text


class CandidateFeedback(SQLModel, table=True):
    """Feedback from candidates about their interview experience."""
    __tablename__ = "candidate_feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(nullable=False, index=True)
    candidate_id: int = Field(nullable=False, index=True)
    rating: int = Field(nullable=False)  # 1-5 stars
    questions_relevant: Optional[str] = Field(default=None)  # Yes/No/Somewhat
    interview_length: Optional[str] = Field(default=None)  # Too short/Just right/Too long
    would_recommend: Optional[bool] = Field(default=None)
    additional_feedback: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class HRFeedback(SQLModel, table=True):
    """Structured feedback from HR about candidates."""
    __tablename__ = "hr_feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(nullable=False, index=True)
    candidate_id: int = Field(nullable=False, index=True)
    hr_id: int = Field(nullable=False, index=True)
    strengths: Optional[str] = Field(default=None, sa_column=Column(Text))
    weaknesses: Optional[str] = Field(default=None, sa_column=Column(Text))
    hire_recommendation: Optional[str] = Field(default=None)  # Strong Yes/Yes/No/Strong No
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    rating: Optional[int] = Field(default=None)  # 1-10
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
