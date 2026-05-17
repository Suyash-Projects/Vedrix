"""
Admin schemas for audit logs and system configuration.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AuditLogBase(BaseModel):
    user_id: Optional[int] = None
    action: str
    target: str
    ip_address: Optional[str] = None
    details: Optional[str] = None
    status_code: Optional[int] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogRead(AuditLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    """Schema for updating system configuration."""
    ai_provider: Optional[str] = None
    rate_limit_per_minute: Optional[int] = None
    session_timeout_minutes: Optional[int] = None
    max_interview_duration_minutes: Optional[int] = None
    enable_email_notifications: Optional[bool] = None
    enable_audit_logging: Optional[bool] = None


class SystemConfigRead(BaseModel):
    """Schema for system configuration."""
    ai_provider: str
    rate_limit_per_minute: int
    session_timeout_minutes: int
    max_interview_duration_minutes: int
    enable_email_notifications: bool
    enable_audit_logging: bool
    version: str
    environment: str
