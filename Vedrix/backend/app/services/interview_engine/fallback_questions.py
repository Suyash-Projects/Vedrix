"""
Static Fallback Questions for AI Interview Engine.

Used when all AI providers are unavailable.
Questions are contextual based on the job role and interview phase.
"""
import random
from typing import List, Dict, Any

# ── Technical Questions by Topic ──────────────────────────────────────────────

TECHNICAL_QUESTIONS = {
    "python": [
        {
            "question": "Explain the difference between a list and a tuple in Python. When would you use each?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 120,
            "skill_tested": "python",
            "follow_up_topic": "data structures",
        },
        {
            "question": "What are Python decorators? Can you give an example of when you'd use one?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 180,
            "skill_tested": "python",
            "follow_up_topic": "design patterns",
        },
        {
            "question": "How does Python's garbage collection work? Explain reference counting and the generational GC.",
            "category": "technical",
            "difficulty": "hard",
            "time_limit": 240,
            "skill_tested": "python",
            "follow_up_topic": "memory management",
        },
    ],
    "database": [
        {
            "question": "What is the difference between INNER JOIN and LEFT JOIN? Can you give a practical example?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 120,
            "skill_tested": "database",
            "follow_up_topic": "query optimization",
        },
        {
            "question": "Explain database indexing. How does it improve query performance and what are the trade-offs?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 180,
            "skill_tested": "database",
            "follow_up_topic": "performance tuning",
        },
        {
            "question": "What is database normalization? Explain the first three normal forms.",
            "category": "technical",
            "difficulty": "hard",
            "time_limit": 240,
            "skill_tested": "database",
            "follow_up_topic": "schema design",
        },
    ],
    "frontend": [
        {
            "question": "Explain the virtual DOM in React. How does it improve performance?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 120,
            "skill_tested": "frontend",
            "follow_up_topic": "react internals",
        },
        {
            "question": "What is the difference between useState and useReducer? When would you choose one over the other?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 180,
            "skill_tested": "frontend",
            "follow_up_topic": "state management",
        },
    ],
    "backend": [
        {
            "question": "What is the difference between REST and GraphQL? What are the advantages of each?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 120,
            "skill_tested": "backend",
            "follow_up_topic": "api design",
        },
        {
            "question": "Explain middleware in the context of a web framework like FastAPI or Express. How have you used it?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 180,
            "skill_tested": "backend",
            "follow_up_topic": "architecture patterns",
        },
    ],
    "system_design": [
        {
            "question": "How would you design a URL shortening service like bit.ly? Consider scalability and performance.",
            "category": "technical",
            "difficulty": "hard",
            "time_limit": 300,
            "skill_tested": "system_design",
            "follow_up_topic": "distributed systems",
        },
        {
            "question": "Explain the CAP theorem. How does it influence your database choices?",
            "category": "technical",
            "difficulty": "hard",
            "time_limit": 240,
            "skill_tested": "system_design",
            "follow_up_topic": "database selection",
        },
    ],
    "devops": [
        {
            "question": "What is the difference between Docker containers and virtual machines? When would you use each?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 120,
            "skill_tested": "devops",
            "follow_up_topic": "infrastructure",
        },
        {
            "question": "Explain CI/CD pipeline. What tools have you used and what stages would you include?",
            "category": "technical",
            "difficulty": "medium",
            "time_limit": 180,
            "skill_tested": "devops",
            "follow_up_topic": "automation",
        },
    ],
}

# ── Behavioral Questions ──────────────────────────────────────────────────────

BEHAVIORAL_QUESTIONS = [
    {
        "question": "Tell me about a challenging technical problem you solved recently. What was your approach?",
        "category": "behavioral",
        "difficulty": "medium",
        "time_limit": 180,
        "skill_tested": "problem_solving",
        "follow_up_topic": "technical depth",
    },
    {
        "question": "Describe a time when you had to work with a difficult team member. How did you handle it?",
        "category": "behavioral",
        "difficulty": "medium",
        "time_limit": 180,
        "skill_tested": "teamwork",
        "follow_up_topic": "conflict resolution",
    },
    {
        "question": "Tell me about a project where you had to learn a new technology quickly. How did you approach it?",
        "category": "behavioral",
        "difficulty": "medium",
        "time_limit": 180,
        "skill_tested": "adaptability",
        "follow_up_topic": "learning style",
    },
    {
        "question": "Describe a situation where you had to make a technical decision with incomplete information.",
        "category": "behavioral",
        "difficulty": "hard",
        "time_limit": 240,
        "skill_tested": "decision_making",
        "follow_up_topic": "risk management",
    },
]

# ── Fallback Question Generator ───────────────────────────────────────────────

def get_fallback_question(
    job_role: str = "",
    phase: str = "technical",
    covered_skills: List[str] = None,
    question_index: int = 0,
) -> Dict[str, Any]:
    """
    Get a fallback question when AI providers are unavailable.

    Args:
        job_role: The target job role (used for topic matching)
        phase: Current interview phase (technical, behavioral, etc.)
        covered_skills: Skills already tested (to avoid repetition)
        question_index: Current question number (for variety)

    Returns:
        A question dict matching the InterviewState schema.
    """
    covered_skills = covered_skills or []

    if phase == "behavioral":
        # Pick a behavioral question not yet asked
        available = [q for q in BEHAVIORAL_QUESTIONS if q not in covered_skills]
        if not available:
            available = BEHAVIORAL_QUESTIONS
        return random.choice(available)

    # Technical phase — try to match job role to topic
    role_lower = job_role.lower()
    topic_map = {
        "python": "python",
        "django": "python",
        "fastapi": "python",
        "backend": "backend",
        "api": "backend",
        "frontend": "frontend",
        "react": "frontend",
        "database": "database",
        "sql": "database",
        "devops": "devops",
        "docker": "devops",
        "system": "system_design",
        "architect": "system_design",
    }

    # Find matching topic
    matched_topic = None
    for keyword, topic in topic_map.items():
        if keyword in role_lower:
            matched_topic = topic
            break

    if matched_topic and matched_topic in TECHNICAL_QUESTIONS:
        questions = TECHNICAL_QUESTIONS[matched_topic]
        return questions[question_index % len(questions)]

    # Default: pick from any available topic
    all_topics = list(TECHNICAL_QUESTIONS.keys())
    topic = all_topics[question_index % len(all_topics)]
    questions = TECHNICAL_QUESTIONS[topic]
    return questions[question_index % len(questions)]
