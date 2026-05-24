from typing import Any, List
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api import deps
from app.db.session import get_session
from app.models.user import User
from app.models.interview import InterviewSession, JobDrive
from app.models.coaching_plan import CoachingPlan

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
    scores = [s.overall_score for s in completed if s.overall_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    return {
        "total_interviews": len(sessions),
        "completed_interviews": len(completed),
        "avg_score": avg_score,
        "best_score": max(scores, default=None),
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


@router.get("/sessions/{session_id}/skill-gap")
async def get_student_skill_gap(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get skill gap analysis for a student's completed interview."""
    result = await db.execute(
        select(InterviewSession, JobDrive)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id, isouter=True)
        .where(
            InterviewSession.id == session_id,
            InterviewSession.candidate_id == current_user.id,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Interview session not found")

    session, drive = row

    if session.status != "completed" or not session.overall_score:
        raise HTTPException(status_code=400, detail="Session is not completed yet")

    skill_matrix = session.skill_matrix or {}
    if isinstance(skill_matrix, str):
        try:
            skill_matrix = json.loads(skill_matrix)
        except (json.JSONDecodeError, TypeError):
            skill_matrix = {}

    ai_feedback = session.ai_feedback or {}
    if isinstance(ai_feedback, str):
        try:
            ai_feedback = json.loads(ai_feedback)
        except (json.JSONDecodeError, TypeError):
            ai_feedback = {}

    # Build candidate skills
    candidate_skills = {}
    for topic, score in (skill_matrix or {}).items():
        candidate_skills[topic.lower()] = round(float(score), 1)

    metric_map = {
        "technical_accuracy": "technical accuracy",
        "communication_clarity": "communication",
        "depth_of_knowledge": "depth of knowledge",
    }
    for metric_key, display_name in metric_map.items():
        val = ai_feedback.get(metric_key)
        if val is not None:
            candidate_skills[display_name] = round(float(val), 1)

    # Required skills from drive
    required_skills = {}
    if drive and drive.skills_required:
        for skill in drive.skills_required.split(","):
            skill = skill.strip().lower()
            if skill:
                required_skills[skill] = 8.0

    # Calculate gaps
    gaps = {}
    all_skills = set(list(candidate_skills.keys()) + list(required_skills.keys()))
    for skill in all_skills:
        candidate_score = candidate_skills.get(skill, 0)
        required_score = required_skills.get(skill, 0)
        gaps[skill] = round(candidate_score - required_score, 1)

    # Recommendations
    recommendations = []
    weaknesses = ai_feedback.get("weaknesses", [])
    for w in weaknesses:
        recommendations.append(f"Focus on: {w}")

    for skill, gap in sorted(gaps.items(), key=lambda x: x[1]):
        if gap < -1.0:
            recommendations.append(f"Significant gap in {skill} (gap: {gap}). Consider targeted practice.")
        elif gap < 0:
            recommendations.append(f"Minor gap in {skill} (gap: {gap}). Review fundamentals.")

    if not recommendations:
        recommendations.append("Great job! You meet or exceed role requirements.")

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
        "strengths": ai_feedback.get("strengths", []),
        "weaknesses": weaknesses,
    }


@router.get("/sessions/{session_id}/replay")
async def get_student_replay(
    session_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get full interview replay transcript for a student's session."""
    result = await db.execute(
        select(InterviewSession, JobDrive)
        .join(JobDrive, InterviewSession.job_drive_id == JobDrive.id, isouter=True)
        .where(
            InterviewSession.id == session_id,
            InterviewSession.candidate_id == current_user.id,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Interview session not found")

    session, drive = row

    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Session is not completed yet")

    responses = session.responses or []
    if isinstance(responses, str):
        try:
            responses = json.loads(responses)
        except (json.JSONDecodeError, TypeError):
            responses = []

    questions = session.questions or []
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except (json.JSONDecodeError, TypeError):
            questions = []

    skill_matrix = session.skill_matrix or {}
    if isinstance(skill_matrix, str):
        try:
            skill_matrix = json.loads(skill_matrix)
        except (json.JSONDecodeError, TypeError):
            skill_matrix = {}

    ai_feedback = session.ai_feedback or {}
    if isinstance(ai_feedback, str):
        try:
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
            step = {
                "type": "question",
                "speaker": "AI Interviewer",
                "content": content,
                "question_index": q_idx,
            }
            if q_idx < len(questions):
                q_meta = questions[q_idx]
                if isinstance(q_meta, dict):
                    step["category"] = q_meta.get("category", "")
                    step["difficulty"] = q_meta.get("difficulty", "")
                    step["skill_tested"] = q_meta.get("skill_tested", "")
            steps.append(step)
        elif role == "user":
            step = {
                "type": "answer",
                "speaker": "Candidate",
                "content": content,
                "question_index": q_idx - 1 if q_idx > 0 else 0,
            }
            steps.append(step)
            q_idx += 1

    return {
        "session_id": session_id,
        "job_role": drive.job_role if drive else "Practice Interview",
        "overall_score": session.overall_score,
        "duration_seconds": session.duration or 0,
        "steps": steps,
        "ai_feedback": ai_feedback,
        "skill_matrix": skill_matrix,
    }


@router.get("/coaching-plans")
async def get_student_coaching_plans(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get all coaching plans for the current authenticated candidate."""
    result = await db.execute(
        select(CoachingPlan)
        .where(CoachingPlan.candidate_id == current_user.id)
        .order_by(CoachingPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return [
        {
            "id": plan.id,
            "session_id": plan.session_id,
            "top_3_gaps": plan.top_3_gaps,
            "generation_time_ms": plan.generation_time_ms,
            "notification_sent_at": plan.notification_sent_at,
            "created_at": plan.created_at,
        }
        for plan in plans
    ]


@router.get("/coaching-plans/{plan_id}")
async def get_student_coaching_plan_detail(
    plan_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get a single coaching plan with full skill_gaps and resources for the current candidate."""
    result = await db.execute(
        select(CoachingPlan).where(
            CoachingPlan.id == plan_id,
            CoachingPlan.candidate_id == current_user.id,
        )
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Coaching plan not found")

    return {
        "id": plan.id,
        "session_id": plan.session_id,
        "candidate_id": plan.candidate_id,
        "skill_gaps": plan.skill_gaps,
        "top_3_gaps": plan.top_3_gaps,
        "generation_time_ms": plan.generation_time_ms,
        "notification_sent_at": plan.notification_sent_at,
        "created_at": plan.created_at,
    }
