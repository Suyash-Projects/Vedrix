"""
ObservabilityService — append-only agent audit trail.

Design: Observability_Layer (Section 10 of design.md)
Requirements: 10.1, 10.2, 10.3, 10.6, 10.7, 10.8, 10.10, 10.11, 10.12

Key guarantees
--------------
* Append-only: no UPDATE or DELETE methods are exposed.
* Role-based redaction: HR callers never see raw_input / raw_output.
* Runaway-loop detection: >10,000 entries for a single session triggers an
  alert and sets a per-session pause flag.
* @trace_agent_action decorator: wraps any async function, measures wall-clock
  time, captures input/output summaries, and writes a TraceEntry to the DB.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trace_entry import TraceEntry, TraceEntryCreate

logger = logging.getLogger(__name__)

# ── Runaway-loop threshold ────────────────────────────────────────────────────
RUNAWAY_LOOP_THRESHOLD = 10_000

# ── In-memory pause flags: session_id -> bool ────────────────────────────────
# A True value means the agent for that session has been paused due to a
# runaway loop. Consumers (agents) should check this before proceeding.
_session_pause_flags: Dict[int, bool] = {}


def is_session_paused(session_id: int) -> bool:
    """Return True if the given session has been paused due to a runaway loop."""
    return _session_pause_flags.get(session_id, False)


def clear_session_pause(session_id: int) -> None:
    """Allow an Admin to clear the pause flag for a session."""
    _session_pause_flags.pop(session_id, None)


# ── ObservabilityService ──────────────────────────────────────────────────────

class ObservabilityService:
    """
    Append-only service for recording and querying agent Trace_Entries.

    All write operations go through `record()`. There are intentionally no
    update or delete methods — the table is append-only by design.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Write ─────────────────────────────────────────────────────────────────

    async def record(self, entry: TraceEntryCreate) -> TraceEntry:
        """
        Persist a new TraceEntry.

        Also checks for runaway loops: if the session already has ≥10,000
        entries, emits a log alert and sets the session pause flag.

        Parameters
        ----------
        entry : TraceEntryCreate
            The data to persist.

        Returns
        -------
        TraceEntry
            The newly created (and DB-refreshed) record.
        """
        db_entry = TraceEntry(
            agent_name=entry.agent_name,
            action_type=entry.action_type,
            session_id=entry.session_id,
            workflow_id=entry.workflow_id,
            candidate_id=entry.candidate_id,
            input_summary=entry.input_summary,
            reasoning_summary=entry.reasoning_summary,
            output_summary=entry.output_summary,
            confidence_score=entry.confidence_score,
            raw_input=entry.raw_input,
            raw_output=entry.raw_output,
            duration_ms=entry.duration_ms,
            timestamp=datetime.now(timezone.utc),
        )

        self._db.add(db_entry)
        await self._db.commit()
        await self._db.refresh(db_entry)

        # ── Runaway-loop detection ────────────────────────────────────────────
        if entry.session_id is not None:
            await self._check_runaway_loop(entry.session_id)

        return db_entry

    async def _check_runaway_loop(self, session_id: int) -> None:
        """
        Count entries for the session and emit an alert + pause flag when the
        threshold is exceeded.
        """
        stmt = (
            select(func.count(TraceEntry.id))
            .where(TraceEntry.session_id == session_id)
        )
        result = await self._db.execute(stmt)
        count: int = result.scalar_one()

        if count >= RUNAWAY_LOOP_THRESHOLD and not _session_pause_flags.get(session_id):
            _session_pause_flags[session_id] = True
            logger.critical(
                "RUNAWAY LOOP DETECTED — session_id=%s has %d TraceEntries "
                "(threshold=%d). Agent has been paused. An Admin must call "
                "clear_session_pause(%s) to resume.",
                session_id,
                count,
                RUNAWAY_LOOP_THRESHOLD,
                session_id,
            )

    # ── Read ──────────────────────────────────────────────────────────────────

    async def query(
        self,
        agent_name: Optional[str] = None,
        session_id: Optional[int] = None,
        action_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        requester_role: str = "admin",
    ) -> List[TraceEntry]:
        """
        Return TraceEntries matching the given filters.

        Role-based redaction
        --------------------
        * ``requester_role == "admin"`` — full records returned as-is.
        * Any other role (e.g. ``"hr"``) — ``raw_input`` and ``raw_output``
          are set to ``None`` on each returned object before returning.

        Parameters
        ----------
        agent_name     : Filter by agent name (exact match).
        session_id     : Filter by session ID.
        action_type    : Filter by action type (exact match).
        start_time     : Lower bound on timestamp (inclusive).
        end_time       : Upper bound on timestamp (inclusive).
        requester_role : Role of the caller; controls field redaction.

        Returns
        -------
        List[TraceEntry]
            Matching records, ordered by timestamp ascending.
        """
        stmt = select(TraceEntry)

        if agent_name is not None:
            stmt = stmt.where(TraceEntry.agent_name == agent_name)
        if session_id is not None:
            stmt = stmt.where(TraceEntry.session_id == session_id)
        if action_type is not None:
            stmt = stmt.where(TraceEntry.action_type == action_type)
        if start_time is not None:
            stmt = stmt.where(TraceEntry.timestamp >= start_time)
        if end_time is not None:
            stmt = stmt.where(TraceEntry.timestamp <= end_time)

        stmt = stmt.order_by(TraceEntry.timestamp.asc())

        result = await self._db.execute(stmt)
        entries: List[TraceEntry] = list(result.scalars().all())

        # Redact Admin-only fields for non-Admin callers
        if requester_role != "admin":
            for entry in entries:
                entry.raw_input = None
                entry.raw_output = None

        return entries

    async def export_session(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Return all TraceEntries for a session as a chronologically ordered
        list of plain dicts (suitable for JSON serialisation).

        Admin-level export — raw fields are included.

        Parameters
        ----------
        session_id : The InterviewSession PK to export.

        Returns
        -------
        List[Dict[str, Any]]
            Chronological list of serialised TraceEntry records.
        """
        entries = await self.query(session_id=session_id, requester_role="admin")
        return [_entry_to_dict(e) for e in entries]

    async def get_explanation(
        self,
        session_id: int,
        score_type: str,
    ) -> List[TraceEntry]:
        """
        Retrieve TraceEntries relevant to explaining a specific score or
        decision for a session.

        The ``score_type`` is matched against ``action_type`` so callers can
        request e.g. ``score_type="bias_check"`` to get all QA_Agent entries.

        Sensitive fields are redacted (HR + Candidate callers use this).

        Parameters
        ----------
        session_id : The InterviewSession PK.
        score_type : The action_type to filter on.

        Returns
        -------
        List[TraceEntry]
            Matching entries with raw fields redacted.
        """
        return await self.query(
            session_id=session_id,
            action_type=score_type,
            requester_role="hr",  # redact raw fields for explanation endpoint
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _entry_to_dict(entry: TraceEntry) -> Dict[str, Any]:
    """Serialise a TraceEntry to a plain dict, converting datetime to ISO."""
    return {
        "id": entry.id,
        "agent_name": entry.agent_name,
        "action_type": entry.action_type,
        "session_id": entry.session_id,
        "workflow_id": entry.workflow_id,
        "candidate_id": entry.candidate_id,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "input_summary": entry.input_summary,
        "reasoning_summary": entry.reasoning_summary,
        "output_summary": entry.output_summary,
        "confidence_score": entry.confidence_score,
        "raw_input": entry.raw_input,
        "raw_output": entry.raw_output,
        "duration_ms": entry.duration_ms,
    }


def _safe_summary(value: Any, max_len: int = 500) -> Optional[str]:
    """
    Convert an arbitrary value to a short string summary.

    Dicts/lists are JSON-serialised and truncated. Strings are truncated
    directly. None returns None.
    """
    if value is None:
        return None
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, default=str)
        except Exception:
            text = str(value)
    return text[:max_len] if len(text) > max_len else text


# ── @trace_agent_action decorator ────────────────────────────────────────────

def trace_agent_action(agent_name: str, action_type: str) -> Callable:
    """
    Async decorator factory that wraps an async function and records a
    TraceEntry to the database on every call.

    Usage
    -----
    ::

        @trace_agent_action("qa_agent", "bias_check")
        async def my_agent_function(state, db: AsyncSession, ...):
            ...

    The decorated function **must** accept a keyword argument ``db`` of type
    ``AsyncSession``. The decorator extracts it to create the
    ``ObservabilityService`` instance.

    If ``db`` is not present in the call arguments, the decorator logs a
    warning and skips recording (graceful degradation — the wrapped function
    still executes normally).

    Captured fields
    ---------------
    * ``input_summary``  — first positional arg (after ``self``/``state``) or
      ``kwargs`` serialised, truncated to 500 chars.
    * ``output_summary`` — return value serialised, truncated to 500 chars.
    * ``duration_ms``    — wall-clock time of the wrapped call.
    * ``raw_input``      — full first positional arg (stored encrypted).
    * ``raw_output``     — full return value (stored encrypted).

    Parameters
    ----------
    agent_name  : Value written to ``TraceEntry.agent_name``.
    action_type : Value written to ``TraceEntry.action_type``.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # ── Extract DB session ────────────────────────────────────────────
            db: Optional[AsyncSession] = kwargs.get("db")
            if db is None:
                # Try positional args — look for AsyncSession instance
                for arg in args:
                    if isinstance(arg, AsyncSession):
                        db = arg
                        break

            # ── Capture raw input ─────────────────────────────────────────────
            # Use the first non-self positional arg as the "input" for summary.
            raw_input_value: Any = None
            if len(args) > 1:
                raw_input_value = args[1]
            elif kwargs:
                raw_input_value = {k: v for k, v in kwargs.items() if k != "db"}

            start_ts = time.monotonic()
            exc_info: Optional[BaseException] = None
            result: Any = None

            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                exc_info = exc
                raise
            finally:
                duration_ms = int((time.monotonic() - start_ts) * 1000)

                if db is not None:
                    try:
                        entry = TraceEntryCreate(
                            agent_name=agent_name,
                            action_type=action_type,
                            input_summary=_safe_summary(raw_input_value),
                            output_summary=(
                                _safe_summary(result)
                                if exc_info is None
                                else f"ERROR: {_safe_summary(str(exc_info))}"
                            ),
                            raw_input=raw_input_value,
                            raw_output=result if exc_info is None else None,
                            duration_ms=duration_ms,
                        )
                        svc = ObservabilityService(db)
                        await svc.record(entry)
                    except Exception as record_exc:
                        # Recording must never crash the agent.
                        logger.warning(
                            "trace_agent_action: failed to record TraceEntry "
                            "for agent=%s action=%s: %s",
                            agent_name,
                            action_type,
                            record_exc,
                        )
                else:
                    logger.warning(
                        "trace_agent_action: no AsyncSession found for "
                        "agent=%s action=%s — TraceEntry not recorded.",
                        agent_name,
                        action_type,
                    )

            return result

        return wrapper

    return decorator
