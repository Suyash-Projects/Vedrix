from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import InterviewSession
from app.schemas.user import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return current_user


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
        "transcript": responses,
        "status": session.status,
        "start_time": session.start_time,
        "end_time": session.end_time,
    }
