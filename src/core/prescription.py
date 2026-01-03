"""Prescription generation and management"""

import logging
from datetime import datetime
from pathlib import Path

from src.config.settings import PathConfig, PRESCRIPTION_TEMPLATE
from src.core.diagnosis import DiagnosisSession
from src.utils.exceptions import FileOperationError
from src.utils.file_handler import FileHandler


logger = logging.getLogger(__name__)


class PrescriptionGenerator:
    """Generates and manages prescription documents"""
    
    def __init__(self):
        self.paths = PathConfig()
        self.file_handler = FileHandler()
        self.no_conversation = "No follow-up questions recorded"

    def generate(self, session: DiagnosisSession) -> Path:
        """
        Generate prescription document from diagnosis session.

        Args:
            session: Complete diagnosis session

        Returns:
            Path to generated prescription file

        Raises:
            FileOperationError: if file generation fails
        """

        try:
            self.file_handler.safe_delete(self.paths.prescription_file)
            content = self.format_prescription(session)
            file_path = self.paths.prescription_file
            self.file_handler.safe_write(file_path, content)
            logger.info("Generated prescription: %s", file_path)
            return file_path
        except Exception as error:
            logger.error("Failed to generate prescription: %s", error)
            raise FileOperationError(f"Could not generate prescription: {error}") from error

    def format_prescription(self, session: DiagnosisSession) -> str:
        """
        Format prescription's content

        Args:
            session: Diagnosis session data

        Returns:
            Formatted prescription string
        """

        now = datetime.now()
        conversation_text = self.format_conversation(session)
        return PRESCRIPTION_TEMPLATE.format(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M"),
            age=session.patient.age,
            gender=session.patient.gender,
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
            lines.append(f"\nQuestion {i}: {turn.question}")
            lines.append(f"Response: {turn.answer}")

        return "\n".join(lines)

    def cleanup(self) -> None:
        """Remove any generated prescription files"""
        self.file_handler.safe_delete(self.paths.prescription_file)


class PrescriptionService:
    """
    High-level service for prescription management.

    Handles prescription generation, storage, and retrieval.
    """

    def __init__(self):
        self.generator = PrescriptionGenerator()

    def create_prescription(self, session: DiagnosisSession) -> Path:
        """
        Create a prescription from completed diagnosis session.

        Args:
            session: Completed diagnosis session

        Returns:
            Path to prescription file
        """
        return self.generator.generate(session)

    def get_prescription_path(self) -> Path:
        """
        Get the path to current prescription file.
        """

        return self.generator.paths.prescription_file
