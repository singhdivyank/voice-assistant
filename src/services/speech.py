"""Speech services for audio input/output"""

import logging
import platform
import subprocess
from typing import Optional

import speech_recognition as sr
from gtts import gTTS

from src.config.settings import Language, PathConfig, Platforms
from src.utils.exceptions import NetworkError, TextToSpeechError, TranscriptionError
from src.utils.file_handler import FileHandler
from src.utils.consts import SpeechToTextService


logger = logging.getLogger(__name__)


class SpeechRecognizer(SpeechToTextService):
    """Google Speech Recognizer implementation"""

    def __init__(self, language: Language):
        self.language = language
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
                audio_data=audio, language=self.language.value
            )
            logger.info("Transcribed: %s ...", txt[:50])
            return txt
        except sr.RequestError as e:
            logger.error("Network error during transcription: %s", e)
            raise NetworkError("No internet connection for speech recognition") from e
        except sr.UnknownValueError as exc:
            logger.warning("Could not understand audio")
            raise TranscriptionError("Could not understand audio") from exc
        except sr.WaitTimeoutError as e:
            logger.warning("Listening timed out")
            raise TranscriptionError("Listening timed out") from e
        except (ValueError, RuntimeError) as e:
            logger.error("Transcription failed: %s", e)
            raise TranscriptionError(f"Speech recognition failed: {e}") from e


class TextToSpeech:
    """Google Text-to-Speech implementation"""

    def __init__(self, language: Language, path: PathConfig):
        self.language = language
        self.audio_path = path.audio_file
        self.file_handler = FileHandler()
        self.system = Platforms.from_string(name=platform.system())
        self.players = ["mpg123", "mpg321", "ffplay", "aplay"]

    def play_audio_file(self, file_path: str) -> None:
        """
        Play an audio file using platform-appropriate method.

        Args:
            file_path: Path to audio file

        Raises:
            TextToSpeechError: If playback fails
        """

        try:
            if self.system == Platforms.MAC:
                subprocess.run(["afplay", file_path], check=True, capture_output=True)
            elif self.system == Platforms.WINDOWS:
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
                played = False

                for player in self.players:
                    try:
                        cmd = [player]
                        if player == "ffplay":
                            cmd.extend(["-nodisp", "-autoexit", "-loglevel", "quiet"])
                        cmd.append(file_path)

                        subprocess.run(cmd, check=True, capture_output=True)
                        played = True
                        break
                    except FileNotFoundError:
                        continue

                if not played:
                    raise TextToSpeechError(
                        "No audio player found. Install mpg123: "
                        "sudo apt-get install mpg123"
                    )
        except subprocess.CalledProcessError as e:
            raise TextToSpeechError(f"Audio playback failed: {e}") from e
        except FileNotFoundError as e:
            raise TextToSpeechError(f"Failed to play audio: {e}") from e

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
            logger.debug("Generated audio for: %s", text[:50])
            self.play_audio_file(str(self.audio_path))
        except (ValueError, RuntimeError) as e:
            logger.error("TTS failed: %s", e)
            raise TextToSpeechError(f"Text-to-speech failed: {e}") from e
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Delete audio file"""
        try:
            self.file_handler.safe_delete(self.audio_path)
        except (ValueError, RuntimeError) as e:
            logger.warning("Failed to cleanup audio file: %s", e)


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
