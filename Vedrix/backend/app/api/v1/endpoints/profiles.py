from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.profile import StudentProfile, HRProfile
from pydantic import BaseModel

router = APIRouter()

class StudentProfileCreate(BaseModel):
    university: Optional[str] = None
    degree: Optional[str] = None
    graduation_year: Optional[int] = None
    skills: Optional[str] = None

class HRProfileCreate(BaseModel):
    company_name: str
    department: Optional[str] = None
    position: Optional[str] = None

@router.post("/student", response_model=dict)
async def create_student_profile(
    profile_in: StudentProfileCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_session)
) -> Any:
    """Create or update a student profile."""
    if current_user.user_type != 'student':
        raise HTTPException(status_code=400, detail="User is not registered as a student")
    
    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == current_user.id))
    db_profile = result.scalars().first()
    
    if db_profile:
        for field, value in profile_in.model_dump(exclude_unset=True).items():
            setattr(db_profile, field, value)
        db.add(db_profile)
    else:
        db_profile = StudentProfile(**profile_in.model_dump(), user_id=current_user.id)
        db.add(db_profile)
    
    await db.commit()
    return {"status": "success", "message": "Student profile updated"}

@router.get("/student", response_model=dict)
async def get_student_profile(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_session)
) -> Any:
    """Retrieve the current student's profile."""
    if current_user.user_type != 'student':
        raise HTTPException(status_code=400, detail="User is not registered as a student")

    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if not profile:
        return {
            "university": None,
            "degree": None,
            "graduation_year": None,
            "skills": None,
            "resume_file": None,
            "resume_text": None,
            "experience_level": None,
        }

    return {
        "university": profile.university,
        "degree": profile.degree,
        "graduation_year": profile.graduation_year,
        "skills": profile.skills,
        "resume_file": profile.resume_file,
        "resume_text": profile.resume_text,
        "experience_level": profile.experience_level,
    }

@router.post("/hr", response_model=dict)
async def create_hr_profile(
    profile_in: HRProfileCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_session)
) -> Any:
    """Create or update an HR profile."""
    if current_user.user_type != 'hr':
        raise HTTPException(status_code=400, detail="User is not registered as HR")
    
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_user.id))
    db_profile = result.scalars().first()
    
    if db_profile:
        for field, value in profile_in.model_dump(exclude_unset=True).items():
            setattr(db_profile, field, value)
    else:
        db_profile = HRProfile(**profile_in.model_dump(), user_id=current_user.id)
        db.add(db_profile)
    
    await db.commit()
    return {"status": "success", "message": "HR profile updated"}
