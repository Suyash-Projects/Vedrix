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
    completion_reason: Optional[str]  # Why interview ended

    # Phase Management - Natural Flow
    # Phases: "greeting" -> "welcome" -> "warmup" -> "technical" -> "stress" -> "behavioral" -> "closing"
    current_phase: Literal["greeting", "welcome", "warmup", "technical", "stress", "behavioral", "closing"]
    phase_transition: bool  # Flag when transitioning to new phase
    previous_phase: Optional[str]

    # Performance & Memory
    difficulty: Literal["easy", "medium", "hard"]

    # Granular Scoring (0-10 scale)
    latest_score: float
    metrics: Dict[str, float]  # accuracy, clarity, depth, communication
    avg_score: float  # Running average

    # Skill Coverage Tracking - Ensure all skills are covered
    covered_skills: List[str]  # Skills covered in interview
    skills_to_cover: List[str]  # Required skills from job role
    pending_skills: List[str]  # Skills not yet covered
    skill_coverage_percentage: float

    topic_scores: Dict[str, float]
    topic_strengths: Dict[str, str]  # "weak", "strong", "improving"

    # Response Quality Tracking
    total_responses: int
    low_quality_count: int  # Count of low effort answers
    high_quality_count: int  # Count of good answers

    # HR Intervention & Mode
    interviewer_mode: Literal["ai", "human", "suggestion"]
    hr_instructions: Optional[str]

    # Latest evaluation
    last_evaluation: Optional[Dict]

    # Next question to be asked
    next_question: Optional[Dict]

    # Technical Coding Sandbox
    code_snippet: Optional[str]
    code_language: Optional[str]
    is_coding_mode: Optional[bool]

    # Natural follow-up tracking
    follow_up_requested: bool  # When candidate asks for clarification
    previous_topic: Optional[str]  # Track for natural continuation

    # ── AI Advisor Tracking (Phase 1A) ─────────────────────────────────────
    # Advisor monitors interview and suggests to HR when ready to close.
    # HR always retains control — AI never forces termination.
    advisor_ready_to_close: bool  # AI suggests ready to close
    advisor_confidence: Optional[float]  # Confidence in suggestion
    advisor_reason: Optional[str]  # Human-readable reason
    advisor_reason_category: Optional[str]  # Categorized reason
    advisor_notified: bool  # Has interviewer been notified?
    advisor_action_taken: bool  # Has interviewer acted on suggestion?
