"""Session workflow state management for CrewAI medical assistant"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.api.schemas import SessionState
from src.utils.consts import WorkflowStep
from src.utils.exceptions import DocJarvisError

logger = logging.getLogger(__name__)


class SessionWorkflowManager:
    """Manages workflow state"""

    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.workflow_history: Dict[str, List[Dict[str, Any]]] = {}
        self.step_progression = {
            WorkflowStep.WELCOME: WorkflowStep.INITIAL_SYMPTOM,
            WorkflowStep.INITIAL_SYMPTOM: WorkflowStep.QUESTIONS_GENERATED,
            WorkflowStep.QUESTIONS_GENERATED: WorkflowStep.QA_IN_PROGRESS,
            WorkflowStep.QA_IN_PROGRESS: WorkflowStep.QA_COMPLETE,
            WorkflowStep.QA_COMPLETE: WorkflowStep.RECOMMENDATIONS_GENERATED,
            WorkflowStep.RECOMMENDATIONS_GENERATED: WorkflowStep.AUDIO_GENERATED,
            WorkflowStep.AUDIO_GENERATED: WorkflowStep.PRESCRIPTION_SENT,
            WorkflowStep.PRESCRIPTION_SENT: WorkflowStep.DOCTOR_REVIEW,
            WorkflowStep.DOCTOR_REVIEW: WorkflowStep.COMPLETED,
        }

    def initialize_sessions(self, session_state: SessionState) -> Dict[str, Any]:
        """Initialise new workflow session"""

        try:
            session_id = session_state.session_id
            self.active_sessions[session_id] = {
                "session_id": session_id,
                "current_step": WorkflowStep.WELCOME,
                "session_state": session_state,
                "created_at": datetime.now(),
                "last_updated": datetime.now(),
                "step_history": [],
                "errors": [],
                "metadata": {
                    "patient_name": session_state.patient_name,
                    "patient_email": session_state.patient_email,
                    "patient_age": session_state.patient_age,
                    "patient_gender": session_state.patient_gender,
                    "language": session_state.language,
                },
            }
            self.workflow_history[session_id] = []
            self._track_step(
                session_id, None, WorkflowStep.WELCOME, "Session initialised"
            )

            logger.info("Initialised workflow session %s", session_id)

            return {
                "session_id": session_id,
                "current_step": WorkflowStep.WELCOME.value,
                "status": "initialised",
                "next_action": "generate_welcome_audio",
            }
        except Exception as e:
            logger.error("Failed to initialize session: %s", str(e))
            raise DocJarvisError(f"Session initialisation failed: {str(e)}") from e

    def get_current_step(self, session_id: str) -> WorkflowStep:
        """get current workflow step for session"""

        if session_id not in self.active_sessions:
            raise DocJarvisError(f"Session {session_id} not found")

        return self.active_sessions[session_id]["current_step"]

    def advance_to_next_step(self, session_id: str) -> Dict[str, Any]:
        """Advance workflow to next state"""

        try:
            if session_id not in self.active_sessions:
                raise DocJarvisError(f"Session {session_id} not found")

            current_step = self.active_sessions[session_id]["current_step"]
            next_step = self._determine_next_step(session_id, current_step)
            self.active_sessions[session_id]["current_step"] = next_step
            self.active_sessions[session_id]["last_updated"] = datetime.now()
            self._track_step(
                session_id,
                current_step,
                next_step,
                f"Advanced from {current_step.value} to {next_step.value}",
            )

            # Get next action
            next_action = self._get_next_action(next_step)

            logger.info(
                "Session %s advanced: %s → %s",
                session_id,
                current_step.value,
                next_step.value,
            )

            return {
                "session_id": session_id,
                "previous_step": current_step.value,
                "current_step": next_step.value,
                "next_action": next_action,
                "status": "advanced",
            }
        except Exception as e:
            logger.error("Failed to advance workflow: %s", str(e))
            self._handle_workflow_error(session_id, str(e))
            raise DocJarvisError(f"Workflow advancement failed: {str(e)}") from e

    def update_session_state(
        self, session_id: str, session_state: SessionState
    ) -> None:
        """Update session state data"""
        try:
            if session_id not in self.active_sessions:
                raise DocJarvisError(f"Session {session_id} not found")

            self.active_sessions[session_id]["session_state"] = session_state
            self.active_sessions[session_id]["last_updated"] = datetime.now()

            logger.debug("Updated session state for %s", session_id)

        except Exception as e:
            logger.error("Failed to update session state: %s", str(e))
            raise DocJarvisError(f"Session state update failed: {str(e)}") from e

    def get_session_state(self, session_id: str) -> SessionState:
        """Get current session state"""
        if session_id not in self.active_sessions:
            raise DocJarvisError(f"Session {session_id} not found")

        return self.active_sessions[session_id]["session_state"]

    def get_session_progress(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session progress information"""
        try:
            if session_id not in self.active_sessions:
                raise DocJarvisError(f"Session {session_id} not found")

            session_data = self.active_sessions[session_id]
            session_state = session_data["session_state"]

            # Calculate progress percentage
            step_order = list(WorkflowStep)
            current_step_index = step_order.index(session_data["current_step"])
            progress_percentage = (current_step_index / len(step_order)) * 100

            # Check Q&A progress
            qa_progress = self._calculate_qa_progress(session_state)

            return {
                "session_id": session_id,
                "current_step": session_data["current_step"].value,
                "progress_percentage": round(progress_percentage, 1),
                "created_at": session_data["created_at"].isoformat(),
                "last_updated": session_data["last_updated"].isoformat(),
                "qa_progress": qa_progress,
                "step_history": [
                    {
                        "step": entry["to_step"].value if entry["to_step"] else None,
                        "timestamp": entry["timestamp"].isoformat(),
                        "description": entry["description"],
                    }
                    for entry in session_data["step_history"][-5:]  # Last 5 steps
                ],
                "errors": session_data["errors"],
                "next_action": self._get_next_action(session_data["current_step"]),
            }

        except Exception as e:
            logger.error("Failed to get session progress: %s", str(e))
            raise DocJarvisError(f"Session progress retrieval failed: {str(e)}") from e

    def mark_session_complete(self, session_id: str) -> Dict[str, Any]:
        """Mark session as completed"""
        try:
            if session_id not in self.active_sessions:
                raise DocJarvisError(f"Session {session_id} not found")

            self.active_sessions[session_id]["current_step"] = WorkflowStep.COMPLETED
            self.active_sessions[session_id]["completed_at"] = datetime.now()

            self._track_step(
                session_id,
                self.active_sessions[session_id]["current_step"],
                WorkflowStep.COMPLETED,
                "Session marked as completed",
            )

            logger.info("Session %s marked as completed", session_id)

            return {
                "session_id": session_id,
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to mark session complete: %s", str(e))
            raise DocJarvisError(f"Session completion failed: {str(e)}") from e

    def _determine_next_step(
        self, session_id: str, current_step: WorkflowStep
    ) -> WorkflowStep:
        """Determine the next workflow step based on current state"""

        # Special handling for Q&A progression
        if current_step == WorkflowStep.QUESTIONS_GENERATED:
            return WorkflowStep.QA_IN_PROGRESS

        if current_step == WorkflowStep.QA_IN_PROGRESS:
            session_state = self.get_session_state(session_id)
            qa_progress = self._calculate_qa_progress(session_state)

            if qa_progress["all_answered"]:
                return WorkflowStep.QA_COMPLETE

            # Stay in Q&A
            return WorkflowStep.QA_IN_PROGRESS

        # Default progression
        return self.step_progression.get(current_step, WorkflowStep.ERROR)

    def _calculate_qa_progress(self, session_state: SessionState) -> Dict[str, Any]:
        """Calculate Q&A progress"""
        total_questions = len(session_state.questions)

        if total_questions == 0:
            return {
                "total_questions": 0,
                "answered_questions": 0,
                "current_question_index": 0,
                "all_answered": False,
            }

        answered_count = sum(
            1
            for turn in session_state.conversation[:total_questions]
            if turn.answer and turn.answer.strip()
        )

        return {
            "total_questions": total_questions,
            "answered_questions": answered_count,
            "current_question_index": answered_count,
            "all_answered": answered_count >= total_questions,
            "completion_percentage": (answered_count / total_questions) * 100,
        }

    def _get_next_action(self, step: WorkflowStep) -> str:
        """Get the next recommended action for a workflow step"""
        action_map = {
            WorkflowStep.WELCOME: "generate_welcome_audio",
            WorkflowStep.INITIAL_SYMPTOM: "process_initial_symptom",
            WorkflowStep.QUESTIONS_GENERATED: "start_qa_conversation",
            WorkflowStep.QA_IN_PROGRESS: "continue_qa_conversation",
            WorkflowStep.QA_COMPLETE: "generate_recommendations",
            WorkflowStep.RECOMMENDATIONS_GENERATED: "generate_audio",
            WorkflowStep.AUDIO_GENERATED: "generate_prescription",
            WorkflowStep.PRESCRIPTION_SENT: "wait_for_doctor_review",
            WorkflowStep.DOCTOR_REVIEW: "process_doctor_response",
            WorkflowStep.COMPLETED: "consultation_complete",
            WorkflowStep.ERROR: "handle_error",
        }
        return action_map.get(step, "unknown_action")

    def _handle_workflow_error(self, session_id: str, error_message: str) -> None:
        """Handle workflow errors"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["current_step"] = WorkflowStep.ERROR
            self.active_sessions[session_id]["errors"].append(
                {"timestamp": datetime.now(), "error": error_message}
            )

            self._track_step(
                session_id,
                self.active_sessions[session_id]["current_step"],
                WorkflowStep.ERROR,
                f"Error occurred: {error_message}",
            )

    def get_all_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active sessions (for monitoring/debugging)"""
        return {
            session_id: {
                "current_step": data["current_step"].value,
                "created_at": data["created_at"].isoformat(),
                "last_updated": data["last_updated"].isoformat(),
                "metadata": data["metadata"],
            }
            for session_id, data in self.active_sessions.items()
        }

    def cleanup_completed_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up old completed sessions"""
        current_time = datetime.now()
        sessions_to_remove = []

        for session_id, data in self.active_sessions.items():
            if data["current_step"] in [WorkflowStep.COMPLETED, WorkflowStep.ERROR]:
                age_hours = (current_time - data["last_updated"]).total_seconds() / 3600
                if age_hours > max_age_hours:
                    sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
            # Keep workflow history for analytics

        logger.info("Cleaned up %d old sessions", len(sessions_to_remove))
        return len(sessions_to_remove)

    def _track_step(
        self,
        session_id: str,
        from_step: Optional[WorkflowStep],
        to_step: WorkflowStep,
        description: str,
    ) -> None:
        """Track workflow step transitions for monitoring"""

        if not session_id in self.active_sessions:
            return

        transition_record = {
            "from_step": from_step,
            "to_step": to_step,
            "timestamp": datetime.now(),
            "description": description,
        }

        self.active_sessions[session_id]["step_history"].append(transition_record)

        if session_id not in self.workflow_history:
            self.workflow_history[session_id] = []

        self.workflow_history[session_id].append(transition_record)
