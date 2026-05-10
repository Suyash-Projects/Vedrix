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
    "greeting": [
        "Hello! Welcome to your Vedrix AI interview. I'm excited to learn more about you today.",
        "Hi there! Thank you for joining us. Let's get started with a warm-up."
    ],
    "welcome": [
        "Thank you for being here. To begin, could you tell me a bit about yourself and what brings you to this interview?",
        "Great to have you here! Let's start with you giving me a brief overview of your background."
    ],
    "warmup": [
        "Could you walk me through your most recent role and what you enjoyed most about it?",
        "Based on your background, I'd love to hear about a project you're particularly proud of."
    ],
    "easy": [
        "Let me simplify that. Can you explain [topic] in simple terms?",
        "No worries, let's try a different approach. Can you describe a basic concept of [topic]?"
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
    time_limit: int = Field(description="Time limit for this question in seconds")


class EvaluationSchema(BaseModel):
    score: float = Field(description="Overall score between 0.0 and 10.0")
    metrics: Dict[str, float] = Field(description="Scores for accuracy, clarity, depth, communication (0-10)")
    feedback: str = Field(description="Constructive feedback for the candidate")
    topic: str = Field(description="The specific skill or topic being evaluated")
    should_deep_dive: bool = Field(description="Whether to ask a follow-up on this same topic")
    is_coding_challenge: bool = Field(default=False, description="Whether to trigger a coding sandbox")
    needs_easier: bool = Field(default=False, description="Whether the candidate needs an easier question")


# ── Nodes ─────────────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Remove markdown code fences from LLM output before JSON parsing."""
    text = text.strip()
    for fence in ["```json", "```json\n", "```"]:
        if text.startswith(fence):
            text = text[len(fence):]
            if text.endswith("```"):
                text = text[:-3]
            break
    return text.strip()


async def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """Interviewer Agent — generates next adaptive question with proper flow."""
    last_eval = state.get('last_evaluation')
    should_deep_dive = last_eval.get('should_deep_dive', False) if last_eval and isinstance(last_eval, dict) else False
    needs_easier = last_eval.get('needs_easier', False) if last_eval and isinstance(last_eval, dict) else False

    llm = get_adaptive_llm() if should_deep_dive else get_fast_llm()
    parser = JsonOutputParser(pydantic_object=QuestionSchema)

    history = "\n".join(
        f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content'][:500]}"
        for m in state.get('messages', [])
    )

    phase = state['current_phase']
    idx = state['current_question_index']

    # ── PHASE-BASED FLOW ─────────────────────────────────────────────────────
    # Start: greeting (0-1) -> welcome (1-2) -> warmup (2-4) -> technical (4-8) -> stress (8-10) -> behavioral (10-12) -> closing (12+)

    if idx <= 1:
        phase = "greeting"
    elif idx <= 3:
        phase = "welcome"
    elif idx <= 5:
        phase = "warmup"
    elif idx <= 9:
        phase = "technical"
    elif idx <= 11:
        phase = "stress"
    elif idx <= 13:
        phase = "behavioral"
    else:
        phase = "closing"

    # Phase instructions with proper flow
    phase_guides = {
        "greeting": "Start with a warm, welcoming greeting. Introduce yourself and the interview format. Make the candidate feel comfortable.",
        "welcome": "Thank the candidate for joining. Ask an easy opening question about their background and what excites them about this opportunity.",
        "warmup": "Ease into resume discussion. Ask about recent experience and favorite projects. Keep questions simple and encouraging.",
        "technical": "Transition into deeper technical concepts. Reference their prior answers. Increase difficulty gradually.",
        "stress": "Push boundaries with complex scenarios. Test problem-solving under pressure. Be fair but challenging.",
        "behavioral": "Evaluate teamwork, communication, and problem-solving mindset with situational questions.",
        "closing": "Wrap up warmly. Summarize, thank the candidate, and ask if they have final questions."
    }

    phase_guide = phase_guides.get(phase, "Ask a relevant question.")

    # Adaptive instructions
    adaptation = ""
    if last_eval:
        score = last_eval.get('score', 5.0)
        topic = last_eval.get('topic', 'the previous topic')
        if should_deep_dive:
            adaptation = f"\nDEEP DIVE: Candidate showed strength in {topic}. Ask a harder follow-up to test limits."
        elif needs_easier or score < 4.0:
            adaptation = f"\nEASIER: Candidate struggled with {topic}. Ask a SIMPLER clarifying question. Make it easy to answer."
        elif score > 7.0:
            adaptation = f"\nADVANCE: Excellent response on {topic}. Increase difficulty - ask a more complex version."

    # First question special instruction
    is_first = idx == 0
    if is_first:
        phase_guide += " CRITICAL: This is the FIRST question. Start with greeting, then ask them to introduce themselves."

    system_prompt = (
        f"You are an expert technical interviewer for the role of {state['job_role']}.\n\n"
        f"CURRENT PHASE: {phase}\n"
        f"QUESTION NUMBER: {idx + 1}\n"
        f"CURRENT DIFFICULTY: {state['difficulty']}\n"
        f"TOPIC STRENGTHS: {state.get('topic_strengths', {})}\n\n"
        f"HR INSTRUCTIONS: {state.get('hr_instructions', 'None')}\n"
        f"PHASE: {phase_guide}\n"
        f"{adaptation}\n\n"
        f"RESUME CONTEXT:\n{state['resume_text'][:2000]}\n\n"
        f"CONVERSATION HISTORY:\n{history}\n\n"
        "RULES:\n"
        "1. Acknowledge the candidate's previous answer briefly.\n"
        "2. Ask ONE clear question at a time.\n"
        "3. If difficulty is 'easy', make questions simple and concrete.\n"
        "4. If difficulty is 'hard', ask complex multi-part questions.\n"
        "5. Never repeat questions already asked.\n"
        "6. OUTPUT JSON ONLY.\n"
        f"{parser.get_format_instructions()}"
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Generate question {idx + 1} for {phase} phase."),
        ])
        clean_content = _strip_markdown(response.content)
        parsed_q = parser.parse(clean_content)

        # Determine if coding challenge
        is_coding = phase in ['technical', 'stress'] and (idx + 1) % 3 == 0

        return {
            "next_question": parsed_q,
            "messages": [{"role": "assistant", "content": parsed_q['question']}],
            "current_phase": phase,
            "is_coding_mode": is_coding,
            "code_language": "python" if is_coding else None,
        }
    except Exception as e:
        logger.error(f"generate_question_node failed: {e}")
        # Fallback
        fallback_questions = SAFETY_QUESTION_BANK.get(phase, SAFETY_QUESTION_BANK.get("technical"))
        fallback_q = fallback_questions[idx % len(fallback_questions)]

        return {
            "next_question": {
                "id": idx + 1,
                "question": fallback_q,
                "category": phase,
                "difficulty": state['difficulty'],
                "time_limit": 120,
            },
            "messages": [{"role": "assistant", "content": fallback_q}],
            "current_phase": phase,
            "is_coding_mode": False,
            "code_language": None,
        }


async def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """Evaluator Agent — scores the candidate's answer with adaptive feedback."""
    llm = get_strong_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)

    last_question = state.get('next_question', {})
    q_text = last_question.get('question', '') if isinstance(last_question, dict) else ''
    last_answer = state['messages'][-1]['content'] if state.get('messages') else ""

    # Check for low effort/no answer
    low_effort = len(last_answer.strip()) < 10 or last_answer.lower() in ['ok', 'yes', 'no', 'okay', 'uh', 'um']

    if low_effort:
        return {
            "last_evaluation": {
                "score": 3.0,
                "metrics": {"accuracy": 2, "clarity": 4, "depth": 2, "communication": 4},
                "topic": "engagement",
                "should_deep_dive": False,
                "needs_easier": True,
                "feedback": "Candidate gave minimal response. Ask an easier question to encourage engagement."
            },
            "latest_score": 3.0,
            "metrics": {"accuracy": 2, "clarity": 4, "depth": 2, "communication": 4},
        }

    system_prompt = (
        f"You are a senior hiring manager grading a candidate for {state['job_role']}.\n\n"
        "SCORING (0.0–10.0): Accuracy (technical correctness), Clarity (communication), "
        "Depth (senior insight), Communication (professionalism).\n\n"
        f"DIFFICULTY OF QUESTION ASKED: {state.get('difficulty', 'medium')}\n"
        f"HR GUIDANCE: {state.get('hr_instructions', 'None')}\n"
        f"QUESTION: {q_text}\n"
        f"ANSWER: {last_answer}\n\n"
        "Evaluate fairly. If the answer is good, recommend follow-up questions. "
        "If weak, mark needs_easier: true.\n\n"
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
            "last_evaluation": {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": "general",
                "should_deep_dive": False,
                "needs_easier": False,
                "feedback": ""
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
        }


async def evaluate_code_node(state: InterviewState) -> Dict[str, Any]:
    """Code Evaluator Agent — specialized evaluation for code submissions."""
    llm = get_code_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)

    code = state.get('code_snippet', "")
    question = state.get('next_question', {})
    q_text = question.get('question', '') if isinstance(question, dict) else ""

    last_message = state['messages'][-1]['content'] if state.get('messages') else ""
    execution_info = ""
    if "Status:" in last_message and "Output:" in last_message:
        execution_info = f"\nEXECUTION RESULTS:\n{last_message}"

    system_prompt = (
        f"You are a Principal Software Engineer evaluating a code submission for {state['job_role']}.\n\n"
        f"CHALLENGE: {q_text}\n"
        f"CODE:\n{code}\n"
        f"{execution_info}\n\n"
        "CRITERIA: Logic & Correctness, Time/Space Complexity, Readability.\n\n"
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
            "last_evaluation": {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": "coding",
                "should_deep_dive": False,
                "needs_easier": False,
                "feedback": ""
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "is_coding_mode": False,
        }


async def update_memory_node(state: InterviewState) -> Dict[str, Any]:
    """Decision & Memory Agent — adaptive difficulty, phase transitions, completion."""
    try:
        eval_result = state.get('last_evaluation', {})
        topic = eval_result.get('topic', 'general')
        score = eval_result.get('score', 5.0)
        needs_easier = eval_result.get('needs_easier', False)

        # Update topic scores
        new_topic_scores = state.get('topic_scores', {}).copy()
        new_topic_scores[topic] = score

        new_strengths = state.get('topic_strengths', {}).copy()
        if score >= 7.5:
            new_strengths[topic] = "strong"
        elif score >= 4.5:
            new_strengths[topic] = "improving"
        else:
            new_strengths[topic] = "weak"

        # Adaptive difficulty with easier fallback
        diff = state['difficulty']
        if needs_easier:
            diff = "easy"
        elif score > 7.0:
            if diff == "easy":
                diff = "medium"
            elif diff == "medium":
                diff = "hard"
        elif score < 4.0:
            if diff == "hard":
                diff = "medium"
            elif diff == "medium":
                diff = "easy"

        # Phase transitions based on question count
        idx = state['current_question_index'] + 1
        phase = state['current_phase']

        # Auto transition phases
        if phase == "greeting" and idx >= 2:
            phase = "welcome"
        elif phase == "welcome" and idx >= 4:
            phase = "warmup"
        elif phase == "warmup" and idx >= 6:
            phase = "technical"
        elif phase == "technical" and idx >= 10:
            phase = "stress"
        elif phase == "stress" and idx >= 12:
            phase = "behavioral"
        elif phase == "behavioral" and idx >= 14:
            phase = "closing"

        # Complete when closing done with sufficient questions
        is_complete = (
            idx >= state.get('max_questions', 12) and phase in ['closing', 'behavioral'] or
            idx >= 15  # Hard cap at 15 questions
        )

        return {
            "difficulty": diff,
            "topic_strengths": new_strengths,
            "topic_scores": new_topic_scores,
            "current_phase": phase,
            "current_question_index": idx,
            "interview_complete": is_complete,
            "is_coding_mode": False,
        }
    except Exception as e:
        logger.error(f"update_memory_node failed: {e}")
        return {
            "current_question_index": state['current_question_index'] + 1,
            "interview_complete": state['current_question_index'] + 1 >= state.get('max_questions', 12)
        }