"""
ReAct (Reasoning + Acting) Agent Framework for Vedrix.

A proper ReAct implementation following the paper:
  "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022)

Each agent alternates between:
  1. THOUGHT  — what is the next logical step? What tool do I need?
  2. ACTION   — invoke a registered tool by name with structured arguments
  3. OBSERVATION — receive the tool's output
  4. repeat until the agent emits FINISH with a final answer

This module is LLM-agnostic — it works with any BaseChatModel that supports
JSON / structured output, including the local Groq / NVIDIA / OpenRouter
chains configured in model_router.py.

Public surface
--------------
- `Tool`           : A single tool the agent can invoke (name, description, schema, callable)
- `ToolRegistry`   : Holds a name → Tool mapping and exposes to the LLM as JSON
- `ReActStep`      : One Thought/Action/Observation cycle
- `ReActTrace`     : Full transcript of an agent run
- `ReActAgent`     : The ReAct loop itself
- `BUILTIN_TOOLS`  : Pre-built tools for skill lookup, RAG, memory, etc.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Tool definition
# ─────────────────────────────────────────────────────────────────────────────

class ToolParameter(BaseModel):
    """A single named parameter a tool accepts."""
    name: str
    type: str = "string"            # "string" | "number" | "boolean" | "array" | "object"
    description: str
    required: bool = True
    items: Optional[Dict[str, Any]] = None  # for arrays: {type: "string"}


class Tool(BaseModel):
    """A named tool the ReAct agent can invoke."""
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    # The async callable. Stored separately from the schema so the model
    # can be JSON-serialized without carrying the function.
    callable: Optional[Callable[..., Awaitable[Any]]] = Field(default=None, exclude=True)
    # Optional per-tool timeout in seconds
    timeout_seconds: float = 10.0

    def to_openai_function(self) -> Dict[str, Any]:
        """Render this tool in OpenAI function-calling JSON format."""
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for p in self.parameters:
            prop: Dict[str, Any] = {"description": p.description}
            if p.type == "array":
                prop["type"] = "array"
                if p.items:
                    prop["items"] = p.items
                else:
                    prop["items"] = {"type": "string"}
            else:
                prop["type"] = p.type
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    async def invoke(self, **kwargs: Any) -> Any:
        """Run the tool with a timeout. Returns the tool's output (any JSON-safe value).

        Unknown kwargs are silently dropped so a misbehaving agent cannot crash
        the tool with extra arguments.
        """
        if self.callable is None:
            raise RuntimeError(f"Tool '{self.name}' has no callable attached")

        valid_keys = {p.name for p in self.parameters}
        clean_args = {k: v for k, v in kwargs.items() if k in valid_keys}

        async def _run() -> Any:
            return await self.callable(**clean_args)

        return await asyncio.wait_for(_run(), timeout=self.timeout_seconds)


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────────────────────────────────────

class ToolRegistry:
    """A name → Tool mapping. Tools are registered once and shared across agents."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)
        return tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_names(self) -> List[str]:
        return sorted(self._tools.keys())

    def describe_for_prompt(self) -> str:
        """Plain-text description of every tool, for the LLM system prompt."""
        if not self._tools:
            return "(no tools available)"
        lines = []
        for tool in self._tools.values():
            params_str = ", ".join(
                f"{p.name}: {p.type}" + ("" if p.required else " (optional)")
                for p in tool.parameters
            )
            lines.append(f"- {tool.name}({params_str}): {tool.description}")
        return "\n".join(lines)

    def to_openai_functions(self) -> List[Dict[str, Any]]:
        return [t.to_openai_function() for t in self._tools.values()]


# ─────────────────────────────────────────────────────────────────────────────
# ReAct step / trace data classes
# ─────────────────────────────────────────────────────────────────────────────

class ReActActionType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINISH = "finish"


@dataclass
class ReActStep:
    """A single Thought / Action / Observation / Finish step."""
    step_number: int
    action_type: ReActActionType
    thought: Optional[str] = None
    action_name: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[Any] = None
    observation_error: Optional[str] = None
    final_answer: Optional[Any] = None
    duration_ms: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "action_type": self.action_type.value,
            "thought": self.thought,
            "action_name": self.action_name,
            "action_input": self.action_input,
            "observation": self.observation,
            "observation_error": self.observation_error,
            "final_answer": self.final_answer,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class ReActTrace:
    """Complete trace of a ReAct agent run."""
    agent_name: str
    session_id: Optional[str] = None
    steps: List[ReActStep] = field(default_factory=list)
    final_answer: Optional[Any] = None
    total_duration_ms: int = 0
    completed: bool = False
    termination_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "total_duration_ms": self.total_duration_ms,
            "completed": self.completed,
            "termination_reason": self.termination_reason,
        }


# ─────────────────────────────────────────────────────────────────────────────
# LLM response parser
# ─────────────────────────────────────────────────────────────────────────────

THOUGHT_PATTERN = re.compile(r"Thought\s*\d*\s*:\s*(.+?)(?=\n\s*(?:Action\s*\d*\s*:|Final Answer\s*:|$))", re.IGNORECASE | re.DOTALL)
ACTION_NAME_PATTERN = re.compile(r"Action\s*\d*\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)
FINAL_ANSWER_PATTERN = re.compile(r"Final Answer\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)


def _extract_action_args(action_line: str) -> str:
    """Given a matched action line like
        'Action: tool_name({"a": 1, "b": [2,3]})'
    return the substring inside the outer parens — handling one level of
    nested parens/braces/brackets so JSON objects and lists parse correctly.
    """
    open_idx = -1
    open_char = ""
    for i, ch in enumerate(action_line):
        if ch in "([{":
            open_idx = i
            open_char = ch
            break
    if open_idx < 0:
        return ""

    close_char = {"(": ")", "[": "]", "{": "}"}[open_char]
    depth = 0
    in_str = False
    str_q = ""
    for j in range(open_idx, len(action_line)):
        ch = action_line[j]
        if in_str:
            if ch == "\\" and j + 1 < len(action_line):
                # skip escaped char
                j += 1
                continue
            if ch == str_q:
                in_str = False
            continue
        if ch in ("'", '"'):
            in_str = True
            str_q = ch
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return action_line[open_idx + 1 : j]
    return action_line[open_idx + 1 :]


@dataclass
class ParsedReActOutput:
    thought: Optional[str] = None
    action_name: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    final_answer: Optional[str] = None
    raw: str = ""


def _merge_text_action(out: ParsedReActOutput, text: str) -> None:
    """Try to recover an `Action: name({...})` from the surrounding text and
    merge it into `out` in place. Mutates `out`."""
    m_action = ACTION_NAME_PATTERN.search(text)
    if not m_action:
        return
    out.action_name = m_action.group(1).strip()
    arg_text = _extract_action_args(text[m_action.end():]).strip()
    as_json = _safe_parse_json(arg_text)
    if isinstance(as_json, dict):
        out.action_input = as_json
    elif "=" in arg_text and not arg_text.startswith("{"):
        try:
            kv: Dict[str, Any] = {}
            for piece in re.split(r",\s*(?=[a-zA-Z_])", arg_text):
                if "=" in piece:
                    k, v = piece.split("=", 1)
                    kv[k.strip()] = v.strip().strip('"').strip("'")
            if kv:
                out.action_input = kv
        except Exception:
            out.action_input = {"input": arg_text}
    else:
        out.action_input = {"input": arg_text}


def _safe_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Parse a JSON object from inside a string, tolerating surrounding text."""
    text = text.strip()
    if text.startswith("```"):
        # strip code fences
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # try to locate the first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def parse_react_output(text: str) -> ParsedReActOutput:
    """
    Parse a ReAct LLM response.

    The canonical format is:
        Thought: <reasoning>
        Action: tool_name({"key": "value"})
        ...
        Final Answer: <answer>

    We also accept JSON-only outputs of shape:
        {"thought": "...", "action": "tool_name", "action_input": {...}}
        {"final_answer": "..."}
    """
    out = ParsedReActOutput(raw=text)

    # Try JSON-first
    as_json = _safe_parse_json(text)
    if isinstance(as_json, dict):
        out.thought = as_json.get("thought")
        out.action_name = as_json.get("action")
        out.action_input = as_json.get("action_input") or as_json.get("action_input_json")
        if as_json.get("final_answer") is not None:
            fa = as_json.get("final_answer")
            # Keep structured answers as structured data, strings as strings
            out.final_answer = fa
        # If the JSON didn't carry a thought, look for one in the surrounding text
        # (LLMs often emit "Thought: ...\nAction: {...}" mixed-style).
        if not out.thought:
            m = THOUGHT_PATTERN.search(text)
            if m:
                out.thought = m.group(1).strip()
        # Likewise, if the JSON didn't carry an action (e.g. the JSON we extracted
        # was only the action_input payload), try to recover the action name from
        # the surrounding text using the text-style parser's helpers below.
        if not out.action_name and not out.final_answer:
            _merge_text_action(out, text)
        # And if no final_answer was found, scan the text for `Final Answer: ...`
        if not out.final_answer:
            m_fa = FINAL_ANSWER_PATTERN.search(text)
            if m_fa:
                out.final_answer = m_fa.group(1).strip()
        return out

    # Fallback: text-style parsing
    m_final = FINAL_ANSWER_PATTERN.search(text)
    if m_final:
        out.final_answer = m_final.group(1).strip()
        # also capture any thought that came before
        m_thought = THOUGHT_PATTERN.search(text)
        if m_thought:
            out.thought = m_thought.group(1).strip()
        return out

    m_thought = THOUGHT_PATTERN.search(text)
    if m_thought:
        out.thought = m_thought.group(1).strip()

    _merge_text_action(out, text)

    return out


# ─────────────────────────────────────────────────────────────────────────────
# The ReAct agent loop
# ─────────────────────────────────────────────────────────────────────────────

REACT_SYSTEM_PROMPT = """You are {agent_name}, an autonomous AI agent that solves problems by reasoning and acting on tools.

You must ALWAYS follow this exact format — no deviations:

Thought: <one short paragraph explaining what you know, what you still need, and which tool (if any) to call next>
Action: tool_name({{"param1": "value1", "param2": "value2"}})
OR
Final Answer: <your final answer in the same JSON shape the caller expects>

Rules:
1. Begin every turn with "Thought:".
2. If you need more information, call exactly ONE tool with a single Action line.
3. After each Observation, write another "Thought:" describing what you learned and what to do next.
4. When you have enough information to answer, output "Final Answer: ..." with the final result.
5. Do not call a tool you have not been told about. Do not invent parameter names.
6. Prefer simple, focused tool calls over chaining many.
7. Maximum {max_steps} steps — at that point you MUST emit a Final Answer.
8. Output ONLY valid JSON-style tool calls (double quotes, no trailing commas).

Available tools:
{tool_descriptions}

User task:
{task}
"""


class ReActAgent:
    """
    A proper ReAct agent: Thought → Action → Observation → ... → Final Answer.

    Usage
    -----
    >>> registry = ToolRegistry()
    >>> registry.register(my_tool)
    >>> agent = ReActAgent(name="interviewer", llm=my_llm, registry=registry)
    >>> trace = await agent.run(task="Generate a Python question for backend role")
    >>> print(trace.final_answer)
    """

    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        registry: ToolRegistry,
        max_steps: int = 6,
        system_prompt: Optional[str] = None,
        trace_recorder: Optional[Callable[[ReActStep], Awaitable[None]]] = None,
    ) -> None:
        self.name = name
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps
        self.system_prompt_override = system_prompt
        self._trace_recorder = trace_recorder

    def _build_system_prompt(self, task: str) -> str:
        if self.system_prompt_override:
            base = self.system_prompt_override
        else:
            base = REACT_SYSTEM_PROMPT
        # Use string replacement instead of str.format so that literal '{' and '}'
        # characters in user-supplied prompts (e.g. JSON examples) do not collide
        # with our placeholders.
        return (
            base
            .replace("{agent_name}", self.name)
            .replace("{max_steps}", str(self.max_steps))
            .replace("{tool_descriptions}", self.registry.describe_for_prompt())
            .replace("{task}", task)
        )

    async def _record_step(self, step: ReActStep) -> None:
        if self._trace_recorder is not None:
            try:
                await self._trace_recorder(step)
            except Exception as e:  # pragma: no cover - observability must not break the agent
                logger.warning("[%s] trace recorder failed: %s", self.name, e)

    async def _invoke_tool(self, name: str, args: Dict[str, Any]) -> tuple[Any, Optional[str]]:
        tool = self.registry.get(name)
        if tool is None:
            return None, f"Unknown tool: '{name}'. Available tools: {self.registry.list_names()}"
        if tool.callable is None:
            return None, f"Tool '{name}' has no callable attached"
        # Filter args to the tool's declared parameters
        valid_keys = {p.name for p in tool.parameters}
        clean_args = {k: v for k, v in args.items() if k in valid_keys}
        try:
            result = await tool.invoke(**clean_args)
            return result, None
        except asyncio.TimeoutError:
            return None, f"Tool '{name}' timed out after {tool.timeout_seconds}s"
        except Exception as e:
            logger.exception("[%s] tool %s raised", self.name, name)
            return None, f"Tool '{name}' failed: {type(e).__name__}: {e}"

    async def _llm_step(self, system_prompt: str, history: List[str]) -> str:
        """Call the LLM. History is a list of previous Thought/Action/Observation lines."""
        messages = [SystemMessage(content=system_prompt)]
        if history:
            messages.append(HumanMessage(content="\n".join(history)))
        response = await self.llm.ainvoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        return content

    async def run(
        self,
        task: str,
        session_id: Optional[str] = None,
        max_steps: Optional[int] = None,
    ) -> ReActTrace:
        """
        Execute the ReAct loop for the given task.

        Returns a ReActTrace with all intermediate steps and the final answer.
        """
        max_steps = max_steps or self.max_steps
        trace = ReActTrace(agent_name=self.name, session_id=session_id)
        run_start = time.monotonic()
        history: List[str] = []

        system_prompt = self._build_system_prompt(task)

        for step_num in range(1, max_steps + 1):
            step_start = time.monotonic()
            try:
                raw = await self._llm_step(system_prompt, history)
            except Exception as e:
                logger.error("[%s] LLM call failed: %s", self.name, e)
                trace.termination_reason = f"llm_error: {e}"
                trace.steps.append(ReActStep(
                    step_number=step_num,
                    action_type=ReActActionType.THOUGHT,
                    observation_error=str(e),
                    duration_ms=int((time.monotonic() - step_start) * 1000),
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ))
                break

            parsed = parse_react_output(raw)
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc).isoformat()

            # Final answer?
            if parsed.final_answer is not None and parsed.action_name is None:
                answer = parsed.final_answer
                # Try to parse as JSON so downstream gets a structured answer
                as_json = _safe_parse_json(answer)
                if isinstance(as_json, dict):
                    answer = as_json
                trace.steps.append(ReActStep(
                    step_number=step_num,
                    action_type=ReActActionType.FINISH,
                    thought=parsed.thought,
                    final_answer=answer,
                    duration_ms=int((time.monotonic() - step_start) * 1000),
                    timestamp=ts,
                ))
                trace.final_answer = answer
                trace.completed = True
                trace.termination_reason = "final_answer"
                await self._record_step(trace.steps[-1])
                history.append(f"Thought: {parsed.thought or ''}\nFinal Answer: {answer}")
                break

            # Action?
            if parsed.action_name:
                observation, err = await self._invoke_tool(parsed.action_name or "", parsed.action_input or {})
                obs_text = observation if err is None else f"ERROR: {err}"
                step = ReActStep(
                    step_number=step_num,
                    action_type=ReActActionType.ACTION,
                    thought=parsed.thought,
                    action_name=parsed.action_name,
                    action_input=parsed.action_input,
                    observation=obs_text,
                    observation_error=err,
                    duration_ms=int((time.monotonic() - step_start) * 1000),
                    timestamp=ts,
                )
                trace.steps.append(step)
                await self._record_step(step)

                history.append(
                    f"Thought {step_num}: {parsed.thought or ''}\n"
                    f"Action {step_num}: {parsed.action_name}({json.dumps(parsed.action_input or {}, ensure_ascii=False)})\n"
                    f"Observation {step_num}: {obs_text}"
                )
                continue

            # Neither final answer nor action — could not parse. Inject a recovery.
            logger.warning("[%s] could not parse step %d output: %r", self.name, step_num, raw[:300])
            trace.steps.append(ReActStep(
                step_number=step_num,
                action_type=ReActActionType.THOUGHT,
                thought=parsed.thought or raw[:300],
                observation_error="Could not parse LLM output into Thought/Action/Final Answer",
                duration_ms=int((time.monotonic() - step_start) * 1000),
                timestamp=ts,
            ))
            history.append(
                f"Thought {step_num}: {parsed.thought or 'I need to act or finish.'}\n"
                f"Observation {step_num}: Your last response was not in the expected format. "
                "Please reply with 'Thought: ...' followed by either 'Action: tool_name({...})' "
                "or 'Final Answer: ...'."
            )

        else:
            # Loop exhausted without a Final Answer
            trace.termination_reason = f"max_steps_reached ({max_steps})"

        trace.total_duration_ms = int((time.monotonic() - run_start) * 1000)
        return trace


# ─────────────────────────────────────────────────────────────────────────────
# Built-in tools for the Vedrix interview engine
# ─────────────────────────────────────────────────────────────────────────────

async def _tool_lookup_skill_definition(skill: str) -> Dict[str, Any]:
    """Return the canonical definition of a skill from the static skill registry."""
    from app.services.interview_engine.nodes import TECHNICAL_SKILLS, SOFT_SKILLS, BEHAVIORAL_AREAS
    skill_lower = (skill or "").lower().strip()

    if skill_lower in TECHNICAL_SKILLS:
        return {
            "skill": skill,
            "category": "technical",
            "keywords": TECHNICAL_SKILLS[skill_lower],
            "definition": f"Technical competency in {skill_lower}.",
        }
    for s in SOFT_SKILLS:
        if s in skill_lower or skill_lower in s:
            return {"skill": s, "category": "soft_skill", "definition": f"Soft skill: {s}."}
    for b in BEHAVIORAL_AREAS:
        if b in skill_lower or skill_lower in b:
            return {"skill": b, "category": "behavioral", "definition": f"Behavioral competency: {b}."}
    return {"skill": skill, "category": "unknown", "definition": f"No static definition found for '{skill}'."}


async def _tool_query_rag(query: str, top_k: int = 3) -> Dict[str, Any]:
    """Query the RAG index for candidate background context (resume/GitHub)."""
    try:
        from app.services.rag_service import rag_service
        rag_service._ensure_initialized()
        if not rag_service._initialized:
            return {"hits": [], "note": "RAG service not initialized"}

        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(None, lambda: rag_service.model.encode([query])[0].tolist())
        results = rag_service.collection.query(
            query_embeddings=[embedding],
            n_results=min(int(top_k), 10),
        )
        docs = results.get("documents", [[]])[0] if results.get("documents") else []
        metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
        return {
            "hits": [
                {"text": d[:600], "metadata": m}
                for d, m in zip(docs, metas)
            ]
        }
    except Exception as e:
        return {"hits": [], "error": str(e)}


async def _tool_get_candidate_history(candidate_id: int) -> Dict[str, Any]:
    """Fetch a candidate's longitudinal skill profile from memory."""
    try:
        from app.db.session import async_session
        from app.services.memory_service import memory_service
        async with async_session() as db:
            profile = await memory_service.get_or_create_profile(candidate_id=candidate_id, db=db)
            return profile if isinstance(profile, dict) else {"profile": str(profile)}
    except Exception as e:
        return {"error": f"memory lookup failed: {e}"}


async def _tool_get_session_state(session_id: int) -> Dict[str, Any]:
    """Fetch the current InterviewSession row for read-only inspection."""
    try:
        from app.db.session import async_session
        from sqlmodel import select
        from app.models.interview import InterviewSession
        async with async_session() as db:
            res = await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
            s = res.scalars().first()
            if not s:
                return {"error": f"session {session_id} not found"}
            return {
                "id": s.id,
                "status": s.status,
                "session_type": s.session_type,
                "overall_score": s.overall_score,
                "current_question_index": len(s.questions) if isinstance(s.questions, list) else 0,
                "qa_quality_score": s.qa_quality_score,
                "workflow_state": s.workflow_state,
            }
    except Exception as e:
        return {"error": f"session lookup failed: {e}"}


async def _tool_emit_alert(session_id: int, severity: str, message: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Broadcast an HR alert over WebSocket (best-effort)."""
    try:
        from app.api.v1.endpoints.interview import manager
        await manager.broadcast_to_hr(
            {
                "type": "react_agent_alert",
                "session_id": str(session_id),
                "severity": severity,
                "message": message,
                "payload": payload or {},
            },
            str(session_id),
        )
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "error": str(e)}


async def _tool_check_bias(text: str) -> Dict[str, Any]:
    """Run the deterministic bias check from qa_node on arbitrary text."""
    try:
        from app.services.interview_engine.qa_node import _qa_node_instance
        flag = _qa_node_instance.check_bias(text)
        if flag is None:
            return {"is_biased": False}
        return {
            "is_biased": True,
            "category": flag.category,
            "markers_found": flag.markers_found,
        }
    except Exception as e:
        return {"is_biased": False, "error": str(e)}


def build_default_tool_registry() -> ToolRegistry:
    """Build the canonical ReAct tool registry used across Vedrix agents."""
    reg = ToolRegistry()

    reg.register(Tool(
        name="lookup_skill_definition",
        description="Look up the canonical definition, category (technical/soft/behavioral), "
                    "and keyword list for a given skill name.",
        parameters=[ToolParameter(name="skill", type="string", description="Skill name to look up")],
        callable=_tool_lookup_skill_definition,
    ))

    reg.register(Tool(
        name="query_rag",
        description="Search the candidate's indexed resume / GitHub / LinkedIn corpus "
                    "for the most relevant passages to a natural-language query.",
        parameters=[
            ToolParameter(name="query", type="string", description="Natural-language query"),
            ToolParameter(name="top_k", type="number", description="How many hits to return (1-10)", required=False),
        ],
        callable=_tool_query_rag,
    ))

    reg.register(Tool(
        name="get_candidate_history",
        description="Fetch the candidate's longitudinal skill profile (cumulative scores, "
                    "session count, last interview date) from the memory service.",
        parameters=[ToolParameter(name="candidate_id", type="number", description="Candidate user id")],
        callable=_tool_get_candidate_history,
    ))

    reg.register(Tool(
        name="get_session_state",
        description="Read the current InterviewSession row by id (status, score, QA score, workflow state).",
        parameters=[ToolParameter(name="session_id", type="number", description="Interview session id")],
        callable=_tool_get_session_state,
    ))

    reg.register(Tool(
        name="emit_alert",
        description="Broadcast an alert to the connected HR dashboard over WebSocket.",
        parameters=[
            ToolParameter(name="session_id", type="number", description="Interview session id"),
            ToolParameter(name="severity", type="string", description="info | warning | critical"),
            ToolParameter(name="message", type="string", description="Human-readable alert message"),
            ToolParameter(name="payload", type="object", description="Optional structured data", required=False),
        ],
        callable=_tool_emit_alert,
    ))

    reg.register(Tool(
        name="check_bias",
        description="Run the deterministic bias detector on a piece of text. Returns "
                    "{is_biased: bool, category?, markers_found?}.",
        parameters=[ToolParameter(name="text", type="string", description="Text to scan for bias markers")],
        callable=_tool_check_bias,
    ))

    return reg


# Public alias so callers don't have to know the build function
BUILTIN_TOOLS = build_default_tool_registry()
