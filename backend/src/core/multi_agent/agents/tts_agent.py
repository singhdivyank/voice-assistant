import base64
import logging

from .base_agent import BaseAgent
from src.config.settings import get_settings
from src.core.multi_agent.workflow.state_manager import AgentExecutionState

logger = logging.getLogger(__name__)
settings = get_settings()


class TTSAgent(BaseAgent):
    """Text-to-Speech Agent"""

    def __init__(self):
        super().__init__("tts")
    
    async def _execute_logic(self, state: AgentExecutionState) -> AgentExecutionState:
        """Generate audio responses"""

        from src.services.speech import TextToSpeech

        language = state.source_language
        tts = TextToSpeech(language)
        audio_files = []

        current_idx = len(state.answers)
        if current_idx - len(state.questions) < 0:
            question_text = state.translated_content.get("questions_to_user", state.questions)[current_idx]
            
            try:
                audio_bytes = await tts.synthesize(question_text)
                audio_path = settings.audio_dir / f"question_{current_idx}_{state.execution_id}.mp3"
                audio_path.write_bytes(audio_bytes)
                audio_files.append(audio_path)
                state.response_audio = base64.b64encode(audio_bytes).decode('utf-8')
            except Exception as e:
                logger.error("TTS failed for question: %s", e)
        
        if state.medication_recommendations and state.conversation_complete:
            recommendations_text = state.translated_context.get("recommendations_to_user", state.medication_recommendations)

            try:
                audio_bytes = await tts.synthesize(recommendations_text)
                audio_path = settings.audio_dir / f"recommendations_{state.execution_id}.mp3"
                audio_path.write_bytes(audio_bytes)
                audio_files.append(audio_path)
                state.response_audio = base64.b64encode(audio_bytes).decode('utf-8')
            except Exception as e:
                logger.error("TTS failed for recommendations: %s", e)
        
        state.tts_files = audio_files
        state.agent_results["tts"] = {
            "audio_files_generated": len(audio_files),
            "has_response_audio": bool(state.response_audio)
        }

        return state
