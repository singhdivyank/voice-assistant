"""Unit tests for src/core/crew_ai/workflows/session_workflow.py"""

from datetime import timedelta

import pytest
from src.core.crew_ai.workflows.session_workflow import SessionWorkflowManager
from src.utils.consts import WorkflowStep
from src.utils.exceptions import DocJarvisError


@pytest.fixture()
def manager():
    return SessionWorkflowManager()


@pytest.fixture()
def initialized_manager(manager, session_state):
    """Manager with one pre-initialized session."""
    manager.initialize_sessions(session_state)
    return manager, session_state.session_id


# initialize_sessions
class TestInitializeSessions:
    def test_creates_session_entry(self, manager, session_state):
        result = manager.initialize_sessions(session_state)
        assert result["session_id"] == session_state.session_id
        assert result["current_step"] == WorkflowStep.WELCOME.value
        assert result["status"] == "initialised"

    def test_session_is_stored_in_active_sessions(self, manager, session_state):
        manager.initialize_sessions(session_state)
        assert session_state.session_id in manager.active_sessions

    def test_workflow_history_entry_created(self, manager, session_state):
        manager.initialize_sessions(session_state)
        assert session_state.session_id in manager.workflow_history

    def test_initial_step_is_welcome(self, manager, session_state):
        manager.initialize_sessions(session_state)
        step = manager.get_current_step(session_state.session_id)
        assert step == WorkflowStep.WELCOME


# get_current_step
class TestGetCurrentStep:
    def test_raises_for_unknown_session(self, manager):
        with pytest.raises(DocJarvisError):
            manager.get_current_step("nonexistent-id")


# advance_to_next_step
class TestAdvanceToNextStep:
    def test_welcome_advances_to_initial_symptom(self, initialized_manager):
        mgr, sid = initialized_manager
        result = mgr.advance_to_next_step(sid)
        assert result["current_step"] == WorkflowStep.INITIAL_SYMPTOM.value

    def test_sequential_progression(self, initialized_manager):
        mgr, sid = initialized_manager
        expected_sequence = [
            WorkflowStep.INITIAL_SYMPTOM,
            WorkflowStep.QUESTIONS_GENERATED,
            WorkflowStep.QA_IN_PROGRESS,
        ]
        for expected in expected_sequence:
            result = mgr.advance_to_next_step(sid)
            assert result["current_step"] == expected.value

    def test_raises_for_unknown_session(self, manager):
        with pytest.raises(DocJarvisError):
            manager.advance_to_next_step("ghost-session")

    def test_result_contains_previous_and_current_step(self, initialized_manager):
        mgr, sid = initialized_manager
        result = mgr.advance_to_next_step(sid)
        assert "previous_step" in result
        assert "current_step" in result
        assert result["previous_step"] == WorkflowStep.WELCOME.value


# update_session_state / get_session_state
class TestSessionStateUpdates:
    def test_update_and_retrieve_state(self, initialized_manager, session_state):
        mgr, sid = initialized_manager
        session_state.status = "updated"
        mgr.update_session_state(sid, session_state)
        retrieved = mgr.get_session_state(sid)
        assert retrieved.status == "updated"

    def test_get_state_raises_for_unknown(self, manager):
        with pytest.raises(DocJarvisError):
            manager.get_session_state("ghost")

    def test_update_raises_for_unknown(self, manager, session_state):
        with pytest.raises(DocJarvisError):
            manager.update_session_state("ghost", session_state)


# get_session_progress
class TestGetSessionProgress:
    def test_returns_progress_dict(self, initialized_manager):
        mgr, sid = initialized_manager
        progress = mgr.get_session_progress(sid)
        assert "current_step" in progress
        assert "progress_percentage" in progress
        assert "qa_progress" in progress
        assert "step_history" in progress

    def test_progress_percentage_is_numeric(self, initialized_manager):
        mgr, sid = initialized_manager
        progress = mgr.get_session_progress(sid)
        assert isinstance(progress["progress_percentage"], float)

    def test_raises_for_unknown_session(self, manager):
        with pytest.raises(DocJarvisError):
            manager.get_session_progress("ghost")


# mark_session_complete
class TestMarkSessionComplete:
    def test_marks_session_as_completed(self, initialized_manager):
        mgr, sid = initialized_manager
        result = mgr.mark_session_complete(sid)
        assert result["status"] == "completed"
        assert mgr.get_current_step(sid) == WorkflowStep.COMPLETED

    def test_raises_for_unknown_session(self, manager):
        with pytest.raises(DocJarvisError):
            manager.mark_session_complete("ghost")


# _calculate_qa_progress
class TestCalculateQaProgress:
    def test_all_answered_when_conversation_complete(self, manager, session_state):
        progress = manager._calculate_qa_progress(session_state)
        assert "all_answered" in progress
        assert "total_questions" in progress

    def test_no_questions_means_not_answered(self, manager, session_state):
        session_state.questions = []
        progress = manager._calculate_qa_progress(session_state)
        assert progress["all_answered"] is False

    def test_partial_answers_not_complete(self, manager, session_state):
        from src.api.schemas import ConversationTurnSchema

        session_state.questions = ["Q1", "Q2", "Q3"]
        session_state.conversation = [
            ConversationTurnSchema(question="Q1", answer="Yes"),
        ]
        progress = manager._calculate_qa_progress(session_state)
        assert not progress["all_answered"]
        assert progress["answered_questions"] == 1


# cleanup_completed_sessions
class TestCleanupCompletedSessions:
    def test_removes_old_completed_sessions(self, initialized_manager):
        mgr, sid = initialized_manager
        mgr.mark_session_complete(sid)
        mgr.active_sessions[sid]["last_updated"] -= timedelta(hours=25)

        removed = mgr.cleanup_completed_sessions(max_age_hours=24)
        assert removed == 1
        assert sid not in mgr.active_sessions

    def test_keeps_recent_completed_sessions(self, initialized_manager):
        mgr, sid = initialized_manager
        mgr.mark_session_complete(sid)
        removed = mgr.cleanup_completed_sessions(max_age_hours=24)
        assert removed == 0
        assert sid in mgr.active_sessions

    def test_does_not_remove_active_sessions(self, initialized_manager):
        mgr, sid = initialized_manager
        mgr.active_sessions[sid]["last_updated"] -= timedelta(hours=48)
        removed = mgr.cleanup_completed_sessions(max_age_hours=24)
        # session is still in WELCOME step (active), not COMPLETED/ERROR → not cleaned
        assert removed == 0
