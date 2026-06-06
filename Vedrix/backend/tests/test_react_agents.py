"""
Tests for the ReAct agent wrappers and LangGraph node integration.

Covers:
- ReActInterviewerAgent: happy path, returns next_question
- ReActEvaluatorAgent: returns structured evaluation
- ReActSupervisorAgent: returns action recommendation
- ReActResearchAgent: returns enrichment summary
- LangGraph node wrappers: fallback when ReAct disabled, fallback on failure
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Force the deterministic path for the ReAct nodes in tests by default;
# individual tests opt in to ReAct by patching env vars or singletons.
os.environ.setdefault("VEDRIX_USE_REACT_AGENTS", "0")
os.environ.setdefault("VEDRIX_REACT_GRAPH", "0")

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from app.services.interview_engine.react_agents import (
    ReActEvaluatorAgent,
    ReActInterviewerAgent,
    ReActResearchAgent,
    ReActSupervisorAgent,
)
from app.services.interview_engine.react_nodes import (
    react_evaluator_node,
    react_interviewer_node,
    react_supervisor_node,
    reset_singletons,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class ScriptedLLM(GenericFakeChatModel):
    def __init__(self, messages):
        super().__init__(messages=iter(list(messages)))

    async def ainvoke(self, input, *args, **kwargs):
        return await super().ainvoke(input, *args, **kwargs)


def make_llm(*messages: str) -> ScriptedLLM:
    return ScriptedLLM(list(messages))


def make_state(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "messages": [],
        "current_question_index": 0,
        "max_questions": 10,
        "difficulty": "medium",
        "candidate_first_name": "Test",
        "job_role": "Backend Engineer",
        "skills_to_cover": ["python", "system_design"],
        "pending_skills": ["python", "system_design"],
        "covered_skills": [],
        "current_phase": "technical",
        "score_history": [],
        "difficulty_history": [],
        "per_question_times": [],
        "session_start_epoch": 0,
        "question_start_epoch": None,
        "latest_score": 0.0,
        "avg_score": 0.0,
        "skill_coverage_percentage": 0.0,
        "low_quality_count": 0,
        "high_quality_count": 0,
        "supervisor_paused": False,
        "supervisor_mode": "suggest",
    }
    if extra:
        base.update(extra)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Interviewer Agent
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_react_interviewer_returns_question_dict():
    """Interviewer: LLM emits a final answer JSON for the question schema."""
    llm = make_llm(
        'Thought: I have all I need.\n'
        'Final Answer: {"id": 1, "question": "How does Python GIL work?", '
        '"category": "technical", "difficulty": "medium", '
        '"time_limit": 120, "skill_tested": "python", "follow_up_topic": "threading"}'
    )
    agent = ReActInterviewerAgent(llm=llm)
    state = make_state()
    result = await agent.run(
        state=state, pending_skills=["python"], difficulty="medium", question_index=0
    )
    assert "next_question" in result
    q = result["next_question"]
    assert "question" in q and q["question"]
    assert q["skill_tested"] == "python"
    assert result["messages"][-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_react_interviewer_fills_missing_fields():
    """When the LLM omits a field, the agent backfills with safe defaults."""
    llm = make_llm('Final Answer: {"question": "Walk me through a REST API you built."}')
    agent = ReActInterviewerAgent(llm=llm)
    result = await agent.run(
        state=make_state(), pending_skills=["backend"], difficulty="easy", question_index=3
    )
    q = result["next_question"]
    assert q["id"] == 4  # question_index + 1
    assert q["difficulty"] == "easy"
    assert q["time_limit"] == 120


@pytest.mark.asyncio
async def test_react_interviewer_handles_non_dict_answer():
    """If the LLM returns a plain string, the agent coerces it to a question dict."""
    llm = make_llm('Final Answer: Tell me about your biggest bug fix.')
    agent = ReActInterviewerAgent(llm=llm)
    result = await agent.run(
        state=make_state(), pending_skills=["debugging"], difficulty="medium", question_index=0
    )
    # The string should be captured as the question text
    assert result["next_question"].get("question")
    assert "bug fix" in result["next_question"]["question"]


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Evaluator Agent
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_react_evaluator_returns_structured_evaluation():
    llm = make_llm(
        'Thought: I have what I need to score this.\n'
        'Final Answer: {"score": 8.5, "metrics": {"accuracy": 9, "clarity": 8, "depth": 8, "communication": 9}, '
        '"feedback": "Solid answer with concrete examples.", "topic": "python", '
        '"skill_category": "technical", "should_deep_dive": false, "is_coding_challenge": false, '
        '"needs_easier": false, "low_effort": false, "skill_identified": "python"}'
    )
    agent = ReActEvaluatorAgent(llm=llm)
    result = await agent.run(
        question="Explain Python GIL.",
        answer="The GIL is a mutex that protects access to Python objects...",
        skill="python",
    )
    assert result["score"] == 8.5
    assert result["metrics"]["accuracy"] == 9
    assert result["skill_identified"] == "python"


@pytest.mark.asyncio
async def test_react_evaluator_backfills_missing_keys():
    llm = make_llm('Final Answer: {"score": 6}')
    agent = ReActEvaluatorAgent(llm=llm)
    result = await agent.run(question="Q", answer="A", skill="python")
    assert result["score"] == 6
    assert result["metrics"]["accuracy"] == 5  # default
    assert result["skill_category"] == "technical"
    assert result["should_deep_dive"] is False


@pytest.mark.asyncio
async def test_react_evaluator_handles_string_answer():
    llm = make_llm('Final Answer: "score: 7"')
    agent = ReActEvaluatorAgent(llm=llm)
    result = await agent.run(question="Q", answer="A", skill="python")
    # Falls back to defaults since the string doesn't parse to a useful dict
    assert result["score"] == 5.0


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Supervisor Agent
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_react_supervisor_returns_no_action_when_stable():
    llm = make_llm(
        'Final Answer: {"action_type": "no_action", "confidence": 0.95, '
        '"reason": "All signals normal", "reason_category": "no_action"}'
    )
    agent = ReActSupervisorAgent(llm=llm)
    state = make_state({"score_history": [7, 8, 7.5]})
    result = await agent.run(state)
    assert result["supervisor_last_action"]["action_type"] == "no_action"
    assert "supervisor_observations" in result


@pytest.mark.asyncio
async def test_react_supervisor_handles_unknown_action_type():
    """If the LLM emits a bogus action_type, the agent defaults to no_action."""
    llm = make_llm(
        'Final Answer: {"action_type": "self_destruct", "confidence": 0.5, "reason": "x"}'
    )
    agent = ReActSupervisorAgent(llm=llm)
    result = await agent.run(make_state())
    assert result["supervisor_last_action"]["action_type"] == "no_action"


@pytest.mark.asyncio
async def test_react_supervisor_recommends_close_on_completion():
    llm = make_llm(
        'Final Answer: {"action_type": "suggest_close", "confidence": 0.9, '
        '"reason": "All skills covered with high scores", "reason_category": "skill_coverage_complete"}'
    )
    agent = ReActSupervisorAgent(llm=llm)
    state = make_state({"score_history": [9, 9, 9]})
    result = await agent.run(state)
    assert result["supervisor_last_action"]["action_type"] == "suggest_close"
    assert result["supervisor_last_action"]["confidence"] == 0.9


@pytest.mark.asyncio
async def test_react_supervisor_recommends_difficulty_adjustment():
    llm = make_llm(
        'Final Answer: {"action_type": "adjust_difficulty", "confidence": 0.8, '
        '"reason": "Candidate struggling", "reason_category": "performance_declining", '
        '"new_difficulty": "easy"}'
    )
    agent = ReActSupervisorAgent(llm=llm)
    state = make_state({"score_history": [3, 3, 4]})
    result = await agent.run(state)
    action = result["supervisor_last_action"]
    assert action["action_type"] == "adjust_difficulty"
    assert action["payload"]["new_difficulty"] == "easy"


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Research Agent
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_react_research_returns_enrichment_dict():
    llm = make_llm(
        'Final Answer: {"candidate_id": 7, "sources": ["github"], '
        '"skills": ["python", "rust"], "summary": "Strong systems engineer.", "errors": []}'
    )
    agent = ReActResearchAgent(llm=llm)
    result = await agent.run(candidate_id=7, github_username="octocat")
    assert result["candidate_id"] == 7
    assert "github" in result["sources"]
    assert "python" in result["skills"]


@pytest.mark.asyncio
async def test_react_research_backfills_defaults_on_minimal_answer():
    llm = make_llm('Final Answer: {"summary": "limited info"}')
    agent = ReActResearchAgent(llm=llm)
    result = await agent.run(candidate_id=42)
    assert result["candidate_id"] == 42
    assert result["sources"] == []
    assert result["skills"] == []


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph node wrappers — fallback path
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_react_interviewer_node_falls_back_when_disabled(monkeypatch):
    """With VEDRIX_USE_REACT_AGENTS=0, the node calls the original deterministic node."""
    monkeypatch.setenv("VEDRIX_USE_REACT_AGENTS", "0")
    # Reload flag
    import importlib
    import app.services.interview_engine.react_nodes as rn
    importlib.reload(rn)
    # Patch the fallback shim directly (it's bound at module load in react_nodes)
    async def fake_fallback(state):
        return {"next_question": {"id": 1, "question": "fallback Q"}}
    monkeypatch.setattr(rn, "_fallback_interviewer", fake_fallback)
    result = await rn.react_interviewer_node(make_state())
    assert result["next_question"]["question"] == "fallback Q"


@pytest.mark.asyncio
async def test_react_interviewer_node_falls_back_on_hr_takeover(monkeypatch):
    """HR takeover forces the deterministic path even if ReAct is enabled."""
    monkeypatch.setenv("VEDRIX_USE_REACT_AGENTS", "1")
    import importlib
    import app.services.interview_engine.react_nodes as rn
    importlib.reload(rn)
    state = make_state({"supervisor_mode": "hr_takeover"})
    async def fake_fallback(state):
        return {"next_question": {"id": 1, "question": "HR takeover"}}
    monkeypatch.setattr(rn, "_fallback_interviewer", fake_fallback)
    result = await rn.react_interviewer_node(state)
    assert result["next_question"]["question"] == "HR takeover"


@pytest.mark.asyncio
async def test_react_interviewer_node_falls_back_on_qa_pause(monkeypatch):
    monkeypatch.setenv("VEDRIX_USE_REACT_AGENTS", "1")
    import importlib
    import app.services.interview_engine.react_nodes as rn
    importlib.reload(rn)
    state = make_state({"qa_paused": True})
    async def fake_fallback(state):
        return {"next_question": {"id": 1, "question": "paused"}}
    monkeypatch.setattr(rn, "_fallback_interviewer", fake_fallback)
    result = await rn.react_interviewer_node(state)
    assert result["next_question"]["question"] == "paused"


@pytest.mark.asyncio
async def test_react_interviewer_node_falls_back_on_agent_failure(monkeypatch):
    """If the ReAct agent raises, the node swallows it and calls the original."""
    monkeypatch.setenv("VEDRIX_USE_REACT_AGENTS", "1")
    import importlib
    import app.services.interview_engine.react_nodes as rn
    importlib.reload(rn)
    # Force a faulty agent by stubbing the singleton
    class Boom:
        async def run(self, **kw):
            raise RuntimeError("agent broken")

    monkeypatch.setitem(rn._singletons, "interviewer", Boom())

    async def fake_fallback(state):
        return {"next_question": {"id": 1, "question": "recovered"}}
    monkeypatch.setattr(rn, "_fallback_interviewer", fake_fallback)
    result = await rn.react_interviewer_node(make_state())
    assert result["next_question"]["question"] == "recovered"


@pytest.mark.asyncio
async def test_react_evaluator_node_falls_back_when_disabled(monkeypatch):
    monkeypatch.setenv("VEDRIX_USE_REACT_AGENTS", "0")
    import importlib
    import app.services.interview_engine.react_nodes as rn
    importlib.reload(rn)
    async def fake_fallback(state):
        return {"last_evaluation": {"score": 7}}
    monkeypatch.setattr(rn, "_fallback_evaluator", fake_fallback)
    state = make_state({"next_question": {"question": "Q", "skill_tested": "python"},
                        "messages": [{"role": "user", "content": "A"}]})
    result = await rn.react_evaluator_node(state)
    assert result["last_evaluation"]["score"] == 7


@pytest.mark.asyncio
async def test_react_supervisor_node_falls_back_when_disabled(monkeypatch):
    monkeypatch.setenv("VEDRIX_USE_REACT_AGENTS", "0")
    import importlib
    import app.services.interview_engine.react_nodes as rn
    importlib.reload(rn)
    with patch("app.services.interview_engine.supervisor_node.supervisor_node") as mock_node:
        mock_node.return_value = {"supervisor_observations": []}
        result = await rn.react_supervisor_node(make_state())
        assert mock_node.called


@pytest.mark.asyncio
async def test_react_supervisor_node_falls_back_on_agent_failure(monkeypatch):
    monkeypatch.setenv("VEDRIX_USE_REACT_AGENTS", "1")
    import importlib
    import app.services.interview_engine.react_nodes as rn
    importlib.reload(rn)

    class Boom:
        async def run(self, state):
            raise RuntimeError("supervisor broken")

    monkeypatch.setitem(rn._singletons, "supervisor", Boom())

    with patch("app.services.interview_engine.supervisor_node.supervisor_node") as mock_node:
        mock_node.return_value = {"supervisor_observations": [], "supervisor_last_action": None}
        result = await rn.react_supervisor_node(make_state())
        assert mock_node.called


def test_reset_singletons_clears_cache():
    import app.services.interview_engine.react_nodes as rn
    rn._singletons["interviewer"] = "stub"
    rn.reset_singletons()
    assert rn._singletons == {}


# ─────────────────────────────────────────────────────────────────────────────
# ReAct agents are auto-registered with their specialized tools
# ─────────────────────────────────────────────────────────────────────────────

def test_interviewer_registers_synthesize_question_tool():
    from app.services.interview_engine.react import BUILTIN_TOOLS, ToolRegistry

    reg = ToolRegistry()
    agent = ReActInterviewerAgent(llm=make_llm("Final Answer: {}"), registry=reg)
    assert "synthesize_question" in reg.list_names()


def test_evaluator_registers_score_answer_tool():
    from app.services.interview_engine.react import ToolRegistry

    reg = ToolRegistry()
    agent = ReActEvaluatorAgent(llm=make_llm("Final Answer: {}"), registry=reg)
    assert "score_answer" in reg.list_names()


def test_supervisor_uses_builtin_tools():
    from app.services.interview_engine.react import ToolRegistry

    reg = ToolRegistry()
    agent = ReActSupervisorAgent(llm=make_llm("Final Answer: {}"), registry=reg)
    # Supervisor uses the default registry as-is
    assert "emit_alert" in reg.list_names()
    assert "check_bias" in reg.list_names()


def test_research_registers_fetch_tools():
    from app.services.interview_engine.react import ToolRegistry

    reg = ToolRegistry()
    agent = ReActResearchAgent(llm=make_llm("Final Answer: {}"), registry=reg)
    assert "fetch_github" in reg.list_names()
    assert "fetch_linkedin" in reg.list_names()
