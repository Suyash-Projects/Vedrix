import logging
import re
import random
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from .state import InterviewState
from .providers import get_fast_llm, get_strong_llm, get_adaptive_llm, get_code_llm

logger = logging.getLogger(__name__)


# ── SKILL DEFINITIONS ──────────────────────────────────────────────────────────

TECHNICAL_SKILLS = {
    "programming": ["coding", "programming", "code", "developer", "software"],
    "database": ["database", "sql", "mysql", "postgres", "mongodb", "data"],
    "frontend": ["react", "vue", "angular", "javascript", "html", "css", "frontend"],
    "backend": ["node", "python", "java", "django", "fastapi", "backend", "api"],
    "devops": ["docker", "kubernetes", "aws", "cloud", "ci/cd", "devops", "deployment"],
    "system_design": ["architecture", "system", "design", "scalability", "microservices"],
    "testing": ["test", "testing", "unit", "jest", "pytest", "quality"],
    "security": ["security", "auth", "oauth", "jwt", "encryption"],
}

SOFT_SKILLS = [
    "leadership", "teamwork", "communication", "problem_solving",
    "time_management", "adaptability", "conflict_resolution",
    "critical_thinking", "creativity", "decision_making"
]

BEHAVIORAL_AREAS = [
    "leadership", "teamwork", "conflict", "failure", "success",
    "challenge", "goal", "learning", "communication", "motivation"
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class QuestionSchema(BaseModel):
    id: int = Field(description="Sequence number of the question")
    question: str = Field(description="The actual interview question text")
    category: str = Field(description="Category: technical, behavioral, resume-based, situational")
    difficulty: str = Field(description="The difficulty level targeted")
    time_limit: int = Field(description="Time limit for this question in seconds")
    skill_tested: str = Field(description="Primary skill being tested")
    follow_up_topic: str = Field(description="Topic for potential follow-up question")


class EvaluationSchema(BaseModel):
    score: float = Field(description="Overall score between 0.0 and 10.0")
    metrics: Dict[str, float] = Field(description="Scores for accuracy, clarity, depth, communication (0-10)")
    feedback: str = Field(description="Constructive feedback for the candidate")
    topic: str = Field(description="The specific skill or topic being evaluated")
    skill_category: str = Field(description="Category: technical, soft_skill, behavioral")
    should_deep_dive: bool = Field(description="Whether to ask a follow-up on this same topic")
    is_coding_challenge: bool = Field(default=False, description="Whether to trigger a coding sandbox")
    needs_easier: bool = Field(default=False, description="Whether the candidate needs an easier question")
    low_effort: bool = Field(default=False, description="Whether the answer is low effort")
    skill_identified: str = Field(description="The specific skill detected in the answer")


class CompletionSchema(BaseModel):
    should_complete: bool = Field(description="Whether interview should end")
    reason: str = Field(description="Reason for completion decision")
    skills_covered_count: int = Field(description="Number of unique skills covered")
    coverage_percentage: float = Field(description="Percentage of skills covered")
    average_score: float = Field(description="Average score across all questions")
    overall_quality: str = Field(description="Good, Average, or Poor")


# ── Helper Functions ───────────────────────────────────────────────────────────

# ── Human-like Response Templates ───────────────────────────────────────
CONVERSATIONAL_ACKNOWLEDGMENTS = [
    "Great, thanks for sharing that. ",
    "I appreciate you telling me about that. ",
    "That's helpful context. ",
    "Understood, let's build on that. ",
    "Got it, moving on. ",
    "Thanks for that perspective. ",
    "Good to know. ",
    "That's interesting — ",
    "Makes sense. ",
    "Interesting! Let me follow up on that. ",
]

PHASE_TRANSITIONS = {
    ("greeting", "welcome"): "Wonderful! It's great to have you here today. ",
    ("welcome", "warmup"): "I enjoy hearing about your journey. ",
    ("warmup", "technical"): "Now let's dig a bit deeper into your technical background. ",
    ("technical", "stress"): "Alright, let me challenge you a little. ",
    ("stress", "behavioral"): "That was a good exercise. Now let's talk about how you work with others. ",
    ("behavioral", "closing"): "We're almost done. I appreciate your patience. ",
}

GREETING_MESSAGES = [
    "Hey! I'm really glad you could make it today.",
    "Hi there! Welcome — thank you for joining.",
    "Hello! I'm excited to speak with you today.",
    "Good to see you! I appreciate you taking the time.",
]


def _get_conversational_ack(score: float, topic: str, should_deep_dive: bool = False) -> str:
    """Build a natural acknowledgment based on the previous answer quality."""
    if should_deep_dive:
        ack_options = [
            "That's a really strong answer. ",
            "Excellent response — you've clearly thought this through. ",
            "Impressive. You really know your stuff here. ",
            "Love that depth. You nailed it. ",
            "That's exactly the kind of insight I was looking for. ",
        ]
    elif score >= 6.0:
        ack_options = [
            "Good answer. ",
            "That's a solid response. ",
            "Right, that makes sense. ",
            "Good, I like where you're going with this. ",
            "Okay, that's a reasonable perspective. ",
        ]
    elif score >= 4.0:
        ack_options = [
            "I see what you mean. Let me ask about that differently. ",
            "Interesting approach. Let me dig a bit deeper. ",
            "That's one way to look at it — let's explore it further. ",
            "I hear you. Let me probe a bit more on this. ",
        ]
    else:
        ack_options = [
            "No worries, let me rephrase. ",
            "That's okay — let me try a simpler angle. ",
            "No problem at all. Let's approach this differently. ",
            "I understand. Let me help you with this one. ",
        ]
    return random.choice(ack_options)


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


def _extract_skills_from_text(text: str) -> List[str]:
    """Extract skills mentioned in the text."""
    text_lower = text.lower()
    found_skills = []

    for category, keywords in TECHNICAL_SKILLS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_skills.append(category)
                break

    for skill in SOFT_SKILLS:
        if skill in text_lower:
            found_skills.append(f"soft_{skill}")

    return list(set(found_skills))


def _determine_phase_from_index(idx: int) -> str:
    """Natural phase flow based on question index."""
    if idx <= 1:
        return "greeting"
    elif idx <= 3:
        return "welcome"
    elif idx <= 6:
        return "warmup"
    elif idx <= 10:
        return "technical"
    elif idx <= 12:
        return "stress"
    elif idx <= 14:
        return "behavioral"
    else:
        return "closing"


def _initialize_skills_to_cover(resume_text: str, job_role: str) -> List[str]:
    """Initialize skills to cover based on resume and job role."""
    text = f"{resume_text} {job_role}".lower()
    skills = []

    for category, keywords in TECHNICAL_SKILLS.items():
        if any(kw in text for kw in keywords):
            skills.append(category)

    if not skills:
        skills = list(TECHNICAL_SKILLS.keys())[:5]

    skills.extend(["soft_communication", "soft_problem_solving", "soft_teamwork"])

    return list(set(skills))


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def generate_question_node(state: InterviewState) -> Dict[str, Any]:
    """Interviewer Agent — generates natural, adaptive, skill-based questions."""
    last_eval = state.get('last_evaluation')
    idx = state['current_question_index']
    current_phase = _determine_phase_from_index(idx)
    previous_phase = state.get('current_phase')

    # Check if transitioning to new phase
    phase_transition = previous_phase != current_phase if previous_phase else False

    # Parse evaluation
    should_deep_dive = False
    needs_easier = False
    detected_skill = None

    if last_eval and isinstance(last_eval, dict):
        should_deep_dive = last_eval.get('should_deep_dive', False)
        needs_easier = last_eval.get('needs_easier', False)
        detected_skill = last_eval.get('skill_identified')
        low_effort = last_eval.get('low_effort', False)

        if low_effort:
            needs_easier = True

    # Get LLM based on complexity
    llm = get_adaptive_llm() if should_deep_dive else get_fast_llm()
    parser = JsonOutputParser(pydantic_object=QuestionSchema)

    # Build conversation history with last few exchanges
    messages = state.get('messages', [])
    recent_history = messages[-6:] if len(messages) > 6 else messages

    history = "\n".join(
        f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content'][:400]}"
        for m in recent_history
    )

    # Get skills tracking
    covered_skills = state.get('covered_skills', [])
    pending_skills = state.get('pending_skills', [])

    # Build a natural conversational opening based on previous answer
    conversational_opening = ""
    if last_eval and messages:
        prev_score = last_eval.get('score', 5.0)
        prev_topic = last_eval.get('topic', 'topic')
        conversational_opening = _get_conversational_ack(prev_score, prev_topic, should_deep_dive)
        # Add specific acknowledgment that acknowledges what they actually said
        last_answer = messages[-1]['content'] if messages and messages[-1]['role'] == 'user' else ""
        if len(last_answer) < 100:
            conversational_opening += f"I hear you. "
        elif len(last_answer) < 300:
            conversational_opening += f"Got it. "

    # Phase guides with NATURAL flow — sound like a real human interviewer
    phase_guides = {
        "greeting": "Start with genuine warmth. Introduce yourself casually, like 'Hey, I'm Alex — thanks for making time for this.' Then casually ask something simple like 'How's your day going?' or 'How are you feeling about this?' Don't sound like a robot.",
        "welcome": "Express genuine interest in their story. Say something like 'I'd love to hear a bit about your background — what brought you here?' Make it feel like a conversation, not an interrogation. Use their name if you know it.",
        "warmup": "Ease into it naturally. Ask about their recent work in a way that lets them open up — 'What's been the most interesting thing you've worked on recently?' or 'Tell me about a project you're proud of.' Let them relax.",
        "technical": "Make the technical questions feel like a discussion, not a test. Say something like 'So I want to dig into some of the technical stuff you've worked on' or 'Let me ask you about some of the things you mentioned in your background.'",
        "stress": "Acknowledge the shift: 'Alright, things are about to get a bit more interesting' or 'Let me push you a little here.' Make it feel like a challenge between two professionals, not an interrogation.",
        "behavioral": "Transition naturally: 'Now let's talk about you as a person — how you work with teams, handle difficult situations, that kind of thing.' Sound like you genuinely want to understand who they are.",
        "closing": "Make it feel like the natural end of a good conversation. 'We're almost done here' or 'Almost through — I appreciate your patience.' Then give them space for any final thoughts. End warmly."
    }

    phase_guide = phase_guides.get(current_phase, "Ask a relevant question in a conversational way.")

    # Build context-aware instructions
    context_instructions = []

    # First question - natural greeting
    if idx == 0:
        greeting = random.choice(GREETING_MESSAGES)
        context_instructions.append(f"FIRST IMPRESSION: Start with a warm, human greeting like '{greeting}' Then ask them to introduce themselves naturally. Use their name if known. Sound like a real person, not a script.")

    # Phase transition - natural bridge
    if phase_transition and previous_phase and current_phase:
        bridge = PHASE_TRANSITIONS.get((previous_phase, current_phase), "")
        if bridge:
            context_instructions.append(f"PHASE TRANSITION: Begin your response with something natural like '{bridge}' This should feel like a smooth, conversational shift.")

    # Skills coverage - naturally weave in
    if pending_skills and current_phase in ["technical", "stress"]:
        skill_context = f"IMPORTANT: These skills still need coverage: {', '.join(pending_skills[:3])}. Find natural ways to weave questions about these into the conversation."
        context_instructions.append(skill_context)

    # Adaptive based on last response - conversational adaptation
    if last_eval:
        score = last_eval.get('score', 5.0)
        topic = last_eval.get('topic', 'previous topic')
        skill_identified = last_eval.get('skill_identified', topic)

        if should_deep_dive:
            context_instructions.append(f"DEEP DIVE: They showed strength in '{skill_identified}'. Acknowledge their good answer naturally, then push them further with a more challenging angle.")
        elif needs_easier:
            context_instructions.append(f"SIMPLER PATH: They seemed to struggle a bit with '{skill_identified}'. Back off the complexity. Acknowledge their answer warmly, then ask an easier version that still lets them shine.")
        elif score >= 7.5:
            context_instructions.append(f"STRONG ANSWER: They did well on '{skill_identified}'. Acknowledge it naturally like 'Nice answer,' then either increase difficulty or explore a related angle.")

    # Natural follow-up instruction
    if state.get('follow_up_requested'):
        context_instructions.append("They asked a clarifying question. Answer it conversationally and briefly (1-2 sentences max), then smoothly return to the interview flow.")

    # Build system prompt — sounds like a real, thoughtful human interviewer
    context_str = "\n".join(context_instructions)
    conversational_str = conversational_opening if conversational_opening else ""

    system_prompt = f"""You are a senior interviewer conducting a CONVERSATIONAL, NATURAL interview — not a rigid Q&A. You sound like an intelligent, empathetic human who is genuinely curious about the candidate. Think of yourself as a thoughtful senior engineer having a real conversation.

JOB ROLE: {state['job_role']}

CURRENT PHASE: {current_phase}
QUESTION NUMBER: {idx + 1}
CURRENT DIFFICULTY: {state['difficulty']}

YOUR APPROACH: {phase_guide}

{context_str}

YOUR PREVIOUS RESPONSE ACKNOWLEDGMENT (include naturally at the start of your response):
{conversational_str}

SKILLS COVERED: {', '.join(covered_skills) if covered_skills else 'None yet'}
SKILLS STILL TO COVER: {', '.join(pending_skills) if pending_skills else 'All covered'}

RESUME CONTEXT (for relevant, personalized questions):
{state['resume_text'][:1500]}

RECENT CONVERSATION:
{history}

IMPORTANT RULES — READ CAREFULLY:
1. Your response should sound like a REAL HUMAN SPEAKING. Use casual but professional language.
2. Include a brief acknowledgment of their previous answer naturally (1-3 sentences).
3. Then ask ONE clear, conversational question at a time.
4. Never sound robotic. Avoid: "I would like to ask", "Moving on to", "Next question", etc.
5. Use phrases that sound human: "Tell me about...", "What are your thoughts on...", "How did you approach...", "Walk me through..."
6. If difficulty='easy', ask simple, concrete questions that let them shine.
7. If difficulty='hard', ask multi-part challenges that probe depth.
8. Never repeat questions already asked.
9. OUTPUT JSON ONLY with these fields: id, question, category, difficulty, time_limit, skill_tested, follow_up_topic
10. The 'question' field should be natural, human-sounding text only — no prefix like "Question:" or "My next question is:"

BIAS MITIGATION — CRITICAL:
- Evaluate candidates solely on their demonstrated skills and knowledge.
- Never make assumptions about a candidate's abilities based on their background, gender, age, or communication style.
- Ask the same core competency questions to all candidates for the same role.
- Focus on what the candidate CAN do, not what they haven't had the opportunity to learn.
- Avoid questions that assume specific cultural or socioeconomic experiences.
- If a candidate struggles with a question, offer an alternative approach rather than assuming lack of ability.

{parser.get_format_instructions()}"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Generate natural question {idx + 1} for {current_phase} phase."),
        ])
        clean_content = _strip_markdown(response.content)
        parsed_q = parser.parse(clean_content)

        # Determine if coding challenge (for technical phases)
        is_coding = current_phase in ['technical', 'stress'] and (idx + 1) % 4 == 0

        return {
            "next_question": parsed_q,
            "messages": [{"role": "assistant", "content": parsed_q['question']}],
            "current_phase": current_phase,
            "phase_transition": phase_transition,
            "previous_phase": previous_phase,
            "is_coding_mode": is_coding,
            "code_language": "python" if is_coding else None,
            "follow_up_requested": False,
            "previous_topic": parsed_q.get('follow_up_topic'),
        }
    except Exception as e:
        logger.error(f"generate_question_node failed: {e}")

        # Smart fallback
        fallback_questions = {
            "greeting": ["Hello! Welcome to your interview. How are you feeling today?"],
            "welcome": ["Could you tell me a bit about yourself and your background?"],
            "warmup": ["What was your most recent role and what did you enjoy most about it?"],
            "technical": ["Can you describe a technical challenge you solved recently?"],
            "stress": ["Tell me about a time you had to handle a difficult situation under pressure."],
            "behavioral": ["Can you share an experience where you had to work with a difficult team member?"],
            "closing": ["Do you have any questions for me? What are your key takeaways from this interview?"]
        }

        fallback_q = fallback_questions.get(current_phase, fallback_questions["technical"])[idx % 3]

        return {
            "next_question": {
                "id": idx + 1,
                "question": fallback_q,
                "category": current_phase,
                "difficulty": state['difficulty'],
                "time_limit": 120,
                "skill_tested": "general",
                "follow_up_topic": None
            },
            "messages": [{"role": "assistant", "content": fallback_q}],
            "current_phase": current_phase,
            "phase_transition": phase_transition,
            "is_coding_mode": False,
            "code_language": None,
        }


async def evaluate_answer_node(state: InterviewState) -> Dict[str, Any]:
    """Evaluator Agent — scores answers and extracts skills."""
    llm = get_strong_llm()
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)

    last_question = state.get('next_question', {})
    q_text = last_question.get('question', '') if isinstance(last_question, dict) else ''
    q_skill = last_question.get('skill_tested', 'general') if isinstance(last_question, dict) else 'general'

    last_message = state['messages'][-1]['content'] if state.get('messages') else ""

    # Check for low effort responses
    low_effort_indicators = ['ok', 'yes', 'no', 'okay', 'uh', 'um', 'idk', 'maybe', 'shrug', '🤷']
    is_low_effort = (
        len(last_message.strip()) < 15 or
        last_message.lower().strip() in low_effort_indicators or
        all(last_message.lower().count(c) < 3 for c in 'aeiou')
    )

    if is_low_effort:
        return {
            "last_evaluation": {
                "score": 2.0,
                "metrics": {"accuracy": 1, "clarity": 2, "depth": 1, "communication": 3},
                "topic": "engagement",
                "skill_category": "behavioral",
                "should_deep_dive": False,
                "needs_easier": True,
                "low_effort": True,
                "skill_identified": "engagement"
            },
            "latest_score": 2.0,
            "metrics": {"accuracy": 1, "clarity": 2, "depth": 1, "communication": 3},
            "total_responses": state.get('total_responses', 0) + 1,
            "low_quality_count": state.get('low_quality_count', 0) + 1,
        }

    system_prompt = f"""You are a senior hiring manager evaluating a candidate for {state['job_role']}.

SCORING (0.0–10.0):
- Accuracy: Technical correctness
- Clarity: How well they communicate
- Depth: Level of insight and detail
- Communication: Professionalism and structure

QUESTION ASKED: {q_text}
SKILL BEING TESTED: {q_skill}
CANDIDATE'S ANSWER: {last_message}

Evaluate the answer carefully. Consider:
1. Did they answer the question?
2. How detailed was their response?
3. Did they provide examples?
4. Was their communication clear?
5. Did they show relevant skills?

Also identify:
- The PRIMARY skill category they demonstrated (technical, soft_skill, behavioral)
- The specific skill they used (e.g., leadership, python, teamwork)
- Whether you should follow up for deeper evaluation
- Whether they need an easier question
- If the answer is low effort (too short or meaningless)

BIAS MITIGATION — CRITICAL:
- Evaluate solely on demonstrated skills and knowledge in this answer.
- Do not penalize for communication style differences, cultural background, or non-native English.
- Focus on substance over eloquence — a technically correct but brief answer can still score well.
- Consider that candidates may express knowledge differently based on their background.
- Never assume lack of experience equals lack of ability.
- Score based on what IS present in the answer, not what is absent.

{parser.get_format_instructions()}"""

    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt)])
        clean_content = _strip_markdown(response.content)
        parsed = parser.parse(clean_content)

        return {
            "last_evaluation": parsed,
            "latest_score": parsed['score'],
            "metrics": parsed['metrics'],
            "total_responses": state.get('total_responses', 0) + 1,
            "high_quality_count": state.get('high_quality_count', 0) + (1 if parsed.get('score', 0) >= 6 else 0),
            "low_quality_count": state.get('low_quality_count', 0),
        }
    except Exception as e:
        logger.error(f"evaluate_answer_node failed: {e}")
        return {
            "last_evaluation": {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": "general",
                "skill_category": "behavioral",
                "should_deep_dive": False,
                "needs_easier": False,
                "low_effort": False,
                "skill_identified": "general"
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "total_responses": state.get('total_responses', 0) + 1,
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

    system_prompt = f"""You are a Principal Software Engineer evaluating a code submission for {state['job_role']}.

CHALLENGE: {q_text}
CODE:\n{code}
{execution_info}

CRITERIA: Logic & Correctness, Time/Space Complexity, Readability, Best Practices.

Evaluate the code carefully and provide scores.

{parser.get_format_instructions()}"""

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
                "skill_category": "technical",
                "should_deep_dive": False,
                "needs_easier": False,
                "low_effort": False,
                "skill_identified": "programming"
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "is_coding_mode": False,
        }


async def update_memory_node(state: InterviewState) -> Dict[str, Any]:
    """Decision & Memory Agent — adaptive difficulty, skill tracking, completion detection."""
    try:
        eval_result = state.get('last_evaluation', {})
        score = eval_result.get('score', 5.0)
        topic = eval_result.get('topic', 'general')
        skill_category = eval_result.get('skill_category', 'behavioral')
        skill_identified = eval_result.get('skill_identified', topic)

        # Update difficulty based on performance
        diff = state['difficulty']
        if eval_result.get('needs_easier', False) or score < 4.0:
            diff = "easy" if diff not in ["easy"] else "easy"
        elif score > 7.5:
            if diff == "easy":
                diff = "medium"
            elif diff == "medium":
                diff = "hard"

        # Update topic scores
        new_topic_scores = state.get('topic_scores', {}).copy()
        new_topic_scores[skill_identified] = score

        # Update topic strengths
        new_strengths = state.get('topic_strengths', {}).copy()
        if score >= 7.5:
            new_strengths[skill_identified] = "strong"
        elif score >= 4.5:
            new_strengths[skill_identified] = "improving"
        else:
            new_strengths[skill_identified] = "weak"

        # Update skill coverage
        covered_skills = state.get('covered_skills', []).copy()
        pending_skills = state.get('pending_skills', []).copy()

        if skill_identified and skill_identified not in covered_skills:
            covered_skills.append(skill_identified)
            if skill_identified in pending_skills:
                pending_skills.remove(skill_identified)

        # Calculate coverage percentage
        total_skills = len(state.get('skills_to_cover', []))
        if total_skills > 0:
            coverage_pct = (len(covered_skills) / total_skills) * 100
        else:
            coverage_pct = 100.0

        # Calculate running average
        current_avg = state.get('avg_score', 0)
        idx = state['current_question_index']
        new_avg = ((current_avg * idx) + score) / (idx + 1) if idx > 0 else score

        # Determine phase
        idx = state['current_question_index'] + 1
        current_phase = _determine_phase_from_index(idx)

        # AUTO-COMPLETION DETECTION
        interview_complete = False
        completion_reason = None

        max_q = state.get('max_questions', 15)
        high_q = state.get('high_quality_count', 0)
        low_q = state.get('low_quality_count', 0)

        # Completion condition 1: Maximum questions reached with good coverage
        if idx >= max_q:
            if coverage_pct >= 60:
                interview_complete = True
                completion_reason = f"Completed with {coverage_pct:.0f}% skill coverage and avg score {new_avg:.1f}"
            else:
                interview_complete = True
                completion_reason = f"Maximum questions ({max_q}) reached"

        # Completion condition 2: All skills covered and good average
        elif coverage_pct >= 85 and new_avg >= 6.0:
            interview_complete = True
            completion_reason = f"All major skills covered ({coverage_pct:.0f}%) with quality average {new_avg:.1f}"

        # Completion condition 3: Too many low quality responses
        elif low_q >= 3 and idx >= 5:
            interview_complete = True
            completion_reason = "Multiple low-effort responses detected"

        # Completion condition 4: Consistently high performance
        elif high_q >= 5 and new_avg >= 8.0 and idx >= 10:
            interview_complete = True
            completion_reason = f"Excellent performance ({high_q} high-quality responses, avg {new_avg:.1f})"

        # Completion condition 5: User unresponsive in closing phase
        elif current_phase == "closing" and idx >= 12:
            interview_complete = True
            completion_reason = "Interview closing phase complete"

        # Don't complete too early
        if idx < 6 and interview_complete:
            interview_complete = False
            completion_reason = None

        return {
            "difficulty": diff,
            "topic_strengths": new_strengths,
            "topic_scores": new_topic_scores,
            "covered_skills": covered_skills,
            "pending_skills": pending_skills,
            "skill_coverage_percentage": coverage_pct,
            "avg_score": new_avg,
            "current_phase": current_phase,
            "current_question_index": idx,
            "interview_complete": interview_complete,
            "completion_reason": completion_reason,
            "is_coding_mode": False,
        }
    except Exception as e:
        logger.error(f"update_memory_node failed: {e}")
        return {
            "current_question_index": state['current_question_index'] + 1,
            "interview_complete": state['current_question_index'] + 1 >= state.get('max_questions', 15),
            "completion_reason": "Maximum questions reached",
        }


# ── AI Advisor Monitor Node (Phase 1A) ─────────────────────────────────────────

async def advisor_monitor_node(state: InterviewState) -> Dict[str, Any]:
    """
    Silent advisor that monitors interview and notifies HR when ready to close.
    Never forces termination — only suggests to interviewer.

    This node runs after update_memory_node and before the should_continue check.
    It analyzes interview signals and returns advisor state fields.
    """
    from .advisor_service import assess_interview_advisor

    # Don't suggest before question 6 (minimum data needed)
    if state.get('current_question_index', 0) < 6:
        return {
            "advisor_ready_to_close": False,
            "advisor_notified": False,
        }

    # Don't suggest again if already notified and interviewer hasn't acted
    if state.get('advisor_notified') and not state.get('advisor_action_taken'):
        return {}  # No change — already notified

    try:
        decision = await assess_interview_advisor(state)

        return {
            "advisor_ready_to_close": decision.ready_to_close,
            "advisor_confidence": decision.confidence,
            "advisor_reason": decision.reason,
            "advisor_reason_category": decision.reason_category,
            "advisor_notified": decision.ready_to_close,
            "advisor_action_taken": False,
        }
    except Exception as e:
        logger.error(f"advisor_monitor_node failed: {e}")
        # Return empty dict — no advisor suggestion on failure
        # Interview continues normally
        return {}
