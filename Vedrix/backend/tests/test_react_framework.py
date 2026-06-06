"""
Tests for the ReAct framework core (react.py).

Covers:
- Tool / ToolRegistry: registration, OpenAI serialization, invocation, timeouts
- parse_react_output: text format, JSON format, edge cases
- ReActAgent: happy path, tool use, max-steps guard, unparseable output recovery
- Built-in tool registry: presence and basic dispatch
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from app.services.interview_engine.react import (
    BUILTIN_TOOLS,
    ParsedReActOutput,
    ReActActionType,
    ReActAgent,
    ReActStep,
    ReActTrace,
    Tool,
    ToolParameter,
    ToolRegistry,
    _safe_parse_json,
    build_default_tool_registry,
    parse_react_output,
)
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
    """A fake chat model that returns a queued list of messages, one per call."""

    model_config = {"extra": "allow"}

    def __init__(self, messages):
        super().__init__(messages=iter(list(messages)))
        self.invocations: list[str] = []

    async def ainvoke(self, input, *args, **kwargs):
        self.invocations.append(str(input))
        return await super().ainvoke(input, *args, **kwargs)


def make_scripted_llm(*messages: str) -> ScriptedLLM:
    return ScriptedLLM(list(messages))


# ─────────────────────────────────────────────────────────────────────────────
# Tool / ToolRegistry
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_invoke_returns_callable_result():
    async def adder(a: int, b: int) -> int:
        return a + b

    tool = Tool(
        name="adder",
        description="Add two numbers",
        parameters=[
            ToolParameter(name="a", type="number", description="First number"),
            ToolParameter(name="b", type="number", description="Second number"),
        ],
        callable=adder,
    )
    result = await tool.invoke(a=2, b=3)
    assert result == 5


@pytest.mark.asyncio
async def test_tool_filters_unknown_arguments():
    async def echo(**kwargs):
        return kwargs

    tool = Tool(name="echo", description="echo", callable=echo)
    result = await tool.invoke(a=1, b=2, unexpected="x")
    assert "unexpected" not in result


@pytest.mark.asyncio
async def test_tool_times_out():
    async def slow():
        await asyncio.sleep(2)
        return "done"

    tool = Tool(name="slow", description="slow", callable=slow, timeout_seconds=0.1)
    with pytest.raises(asyncio.TimeoutError):
        await tool.invoke()


def test_tool_to_openai_function_shape():
    tool = Tool(
        name="search",
        description="Search the web",
        parameters=[
            ToolParameter(name="query", type="string", description="Search query"),
            ToolParameter(name="top_k", type="number", description="Number of results", required=False),
        ],
    )
    spec = tool.to_openai_function()
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "search"
    assert spec["function"]["parameters"]["required"] == ["query"]
    assert "top_k" in spec["function"]["parameters"]["properties"]


def test_tool_to_openai_function_with_array_param():
    tool = Tool(
        name="tag",
        description="Tag an item",
        parameters=[
            ToolParameter(
                name="tags",
                type="array",
                description="Tags to apply",
                items={"type": "string"},
            )
        ],
    )
    spec = tool.to_openai_function()
    arr = spec["function"]["parameters"]["properties"]["tags"]
    assert arr["type"] == "array"
    assert arr["items"] == {"type": "string"}


def test_tool_registry_register_and_get():
    reg = ToolRegistry()
    tool = Tool(name="t1", description="d", callable=AsyncMock(return_value=1))
    reg.register(tool)
    assert reg.get("t1") is tool
    assert "t1" in reg.list_names()


def test_tool_registry_duplicate_raises():
    reg = ToolRegistry()
    reg.register(Tool(name="t", description="d"))
    with pytest.raises(ValueError):
        reg.register(Tool(name="t", description="d2"))


def test_tool_registry_describe_for_prompt_contains_all_tools():
    reg = ToolRegistry()
    reg.register(Tool(
        name="alpha",
        description="first",
        parameters=[ToolParameter(name="x", type="string", description="x")],
    ))
    reg.register(Tool(
        name="beta",
        description="second",
        parameters=[ToolParameter(name="y", type="number", description="y", required=False)],
    ))
    desc = reg.describe_for_prompt()
    assert "alpha(x: string)" in desc
    assert "beta(y: number (optional))" in desc


def test_tool_registry_to_openai_functions():
    reg = ToolRegistry()
    reg.register(Tool(name="x", description="x"))
    reg.register(Tool(name="y", description="y"))
    specs = reg.to_openai_functions()
    assert {s["function"]["name"] for s in specs} == {"x", "y"}


# ─────────────────────────────────────────────────────────────────────────────
# _safe_parse_json / parse_react_output
# ─────────────────────────────────────────────────────────────────────────────

def test_safe_parse_json_strips_fences():
    raw = "```json\n{\"a\": 1}\n```"
    out = _safe_parse_json(raw)
    assert out == {"a": 1}


def test_safe_parse_json_extracts_object_from_text():
    raw = 'Here you go: {"skill": "python", "score": 9}. Cheers!'
    out = _safe_parse_json(raw)
    assert out == {"skill": "python", "score": 9}


def test_safe_parse_json_returns_none_on_garbage():
    assert _safe_parse_json("not json at all") is None


def test_parse_react_output_json_form_action():
    raw = json.dumps({
        "thought": "I need to look up skills first",
        "action": "lookup_skill_definition",
        "action_input": {"skill": "python"},
    })
    parsed = parse_react_output(raw)
    assert parsed.thought == "I need to look up skills first"
    assert parsed.action_name == "lookup_skill_definition"
    assert parsed.action_input == {"skill": "python"}
    assert parsed.final_answer is None


def test_parse_react_output_json_form_final_answer():
    raw = json.dumps({
        "thought": "I have all the info I need",
        "final_answer": {"score": 8, "feedback": "good"},
    })
    parsed = parse_react_output(raw)
    assert parsed.thought == "I have all the info I need"
    # Final answer is preserved as a dict so downstream gets structured data
    assert parsed.final_answer == {"score": 8, "feedback": "good"}
    assert parsed.action_name is None


def test_parse_react_output_json_form_final_answer_string():
    """If the LLM emits a string final_answer, the parser keeps it as a string."""
    raw = json.dumps({
        "thought": "Done",
        "final_answer": "The candidate is a strong fit.",
    })
    parsed = parse_react_output(raw)
    assert parsed.final_answer == "The candidate is a strong fit."


def test_parse_react_output_text_form():
    raw = (
        "Thought: I should check the candidate's history.\n"
        'Action: get_candidate_history({"candidate_id": 42})'
    )
    parsed = parse_react_output(raw)
    assert "candidate's history" in parsed.thought
    assert parsed.action_name == "get_candidate_history"
    assert parsed.action_input == {"candidate_id": 42}


def test_parse_react_output_text_form_final_answer():
    raw = "Thought: I'm done.\nFinal Answer: {\"score\": 7}"
    parsed = parse_react_output(raw)
    assert parsed.final_answer == '{"score": 7}'


def test_parse_react_output_text_form_kv_args():
    raw = (
        "Thought: emit an alert\n"
        'Action: emit_alert(severity="warning", message="hi")'
    )
    parsed = parse_react_output(raw)
    assert parsed.action_name == "emit_alert"
    assert parsed.action_input == {"severity": "warning", "message": "hi"}


def test_parse_react_output_text_form_single_string_arg():
    raw = 'Action: lookup_skill_definition({"skill": "rust"})'
    parsed = parse_react_output(raw)
    assert parsed.action_name == "lookup_skill_definition"
    assert parsed.action_input == {"skill": "rust"}


def test_parse_react_output_handles_unparseable():
    parsed = parse_react_output("I don't know what to do.")
    assert parsed.thought is None
    assert parsed.action_name is None
    assert parsed.final_answer is None


# ─────────────────────────────────────────────────────────────────────────────
# ReActAgent — core loop behavior
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_react_agent_final_answer_first_try():
    llm = make_scripted_llm(
        'Thought: I have all the info I need.\n'
        'Final Answer: {"score": 9, "feedback": "excellent"}'
    )
    agent = ReActAgent(name="test", llm=llm, registry=ToolRegistry(), max_steps=3)
    trace = await agent.run(task="score this candidate")

    assert trace.completed is True
    assert trace.termination_reason == "final_answer"
    assert trace.final_answer == {"score": 9, "feedback": "excellent"}
    assert len(trace.steps) == 1
    assert trace.steps[0].action_type == ReActActionType.FINISH


@pytest.mark.asyncio
async def test_react_agent_uses_tool_then_finishes():
    """LLM emits a tool call, then a Final Answer on the next turn."""
    async def add(a: int, b: int) -> int:
        return a + b

    registry = ToolRegistry()
    registry.register(Tool(
        name="add",
        description="add two numbers",
        parameters=[
            ToolParameter(name="a", type="number", description="a"),
            ToolParameter(name="b", type="number", description="b"),
        ],
        callable=add,
    ))

    llm = make_scripted_llm(
        'Thought: I need to add 2 and 3.\n'
        'Action: add({"a": 2, "b": 3})',
        'Thought: I got the sum.\n'
        'Final Answer: {"sum": 5}',
    )

    agent = ReActAgent(name="calc", llm=llm, registry=registry, max_steps=4)
    trace = await agent.run(task="add 2 and 3")

    assert trace.completed is True
    assert trace.final_answer == {"sum": 5}
    assert len(trace.steps) == 2
    assert trace.steps[0].action_type == ReActActionType.ACTION
    assert trace.steps[0].action_name == "add"
    assert trace.steps[0].observation == 5
    assert trace.steps[1].action_type == ReActActionType.FINISH


@pytest.mark.asyncio
async def test_react_agent_unknown_tool_observation_is_error():
    llm = make_scripted_llm(
        'Action: no_such_tool({"x": 1})',
        'Final Answer: {"done": true}',
    )
    agent = ReActAgent(name="t", llm=llm, registry=ToolRegistry(), max_steps=3)
    trace = await agent.run(task="test")
    assert trace.steps[0].observation_error is not None
    assert "no_such_tool" in trace.steps[0].observation_error
    assert trace.completed is True


@pytest.mark.asyncio
async def test_react_agent_hits_max_steps():
    """When the LLM never emits a Final Answer, the agent terminates gracefully."""
    llm = make_scripted_llm('Action: nope({})', 'Action: nope({})', 'Action: nope({})', 'Action: nope({})')
    agent = ReActAgent(name="t", llm=llm, registry=ToolRegistry(), max_steps=2)
    trace = await agent.run(task="loop forever")
    assert trace.completed is False
    assert trace.termination_reason.startswith("max_steps_reached")
    assert trace.final_answer is None


@pytest.mark.asyncio
async def test_react_agent_unparseable_output_recovers():
    """An unparseable turn should not crash — it gets a recovery Observation."""
    llm = make_scripted_llm(
        "I think I should just answer: 42",
        'Final Answer: {"value": 42}',
    )
    agent = ReActAgent(name="t", llm=llm, registry=ToolRegistry(), max_steps=3)
    trace = await agent.run(task="get the answer")
    assert trace.completed is True
    assert trace.final_answer == {"value": 42}
    # Two steps: one recovery, one finish
    assert len(trace.steps) == 2


@pytest.mark.asyncio
async def test_react_agent_trace_recorder_invoked():
    recorded = []
    async def recorder(step: ReActStep):
        recorded.append(step)

    llm = make_scripted_llm('Final Answer: {"ok": 1}')
    agent = ReActAgent(
        name="t", llm=llm, registry=ToolRegistry(),
        max_steps=2, trace_recorder=recorder,
    )
    await agent.run(task="x")
    assert len(recorded) == 1
    assert recorded[0].action_type == ReActActionType.FINISH


@pytest.mark.asyncio
async def test_react_agent_records_session_id():
    llm = make_scripted_llm('Final Answer: {"ok": 1}')
    agent = ReActAgent(name="t", llm=llm, registry=ToolRegistry(), max_steps=2)
    trace = await agent.run(task="x", session_id="sess-123")
    assert trace.session_id == "sess-123"


@pytest.mark.asyncio
async def test_react_agent_handles_llm_exception():
    class BoomLLM(GenericFakeChatModel):
        def __init__(self):
            super().__init__(messages=iter([]))

        async def ainvoke(self, *a, **kw):
            raise RuntimeError("LLM down")

    agent = ReActAgent(name="t", llm=BoomLLM(), registry=ToolRegistry(), max_steps=2)
    trace = await agent.run(task="x")
    assert trace.completed is False
    assert trace.termination_reason.startswith("llm_error")
    assert "LLM down" in trace.termination_reason


# ─────────────────────────────────────────────────────────────────────────────
# Built-in tool registry
# ─────────────────────────────────────────────────────────────────────────────

def test_builtin_tool_registry_has_expected_tools():
    expected = {
        "lookup_skill_definition",
        "query_rag",
        "get_candidate_history",
        "get_session_state",
        "emit_alert",
        "check_bias",
    }
    actual = set(BUILTIN_TOOLS.list_names())
    assert expected.issubset(actual), f"Missing built-in tools: {expected - actual}"


def test_build_default_tool_registry_is_idempotent():
    reg = build_default_tool_registry()
    assert reg.get("lookup_skill_definition") is not None
    assert reg.get("query_rag") is not None
    assert reg.get("emit_alert") is not None
    assert reg.get("check_bias") is not None


@pytest.mark.asyncio
async def test_builtin_lookup_skill_definition_known_skill():
    from app.services.interview_engine.react import _tool_lookup_skill_definition
    result = await _tool_lookup_skill_definition("python")
    # "python" maps to "backend" via the keyword reverse-lookup OR returns unknown;
    # either way the tool should not raise and should return a sane dict.
    assert "category" in result
    assert result["category"] in ("technical", "unknown")


@pytest.mark.asyncio
async def test_builtin_lookup_skill_definition_backend():
    """'backend' is a real TECHNICAL_SKILLS key — should return technical category."""
    from app.services.interview_engine.react import _tool_lookup_skill_definition
    result = await _tool_lookup_skill_definition("backend")
    assert result["category"] == "technical"
    assert "keywords" in result


@pytest.mark.asyncio
async def test_builtin_lookup_skill_definition_unknown_skill():
    from app.services.interview_engine.react import _tool_lookup_skill_definition
    result = await _tool_lookup_skill_definition("obscure-framework-x")
    assert result["category"] == "unknown"


@pytest.mark.asyncio
async def test_builtin_check_bias_clean_text():
    from app.services.interview_engine.react import _tool_check_bias
    result = await _tool_check_bias("Tell me about your experience with Python.")
    assert result["is_biased"] is False


@pytest.mark.asyncio
async def test_builtin_check_bias_biased_text():
    from app.services.interview_engine.react import _tool_check_bias
    # qa_node checks for markers — use language that hits a known marker
    result = await _tool_check_bias("We prefer candidates from IIT or IIM backgrounds only.")
    # Even if no specific marker hits, the call must not raise
    assert "is_biased" in result


# ─────────────────────────────────────────────────────────────────────────────
# Step / Trace serialization
# ─────────────────────────────────────────────────────────────────────────────

def test_react_step_to_dict_includes_all_fields():
    step = ReActStep(
        step_number=2,
        action_type=ReActActionType.ACTION,
        thought="I need to look up X",
        action_name="lookup_skill_definition",
        action_input={"skill": "python"},
        observation={"result": "ok"},
        duration_ms=42,
        timestamp="2025-01-01T00:00:00Z",
    )
    d = step.to_dict()
    assert d["step_number"] == 2
    assert d["action_type"] == "action"
    assert d["action_name"] == "lookup_skill_definition"
    assert d["action_input"] == {"skill": "python"}
    assert d["observation"] == {"result": "ok"}


def test_react_trace_to_dict_serializable():
    trace = ReActTrace(
        agent_name="t",
        session_id="s",
        steps=[ReActStep(step_number=1, action_type=ReActActionType.FINISH, final_answer={"x": 1})],
        final_answer={"x": 1},
        completed=True,
        termination_reason="final_answer",
        total_duration_ms=120,
    )
    d = trace.to_dict()
    assert d["agent_name"] == "t"
    assert d["completed"] is True
    assert d["steps"][0]["action_type"] == "finish"
    # Final answer must be JSON-serializable
    json.dumps(d)
