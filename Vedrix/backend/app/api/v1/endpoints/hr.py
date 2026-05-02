from typing import Any, List, Optional
import uuid
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import JobDrive, InterviewSession, DriveInviteToken
from app.models.profile import HRProfile
from app.schemas.hr import (
    JobDriveCreate, JobDriveRead, MagicLinkResponse,
    BulkInviteRequest, BulkInviteResponse
)
from app.services.email_service import send_invite_email
from app.services.pdf_service import generate_interview_pdf

router = APIRouter()

FRONTEND_BASE_URL = "http://localhost:5173"


async def _get_hr_profile(db: AsyncSession, user_id: int) -> HRProfile:
    result = await db.execute(select(HRProfile).where(HRProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="HR Profile not found. Please complete your profile setup."
        )
    return profile


# ── DRIVES ──────────────────────────────────────────────────────────────────

@router.post("/drives", response_model=JobDriveRead)
async def create_job_drive(
    drive_in: JobDriveCreate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    hr_profile = await _get_hr_profile(db, current_hr.id)
    drive = JobDrive(**drive_in.model_dump(), hr_id=hr_profile.id)
    db.add(drive)
    await db.commit()
    await db.refresh(drive)
    return drive


@router.get("/drives")
async def list_job_drives(
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
        completed = [s for s in sessions if s.overall_score is not None]
        avg_score = (
            round(sum(s.overall_score for s in completed) / len(completed), 1)
            if completed else None
        )
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
            "participant_count": len(sessions),
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


# ── INVITE LINKS ─────────────────────────────────────────────────────────────

@router.post("/drives/{drive_id}/magic-link", response_model=MagicLinkResponse)
async def generate_magic_link(
    drive_id: int,
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
        expires_at=datetime.utcnow() + timedelta(hours=72)
    )
    db.add(invite)
    await db.commit()

    link = f"{FRONTEND_BASE_URL}?drive_id={drive_id}&token={token}"
    return {"link": link, "token": token}


@router.post("/drives/{drive_id}/bulk-invite", response_model=BulkInviteResponse)
async def bulk_invite_candidates(
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

    expires_at = datetime.utcnow() + timedelta(hours=invite_in.expires_in_hours)
    links = []
    for email in invite_in.emails:
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
    hr_profile = await _get_hr_profile(db, current_hr.id)
    # Join with JobDrive to get metadata for the table (Issue #7)
    query = (
        select(InterviewSession, JobDrive.title, JobDrive.job_role)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id)
        .where(JobDrive.hr_id == hr_profile.id)
    )
    result = await db.execute(query)
    rows = result.all()
    
    return [
        {
            "id": s.id,
            "candidate_id": s.candidate_id,
            "job_drive_id": s.job_drive_id,
            "status": s.status,
            "overall_score": s.overall_score,
            "created_at": s.created_at,
            "drive_title": title,
            "job_role": job_role,
        }
        for s, title, job_role in rows
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
    
    # Parse transcript and feedback
    transcript = json.loads(session.responses) if isinstance(session.responses, str) else (session.responses or [])
    report = json.loads(session.ai_feedback) if isinstance(session.ai_feedback, str) else (session.ai_feedback or {})
    
    # Use real PDF service (Issue #8)
    pdf_bytes = generate_interview_pdf(
        candidate_name=f"{candidate.first_name} {candidate.last_name}",
        job_role=drive.job_role,
        report=report,
        transcript=transcript
    )
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Vedrix_Report_{candidate.last_name}.pdf"
        }
    )
