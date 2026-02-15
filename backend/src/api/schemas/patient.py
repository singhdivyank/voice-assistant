"""Patient-related Pydantic models"""

from pydantic import BaseModel, Field, field_validator
from src.utils.consts import Gender, Language


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
