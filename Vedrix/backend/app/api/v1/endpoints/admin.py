from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import InterviewSession
from app.schemas.user import UserRead

router = APIRouter()

@router.get("/users", response_model=List[UserRead])
async def read_users(
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """List all users in the system."""
    result = await db.execute(select(User))
    return result.scalars().all()

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Delete a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return {"status": "success", "message": "User deleted"}

@router.get("/stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(deps.get_current_admin),
) -> Any:
    """Get global system statistics."""
    user_count = await db.execute(select(func.count(User.id)))
    session_count = await db.execute(select(func.count(InterviewSession.id)))
    
    return {
        "total_users": user_count.scalar(),
        "total_sessions": session_count.scalar(),
        "system_status": "Healthy",
        "version": "1.0.0"
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
            "created_at": s.created_at,
        }
        for s in sessions
    ]
