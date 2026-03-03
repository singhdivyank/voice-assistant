import logging

from.base_agent import BaseAgent
from src.core.multi_agent.workflow import AgentExecutionState

logger = logging.getLogger(__name__)


class STTAgent(BaseAgent):
    """Speech-to-Text Agent"""

    def __init__(self):
        super().__init__("stt")
    
    async def execute_logic(self, state: AgentExecutionState) -> AgentExecutionState:
        """Process audio files to text"""

        if not state.audio_files:
            logger.warning("No audio files to process")
            return state
        
        from src.services.speech import SpeechRecognizer
        from src.utils.consts import Language

        recognizer = SpeechRecognizer(Language.from_code(state.source_language.value))
        transcribed_texts = []

        for audio_file in state.audio_files:
            try:
                text = recognizer.transcribe_from_file(audio_file)
                transcribed_texts.append(text)
                logger.info("Transcribed audio: %s...", text[:50])
            except Exception as e:
                logger.error("STT failed for file %s: %s", audio_file, e)
                transcribed_texts.append("")
        
        state.transcribed_texts = transcribed_texts
        state.agent_results["stt"] = {
            "text": transcribed_texts,
            "processed_files": len(state.audio_files)
        }
        
        return state
