import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from .state import InterviewState
from .providers import get_fast_llm, get_strong_llm, get_adaptive_llm, get_code_llm

logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

SAFETY_QUESTION_BANK = {
    "warmup": [
        "Welcome! Could you start by walking me through your background and the most recent role on your resume?",
        "Hello! I've reviewed your resume. Could you highlight a project you are particularly proud of?"
    ],
    "technical": [
        "Can you describe a challenging technical problem you solved recently and how you approached it?",
        "How do you ensure the code you write is scalable and maintainable?",
        "Could you explain the architecture of the most complex system you've worked on?"
    ],
    "stress": [
        "Tell me about a time when a critical system failed in production. How did you handle the situation?",
        "How do you manage situations where you need to deliver a project but have conflicting requirements from stakeholders?"
    ],
    "behavioral": [
        "Can you share an experience where you had a technical disagreement with a colleague? How was it resolved?",
        "Describe a time you had to learn a completely new technology under a tight deadline."
    ],
    "closing": [
        "We are wrapping up. Based on what we've discussed, what are your key takeaways?",
        "To conclude, how do you see yourself contributing to our team based on your experience?"
    ]
}

class QuestionSchema(BaseModel):
    id: int = Field(description="Sequence number of the question")
    question: str = Field(description="The actual interview question text")
    category: str = Field(description="Category: technical, behavioral, or resume-based")
    difficulty: str = Field(description="The difficulty level targeted")
    time_limit: int = Field(description="Time limit for this question in seconds (e.g. 60, 120, 180)")


class EvaluationSchema(BaseModel):
    score: float = Field(description="Overall score between 0.0 and 10.0")
    metrics: Dict[str, float] = Field(description="Scores for accuracy, clarity, depth, communication (0-10)")
    feedback: str = Field(description="Constructive feedback for the candidate")
    topic: str = Field(description="The specific skill or topic being evaluated")
    should_deep_dive: bool = Field(description="Whether to ask a follow-up on this same topic")
    is_coding_challenge: bool = Field(default=False, description="Whether to trigger a coding sandbox")


# ── Nodes ─────────────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Remove markdown code fences from LLM output before JSON parsing."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    for fence in ["```json", "```json\n", "```"]:
        if text.startswith(fence):
            text = text[len(fence):]
            if text.endswith("```"):
                text = text[:-3]
            break
    return text.strip()


async def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """Interviewer Agent — generates next adaptive question."""
    # Reference Phase 6: Adaptive Follow-ups using specialized model
    last_eval = state.get('last_evaluation')
    should_deep_dive = last_eval.get('should_deep_dive', False) if last_eval and isinstance(last_eval, dict) else False

    llm = get_adaptive_llm() if should_deep_dive else get_fast_llm()
    parser = JsonOutputParser(pydantic_object=QuestionSchema)

    history = "\n".join(
        f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
        for m in state.get('messages', [])
    )

    phase = state['current_phase']
    is_first_question = state['current_question_index'] == 0

    phase_guide = {
        "warmup": "Start with a warm, welcoming greeting if this is the first message. Then ease into resume discussion.",
        "technical": "Transition smoothly from resume into deep technical concepts. Reference prior answers.",
        "stress": "Push boundaries with complex architectural or edge-case logic questions.",
        "behavioral": "Evaluate teamwork, communication, and problem-solving mindset with situational questions.",
        "closing": "Wrap up the interview warmly. Summarize the session, thank the candidate, and ask if they have any final questions for the company.",
    }.get(phase, "Ask a relevant professional question.")

    if is_first_question:
        phase_guide += " CRITICAL INITIALIZATION: You MUST start by welcoming the candidate and asking a specific question about a concrete detail found in their RESUME CONTEXT. Do not ask a generic question."

    # Explicit Adaptation Logic (Reference Workflow A.4)
    adaptation_instruction = ""
    if last_eval:
        score = last_eval.get('score', 5.0)
        topic = last_eval.get('topic', 'the previous topic')
        if should_deep_dive:
            adaptation_instruction = f"\nADAPTATION: The candidate showed good understanding of {topic}. Ask a much more HARDER and GRANULAR follow-up question to test the limits of their knowledge on this specific topic."
        elif score < 4.0:
            adaptation_instruction = f"\nADAPTATION: The candidate struggled with {topic}. Ask a SIMPLER or CLARIFYING question on this topic to help them recover or demonstrate basic competency."

    system_prompt = (
        f"You are an expert technical interviewer for the role of {state['job_role']}.\n\n"
        f"CURRENT PHASE: {phase}\n"
        f"CURRENT DIFFICULTY: {state['difficulty']}\n"
        f"TOPIC STRENGTHS: {state['topic_strengths']}\n\n"
        f"HR INSTRUCTIONS: {state.get('hr_instructions', 'None')}\n"
        f"PHASE INSTRUCTION: {phase_guide}\n"
        f"{adaptation_instruction}\n\n"
        f"RESUME CONTEXT:\n{state['resume_text'][:2000]}\n\n"
        "RULES:\n"
        "1. Acknowledge the candidate's previous answer before asking the next question.\n"
        "2. Never repeat a question already asked.\n"
        "3. OUTPUT JSON ONLY — no markdown, no explanation, just the JSON object.\n"
        f"{parser.get_format_instructions()}"
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Conversation History:\n{history}\n\nGenerate the next question for the {phase} phase. Output JSON only."),
        ])
        # Strip markdown before parsing (LLMs often wrap JSON in ```json ... ```)
        clean_content = _strip_markdown(response.content)
        parsed_q = parser.parse(clean_content)
        is_coding = phase == 'technical' and (state['current_question_index'] + 1) % 3 == 0
        return {
            "next_question": parsed_q,
            "messages": [{"role": "assistant", "content": parsed_q['question']}],
            "is_coding_mode": is_coding,
            "code_language": "python" if is_coding else None,
        }
    except Exception as e:
        logger.error(f"generate_question_node failed: {e}")
        
        # Robust Fallback Mechanism based on phase
        fallback_questions = SAFETY_QUESTION_BANK.get(phase, SAFETY_QUESTION_BANK["technical"])
        idx = state['current_question_index'] + 1
        fallback_q = fallback_questions[(idx - 1) % len(fallback_questions)]
        
        fallback = {
            "id": idx,
            "question": fallback_q,
            "category": phase,
            "difficulty": state['difficulty'],
            "time_limit": 120,
        }
        return {
            "next_question": fallback,
            "messages": [{"role": "assistant", "content": fallback['question']}],
            "is_coding_mode": False,
            "code_language": "python",
        }


async def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """Evaluator Agent — scores the candidate's text/voice answer."""
    llm = get_strong_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)

    last_question = state.get('next_question', {}).get('question') if state.get('next_question') else None
    last_answer = state['messages'][-1]['content'] if state.get('messages') else ""
    
    if not last_question:
        logger.warning("evaluate_answer_node: no last_question in state")

    system_prompt = (
        f"You are a senior hiring manager grading a candidate for {state['job_role']}.\n\n"
        "SCORING (0.0–10.0): Accuracy (technical correctness), Clarity (communication), "
        "Depth (senior insight), Communication (professionalism).\n\n"
        f"HR GUIDANCE: {state.get('hr_instructions', 'None')}\n"
        f"QUESTION: {last_question}\n"
        f"ANSWER: {last_answer}\n\n"
        f"{parser.get_format_instructions()}"
    )

    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        clean_content = _strip_markdown(response.content)
        parsed = parser.parse(clean_content)
        return {
            "last_evaluation": parsed,
            "latest_score": parsed['score'],
            "metrics": parsed['metrics'],
        }
    except Exception as e:
        logger.error(f"evaluate_answer_node failed: {e}")
        return {
            "last_evaluation": {"score": 5.0, "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5}, "topic": "general", "should_deep_dive": False, "feedback": ""},
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
        }


async def evaluate_code_node(state: InterviewState) -> Dict[str, Any]:
    """Code Evaluator Agent — specialized evaluation for code submissions."""
    # Reference Phase 5: GPT class model for technical logic
    llm = get_code_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)

    code = state.get('code_snippet', "")
    question = state.get('next_question', {}).get('question') if state.get('next_question') else None
    
    # Audit #11: Include Judge0 execution results in prompt
    last_message = state['messages'][-1]['content'] if state.get('messages') else ""
    execution_info = ""
    if "Status:" in last_message and "Output:" in last_message:
        execution_info = f"\nJUDGE0 EXECUTION RESULTS:\n{last_message}"

    if not question:
        logger.warning("evaluate_code_node: no question in state")

    system_prompt = (
        f"You are a Principal Software Engineer evaluating a code submission for {state['job_role']}.\n\n"
        f"CHALLENGE: {question}\n"
        f"SUBMITTED CODE:\n{code}\n"
        f"{execution_info}\n\n"
        "CRITERIA: Logic & Correctness (Accuracy), Time/Space Complexity (Depth), Readability (Communication).\n\n"
        f"{parser.get_format_instructions()}"
    )

    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        clean_content = _strip_markdown(response.content)
        parsed = parser.parse(clean_content)
        return {
            "last_evaluation": parsed,
            "latest_score": parsed['score'],
            "metrics": parsed['metrics'],
            "is_coding_mode": False,
        }
    except Exception as e:
        logger.error(f"evaluate_code_node failed: {e}")
        return {
            "last_evaluation": {"score": 5.0, "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5}, "topic": "coding", "should_deep_dive": False, "feedback": ""},
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "is_coding_mode": False,
        }


async def update_memory_node(state: InterviewState) -> Dict[str, Any]:
    """Decision & Memory Agent — updates difficulty, phase, and topic scores."""
    try:
        eval_result = state['last_evaluation']
        topic = eval_result.get('topic', 'general')
        score = eval_result.get('score', 5.0)

        # Update topic strengths (audit #19: also write topic_scores)
        new_strengths = state.get('topic_strengths', {}).copy()
        new_topic_scores = state.get('topic_scores', {}).copy()
        new_topic_scores[topic] = score
        if score >= 7.5:
            new_strengths[topic] = "strong"
        elif score >= 4.5:
            new_strengths[topic] = "improving"
        else:
            new_strengths[topic] = "weak"

        # Adaptive difficulty
        diff = state['difficulty']
        if score > 7.0:
            if diff == "easy": diff = "medium"
            elif diff == "medium": diff = "hard"
        elif score < 4.0:
            if diff == "hard": diff = "medium"
            elif diff == "medium": diff = "easy"

        # Phase transitions
        phase = state['current_phase']
        idx = state['current_question_index'] + 1

        if phase == "warmup" and idx >= 2:
            phase = "technical"
        elif phase == "technical" and idx >= 6:
            phase = "stress" if score > 8.0 else "behavioral"
        elif phase == "stress" and idx >= 9:
            phase = "behavioral"
        elif phase == "behavioral" and idx >= 11:
            phase = "closing"

        # Mark complete when we've finished all question cycles AND have conducted the closing phase
        is_complete = (
            idx >= state['max_questions'] or
            (state['current_phase'] == "closing" and idx >= 11)
        )

        return {
            "difficulty": diff,
            "topic_strengths": new_strengths,
            "topic_scores": new_topic_scores,
            "current_phase": phase,
            "current_question_index": idx,
            "interview_complete": is_complete,
            "is_coding_mode": state.get('is_coding_mode', False),
        }
    except Exception as e:
        logger.error(f"update_memory_node failed: {e}")
        # Return current state to avoid breaking the graph
        return {
            "current_question_index": state['current_question_index'] + 1,
            "interview_complete": state['current_question_index'] + 1 >= state['max_questions']
        }
