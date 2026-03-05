"""Tools for prescription generation"""

import logging
from datetime import datetime

from langchain.tools import tool

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@tool
def create_prescription(
    session_id: str, 
    medications: str, 
    patient_info: dict
) -> str:

    from src.utils.file_handler import FileHandler
    from src.utils.consts import PRESCRIPTION_TEMPLATE
    from src.utils.exceptions import FileOperationError

    try:
        if not medications:
            logger.info("No medications generated. Generating prescripion with custom text")

        file_handler = FileHandler()
        prescription_path = settings.prescription_dir / f"prescription_{session_id}.txt"
        now = datetime.now()
        file_handler.safe_delete(prescription_path)

        content = PRESCRIPTION_TEMPLATE.format(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M"),
            age=patient_info.get("age"),
            gender=patient_info.get("gender"),
            initial_complaint=patient_info.get("complaint", "N/A"),
            conversation="See session history",
            medication=medications or "No recommendations generated",
        )

        file_handler.safe_write(prescription_path, content)
        logger.info("Prescription generated: %s", prescription_path)
        return str(prescription_path)
    except Exception as error:
        logger.error("Failed to generate prescription: %s", error)
        raise FileOperationError(
            f"Could not generate prescription: {error}"
        ) from error

@tool
async def draft_prescription_email(recipient_email: str, prescription_content: str) -> str:
    """
    Prepares a draft email for the patient with their prescription details.
    Note: In the future, this will connect to the Gmail MCP server.
    """
    # For now, this acts as a placeholder for your internal logic
    return f"Email draft created for {recipient_email}."
