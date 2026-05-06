"""Speech services for audio input/output with monitoring."""

import asyncio
import base64
import logging
import subprocess
import tempfile
from pathlib import Path

from gtts import gTTS

from src.config.settings import get_settings
from src.config.monitoring import telemetry, timed_operation
from src.utils.consts import (
    Language,
    TextToSpeechService,
    Platform,
)
from src.utils.exceptions import TextToSpeechError
from src.utils.file_handler import FileHandler

logger = logging.getLogger(__name__)
settings = get_settings()


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
                subprocess.run(
                    ["afplay", str(file_path)], check=True, capture_output=True
                )
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
                cmd.append(str(file_path))

                subprocess.run(cmd, check=True, capture_output=True)
                return
            except FileNotFoundError:
                continue
            except subprocess.CalledProcessError:
                continue

        raise TextToSpeechError(
            "No audio player found. Install: sudo apt-get install mpg123"
        )

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

            def generate_audio(path: Path):
                audio = gTTS(text=text, lang=self.language.value, slow=slow)
                audio.save(savefile=str(path))
                return path.read_bytes()

            loop = asyncio.get_event_loop()

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            audio_bytes = await loop.run_in_executor(None, generate_audio, tmp_path)
            self.file_handler.safe_delete(tmp_path)

            logger.debug("Synthesized audio for: %s...", text[:50])
            return audio_bytes
        except (ValueError, RuntimeError) as e:
            logger.error("Async TTS failed %s", e)
            telemetry.increment_counter(
                "spech_errors", attributes={"type": "tts_async"}
            )
            raise TextToSpeechError(f"Text synthesis failed: {e}") from e

    async def synthesize_to_base64(self, text: str, slow: bool = False) -> str:
        """Sythesize text and return as base64 encoded string"""

        audio_bytes = await self.synthesize(text, slow)
        return base64.b64encode(audio_bytes).decode("utf-8")


class SpeechService:
    """Unified speech service combining STT and TTS."""

    def __init__(self, language: Language):
        self.language = language
        self._tss = TextToSpeech(language=language)

    def speak(self, text: str, slow: bool = False) -> None:
        """Speak out the text to user"""
        return self._tss.speak(text=text, slow=slow)

    async def synthesize(self, text: str, slow: bool = False) -> bytes:
        """Synthesize text to audio bytes"""
        return await self._tss.synthesize(text=text, slow=slow)

    async def synthesize_base64(self, text: str, slow: bool = False) -> str:
        """Synthesize text and return as base64"""
        return await self._tss.synthesize_to_base64(text=text, slow=slow)


def get_speech_service(language: Language) -> SpeechService:
    """Factory function for speech service"""
    return SpeechService(language=language)
