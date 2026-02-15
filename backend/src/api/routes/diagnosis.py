"""Diagnosis API routes"""

import logging

from fastapi import APIRouter, HTTPException

from src.api.schemas import DiagnosisRequest, DiagnosisQuestion
from src.core.diagnosis import DiagnosisEngine
from src.config.monitoring import telemetry
from src.services.translation import TranslationService
from src.utils.consts import Language


logger = logging.getLogger(__name__)
router = APIRouter()

diagnosis_engine = DiagnosisEngine()


@router.post("/questions", response_model=list[DiagnosisQuestion])
async def generate_questions(request: DiagnosisRequest):
    """Generate diagnostic questions for a complaint."""

    with telemetry.span("api_generate_questions"):
        try:
            questions = diagnosis_engine.generate_questions(request.complaint)
            return [
                DiagnosisQuestion(index=idx, question=question)
                for idx, question in enumerate(questions)
            ]
        except Exception as e:
            logger.error("Failed to generate questions: %s", e)
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/questions/translate")
async def generate_questions_translated(
    request: DiagnosisRequest,
    language: str = "en"
):
    """Generate diagnostic questions with translation"""

    with telemetry.span("api_generate_questions_translated", {"language": language}):
        try:
            questions = diagnosis_engine.generate_questions(request.complaint)
            if not language == "en":
                lang = Language.from_sring(language)
                translation = TranslationService(target_language=lang)
                questions = [
                    translation.to_user_language(question) for question in questions
                ]
            
            return {
                "questions": [
                    {"index": idx, "question" : question, "original_language": "en", "translated_language": language}
                    for idx, question in enumerate(questions)
                ],
                "language": language
            }
        except Exception as e:
            logger.error("Failed to generate translated questions: %s", e)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts")
async def get_prompts():
    """Get current prompt templates (for debugging)"""

    from src.config.settings import DIAGNOSIS_PROMPT, MEDICATION_PROMPT
    return {
        "diagnosis_prompt": DIAGNOSIS_PROMPT,
        "medication_prompt": MEDICATION_PROMPT
    }
