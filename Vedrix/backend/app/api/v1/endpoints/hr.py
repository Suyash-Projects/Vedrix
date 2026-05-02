from typing import Any, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import JobDrive
from app.models.profile import HRProfile
from app.schemas.hr import JobDriveCreate, JobDriveRead, MagicLinkResponse

router = APIRouter()

@router.post("/drives", response_model=JobDriveRead)
async def create_job_drive(
    drive_in: JobDriveCreate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Create a new Job Drive."""
    # Find HR Profile
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_hr.id))
    hr_profile = result.scalars().first()
    
    if not hr_profile:
        raise HTTPException(status_code=400, detail="HR Profile not found. Please complete your profile first.")
    
    drive = JobDrive(
        **drive_in.model_dump(),
        hr_id=hr_profile.id
    )
    db.add(drive)
    await db.commit()
    await db.refresh(drive)
    return drive

@router.get("/drives", response_model=List[JobDriveRead])
async def list_job_drives(
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """List all Job Drives created by the HR expert."""
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_hr.id))
    hr_profile = result.scalars().first()
    
    if not hr_profile:
        return []
        
    result = await db.execute(select(JobDrive).where(JobDrive.hr_id == hr_profile.id))
    return result.scalars().all()

@router.post("/drives/{drive_id}/magic-link", response_model=MagicLinkResponse)
async def generate_magic_link(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Generate a unique Magic Link (one-time token) for a specific job drive."""
    result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
    drive = result.scalars().first()
    
    if not drive:
        raise HTTPException(status_code=404, detail="Job Drive not found")
        
    # Generate a unique token
    token = str(uuid.uuid4())
    # In a real app, we might store this token in a separate 'InterviewInvite' table
    # For now, let's use the drive ID and token in the link
    # The link will be handled by the frontend
    link = f"http://localhost:5173/interview/guest?drive_id={drive_id}&token={token}"
    
    return {"link": link, "token": token}
