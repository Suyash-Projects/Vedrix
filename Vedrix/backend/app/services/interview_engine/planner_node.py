import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session
from app.models.interview import InterviewSession, JobDrive
from app.models.interview_plan import InterviewPlan
from app.services.memory_service import memory_service, PlannerContext
from app.services.observability_service import trace_agent_action
from app.services.interview_engine.providers import get_fast_llm
from app.services.interview_engine.circuit_breaker import execute_with_circuit_breaker
from app.services.interview_engine.state import InterviewState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class PhaseDetail(BaseModel):
    phase: str = Field(description="Name of phase: greeting, welcome, warmup, technical, stress, behavioral, closing")
    skill: str = Field(description="Skill targeted in this phase")
    difficulty: str = Field(description="Difficulty target: easy, medium, hard")
    question_count: int = Field(description="Number of questions in this phase")
    topics: List[str] = Field(description="Specific sub-topics to cover")

class InterviewPlanSchema(BaseModel):
    phases: List[PhaseDetail] = Field(description="Chronological list of interview phases")

class PlannerNode:
    async def __call__(self, state: InterviewState) -> Dict[str, Any]:
        """
        LangGraph node entry point. Opens a DB session and delegates to the decorated helper.
        """
        async with async_session() as db:
            return await self.process_planning(state, db=db)

    @trace_agent_action("planner_agent", "generate_plan")
    async def process_planning(self, state: InterviewState, db: AsyncSession) -> Dict[str, Any]:
        """
        Retrieve candidate longitudinal history, compute skill difficulties,
        and generate a custom InterviewPlan using LLM with 5s timeout & circuit breaker.
        """
        if state.get("interview_plan"):
            return {}

        session_id_str = state.get("supervisor_session_id")
        session_id = int(session_id_str) if session_id_str else None

        candidate_id = None
        job_drive_id = None
        skills_required = list(state.get("skills_to_cover") or [])

        # Fetch session to get job drive required skills
        if session_id:
            stmt = select(InterviewSession).where(InterviewSession.id == session_id)
            res = await db.execute(stmt)
            session_rec = res.scalars().first()
            if session_rec:
                candidate_id = session_rec.candidate_id
                job_drive_id = session_rec.job_drive_id
                if job_drive_id:
                    drive_stmt = select(JobDrive).where(JobDrive.id == job_drive_id)
                    drive_res = await db.execute(drive_stmt)
                    drive_rec = drive_res.scalars().first()
                    if drive_rec and drive_rec.skills_required:
                        skills_required = [s.strip().lower() for s in drive_rec.skills_required.split(",") if s.strip()]

        if not skills_required:
            skills_required = ["programming"]

        # Fetch LongitudinalProfile for candidate
        prior_averages: Dict[str, float] = {}
        if candidate_id:
            profile_data = await memory_service.get_profile_for_planner(candidate_id=candidate_id, db=db)
            if profile_data:
                prior_averages = profile_data.get("skill_scores") or {}

        # Compute skill difficulties based on profile
        skill_difficulties = {}
        for skill in skills_required:
            score = prior_averages.get(skill)
            if score is None:
                difficulty = "medium"
            elif score > 8.0:
                difficulty = "hard"
            elif 0.0 < score < 5.0:
                difficulty = "easy"
            else:
                difficulty = "medium"
            skill_difficulties[skill] = difficulty

        start_time_ms = int(time.time() * 1000)

        # Call LLM with 5-second timeout and circuit breaker from circuit_breaker.py
        try:
            plan_data = await self.generate_plan(
                job_role=state.get("job_role", "Developer"),
                skills_required=skills_required,
                skill_difficulties=skill_difficulties,
                timeout_seconds=5.0,
            )
            generated_by = "planner_agent"
        except Exception as e:
            logger.warning(f"Planner LLM failed or timed out: {e}. Falling back to default plan.")
            # Record exception as a TraceEntry to the database
            try:
                from app.services.observability_service import ObservabilityService
                from app.models.trace_entry import TraceEntryCreate
                obs = ObservabilityService(db)
                await obs.record(TraceEntryCreate(
                    agent_name="planner_agent",
                    action_type="planner_llm_failed",
                    session_id=session_id,
                    input_summary=f"Role: {state.get('job_role', 'Developer')}, Skills: {skills_required}",
                    reasoning_summary=f"LLM planning failed or timed out: {str(e)[:300]}",
                    output_summary="Falling back to default plan",
                    confidence_score=0.0,
                    duration_ms=int(time.time() * 1000) - start_time_ms,
                ))
            except Exception as trace_err:
                logger.error(f"Failed to record TraceEntry for planner failure: {trace_err}")
            
            plan_data = self.get_default_plan(skills_required, skill_difficulties)
            generated_by = "fallback"

        duration_ms = int(time.time() * 1000) - start_time_ms

        # Persist InterviewPlan
        db_plan = None
        if session_id and candidate_id:
            db_plan = InterviewPlan(
                session_id=session_id,
                job_drive_id=job_drive_id,
                candidate_id=candidate_id,
                phases=plan_data.get("phases"),
                revision_count=0,
                revisions=[],
                generated_by=generated_by,
                generation_time_ms=duration_ms,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(db_plan)
            await db.commit()
            await db.refresh(db_plan)

            # Link plan to session
            session_stmt = select(InterviewSession).where(InterviewSession.id == session_id)
            session_res = await db.execute(session_stmt)
            session_rec = session_res.scalars().first()
            if session_rec:
                session_rec.interview_plan_id = db_plan.id
                db.add(session_rec)
                await db.commit()

        # Build list of skills based on the plan phases
        plan_skills = []
        for phase in plan_data.get("phases", []):
            if phase.get("phase") in ["technical", "stress"] and phase.get("skill"):
                plan_skills.append(phase.get("skill"))

        if not plan_skills:
            plan_skills = skills_required

        return {
            "interview_plan": plan_data,
            "plan_phase_index": 0,
            "consecutive_low_quality": 0,
            "skills_to_cover": plan_skills,
            "pending_skills": plan_skills.copy()
        }

    @trace_agent_action("planner_agent", "generate_plan_llm")
    async def generate_plan(
        self,
        job_role: str,
        skills_required: List[str],
        skill_difficulties: Dict[str, str],
        timeout_seconds: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Generate an interview plan via LLM with timeout and circuit breaker.

        Uses the fast LLM (Groq) with a configurable timeout. If the circuit
        breaker for the provider is OPEN, falls back to the default plan immediately.

        Parameters
        ----------
        job_role : str
            The job role for the interview.
        skills_required : List[str]
            Skills that must be covered in the plan.
        skill_difficulties : Dict[str, str]
            Pre-computed difficulty targets per skill.
        timeout_seconds : float
            Maximum time to wait for LLM response (default 5s).

        Returns
        -------
        Dict[str, Any]
            Plan data with a "phases" key.
        """
        async def _call_llm() -> Dict[str, Any]:
            return await self._generate_plan_llm(job_role, skills_required, skill_difficulties)

        # Wrap with circuit breaker (provider = "groq" for fast LLM)
        # Note: Do not pass fallback directly so that the caller can catch the exception,
        # log it as a TraceEntry, and record the correct fallback status in the database.
        result = await execute_with_circuit_breaker(
            provider="groq",
            func=_call_llm,
            timeout=timeout_seconds,
        )
        return result

    async def _generate_plan_llm(
        self, job_role: str, skills: List[str], difficulties: Dict[str, str]
    ) -> Dict[str, Any]:
        """Internal: Call LLM to generate structured JSON plan."""
        llm = get_fast_llm()
        parser = JsonOutputParser(pydantic_object=InterviewPlanSchema)

        skills_str = ", ".join(skills)
        diff_str = ", ".join([f"{k}: {v}" for k, v in difficulties.items()])

        system_prompt = f"""You are an Autonomous Recruitment Planner Agent. Generate a custom, structured interview plan for the role: {job_role}.
The interview needs to cover these skills: {skills_str}.
The computed target difficulties for these skills are: {diff_str}.

Requirements:
1. The plan must contain a list of phases in chronological order.
2. Phases must include: greeting, welcome, warmup, technical (one or more), behavioral, and closing.
3. Every required skill in {skills_str} MUST have at least one corresponding technical phase.
4. Set appropriate question counts: greeting (1), welcome (1), warmup (1), technical (1-2 per skill), behavioral (1-2), closing (1).

Output format:
{parser.get_format_instructions()}"""

        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="Create the custom interview plan in JSON format.")
        ])
        
        # Clean markdown wrappers if any
        content = response.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        return parser.parse(content)

    def get_default_plan(self, skills_required: List[str], difficulties: Dict[str, str]) -> Dict[str, Any]:
        """
        Fallback plan: greeting → warmup → technical → behavioral → closing.

        Used when the LLM call fails or times out (>10s).
        """
        phases = [
            {"phase": "greeting", "skill": "general", "difficulty": "medium", "question_count": 1, "topics": ["icebreaker"]},
            {"phase": "warmup", "skill": "general", "difficulty": "medium", "question_count": 1, "topics": ["experience"]}
        ]

        # Add technical phase for each required skill
        for skill in skills_required:
            diff = difficulties.get(skill, "medium")
            phases.append({
                "phase": "technical",
                "skill": skill,
                "difficulty": diff,
                "question_count": 2,
                "topics": [f"{skill}_fundamentals", f"{skill}_application"]
            })

        phases.extend([
            {"phase": "behavioral", "skill": "communication", "difficulty": "medium", "question_count": 1, "topics": ["teamwork"]},
            {"phase": "closing", "skill": "general", "difficulty": "medium", "question_count": 1, "topics": ["wrap_up"]}
        ])

        return {"phases": phases}

    @trace_agent_action("planner_agent", "revise_plan")
    async def revise_plan(self, state: InterviewState, db: AsyncSession) -> Dict[str, Any]:
        """
        Triggered when candidate struggles (2+ consecutive low-quality responses).
        Revises the plan to reduce difficulty or substitute skills.
        """
        plan = state.get("interview_plan")
        if not plan:
            return {}

        current_idx = state.get("plan_phase_index", 0)
        phases = list(plan.get("phases", []))

        # Adjust difficulty down for remaining phases
        revised = False
        for i in range(current_idx, len(phases)):
            phase = phases[i]
            if phase.get("phase") in ["technical", "stress"] and phase.get("difficulty") != "easy":
                phase["difficulty"] = "easy"
                revised = True

        if not revised:
            return {}

        # Save revised plan to database
        session_id_str = state.get("supervisor_session_id")
        if session_id_str:
            try:
                session_id = int(session_id_str)
                stmt = select(InterviewPlan).where(InterviewPlan.session_id == session_id)
                res = await db.execute(stmt)
                db_plan = res.scalars().first()
                if db_plan:
                    revisions = list(db_plan.revisions or [])
                    revisions.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "reason": "Struggled with questions (consecutive_low_quality)",
                        "previous_phases": db_plan.phases
                    })
                    db_plan.phases = phases
                    db_plan.revision_count += 1
                    db_plan.revisions = revisions
                    db_plan.updated_at = datetime.now(timezone.utc)
                    db.add(db_plan)
                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to save revised plan: {e}")

        return {
            "interview_plan": {"phases": phases},
            "difficulty": "easy",
            "consecutive_low_quality": 0
        }

# Global instance
planner_node = PlannerNode()
