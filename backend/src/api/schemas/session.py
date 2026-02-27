"""Session-related Pydantic moodels"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


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
