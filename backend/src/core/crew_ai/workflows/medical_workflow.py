"""Sequential medical workflow"""

import logging
from typing import Any, Dict

from crewai import Task, Crew

from .task_descriptions import (
    INTRO_TASK_DESCRIPTION
)
from src.core.crew_ai.agents.medical_agents import (
    speech_processor, translator, qna_generator,
    medication, prescription_specialist
)
from src.core.crew_ai.tools.medical_tools import (
    SpeechToTextTool, TextToSpeechTool,
    TranslationTool, QuestionGenerationTool,
    MedicationTool, PrescriptionTool
)
from src.utils.consts import MESSAGES
from src.utils.exceptions import DocJarvisError

logger = logging.getLogger(__name__)


class MedicalWorkflow:
    """Handle sequential medical consultation workflow"""

    def __init__(self):
        self.agents = self._initialise_agents()
        self.tools = self._initialise_tools()
    
    def _initialise_agents(self) -> Dict[str, Any]:
        """Initialise all agents"""
        return {
            "speech_agent": speech_processor, 
            "translation_agent": translator, 
            "qna_agent": qna_generator,
            "medication_agent": medication, 
            "prescription_agent": prescription_specialist
        }
    
    def _initialise_tools(self) -> Dict[str, Any]:
        """Initialise all tools"""
        return {
            "stt_tool": SpeechToTextTool, 
            "tts_tool": TextToSpeechTool,
            "translation_tool": TranslationTool, 
            "qna_tool": QuestionGenerationTool,
            "medication_tool": MedicationTool, 
            "prescription_tool": PrescriptionTool
        }
    
    async def generate_welcome_audio(self, language: str = "en") -> Dict[str, Any]:
        """Generate welcome message audio"""

        welcome_message = MESSAGES['intro'] + MESSAGES['instruction']
        welcome_task = Task(
            description=INTRO_TASK_DESCRIPTION.format(
                language=language,
                welcome_message=welcome_message,
                expected_output="Base64 encoded audio of welcome message",
                agent=self.agents['speech_agent']
            )
        )
        crew = Crew(
            agents=[self.agents['speech_agent']],
            tasks=[welcome_task],
            verbose=True
        )

        try:
            result = crew.kickoff()
            audio_base64 = self._extract_audio_from_result(str(result))
            logger.info("Welcome audio generated successfully")
            return {
                "status": "success",
                "audio_base64": audio_base64,
                "message": welcome_message,
                "step": "welcome_message_generation"
            }
        except Exception as e:
            logger.error(f"Failed to generate welcome audio: {e}")
            raise DocJarvisError(f"Welcome audio generation failed: {str(e)}")
