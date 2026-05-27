import pytest
import os
import shutil
from typing import Dict, Any
from app.services.interview_engine.state import InterviewState
from app.services.interview_engine.nodes import (
    empathy_analyzer_node,
    skeptic_evaluation_node,
    pragmatist_evaluation_node,
    bias_auditor_node,
    consensus_synthesizer_node,
    code_copilot_node,
)
from app.services.interview_engine.graph import interview_graph
from app.services.rag_service import rag_service

@pytest.fixture(scope="module")
def mock_state() -> InterviewState:
    return {
        "messages": [
            {"role": "assistant", "content": "Welcome to the interview! Can you tell me how you build scalable APIs in Python?"},
            {"role": "user", "content": "Um, uh, I think I use FastAPI and like, maybe Celery for async tasks, but it's sorry, a bit difficult to remember everything."}
        ],
        "resume_text": "Experienced Python Backend Developer, specialized in FastAPI, PostgreSQL, Redis.",
        "job_role": "Senior Backend Engineer",
        "current_question_index": 1,
        "max_questions": 15,
        "interview_complete": False,
        "completion_reason": None,
        "current_phase": "technical",
        "phase_transition": False,
        "previous_phase": "warmup",
        "difficulty": "medium",
        "latest_score": 0.0,
        "metrics": {"accuracy": 0, "clarity": 0, "depth": 0, "communication": 0},
        "avg_score": 0.0,
        "covered_skills": [],
        "skills_to_cover": ["fastapi", "postgresql", "redis"],
        "pending_skills": ["fastapi", "postgresql", "redis"],
        "skill_coverage_percentage": 0.0,
        "topic_scores": {},
        "topic_strengths": {},
        "total_responses": 1,
        "low_quality_count": 0,
        "high_quality_count": 0,
        "interviewer_mode": "ai",
        "hr_instructions": None,
        "last_evaluation": None,
        "next_question": {"question": "How do you build scalable APIs in Python?", "skill_tested": "api"},
        "code_snippet": "def get_api(): pass",
        "code_language": "python",
        "is_coding_mode": True,
        "follow_up_requested": False,
        "previous_topic": "api",
        "supervisor_session_id": "test_session_123",
        "supervisor_mode": "suggest",
        "supervisor_observations": [],
        "supervisor_last_action": None,
        "supervisor_paused": False,
        "session_start_epoch": 1716499999.0,
        "question_start_epoch": 1716499999.0,
        "per_question_times": [],
        "score_history": [],
        "difficulty_history": ["medium"],
        "copilot_suggestions": [],
        "copilot_request_pending": True,
        "hr_whisper_instructions": "Focus heavily on concurrent processes.",
        "empathy_metrics": {"stress_level": 0.0, "hesitation_rating": 0.0, "typing_speed": 0.0},
        "rag_context": "Background: Candidate built microservices with FastAPI.",
        "debate_rounds": None,
        "skeptic_critique": None,
        "pragmatist_critique": None,
        "bias_auditor_critique": None,
    }

@pytest.mark.asyncio
async def test_empathy_analyzer(mock_state):
    # Test empathy analyzer node
    res = await empathy_analyzer_node(mock_state)
    assert "empathy_metrics" in res
    metrics = res["empathy_metrics"]
    assert "stress_level" in metrics
    assert "hesitation_rating" in metrics
    assert "typing_speed" in metrics
    
    # Stress level should be high because of multiple hesitation words and moderate length
    assert metrics["stress_level"] > 2.0
    assert metrics["hesitation_rating"] > 0.0

@pytest.mark.asyncio
async def test_code_copilot(mock_state):
    # Test co-pilot suggestions generator
    res = await code_copilot_node(mock_state)
    assert "copilot_suggestions" in res
    assert len(res["copilot_suggestions"]) > 0
    assert "hint" in res["copilot_suggestions"][0]
    assert res["copilot_request_pending"] is False

@pytest.mark.asyncio
async def test_evaluation_debate(mock_state):
    # Run parallel nodes and verify output keys
    skeptic_res = await skeptic_evaluation_node(mock_state)
    assert "skeptic_critique" in skeptic_res
    assert isinstance(skeptic_res["skeptic_critique"], str)
    
    pragmatist_res = await pragmatist_evaluation_node(mock_state)
    assert "pragmatist_critique" in pragmatist_res
    
    auditor_res = await bias_auditor_node(mock_state)
    assert "bias_auditor_critique" in auditor_res

@pytest.mark.asyncio
async def test_consensus_synthesizer(mock_state):
    # Set critiques in state
    state_with_critiques = mock_state.copy()
    state_with_critiques["skeptic_critique"] = "Lack of detail on concurrency."
    state_with_critiques["pragmatist_critique"] = "Readability is acceptable, uses standard imports."
    state_with_critiques["bias_auditor_critique"] = "Correct core ideas present."
    
    res = await consensus_synthesizer_node(state_with_critiques)
    assert "last_evaluation" in res
    assert "latest_score" in res
    assert "metrics" in res
    assert res["skeptic_critique"] is None # cleared

@pytest.mark.asyncio
async def test_rag_service():
    session_id = "test_session_rag_456"
    resume = "Candidate is an expert in Docker, Kubernetes, and Golang backend development."
    
    # Clean chroma persistent directory to avoid stale data corruption
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "db", "chroma")
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    os.makedirs(db_path, exist_ok=True)
    # Reset singleton state so _ensure_initialized() creates a fresh client
    rag_service._initialized = False
    rag_service.client = None
    rag_service.collection = None
    
    try:
        # Index resume
        await rag_service.index_resume(session_id, resume)
        
        # Query context
        context = rag_service.query_context(session_id, "Does candidate know Kubernetes?")
        assert "Kubernetes" in context
        
        # Index fake github profile
        await rag_service.index_github_profile(session_id, "mock_user")
        
    finally:
        # Clean up
        rag_service.clear_session_data(session_id)

def test_graph_compilation():
    # Verify graph compiled and nodes are valid
    assert interview_graph is not None
    assert "generate_question" in interview_graph.nodes
    assert "empathy_analyzer" in interview_graph.nodes
    assert "consensus_synthesizer" in interview_graph.nodes
    assert "code_copilot" in interview_graph.nodes


def test_pdf_report_with_radar_chart():
    from app.services.pdf_service import generate_interview_pdf
    
    candidate_name = "Jane Doe"
    job_role = "Senior FastAPI Developer"
    report = {
        "overall_score": 8.5,
        "technical_accuracy": 9.0,
        "communication_clarity": 8.0,
        "depth_of_knowledge": 8.5,
        "hire_recommendation": "strong_hire",
        "summary": "Excellent depth of FastAPI concurrency models and postgresql execution optimization.",
        "strengths": ["Strong coding habits", "Vocal logic formulation"],
        "weaknesses": ["Minor typing stutter under pressure"]
    }
    transcript = [
        {"role": "assistant", "content": "Explain how task queues work in Celery."},
        {"role": "user", "content": "Celery uses brokers like Redis or RabbitMQ to route messages asynchronously to workers."}
    ]
    skill_matrix = {
        "fastapi": 9.0,
        "postgresql": 7.5,
        "redis": 8.5,
        "celery": 9.0
    }
    
    pdf_bytes = generate_interview_pdf(
        candidate_name=candidate_name,
        job_role=job_role,
        report=report,
        transcript=transcript,
        skill_matrix=skill_matrix
    )
    
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000  # Should be a valid PDF document of significant size
    # Check signature magic bytes of PDF
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_takeover_question_node(mock_state):
    from app.services.interview_engine.nodes import generate_question_node
    state_with_takeover = mock_state.copy()
    state_with_takeover["supervisor_mode"] = "hr_takeover"
    
    res = await generate_question_node(state_with_takeover)
    assert "next_question" in res
    q = res["next_question"]
    assert "recruiter has taken over" in q["question"]
    assert q["category"] == "situational"
    assert q["time_limit"] == 600
