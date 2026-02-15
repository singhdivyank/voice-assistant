"""Speech services for audio input/output with monitoring."""

import logging
import subprocess
import asyncio
from pathlib import Path
from typing import Optional
import base64
import tempfile

import speech_recognition as sr
from gtts import gTTS

from src.config.settings import get_settings
from src.config.monitoring import telemetry, timed_operation
from src.utils.consts import (
    Language, SpeechToTextService, TextToSpeechService, Platform
)
from src.utils.exceptions import (
    AudioError, NetworkError, TextToSpeechError, TranscriptionError
)
from src.utils.file_handler import FileHandler


logger = logging.getLogger(__name__)
settings = get_settings()


class SpeechRecognizer(SpeechToTextService):
    """Google Speech Recognizer implementation"""

    def __init__(self, language: Language):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()

    @timed_operation("speech_to_text")
    def transcribe(self, timeout: Optional[float] = None) -> str:
        """Convert audio from microphone to text"""

        telemetry.increment_counter("speech_requests", attributes={"type": "stt"})

        try:
            with self.mic as source:
                logger.info("Listening for audio input...")
                self.recognizer.adjust_for_ambient_noise(source=source)
                audio = self.recognizer.listen(source=source, timeout=timeout)

            txt = self.recognizer.recognize_google(
                audio_data=audio, language=self.language.value
            )
            logger.info("Transcribed: %s ...", txt[:50] if len(txt) > 50 else txt)
            return txt
        except sr.RequestError as e:
            logger.error("Network error during transcription: %s", e)
            telemetry.increment_counter("speech_errors", attributes={"type": "network"})
            raise NetworkError("No internet connection for speech recognition") from e
        except sr.UnknownValueError as e:
            logger.warning("Could not understand audio")
            telemetry.increment_counter("speech_errors", attributes={"type": "unknown_value"})
            raise TranscriptionError("Could not understand audio") from e
        except sr.WaitTimeoutError as e:
            logger.warning("Listening timed out")
            telemetry.increment_counter("speech_errors", attributes={"type": "unkown"})
            raise TranscriptionError("Listening timed out") from e
        except (ValueError, RuntimeError) as e:
            logger.error("Transcription failed: %s", e)
            telemetry.increment_counter("speech_errors", attributes={"type": "unknown"})
            raise TranscriptionError(f"Speech recognition failed: {e}") from e
    
    async def transcribe_async(self, audio_data: bytes) -> str:
        """Transcribe audio data asynchronously"""
        
        telemetry.increment_counter("speech_requests", attributes={"type": "stt_async"})

        try:
            audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None,
                lambda: self.recognizer.recognize_google(
                    audio_data=audio, language=self.language.value
                )
            )
            logger.info("Async transcribed: %s...", text[:50] if len(text) > 50 else text)
            return text
        except sr.RequestError as e:
            logger.error("Network error during async transcription: %s", e)
            raise NetworkError("No internet connection for speech recognition") from e
        except sr.UnknownValueError as e:
            logger.warning("Could not understand audio")
            raise TranscriptionError("Could not understand audio") from e
        except (ValueError, RuntimeError) as e:
            logger.error("Async transcription failed: %s", e)
            raise TranscriptionError(f"Speech recognition failed: {e}") from e
    
    def transcribe_from_file(self, file_path: Path) -> str:
        """Transcribe audio from a file"""
        
        telemetry.increment_counter("speech_requests", attributes={"type": "stt_file"})

        try:
            with sr.AudioFile(str(file_path)) as source:
                audio = self.recognizer.record(source)
            
            text = self.recognizer.recognize_google(
                audio_data=audio, language=self.language.value
            )
            logger.info("File transcribed: %s...", text[:50] if len(text) > 50 else 0)
            return text
        except sr.RequestError as e:
            raise NetworkError("No internet connection for speech recognition") from e
        except sr.UnknownValueError as e:
            raise TranscriptionError("Could not understand audio") from e
        except FileNotFoundError as e:
            raise AudioError(f"Audio file not found: {file_path}") from e
        except (ValueError, RuntimeError) as e:
            raise TranscriptionError(f"File transcription failed: {e}") from e


class TextToSpeech(TextToSpeechService):
    """Google Text-to-Speech implementation"""

    def __init__(self, language: Language):
        self.language = language
        self.file_handler = FileHandler()
        self.audio_dir = settings.audio_dir
        self.players = ["mpg123", "mpg321", "ffplay", "aplay"]
    
    def _get_temp_audio_path(self) -> Path:
        """Get temporary audio file path"""
        return self.audio_dir / f"tts_{id(self)}.mp3"

    def _play_audio_file(self, file_path: Path) -> None:
        """Play an audio file using platform-appropriate method."""

        try:
            if Platform.is_mac():
                subprocess.run(["afplay", str(file_path)], check=True, capture_output=True)
            elif Platform.is_windows():
                subprocess.run(
                    [
                        "powershell",
                        "-c",
                        f"New-Object Media.SoundPlayer '{file_path}').PlaySync();",
                    ],
                    check=True,
                    capture_output=True,
                )
            else:
                self._play_linux(file_path=file_path)
        except subprocess.CalledProcessError as e:
            raise TextToSpeechError(f"Audio playback failed: {e}") from e
        except FileNotFoundError as e:
            raise TextToSpeechError(f"Audio player not found: {e}") from e

    def _play_linux(self, file_path: Path) -> None:
        """Play audio on Linux system"""

        for player in self.players:
            try:
                cmd = [player]
                if player == "ffplay":
                    cmd.extend(["-nodisp", "-autoexit", "-loglevel", "quiet"])
                cmd.append(file_path)

                subprocess.run(cmd, check=True, capture_output=True)
                return
            except FileNotFoundError:
                continue
            except subprocess.CalledProcessError:
                continue
        
        raise TextToSpeechError("No audio player found. Install mpg123: sudo apt-get install mpg123")

    @timed_operation("text_to_speech")
    def speak(self, text: str, slow: bool = False) -> None:
        """Convert text to speech and play it"""

        if not text or not text.strip():
            logger.warning("Empty text provided by TTS")
            return
        
        telemetry.increment_counter("speech_requests", attributes={"type": "tts"})
        audio_path = self._get_temp_audio_path()

        try:
            self.file_handler.safe_delete(audio_path)
            audio = gTTS(text=text, lang=self.language.value, slow=slow)
            audio.save(savefile=str(audio_path))
            logger.debug("Generated audio for: %s", text[:50])
            self._play_audio_file(audio_path)
        except (ValueError, RuntimeError) as e:
            logger.error("TTS failed: %s", e)
            telemetry.increment_counter("speech_errors", attributes={"type": "tts"})
            raise TextToSpeechError(f"Text-to-speech failed: {e}") from e
        finally:
            self.file_handler.safe_delete(audio_path)

    async def synthesize(self, text: str, slow: bool = False) -> bytes:
        """Synthesize text to audio bytes asynchronously"""

        if not text or not text.strip():
            raise TextToSpeechError("Empty text provided for synthesis")
        
        telemetry.increment_counter("speech_requests", attributes={"type": "tts_async"})
        try:

            def generate_audio():
                audio = gTTS(text=text, lang=self.language.value, slow=slow)
                audio.save(savefile=str(tmp_path))
                return tmp_path.read_bytes()

            loop = asyncio.get_event_loop()

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            
            audio_bytes = await loop.run_in_executor(None, generate_audio)
            self.file_handler.safe_delete(tmp_path)

            logger.debug("Synthesized audio for: %s...", text[:50])
            return audio_bytes
        except (ValueError, RuntimeError) as e:
            logger.error("Async TTS failed %s", e)
            telemetry.increment_counter("spech_errors", attributes={"type": "tts_async"})
            raise TextToSpeechError(f"Text synthesis failed: {e}") from e
    
    def synthesize_to_base64(self, text: str, slow: bool = False) -> str:
        """Sythesize text and return as base64 encoded string"""

        loop = asyncio.new_event_loop()
        try:
            audio_bytes = loop.run_until_complete(self.synthesize(text, slow))
            return base64.b64encode(audio_bytes).decode("utf-8")
        finally:
            loop.close()


class SpeechService:
    """Unified speech service combining STT and TTS."""

    def __init__(self, language: Language):
        self.language = language
        self._stt = SpeechRecognizer(language=language)
        self._tss = TextToSpeech(language=language)

    def listen(self, timeout: Optional[float] = None) -> str:
        """Listen and transcribe user speech"""
        return self._stt.transcribe(timeout=timeout)
    
    async def listen_async(self, audio_data: bytes) -> str:
        """Transcribe audio data asynchronously"""
        return await self._stt.transcribe_async(audio_data)
    
    def listen_from_file(self, file_path: Path) -> str:
        """Transcribe audio from file"""
        return self._stt.transcribe_from_file(file_path)

    def speak(self, text: str, slow: bool = False) -> None:
        """Speak out the text to user"""
        return self._tss.speak(text=text, slow=slow)
    
    async def synthesize(self, text: str, slow: bool = False) -> bytes:
        """Synthesize text to audio bytes"""
        return await self._tss.synthesize(text=text, slow=slow)
    
    def synthesize_base64(self, text: str, slow: bool = False) -> str:
        """Synthesize text and return as base64"""
        return self._tss.synthesize_to_base64(text=text, slow=False)

def get_speech_service(language: Language) -> SpeechService:
    """Factory function for speech service"""
    return SpeechService(language=language)
