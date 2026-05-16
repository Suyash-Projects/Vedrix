"""
Test Interview Engine Nodes — question generation, evaluation, and memory.
Covers: adaptive flow, skill tracking, phase transitions, edge cases.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class MockResponse:
    """Mock LLM response that returns structured JSON."""
    def __init__(self, content):
        self.content = content


class TestQuestionGeneration:
    """Tests for generate_question_node."""

    @pytest.mark.asyncio
    async def test_first_question_is_greeting_phase(self, sample_interview_state):
        """First question should always be in greeting phase."""
        from app.services.interview_engine.nodes import generate_question_node, _determine_phase_from_index

        state = sample_interview_state.copy()
        state['current_question_index'] = 0
        state['current_phase'] = _determine_phase_from_index(0)

        assert state['current_phase'] == "greeting"

    @pytest.mark.asyncio
    async def test_greeting_phase_uses_greeting_messages(self):
        """Greeting phase should return greeting-style questions."""
        from app.services.interview_engine.nodes import (
            generate_question_node, GREETING_MESSAGES, CONVERSATIONAL_ACKNOWLEDGMENTS
        )

        assert len(GREETING_MESSAGES) > 0
        assert all(isinstance(g, str) and len(g) > 5 for g in GREETING_MESSAGES)

    @pytest.mark.asyncio
    async def test_phase_transitions_are_defined(self):
        """Phase transitions should have natural bridging messages."""
        from app.services.interview_engine.nodes import PHASE_TRANSITIONS

        assert ("greeting", "welcome") in PHASE_TRANSITIONS
        assert ("welcome", "warmup") in PHASE_TRANSITIONS
        assert ("warmup", "technical") in PHASE_TRANSITIONS
        assert ("technical", "stress") in PHASE_TRANSITIONS
        assert ("stress", "behavioral") in PHASE_TRANSITIONS
        assert ("behavioral", "closing") in PHASE_TRANSITIONS

    @pytest.mark.asyncio
    async def test_conversational_acknowledgments_vary_by_score(self):
        """Conversational acknowledgments should vary based on answer score."""
        from app.services.interview_engine.nodes import _get_conversational_ack

        high_ack = _get_conversational_ack(8.5, "python", should_deep_dive=True)
        assert any(high_ack.startswith(good) for good in ["That's", "Excellent", "Impressive", "Love"])

        mid_ack = _get_conversational_ack(6.0, "python")
        assert any(mid_ack.startswith(good) for good in ["Good", "That's", "Right", "Okay"])

        low_ack = _get_conversational_ack(3.0, "python")
        assert any(low_ack.startswith(good) for good in ["No worries", "That's", "No problem", "I understand"])

    @pytest.mark.asyncio
    async def test_determine_phase_from_index(self):
        """Phase determination should be consistent across indices."""
        from app.services.interview_engine.nodes import _determine_phase_from_index

        assert _determine_phase_from_index(0) == "greeting"
        assert _determine_phase_from_index(1) == "greeting"
        assert _determine_phase_from_index(2) == "welcome"
        assert _determine_phase_from_index(4) == "warmup"
        assert _determine_phase_from_index(7) == "technical"
        assert _determine_phase_from_index(11) == "stress"
        assert _determine_phase_from_index(13) == "behavioral"
        assert _determine_phase_from_index(15) == "closing"

    @pytest.mark.asyncio
    async def test_fallback_question_on_llm_failure(self, sample_interview_state):
        """If LLM fails, should return a fallback question, not crash."""
        from app.services.interview_engine.nodes import generate_question_node
        import logging

        state = sample_interview_state.copy()
        state['current_phase'] = "technical"
        state['messages'] = []

        with patch('app.services.interview_engine.nodes.get_fast_llm') as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=Exception("API Error"))
            mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            result = await generate_question_node(state)

            # Should get fallback question
            assert 'next_question' in result
            assert 'question' in result['next_question']
            assert len(result['next_question']['question']) > 5
            assert result['messages'][0]['role'] == 'assistant'

    @pytest.mark.asyncio
    async def test_low_effort_answer_detection(self, sample_interview_state):
        """Low effort answers should be detected and scored low."""
        from app.services.interview_engine.nodes import evaluate_answer_node

        state = sample_interview_state.copy()
        state['messages'] = [
            {"role": "assistant", "content": "Tell me about your experience."},
            {"role": "user", "content": "ok"}
        ]
        state['next_question'] = {
            "question": "Tell me about your experience",
            "skill_tested": "communication"
        }

        with patch('app.services.interview_engine.nodes.get_strong_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            result = await evaluate_answer_node(state)

            assert result['last_evaluation']['low_effort'] == True
            assert result['last_evaluation']['score'] == 2.0
            assert result['metrics']['clarity'] == 2

    @pytest.mark.asyncio
    async def test_very_short_answer_is_low_effort(self, sample_interview_state):
        """Answers with less than 15 characters should be flagged as low effort."""
        from app.services.interview_engine.nodes import evaluate_answer_node

        state = sample_interview_state.copy()
        state['messages'] = [
            {"role": "assistant", "content": "What is Python?"},
            {"role": "user", "content": "uh"}
        ]
        state['next_question'] = {"question": "What is Python?", "skill_tested": "python"}

        with patch('app.services.interview_engine.nodes.get_strong_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            result = await evaluate_answer_node(state)
            assert result['last_evaluation']['low_effort'] == True


class TestMemoryAndAdaptiveDifficulty:
    """Tests for update_memory_node — difficulty adaptation and skill tracking."""

    @pytest.mark.asyncio
    async def test_difficulty_increases_after_good_answers(self, sample_answer_state):
        """After consistently good answers, difficulty should increase."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_answer_state.copy()
        state['difficulty'] = "easy"
        state['last_evaluation'] = {'score': 8.0, 'topic': 'python', 'skill_category': 'technical',
                                     'skill_identified': 'programming', 'needs_easier': False, 'should_deep_dive': False}

        result = await update_memory_node(state)

        assert result['difficulty'] in ["medium", "hard"]

    @pytest.mark.asyncio
    async def test_difficulty_decreases_after_struggles(self, sample_answer_state):
        """After poor answers, difficulty should decrease."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_answer_state.copy()
        state['difficulty'] = "hard"
        state['last_evaluation'] = {'score': 3.0, 'topic': 'python', 'skill_category': 'technical',
                                     'skill_identified': 'programming', 'needs_easier': True, 'should_deep_dive': False}

        result = await update_memory_node(state)

        assert result['difficulty'] == "easy"

    @pytest.mark.asyncio
    async def test_skills_are_tracked_as_covered(self, sample_answer_state):
        """Skills identified in answers should be marked as covered."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_answer_state.copy()
        state['pending_skills'] = ['programming', 'database', 'backend']
        state['covered_skills'] = []
        state['last_evaluation'] = {'score': 7.5, 'topic': 'python', 'skill_category': 'technical',
                                     'skill_identified': 'programming', 'needs_easier': False, 'should_deep_dive': False}

        result = await update_memory_node(state)

        assert 'programming' in result['covered_skills']
        assert 'programming' not in result['pending_skills']

    @pytest.mark.asyncio
    async def test_interview_completes_after_max_questions(self, sample_interview_state):
        """Interview should complete when max questions are reached."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_interview_state.copy()
        state['current_question_index'] = 14  # max is 15
        state['max_questions'] = 15
        state['skill_coverage_percentage'] = 70

        result = await update_memory_node(state)

        assert result['interview_complete'] == True

    @pytest.mark.asyncio
    async def test_interview_never_completes_before_question_6(self, sample_interview_state):
        """Interview shouldn't end too early (minimum questions)."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_interview_state.copy()
        state['current_question_index'] = 3
        state['max_questions'] = 15
        state['low_quality_count'] = 10  # Would trigger completion

        result = await update_memory_node(state)

        # Should NOT complete early
        assert result['interview_complete'] == False

    @pytest.mark.asyncio
    async def test_topic_scores_are_recorded(self, sample_answer_state):
        """Topic scores should be recorded for the radar chart."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_answer_state.copy()
        state['topic_scores'] = {}
        state['last_evaluation'] = {'score': 7.5, 'topic': 'python', 'skill_category': 'technical',
                                     'skill_identified': 'programming', 'needs_easier': False, 'should_deep_dive': False}

        result = await update_memory_node(state)

        assert 'programming' in result['topic_scores']
        assert result['topic_scores']['programming'] == 7.5

    @pytest.mark.asyncio
    async def test_topic_strengths_are_categorized(self, sample_answer_state):
        """Topic strengths should be categorized as weak/improving/strong."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_answer_state.copy()
        state['topic_strengths'] = {}
        state['last_evaluation'] = {'score': 8.5, 'topic': 'python', 'skill_category': 'technical',
                                     'skill_identified': 'python', 'needs_easier': False, 'should_deep_dive': False}

        result = await update_memory_node(state)

        assert result['topic_strengths'].get('python') == 'strong'

        # Test weak
        state['last_evaluation']['score'] = 3.0
        state['topic_strengths'] = {}
        result = await update_memory_node(state)
        assert result['topic_strengths'].get('python') == 'weak'


class TestCodeEvaluation:
    """Tests for evaluate_code_node."""

    @pytest.mark.asyncio
    async def test_code_evaluation_returns_structured_result(self, sample_interview_state):
        """Code evaluation should return properly structured evaluation."""
        from app.services.interview_engine.nodes import evaluate_code_node

        state = sample_interview_state.copy()
        state['messages'] = [
            {"role": "assistant", "content": "Write a function to reverse a string."},
            {"role": "user", "content": "[Code Submitted]\nStatus: Accepted\nOutput: tests passed"}
        ]
        state['code_snippet'] = "def reverse(s): return s[::-1]"
        state['next_question'] = {"question": "Write a function to reverse a string.", "skill_tested": "python"}

        with patch('app.services.interview_engine.nodes.get_code_llm') as mock_get_llm:
            mock_llm = AsyncMock()
            response = MockResponse(
                '{"score": 8.0, "metrics": {"accuracy": 9.0, "clarity": 7.5, "depth": 7.5, "communication": 8.0}, "feedback": "Clean solution", "topic": "string_manipulation", "skill_category": "technical", "should_deep_dive": false, "is_coding_challenge": true, "needs_easier": false, "low_effort": false, "skill_identified": "programming"}'
            )
            mock_llm.ainvoke = AsyncMock(return_value=response)
            mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            result = await evaluate_code_node(state)

            assert 'last_evaluation' in result
            assert result['latest_score'] == 8.0
            assert result['is_coding_mode'] == False  # Should exit coding mode after evaluation


class TestReportGeneration:
    """Tests for evaluation_service — final report generation."""

    @pytest.mark.asyncio
    async def test_report_generation_returns_all_required_fields(self, sample_report):
        """Report should contain all required fields for display."""
        required_fields = [
            'overall_score', 'hire_recommendation', 'technical_accuracy',
            'communication_clarity', 'depth_of_knowledge', 'strengths',
            'weaknesses', 'summary'
        ]

        for field in required_fields:
            assert field in sample_report, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_hire_recommendation_values(self, sample_report):
        """Hire recommendation should be a valid value."""
        valid_recs = ['Strong Hire', 'Hire', 'Maybe', 'No Hire']
        assert sample_report['hire_recommendation'] in valid_recs

    @pytest.mark.asyncio
    async def test_scores_are_within_valid_range(self, sample_report):
        """All scores should be between 0 and 10."""
        assert 0 <= sample_report['overall_score'] <= 10
        assert 0 <= sample_report['technical_accuracy'] <= 10
        assert 0 <= sample_report['communication_clarity'] <= 10
        assert 0 <= sample_report['depth_of_knowledge'] <= 10

    @pytest.mark.asyncio
    async def test_strengths_and_weaknesses_are_lists(self, sample_report):
        """Strengths and weaknesses should be lists."""
        assert isinstance(sample_report['strengths'], list)
        assert isinstance(sample_report['weaknesses'], list)
        assert len(sample_report['strengths']) > 0
        assert len(sample_report['summary']) > 10


class TestSkillInitialization:
    """Tests for _initialize_skills_to_cover."""

    def test_skills_from_resume_are_detected(self):
        """Skills mentioned in resume should be included in skills to cover."""
        from app.services.interview_engine.nodes import _initialize_skills_to_cover

        resume = "I have 5 years of experience with Python, Django, PostgreSQL, Docker and React."
        skills = _initialize_skills_to_cover(resume, "Software Engineer")

        assert 'programming' in skills
        assert 'backend' in skills
        assert 'database' in skills

    def test_fallback_skills_when_none_detected(self):
        """If no skills match, should return default skills."""
        from app.services.interview_engine.nodes import _initialize_skills_to_cover

        skills = _initialize_skills_to_cover("General background", "Any role")

        assert len(skills) > 0
        assert 'programming' in skills  # Should have fallback

    def test_soft_skills_are_always_included(self):
        """Soft skills like communication and teamwork should always be included."""
        from app.services.interview_engine.nodes import _initialize_skills_to_cover

        skills = _initialize_skills_to_cover("Java developer", "Backend Engineer")

        assert 'soft_communication' in skills
        assert 'soft_problem_solving' in skills
        assert 'soft_teamwork' in skills


class TestEdgeCases:
    """Edge case handling for the interview engine."""

    @pytest.mark.asyncio
    async def test_empty_answer_handled_gracefully(self, sample_interview_state):
        """Empty or very short answers should be handled without crashing."""
        from app.services.interview_engine.nodes import evaluate_answer_node

        state = sample_interview_state.copy()
        state['messages'] = [
            {"role": "assistant", "content": "What is your favorite project?"},
            {"role": "user", "content": ""}  # Empty answer
        ]
        state['next_question'] = {"question": "What is your favorite project?", "skill_tested": "general"}

        with patch('app.services.interview_engine.nodes.get_strong_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            result = await evaluate_answer_node(state)
            # Should get evaluation result, not crash
            assert 'last_evaluation' in result

    @pytest.mark.asyncio
    async def test_null_last_evaluation_at_start(self, sample_interview_state):
        """At the start of interview, last_evaluation should be None."""
        from app.services.interview_engine.nodes import generate_question_node

        state = sample_interview_state.copy()
        state['last_evaluation'] = None
        state['messages'] = []

        with patch('app.services.interview_engine.nodes.get_fast_llm') as mock_get_llm:
            mock_llm = AsyncMock()
            response = MockResponse(
                '{"id": 1, "question": "Welcome! Can you tell me about yourself?", "category": "behavioral", "difficulty": "medium", "time_limit": 120, "skill_tested": "communication", "follow_up_topic": null}'
            )
            mock_llm.ainvoke = AsyncMock(return_value=response)
            mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            result = await generate_question_node(state)

            assert result['next_question']['category'] in ['behavioral', 'welcome', 'greeting']

    @pytest.mark.asyncio
    async def test_pending_skills_empty_list_handled(self, sample_interview_state):
        """Empty pending_skills list should not cause errors."""
        from app.services.interview_engine.nodes import generate_question_node

        state = sample_interview_state.copy()
        state['pending_skills'] = []
        state['last_evaluation'] = None

        with patch('app.services.interview_engine.nodes.get_fast_llm') as mock_get_llm:
            mock_llm = AsyncMock()
            response = MockResponse(
                '{"id": 1, "question": "What did you work on recently?", "category": "warmup", "difficulty": "easy", "time_limit": 120, "skill_tested": "general", "follow_up_topic": null}'
            )
            mock_llm.ainvoke = AsyncMock(return_value=response)
            mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            result = await generate_question_node(state)
            assert 'next_question' in result

    @pytest.mark.asyncio
    async def test_max_questions_edge_case(self, sample_interview_state):
        """At exactly max questions, interview should complete."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_interview_state.copy()
        state['current_question_index'] = 15
        state['max_questions'] = 15
        state['skill_coverage_percentage'] = 80
        state['avg_score'] = 6.5
        state['topic_scores'] = {'python': 7.0, 'communication': 6.0}

        result = await update_memory_node(state)

        assert result['interview_complete'] == True
        assert result['completion_reason'] is not None

    @pytest.mark.asyncio
    async def test_multi_word_skill_identified(self, sample_answer_state):
        """Multi-word skills like 'problem_solving' should be tracked correctly."""
        from app.services.interview_engine.nodes import update_memory_node

        state = sample_answer_state.copy()
        state['last_evaluation'] = {'score': 7.0, 'topic': 'problem_solving', 'skill_category': 'soft_skill',
                                     'skill_identified': 'soft_problem_solving', 'needs_easier': False, 'should_deep_dive': False}

        result = await update_memory_node(state)

        assert 'soft_problem_solving' in result['covered_skills'] or 'problem_solving' in result['covered_skills']