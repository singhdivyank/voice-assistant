from typing import Any, Dict, Optional

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
    ):
        """Handler for POST /sessions/"""
        return await self.service.create_session(
            patient_age=patient_age,
            patient_gender=patient_gender,
            language=language,
            initial_complaint=initial_complaint
        )
    
    async def chat_handler(
        self, 
        session_id: str, 
        user_input: str, 
        patient_info: Dict[str, Any]
    ):
        """Handler for POST /sessions/{session_id}/chat"""
        
        response = await self.service.coordinator.process_user_input(
            user_input=user_input,
            session_id=session_id,
            patient_info=patient_info
        )
        return {"reply": response}
    
    async def speak_recommendations_handler(
        self, 
        session_id: str, 
        text: str, 
        langauge: str
    ):
        """Handler for POST /sessions/{session_id}/speak-recommendations"""

        audio_base64 = await self.service.generate_speech_response(
            session_id=session_id,
            language=langauge,
            text=text
        )
        return {"audio": audio_base64}
