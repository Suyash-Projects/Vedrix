from typing import Any
import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import InterviewSession

router = APIRouter()


@router.get("/stats")
async def get_student_stats(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    result = await db.execute(
        select(InterviewSession).where(InterviewSession.candidate_id == current_user.id)
    )
    sessions = result.scalars().all()
    completed = [s for s in sessions if s.status == "completed" and s.overall_score is not None]
    avg_score = round(sum(s.overall_score for s in completed) / len(completed), 1) if completed else None

    return {
        "total_interviews": len(sessions),
        "completed_interviews": len(completed),
        "avg_score": avg_score,
        "best_score": max((s.overall_score for s in completed), default=None),
    }


@router.get("/interviews")
async def get_student_interviews(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.candidate_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "status": s.status,
            "overall_score": s.overall_score,
            "session_type": s.session_type,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "created_at": s.created_at,
        }
        for s in sessions
    ]
