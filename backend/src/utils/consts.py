"""Define all dataclasses, Enums, and property classes"""

import platform

from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Gender(str, Enum):
    """Patient gender options"""

    MALE = "male"
    FEMALE = "female"
    UNDISCLOSED = "undisclosed"

    @classmethod
    def from_string(cls, value: str) -> "Gender":
        "Get gender enim from string"
        mapping = {g.value.lower(): g for g in cls}
        return mapping.get(value.lower(), cls.UNDISCLOSED)


class Language(Enum):
    """Supported languages with their ISO codes"""

    ENGLISH = "en"
    BENGALI = "bn"
    GUJRATI = "gu"
    HINDI = "hi"
    KANNADA = "kn"
    MALAYALAM = "ml"
    MARATHI = "mr"
    TAMIL = "ta"
    TELUGU = "te"
    URDU = "ur"
    SPANISH = "es"
    FRENCH = "fr"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"

    @classmethod
    def from_string(cls, name: str) -> "Language":
        """Get language enum from string name (e.g. 'hindi', 'spanish')"""
        mapping = {lang.name.lower(): lang for lang in cls}
        return mapping.get(name.lower(), cls.ENGLISH)

    @classmethod
    def from_code(cls, code: str) -> "Language":
        """Get language enum from ISO code (e.g. 'en', 'hi', 'es')"""
        if not code:
            return cls.ENGLISH
        mapping = {lang.value.lower(): lang for lang in cls}
        return mapping.get(code.lower().strip(), cls.ENGLISH)

    @classmethod
    def choices(cls) -> list[str]:
        """Return list of language names for UI"""
        return [lang.name.lower() for lang in cls]


class Platform:
    """Platform detection utility"""
    
    MAC = "Darwin"
    WINDOWS = "windows"
    LINUX = "Linux"

    @classmethod
    def current(cls) -> str:
        return platform.system()
    
    @classmethod
    def is_mac(cls) -> bool:
        return cls.current() == cls.MAC
    
    @classmethod
    def is_windows(cls) -> bool:
        return cls.current() == cls.WINDOWS
    
    @classmethod
    def is_linux(cls) -> bool:
        return cls.current() == cls.LINUX


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

    session_id: str
    patient: PatientInfo
    initial_complaint: str
    conversation: list[ConversationTurn] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    medication: Optional[str] = None
    current_question_index: int = 0
    status: str = "active"
    language: str = "en"

    @property
    def conversation_summary(self) -> str:
        """Summarize the conversation for LLM input"""
        
        lines = [f"Initial complaint: {self.initial_complaint}"]
        for turn in self.conversation:
            lines.append(f"Q: {turn.question}\nA: {turn.answer}")
        return "\n".join(lines)
    
    @property
    def is_complete(self) -> bool:
        """Check if all questions have been answered"""
        return self.current_question_index >= len(self.questions)

    def to_dict(self) -> dict:
        """Convert session to dictionary for storage"""

        return {
            "session_id": self.session_id,
            "patient_age": self.patient.age,
            "patient_gender": self.patient.gender.value,
            "initial_complaint": self.initial_complaint,
            "questions": self.questions,
            "conversation": [
                {"question": turn.question, "answer": turn.answer}
                for turn in self.conversation
            ],
            "medication": self.medication,
            "current_question_index": self.current_question_index,
            "status": self.status,
            "language": getattr(self, "language", "en"),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DiagnosisSession":
        """Create session from dictionary"""

        patient = PatientInfo(
            age=data.get("patient_age", 1),
            gender=Gender.from_string(data.get("patient_gender", "other"))
        )
        session = cls(
            session_id=data.get("session_id", ""),
            patient=patient,
            initial_complaint=data.get("initial_complaint", "")
        )
        session.questions = data.get("questions", [])
        session.conversation = []
        session.medication = data.get("medication")
        session.current_question_index = data.get("current_question_index", 0)
        session.status = data.get("status", "active")
        session.language = data.get("language", "en")
        return session


class SessionStore(ABC):
    """Abstract base class for session storage."""

    @abstractmethod
    async def save(self, session: DiagnosisSession) -> None:
        """Save a diagnosis session"""
        pass

    @abstractmethod
    async def get(self, session_id: str) -> Optional[DiagnosisSession]:
        """Get a session by ID"""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete a session by ID"""
        pass

    @abstractmethod
    def get_created_at(self, session_id: str) -> datetime:
        """Get session creation time"""
        pass


class SpeechToTextService(ABC):
    """Abstract base class for speech-to-text services."""

    @abstractmethod
    def transcribe(self, timeout: Optional[float] = None) -> str:
        """Transcribe auio to text."""
        pass

    @abstractmethod
    async def transcribe_async(self, audio_data: bytes) -> str:
        """Transcribe audio data asynchronously"""
        pass


class TextToSpeechService(ABC):
    """Abstract base class for text-to-speech services."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Convert text to speech and play it"""
        pass

    @abstractmethod
    async def synthesize(self, text: str, slow: bool = False) -> bytes:
        """Synthesize text to audio bytes"""
        pass

# Prompt templates
DIAGNOSIS_PROMPT = """
You are a medical professional conducting an initial assessment. Based on the patient's complaint, generate exactly 3 focused diagnostic questions.
These questions should help narrow down the diagnosis.

Patient's complaint: {input}

Generate 3 specific, medically relevant follow-up questions.
Format each question on a new line, numbered 1-3""".strip()

MEDICATION_PROMPT = """Based on the following patient information and conversation, provide:
1. A likely diagnosis (or differential diagnosis if uncertain)
2. Recommended medications with dosage
3. Lifestyle recommendations
4. When to seek emergency care

Patient information:
- Age: {age}
- Gender: {gender}

Consultation Summary:
{conversation}

Provide clear, actionable medical guidance. Include appropriaet disclaimers.
""".strip()

PRESCRIPTION_TEMPLATE = """
Date: {date}
Time: {time}

------ Patient Details --------
Age: {age}
Gender: {gender}

------ Notes --------
Initial complaint: 
{initial_complaint}

Follow-up: 
{conversation}

------ Diagnosis & Recommendation --------
{medication}

------------
DISCLAIMER: This is an AI-generated consultation.
Please consult a liscensed physician for proper diagnosis
""".strip()

APP_DESCRIPTION = """
DocJarvis is an AI-powered medical consultation assistant that provides
preliminary diagnosis and medication recommendations based on patient symptoms.
        
**Disclaimer:** This tool is for informational purposes only and should not
replace professional medical advice, diagnosis, or treatment.
""".strip()

MESSAGES = {
    "intro": "Welcome to DocJarvis. I will help you with a preliminary medical consultation.",
    "instruction": "Please describe your symptoms clearly. Speak after the beep.",
    "diagnosis": "Analyzing your symptoms and generating recommendations...",
    "questions_intro": "I have a few follow-up questions to better understand your condition.",
    "complete": "Thank you for your responses. Generating your consultation summary.",
    "error": "An error occurred. Please try again.",
    "network_error": "Unable to connect. Please check your internet connection.",
    "disclaimer": "This is AI-generated advice. Please consult a licensed physician.",
}
