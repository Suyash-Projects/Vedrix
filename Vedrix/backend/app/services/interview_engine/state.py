from typing import List, Dict, Optional, TypedDict, Annotated
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
    
    # Performance & Memory
    difficulty: str  # "easy", "medium", "hard"
    topic_scores: Dict[str, float]
    topic_strengths: Dict[str, str]  # "weak", "strong", "improving"
    
    # Latest evaluation
    last_evaluation: Optional[Dict]
    
    # Next question to be asked
    next_question: Optional[Dict]
