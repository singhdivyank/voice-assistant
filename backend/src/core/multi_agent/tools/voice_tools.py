"""Tools for stt, tts, and translation operations"""

import base64

from langchain.tools import tool

from src.utils.consts import Language

@tool
async def transcribe_audio(audio_path: str, language_code: str):
    """convert patient audio recording into English"""

    try:

        from src.services.speech import SpeechRecognizer
        from src.services.translation import TranslationService
        
        user_lang = Language.from_code(language_code)
        recognizer = SpeechRecognizer(user_lang)
        text = recognizer.transcribe_from_file(audio_path)
        
        if user_lang != Language.ENGLISH:
            translator = TranslationService(user_lang)
            return translator.to_english(text)
        
        return text
    except Exception:
        raise

@tool
async def generate_voice_response(
    text: str, 
    audio_path: str, 
    language_code: str
) -> str:
    """convert message to audio file"""

    try:
    
        from src.services.speech import TextToSpeech
    
        target_language = Language.from_code(language_code)
        tts = TextToSpeech(target_language)
        audio_bytes = await tts.synthesize(text)
        audio_path.write_bytes(audio_bytes)
        audio_bytes = base64.b64encode(audio_bytes).decode('utf-8')
    except Exception:
        raise
