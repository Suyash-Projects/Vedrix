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
        # The user requested to only count candidates whom we have sent invites to.
        participant_count = len(tokens)
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
        
    # Delete associated tokens and sessions first to prevent orphans
    tokens_result = await db.execute(select(DriveInviteToken).where(DriveInviteToken.drive_id == drive_id))
    for t in tokens_result.scalars().all():
        await db.delete(t)
        
    sessions_result = await db.execute(select(InterviewSession).where(InterviewSession.job_drive_id == drive_id))
    for s in sessions_result.scalars().all():
        await db.delete(s)

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
    total_invited = 0
    for email in invite_in.emails:
        total_invited += 1
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
            # Create an invite token purely for tracking the invite metric
            db.add(DriveInviteToken(
                drive_id=drive_id,
                token=str(uuid.uuid4()),
                candidate_email=email,
                expires_at=expires_at,
                is_used=True
            ))
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
    return {"invited": total_invited, "links": links}


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

    user_ids = [s.candidate_id for s in sessions if s.candidate_id]
    users = []
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = users_result.scalars().all()
    user_map = {u.id: u.email for u in users}

    candidates = []
    for t in tokens:
        matching_session = None
        for s in sessions:
            if user_map.get(s.candidate_id) == t.candidate_email:
                matching_session = s
                break
        
        status = "pending"
        if matching_session:
            status = matching_session.status
        else:
            expires = t.expires_at if t.expires_at.tzinfo else t.expires_at.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                status = "expired"

        candidates.append({
            "email": t.candidate_email,
            "status": status,
            "expires_at": t.expires_at,
            "score": matching_session.overall_score if matching_session else None,
            "session_id": matching_session.id if matching_session else None
        })

    return {
        "total_invited": len(tokens),
        "total_completed": len([s for s in sessions if s.status == "completed"]),
        "candidates": candidates
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
            # Phase 1A: Advisor fields
            "advisor_ready_to_close": row[0].advisor_ready_to_close,
            "advisor_confidence": row[0].advisor_confidence,
            "advisor_reason": row[0].advisor_reason,
            "advisor_reason_category": row[0].advisor_reason_category,
            "advisor_suggested_at": row[0].advisor_suggested_at,
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


# ── Phase 1A: HR Close Interview Endpoint ─────────────────────────────────────

@router.post("/interviews/{session_id}/close")
async def hr_close_interview(
    session_id: int,
    body: dict = None,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """
    HR closes an active interview session.
    Updates status to 'hr_closed' and marks advisor action as taken.
    """
    hr_profile = await _get_hr_profile(db, current_hr.id)

    result = await db.execute(
        select(InterviewSession).join(
            JobDrive, InterviewSession.job_drive_id == JobDrive.id
        ).where(
            InterviewSession.id == session_id,
            JobDrive.hr_id == hr_profile.id,
            InterviewSession.status == "in_progress"
        )
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Active interview session not found")

    session.status = "hr_closed"
    session.end_time = datetime.now(timezone.utc)
    session.advisor_action_taken = True
    if body and body.get("message"):
        session.advisor_reason = body.get("message")

    db.add(session)
    await db.commit()

    return {
        "status": "closed",
        "session_id": session_id,
        "message": "Interview closed by HR",
    }


# ── Phase 3: Analytics & Reporting ──────────────────────────────────────────

@router.get("/interviews/{session_id}/skill-gap")
async def get_skill_gap_analysis(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Get detailed skill gap analysis for a completed interview session."""
    hr_profile = await _get_hr_profile(db, current_hr.id)

    result = await db.execute(
        select(InterviewSession, JobDrive)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id, isouter=True)
        .where(
            InterviewSession.id == session_id,
            JobDrive.hr_id == hr_profile.id
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Interview session not found")

    session, drive = row

    if session.status != "completed" or not session.overall_score:
        raise HTTPException(status_code=400, detail="Session is not completed yet")

    # Get candidate skills from skill_matrix
    skill_matrix = session.skill_matrix or {}
    if isinstance(skill_matrix, str):
        try:
            import json
            skill_matrix = json.loads(skill_matrix)
        except (json.JSONDecodeError, TypeError):
            skill_matrix = {}

    # Get required skills from drive
    required_skills = {}
    if drive and drive.skills_required:
        for skill in drive.skills_required.split(","):
            skill = skill.strip().lower()
            if skill:
                required_skills[skill] = 8.0  # Default required level

    # If no drive skills defined, infer from ai_feedback
    ai_feedback = session.ai_feedback or {}
    if isinstance(ai_feedback, str):
        try:
            import json
            ai_feedback = json.loads(ai_feedback)
        except (json.JSONDecodeError, TypeError):
            ai_feedback = {}

    # Build candidate skill scores
    candidate_skills = {}
    for topic, score in (skill_matrix or {}).items():
        topic_lower = topic.lower()
        candidate_skills[topic_lower] = round(float(score), 1)

    # Also include metrics from ai_feedback
    metric_map = {
        "technical_accuracy": "Technical Accuracy",
        "communication_clarity": "Communication",
        "depth_of_knowledge": "Depth of Knowledge",
    }
    for metric_key, display_name in metric_map.items():
        val = ai_feedback.get(metric_key)
        if val is not None:
            candidate_skills[display_name.lower()] = round(float(val), 1)

    # Calculate gaps
    gaps = {}
    all_skills = set(list(candidate_skills.keys()) + list(required_skills.keys()))
    for skill in all_skills:
        candidate_score = candidate_skills.get(skill, 0)
        required_score = required_skills.get(skill, 0)
        gaps[skill] = round(candidate_score - required_score, 1)

    # Generate recommendations
    recommendations = []
    weaknesses = ai_feedback.get("weaknesses", [])
    if weaknesses:
        for w in weaknesses:
            recommendations.append(f"Focus on: {w}")

    for skill, gap in sorted(gaps.items(), key=lambda x: x[1]):
        if gap < -1.0:
            recommendations.append(f"Significant gap in {skill} (gap: {gap}). Consider targeted practice.")
        elif gap < 0:
            recommendations.append(f"Minor gap in {skill} (gap: {gap}). Review fundamentals.")

    if not recommendations:
        recommendations.append("Candidate meets or exceeds role requirements across all assessed areas.")

    return {
        "session_id": session_id,
        "job_role": drive.job_role if drive else "General",
        "candidate_skills": candidate_skills,
        "required_skills": required_skills,
        "gaps": gaps,
        "overall_match_score": round(
            sum(1 for g in gaps.values() if g >= 0) / max(len(gaps), 1) * 100, 1
        ),
        "recommendations": recommendations,
    }


@router.get("/interviews/{session_id}/replay")
async def get_interview_replay(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Get full interview transcript with timestamps for replay."""
    hr_profile = await _get_hr_profile(db, current_hr.id)

    result = await db.execute(
        select(InterviewSession, User, JobDrive)
        .join(User, InterviewSession.candidate_id == User.id)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id, isouter=True)
        .where(
            InterviewSession.id == session_id,
            JobDrive.hr_id == hr_profile.id
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Interview session not found")

    session, candidate, drive = row

    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Session is not completed yet")

    # Get transcript (responses)
    responses = session.responses or []
    if isinstance(responses, str):
        try:
            import json
            responses = json.loads(responses)
        except (json.JSONDecodeError, TypeError):
            responses = []

    # Get questions
    questions = session.questions or []
    if isinstance(questions, str):
        try:
            import json
            questions = json.loads(questions)
        except (json.JSONDecodeError, TypeError):
            questions = []

    # Get skill matrix
    skill_matrix = session.skill_matrix or {}
    if isinstance(skill_matrix, str):
        try:
            import json
            skill_matrix = json.loads(skill_matrix)
        except (json.JSONDecodeError, TypeError):
            skill_matrix = {}

    # Get AI feedback
    ai_feedback = session.ai_feedback or {}
    if isinstance(ai_feedback, str):
        try:
            import json
            ai_feedback = json.loads(ai_feedback)
        except (json.JSONDecodeError, TypeError):
            ai_feedback = {}

    # Build replay steps
    steps = []
    q_idx = 0
    for msg in responses:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "assistant":
            # This is an AI question
            step = {
                "type": "question",
                "speaker": "AI Interviewer",
                "content": content,
                "question_index": q_idx,
            }
            # Attach question metadata if available
            if q_idx < len(questions):
                q_meta = questions[q_idx]
                if isinstance(q_meta, dict):
                    step["category"] = q_meta.get("category", "")
                    step["difficulty"] = q_meta.get("difficulty", "")
                    step["skill_tested"] = q_meta.get("skill_tested", "")
            steps.append(step)
        elif role == "user":
            # This is a candidate answer
            step = {
                "type": "answer",
                "speaker": "Candidate",
                "content": content,
                "question_index": q_idx - 1 if q_idx > 0 else 0,
            }
            # Try to attach evaluation if available from ai_feedback
            steps.append(step)
            q_idx += 1

    # Calculate timing info
    start_time = session.start_time
    end_time = session.end_time
    duration_secs = session.duration or 0

    return {
        "session_id": session_id,
        "candidate_name": f"{candidate.first_name} {candidate.last_name}".strip(),
        "candidate_email": candidate.email,
        "job_role": drive.job_role if drive else "General",
        "drive_title": drive.title if drive else "Practice Interview",
        "overall_score": session.overall_score,
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "duration_seconds": duration_secs,
        "steps": steps,
        "ai_feedback": ai_feedback,
        "skill_matrix": skill_matrix,
    }


@router.get("/analytics/export/csv")
async def export_interviews_csv(
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Export all HR's interview data as CSV."""
    from app.services.export_service import export_service

    hr_profile = await _get_hr_profile(db, current_hr.id)

    # Fetch all interviews for this HR's drives
    query = (
        select(InterviewSession, User, JobDrive)
        .join(User, InterviewSession.candidate_id == User.id)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id)
        .where(JobDrive.hr_id == hr_profile.id)
    )
    result = await db.execute(query)
    rows = result.all()

    interviews = []
    for session, user, drive in rows:
        interviews.append({
            "id": session.id,
            "candidate_email": user.email,
            "candidate_name": f"{user.first_name} {user.last_name}".strip(),
            "job_role": drive.job_role,
            "drive_title": drive.title,
            "overall_score": session.overall_score,
            "ai_feedback": session.ai_feedback,
            "skill_matrix": session.skill_matrix,
            "status": session.status,
            "duration": session.duration,
            "created_at": session.created_at,
        })

    csv_content = export_service.interviews_to_csv(interviews)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=vedrix_interviews_export.csv"
        }
    )


# ── Bulk Import ─────────────────────────────────────────────────────────────

@router.get("/import/template")
async def get_import_template(
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Get CSV template for candidate import."""
    from app.services.bulk_import import bulk_import_service

    template = bulk_import_service.get_csv_template()
    return Response(
        content=template,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=candidate_import_template.csv"
        }
    )


@router.post("/import/validate")
async def validate_import(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Validate CSV import data before importing."""
    from app.services.bulk_import import bulk_import_service
    from app.models.user import User as UserModel

    body = await request.json()
    csv_content = body.get("csv_content", "")

    if not csv_content:
        raise HTTPException(status_code=400, detail="No CSV content provided")

    # Get existing emails
    result = await db.execute(select(UserModel.email))
    existing_emails = {email.lower() for email in result.scalars().all()}

    # Validate
    import_result = bulk_import_service.process_import(
        csv_content=csv_content,
        existing_emails=existing_emails,
        dry_run=True,
    )

    return import_result


@router.post("/import/execute")
async def execute_import(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Execute CSV import after validation."""
    from app.services.bulk_import import bulk_import_service
    from app.models.user import User as UserModel
    from app.models.profile import StudentProfile
    from app.core import security

    body = await request.json()
    csv_content = body.get("csv_content", "")

    if not csv_content:
        raise HTTPException(status_code=400, detail="No CSV content provided")

    # Get existing emails
    result = await db.execute(select(UserModel.email))
    existing_emails = {email.lower() for email in result.scalars().all()}

    # Validate first
    import_result = bulk_import_service.process_import(
        csv_content=csv_content,
        existing_emails=existing_emails,
        dry_run=False,
    )

    if import_result.invalid_rows > 0 or import_result.duplicate_rows > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Import has validation errors",
                "errors": import_result.errors,
            },
        )

    # Create users
    created_users = []
    for candidate in import_result.candidates:
        # Check again for race conditions
        if candidate["email"] in existing_emails:
            continue

        user = User(
            email=candidate["email"],
            username=candidate["username"],
            password_hash=security.get_password_hash(candidate["password"]),
            first_name=candidate["first_name"],
            last_name=candidate["last_name"],
            user_type=candidate["role"],
            is_active=True,
        )
        db.add(user)
        created_users.append({
            "email": candidate["email"],
            "username": candidate["username"],
            "password": candidate["password"],
            "first_name": candidate["first_name"],
            "last_name": candidate["last_name"],
        })
        existing_emails.add(candidate["email"])

    await db.commit()

    # Send credentials emails in background
    for user_data in created_users:
        background_tasks.add_task(
            send_credentials_email,
            user_data["email"],
            user_data["first_name"],
            user_data["username"],
            user_data["password"],
            "student",
        )

    return {
        "status": "success",
        "imported": len(created_users),
        "users": created_users,
    }


# ── Feedback & Communication ────────────────────────────────────────────────

@router.post("/feedback/candidate")
async def submit_candidate_feedback(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """Submit candidate feedback survey after interview completion."""
    from app.models.feedback import CandidateFeedback

    body = await request.json()
    session_id = body.get("session_id")
    candidate_id = body.get("candidate_id")

    if not session_id or not candidate_id:
        raise HTTPException(status_code=400, detail="session_id and candidate_id are required")

    # Check if feedback already exists
    existing = await db.execute(
        select(CandidateFeedback).where(
            CandidateFeedback.session_id == session_id,
            CandidateFeedback.candidate_id == candidate_id,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Feedback already submitted for this session")

    feedback = CandidateFeedback(
        session_id=session_id,
        candidate_id=candidate_id,
        rating=body.get("rating", 0),
        questions_relevant=body.get("questions_relevant"),
        interview_length=body.get("interview_length"),
        would_recommend=body.get("would_recommend"),
        additional_feedback=body.get("additional_feedback"),
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return {"status": "success", "message": "Feedback submitted successfully"}


@router.get("/feedback/candidate/{session_id}")
async def get_candidate_feedback(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Get candidate feedback for a specific session."""
    from app.models.feedback import CandidateFeedback

    result = await db.execute(
        select(CandidateFeedback).where(CandidateFeedback.session_id == session_id)
    )
    feedback = result.scalars().first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return feedback


@router.post("/feedback/hr")
async def submit_hr_feedback(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Submit HR feedback for a candidate."""
    from app.models.feedback import HRFeedback
    from app.models.profile import HRProfile

    hr_profile = await _get_hr_profile(db, current_hr.id)

    body = await request.json()
    session_id = body.get("session_id")
    candidate_id = body.get("candidate_id")

    if not session_id or not candidate_id:
        raise HTTPException(status_code=400, detail="session_id and candidate_id are required")

    # Check if feedback already exists
    existing = await db.execute(
        select(HRFeedback).where(
            HRFeedback.session_id == session_id,
            HRFeedback.hr_id == hr_profile.id,
        )
    )
    existing_feedback = existing.scalars().first()

    if existing_feedback:
        # Update existing feedback
        existing_feedback.strengths = body.get("strengths", existing_feedback.strengths)
        existing_feedback.weaknesses = body.get("weaknesses", existing_feedback.weaknesses)
        existing_feedback.hire_recommendation = body.get("hire_recommendation", existing_feedback.hire_recommendation)
        existing_feedback.notes = body.get("notes", existing_feedback.notes)
        existing_feedback.rating = body.get("rating", existing_feedback.rating)
        existing_feedback.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing_feedback)
        return {"status": "success", "message": "Feedback updated successfully"}

    # Create new feedback
    feedback = HRFeedback(
        session_id=session_id,
        candidate_id=candidate_id,
        hr_id=hr_profile.id,
        strengths=body.get("strengths"),
        weaknesses=body.get("weaknesses"),
        hire_recommendation=body.get("hire_recommendation"),
        notes=body.get("notes"),
        rating=body.get("rating"),
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return {"status": "success", "message": "Feedback submitted successfully"}


@router.get("/feedback/hr/{session_id}")
async def get_hr_feedback(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Get HR feedback for a specific session."""
    from app.models.feedback import HRFeedback
    from app.models.profile import HRProfile

    hr_profile = await _get_hr_profile(db, current_hr.id)

    result = await db.execute(
        select(HRFeedback).where(
            HRFeedback.session_id == session_id,
            HRFeedback.hr_id == hr_profile.id,
        )
    )
    feedback = result.scalars().first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return feedback


@router.get("/feedback/hr/all")
async def list_hr_feedback(
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """List all HR feedback entries."""
    from app.models.feedback import HRFeedback
    from app.models.profile import HRProfile

    hr_profile = await _get_hr_profile(db, current_hr.id)

    result = await db.execute(
        select(HRFeedback).where(HRFeedback.hr_id == hr_profile.id).order_by(HRFeedback.created_at.desc())
    )
    feedback_list = result.scalars().all()

    return feedback_list


# ── Interview Scheduling ────────────────────────────────────────────────────

@router.post("/interviews/schedule")
async def schedule_interview(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """Schedule a new interview session."""
    from app.models.interview import InterviewSession
    from app.models.profile import HRProfile

    hr_profile = await _get_hr_profile(db, current_hr.id)

    body = await request.json()
    drive_id = body.get("drive_id")
    candidate_email = body.get("candidate_email")
    scheduled_time = body.get("scheduled_time")
    notes = body.get("notes", "")

    if not drive_id or not candidate_email or not scheduled_time:
        raise HTTPException(status_code=400, detail="drive_id, candidate_email, and scheduled_time are required")

    # Verify drive exists and belongs to this HR
    drive_result = await db.execute(
        select(JobDrive).where(JobDrive.id == drive_id, JobDrive.hr_id == hr_profile.id)
    )
    drive = drive_result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found or you don't have access")

    # Check if candidate already exists
    user_result = await db.execute(select(User).where(User.email == candidate_email.lower()))
    user = user_result.scalars().first()

    if not user:
        # Create a new user for the candidate
        import secrets
        username = candidate_email.split('@')[0].lower()
        # Ensure username is unique
        base_username = username
        counter = 1
        while True:
            check = await db.execute(select(User).where(User.username == username))
            if not check.scalars().first():
                break
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            email=candidate_email.lower(),
            username=username,
            password_hash=security.get_password_hash(secrets.token_urlsafe(8)),
            first_name=candidate_email.split('@')[0].title(),
            last_name="",
            user_type="student",
            is_active=True,
        )
        db.add(user)
        await db.flush()

    # Check if interview already scheduled for this drive and candidate
    existing = await db.execute(
        select(InterviewSession).where(
            InterviewSession.job_drive_id == drive_id,
            InterviewSession.candidate_id == user.id,
            InterviewSession.status == "scheduled",
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Interview already scheduled for this candidate")

    # Create scheduled interview session
    session = InterviewSession(
        candidate_id=user.id,
        job_drive_id=drive_id,
        status="scheduled",
        session_type="scheduled",
        start_time=datetime.fromisoformat(scheduled_time),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Send invite email in background
    if drive.is_active:
        background_tasks.add_task(
            send_invite_email,
            candidate_email,
            drive.job_role,
            drive.title,
            f"{settings.FRONTEND_URL}/interview?drive_id={drive_id}",
            24,
            drive.skills_required,
        )

    return {
        "status": "success",
        "message": "Interview scheduled successfully",
        "session_id": session.id,
        "candidate_email": candidate_email,
        "scheduled_time": scheduled_time,
    }


@router.get("/interviews")
async def list_hr_interviews(
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr)
) -> Any:
    """List all interviews for HR's drives."""
    from app.models.profile import HRProfile

    hr_profile = await _get_hr_profile(db, current_hr.id)

    # Get all drives for this HR
    drives_result = await db.execute(
        select(JobDrive).where(JobDrive.hr_id == hr_profile.id)
    )
    drives = drives_result.scalars().all()
    drive_ids = [d.id for d in drives]

    if not drive_ids:
        return {"interviews": []}

    # Get all sessions for these drives
    sessions_result = await db.execute(
        select(InterviewSession).where(InterviewSession.job_drive_id.in_(drive_ids))
    )
    sessions = sessions_result.scalars().all()

    interviews = []
    for session in sessions:
        user_result = await db.execute(select(User).where(User.id == session.candidate_id))
        user = user_result.scalars().first()

        drive_result = await db.execute(select(JobDrive).where(JobDrive.id == session.job_drive_id))
        drive = drive_result.scalars().first()

        interviews.append({
            "id": session.id,
            "candidate_id": session.candidate_id,
            "candidate_name": f"{user.first_name} {user.last_name}".strip() if user else "Unknown",
            "candidate_email": user.email if user else "",
            "job_role": drive.job_role if drive else "",
            "drive_title": drive.title if drive else "",
            "status": session.status,
            "overall_score": session.overall_score,
            "scheduled_time": session.start_time.isoformat() if session.start_time else None,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration": session.duration,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        })

    return {"interviews": interviews}
