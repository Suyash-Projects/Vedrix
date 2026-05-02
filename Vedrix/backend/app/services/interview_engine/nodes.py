import json
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from .state import InterviewState
from .providers import get_fast_llm, get_strong_llm

# --- Structured Output Schemas ---

class QuestionSchema(BaseModel):
    id: int = Field(description="Sequence number of the question")
    question: str = Field(description="The actual interview question text")
    category: str = Field(description="Category: technical, behavioral, or resume-based")
    difficulty: str = Field(description="The difficulty level targeted")

class EvaluationSchema(BaseModel):
    score: float = Field(description="Overall score between 0.0 and 10.0")
    metrics: Dict[str, float] = Field(description="Scores for accuracy, clarity, depth, and communication (all 0-10)")
    feedback: str = Field(description="Constructive feedback for the candidate")
    topic: str = Field(description="The specific skill or topic being evaluated")
    should_deep_dive: bool = Field(description="Whether to ask a follow-up on this same topic")

# --- Nodes ---

def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node: Interviewer Agent
    Goal: Create the next interview question based on current phase and performance.
    
    Logic:
    - Consults the resume text for context.
    - Tailors tone and question to the current phase (Warmup, Technical, Stress, etc.).
    - Uses Groq for low-latency response.
    """
    llm = get_fast_llm()
    parser = JsonOutputParser(pydantic_object=QuestionSchema)
    
    # Construct conversation history
    history = ""
    for msg in state.get('messages', []):
        role = "Interviewer" if msg['role'] == 'assistant' else "Candidate"
        history += f"{role}: {msg['content']}\n"

    system_prompt = f"""You are an expert technical interviewer for the role of {state['job_role']}.
    Conduct a realistic interview using a professional, slightly strict tone.
    
    CURRENT PHASE: {state['current_phase']}
    CURRENT DIFFICULTY: {state['difficulty']}
    TOPIC STRENGTHS: {state['topic_strengths']}
    
    PHASE GUIDELINES:
    - warmup: Friendly but professional, verify resume experience.
    - technical: Deep dive into core skills mentioned in resume.
    - stress: Ask high-pressure logic or deep architectural questions.
    - behavioral: Evaluate communication and problem-solving mindset.
    
    CONTEXT:
    - Resume: {state['resume_text'][:2000]}
    
    INSTRUCTIONS:
    1. Do not repeat questions.
    2. Adapt based on history.
    3. {parser.get_format_instructions()}
    """
    
    human_msg = f"Conversation History:\n{history}\n\nGenerate the next question for the {state['current_phase']} phase."
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_msg)
        ])
        parsed_q = parser.parse(response.content)
        return {
            "next_question": parsed_q,
            "messages": [{"role": "assistant", "content": parsed_q['question']}]
        }
    except Exception:
        fallback_q = {
            "id": state['current_question_index'] + 1,
            "question": "Can you elaborate more on your most recent project and the technical stack used?",
            "category": "technical",
            "difficulty": state['difficulty']
        }
        return {
            "next_question": fallback_q,
            "messages": [{"role": "assistant", "content": fallback_q['question']}]
        }

def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node: Evaluator Agent
    Goal: Deep analysis of candidate's response using NVIDIA 405B.
    
    Scoring: 0-10 scale across Accuracy, Clarity, Depth, and Communication.
    """
    llm = get_strong_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)
    
    last_question = state['next_question']['question']
    last_answer = state['messages'][-1]['content']
    hr_guidance = state.get('hr_instructions', "None")
    
    system_prompt = f"""You are a senior hiring manager. Grade the candidate's answer for a {state['job_role']} position.
    
    SCORING (0.0 to 10.0):
    - Accuracy: Technical correctness.
    - Clarity: Communication ease.
    - Depth: Senior-level insight.
    - Communication: Professionalism.
    
    HR INTERVENTION GUIDANCE: {hr_guidance}
    
    QUESTION: {last_question}
    ANSWER: {last_answer}
    
    {parser.get_format_instructions()}
    """
    
    try:
        response = llm.invoke([SystemMessage(content=system_prompt)])
        parsed_eval = parser.parse(response.content)
        return {
            "last_evaluation": parsed_eval,
            "latest_score": parsed_eval['score'],
            "metrics": parsed_eval['metrics']
        }
    except Exception:
        return {
            "last_evaluation": {"score": 5.0, "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5}},
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5}
        }

def update_memory_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node: Decision & Memory Agent
    Goal: Update state, manage adaptive difficulty, and handle phase transitions.
    """
    eval_result = state['last_evaluation']
    topic = eval_result.get('topic', 'general')
    score = eval_result.get('score', 5.0)
    
    # 1. Update Memory
    new_strengths = state.get('topic_strengths', {}).copy()
    if score >= 7.5: new_strengths[topic] = "strong"
    elif score >= 4.5: new_strengths[topic] = "improving"
    else: new_strengths[topic] = "weak"
        
    # 2. Adaptive Difficulty Logic
    current_diff = state['difficulty']
    new_diff = current_diff
    if score > 7.0:
        if current_diff == "easy": new_diff = "medium"
        elif current_diff == "medium": new_diff = "hard"
    elif score < 4.0:
        if current_diff == "hard": new_diff = "medium"
        elif current_diff == "medium": new_diff = "easy"
        
    # 3. Phase Transitions
    curr_phase = state['current_phase']
    new_phase = curr_phase
    idx = state['current_question_index'] + 1
    
    if curr_phase == "warmup" and idx >= 2: new_phase = "technical"
    elif curr_phase == "technical" and idx >= 6:
        new_phase = "stress" if score > 8.0 else "behavioral"
    elif curr_phase == "stress" and idx >= 9: new_phase = "behavioral"
    elif curr_phase == "behavioral" and idx >= 11: new_phase = "closing"
        
    return {
        "difficulty": new_diff,
        "topic_strengths": new_strengths,
        "current_phase": new_phase,
        "current_question_index": idx,
        "interview_complete": idx >= state['max_questions'] or new_phase == "closing"
    }
