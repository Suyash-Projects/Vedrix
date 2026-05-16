from typing import Any, List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
import uuid

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import JobDrive, InterviewSession, DriveInviteToken, ScenarioTemplate
from app.models.profile import HRProfile, StudentProfile
from app.schemas.user import UserRead, UserCreate, UserUpdate
from app.schemas.hr import JobDriveRead, JobDriveCreate, JobDriveUpdate, MagicLinkRequest, MagicLinkResponse, BulkInviteRequest, BulkInviteResponse
from app.schemas.interview import ScenarioTemplateRead, ScenarioTemplateCreate, ScenarioTemplateUpdate
from app.core import security
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.email_service import send_invite_email, send_credentials_email
from app.services.pdf_service import generate_interview_pdf
import asyncio

router = APIRouter()

# ── User Management ──────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserRead])
async def read_users(
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """List all users in the system."""
    result = await db.execute(select(User))
    return result.scalars().all()


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
    user_in: UserCreate,
) -> Any:
    """Admin creates a new user account."""
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    # Check username uniqueness
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=user_in.email,
        username=user_in.username,
        password_hash=security.get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        user_type=user_in.user_type,
    )
    db.add(user)
    await db.flush()

    # Auto-create profile for HR/student
    if user_in.user_type == 'hr':
        from app.models.profile import HRProfile
        profile = HRProfile(user_id=user.id, company_name=user_in.company_name or "Not specified")
        db.add(profile)
    elif user_in.user_type == 'student':
        from app.models.profile import StudentProfile
        profile = StudentProfile(user_id=user.id)
        db.add(profile)

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Get a specific user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
    user_in: UserUpdate,
) -> Any:
    """Update user details (name, email, etc)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If changing email, check uniqueness
    if user_in.email and user_in.email != user.email:
        result = await db.execute(select(User).where(User.email == user_in.email, User.id != user_id))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")

    # If changing username, check uniqueness
    if user_in.username and user_in.username != user.username:
        result = await db.execute(select(User).where(User.username == user_in.username, User.id != user_id))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Username already taken")

    # Update fields
    update_data = user_in.model_dump(exclude_unset=True, exclude={'password'})
    for field, value in update_data.items():
        setattr(user, field, value)

    # If password is being updated
    if user_in.password:
        user.password_hash = security.get_password_hash(user_in.password)

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Deactivate a user account (block login)."""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.commit()
    return {"status": "success", "message": f"User {user.username} deactivated"}


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Activate a deactivated user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    await db.commit()
    return {"status": "success", "message": f"User {user.username} activated"}


@router.patch("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
    body: dict,  # Expects {"role": "student"|"hr"|"admin"}
) -> Any:
    """Change a user's role (student/hr/admin) and sync profiles."""
    role = body.get("role")
    if role not in ("student", "hr", "admin"):
        raise HTTPException(status_code=400, detail="Role must be student, hr, or admin")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.user_type == role:
        return {"status": "success", "message": f"User {user.username} is already {role}"}

    # Delete existing profiles if applicable
    if user.user_type == 'hr':
        hr_profile = (await db.execute(select(HRProfile).where(HRProfile.user_id == user_id))).scalars().first()
        if hr_profile:
            await db.delete(hr_profile)
    elif user.user_type == 'student':
        student_profile = (await db.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))).scalars().first()
        if student_profile:
            await db.delete(student_profile)
            
    # Create new profile
    if role == 'hr':
        profile = HRProfile(user_id=user_id, company_name="Not specified")
        db.add(profile)
    elif role == 'student':
        profile = StudentProfile(user_id=user_id)
        db.add(profile)

    user.user_type = role
    await db.commit()
    return {"status": "success", "message": f"User {user.username} role changed to {role}"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Permanently delete a user account."""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete ALL related data — fetch first, then delete
    from app.models.profile import HRProfile, StudentProfile
    from app.models.interview import InterviewSession

    # Profiles
    hr_profile = (await db.execute(select(HRProfile).where(HRProfile.user_id == user_id))).scalars().first()
    if hr_profile:
        await db.delete(hr_profile)

    student_profile = (await db.execute(select(StudentProfile).where(StudentProfile.user_id == user_id))).scalars().first()
    if student_profile:
        await db.delete(student_profile)

    # Interview sessions
    sessions = (await db.execute(select(InterviewSession).where(InterviewSession.candidate_id == user_id))).scalars().all()
    for session in sessions:
        await db.delete(session)

    # Finally delete the user
    await db.delete(user)
    await db.commit()
    return {"status": "success", "message": "User permanently deleted"}


# ── Stats & Sessions ─────────────────────────────────────────────────────────

@router.get("/stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Get global system statistics."""
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    session_count = (await db.execute(select(func.count(InterviewSession.id)))).scalar()
    active_count = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar()
    student_count = (await db.execute(select(func.count(User.id)).where(User.user_type == 'student'))).scalar()
    hr_count = (await db.execute(select(func.count(User.id)).where(User.user_type == 'hr'))).scalar()
    admin_count = (await db.execute(select(func.count(User.id)).where(User.user_type == 'admin'))).scalar()

    # DB Health check
    try:
        await db.execute(text("SELECT 1"))
        system_status = "Healthy"
    except Exception as e:
        system_status = "Degraded"

    return {
        "total_users": user_count,
        "active_users": active_count,
        "total_sessions": session_count,
        "students": student_count,
        "hr_managers": hr_count,
        "admins": admin_count,
        "system_status": system_status,
        "version": "1.0.0"
    }


@router.get("/ai-health")
async def get_ai_provider_health(
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """
    Get health status of all AI providers and circuit breakers.
    Shows which providers are available, which are in circuit-breaker state,
    and the current fallback chain status.
    """
    from app.services.interview_engine.circuit_breaker import get_all_circuit_breaker_statuses
    from app.services.interview_engine.model_router import TaskType, _get_routes

    # Get circuit breaker statuses
    circuit_statuses = get_all_circuit_breaker_statuses()

    # Get route configurations
    routes = _get_routes()
    route_info = {}
    for task_type, route in routes.items():
        route_info[task_type.value] = {
            "description": route.description,
            "providers": [f"{s.provider}/{s.model_id}" for s in route.chain],
        }

    return {
        "circuit_breakers": circuit_statuses,
        "routes": route_info,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/interviews")
async def list_all_interviews(
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """List all interview sessions across the platform."""
    result = await db.execute(select(InterviewSession))
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "candidate_id": s.candidate_id,
            "job_drive_id": s.job_drive_id,
            "status": s.status,
            "overall_score": s.overall_score,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "duration": s.duration,
            "created_at": s.created_at,
        }
        for s in sessions
    ]


# ═══════════════════════════════════════════════════════════════════════════
# DRIVE MANAGEMENT — Admin has ultimate rights over ALL drives
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/drives")
async def list_all_drives(
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """List ALL job drives across the platform (admin sees everything)."""
    result = await db.execute(select(JobDrive))
    drives = result.scalars().all()

    enriched = []
    for drive in drives:
        # Get HR owner info
        hr_res = await db.execute(select(HRProfile).where(HRProfile.id == drive.hr_id))
        hr_profile = hr_res.scalars().first()
        hr_user = None
        if hr_profile:
            hr_user_res = await db.execute(select(User).where(User.id == hr_profile.user_id))
            hr_user = hr_user_res.scalars().first()

        # Session stats
        sessions_res = await db.execute(
            select(InterviewSession).where(InterviewSession.job_drive_id == drive.id)
        )
        sessions = sessions_res.scalars().all()
        tokens_res = await db.execute(
            select(DriveInviteToken).where(DriveInviteToken.drive_id == drive.id)
        )
        tokens = tokens_res.scalars().all()
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
            "hr_name": f"{hr_user.first_name} {hr_user.last_name}" if hr_user else "Unknown",
            "hr_email": hr_user.email if hr_user else "",
            "total_sessions": len(sessions),
            "completed_sessions": len(completed),
            "avg_score": avg_score,
            "participant_count": max(len(tokens), len(sessions)),
            "invite_count": len(tokens),
        })
    return enriched


@router.get("/drives/{drive_id}")
async def get_drive(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Get a specific drive by ID (admin sees any drive)."""
    result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    hr_res = await db.execute(select(HRProfile).where(HRProfile.id == drive.hr_id))
    hr_profile = hr_res.scalars().first()
    hr_user = None
    if hr_profile:
        hr_user_res = await db.execute(select(User).where(User.id == hr_profile.user_id))
        hr_user = hr_user_res.scalars().first()

    sessions_res = await db.execute(
        select(InterviewSession).where(InterviewSession.job_drive_id == drive_id)
    )
    sessions = sessions_res.scalars().all()
    completed = [s for s in sessions if s.overall_score is not None]

    return {
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
        "hr_name": f"{hr_user.first_name} {hr_user.last_name}" if hr_user else "Unknown",
        "hr_email": hr_user.email if hr_user else "",
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
        "avg_score": (
            round(sum(s.overall_score for s in completed) / len(completed), 1)
            if completed else None
        ),
    }


@router.post("/drives", response_model=JobDriveRead, status_code=201)
async def create_drive(
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
    drive_in: JobDriveCreate,
    hr_id: int,
) -> Any:
    """Admin creates a job drive for a specific HR."""
    # Verify HR exists
    hr_res = await db.execute(select(HRProfile).where(HRProfile.id == hr_id))
    hr_profile = hr_res.scalars().first()
    if not hr_profile:
        raise HTTPException(status_code=404, detail="HR profile not found")

    drive = JobDrive(**drive_in.model_dump(), hr_id=hr_id)
    db.add(drive)
    await db.commit()
    await db.refresh(drive)
    return drive


@router.patch("/drives/{drive_id}", response_model=JobDriveRead)
async def update_drive(
    drive_id: int,
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
    drive_in: JobDriveUpdate,
) -> Any:
    """Admin updates any drive on the platform."""
    result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
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
async def toggle_drive(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin toggles any drive active/inactive."""
    result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    drive.is_active = not drive.is_active
    drive.updated_at = datetime.now(timezone.utc)
    db.add(drive)
    await db.commit()
    await db.refresh(drive)
    return drive


@router.delete("/drives/{drive_id}")
async def delete_drive(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin deletes any drive on the platform."""
    result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    # Delete related invite tokens
    tokens_res = await db.execute(select(DriveInviteToken).where(DriveInviteToken.drive_id == drive_id))
    for token in tokens_res.scalars().all():
        await db.delete(token)

    # Delete related sessions
    sessions_res = await db.execute(select(InterviewSession).where(InterviewSession.job_drive_id == drive_id))
    for session in sessions_res.scalars().all():
        await db.delete(session)

    await db.delete(drive)
    await db.commit()
    return {"status": "success", "message": f"Drive '{drive.title}' and all its data deleted"}


@router.get("/drives/{drive_id}/candidates")
async def list_drive_candidates(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin views candidates for any drive."""
    result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    tokens_res = await db.execute(select(DriveInviteToken).where(DriveInviteToken.drive_id == drive_id))
    tokens = tokens_res.scalars().all()

    sessions_res = await db.execute(select(InterviewSession).where(InterviewSession.job_drive_id == drive_id))
    sessions = sessions_res.scalars().all()

    # Get candidate info for sessions
    candidate_info = []
    for s in sessions:
        user_res = await db.execute(select(User).where(User.id == s.candidate_id))
        user = user_res.scalars().first()
        if user:
            candidate_info.append({
                "id": s.id,
                "email": user.email,
                "name": f"{user.first_name} {user.last_name}",
                "status": s.status,
                "overall_score": s.overall_score,
                "start_time": s.start_time,
                "end_time": s.end_time,
            })

    return {
        "drive": {
            "id": drive.id,
            "title": drive.title,
            "job_role": drive.job_role,
            "is_active": drive.is_active,
        },
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
        "sessions": candidate_info,
    }


@router.post("/drives/{drive_id}/magic-link")
async def generate_drive_magic_link(
    drive_id: int,
    magic_request: MagicLinkRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin generates a magic invite link for any drive."""
    result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    token = str(uuid.uuid4())
    invite = DriveInviteToken(
        drive_id=drive_id,
        token=token,
        candidate_email=magic_request.candidate_email,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=magic_request.expires_in_hours),
    )
    db.add(invite)
    await db.commit()

    link = f"{settings.FRONTEND_URL}?drive_id={drive_id}&token={token}"

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


@router.get("/drives/{drive_id}/sessions")
async def list_drive_sessions(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin views all interview sessions for any drive."""
    result = await db.execute(select(JobDrive).where(JobDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    sessions_res = await db.execute(
        select(InterviewSession).where(InterviewSession.job_drive_id == drive_id)
    )
    sessions = sessions_res.scalars().all()

    enriched = []
    for s in sessions:
        user_res = await db.execute(select(User).where(User.id == s.candidate_id))
        user = user_res.scalars().first()
        enriched.append({
            "id": s.id,
            "candidate_id": s.candidate_id,
            "candidate_email": user.email if user else "",
            "candidate_name": f"{user.first_name} {user.last_name}" if user else "Unknown",
            "status": s.status,
            "overall_score": s.overall_score,
            "ai_feedback": s.ai_feedback,
            "skill_matrix": s.skill_matrix,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "duration": s.duration,
            "created_at": s.created_at,
        })

    return {
        "drive_id": drive_id,
        "drive_title": drive.title,
        "total_sessions": len(sessions),
        "sessions": enriched,
    }


@router.get("/interviews/{session_id}")
async def get_drive_interview_session(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin views full details of any interview session."""
    result = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_res = await db.execute(select(User).where(User.id == session.candidate_id))
    user = user_res.scalars().first()

    return {
        "id": session.id,
        "candidate_id": session.candidate_id,
        "candidate_email": user.email if user else "",
        "candidate_name": f"{user.first_name} {user.last_name}" if user else "Unknown",
        "job_drive_id": session.job_drive_id,
        "session_type": session.session_type,
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
async def export_admin_interview_pdf(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin exports PDF for any interview session."""
    result = await db.execute(
        select(InterviewSession, User, JobDrive)
        .join(User, InterviewSession.candidate_id == User.id)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id)
        .where(InterviewSession.id == session_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    session, candidate, drive = row

    transcript = session.responses or []
    report = session.ai_feedback or {}

    pdf_bytes = await asyncio.to_thread(
        generate_interview_pdf,
        candidate_name=f"{candidate.first_name} {candidate.last_name}",
        job_role=drive.job_role,
        report=report,
        transcript=transcript,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Vedrix_Report_{session.id}.pdf",
        },
    )

# ── Scenario Template Management ─────────────────────────────────────────────

@router.get("/templates", response_model=List[ScenarioTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """List all scenario templates."""
    result = await db.execute(select(ScenarioTemplate))
    return result.scalars().all()


@router.post("/templates", response_model=ScenarioTemplateRead, status_code=201)
async def create_template(
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
    template_in: ScenarioTemplateCreate,
) -> Any:
    """Create a new scenario template."""
    template = ScenarioTemplate(**template_in.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.patch("/templates/{template_id}", response_model=ScenarioTemplateRead)
async def update_template(
    template_id: int,
    *,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
    template_in: ScenarioTemplateUpdate,
) -> Any:
    """Update an existing scenario template."""
    result = await db.execute(select(ScenarioTemplate).where(ScenarioTemplate.id == template_id))
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = template_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    template.updated_at = datetime.now(timezone.utc)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Delete a scenario template."""
    result = await db.execute(select(ScenarioTemplate).where(ScenarioTemplate.id == template_id))
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()
    return {"status": "success", "message": f"Template '{template.title}' deleted"}


# ── Credentials Management ─────────────────────────────────────────────────────

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin resets a user's password and sends new credentials via email."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate a new random password
    import secrets
    new_password = secrets.token_urlsafe(8)[:8]
    user.password_hash = security.get_password_hash(new_password)
    await db.commit()

    # Send credentials email in background
    background_tasks.add_task(
        send_credentials_email,
        user.email,
        user.first_name or "User",
        user.username,
        new_password,
        user.user_type,
    )

    return {
        "status": "success",
        "message": f"Password reset for {user.username}. New credentials sent to {user.email}",
        "username": user.username,
    }


@router.post("/users/{user_id}/send-credentials")
async def send_user_credentials(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Admin resends login credentials to user's email (keeps existing password)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate a temporary password to include in email (actual password stays the same)
    import secrets
    temp_password = secrets.token_urlsafe(8)[:8]

    # Send credentials email with the temporary password
    background_tasks.add_task(
        send_credentials_email,
        user.email,
        user.first_name or "User",
        user.username,
        temp_password,
        user.user_type,
    )

    return {
        "status": "success",
        "message": f"Credentials sent to {user.email}",
    }
