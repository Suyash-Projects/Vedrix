"""
Audit Log model for tracking system actions.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)
    action: str = Field(nullable=False, index=True)  # e.g., "POST /api/v1/users"
    target: str = Field(nullable=False)  # e.g., "user:12"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    ip_address: Optional[str] = Field(default=None)
    details: Optional[str] = Field(default=None, sa_column=Column(Text))
    status_code: Optional[int] = Field(default=None)
