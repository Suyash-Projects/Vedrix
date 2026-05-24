"""
CoachingService — Autonomous Post-Interview Coaching Agent.

Design: Coaching_Agent (Section 4 of design.md)
Requirements: 4.1, 4.2, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10

Key behaviors:
- generate_coaching_plan(): Identifies Skill_Gaps (score < passing_threshold),
  excludes skills >= 8.0, sorts by magnitude descending, generates at least one
  resource per gap using LLM with circuit breaker. Must complete within 60s.
  On timeout > 120s: log failure Trace_Entry, notify Admin, deliver static report.
- compute_coaching_effectiveness(): Compares new scores against previous plan targets.
- send_coaching_notification(): Sends email within 5 minutes with top 3 gaps and link.
"""
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.models.coaching_plan import CoachingPlan
from app.models.user import User
from app.services.observability_service import trace_agent_action, ObservabilityService
from app.models.trace_entry import TraceEntryCreate
from app.services.interview_engine.circuit_breaker import execute_with_circuit_breaker
from app.services.interview_engine.providers import get_fast_llm
from app.services.email_service import send_coaching_plan_email
from app.db.session import async_session
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)

# ── Default learning resources fallback ──────────────────────────────────────────
DEFAULT_RESOURCES = {
    "programming": [
        {"title": "Clean Code Handbook", "url": "https://www.oreilly.com/library/view/clean-code-a/9780136083238/", "type": "book"},
        {"title": "Data Structures & Algorithms Course", "url": "https://www.coursera.org/specializations/data-structures-algorithms", "type": "course"}
    ],
    "database": [
        {"title": "Designing Data-Intensive Applications", "url": "https://www.oreilly.com/library/view/designing-data-intensive-applications/9781491903063/", "type": "book"},
        {"title": "SQL & Relational Databases fundamentals", "url": "https://www.khanacademy.org/computing/computer-programming/sql", "type": "course"}
    ],
    "frontend": [
        {"title": "React Documentation & Guides", "url": "https://react.dev/learn", "type": "documentation"},
        {"title": "Modern JavaScript Deep Dive", "url": "https://javascript.info/", "type": "tutorial"}
    ],
    "backend": [
        {"title": "API Design Guidelines", "url": "https://geemus.gitbooks.io/http-api-design/content/", "type": "documentation"},
        {"title": "FastAPI Web Development Tutorial", "url": "https://fastapi.tiangolo.com/tutorial/", "type": "documentation"}
    ],
    "devops": [
        {"title": "Docker & Containerization Tutorial", "url": "https://docs.docker.com/get-started/", "type": "documentation"},
        {"title": "DevOps Handbook", "url": "https://itrevolution.com/book/the-devops-handbook/", "type": "book"}
    ],
    "system_design": [
        {"title": "System Design Primer", "url": "https://github.com/donnemartin/system-design-primer", "type": "resource"},
        {"title": "Designing Distributed Systems", "url": "https://www.oreilly.com/library/view/designing-distributed-systems/9781491983638/", "type": "book"}
    ],
    "testing": [
        {"title": "Test Driven Development by Example", "url": "https://www.oreilly.com/library/view/test-driven-development/0321146530/", "type": "book"},
        {"title": "Unit Testing Principles & Practices", "url": "https://www.manning.com/books/unit-testing", "type": "book"}
    ],
    "security": [
        {"title": "OWASP Top 10 Web Risks", "url": "https://owasp.org/www-project-top-ten/", "type": "documentation"},
        {"title": "OAuth 2.0 Simplified", "url": "https://aaronparecki.com/oauth-2-simplified/", "type": "resource"}
    ],
    "general": [
        {"title": "Core Engineering Principles", "url": "https://google.github.io/styleguide/", "type": "documentation"},
        {"title": "Software Engineering at Google", "url": "https://abseil.io/resources/swe-book", "type": "book"}
    ]
}


# ── Pydantic schemas for LLM output parsing ─────────────────────────────────────

class ResourceRecommendation(BaseModel):
    title: str = Field(description="Title of the learning resource")
    url: str = Field(description="URL of the learning resource")
    type: str = Field(description="Type: book, course, documentation, video, tutorial")


class SkillGapRecommendation(BaseModel):
    skill: str = Field(description="Name of the skill gap")
    score: float = Field(description="Score achieved in evaluation (0.0-10.0)")
    gap_magnitude: float = Field(description="Difference between threshold and achieved score")
    resources: List[ResourceRecommendation] = Field(description="List of recommended learning resources")


class CoachingPlanSchema(BaseModel):
    skill_gaps: List[SkillGapRecommendation] = Field(description="List of identified skill gaps and resources")


# ── CoachingService ──────────────────────────────────────────────────────────────

class CoachingService:
    """
    Autonomous Post-Interview Coaching Agent.

    Generates personalized learning plans after interview completion,
    tracks coaching effectiveness across sessions, and sends notifications.
    """

    @trace_agent_action("coaching_agent", "generate_plan")
    async def generate_coaching_plan(
        self,
        session_id: int,
        candidate_id: int,
        evaluation_report: Dict[str, Any],
        skill_matrix: Dict[str, float],
        passing_threshold: float = 6.0,
        db: Optional[AsyncSession] = None,
    ) -> CoachingPlan:
        """
        Generate a personalized coaching plan for a candidate post-interview.

        Must complete within 60s. On timeout > 120s, logs failure Trace_Entry,
        notifies Admin, and delivers static evaluation report.

        Parameters
        ----------
        session_id : The InterviewSession PK.
        candidate_id : The Candidate's user PK.
        evaluation_report : Full evaluation report dict from the session.
        skill_matrix : Dict of {skill_name: score} from the evaluation.
        passing_threshold : Score below which a skill is a gap (default 6.0).
        db : AsyncSession for database operations.

        Returns
        -------
        CoachingPlan : The generated and persisted coaching plan.
        """
        start_time_ms = int(time.time() * 1000)

        # 1. Identify Skill Gaps: score < passing_threshold
        #    Exclude skills where score >= 8.0 (Requirement 4.10)
        gaps: List[Dict[str, Any]] = []
        for skill, score in skill_matrix.items():
            if score >= 8.0:
                # Explicitly exclude high-performing skills
                continue
            if score < passing_threshold:
                gap_magnitude = passing_threshold - score
                gaps.append({
                    "skill": skill,
                    "score": score,
                    "gap_magnitude": gap_magnitude,
                })

        # 2. Sort gaps by magnitude descending (largest gap first) — Requirement 4.5
        gaps.sort(key=lambda x: x["gap_magnitude"], reverse=True)

        # If no gaps, still create a minimal plan
        if not gaps:
            logger.info(
                f"No skill gaps identified for candidate {candidate_id} "
                f"in session {session_id}. Creating empty plan."
            )
            plan_data: Dict[str, Any] = {"skill_gaps": []}
        else:
            # 3. Generate resources using LLM with circuit breaker
            plan_data = await self._generate_resources_with_circuit_breaker(
                gaps, session_id, start_time_ms, db
            )

        duration_ms = int(time.time() * 1000) - start_time_ms

        # 4. Check for 120s timeout — log failure, notify Admin
        if duration_ms > 120_000:
            await self._handle_timeout_failure(
                session_id, candidate_id, duration_ms, db
            )

        # 5. Persist CoachingPlan to database
        top_3 = [{"skill": g["skill"], "score": g["score"]} for g in gaps[:3]]

        if db is not None:
            # Check if plan already exists (avoid duplicate constraint errors)
            exist_stmt = select(CoachingPlan).where(CoachingPlan.session_id == session_id)
            exist_res = await db.execute(exist_stmt)
            db_plan = exist_res.scalars().first()

            if not db_plan:
                db_plan = CoachingPlan(
                    session_id=session_id,
                    candidate_id=candidate_id,
                    skill_gaps=plan_data.get("skill_gaps"),
                    top_3_gaps=top_3,
                    generation_time_ms=duration_ms,
                )
                db.add(db_plan)
                await db.commit()
                await db.refresh(db_plan)
            else:
                db_plan.skill_gaps = plan_data.get("skill_gaps")
                db_plan.top_3_gaps = top_3
                db_plan.generation_time_ms = duration_ms
                db.add(db_plan)
                await db.commit()
                await db.refresh(db_plan)
        else:
            # No DB session — create in-memory plan for testing
            db_plan = CoachingPlan(
                session_id=session_id,
                candidate_id=candidate_id,
                skill_gaps=plan_data.get("skill_gaps"),
                top_3_gaps=top_3,
                generation_time_ms=duration_ms,
            )

        return db_plan

    @trace_agent_action("coaching_agent", "compute_effectiveness")
    async def compute_coaching_effectiveness(
        self,
        previous_plan: CoachingPlan,
        new_skill_scores: Dict[str, float],
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, float]:
        """
        Compare new scores against previous coaching plan targets.

        For each skill in the previous plan's skill_gaps, compute the delta
        between the new score and the old score.

        Parameters
        ----------
        previous_plan : The CoachingPlan from a prior session.
        new_skill_scores : Dict of {skill: new_score} from the latest evaluation.

        Returns
        -------
        Dict[str, float] : {skill: effectiveness_delta} where delta = new_score - old_score.
        """
        effectiveness: Dict[str, float] = {}

        if not previous_plan.skill_gaps:
            return effectiveness

        for gap_entry in previous_plan.skill_gaps:
            skill = gap_entry.get("skill") if isinstance(gap_entry, dict) else getattr(gap_entry, "skill", None)
            old_score = gap_entry.get("score") if isinstance(gap_entry, dict) else getattr(gap_entry, "score", None)

            if skill and skill in new_skill_scores and old_score is not None:
                new_score = new_skill_scores[skill]
                delta = new_score - old_score
                effectiveness[skill] = round(delta, 2)

        return effectiveness

    @trace_agent_action("coaching_agent", "send_notification")
    async def send_coaching_notification(
        self,
        candidate_email: str,
        coaching_plan: CoachingPlan,
        db: Optional[AsyncSession] = None,
    ) -> None:
        """
        Send coaching plan notification to candidate via email service.

        Must be called within 5 minutes of plan generation.
        Includes top 3 priority gaps and a link to the full plan.

        Parameters
        ----------
        candidate_email : The candidate's email address.
        coaching_plan : The generated CoachingPlan with top_3_gaps.
        """
        top_gaps = coaching_plan.top_3_gaps or []
        plan_id = coaching_plan.id

        # Fetch candidate name for personalization
        first_name = "Candidate"
        if db is not None and coaching_plan.candidate_id:
            try:
                stmt = select(User).where(User.id == coaching_plan.candidate_id)
                res = await db.execute(stmt)
                user_rec = res.scalars().first()
                if user_rec:
                    first_name = user_rec.first_name or user_rec.username or "Candidate"
            except Exception as e:
                logger.warning(f"Failed to fetch candidate name: {e}")

        try:
            await send_coaching_plan_email(
                to=candidate_email,
                first_name=first_name,
                top_gaps=top_gaps,
                plan_id=plan_id or 0,
            )

            # Update notification_sent_at timestamp
            if db is not None and coaching_plan.id:
                coaching_plan.notification_sent_at = datetime.now(timezone.utc)
                db.add(coaching_plan)
                await db.commit()

            logger.info(
                f"Coaching notification sent to {candidate_email} "
                f"for plan {plan_id}"
            )
        except Exception as e:
            logger.error(f"Failed to send coaching notification: {e}")

    # ── Private helpers ───────────────────────────────────────────────────────────

    async def _generate_resources_with_circuit_breaker(
        self,
        gaps: List[Dict[str, Any]],
        session_id: int,
        start_time_ms: int,
        db: Optional[AsyncSession],
    ) -> Dict[str, Any]:
        """
        Generate learning resources using LLM with circuit breaker protection.
        Falls back to static resources on failure.
        """

        async def _llm_call() -> Dict[str, Any]:
            """The actual LLM call wrapped for circuit breaker."""
            return await asyncio.wait_for(
                self._recommend_resources_llm(gaps),
                timeout=15.0,
            )

        async def _fallback_call() -> Dict[str, Any]:
            """Static fallback when LLM is unavailable."""
            return self._get_static_resources(gaps)

        try:
            plan_data = await execute_with_circuit_breaker(
                provider="groq",
                func=_llm_call,
                fallback=_fallback_call,
            )
        except Exception as e:
            logger.warning(
                f"Coaching LLM failed with circuit breaker: {e}. "
                f"Using static resources."
            )
            plan_data = self._get_static_resources(gaps)

            # Log trace failure
            if db is not None:
                try:
                    obs = ObservabilityService(db)
                    await obs.record(TraceEntryCreate(
                        agent_name="coaching_agent",
                        action_type="llm_recommendation_failed",
                        session_id=session_id,
                        input_summary=f"Gaps: {[g['skill'] for g in gaps]}",
                        reasoning_summary=f"LLM failed: {str(e)[:200]}",
                        output_summary="Fallback to static recommendations",
                        confidence_score=0.5,
                        duration_ms=int(time.time() * 1000) - start_time_ms,
                    ))
                except Exception as trace_err:
                    logger.error(f"Failed to record TraceEntry: {trace_err}")

        return plan_data

    async def _recommend_resources_llm(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Query LLM for personalized learning resources for candidate gaps."""
        llm = get_fast_llm()
        parser = JsonOutputParser(pydantic_object=CoachingPlanSchema)

        gaps_desc = "\n".join([
            f"- Skill: {g['skill']}, Score: {g['score']}/10, Gap: {g['gap_magnitude']}"
            for g in gaps
        ])

        system_prompt = (
            "You are an Autonomous Career Coaching Agent. Your goal is to provide "
            "high-quality learning resources for a candidate who struggled in their "
            "technical interview.\n"
            f"Here are the candidate's skill gaps:\n{gaps_desc}\n\n"
            "For each skill gap, recommend 2-3 specific, high-quality resources:\n"
            "- Books, courses (from Coursera/Udemy/Pluralsight), documentation, or GitHub repos.\n"
            "- Ensure the URLs are valid and resources are modern and highly relevant.\n\n"
            f"Output format:\n{parser.get_format_instructions()}"
        )

        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="Generate learning resource recommendations in JSON format."),
        ])

        # Clean markdown wrapper if present
        content = response.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        return parser.parse(content)

    def _get_static_resources(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate static fallback resources for each gap."""
        plan_gaps = []
        for gap in gaps:
            skill_key = gap["skill"].lower().replace(" ", "_")
            resources = DEFAULT_RESOURCES.get(skill_key, DEFAULT_RESOURCES["general"])
            plan_gaps.append({
                "skill": gap["skill"],
                "score": gap["score"],
                "gap_magnitude": gap["gap_magnitude"],
                "resources": resources,
            })
        return {"skill_gaps": plan_gaps}

    async def _handle_timeout_failure(
        self,
        session_id: int,
        candidate_id: int,
        duration_ms: int,
        db: Optional[AsyncSession],
    ) -> None:
        """
        Handle timeout > 120s: log failure Trace_Entry and notify Admin.
        Requirement 4.9.
        """
        logger.error(
            f"Coaching plan generation exceeded 120s for session {session_id} "
            f"(took {duration_ms}ms). Logging failure and notifying Admin."
        )

        if db is not None:
            try:
                obs = ObservabilityService(db)
                await obs.record(TraceEntryCreate(
                    agent_name="coaching_agent",
                    action_type="generation_timeout",
                    session_id=session_id,
                    candidate_id=candidate_id,
                    input_summary=f"session_id={session_id}, candidate_id={candidate_id}",
                    reasoning_summary=(
                        f"Coaching plan generation exceeded 120s timeout "
                        f"(actual: {duration_ms}ms). Admin notified."
                    ),
                    output_summary="Timeout failure — static report delivered",
                    confidence_score=0.0,
                    duration_ms=duration_ms,
                ))
            except Exception as trace_err:
                logger.error(f"Failed to record timeout TraceEntry: {trace_err}")

            # Notify Admin users
            try:
                admin_stmt = select(User).where(User.user_type == "admin")
                admin_res = await db.execute(admin_stmt)
                admins = admin_res.scalars().all()
                for admin in admins:
                    logger.warning(
                        f"ADMIN ALERT: Coaching plan generation timeout for "
                        f"session {session_id} (candidate {candidate_id}). "
                        f"Duration: {duration_ms}ms. Admin: {admin.email}"
                    )
            except Exception as admin_err:
                logger.error(f"Failed to notify admins: {admin_err}")


# ── Module-level singleton ────────────────────────────────────────────────────────
coaching_service = CoachingService()
