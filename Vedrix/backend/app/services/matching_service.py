"""
MatchingService — Agentic Job-Candidate Matching Engine.

Design: Matching_Engine (Section 5 of design.md)
Requirements: 5.1, 5.2, 5.5, 5.7, 5.8, 5.9, 5.10

Key guarantees
--------------
* compute_score() is a PURE function — no DB access, no async, deterministic.
* Never uses demographic attributes (age, gender, nationality).
* Configurable top-match threshold (default 80).
* All async methods decorated with @trace_agent_action("matching_engine", ...).
* Sets match_score=null and logs Trace_Entry when evaluation data is missing.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewSession, JobDrive
from app.models.match_result import MatchResult
from app.models.longitudinal_profile import LongitudinalProfile
from app.services.observability_service import trace_agent_action, ObservabilityService
from app.models.trace_entry import TraceEntryCreate

logger = logging.getLogger(__name__)

# Configurable threshold — can be overridden via environment or settings
DEFAULT_TOP_MATCH_THRESHOLD: float = 80.0


class MatchingService:
    """
    Agentic Job-Candidate Matching Engine.

    Computes Match_Score (0-100) from skill scores, coverage %, overall score,
    and growth trend. Generates natural-language explanations. Re-ranks
    candidates for a drive when a new candidate completes.
    """

    def __init__(self, top_match_threshold: float = DEFAULT_TOP_MATCH_THRESHOLD):
        self.top_match_threshold = top_match_threshold

    # ── Pure Function — No DB, No Async ──────────────────────────────────────

    def compute_score(
        self,
        skill_scores: Dict[str, float],
        required_skills: List[str],
        coverage_pct: float,
        overall_score: float,
        growth_trend: str,
    ) -> float:
        """
        Pure function that computes the match score.

        Formula:
            match_score = (
                0.40 * skill_coverage_score +
                0.30 * avg_skill_score_norm +
                0.20 * overall_score_norm +
                0.10 * growth_bonus
            ) * 100

        Parameters
        ----------
        skill_scores : Dict mapping skill name (lowercase) to score (0-10 scale).
        required_skills : List of required skill names (lowercase).
        coverage_pct : Fraction (0.0 to 1.0) of required skills covered above threshold.
        overall_score : Overall interview score on 0-10 scale.
        growth_trend : One of "improving", "stable", "declining".

        Returns
        -------
        float : Match score clamped to [0.0, 100.0].
        """
        # Skill coverage score: fraction of required skills covered (0.0 to 1.0)
        skill_coverage_score = max(0.0, min(1.0, coverage_pct))

        # Average skill score normalized: avg of scores on required skills / 10
        if required_skills:
            matching_scores = [skill_scores.get(s, 0.0) for s in required_skills]
            avg_skill_score_norm = sum(matching_scores) / (len(matching_scores) * 10.0)
        else:
            avg_skill_score_norm = 0.0
        avg_skill_score_norm = max(0.0, min(1.0, avg_skill_score_norm))

        # Overall score normalized: overall_score / 10
        overall_score_norm = max(0.0, min(1.0, overall_score / 10.0))

        # Growth bonus: +1.0 if improving, 0.0 if stable, -0.5 if declining
        if growth_trend == "improving":
            growth_bonus = 1.0
        elif growth_trend == "stable":
            growth_bonus = 0.0
        else:  # "declining" or unknown
            growth_bonus = -0.5

        # Weighted formula
        raw_score = (
            0.40 * skill_coverage_score
            + 0.30 * avg_skill_score_norm
            + 0.20 * overall_score_norm
            + 0.10 * growth_bonus
        ) * 100

        return max(0.0, min(100.0, raw_score))

    # ── Explanation Generator ────────────────────────────────────────────────

    def generate_explanation(
        self,
        skill_scores: Dict[str, float],
        required_skills: List[str],
        overall_score: float,
        growth_trend: str,
        match_score: float,
        coverage_pct: float,
    ) -> Dict[str, Any]:
        """
        Generate natural-language explanation identifying top 3 contributing
        factors and top 2 disqualifying factors.

        Parameters
        ----------
        skill_scores : Candidate's skill scores (0-10 scale).
        required_skills : Required skills for the job drive.
        overall_score : Overall interview score (0-10 scale).
        growth_trend : "improving", "stable", or "declining".
        match_score : The computed match score (0-100).
        coverage_pct : Fraction of required skills covered (0.0-1.0).

        Returns
        -------
        Dict with contributing_factors (top 3), disqualifying_factors (top 2),
        and summary_text.
        """
        contributing_factors: List[str] = []
        disqualifying_factors: List[str] = []

        # ── Contributing factors (sorted by impact) ──────────────────────────
        # Identify top scoring skills among required skills
        scored_required = [
            (s, skill_scores.get(s, 0.0))
            for s in required_skills
            if s in skill_scores
        ]
        scored_required.sort(key=lambda x: x[1], reverse=True)

        # Top 3 contributing: highest skill scores
        for skill, score in scored_required[:3]:
            contributing_factors.append(
                f"Strong performance in '{skill}' (score: {score:.1f}/10)"
            )

        # Additional contributing factors if we have room
        if len(contributing_factors) < 3 and overall_score >= 7.0:
            contributing_factors.append(
                f"Strong overall interview performance (score: {overall_score:.1f}/10)"
            )
        if len(contributing_factors) < 3 and coverage_pct >= 0.8:
            contributing_factors.append(
                f"High coverage of required skills ({coverage_pct * 100:.0f}%)"
            )
        if len(contributing_factors) < 3 and growth_trend == "improving":
            contributing_factors.append(
                "Demonstrated improving skill trajectory over time"
            )

        # Fallback if still empty
        if not contributing_factors:
            contributing_factors.append("Candidate completed the full interview.")

        # ── Disqualifying factors (top 2) ────────────────────────────────────
        # Missing skills (not covered at all)
        missing_skills = [s for s in required_skills if s not in skill_scores]
        if missing_skills:
            disqualifying_factors.append(
                f"Missing required skills: {', '.join(missing_skills[:3])}"
            )

        # Lowest scoring required skills (below passing threshold of 6.0)
        weak_skills = [
            (s, skill_scores[s])
            for s in required_skills
            if s in skill_scores and skill_scores[s] < 6.0
        ]
        weak_skills.sort(key=lambda x: x[1])
        if weak_skills:
            weak_names = [f"'{s}' ({sc:.1f}/10)" for s, sc in weak_skills[:2]]
            disqualifying_factors.append(
                f"Below passing threshold on: {', '.join(weak_names)}"
            )

        if len(disqualifying_factors) < 2 and growth_trend == "declining":
            disqualifying_factors.append(
                "Declining skill trajectory in longitudinal history"
            )

        # Fallback
        if not disqualifying_factors:
            disqualifying_factors.append(
                "No major skill gaps or disqualifying factors identified."
            )

        return {
            "contributing_factors": contributing_factors[:3],
            "disqualifying_factors": disqualifying_factors[:2],
            "summary_text": (
                f"Candidate achieved a match score of {match_score:.1f}% "
                f"based on {coverage_pct * 100:.0f}% skill coverage "
                f"and {overall_score:.1f}/10 overall score."
            ),
        }

    # ── Async Methods (DB Access) ────────────────────────────────────────────

    @trace_agent_action("matching_engine", "compute_match")
    async def compute_match_score(
        self, session_id: int, db: AsyncSession
    ) -> Optional[MatchResult]:
        """
        Computes Job-Candidate Match Score for a given session.

        Must complete within 30 seconds. Uses the weighted formula:
        0.40 × skill_coverage + 0.30 × avg_skill_norm + 0.20 × overall_norm
        + 0.10 × growth_bonus.

        Never uses demographic attributes.
        """
        start_time_ms = int(time.time() * 1000)

        # 1. Fetch Session
        stmt = select(InterviewSession).where(InterviewSession.id == session_id)
        res = await db.execute(stmt)
        session_rec = res.scalars().first()

        if not session_rec:
            logger.warning(f"Matching request for non-existent session: {session_id}")
            return None

        # AC 5.9: If missing evaluation data, Match Score = null (Pending)
        if session_rec.overall_score is None:
            return await self._handle_missing_evaluation(
                session_rec, session_id, db, start_time_ms
            )

        job_drive_id = session_rec.job_drive_id
        if not job_drive_id:
            logger.warning(f"Session {session_id} is not linked to any Job Drive.")
            return None

        # 2. Fetch Job Drive
        drive_stmt = select(JobDrive).where(JobDrive.id == job_drive_id)
        drive_res = await db.execute(drive_stmt)
        drive_rec = drive_res.scalars().first()

        if not drive_rec:
            logger.warning(
                f"Session {session_id} linked to non-existent Job Drive: {job_drive_id}"
            )
            return None

        # 3. Extract required skills
        required_skills: List[str] = []
        if drive_rec.skills_required:
            required_skills = [
                s.strip().lower()
                for s in drive_rec.skills_required.split(",")
                if s.strip()
            ]
        if not required_skills:
            required_skills = ["programming"]

        # 4. Extract candidate's skill scores
        candidate_scores: Dict[str, float] = {}
        if session_rec.skill_matrix:
            candidate_scores = {k.lower(): v for k, v in session_rec.skill_matrix.items()}
        elif hasattr(session_rec, "topic_scores") and session_rec.topic_scores:
            candidate_scores = {k.lower(): v for k, v in session_rec.topic_scores.items()}

        # 5. Compute coverage percentage (skills covered above threshold 6.0)
        covered_count = sum(
            1 for s in required_skills
            if candidate_scores.get(s, 0.0) >= 6.0
        )
        coverage_pct = covered_count / len(required_skills) if required_skills else 0.0

        # 6. Fetch growth trend from LongitudinalProfile
        prof_stmt = select(LongitudinalProfile).where(
            LongitudinalProfile.candidate_id == session_rec.candidate_id
        )
        prof_res = await db.execute(prof_stmt)
        profile = prof_res.scalars().first()

        growth_trend = "stable"
        if profile and profile.skill_trends and isinstance(profile.skill_trends, dict):
            # Use overall trend if available, otherwise compute from individual trends
            trends = list(profile.skill_trends.values())
            if trends:
                improving_count = trends.count("improving")
                declining_count = trends.count("declining")
                if improving_count > declining_count:
                    growth_trend = "improving"
                elif declining_count > improving_count:
                    growth_trend = "declining"
                else:
                    growth_trend = "stable"

        # 7. Compute score using pure function
        match_score = self.compute_score(
            skill_scores=candidate_scores,
            required_skills=required_skills,
            coverage_pct=coverage_pct,
            overall_score=session_rec.overall_score,
            growth_trend=growth_trend,
        )

        # 8. Flag top match using configurable threshold
        is_top_match = match_score > self.top_match_threshold

        # 9. Generate explanation
        explanation = self.generate_explanation(
            skill_scores=candidate_scores,
            required_skills=required_skills,
            overall_score=session_rec.overall_score,
            growth_trend=growth_trend,
            match_score=match_score,
            coverage_pct=coverage_pct,
        )

        # 10. Build score breakdown
        if required_skills:
            matching_scores = [candidate_scores.get(s, 0.0) for s in required_skills]
            avg_skill_score_norm = sum(matching_scores) / (len(matching_scores) * 10.0)
        else:
            avg_skill_score_norm = 0.0

        score_breakdown = {
            "skill_coverage_pct": round(coverage_pct * 100, 1),
            "avg_skill_score_norm": round(avg_skill_score_norm * 100, 1),
            "overall_score_norm": round((session_rec.overall_score / 10.0) * 100, 1),
            "growth_bonus": growth_trend,
            "growth_bonus_value": (
                1.0 if growth_trend == "improving"
                else (0.0 if growth_trend == "stable" else -0.5)
            ),
        }

        # 11. Persist MatchResult
        exist_stmt = select(MatchResult).where(MatchResult.session_id == session_id)
        exist_res = await db.execute(exist_stmt)
        db_match = exist_res.scalars().first()

        if not db_match:
            db_match = MatchResult(
                candidate_id=session_rec.candidate_id,
                job_drive_id=job_drive_id,
                session_id=session_id,
                match_score=match_score,
                is_top_match=is_top_match,
                explanation=explanation,
                score_breakdown=score_breakdown,
                computed_at=datetime.now(timezone.utc),
            )
            db.add(db_match)
        else:
            db_match.match_score = match_score
            db_match.is_top_match = is_top_match
            db_match.explanation = explanation
            db_match.score_breakdown = score_breakdown
            db_match.computed_at = datetime.now(timezone.utc)
            db.add(db_match)

        await db.commit()
        await db.refresh(db_match)

        return db_match

    @trace_agent_action("matching_engine", "rank_candidates")
    async def rank_candidates(
        self, job_drive_id: int, db: AsyncSession
    ) -> List[MatchResult]:
        """
        Re-rank all candidates for a drive. Fetches all completed sessions,
        recomputes match scores, and returns sorted results.

        Must complete within 60 seconds of a new candidate completing.
        """
        # Fetch all completed sessions for this drive
        stmt = select(InterviewSession).where(
            InterviewSession.job_drive_id == job_drive_id,
            InterviewSession.status == "completed",
        )
        res = await db.execute(stmt)
        sessions = res.scalars().all()

        # Recompute match scores for all sessions
        for session in sessions:
            await self.compute_match_score(session.id, db=db)

        # Return all MatchResults sorted by match_score DESC
        rankings_stmt = (
            select(MatchResult)
            .where(MatchResult.job_drive_id == job_drive_id)
            .order_by(desc(MatchResult.match_score))
        )
        rankings_res = await db.execute(rankings_stmt)
        return list(rankings_res.scalars().all())

    # ── Private Helpers ──────────────────────────────────────────────────────

    async def _handle_missing_evaluation(
        self,
        session_rec: InterviewSession,
        session_id: int,
        db: AsyncSession,
        start_time_ms: int,
    ) -> Optional[MatchResult]:
        """
        Handle the case where evaluation data is missing.
        Sets match_score=null and logs a Trace_Entry.
        """
        # Check if match result already exists
        exist_stmt = select(MatchResult).where(MatchResult.session_id == session_id)
        exist_res = await db.execute(exist_stmt)
        db_match = exist_res.scalars().first()

        if not db_match:
            db_match = MatchResult(
                candidate_id=session_rec.candidate_id,
                job_drive_id=session_rec.job_drive_id,
                session_id=session_id,
                match_score=None,
                is_top_match=False,
                explanation={"message": "Pending Evaluation"},
            )
            db.add(db_match)
            await db.commit()

        # Log trace entry for missing evaluation data
        try:
            obs = ObservabilityService(db)
            await obs.record(
                TraceEntryCreate(
                    agent_name="matching_engine",
                    action_type="missing_evaluation_data",
                    session_id=session_id,
                    input_summary=f"Session ID: {session_id}",
                    reasoning_summary=(
                        "Overall evaluation score is missing; "
                        "match score set to NULL"
                    ),
                    output_summary="Pending Evaluation",
                    confidence_score=1.0,
                    duration_ms=int(time.time() * 1000) - start_time_ms,
                )
            )
        except Exception as trace_err:
            logger.error(
                f"Failed to record TraceEntry in matching fallback: {trace_err}"
            )

        return db_match


# Module-level singleton
matching_service = MatchingService()
