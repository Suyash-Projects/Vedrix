from typing import Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import InterviewSession
from app.schemas.user import UserRead
from app.core import security
from app.services.pdf_service import generate_certificate

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

    if session.overall_score < 60:
        raise HTTPException(status_code=400, detail="Score must be >= 60% to generate certificate")

    candidate_name = current_user.username
    job_role = session.job_role or "General Candidate"
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


@router.post("/change-password")
async def change_password(
    *,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
    current_password: str,
    new_password: str,
) -> Any:
    """Change user's own password (requires current password verification)."""
    if not security.verify_password(current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")

    # Re-fetch user in this session
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalars().first()
    if user:
        user.password_hash = security.get_password_hash(new_password)
        await db.commit()

    return {"status": "success", "message": "Password changed successfully"}


@router.put("/username")
async def update_username(
    *,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
    new_username: str,
) -> Any:
    """Change user's own username (must be unique)."""
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
