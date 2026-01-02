"""Speech services for audio input/output"""

import logging
from typing import Optional

import playsound
import speech_recognition as sr
from gtts import gTTS

from src.config.settings import Language, PathConfig
from src.utils.dataclasses import SpeechToTextServive
from src.utils.exceptions import NetworkError, TextToSpeechError, TranscriptionError
from src.utils.file_handler import FileHandler


logger = logging.getLogger(__name__)


class SpeechRecognizer(SpeechToTextServive):
    """Google Speech Recognizer implementation"""

    def __init__(self, language: Language):
        self.language=language
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
    
    def transcribe(self, timeout: Optional[float] = None) -> str:
        """
        Convert audio from microphone to text.

        Args:
            timeout: Maximum seconds to wait for audio.
        
        Returns:
            Transcribed text
        
        Raises:
            TranscriptionError: If transcription fails
            NetworkError: If there is no internet connection
        """

        try:
            with self.mic as source:
                logger.info("Listening for audio input...")
                self.recognizer.adjust_for_ambient_noise(source=source)
                audio = self.recognizer.listen(source=source, timeout=timeout)
            
            txt = self.recognizer.recognize_google(
                audio_data=audio, 
                language=self.language
            )
            logger.info(f"Transcribed: {txt[:50]} ...")
            return txt
        except sr.RequestError as e:
            logger.error(f"Network error during transcription: {e}")
            raise NetworkError("No internet connection for speech recognition")
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            raise TranscriptionError("Could not understand audio")
        except sr.WaitTimeoutError:
            logger.warning("Listening timed out")
            raise TranscriptionError("Listening timed out")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise TranscriptionError(f"Speech recognition failed: {e}")


class TextToSpeech:
    """Google Text-to-Speech implementation"""
    def __init__(self, language: Language, path: PathConfig):
        self.language = language
        self.audio_path = path.audio_file
        self.file_handler = FileHandler()
    
    def speak(self, text: str, slow: bool = False) -> None:
        """
        Convert text to speech and play it.

        Args:
            text: Text to speak
            slow: If True, speak slowly
        
        Raises:
            TextToSpeechError: if TTS fails
        """

        if not text or not text.strip():
            logger.warning("Empty text provided by TTS")
            return
        
        try:
            self.cleanup()
            audio = gTTS(text=text, lang=self.language.value, slow=slow)
            audio.save(savefile=str(self.audio_path))   
            logger.debug(f"Generated audio for: {text[:50]}")
            playsound.playsound(str(self.audio_path))
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            raise TextToSpeechError(f"Text-to-speech failed: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Delete audio file"""

        try:
            self.file_handler.safe_delete(self.audio_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup audio file: {e}")
    

class SpeechService:
    """
    Unified speech service combining STT and TTS.

    Provides a single interface for all speech operations.
    """

    def __init__(self, language: Language, paths: PathConfig):
        self.language = language
        self._stt = SpeechRecognizer(language=language)
        self._tss = TextToSpeech(language=language, path=paths)
    
    def listen(self, timeout: Optional[float] = None) -> str:
        """Listen and transcribe user speech"""
        return self._stt.transcribe(timeout=timeout)

    def speak(self, text: str, slow: bool = False) -> None:
        """Speak out the text to user"""
        return self._tss.speak(text=text, slow=slow)
