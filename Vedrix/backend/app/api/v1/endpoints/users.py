from typing import Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import InterviewSession, JobDrive
from app.schemas.user import UserRead
from app.core import security
from app.services.pdf_service import generate_certificate, generate_certificate_png


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ChangeUsernameRequest(BaseModel):
    new_username: str

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return current_user


@router.delete("/clear-interviews")
async def clear_my_interviews(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Permanently delete ALL interview data for the current user."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Fetch first, then delete — safer for some async ORM configurations
        result = await db.execute(
            select(InterviewSession).where(InterviewSession.candidate_id == current_user.id)
        )
        sessions = result.scalars().all()
        
        for session in sessions:
            await db.delete(session)
            
        await db.commit()
        return {"status": "success", "message": f"Cleared {len(sessions)} interview sessions."}
    except Exception as e:
        logger.error(f"Error clearing interviews for user {current_user.id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal error clearing data: {str(e)}")


@router.get("/sessions/{session_id}/report")
async def get_session_report(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Fetch report for a session — accessible by the candidate or any HR/admin."""
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.user_type == "student" and session.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Native JSON columns — no json.loads needed
    ai_feedback = session.ai_feedback or {}
    responses = session.responses or []

    return {
        "id": session.id,
        "overall_score": session.overall_score,
        "hire_recommendation": ai_feedback.get("hire_recommendation", "Unknown"),
        "technical_accuracy": ai_feedback.get("technical_accuracy", 0),
        "communication_clarity": ai_feedback.get("communication_clarity", 0),
        "depth_of_knowledge": ai_feedback.get("depth_of_knowledge", 0),
        "strengths": ai_feedback.get("strengths", []),
        "weaknesses": ai_feedback.get("weaknesses", []),
        "summary": ai_feedback.get("summary", "No summary available."),
        "skill_matrix": session.skill_matrix,
        "transcript": responses,
        "status": session.status,
        "start_time": session.start_time,
        "end_time": session.end_time,
    }


@router.get("/sessions/{session_id}/certificate")
async def get_session_certificate(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Response:
    """Generate and download a completion certificate for the session."""
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.user_type == "student" and session.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if (session.overall_score or 0) < 6:
        raise HTTPException(status_code=400, detail="Score must be >= 6/10 to generate certificate")

    candidate_name = current_user.username

    # Resolve job_role from the linked JobDrive (InterviewSession has no job_role column)
    job_role = "General Candidate"
    if session.job_drive_id:
        drive_res = await db.execute(select(JobDrive).where(JobDrive.id == session.job_drive_id))
        drive = drive_res.scalars().first()
        if drive:
            job_role = drive.job_role
    overall_score = float(session.overall_score or 0)
    date_completed = session.end_time.strftime("%B %d, %Y") if session.end_time else datetime.now().strftime("%B %d, %Y")

    pdf_bytes = generate_certificate(
        candidate_name=candidate_name,
        job_role=job_role,
        overall_score=overall_score,
        date_completed=date_completed,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Vedrix_Certificate_{session_id}.pdf"},
    )


@router.get("/sessions/{session_id}/certificate/png")
async def get_session_certificate_png(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Response:
    """Generate and download a certificate as PNG for social sharing."""
    import asyncio

    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.user_type == "student" and session.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if (session.overall_score or 0) < 6:
        raise HTTPException(status_code=400, detail="Score must be >= 6/10 to generate certificate")

    candidate_name = current_user.username

    # Resolve job_role from the linked JobDrive
    job_role = "General Candidate"
    if session.job_drive_id:
        drive_res = await db.execute(select(JobDrive).where(JobDrive.id == session.job_drive_id))
        drive = drive_res.scalars().first()
        if drive:
            job_role = drive.job_role

    overall_score = float(session.overall_score or 0)
    date_completed = session.end_time.strftime("%B %d, %Y") if session.end_time else datetime.now().strftime("%B %d, %Y")

    # Generate verification token
    verification_token = security.generate_verification_token(session_id, candidate_name)

    # Audit: Use to_thread for blocking PNG generation
    png_bytes = await asyncio.to_thread(
        generate_certificate_png,
        candidate_name=candidate_name,
        job_role=job_role,
        overall_score=overall_score,
        date_completed=date_completed,
        verification_token=verification_token,
    )

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=Vedrix_Certificate_{session_id}.png"},
    )


@router.get("/sessions/{session_id}/share-link")
async def get_shareable_link(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Generate a shareable verification link for the certificate."""
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.user_type == "student" and session.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if (session.overall_score or 0) < 6:
        raise HTTPException(status_code=400, detail="Score must be >= 6/10 to share certificate")

    # Generate verification token
    candidate_name = current_user.username
    verification_token = security.generate_verification_token(session_id, candidate_name)

    return {
        "verification_token": verification_token,
        "share_url": f"/verify/{verification_token}",
        "linkedin_url": (
            f"https://www.linkedin.com/sharing/share-offsite/?"
            f"url=https://vedrix.ai/verify/{verification_token}"
        ),
        "certificate_data": {
            "candidate_name": candidate_name,
            "overall_score": session.overall_score,
            "session_id": session_id,
        },
    }


@router.get("/verify/{token}")
async def verify_certificate(
    token: str,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """Verify a certificate using the verification token. Public endpoint (no auth required)."""
    # Decode the verification token
    try:
        session_id, candidate_name = security.decode_verification_token(token)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid or expired verification token")

    result = await db.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if (session.overall_score or 0) < 6:
        raise HTTPException(status_code=404, detail="Certificate not available for this session")

    # Resolve job_role
    job_role = "General Candidate"
    if session.job_drive_id:
        drive_res = await db.execute(select(JobDrive).where(JobDrive.id == session.job_drive_id))
        drive = drive_res.scalars().first()
        if drive:
            job_role = drive.job_role

    # Get candidate name from user
    user_result = await db.execute(select(User).where(User.id == session.candidate_id))
    user = user_result.scalars().first()
    actual_name = user.username if user else "Unknown"

    return {
        "valid": True,
        "candidate_name": actual_name,
        "job_role": job_role,
        "overall_score": session.overall_score,
        "date_completed": session.end_time.strftime("%B %d, %Y") if session.end_time else None,
        "verified_at": datetime.now().isoformat(),
    }


@router.post("/change-password")
async def change_password(
    *,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
    body: ChangePasswordRequest,
) -> Any:
    """Change user's own password (requires current password verification)."""
    if not security.verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")

    # Re-fetch user in this session
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalars().first()
    if user:
        user.password_hash = security.get_password_hash(body.new_password)
        await db.commit()

    return {"status": "success", "message": "Password changed successfully"}


@router.put("/username")
async def update_username(
    *,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
    body: ChangeUsernameRequest,
) -> Any:
    """Change user's own username (must be unique)."""
    new_username = body.new_username
    if len(new_username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    # Check if username is already taken
    result = await db.execute(
        select(User).where(User.username == new_username, User.id != current_user.id)
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Update username - re-fetch user in this session
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalars().first()
    if user:
        user.username = new_username
        await db.commit()

    return {"status": "success", "message": f"Username changed to @{new_username}"}
