from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config.settings import Gender


@dataclass
class ConversationTurn:
    """Represents a single turn in doctor-patient conversation"""

    question: str
    answer: str


@dataclass
class PatientInfo:
    """Patient demographic information"""

    age: int
    gender: Gender

    def __str__(self) -> str:
        return f"Age: {self.age}, Gender: {self.gender.value}"


@dataclass
class DiagnosisSession:
    """Track the state of diagnosis session"""

    patient: PatientInfo
    initial_complaint: str
    conversation: list[ConversationTurn] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    medication: Optional[str] = None

    @property
    def conversation_summary(self) -> str:
        """Format conversation for LLM input"""
        lines = [f"Initial complaint: {self.initial_complaint}"]
        for turn in self.conversation:
            lines.append(f"Q: {turn.question}")
            lines.append(f"A: {turn.answer}")
        return "\n".join(lines)


@dataclass
class PrescriptionMetadata:
    """Metadata for a prescription document"""

    created_at: datetime
    session_id: str
    file_path: Path


@dataclass
class TranslationResult:
    """Result of a translation operation"""

    original: str
    translated: str
    source_lang: str
    target_lang: str


class SpeechToTextService(ABC):
    """Abstract base class for speech-to-text services."""

    @abstractmethod
    def transcribe(self) -> str:
        """Transcribe auio to text."""


class TextToSpeechService(ABC):
    """Abstract base class for text-to-speech services."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Convert text to speech and play it"""
