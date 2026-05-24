"""
TraceEntry SQLModel — append-only audit record for every agent action.

Design: Observability_Layer (Section 10 of design.md)
Requirements: 10.1, 10.2, 10.3, 10.6, 10.7, 10.8, 10.10, 10.11, 10.12

Append-only semantics are enforced at the service layer (ObservabilityService
exposes no update/delete methods). No UPDATE or DELETE operations should ever
be issued against the `trace_entries` table.
"""
from datetime import datetime, timezone
from typing import Optional, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Text, Index
from app.core.encryption import EncryptedJSON


class TraceEntry(SQLModel, table=True):
    """
    Immutable, timestamped record of a single agent decision.

    Fields
    ------
    agent_name        : Name of the agent that produced this entry.
    action_type       : Category of action (e.g. "bias_check", "text_analysis").
    session_id        : InterviewSession PK — nullable for workflow-level actions.
    workflow_id       : CandidateWorkflow PK — nullable for session-level actions.
    candidate_id      : User PK of the candidate involved — nullable.
    timestamp         : UTC creation time; immutable after insert.
    input_summary     : Human-readable summary of inputs (non-sensitive).
    reasoning_summary : Human-readable summary of agent reasoning.
    output_summary    : Human-readable summary of outputs.
    confidence_score  : Agent's self-reported confidence (0.0–1.0).
    raw_input         : Full encrypted input payload — Admin-only.
    raw_output        : Full encrypted output payload — Admin-only.
    duration_ms       : Wall-clock time the agent action took.
    """

    __tablename__ = "trace_entries"
    __table_args__ = (
        Index("ix_trace_agent_session", "agent_name", "session_id"),
        Index("ix_trace_timestamp", "timestamp"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # ── Agent identification ──────────────────────────────────────────────────
    agent_name: str = Field(nullable=False, index=True)
    action_type: str = Field(nullable=False, index=True)

    # ── Context ───────────────────────────────────────────────────────────────
    session_id: Optional[int] = Field(default=None, index=True)
    workflow_id: Optional[int] = Field(default=None, index=True)
    candidate_id: Optional[int] = Field(default=None, index=True)

    # ── Immutable timestamp ───────────────────────────────────────────────────
    # server_default ensures the DB sets the value even if the ORM omits it.
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
        sa_column_kwargs={"server_default": "CURRENT_TIMESTAMP"},
    )

    # ── Trace content (non-sensitive — visible to HR + Admin) ─────────────────
    input_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    reasoning_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    output_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    confidence_score: Optional[float] = None

    # ── Admin-only sensitive fields (encrypted at rest) ───────────────────────
    raw_input: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    raw_output: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))

    # ── Latency tracking ──────────────────────────────────────────────────────
    duration_ms: Optional[int] = None


# ── Pydantic schema for creating a new TraceEntry ────────────────────────────
class TraceEntryCreate(SQLModel):
    """Input schema used by ObservabilityService.record()."""

    agent_name: str
    action_type: str
    session_id: Optional[int] = None
    workflow_id: Optional[int] = None
    candidate_id: Optional[int] = None
    input_summary: Optional[str] = None
    reasoning_summary: Optional[str] = None
    output_summary: Optional[str] = None
    confidence_score: Optional[float] = None
    raw_input: Optional[Any] = None
    raw_output: Optional[Any] = None
    duration_ms: Optional[int] = None


# ── Pydantic schema for reading a TraceEntry (HR view — redacted) ─────────────
class TraceEntryRead(SQLModel):
    """Public read schema. raw_input / raw_output are omitted for HR callers."""

    id: Optional[int]
    agent_name: str
    action_type: str
    session_id: Optional[int]
    workflow_id: Optional[int]
    candidate_id: Optional[int]
    timestamp: datetime
    input_summary: Optional[str]
    reasoning_summary: Optional[str]
    output_summary: Optional[str]
    confidence_score: Optional[float]
    duration_ms: Optional[int]


# ── Pydantic schema for reading a TraceEntry (Admin view — full) ──────────────
class TraceEntryReadAdmin(TraceEntryRead):
    """Extended read schema for Admin callers — includes encrypted fields."""

    raw_input: Optional[Any]
    raw_output: Optional[Any]
