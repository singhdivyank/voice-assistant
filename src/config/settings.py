import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


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

    @classmethod
    def from_sring(cls, name: str) -> "Language":
        """Get language enum from string name"""
        mapping = {lang.name.lower(): lang for lang in cls}
        return mapping.get(name.lower(), cls.ENGLISH)

    @classmethod
    def choices(cls) -> list[str]:
        """Return list of language names for UI"""
        return [lang.name.lower() for lang in cls]


class Gender(Enum):
    """Patient gender options"""

    MALE = "male"
    FEMALE = "female"
    UNDISCLOSED = "Prefer not to disclose"

    @classmethod
    def from_string(cls, value: str) -> "Gender":
        "Get gender enim from string"
        for gender in cls:
            if gender.value.lower() == value.lower():
                return gender

        return cls.UNDISCLOSED


class Platforms(Enum):
    """Supported Operating Systems"""

    WINDOWS = "Windows"
    LINUX = "Linux"
    MAC = "Darwin"

    @classmethod
    def from_sring(cls, name: str) -> "Platforms":
        """Get platform enum from string name"""
        mapping = {lang.name.lower(): lang for lang in cls}
        return mapping.get(name.lower(), cls.MAC)


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for the LLM model"""

    model_name = "jarvis_backend"
    gemini_model: str = "gemini-pro"
    temperature: float = 0.0
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY"))

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")


@dataclass(frozen=True)
class ServerConfig:
    """Configuration for the Gradio server"""

    host: str = field(default_factory=lambda: os.getenv(key="GRADIO_SERVER_NAME"))
    port: int = field(default_factory=lambda: int(os.getenv(key="GRADIO_SERVER_PORT")))
    share: bool = False


@dataclass(frozen=True)
class PathConfig:
    """File path configuration"""

    base_dir: Path = field(default_factory=lambda: Path.cwd())

    @property
    def prescription_file(self) -> Path:
        return self.base_dir / "prescription.txt"

    @property
    def audio_file(self) -> Path:
        return self.base_dir / "voice.mp3"


@dataclass
class AppConfig:
    """Main application configuration"""

    llm: LLMConfig = field(default_factory=LLMConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    main_age: int = 1
    max_age: int = 120
    default_age: int = 25


# Prompt templates
DIAGNOSIS_PROMPT = """
You are a medical professional conducting an initial assessment.
Your role is to ask targeted follow-up questions to better understand the patient's condition.

Guidelines:
- Ask exactly 3 focused questions
- Each question should gather specific, actionable information
- Use clear, simple language appropriate for patients
- Focus on: symptom characteristics, duration/onset, and associated symptoms

Patient's initial complaint: {input}

Provide your 3 questions, one per line, numbered 1-3
"""

MEDICATION_PROMPT = """
You are a certified medical professional in India providing treatment recommendations.\

Patient information:
- Age: {age}
- Gender: {gender}

Consultation Summary:
{conversation}

Provide recommendations following these guidelines:
1. Prioritize dietary modifications with specific foods (name exact fruits, vegetables, spices)
2. Include relevant natural remedies (turmeric, asafoetida, carom seeds, fennel, etc.)
3. Suggest appropriate lifestyle changes
4. Only prescribe medications when necessary, avoiding over-prescription
5. Consider the patient's age and gender in your recommendations

Format your response with clear sections for Diet, Lifestyle, and Medications (if needed).
"""

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

------ Recommendation --------
{medication}
"""

APP_DESCRIPTION = """
Welcome to DocJarvis, your AI-powered medical consultation assistant.
        
**Instructions:**
    1. Select your preferred language
    2. Select your gender and age
    3. Click Submit to start the consultation
    4. Speak your symptoms when prompted
    5. Answer the follow-up questions
    6. Receive your consultation summary
        
**Note:** This is for informational purposes only. Always consult a 
qualified healthcare professional for medical advice.
""".strip()
