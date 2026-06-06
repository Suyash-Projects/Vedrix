"""
Property-based tests for the QA_Agent (Question Bias and Relevance Gating).

Feature: agentic-platform-evolution
Design: QA_Agent (Section 7 of design.md)
Validates: Requirements 7.4, 7.5, 7.6, 7.8, 7.10

These tests exercise the real `QANode` evaluation logic via the inline
`qa_agent.evaluate_question(text, required_skills, state)` interface (the same
calling convention used by `generate_question_node`). Bias detection is fully
deterministic (regex/keyword matching). For relevance-threshold properties we
patch `rag_service.model` with a tiny deterministic stand-in so the cosine
similarity is exact, fast, and does not require loading SentenceTransformer.
"""
from __future__ import annotations

import asyncio
import math
from contextlib import contextmanager
from unittest.mock import patch

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st, HealthCheck, assume

from app.services import rag_service as rag_module
from app.services.interview_engine.qa_node import qa_agent, QANode, BIAS_CATEGORIES


# ── Helpers ───────────────────────────────────────────────────────────────────

def run_async(coro):
    """Run an async coroutine synchronously for use inside Hypothesis examples."""
    return asyncio.run(coro)


_QA = QANode()


class _OnTopicModel:
    """Fake embedding model: every text maps to the same unit vector.

    Cosine similarity between any question and any skill is therefore 1.0,
    which is comfortably above the 0.4 relevance threshold.
    """

    def encode(self, texts):
        return np.array([[1.0, 0.0, 0.0] for _ in texts], dtype=np.float32)


class _OffTopicModel:
    """Fake embedding model that maps skills onto one axis and everything else
    (the question) onto an orthogonal axis, yielding a cosine similarity of 0.0
    (strictly below the 0.4 threshold)."""

    def __init__(self, skills):
        self._skills = set(skills)

    def encode(self, texts):
        out = []
        for t in texts:
            if t in self._skills:
                out.append([0.0, 1.0, 0.0])  # skill axis
            else:
                out.append([1.0, 0.0, 0.0])  # question axis (orthogonal to skills)
        return np.array(out, dtype=np.float32)


@contextmanager
def patched_model(fake):
    """Temporarily replace the global rag_service embedding model."""
    with patch.object(rag_module.rag_service, "model", fake):
        yield


# A small set of literal tokens drawn from the four configured bias categories.
# Each token is known to match its category's regex markers in qa_node.
KNOWN_BIAS_TOKENS = [
    # gender
    "he/she", "manpower", "chairman", "spokesman", "mankind", "housewife", "guys",
    # age
    "young", "fresh graduate", "digital native", "energetic", "millennial",
    "gen z", "overqualified", "retirement age",
    # nationality
    "native speaker", "american style", "citizenship", "foreign", "accent",
    "visa status", "passport", "green card",
    # disability
    "physically fit", "handicapped", "wheelchair", "healthy", "able-bodied",
]


# ── Property 25: QA Zero False Positives ───────────────────────────────────────
@given(
    text=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz ",
        min_size=10,
        max_size=120,
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_property_25_qa_zero_false_positives(text):
    """Feature: agentic-platform-evolution, Property 25: For any question text that
    contains zero tokens from the configured bias marker list and has a cosine
    similarity to the required skills above 0.4, the QA_Agent SHALL produce zero
    Bias_Flag records and SHALL NOT mark the question as off-topic.

    Validates: Requirements 7.4
    """
    # Only keep genuinely clean questions (no configured bias marker present).
    assume(_QA.check_bias(text) is None)

    required_skills = ["python programming", "backend development"]
    with patched_model(_OnTopicModel()):
        res = run_async(qa_agent.evaluate_question(text, required_skills, {"job_role": "Developer"}))

    assert res["bias_flag"] is None
    assert res["is_off_topic"] is False
    assert res["is_flagged"] is False
    # cosine similarity (1.0) is above threshold -> high relevance score reported
    assert res["relevance_score"] >= 0.4


# ── Property 26: QA Detection Completeness ─────────────────────────────────────
@given(token=st.sampled_from(KNOWN_BIAS_TOKENS))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_property_26_qa_detection_completeness(token):
    """Feature: agentic-platform-evolution, Property 26: For any question text that
    contains at least one token from the configured bias marker list, the QA_Agent
    SHALL produce at least one Bias_Flag record identifying the bias category.

    Validates: Requirements 7.5
    """
    question = f"Please describe how a {token} candidate would handle this software role."

    # No skills passed -> relevance check is skipped; we only assert bias detection.
    res = run_async(qa_agent.evaluate_question(question, [], {"job_role": "Developer"}))

    assert res["bias_flag"] is not None, f"Expected a Bias_Flag for token {token!r}"
    assert res["is_flagged"] is True
    # The detected category must be one of the configured bias categories.
    assert res["bias_flag"]["type"] in BIAS_CATEGORIES


# ── Property 27: QA Idempotence ────────────────────────────────────────────────
@given(question=st.text(min_size=5, max_size=300))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_property_27_qa_idempotence(question):
    """Feature: agentic-platform-evolution, Property 27: For any question text Q,
    evaluating Q with the QA_Agent twice in succession SHALL produce identical
    Bias_Flag results (same flags, same categories, same off-topic determination).

    Validates: Requirements 7.10
    """
    state = {"job_role": "Developer"}
    res1 = run_async(qa_agent.evaluate_question(question, [], state))
    res2 = run_async(qa_agent.evaluate_question(question, [], state))

    # Compare all semantically meaningful fields (evaluation_time_ms is timing noise).
    assert res1["is_flagged"] == res2["is_flagged"]
    assert res1["bias_flag"] == res2["bias_flag"]
    assert res1["is_off_topic"] == res2["is_off_topic"]
    assert res1["relevance_score"] == res2["relevance_score"]
    assert res1["closest_skill"] == res2["closest_skill"]


# ── Property 28: QA Relevance Threshold ────────────────────────────────────────
@given(
    question=st.sampled_from(
        [
            "What is your favorite color and why do you enjoy it so much?",
            "Tell me about your weekend plans for the upcoming public holiday.",
            "Do you prefer tea or coffee in the early morning hours?",
            "Which season of the year makes you feel the happiest overall?",
            "How do you usually like to spend a relaxing rainy afternoon?",
        ]
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_property_28_qa_relevance_threshold(question):
    """Feature: agentic-platform-evolution, Property 28: For any question whose
    embedding has a cosine similarity strictly below 0.4 against all required skill
    embeddings, the QA_Agent SHALL mark the question as off-topic and produce a
    relevance flag with the computed similarity score.

    Validates: Requirements 7.6
    """
    required_skills = ["python programming", "database design", "system architecture"]

    with patched_model(_OffTopicModel(required_skills)):
        res = run_async(qa_agent.evaluate_question(question, required_skills, {"job_role": "Developer"}))

    assert res["is_off_topic"] is True
    assert res["is_flagged"] is True
    # Orthogonal embeddings -> cosine similarity 0.0, strictly below the 0.4 threshold.
    assert res["relevance_score"] < 0.4
    assert math.isclose(res["relevance_score"], 0.0, abs_tol=1e-6)
    assert res["closest_skill"] in required_skills


# ── Property 29: QA Session Quality Score Computation ──────────────────────────
@given(data=st.data())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_property_29_qa_session_quality_score(data):
    """Feature: agentic-platform-evolution, Property 29: For any session with N total
    questions evaluated and K questions flagged, the qa_session_quality_score SHALL
    equal (N - K) / N (the ratio of approved questions to total questions).

    Validates: Requirements 7.8
    """
    total = data.draw(st.integers(min_value=1, max_value=10_000))
    flagged = data.draw(st.integers(min_value=0, max_value=total))

    score = _QA._compute_quality_score(total, flagged)

    assert math.isclose(score, (total - flagged) / total, rel_tol=1e-9, abs_tol=1e-9)
    assert 0.0 <= score <= 1.0
