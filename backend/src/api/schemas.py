"""Diagnosis-related Pydantic models"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from src.utils.consts import Gender, Language


class DiagnosisRequest(BaseModel):
    """Schema for diagnosis request"""
    
    complaint: str = Field(..., min_length=5, max_length=2000)


class DiagnosisQuestion(BaseModel):
    """Schema for a diagnostic question"""

    index: int
    question: str
    answered: bool = False


class DiagnosisResponse(BaseModel):
    """Schema for diagnosis response"""

    session_id: str
    questions: list[DiagnosisQuestion]


class MedicationResponse(BaseModel):
    """Schema for medication recommendation"""

    session_id: str
    medication: str
    medication_english: Optional[str] = None
    disclaimer: str = "This is AI-generated advice, please consult physician"


class PrescriptionResponse(BaseModel):
    """Schema for prescription"""

    session_id: str
    prescription_path: str
    download_url: str


class StreamingChunk(BaseModel):
    """Schema for streaming response chunk"""

    _type: str
    content: str
    index: Optional[int] = None
    is_final: bool = False


class PatientCreate(BaseModel):
    """Schema for creating patient info"""

    age: int = Field(..., ge=1, le=90, description="Age of patient")
    gender: Gender = Field(default=Gender.FEMALE)
    language: Language = Field(default=Language.ENGLISH)

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: int) -> int:
        """Validate age is between 1 and 90"""

        if v < 1 or v > 90:
            raise ValueError("Age must be between 1 adn 90")
        return v


class PatientResponse(BaseModel):
    """Schema for patient response"""

    age: int
    gender: str
    language: str

class SessionCreate(BaseModel):
    """Model for creating new consultation session"""

    patient_age: int = Field(..., ge=1, le=90)
    patient_gender: str = Field(default="other")
    language: str = Field(default="en")
    initial_complaint: Optional[str] = Field(default="", min_length=0, max_length=2000)


class SessionResponse(BaseModel):
    """Schema for session response"""

    session_id: str
    created_at: datetime
    status: str
    patient_age: int
    patient_gender: str
    language: str
    initial_complaint: str
    questions: list[str] = []


class ConversationTurnSchema(BaseModel):
    """Schema for a single turn in the conversation"""

    question: str
    answer: str


class SubmitAnswer(BaseModel):
    """Schema for submitting an answer"""

    question_index: int = Field(..., ge=0)
    answer: str = Field(..., min_length=1, max_length=2000)


class SessionState(BaseModel):
    """Full session state"""

    session_id: str
    status: str
    patient_age: int
    patient_gender: str
    language: str
    initial_complaint: str
    questions: list[str]
    conversation: list[ConversationTurnSchema]
    current_question_index: int
    medication: Optional[str] = None
    prescription_path: Optional[str] = None
