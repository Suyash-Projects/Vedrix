import json
from typing import Dict, Any
from .state import InterviewState
from .providers import get_fast_llm, get_strong_llm

def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """Node to generate the next interview question based on resume and difficulty."""
    llm = get_fast_llm()
    
    # Logic to generate question using state['resume_text'], state['difficulty'], state['topic_strengths']
    # For now, a mock prompt logic
    prompt = f"""You are a professional interviewer for {state['job_role']}.
    Difficulty Level: {state['difficulty']}
    Candidate Resume: {state['resume_text'][:1000]}...
    Topic Strengths: {state['topic_strengths']}
    
    Generate the next technical/behavioral question. 
    Return as JSON: {{"id": {state['current_question_index']+1}, "question": "...", "category": "..."}}
    """
    
    # In a real implementation, we'd use a structured output parser
    # Mocking the response for now
    next_q = {
        "id": state['current_question_index'] + 1,
        "question": f"Based on your resume, can you explain your experience with a {state['difficulty']} level problem in {state['job_role']}?",
        "category": "technical"
    }
    
    return {
        "next_question": next_q,
        "messages": [{"role": "assistant", "content": next_q['question']}]
    }

def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """Node to evaluate the user's last answer."""
    llm = get_strong_llm()
    
    last_user_message = state['messages'][-1]['content']
    last_question = state['next_question']['question']
    
    # Logic to evaluate answer
    # Mocking evaluation
    evaluation = {
        "score": 0.8 if len(last_user_message) > 20 else 0.4,
        "feedback": "Good depth" if len(last_user_message) > 20 else "Too brief",
        "topic": state['next_question']['category']
    }
    
    return {"last_evaluation": evaluation}

def update_memory_node(state: InterviewState) -> Dict[str, Any]:
    """Node to update topic strengths and decide difficulty for next round."""
    eval_result = state['last_evaluation']
    score = eval_result['score']
    
    new_difficulty = state['difficulty']
    new_strengths = state['topic_strengths'].copy()
    
    # Logic: weak -> easier, strong -> harder
    if score > 0.7:
        new_strengths[eval_result['topic']] = "strong"
        if state['difficulty'] == "easy": new_difficulty = "medium"
        elif state['difficulty'] == "medium": new_difficulty = "hard"
    else:
        new_strengths[eval_result['topic']] = "weak"
        if state['difficulty'] == "hard": new_difficulty = "medium"
        elif state['difficulty'] == "medium": new_difficulty = "easy"
        
    return {
        "difficulty": new_difficulty,
        "topic_strengths": new_strengths,
        "current_question_index": state['current_question_index'] + 1
    }
