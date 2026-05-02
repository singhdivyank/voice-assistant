"""Session workflow state management for CrewAI medical assistant"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.api.schemas import SessionState, ConversationTurnSchema
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
            WorkflowStep.DOCTOR_REVIEW: WorkflowStep.COMPLETED
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
                    # TODO- add patient name
                    "patient_age": session_state.patient_age,
                    "patient_gender": session_state.patient_gender,
                    "language": session_state.language
                }
            }
            self.workflow_history[session_id] = []
            self._track_step(session_id, None, WorkflowStep.WELCOME, "Session initialised")
            
            logger.info(f"Initialised workflow session {session_id}")

            return {
                "session_id": session_id,
                "current_step": WorkflowStep.WELCOME.value,
                "status": "initialised",
                "next_action": "generate_welcome_audio"
            }
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            raise DocJarvisError(f"Session initialisation failed: {str(e)}")
    
    def get_current_step(self, session_id: str) -> WorkflowStep:
        """get current workflow step for session"""

        if session_id not in self.active_sessions:
            raise DocJarvisError(f"Session {session_id} not found")

        return self.active_sessions[session_id]["current_step"]
    
    def _track_step(
        self, 
        session_id: str, 
        from_step: Optional[WorkflowStep], 
        to_step: WorkflowStep,
        description: str
    ) -> None:
        """Track workflow step transitions for monitoring"""

        if not session_id in self.active_sessions:
            return
        
        transition_record = {
            "from_step": from_step,
            "to_step": to_step,
            "timestamp": datetime.now(),
            "description": description
        }

        self.active_sessions[session_id]["step_history"].append(transition_record)

        if session_id not in self.workflow_history:
            self.workflow_history[session_id] = []
        
        self.workflow_history[session_id].append(transition_record)
