from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import SQLModel, Field, Column
from app.core.encryption import EncryptedJSON

class ViolationRecord(SQLModel, table=True):
    __tablename__ = "violation_record"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="interview_session.id", nullable=False, index=True)

    violation_type: str = Field(nullable=False, index=True)  # tab_switch | paste_detected | anomalous_typing
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)

    # Type-specific payload (encrypted — may contain content)
    payload: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))

    # Consent status at time of detection
    consent_granted: bool = Field(default=False)
