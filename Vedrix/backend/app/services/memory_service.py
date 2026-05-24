"""
MemoryService — Persistent Long-Term Memory Agent.

Design: Memory_Agent (Section 1 of design.md)
Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.7, 1.9, 1.10

Key guarantees
--------------
* Cross-session skill persistence via LongitudinalProfile.
* Optimistic locking on updated_at to prevent concurrent write conflicts.
* GDPR deletion via deletion_requested_at marker.
* All public methods decorated with @trace_agent_action for observability.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.longitudinal_profile import LongitudinalProfile
from app.services.observability_service import trace_agent_action

logger = logging.getLogger(__name__)


# ── Type definitions ──────────────────────────────────────────────────────────

class SkillScoreEntry(TypedDict):
    score: float
    session_id: int
    timestamp: str


class PlannerContext(TypedDict):
    skill_scores: Dict[str, float]
    growth_trends: Dict[str, str]


# ── MemoryService ─────────────────────────────────────────────────────────────

class MemoryService:
    """
    Persistent Long-Term Memory Agent service.

    Maintains LongitudinalProfile per candidate across all sessions.
    Uses optimistic locking via updated_at to prevent concurrent write conflicts.
    """

    @staticmethod
    def compute_trend(scores: List[float]) -> str:
        """
        Compute skill trend based on score history.

        Rules (per design):
        - If fewer than 3 scores → "stable"
        - If the last 3+ scores are monotonically increasing → "improving"
        - If the last 3+ scores are monotonically decreasing → "declining"
        - Otherwise → "stable"

        Parameters
        ----------
        scores : List[float]
            Chronological list of skill scores.

        Returns
        -------
        str
            One of "improving", "stable", "declining".
        """
        if len(scores) < 3:
            return "stable"

        # Use the last 3 scores to determine trend direction
        last_three = scores[-3:]

        if all(x < y for x, y in zip(last_three, last_three[1:])):
            return "improving"
        if all(x > y for x, y in zip(last_three, last_three[1:])):
            return "declining"
        return "stable"

    @trace_agent_action("memory_agent", "get_or_create_profile")
    async def get_or_create_profile(
        self, candidate_id: int, db: AsyncSession
    ) -> LongitudinalProfile:
        """
        Retrieve existing LongitudinalProfile or create a new one.

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        db : AsyncSession
            The database session.

        Returns
        -------
        LongitudinalProfile
            The existing or newly created profile.
        """
        stmt = select(LongitudinalProfile).where(
            LongitudinalProfile.candidate_id == candidate_id
        )
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if not profile:
            profile = LongitudinalProfile(
                candidate_id=candidate_id,
                skill_history={},
                skill_averages={},
                skill_trends={},
                enrichment_sources={},
                coaching_effectiveness={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        return profile

    @trace_agent_action("memory_agent", "merge_session_skills")
    async def merge_session_skills(
        self,
        candidate_id: int,
        session_id: int,
        skill_scores: Dict[str, float],
        db: AsyncSession,
    ) -> LongitudinalProfile:
        """
        Merge skill scores from a completed session into candidate's profile.

        Uses optimistic locking on updated_at to prevent lost updates from
        concurrent sessions. Retries up to 5 times with exponential backoff.

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        session_id : int
            The completed session ID.
        skill_scores : Dict[str, float]
            Mapping of skill name to score from the session.
        db : AsyncSession
            The database session.

        Returns
        -------
        LongitudinalProfile
            The updated profile with merged skills.

        Raises
        ------
        RuntimeError
            If optimistic locking fails after 5 attempts.
        """
        for attempt in range(5):
            # 1. Fetch current profile
            profile = await self.get_or_create_profile(candidate_id, db=db)
            old_updated_at = profile.updated_at

            # Ensure dictionaries are initialized
            skill_history: Dict[str, List[Dict[str, Any]]] = dict(
                profile.skill_history or {}
            )
            skill_averages: Dict[str, float] = dict(profile.skill_averages or {})
            skill_trends: Dict[str, str] = dict(profile.skill_trends or {})

            timestamp_str = datetime.now(timezone.utc).isoformat()

            # 2. Merge new scores into history
            for skill, score in skill_scores.items():
                if skill not in skill_history:
                    skill_history[skill] = []

                # Append new score entry
                skill_history[skill].append(
                    {
                        "score": score,
                        "session_id": session_id,
                        "timestamp": timestamp_str,
                    }
                )

                # Recompute running average
                scores_list = [entry["score"] for entry in skill_history[skill]]
                skill_averages[skill] = sum(scores_list) / len(scores_list)

                # Recompute trend direction
                skill_trends[skill] = self.compute_trend(scores_list)

            # 3. Attempt update with optimistic lock on updated_at
            new_updated_at = datetime.now(timezone.utc)
            stmt = (
                update(LongitudinalProfile)
                .where(LongitudinalProfile.candidate_id == candidate_id)
                .where(LongitudinalProfile.updated_at == old_updated_at)
                .values(
                    skill_history=skill_history,
                    skill_averages=skill_averages,
                    skill_trends=skill_trends,
                    updated_at=new_updated_at,
                )
            )
            res = await db.execute(stmt)
            await db.commit()

            if res.rowcount > 0:
                # Successfully updated — refresh and return
                stmt_refresh = select(LongitudinalProfile).where(
                    LongitudinalProfile.candidate_id == candidate_id
                )
                res_refresh = await db.execute(stmt_refresh)
                return res_refresh.scalars().first()

            # Optimistic lock failed — another concurrent write updated first
            # Backoff and retry
            await asyncio.sleep(0.05 * (attempt + 1))

        raise RuntimeError(
            "Concurrent write conflict: failed to update LongitudinalProfile "
            "after 5 attempts."
        )

    @trace_agent_action("memory_agent", "get_skill_history")
    async def get_skill_history(
        self, candidate_id: int, skill: str, db: AsyncSession
    ) -> List[SkillScoreEntry]:
        """
        Retrieve the chronological score history for a specific skill.

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        skill : str
            The skill name to look up.
        db : AsyncSession
            The database session.

        Returns
        -------
        List[SkillScoreEntry]
            Chronological list of score entries for the skill.
            Empty list if the skill has no history.
        """
        stmt = select(LongitudinalProfile).where(
            LongitudinalProfile.candidate_id == candidate_id
        )
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if not profile or not profile.skill_history:
            return []

        skill_history = profile.skill_history or {}
        return skill_history.get(skill, [])

    @trace_agent_action("memory_agent", "delete_profile")
    async def delete_profile(
        self, candidate_id: int, db: AsyncSession
    ) -> Optional[LongitudinalProfile]:
        """
        Mark profile for GDPR deletion.

        Sets deletion_requested_at to current UTC time. Actual deletion
        is handled by a scheduled job (not in scope here).

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        db : AsyncSession
            The database session.

        Returns
        -------
        Optional[LongitudinalProfile]
            The updated profile, or None if no profile exists.
        """
        stmt = select(LongitudinalProfile).where(
            LongitudinalProfile.candidate_id == candidate_id
        )
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if profile:
            profile.deletion_requested_at = datetime.now(timezone.utc)
            db.add(profile)
            await db.commit()
            await db.refresh(profile)

        return profile

    @trace_agent_action("memory_agent", "get_profile_for_planner")
    async def get_profile_for_planner(
        self, candidate_id: int, db: AsyncSession
    ) -> Optional[PlannerContext]:
        """
        Return profile data formatted for the Planner Agent.

        Returns a PlannerContext dict with skill_scores (running averages)
        and growth_trends (per-skill trend direction).

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        db : AsyncSession
            The database session.

        Returns
        -------
        Optional[PlannerContext]
            Dict with skill_scores and growth_trends, or None if no profile.
        """
        stmt = select(LongitudinalProfile).where(
            LongitudinalProfile.candidate_id == candidate_id
        )
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if not profile:
            return None

        return PlannerContext(
            skill_scores=profile.skill_averages or {},
            growth_trends=profile.skill_trends or {},
        )


# ── Global instance ──────────────────────────────────────────────────────────
memory_service = MemoryService()
