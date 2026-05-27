from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .user import User
    from .interview import JobDrive, InterviewSession

class InterviewSlot(SQLModel, table=True):
    __tablename__ = "interview_slot"

    id: Optional[int] = Field(default=None, primary_key=True)
    drive_id: int = Field(foreign_key="job_drive.id", nullable=False)
    start_time: datetime = Field(nullable=False)
    end_time: datetime = Field(nullable=False)
    max_candidates: int = Field(default=1, nullable=False)
    booked_count: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    bookings: List["SlotBooking"] = Relationship(back_populates="slot")


class SlotBooking(SQLModel, table=True):
    __tablename__ = "slot_booking"

    id: Optional[int] = Field(default=None, primary_key=True)
    slot_id: int = Field(foreign_key="interview_slot.id", nullable=False)
    candidate_id: int = Field(foreign_key="user.id", nullable=False)
    session_id: Optional[int] = Field(default=None, foreign_key="interview_session.id")
    reminder_sent: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    slot: "InterviewSlot" = Relationship(back_populates="bookings")
