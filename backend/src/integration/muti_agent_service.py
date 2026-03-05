import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException

from src.config.monitoring import telemetry
from src.core.multi_agent.coordinator.agent_coordinator import AgentCoordinator

logger = logging.getLogger(__name__)


class MultiAgentService:
    """Service layer that bridges FastAPI routes with the multi-agent system."""

    def __init__(self):
        self.coordinator = AgentCoordinator()
    
    async def create_session(
        self, 
        patient_age: int, 
        patient_gender: str, 
        language: str,
        initial_complaint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new consultation session using the multi-agent system"""

        session_id = str(uuid.uuid4())

        with telemetry.span("create_session_multi_agent", {"session_id": session_id}):
            patient_info = {
            "age": patient_age,
            "gender": patient_gender,
            "complaint": initial_complaint or "No initial complaint provided",
            "language": language
        }

        try:
            response_text = await self.coordinator.process_user_input(
                user_input=initial_complaint,
                session_id=session_id,
                patient_info=patient_info
            )

            return {
                "session_id": session_id,
                "status": "active",
                "reply": response_text
            }
        except Exception as e:
            logger.error("Failed to bridge session creation to coordinator: %s", e)
            raise HTTPException(status_code=500, detail="Agentic workflow failed to start")
    
    async def transcribe_and_respond(
        self, 
        session_id: str, 
        audio_file_path: Path,
        patient_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process audio input using STT and generate next response"""
        
        try:
            with telemetry.span("transcribe_and_respond_multi_agent", {"session_id": session_id}):
                prompt = f"I have provided an audio update at {audio_file_path}. Please transcribe and respond."
        
            return await self.coordinator.process_user_input(
                user_input=prompt,
                session_id=session_id,
                patient_info=patient_info
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Transcribe and respond failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
    
    async def generate_speech_response(
        self, 
        session_id: str,
        language: str,
        text: Optional[str] = None
    ) -> str:
        """Generate TTS audio for recommendations"""

        from src.core.multi_agent.tools.voice_tools import generate_voice_response
        
        try:
            return await generate_voice_response(
                text=text, 
                audio_path=f"res_{session_id}.mp3", 
                language_code=language
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("TTS generation failed: %s", e)
            raise HTTPException(status_code=500, detail=f"TTS genration failed: {e}")
