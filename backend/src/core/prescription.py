"""Prescription generation and management"""

import logging
from datetime import datetime
from pathlib import Path

from src.config.monitoring import telemetry
from src.config.settings import get_settings
from src.core.diagnosis import DiagnosisSession
from src.utils.consts import PRESCRIPTION_TEMPLATE
from src.utils.exceptions import FileOperationError
from src.utils.file_handler import FileHandler

logger = logging.getLogger(__name__)
settings = get_settings()


class PrescriptionGenerator:
    """Generates and manages prescription documents"""

    def __init__(self):
        self.file_handler = FileHandler()
        self.output_dir = settings.prescription_dir
        self.no_conversation = "No follow-up questions recorded"

    def generate(self, session: DiagnosisSession) -> Path:
        """Generate prescription document from diagnosis session."""

        with telemetry.span("generateprescription", {"session_id": session.session_id}):
            try:
                file_path = self.output_dir / f"prescription_{session.session_id}.txt"
                self.file_handler.safe_delete(file_path)
                content = self.format_prescription(session)
                self.file_handler.safe_write(file_path, content)
                logger.info("Generated prescription: %s", file_path)
                return file_path
            except Exception as error:
                logger.error("Failed to generate prescription: %s", error)
                raise FileOperationError(
                    f"Could not generate prescription: {error}"
                ) from error
    
    def format_prescription(self, session: DiagnosisSession) -> str:
        """Format prescription's content."""

        now = datetime.now()
        conversation_text = self.format_conversation(session)
        return PRESCRIPTION_TEMPLATE.format(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M"),
            age=session.patient.age,
            gender=session.patient.gender.value,
            initial_complaint=session.initial_complaint,
            conversation=conversation_text,
            medication=session.medication or "No recommendations generated",
        )

    def format_conversation(self, session: DiagnosisSession) -> str:
        """Format the conversation for the prescription"""

        if not session.conversation:
            return self.no_conversation

        lines = []
        for i, turn in enumerate(session.conversation, 1):
            lines.append(f"\nQuestion {i}: {turn.question}\nResponse: {turn.answer}")

        return "\n".join(lines)

    def cleanup(self, session_id: str) -> None:
        """Remove prescription file for a session."""
        
        file_path = self.output_dir / f"prescription_{session_id}.txt"
        self.file_handler.safe_delete(file_path)


class PrescriptionService:
    """High-level service for prescription management."""

    def __init__(self):
        self.generator = PrescriptionGenerator()

    def create_prescription(self, session: DiagnosisSession) -> Path:
        """Create a prescription from completed diagnosis session."""
        return self.generator.generate(session)

    def get_prescription_path(self, session_id: str) -> Path:
        """Get the path to current prescription file."""

        return settings.prescription_dir / f"prescription_{session_id}.txt"
    
    def delete_prescription(self, session_id: str) -> None:
        """Delete a prescription file."""

        self.generator.cleanup(session_id)
