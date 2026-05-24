"""
ProctorService — Multi-Modal Proctoring Agent.

Design: Proctor_Agent (Section 3 of design.md)
Requirements: 3.1, 3.2, 3.3, 3.4, 3.7, 3.8, 3.9, 3.11

Key behaviors
-------------
* Records ViolationRecords only when session is "in_progress".
* Respects consent: full monitoring if granted, tab-switch only if not.
* Emits real-time HR alert via WebSocket when tab-switch count > threshold.
* Analyzes typing cadence: flags anomalous typing when inter-keystroke
  interval deviates > 3 std devs from session baseline.
* Finalizes session by attaching all ViolationRecords to evidence_log.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewSession
from app.models.violation_record import ViolationRecord
from app.services.observability_service import trace_agent_action

logger = logging.getLogger(__name__)

# Default threshold for tab-switch alerts
DEFAULT_TAB_SWITCH_THRESHOLD = 3


class ViolationSummary:
    """Summary of violations for a session."""

    def __init__(
        self,
        session_id: int,
        counts: Dict[str, int],
        timestamps: Dict[str, List[str]],
        total: int,
    ):
        self.session_id = session_id
        self.counts = counts
        self.timestamps = timestamps
        self.total = total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "counts": self.counts,
            "timestamps": self.timestamps,
            "total": self.total,
        }


class ProctorService:
    """
    Multi-Modal Proctoring Agent service.

    All public methods are async and decorated with @trace_agent_action.
    """

    @trace_agent_action("proctor_agent", "handle_browser_event")
    async def handle_browser_event(
        self,
        session_id: int,
        event_type: str,
        payload: Dict[str, Any],
        session_status: str,
        consent_granted: bool,
        db: AsyncSession,
        tab_switch_threshold: int = DEFAULT_TAB_SWITCH_THRESHOLD,
    ) -> Optional[ViolationRecord]:
        """
        Process a browser event and optionally record a ViolationRecord.

        Parameters
        ----------
        session_id : The InterviewSession PK.
        event_type : One of "tab_switch", "paste_detected", "anomalous_typing", etc.
        payload : Event-specific data (e.g., character_count for paste).
        session_status : Current session status (must be "in_progress" to record).
        consent_granted : Whether the candidate consented to full monitoring.
        db : AsyncSession for DB operations.
        tab_switch_threshold : Number of tab switches before HR alert (default 3).

        Returns
        -------
        ViolationRecord if recorded, None otherwise.
        """
        # AC 8: Only record during "in_progress" sessions
        if session_status != "in_progress":
            return None

        # AC 11: Without consent, restrict to tab-switch only
        if not consent_granted and event_type != "tab_switch":
            return None

        # Persist ViolationRecord
        violation = ViolationRecord(
            session_id=session_id,
            violation_type=event_type,
            payload=payload,
            consent_granted=consent_granted,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(violation)
        await db.commit()
        await db.refresh(violation)

        # AC 2: Emit HR alert when tab-switch count exceeds threshold
        if event_type == "tab_switch":
            count_stmt = (
                select(func.count(ViolationRecord.id))
                .where(ViolationRecord.session_id == session_id)
                .where(ViolationRecord.violation_type == "tab_switch")
            )
            count_res = await db.execute(count_stmt)
            tab_switch_count = count_res.scalar() or 0

            if tab_switch_count > tab_switch_threshold:
                await self._emit_hr_alert(session_id, tab_switch_count)

        return violation

    @trace_agent_action("proctor_agent", "get_session_violations")
    async def get_session_violations(
        self,
        session_id: int,
        db: AsyncSession,
    ) -> List[ViolationRecord]:
        """
        Retrieve all ViolationRecords for a session, ordered by detected_at.

        Parameters
        ----------
        session_id : The InterviewSession PK.
        db : AsyncSession for DB operations.

        Returns
        -------
        List of ViolationRecord objects.
        """
        stmt = (
            select(ViolationRecord)
            .where(ViolationRecord.session_id == session_id)
            .order_by(ViolationRecord.detected_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @trace_agent_action("proctor_agent", "get_violation_summary")
    async def get_violation_summary(
        self,
        session_id: int,
        db: AsyncSession,
    ) -> ViolationSummary:
        """
        Return count per violation_type + timestamps for a session.

        Parameters
        ----------
        session_id : The InterviewSession PK.
        db : AsyncSession for DB operations.

        Returns
        -------
        ViolationSummary with counts and timestamps per type.
        """
        violations = await self.get_session_violations(session_id, db=db)

        counts: Dict[str, int] = {}
        timestamps: Dict[str, List[str]] = {}

        for v in violations:
            vtype = v.violation_type
            counts[vtype] = counts.get(vtype, 0) + 1
            if vtype not in timestamps:
                timestamps[vtype] = []
            timestamps[vtype].append(v.detected_at.isoformat())

        return ViolationSummary(
            session_id=session_id,
            counts=counts,
            timestamps=timestamps,
            total=len(violations),
        )

    @trace_agent_action("proctor_agent", "finalize_session")
    async def finalize_session(
        self,
        session_id: int,
        db: AsyncSession,
    ) -> None:
        """
        Attach all ViolationRecords for the session to the InterviewSession's
        evidence_log field.

        Parameters
        ----------
        session_id : The InterviewSession PK.
        db : AsyncSession for DB operations.
        """
        # Fetch all violations
        violations = await self.get_session_violations(session_id, db=db)

        # Fetch the session
        stmt = select(InterviewSession).where(InterviewSession.id == session_id)
        result = await db.execute(stmt)
        session_rec = result.scalars().first()

        if not session_rec:
            logger.warning(
                "finalize_session: session %s not found", session_id
            )
            return

        # Build evidence log entry
        evidence_log = session_rec.evidence_log or {}
        if not isinstance(evidence_log, dict):
            evidence_log = {"raw": evidence_log}

        evidence_log["violations"] = [
            {
                "violation_id": v.id,
                "violation_type": v.violation_type,
                "detected_at": v.detected_at.isoformat(),
                "payload": v.payload,
                "consent_granted": v.consent_granted,
            }
            for v in violations
        ]
        evidence_log["violation_count"] = len(violations)
        evidence_log["finalized_at"] = datetime.now(timezone.utc).isoformat()

        session_rec.evidence_log = evidence_log
        db.add(session_rec)
        await db.commit()

    @trace_agent_action("proctor_agent", "analyze_typing_cadence")
    async def analyze_typing_cadence(
        self,
        keystroke_timestamps: List[float],
        baseline_mean: float,
        baseline_std: float,
        db: AsyncSession,
        session_id: Optional[int] = None,
        consent_granted: bool = True,
    ) -> Optional[ViolationRecord]:
        """
        Detect anomalous typing when inter-keystroke interval deviates
        > 3 standard deviations from the session baseline.

        Parameters
        ----------
        keystroke_timestamps : List of timestamps (in seconds or ms) for keystrokes.
        baseline_mean : Mean inter-keystroke interval for the session baseline.
        baseline_std : Standard deviation of inter-keystroke intervals for baseline.
        db : AsyncSession for DB operations.
        session_id : Optional session ID to record the violation against.
        consent_granted : Whether consent was granted (needed for recording).

        Returns
        -------
        ViolationRecord if anomalous typing detected, None otherwise.
        """
        # Need at least 2 timestamps to compute intervals
        if len(keystroke_timestamps) < 2:
            return None

        # Compute inter-keystroke intervals
        intervals = [
            keystroke_timestamps[i + 1] - keystroke_timestamps[i]
            for i in range(len(keystroke_timestamps) - 1)
        ]

        # Compute mean interval for this sample
        sample_mean = sum(intervals) / len(intervals)

        # Check deviation from baseline
        # Avoid division by zero: if baseline_std is 0, we can't detect anomalies
        if baseline_std <= 0:
            return None

        deviation = abs(sample_mean - baseline_mean) / baseline_std

        # AC 4: Flag when deviation > 3 standard deviations
        if deviation > 3.0:
            payload = {
                "sample_mean_interval": round(sample_mean, 4),
                "baseline_mean": round(baseline_mean, 4),
                "baseline_std": round(baseline_std, 4),
                "deviation_std_devs": round(deviation, 2),
                "keystroke_count": len(keystroke_timestamps),
                "interval_count": len(intervals),
            }

            # If session_id provided, persist the violation
            if session_id is not None:
                violation = ViolationRecord(
                    session_id=session_id,
                    violation_type="anomalous_typing",
                    payload=payload,
                    consent_granted=consent_granted,
                    detected_at=datetime.now(timezone.utc),
                )
                db.add(violation)
                await db.commit()
                await db.refresh(violation)
                return violation

            # Return an unsaved ViolationRecord for analysis purposes
            return ViolationRecord(
                session_id=session_id or 0,
                violation_type="anomalous_typing",
                payload=payload,
                consent_granted=consent_granted,
                detected_at=datetime.now(timezone.utc),
            )

        return None

    async def _emit_hr_alert(self, session_id: int, tab_switch_count: int) -> None:
        """
        Emit a real-time alert to HR via WebSocket when tab-switch threshold
        is exceeded.
        """
        # Import here to avoid circular imports
        from app.api.v1.endpoints.interview import manager

        alert_msg = {
            "type": "proctor_alert",
            "session_id": str(session_id),
            "violation_type": "tab_switch",
            "count": tab_switch_count,
            "message": f"Candidate has switched tabs {tab_switch_count} times.",
        }
        try:
            await manager.broadcast_to_hr(alert_msg, str(session_id))
        except Exception as ws_err:
            logger.error(
                "Failed to broadcast proctor alert over WebSocket: %s", ws_err
            )


proctor_service = ProctorService()
