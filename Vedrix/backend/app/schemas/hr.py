from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
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
    description: Optional[str] = None
    experience_required: Optional[str] = None
    skills_required: Optional[str] = None
    is_active: Optional[bool] = None

class JobDriveRead(JobDriveBase):
    id: int
    hr_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MagicLinkRequest(BaseModel):
    candidate_email: Optional[str] = None  # audit #26: associate email with single link
    expires_in_hours: int = 72

class MagicLinkResponse(BaseModel):
    link: str
    token: str

class BulkInviteRequest(BaseModel):
    emails: List[str]
    expires_in_hours: int = 72

class BulkInviteResponse(BaseModel):
    invited: int
    links: List[MagicLinkResponse]
