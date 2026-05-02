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
    score: float = Field(description="Score between 0.0 and 1.0")
    feedback: str = Field(description="Constructive feedback for the candidate")
    topic: str = Field(description="The specific skill or topic being evaluated")
    should_deep_dive: bool = Field(description="Whether to ask a follow-up on this same topic")

# --- Nodes ---

def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node: Generate Question
    Goal: Create the next interview question based on current state.
    
    Logic:
    - Consults the resume text for context.
    - Adjusts question difficulty based on 'state[difficulty]'.
    - Uses Groq for low-latency response to keep the interview fluid.
    """
    llm = get_fast_llm()
    # ... rest of function
    parser = JsonOutputParser(pydantic_object=QuestionSchema)
    
    # Construct conversation history for context
    history = ""
    for msg in state.get('messages', []):
        role = "Interviewer" if msg['role'] == 'assistant' else "Candidate"
        history += f"{role}: {msg['content']}\n"

    system_prompt = f"""You are an expert technical interviewer for the role of {state['job_role']}.
    Your goal is to conduct an adaptive interview that assesses the candidate's depth of knowledge.
    
    CONTEXT:
    - Candidate Resume: {state['resume_text'][:2000]}
    - Current Difficulty: {state['difficulty']}
    - Topic Strengths/Weaknesses: {state['topic_strengths']}
    - Questions Asked So Far: {state['current_question_index']}
    
    INSTRUCTIONS:
    1. Review the conversation history to avoid repeating questions.
    2. Focus on skills mentioned in the resume that align with the job role.
    3. Generate a {state['difficulty']} level question.
    4. {parser.get_format_instructions()}
    """
    
    human_msg = f"Conversation History:\n{history}\n\nGenerate the next question."
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_msg)
        ])
        
        # Parse the JSON output
        parsed_q = parser.parse(response.content)
        
        return {
            "next_question": parsed_q,
            "messages": [{"role": "assistant", "content": parsed_q['question']}]
        }
    except Exception as e:
        # Fallback logic if LLM fails or returns invalid JSON
        fallback_q = {
            "id": state['current_question_index'] + 1,
            "question": f"Can you tell me about your experience working as a {state['job_role']} and some technical challenges you faced?",
            "category": "technical",
            "difficulty": state['difficulty']
        }
        return {
            "next_question": fallback_q,
            "messages": [{"role": "assistant", "content": fallback_q['question']}]
        }

def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """
    Evaluates the candidate's last answer using a strong model (NVIDIA 405B).
    Provides detailed scoring and logic for the adaptive engine.
    """
    llm = get_strong_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)
    
    last_question = state['next_question']['question']
    last_answer = state['messages'][-1]['content']
    
    system_prompt = f"""You are a senior hiring manager evaluating a candidate's answer for a {state['job_role']} position.
    Grade the answer based on:
    1. Technical accuracy.
    2. Clarity and communication.
    3. Completeness relative to the {state['difficulty']} level.
    
    QUESTION: {last_question}
    CANDIDATE ANSWER: {last_answer}
    
    {parser.get_format_instructions()}
    """
    
    try:
        response = llm.invoke([SystemMessage(content=system_prompt)])
        parsed_eval = parser.parse(response.content)
        return {"last_evaluation": parsed_eval}
    except Exception as e:
        # Graceful fallback evaluation
        fallback_eval = {
            "score": 0.5,
            "feedback": "Answer received and acknowledged.",
            "topic": state['next_question'].get('category', 'general'),
            "should_deep_dive": False
        }
        return {"last_evaluation": fallback_eval}

def update_memory_node(state: InterviewState) -> Dict[str, Any]:
    """
    Updates the topic scores and decides the difficulty of the next round.
    Implements the core adaptive logic: weak -> easier, strong -> harder.
    """
    eval_result = state['last_evaluation']
    topic = eval_result['topic']
    score = eval_result['score']
    
    # 1. Update Topic Strengths
    new_strengths = state.get('topic_strengths', {}).copy()
    if score >= 0.75:
        new_strengths[topic] = "strong"
    elif score >= 0.4:
        new_strengths[topic] = "improving"
    else:
        new_strengths[topic] = "weak"
        
    # 2. Determine Next Difficulty
    current_difficulty = state['difficulty']
    new_difficulty = current_difficulty
    
    if score > 0.8:
        if current_difficulty == "easy": new_difficulty = "medium"
        elif current_difficulty == "medium": new_difficulty = "hard"
    elif score < 0.4:
        if current_difficulty == "hard": new_difficulty = "medium"
        elif current_difficulty == "medium": new_difficulty = "easy"
        
    return {
        "difficulty": new_difficulty,
        "topic_strengths": new_strengths,
        "current_question_index": state['current_question_index'] + 1,
        "interview_complete": state['current_question_index'] + 1 >= state['max_questions']
    }
