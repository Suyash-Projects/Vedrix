from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime

class JobDriveBase(BaseModel):
    title: str
    description: Optional[str] = None
    job_role: str
    experience_required: Optional[str] = None
    skills_required: Optional[str] = None
    is_active: bool = True

class JobDriveCreate(JobDriveBase):
    pass

class JobDriveUpdate(JobDriveBase):
    title: Optional[str] = None
    job_role: Optional[str] = None

class JobDriveRead(JobDriveBase):
    id: int
    hr_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MagicLinkResponse(BaseModel):
    link: str
    token: str

class BulkInviteRequest(BaseModel):
    emails: List[str]
    expires_in_hours: int = 72

class BulkInviteResponse(BaseModel):
    invited: int
    links: List[MagicLinkResponse]
