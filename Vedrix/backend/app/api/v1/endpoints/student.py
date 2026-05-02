from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import InterviewSession

router = APIRouter()

@router.get("/interviews")
async def list_my_interviews(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """List all interview sessions for the current student."""
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.candidate_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "session_type": s.session_type,
            "status": s.status,
            "overall_score": s.overall_score,
            "created_at": s.created_at,
            "end_time": s.end_time,
        }
        for s in sessions
    ]

@router.get("/stats")
async def get_my_stats(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Get performance statistics for the current student."""
    # 1. Total Sessions
    total_result = await db.execute(
        select(func.count(InterviewSession.id))
        .where(InterviewSession.candidate_id == current_user.id)
    )
    total_sessions = total_result.scalar() or 0

    # 2. Average Score
    avg_result = await db.execute(
        select(func.avg(InterviewSession.overall_score))
        .where(InterviewSession.candidate_id == current_user.id, InterviewSession.status == "completed")
    )
    avg_score = round(avg_result.scalar() or 0.0, 1)

    # 3. Best Score
    best_result = await db.execute(
        select(func.max(InterviewSession.overall_score))
        .where(InterviewSession.candidate_id == current_user.id, InterviewSession.status == "completed")
    )
    best_score = best_result.scalar() or 0.0

    # 4. Recent scores for chart
    recent_result = await db.execute(
        select(InterviewSession.overall_score, InterviewSession.created_at)
        .where(InterviewSession.candidate_id == current_user.id, InterviewSession.status == "completed")
        .order_by(InterviewSession.created_at.asc())
        .limit(10)
    )
    recent_data = recent_result.all()
    
    chart_data = [
        {"date": d[1].strftime("%b %d"), "score": d[0]}
        for d in recent_data if d[0] is not None
    ]

    return {
        "total_sessions": total_sessions,
        "avg_score": avg_score,
        "best_score": best_score,
        "chart_data": chart_data
    }
