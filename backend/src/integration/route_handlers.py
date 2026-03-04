from pathlib import Path
from typing import Optional

from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse

from src.services.session_store import SessionStore
from .muti_agent_service import MultiAgentService


class MultiAgentRouteHandlers:
    """Route handlers that use multi-agent system while maintaining API compatibility"""

    def __init__(self):
        self.service = MultiAgentService()
    
    async def create_session_handler(
        self, 
        patient_age: int,
        patient_gender: str,
        language="en",
        initial_complaint: Optional[str] = None,
        session_store: Optional[SessionStore] = None
    ):
        """Handler for POST /sessions/"""
        return await self.service.create_session(
            patient_age=patient_age,
            patient_gender=patient_gender,
            language=language,
            initial_complaint=initial_complaint,
            session_store=session_store
        )
    
    async def transcribe_and_respond_handler(
        self,
        session_id: str,
        audio_file_path: Path,
        question_index: int = 0,
        session_store: Optional[SessionStore] = None
    ):
        """Handler for POST /sessions/{session_id}/transcribe"""

        return await self.service.transcribe_and_respond(
            session_id=session_id,
            audio_file_path=audio_file_path,
            question_index=question_index,
            session_store=session_store
        )
    
    async def complete_session_handler(
        self,
        session_id: str,
        session_store: Optional[SessionStore] = None
    ):
        """Handler for POST /sessions/{session_id}/complete"""

        return await self.service.complete_session(
            session_id=session_id, 
            session_store=session_store
        )

    async def complete_session_stream_handler(
        self, 
        session_id: str, 
        session_store: Optional[SessionStore] = None
    ):
        """Handler for POST /sessions/{session_id}/complete/stream"""

        return StreamingResponse(
            self.service.complete_session_stream(
                session_id=session_id, session_store=session_store
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    
    async def speak_recommendations_handler(self, session_id: str):
        """Handler for POST /sessions/{session_id}/speak-recommendations"""

        audio_base64 = await self.service.generate_speech_response(session_id=session_id)
        return {"audio": audio_base64}
    
    async def get_session_handler(self, session_id: str):
        """Handler for GET /sessions/{session_id}"""

        session_data = self.service.get_session_state(session_id=session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session_data
