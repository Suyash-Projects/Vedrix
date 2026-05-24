"""
QANode — Autonomous Interview Quality Assurance Agent (LangGraph node).

Design: QA_Agent (Section 7 of design.md)
Requirements: 7.1, 7.2, 7.3, 7.6, 7.7, 7.8, 7.9, 7.11

Key guarantees
--------------
* Deterministic bias detection: regex/keyword matching, no LLM calls.
* Relevance check: cosine similarity via existing SentenceTransformer model.
* Regeneration loop: up to 3 retries, then escalate to HR via WebSocket.
* Session quality score: (total - flagged) / total.
* Must complete within 500ms (no LLM calls — just keyword matching + embedding).
* Idempotent: same question always produces the same result.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from app.schemas.interview import BiasFlag, RelevanceFlag
from app.services.interview_engine.state import InterviewState
from app.services.observability_service import trace_agent_action

logger = logging.getLogger(__name__)

# ── Bias Marker Categories ────────────────────────────────────────────────────
# All matching is case-insensitive (text is normalized to lowercase before check).

GENDER_MARKERS: List[str] = [
    r"\bhe/she\b",
    r"\bhis/her\b",
    r"\bmanpower\b",
    r"\bchairman\b",
    r"\bspokesman\b",
    r"\bmankind\b",
    r"\bcareer[- ]oriented woman\b",
    r"\bfamily man\b",
    r"\bhousewife\b",
    r"\bguys\b",
]

AGE_MARKERS: List[str] = [
    r"\byoung\b",
    r"\bfresh graduate\b",
    r"\bdigital native\b",
    r"\benergetic\b",
    r"\brecent graduate\b",
    r"\bolderly\b",
    r"\bretirement age\b",
    r"\bmillennial\b",
    r"\bgen z\b",
    r"\boverqualified\b",
]

NATIONALITY_MARKERS: List[str] = [
    r"\bnative english\b",
    r"\bnative speaker\b",
    r"\bamerican style\b",
    r"\bcitizenship\b",
    r"\bforeign\b",
    r"\baccent\b",
    r"\bvisa status\b",
    r"\blegal resident\b",
    r"\bpassport\b",
    r"\bgreen card\b",
]

DISABILITY_MARKERS: List[str] = [
    r"\bphysically fit\b",
    r"\bstand for long periods\b",
    r"\bhandicapped\b",
    r"\bwheelchair\b",
    r"\bnormal sight\b",
    r"\bnormal hearing\b",
    r"\bhealthy\b",
    r"\bable[- ]bodied\b",
]

# Category name → marker list mapping
BIAS_CATEGORIES: Dict[str, List[str]] = {
    "gender": GENDER_MARKERS,
    "age": AGE_MARKERS,
    "nationality": NATIONALITY_MARKERS,
    "disability": DISABILITY_MARKERS,
}

# Maximum regeneration attempts before HR escalation
MAX_REGENERATION_ATTEMPTS = 3


class QANode:
    """
    LangGraph node that evaluates generated questions for bias and relevance.

    Inserted between `generate_question` and `sentiment_agent_node` in the graph.
    Returns either `{approved: True}` or `{regenerate: True, bias_flag: {...}}`.
    """

    @trace_agent_action("qa_agent", "bias_check")
    async def __call__(self, state: InterviewState) -> Dict[str, Any]:
        """
        LangGraph node entry point.

        Evaluates the current question in state for bias and relevance.
        Manages regeneration count and escalation logic.

        Returns
        -------
        Dict with keys:
            - approved: True if question passes all checks
            - regenerate: True if question should be regenerated
            - bias_flag: BiasFlag dict if bias detected
            - relevance_flag: RelevanceFlag dict if off-topic
            - qa_regeneration_count: updated count
            - qa_session_quality_score: updated quality score
            - qa_flags: updated flags list
        """
        start_time = time.monotonic()

        # Extract question from state
        next_question = state.get("next_question")
        question_text = ""
        if next_question and isinstance(next_question, dict):
            question_text = next_question.get("question", "") or next_question.get("text", "")
        elif next_question and isinstance(next_question, str):
            question_text = next_question

        if not question_text:
            # No question to evaluate — approve by default
            return {"approved": True}

        # Get required skills from state
        skills_to_cover = state.get("skills_to_cover", []) or []
        job_role = state.get("job_role", "")

        # If no skills list, use job_role as a single-item list for relevance check
        required_skills = skills_to_cover if skills_to_cover else ([job_role] if job_role else [])

        # Get current QA tracking state
        qa_regeneration_count = state.get("qa_regeneration_count", 0)
        qa_flags = list(state.get("qa_flags", []) or [])
        total_questions = state.get("current_question_index", 0) + 1

        # ── Bias Check ────────────────────────────────────────────────────────
        bias_flag = self.check_bias(question_text)

        # ── Relevance Check ───────────────────────────────────────────────────
        relevance_flag = self.check_relevance(question_text, required_skills)

        # ── Decision Logic ────────────────────────────────────────────────────
        is_flagged = bias_flag is not None or relevance_flag is not None

        if is_flagged:
            # Record the flag
            flag_record: Dict[str, Any] = {
                "question_text": question_text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if bias_flag:
                flag_record["bias_flag"] = bias_flag.model_dump()
            if relevance_flag:
                flag_record["relevance_flag"] = relevance_flag.model_dump()
            qa_flags.append(flag_record)

            # Check regeneration count
            if qa_regeneration_count < MAX_REGENERATION_ATTEMPTS:
                # Loop back to generate_question
                duration_ms = int((time.monotonic() - start_time) * 1000)
                if duration_ms > 500:
                    logger.warning(
                        "QA Agent exceeded 500ms budget: %dms", duration_ms
                    )

                # Compute quality score
                flagged_count = len(qa_flags)
                quality_score = self._compute_quality_score(total_questions, flagged_count)

                result: Dict[str, Any] = {
                    "regenerate": True,
                    "approved": False,
                    "qa_regeneration_count": qa_regeneration_count + 1,
                    "qa_session_quality_score": quality_score,
                    "qa_flags": qa_flags,
                }
                if bias_flag:
                    result["bias_flag"] = bias_flag.model_dump()
                if relevance_flag:
                    result["relevance_flag"] = relevance_flag.model_dump()
                return result
            else:
                # 4th failure — escalate to HR via WebSocket
                await self._escalate_to_hr(state, question_text, bias_flag, relevance_flag)

                duration_ms = int((time.monotonic() - start_time) * 1000)
                if duration_ms > 500:
                    logger.warning(
                        "QA Agent exceeded 500ms budget: %dms", duration_ms
                    )

                flagged_count = len(qa_flags)
                quality_score = self._compute_quality_score(total_questions, flagged_count)

                # Approve the question after escalation (HR has been notified)
                return {
                    "approved": True,
                    "escalated": True,
                    "qa_regeneration_count": 0,
                    "qa_session_quality_score": quality_score,
                    "qa_flags": qa_flags,
                }
        else:
            # Question passes all checks
            duration_ms = int((time.monotonic() - start_time) * 1000)
            if duration_ms > 500:
                logger.warning(
                    "QA Agent exceeded 500ms budget: %dms", duration_ms
                )

            flagged_count = len(qa_flags)
            quality_score = self._compute_quality_score(total_questions, flagged_count)

            return {
                "approved": True,
                "qa_regeneration_count": 0,
                "qa_session_quality_score": quality_score,
                "qa_flags": qa_flags,
            }

    def check_bias(self, question_text: str) -> Optional[BiasFlag]:
        """
        Deterministic bias detection using regex/keyword matching.

        Normalizes text to lowercase before matching against the four bias
        marker categories: gender-coded language, age references, nationality
        assumptions, and disability assumptions.

        Returns the first category that has matches. Each category is checked
        independently — only markers belonging to the detected category are
        reported.

        Parameters
        ----------
        question_text : The question text to evaluate.

        Returns
        -------
        BiasFlag if bias markers are found, None otherwise.
        """
        normalized_text = question_text.lower()

        for category, patterns in BIAS_CATEGORIES.items():
            category_markers: List[str] = []
            for pattern in patterns:
                match = re.search(pattern, normalized_text)
                if match:
                    category_markers.append(match.group(0))

            if category_markers:
                return BiasFlag(
                    category=category,
                    markers_found=category_markers,
                    question_text=question_text,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

        return None

    def check_relevance(
        self,
        question_text: str,
        required_skills: List[str],
        threshold: float = 0.4,
    ) -> Optional[RelevanceFlag]:
        """
        Evaluate question relevance by embedding similarity.

        Embeds the question using the existing SentenceTransformer('all-MiniLM-L6-v2')
        from rag_service and computes cosine similarity against each required skill.
        If the maximum similarity is below the threshold, flags as off-topic.

        Parameters
        ----------
        question_text : The question text to evaluate.
        required_skills : List of required skills for the job role.
        threshold : Cosine similarity threshold (default 0.4).

        Returns
        -------
        RelevanceFlag if question is off-topic, None otherwise.
        """
        if not required_skills or not question_text.strip():
            return None

        try:
            # Lazy import to avoid module-level ChromaDB initialization failures
            from app.services.rag_service import rag_service

            # Embed question and skills using existing SentenceTransformer
            question_embedding = rag_service.model.encode([question_text])[0]
            skill_embeddings = rag_service.model.encode(required_skills)

            # Compute cosine similarity against each skill
            max_similarity = -1.0
            closest_skill = required_skills[0]

            for skill, skill_emb in zip(required_skills, skill_embeddings):
                similarity = self._cosine_similarity(question_embedding, skill_emb)
                if similarity > max_similarity:
                    max_similarity = similarity
                    closest_skill = skill

            if max_similarity < threshold:
                return RelevanceFlag(
                    similarity_score=float(max_similarity),
                    closest_skill=closest_skill,
                    question_text=question_text,
                    threshold=threshold,
                )

        except Exception as e:
            logger.error("QA relevance check failed: %s", e)
            # On failure, don't flag — graceful degradation
            return None

        return None

    def _cosine_similarity(self, vec1: Any, vec2: Any) -> float:
        """Compute cosine similarity between two vectors."""
        v1 = np.asarray(vec1, dtype=np.float32)
        v2 = np.asarray(vec2, dtype=np.float32)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def _compute_quality_score(self, total_questions: int, flagged_count: int) -> float:
        """
        Compute session quality score: (N - K) / N.

        Parameters
        ----------
        total_questions : Total number of questions evaluated (N).
        flagged_count : Number of flagged questions (K).

        Returns
        -------
        Quality score between 0.0 and 1.0.
        """
        if total_questions <= 0:
            return 1.0
        return max(0.0, (total_questions - flagged_count) / total_questions)

    async def _escalate_to_hr(
        self,
        state: InterviewState,
        question_text: str,
        bias_flag: Optional[BiasFlag],
        relevance_flag: Optional[RelevanceFlag],
    ) -> None:
        """
        Escalate to HR via WebSocket on 4th regeneration failure.

        Sends the original question and flag details to connected HR users.
        """
        try:
            from app.api.v1.endpoints.interview import manager

            # Determine session_id from state for WebSocket routing
            session_id = state.get("supervisor_session_id", "")
            if not session_id:
                logger.warning("QA Agent: no session_id available for HR escalation")
                return

            escalation_message: Dict[str, Any] = {
                "type": "qa_escalation",
                "data": {
                    "question_text": question_text,
                    "reason": "Question failed QA checks after 3 regeneration attempts",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

            if bias_flag:
                escalation_message["data"]["bias_flag"] = bias_flag.model_dump()
            if relevance_flag:
                escalation_message["data"]["relevance_flag"] = relevance_flag.model_dump()

            await manager.broadcast_to_hr(escalation_message, str(session_id))
            logger.info(
                "QA Agent escalated to HR for session %s: question failed after %d attempts",
                session_id,
                MAX_REGENERATION_ATTEMPTS + 1,
            )
        except Exception as e:
            logger.error("QA Agent HR escalation failed: %s", e)


# ── Inline evaluation interface (used by generate_question_node in nodes.py) ──

class QAAgentInline:
    """
    Lightweight wrapper exposing `evaluate_question()` for inline use inside
    `generate_question_node`. This is separate from the LangGraph node entry
    point which operates on full InterviewState.
    """

    def __init__(self, qa_node: QANode):
        self._qa = qa_node

    async def evaluate_question(
        self,
        question_text: str,
        required_skills: List[str],
        state: InterviewState,
    ) -> Dict[str, Any]:
        """
        Evaluate a single question for bias and relevance.

        Returns a dict compatible with the nodes.py QA loop:
            - is_flagged: bool
            - bias_flag: Optional[dict] with 'type' and 'details'
            - is_off_topic: bool
            - relevance_score: float
            - closest_skill: str
            - evaluation_time_ms: int
        """
        start_time = time.monotonic()

        bias_flag_obj = self._qa.check_bias(question_text)
        relevance_flag_obj = self._qa.check_relevance(question_text, required_skills)

        duration_ms = int((time.monotonic() - start_time) * 1000)

        is_flagged = bias_flag_obj is not None or relevance_flag_obj is not None

        bias_flag_dict: Optional[Dict[str, Any]] = None
        if bias_flag_obj:
            bias_flag_dict = {
                "type": bias_flag_obj.category,
                "details": f"Bias markers found: {', '.join(bias_flag_obj.markers_found)}",
            }

        is_off_topic = relevance_flag_obj is not None
        relevance_score = relevance_flag_obj.similarity_score if relevance_flag_obj else 1.0
        closest_skill = relevance_flag_obj.closest_skill if relevance_flag_obj else (required_skills[0] if required_skills else "")

        return {
            "is_flagged": is_flagged,
            "bias_flag": bias_flag_dict,
            "is_off_topic": is_off_topic,
            "relevance_score": relevance_score,
            "closest_skill": closest_skill,
            "evaluation_time_ms": duration_ms,
        }


# ── LangGraph node function ──────────────────────────────────────────────────

_qa_node_instance = QANode()

# Inline evaluator used by generate_question_node in nodes.py
qa_agent = QAAgentInline(_qa_node_instance)


async def qa_agent_node(state: InterviewState) -> Dict[str, Any]:
    """LangGraph node entry point for the QA Agent."""
    return await _qa_node_instance(state)
