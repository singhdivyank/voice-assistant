"""Diagnosis-related Pydantic models"""

from typing import Optional
from pydantic import BaseModel, Field


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
    disclaimer: str = "This is AI-generated advice, please conuslt physician"


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
