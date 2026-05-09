import logging
import asyncio
from sqlalchemy.exc import IntegrityError
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api import deps
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.models.interview import JobDrive, InterviewSession, DriveInviteToken
from app.models.profile import HRProfile
from app.schemas.hr import (
    JobDriveCreate, JobDriveRead, JobDriveUpdate, MagicLinkRequest, MagicLinkResponse,
    BulkInviteRequest, BulkInviteResponse
)
from app.services.email_service import send_invite_email
from app.services.pdf_service import generate_interview_pdf
from app.core.rate_limit import limiter
from app.db.supabase_client import supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()

# Audit #15: use settings instead of hardcoded localhost
FRONTEND_BASE_URL = settings.FRONTEND_URL


async def _sync_drive_to_supabase(drive_data: dict) -> None:
    """Fire-and-forget: mirror a job drive record to Supabase Postgres."""
    if not supabase_client:
        return
    try:
        # Audit: Use to_thread to avoid blocking the event loop
        await asyncio.to_thread(supabase_client.table("job_drive").upsert(drive_data).execute)
    except Exception as exc:
        logger.warning("Supabase drive sync failed (non-fatal): %s", exc)


async def _sync_session_to_supabase(session_data: dict) -> None:
    """Fire-and-forget: mirror an interview session record to Supabase Postgres."""
    if not supabase_client:
        return
    try:
        # Audit: Use to_thread to avoid blocking the event loop
        await asyncio.to_thread(supabase_client.table("interview_session").upsert(session_data).execute)
    except Exception as exc:
        logger.warning("Supabase session sync failed (non-fatal): %s", exc)


async def _get_hr_profile(db: AsyncSession, user_id: int) -> HRProfile:
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="HR Profile not found. Please complete your profile setup."
        )
    return profile


def _calculate_hr_profile_completion(profile: HRProfile) -> int:
    required_fields = [profile.company_name, profile.department, profile.position]
    filled_count = sum(1 for field in required_fields if field and str(field).strip())
    return int((filled_count / len(required_fields)) * 100)


# ── DRIVES ──────────────────────────────────────────────────────────────────

@router.post("/drives", response_model=JobDriveRead)
async def create_job_drive(
    drive_in: JobDriveCreate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    hr_profile = await _get_hr_profile(db, current_hr.id)
    try:
        drive = JobDrive(**drive_in.model_dump(), hr_id=hr_profile.id)
        db.add(drive)
        await db.commit()
        await db.refresh(drive)
        return drive
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError creating JobDrive: {e}")
        raise HTTPException(status_code=400, detail="Failed to create drive due to a database constraint.")
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create JobDrive")
        raise HTTPException(status_code=500, detail="Failed to create drive. Please try again.")


@router.get("/profile-check")
async def profile_check(
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    """Lightweight endpoint to verify HR profile existence and completion for the current HR user."""
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_hr.id))
    profile = result.scalars().first()
    if not profile:
        return {
            "has_profile": False,
            "hr_profile_id": None,
            "completion": 0,
        }

    completion = _calculate_hr_profile_completion(profile)
    return {
        "has_profile": completion >= 50,
        "hr_profile_id": profile.id,
        "completion": completion,
    }


@router.get("/profile")
async def get_hr_profile(
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_hr.id))
    profile = result.scalars().first()
    if not profile:
        # Return empty defaults — profile auto-created on registration
        return {
            "id": None,
            "company_name": "",
            "department": "",
            "position": "",
            "hr_code": None,
            "created_at": None,
            "updated_at": None,
        }
    return {
        "id": profile.id,
        "company_name": profile.company_name or "",
        "department": profile.department or "",
        "position": profile.position or "",
        "hr_code": profile.hr_code,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


class HRProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


@router.put("/profile")
async def update_hr_profile(
    profile_in: HRProfileUpdate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_hr.id))
    profile = result.scalars().first()
    if not profile:
        # Auto-create if missing
        profile = HRProfile(
            user_id=current_hr.id,
            company_name=profile_in.company_name or "Not specified"
        )
        db.add(profile)
    for field, value in profile_in.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(profile, field, value)
    profile.updated_at = datetime.now(timezone.utc)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return {
        "id": profile.id,
        "company_name": profile.company_name or "",
        "department": profile.department or "",
        "position": profile.position or "",
        "updated_at": profile.updated_at,
    }


@router.get("/drives")
@limiter.limit("20/minute")
async def list_job_drives(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_hr.id))
    hr_profile = result.scalars().first()
    if not hr_profile:
        return []

    drives_result = await db.execute(
        select(JobDrive).where(JobDrive.hr_id == hr_profile.id)
    )
    drives = drives_result.scalars().all()

    enriched = []
    for drive in drives:
        sessions_result = await db.execute(
            select(InterviewSession).where(InterviewSession.job_drive_id == drive.id)
        )
        sessions = sessions_result.scalars().all()
        tokens_result = await db.execute(
            select(DriveInviteToken).where(DriveInviteToken.drive_id == drive.id)
        )
        tokens = tokens_result.scalars().all()
        completed = [s for s in sessions if s.overall_score is not None]
        avg_score = (
            round(sum(s.overall_score for s in completed) / len(completed), 1)
            if completed else None
        )
        participant_count = max(len(tokens), len(sessions))
        enriched.append({
            "id": drive.id,
            "hr_id": drive.hr_id,
            "title": drive.title,
            "description": drive.description,
            "job_role": drive.job_role,
            "experience_required": drive.experience_required,
            "skills_required": drive.skills_required,
            "is_active": drive.is_active,
            "created_at": drive.created_at,
            "updated_at": drive.updated_at,
            "participant_count": participant_count,
            "invite_count": len(tokens),
            "avg_score": avg_score,
        })
    return enriched


@router.delete("/drives/{drive_id}")
async def delete_drive(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    hr_profile = await _get_hr_profile(db, current_hr.id)
    result = await db.execute(
        select(JobDrive).where(JobDrive.id == drive_id, JobDrive.hr_id == hr_profile.id)
    )
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    await db.delete(drive)
    await db.commit()
    return {"status": "deleted"}


@router.put("/drives/{drive_id}", response_model=JobDriveRead)
async def update_job_drive(
    drive_id: int,
    drive_in: JobDriveUpdate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Update a job drive."""
    hr_profile = await _get_hr_profile(db, current_hr.id)
    result = await db.execute(
        select(JobDrive).where(JobDrive.id == drive_id, JobDrive.hr_id == hr_profile.id)
    )
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    
    update_data = drive_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(drive, field, value)
    
    drive.updated_at = datetime.now(timezone.utc)
    db.add(drive)
    await db.commit()
    await db.refresh(drive)
    return drive


@router.patch("/drives/{drive_id}/toggle", response_model=JobDriveRead)
async def toggle_job_drive(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Toggle job drive status (Open/Closed)."""
    hr_profile = await _get_hr_profile(db, current_hr.id)
    result = await db.execute(
        select(JobDrive).where(JobDrive.id == drive_id, JobDrive.hr_id == hr_profile.id)
    )
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    
    drive.is_active = not drive.is_active
    drive.updated_at = datetime.now(timezone.utc)
    db.add(drive)
    await db.commit()
    await db.refresh(drive)
    return drive


# ── INVITE LINKS ─────────────────────────────────────────────────────────────

@router.post("/drives/{drive_id}/magic-link", response_model=MagicLinkResponse)
@limiter.limit("10/minute")
async def generate_magic_link(
    request: Request,
    drive_id: int,
    magic_request: MagicLinkRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    hr_profile = await _get_hr_profile(db, current_hr.id)
    result = await db.execute(
        select(JobDrive).where(JobDrive.id == drive_id, JobDrive.hr_id == hr_profile.id)
    )
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Job Drive not found")

    token = str(uuid.uuid4())
    invite = DriveInviteToken(
        drive_id=drive_id,
        token=token,
        candidate_email=magic_request.candidate_email,  # audit #26
        expires_at=datetime.now(timezone.utc) + timedelta(hours=magic_request.expires_in_hours)
    )
    db.add(invite)
    await db.commit()

    link = f"{FRONTEND_BASE_URL}?drive_id={drive_id}&token={token}"

    # Send invite email if email provided
    if magic_request.candidate_email:
        background_tasks.add_task(
            send_invite_email,
            magic_request.candidate_email,
            drive.job_role,
            drive.title,
            link,
            magic_request.expires_in_hours,
            drive.skills_required,
        )

    return {"link": link, "token": token}


@router.post("/drives/{drive_id}/bulk-invite", response_model=BulkInviteResponse)
@limiter.limit("10/minute")
async def bulk_invite_candidates(
    request: Request,
    drive_id: int,
    invite_in: BulkInviteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    hr_profile = await _get_hr_profile(db, current_hr.id)
    result = await db.execute(
        select(JobDrive).where(JobDrive.id == drive_id, JobDrive.hr_id == hr_profile.id)
    )
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Job Drive not found")

    expires_at = datetime.now(timezone.utc) + timedelta(hours=invite_in.expires_in_hours)
    links = []
    for email in invite_in.emails:
        # Check if user already exists
        user_result = await db.execute(select(User).where(User.email == email))
        existing_user = user_result.scalars().first()
        
        if existing_user:
            # Create scheduled interview session for existing user
            new_session = InterviewSession(
                candidate_id=existing_user.id,
                job_drive_id=drive_id,
                session_type="actual",
                status="scheduled",
            )
            db.add(new_session)
            # Send notification email to existing user
            background_tasks.add_task(
                send_invite_email,
                email,
                drive.job_role,
                drive.title,
                f"{FRONTEND_BASE_URL}/dashboard",  # Link to dashboard
                invite_in.expires_in_hours,
                drive.skills_required,
            )
        else:
            # Send invite email for new user
            token = str(uuid.uuid4())
            link = f"{FRONTEND_BASE_URL}?drive_id={drive_id}&token={token}"
            db.add(DriveInviteToken(
                drive_id=drive_id,
                token=token,
                candidate_email=email,
                expires_at=expires_at
            ))
            links.append({"link": link, "token": token})
            background_tasks.add_task(
                send_invite_email,
                email,
                drive.job_role,
                drive.title,
                link,
                invite_in.expires_in_hours,
                drive.skills_required,
            )

    await db.commit()
    return {"invited": len(links), "links": links}


# ── CANDIDATES PER DRIVE ─────────────────────────────────────────────────────

@router.get("/drives/{drive_id}/candidates")
async def list_drive_candidates(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    hr_profile = await _get_hr_profile(db, current_hr.id)
    drive_result = await db.execute(
        select(JobDrive).where(JobDrive.id == drive_id, JobDrive.hr_id == hr_profile.id)
    )
    if not drive_result.scalars().first():
        raise HTTPException(status_code=404, detail="Drive not found")

    tokens_result = await db.execute(
        select(DriveInviteToken).where(DriveInviteToken.drive_id == drive_id)
    )
    tokens = tokens_result.scalars().all()

    sessions_result = await db.execute(
        select(InterviewSession).where(InterviewSession.job_drive_id == drive_id)
    )
    sessions = sessions_result.scalars().all()

    return {
        "total_invited": len(tokens),
        "total_completed": len([s for s in sessions if s.status == "completed"]),
        "candidates": [
            {
                "email": t.candidate_email,
                "token": t.token,
                "is_used": t.is_used,
                "expires_at": t.expires_at,
            }
            for t in tokens
        ],
        "sessions": [
            {
                "id": s.id,
                "status": s.status,
                "overall_score": s.overall_score,
                "start_time": s.start_time,
                "end_time": s.end_time,
            }
            for s in sessions
        ]
    }


# ── INTERVIEWS ───────────────────────────────────────────────────────────────

@router.get("/interviews")
async def list_hr_interviews(
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == current_hr.id))
    hr_profile = result.scalars().first()
    if not hr_profile:
        return []
    query = (
        select(InterviewSession, JobDrive.title, JobDrive.job_role, User.email, User.first_name, User.last_name)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id)
        .join(User, InterviewSession.candidate_id == User.id)
        .where(JobDrive.hr_id == hr_profile.id)
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "id": row[0].id,
            "candidate_id": row[0].candidate_id,
            "candidate_email": row[3],
            "candidate_name": f"{row[4]} {row[5]}".strip(),
            "job_drive_id": row[0].job_drive_id,
            "status": row[0].status,
            "overall_score": row[0].overall_score,
            "ai_feedback": row[0].ai_feedback,
            "skill_matrix": row[0].skill_matrix,
            "created_at": row[0].created_at,
            "drive_title": row[1],
            "job_role": row[2],
        }
        for row in rows
    ]


@router.get("/interviews/{session_id}")
async def get_interview_details(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    hr_profile = await _get_hr_profile(db, current_hr.id)

    result = await db.execute(
        select(InterviewSession).join(
            JobDrive, InterviewSession.job_drive_id == JobDrive.id
        ).where(
            InterviewSession.id == session_id,
            JobDrive.hr_id == hr_profile.id
        )
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")

    return {
        "id": session.id,
        "candidate_id": session.candidate_id,
        "job_drive_id": session.job_drive_id,
        "status": session.status,
        "overall_score": session.overall_score,
        "questions": session.questions,
        "responses": session.responses,
        "ai_feedback": session.ai_feedback,
        "skill_matrix": session.skill_matrix,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "duration": session.duration,
        "created_at": session.created_at,
    }


@router.get("/interviews/{session_id}/pdf")
async def export_interview_pdf(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    hr_profile = await _get_hr_profile(db, current_hr.id)

    # Fetch session and associated candidate/drive
    result = await db.execute(
        select(InterviewSession, User, JobDrive)
        .join(User, InterviewSession.candidate_id == User.id)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id)
        .where(
            InterviewSession.id == session_id,
            JobDrive.hr_id == hr_profile.id
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    session, candidate, drive = row
    
    # Native JSON columns — no loads needed
    transcript = session.responses or []
    report = session.ai_feedback or {}
    
    # Use real PDF service (Issue #8)
    # Audit: Use to_thread for blocking PDF generation
    pdf_bytes = await asyncio.to_thread(
        generate_interview_pdf,
        candidate_name=f"{candidate.first_name} {candidate.last_name}",
        job_role=drive.job_role,
        report=report,
        transcript=transcript
    )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Vedrix_Report_{session.id}.pdf"
        }
    )
