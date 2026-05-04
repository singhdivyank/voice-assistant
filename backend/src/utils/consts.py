"""Define all dataclasses, Enums, and property classes"""

import platform

from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional


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
    def from_code(cls, code: str | None) -> "Language":
        """Get language enum from ISO code (e.g. 'en', 'hi', 'es')"""
        if not code:
            return cls.ENGLISH
        mapping = {lang.value.lower(): lang for lang in cls}
        return mapping.get(code.lower().strip(), cls.ENGLISH)

    @classmethod
    def choices(cls) -> list[str]:
        """Return list of language names for UI"""
        return [lang.name.lower() for lang in cls]


class WorkflowStep(Enum):
    """Workflow step enumeration"""

    WELCOME = "welcome"
    INITIAL_SYMPTOM = "initial_symptom"
    QUESTIONS_GENERATED = "questions_generated"
    QA_IN_PROGRESS = "qa_in_progress"
    QA_COMPLETE = "qa_complete"
    RECOMMENDATIONS_GENERATED = "recommendations_generated"
    AUDIO_GENERATED = "audio_generated"
    PRESCRIPTION_SENT = "prescription_sent"
    DOCTOR_REVIEW = "doctor_review"
    COMPLETED = "completed"
    ERROR = "error"


class ReviewStatus(Enum):
    """Review status enumeration"""

    PENDING = "pending"
    SENT = "sent"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    MODIFIED = "modified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"


class Platform:
    """Platform detection utility"""

    MAC = "Darwin"
    WINDOWS = "Windows"
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

    name: str
    email: str
    age: int
    gender: Gender

    def __str__(self) -> str:
        return f"Name: {self.name}, Age: {self.age}, Gender: {self.gender.value}, Email: {self.email}"


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
            "patient_name": self.patient.name,
            "patient_email": self.patient.email,
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
            name=data.get("patient_name", "Unknown"),
            email=data.get("patient_email", ""),
            age=data.get("patient_age", 1),
            gender=Gender.from_string(data.get("patient_gender", "other")),
        )
        session = cls(
            session_id=data.get("session_id", ""),
            patient=patient,
            initial_complaint=data.get("initial_complaint", ""),
        )
        session.questions = data.get("questions", [])
        session.conversation = [
            ConversationTurn(question=t["question"], answer=t["answer"])
            for t in data.get("conversation", [])
        ]
        session.medication = data.get("medication")
        session.current_question_index = data.get("current_question_index", 0)
        session.status = data.get("status", "active")
        session.language = data.get("language", "en")
        return session


@dataclass
class AgentPerformanceMetrics:
    """Track performance metrics for individual agents"""

    agent_name: str
    total_executions: int = 0
    total_duration_ms: float = 0
    average_duration_ms: float = 0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0
    error_count: int = 0
    success_rate: float = 1.0

    # latency percentiles
    p50_ms: float = 0
    p95_ms: float = 0
    p99_ms: float = 0

    # recent performance (sliding window)
    recent_durations: List[float] = field(default_factory=list)
    max_recent_samples: int = 100

    def update(self, duration_ms: float, success: bool = True):
        """Update metrics with new execution data"""

        self.total_executions += 1

        if not success:
            self.error_count += 1
        else:
            self.total_duration_ms += duration_ms
            self.min_duration_ms = min(self.min_duration_ms, duration_ms)
            self.max_duration_ms = max(self.max_duration_ms, duration_ms)
            self.average_duration_ms = self.total_duration_ms / max(
                1, self.total_executions - self.error_count
            )
            self._update_durations(duration_ms)
            self._calc_percentile()

        self.success_rate = (self.total_executions - self.error_count) / max(
            1, self.total_executions
        )

    def _update_durations(self, exec_time: float):
        """Update the recent durations for percentile calculation"""
        self.recent_durations.append(exec_time)
        if len(self.recent_durations) - self.max_recent_samples > 0:
            self.recent_durations.pop(0)

    def _calc_percentile(self):
        """Calculate percentiles"""
        if self.recent_durations:
            sorted_durations = sorted(self.recent_durations)
            n = len(sorted_durations)
            self.p50_ms = sorted_durations[int(n * 0.5)]
            self.p95_ms = sorted_durations[min(int(n * 0.95), n - 1)]
            self.p99_ms = sorted_durations[min(int(n * 0.99), n - 1)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization"""
        return {
            "agent_name": self.agent_name,
            "total_executions": self.total_executions,
            "average_duration_ms": round(self.average_duration_ms, 2),
            "min_duration_ms": (
                round(self.min_duration_ms, 2)
                if self.min_duration_ms != float("inf")
                else 0
            ),
            "max_duration_ms": round(self.max_duration_ms, 2),
            "error_count": self.error_count,
            "success_rate": round(self.success_rate, 4),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
        }


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


class GmailSendInput(BaseModel):
    """Input for Gmail MCP send tool"""

    to_email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    review_id: str = Field(..., description="Review ID for tracking")


class GmailReadInput(BaseModel):
    """Input for Gmail MCP read tool"""

    search_query: str = Field(..., description="Gmail search query")
    max_results: int = Field(default=10, description="Maximum number of results")


# Prompt templates
DIAGNOSIS_PROMPT = """
You are a medical professional conducting an initial assessment. Based on the patient's complaint, generate exactly 3 focused diagnostic questions.
These questions should help narrow down the diagnosis.

Patient's complaint: {input}

Strictly generate only 3 specific, medically relevant follow-up questions.
Format each question on a new line, numbered 1-3""".strip()

MEDICATION_PROMPT = (
    """Based on the following patient information and conversation, provide:
1. A likely diagnosis (or differential diagnosis if uncertain)
2. Recommended medications with dosage
3. Lifestyle recommendations
4. When to seek emergency care

Patient information:
- Age: {age}
- Gender: {gender}

Consultation Summary:
{conversation}

Provide clear, actionable medical guidance. Include appropriate disclaimers.
""".strip()
)

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

FORMAT_MAP = {
    ".wav": "wav",
    ".flac": "flac",
    ".webm": "webm",
    ".mp3": "mp3",
    ".m4a": "mp4",
    ".aiff": "aiff",
    ".aif": "aiff",
}

EMAIL_BODY = """
<html>
<body>

<h2>Prescription Review Required</h2>
<p><strong>Review ID:</strong> {review_id}</p>
<p><strong>Patient:</strong> {age} year old {gender}</p>
<h3>Prescription Content:</h3>
<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 4px;">
{content}
</pre>

<h3>Review Instructions:</h3>
<p>Please reply with one of the following:</p>
<ul>
    <li><strong>APPROVE #{review_id}</strong> - To approve as-is</li>
    <li><strong>MODIFY #{review_id} - [your changes]</strong> - To approve with modifications</li>
    <li><strong>REJECT #{review_id} - [reason]</strong> - To reject</li>
</ul>

</body>
</html>
""".strip()

TIMEOUT = 300
