import logging
from datetime import datetime

from .base_agent import BaseAgent
from src.config.settings import get_settings
from src.core.multi_agent.workflow.state_manager import AgentExecutionState

logger = logging.getLogger(__name__)
settings = get_settings()


class PrescriptionAgent(BaseAgent):
    """Prescription Agent"""

    def __init__(self):
        super().__init__('prescription_agent')
        self.output_dir = settings.prescription_dir
    
    async def _execute_logic(self, state: AgentExecutionState) -> AgentExecutionState:
        if not state.final_diagnosis:
            logger.warning("No diagnosis available for prescription generation")
            return state
        
        from src.config.monitoring import telemetry
        from src.utils.file_handler import FileHandler
        from src.utils.exceptions import FileOperationError

        file_handler = FileHandler()
        
        with telemetry.span("generateprescription", {"session_id": state.session_id}):
            prescription_path = self.output_dir / f"prescription_{state.session_id}.txt"
            
            try:
                file_handler.safe_delete(prescription_path)
                content = self.format_prescription(state)
                file_handler.safe_write(prescription_path, content)
                logger.info("Generated prescription: %s", prescription_path)
                
                state.prescription_path = prescription_path
                state.agent_results["prescription"] = {
                    "recommendations_generated": True,
                    "prescription_file_created": True,
                    "prescription_path": str(prescription_path)
                }
            
                logger.info("Prescription generated: %s", prescription_path)
            except Exception as error:
                logger.error("Failed to generate prescription: %s", error)
                raise FileOperationError(
                    f"Could not generate prescription: {error}"
                ) from error

        return state

    def format_prescription(self, state: AgentExecutionState) -> str:
        """Format prescription's content."""

        if not state.medication_recommendations:
            logger.info("No medications generated. Generating prescripion with custom text")
        
        from src.utils.consts import PRESCRIPTION_TEMPLATE

        now = datetime.now()
        conversation_text = self.format_conversation(state)
        return PRESCRIPTION_TEMPLATE.format(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M"),
            age=state.patient.age,
            gender=state.patient.gender.value,
            initial_complaint=" ".join(state.transcribed_texts[0]),
            conversation=conversation_text,
            medication=state.medication_recommendations or "No recommendations generated",
        )

    def format_conversation(self, state: AgentExecutionState) -> str:
        """Format the conversation for the prescription"""

        if not state.conversation_complete:
            return "No follow-up questions recorded"
        
        from src.utils.consts import ConversationTurn

        lines = []
        for _, (question, answer) in enumerate(zip(state.questions, state.answers), 1):
            lines.append(ConversationTurn(question=question, answer=answer))

        return "\n".join(lines)
