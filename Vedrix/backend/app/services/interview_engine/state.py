from typing import List, Dict, Optional, TypedDict, Annotated, Literal
import operator

class InterviewState(TypedDict):
    # Chat history
    messages: Annotated[List[Dict[str, str]], operator.add]
    
    # Context
    resume_text: str
    job_role: str
    
    # Interview Tracking
    current_question_index: int
    max_questions: int
    interview_complete: bool
    
    # NEW: Phase Management
    # Phases: "greeting", "welcome", "warmup", "technical", "stress", "behavioral", "closing"
    current_phase: Literal["greeting", "welcome", "warmup", "technical", "stress", "behavioral", "closing"]
    
    # Performance & Memory
    difficulty: Literal["easy", "medium", "hard"]
    
    # NEW: Granular Scoring (0-10 scale as per product vision)
    # Evaluator Agent metrics
    latest_score: float # 0.0 - 10.0
    metrics: Dict[str, float] # accuracy, clarity, depth, communication
    
    topic_scores: Dict[str, float]
    topic_strengths: Dict[str, str]  # "weak", "strong", "improving"
    
    # NEW: HR Intervention & Mode
    # Modes: "ai" (autonomous), "human" (takeover), "suggestion" (guided)
    interviewer_mode: Literal["ai", "human", "suggestion"]
    hr_instructions: Optional[str] # Background prompts from HR
    
    # Latest evaluation
    last_evaluation: Optional[Dict]
    
    # Next question to be asked
    next_question: Optional[Dict]

    # Technical Coding Sandbox
    code_snippet: Optional[str]
    code_language: Optional[str]
    is_coding_mode: Optional[bool]
