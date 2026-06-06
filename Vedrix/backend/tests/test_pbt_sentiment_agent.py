"""
Property-based tests for the Real-Time Sentiment and Emotional Intelligence Agent.

Feature: agentic-platform-evolution (Requirement 6 — Sentiment_Agent)

These tests exercise the real SentimentNode API:
    - sentiment_node._analyze_response(text, state)  -> EmpathyMetrics
    - sentiment_node.check_stress_alert(stress_history) -> bool

The underlying HuggingFace model (cardiffnlp/twitter-roberta-base-sentiment-latest /
distilbert-base-uncased-finetuned-sst-2-english) is slow/heavy to load and is
non-deterministic across environments. For the range-invariant and detection
properties we mock `get_hf_sentiment_pipeline` so the model inference is
deterministic and fast while still exercising the real rule-based + merge logic.
The alert-threshold property drives `check_stress_alert` directly with crafted
stress sequences (no model dependency), per the agent's design.
"""
import asyncio
from unittest.mock import patch, AsyncMock

from hypothesis import given, settings, strategies as st, HealthCheck

from app.services.interview_engine.sentiment_node import sentiment_node


# ── Test helpers ──────────────────────────────────────────────────────────────

def run_async(coro):
    """Run an async coroutine to completion on a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def make_fake_pipeline(label: str, score: float):
    """Build a fake (synchronous) HF sentiment pipeline returning a fixed result."""
    def _pipe(_text):
        return [{"label": label, "score": score}]
    return _pipe


def patch_hf(label: str, score: float):
    """Patch the module-level HF pipeline loader with a deterministic fake."""
    return patch(
        "app.services.interview_engine.sentiment_node.get_hf_sentiment_pipeline",
        new=AsyncMock(return_value=make_fake_pipeline(label, score)),
    )


def count_alerts(stress_sequence):
    """
    Model how `_process` would emit high_stress_alert events: an alert fires once
    on the rising edge where `check_stress_alert` first becomes True for a run of
    3+ consecutive responses with stress_level > 0.8.
    """
    history = []
    alerts = 0
    prev_alerting = False
    for s in stress_sequence:
        history.append(s)
        currently_alerting = sentiment_node.check_stress_alert(history)
        if currently_alerting and not prev_alerting:
            alerts += 1
        prev_alerting = currently_alerting
    return alerts


MOCK_STATE = {"messages": [], "empathy_metrics": {}}


# ── Property 21: Empathy Metrics Range Invariant ──────────────────────────────
@given(
    text=st.text(min_size=1, max_size=200),
    label=st.sampled_from(["POSITIVE", "NEGATIVE"]),
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_21_empathy_metrics_range_invariant(text, label, score):
    """Feature: agentic-platform-evolution, Property 21: Empathy Metrics Range Invariant
    For any text input, all four empathy metrics are within their defined ranges.
    **Validates: Requirements 6.2**
    """
    with patch_hf(label, score):
        metrics = run_async(sentiment_node._analyze_response(text, MOCK_STATE))

    assert -1.0 <= metrics["sentiment_score"] <= 1.0
    assert 0.0 <= metrics["stress_level"] <= 1.0
    assert 0.0 <= metrics["hesitation_rating"] <= 1.0
    assert 0.0 <= metrics["confidence_level"] <= 1.0


# ── Property 22: Positive Sentiment Detection ─────────────────────────────────
@given(positive_text=st.sampled_from([
    "Yes, absolutely, I agree that it is a great approach and a perfect solution",
    "Definitely, I have solved this issue and it is clear and good",
    "Excellent, I designed and implemented this awesome feature easily",
    "I am confident and excited, this is a strong and clear answer",
]))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_22_positive_sentiment_detection(positive_text):
    """Feature: agentic-platform-evolution, Property 22: Positive Sentiment Detection
    Clear affirmative text (no uncertainty markers) yields sentiment_score > 0.0.
    **Validates: Requirements 6.4**
    """
    with patch_hf("POSITIVE", 0.95):
        metrics = run_async(sentiment_node._analyze_response(positive_text, MOCK_STATE))

    assert metrics["sentiment_score"] > 0.0


# ── Property 23: Stress Detection ─────────────────────────────────────────────
@given(distress_text=st.sampled_from([
    "I'm feeling very anxious and nervous about this task, it is so stressful",
    "I am not sure, I think I'm completely stuck and confused here",
    "This is too difficult, I am worried and overwhelmed and frustrated",
    "I don't know, I feel lost and struggling with this, very stressed",
]))
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_23_stress_detection(distress_text):
    """Feature: agentic-platform-evolution, Property 23: Stress Detection
    Text with explicit distress/uncertainty markers yields stress_level > 0.5.
    **Validates: Requirements 6.5**
    """
    with patch_hf("NEGATIVE", 0.95):
        metrics = run_async(sentiment_node._analyze_response(distress_text, MOCK_STATE))

    assert metrics["stress_level"] > 0.5


# ── Property 24: High Stress Alert Threshold ──────────────────────────────────
@given(
    low_prefix=st.lists(
        st.floats(min_value=0.0, max_value=0.8, allow_nan=False, allow_infinity=False),
        min_size=0, max_size=5,
    ),
    high_block=st.lists(
        st.floats(min_value=0.81, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=3, max_size=12,
    ),
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_property_24_high_stress_alert_threshold(low_prefix, high_block):
    """Feature: agentic-platform-evolution, Property 24: High Stress Alert Threshold
    A single run of 3+ consecutive responses with stress_level > 0.8 emits exactly
    one high_stress_alert.
    **Validates: Requirements 6.7**
    """
    # low_prefix values are all <= 0.8 (never qualify), followed by one contiguous
    # run of high-stress responses (> 0.8) of length >= 3.
    sequence = list(low_prefix) + list(high_block)

    # Exactly one alert is emitted across the single qualifying run.
    assert count_alerts(sequence) == 1

    # Threshold anchor: 3 consecutive responses > 0.8 trigger the alert condition.
    assert sentiment_node.check_stress_alert(high_block) is True

    # Fewer than 3 consecutive high responses never trigger an alert.
    assert count_alerts(high_block[:2]) == 0
