import asyncio
import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.session import async_session, get_session
from app.models.user import User
from app.models.profile import StudentProfile, HRProfile
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


async def _trigger_profile_enrichment(candidate_id: int) -> None:
    """
    Background task: run the Research Agent to enrich a newly created profile.

    Opens its own async DB session (the request-scoped session is closed once
    the response is returned) and only enriches when a GitHub or LinkedIn URL
    is present on the candidate's profile.

    Requirements: 9.1, 9.2, 9.5
    """
    try:
        from app.services.research_service import research_service

        async with async_session() as db:
            result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == candidate_id)
            )
            profile = result.scalars().first()
            if not profile:
                return
            if not (profile.github_url or profile.linkedin_url):
                return

            await research_service.enrich_profile(candidate_id, profile, db=db)
    except Exception as exc:  # noqa: BLE001 — background task must not crash the loop
        logger.warning(
            "Research Agent enrichment failed for candidate_id=%s: %s",
            candidate_id,
            exc,
        )

class StudentProfileCreate(BaseModel):
    # Academic
    university: Optional[str] = None
    degree: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None
    major: Optional[str] = None
    minor: Optional[str] = None

    # Skills & Experience
    skills: Optional[str] = None
    experience_level: Optional[str] = None
    work_experience: Optional[str] = None
    internships: Optional[str] = None

    # Resume
    resume_file: Optional[str] = None
    resume_text: Optional[str] = None

    # Additional Profile Fields
    projects: Optional[str] = None
    certifications: Optional[str] = None
    languages: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    hackathons: Optional[str] = None

    # Additional Info
    expected_salary: Optional[str] = None
    preferred_locations: Optional[str] = None
    availability: Optional[str] = None
    interests: Optional[str] = None

class HRProfileCreate(BaseModel):
    # Company Info
    company_name: str
    company_website: Optional[str] = None
    company_size: Optional[str] = None
    company_industry: Optional[str] = None

    # HR Info
    department: Optional[str] = None
    position: Optional[str] = None

    # LinkedIn & Social
    linkedin_url: Optional[str] = None

    # Recruiting Info
    hiring_volume: Optional[str] = None
    common_roles: Optional[str] = None
    tech_stack: Optional[str] = None

    # Interview Preferences
    interview_duration: Optional[int] = None
    include_coding_challenge: Optional[bool] = None

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
    
    is_new_profile = db_profile is None
    if db_profile:
        for field, value in profile_in.model_dump(exclude_unset=True).items():
            setattr(db_profile, field, value)
        db.add(db_profile)
    else:
        db_profile = StudentProfile(**profile_in.model_dump(), user_id=current_user.id)
        db.add(db_profile)
    
    await db.commit()

    # Research Agent: enrich a newly created profile in the background when it
    # carries a GitHub or LinkedIn URL. Uses asyncio.create_task with its own DB
    # session so it survives after the request-scoped session is closed.
    if is_new_profile and (db_profile.github_url or db_profile.linkedin_url):
        asyncio.create_task(_trigger_profile_enrichment(current_user.id))

    return {"status": "success", "message": "Student profile updated"}

@router.put("/student", response_model=dict)
async def update_student_profile(
    profile_in: StudentProfileCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_session)
) -> Any:
    """Update a student profile."""
    return await create_student_profile(profile_in, current_user, db)

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
            # Academic
            "university": None, "degree": None, "graduation_year": None, "gpa": None, "major": None, "minor": None,
            # Skills & Experience
            "skills": None, "experience_level": None, "work_experience": None, "internships": None,
            # Resume
            "resume_file": None, "resume_text": None,
            # Additional Profile Fields
            "projects": None, "certifications": None, "languages": None,
            "linkedin_url": None, "github_url": None, "portfolio_url": None, "hackathons": None,
            # Additional Info
            "expected_salary": None, "preferred_locations": None, "availability": None, "interests": None,
        }

    return {
        # Academic
        "university": profile.university, "degree": profile.degree, "graduation_year": profile.graduation_year,
        "gpa": profile.gpa, "major": profile.major, "minor": profile.minor,
        # Skills & Experience
        "skills": profile.skills, "experience_level": profile.experience_level,
        "work_experience": profile.work_experience, "internships": profile.internships,
        # Resume
        "resume_file": profile.resume_file, "resume_text": profile.resume_text,
        # Additional Profile Fields
        "projects": profile.projects, "certifications": profile.certifications, "languages": profile.languages,
        "linkedin_url": profile.linkedin_url, "github_url": profile.github_url,
        "portfolio_url": profile.portfolio_url, "hackathons": profile.hackathons,
        # Additional Info
        "expected_salary": profile.expected_salary, "preferred_locations": profile.preferred_locations,
        "availability": profile.availability, "interests": profile.interests,
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

@router.put("/hr", response_model=dict)
async def update_hr_profile(
    profile_in: HRProfileCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_session)
) -> Any:
    """Update an HR profile."""
    return await create_hr_profile(profile_in, current_user, db)

@router.get("/hr", response_model=dict)
async def get_hr_profile(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_session)
) -> Any:
    """Retrieve the current HR's profile."""
    if current_user.user_type != 'hr':
        raise HTTPException(status_code=400, detail="User is not registered as HR")

    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if not profile:
        return {
            "company_name": None, "company_website": None, "company_size": None, "company_industry": None,
            "department": None, "position": None, "linkedin_url": None,
            "hiring_volume": None, "common_roles": None, "tech_stack": None,
            "interview_duration": None, "include_coding_challenge": None,
        }

    return {
        "company_name": profile.company_name, "company_website": profile.company_website,
        "company_size": profile.company_size, "company_industry": profile.company_industry,
        "department": profile.department, "position": profile.position,
        "linkedin_url": profile.linkedin_url,
        "hiring_volume": profile.hiring_volume, "common_roles": profile.common_roles, "tech_stack": profile.tech_stack,
        "interview_duration": profile.interview_duration, "include_coding_challenge": profile.include_coding_challenge,
    }
