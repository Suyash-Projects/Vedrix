"""
Memory Agent API — Longitudinal Profile read endpoint.

Exposes candidate skill history and trend directions to HR_Users and Admins.
Requirements: 1.10
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.services.memory_service import memory_service

router = APIRouter()


class SkillScoreEntry(BaseModel):
    """A single skill score observation from an interview session."""
    score: float
    session_id: int
    timestamp: str


class SkillProfileEntry(BaseModel):
    """Frontend-friendly skill summary derived from longitudinal profile data."""
    name: str
    average_score: float
    trend: str = "stable"
    history: List[Dict[str, Any]] = Field(default_factory=list)


class LongitudinalProfileResponse(BaseModel):
    """
    Response schema for the Memory Agent profile endpoint.

    Includes per-skill trend direction (improving, stable, declining)
    as required by Requirement 1.10.
    """
    id: int
    candidate_id: int
    skill_history: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Per-skill chronological score history: {skill: [{score, session_id, timestamp}]}"
    )
    skill_averages: Dict[str, float] = Field(
        default_factory=dict,
        description="Running average score per skill"
    )
    skill_trends: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-skill trend direction: 'improving', 'stable', or 'declining'"
    )
    skills: List[SkillProfileEntry] = Field(
        default_factory=list,
        description="Compatibility projection for frontend charts."
    )
    github_last_indexed: Optional[datetime] = None
    linkedin_last_indexed: Optional[datetime] = None
    enrichment_sources: Dict[str, Any] = Field(default_factory=dict)
    coaching_effectiveness: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/profiles/{candidate_id}", response_model=LongitudinalProfileResponse)
async def get_candidate_profile(
    candidate_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve a candidate's LongitudinalProfile including skill history and trend directions.

    **Access**: HR_Users and Admins can view candidates; students can view only their own profile.

    Returns per-skill trend direction (improving / stable / declining) computed
    from the candidate's chronological score history across all interview sessions.
    """
    if current_user.user_type == "student" and current_user.id != candidate_id:
        raise HTTPException(status_code=403, detail="Students can only view their own profile")
    if current_user.user_type not in ("student", "hr", "admin"):
        raise HTTPException(status_code=403, detail="Role not authorized to view profiles")

    profile = await memory_service.get_or_create_profile(candidate_id=candidate_id, db=db)
    if not profile:
        raise HTTPException(status_code=404, detail="Longitudinal profile not found")

    skill_history = profile.skill_history or {}
    skill_averages = profile.skill_averages or {}
    skill_trends = profile.skill_trends or {}
    skills = [
        SkillProfileEntry(
            name=skill,
            average_score=float(avg_score or 0.0),
            trend=skill_trends.get(skill, "stable"),
            history=[
                {
                    **entry,
                    "date": entry.get("timestamp"),
                }
                for entry in skill_history.get(skill, [])
            ],
        )
        for skill, avg_score in skill_averages.items()
    ]

    return LongitudinalProfileResponse(
        id=profile.id,
        candidate_id=profile.candidate_id,
        skill_history=skill_history,
        skill_averages=skill_averages,
        skill_trends=skill_trends,
        skills=skills,
        github_last_indexed=profile.github_last_indexed,
        linkedin_last_indexed=profile.linkedin_last_indexed,
        enrichment_sources=profile.enrichment_sources or {},
        coaching_effectiveness=profile.coaching_effectiveness or {},
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
