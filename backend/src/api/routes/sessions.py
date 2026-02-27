"""Session management API routes."""

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    SessionCreate, SessionResponse, SessionState,
    SubmitAnswer, MedicationResponse
)
from src.core.diagnosis import DiagnosisService, PatientInfo
from src.config.settings import get_settings
from src.config.monitoring import telemetry
from src.services.session_store import SessionStore, get_session_store
from src.services.translation import TranslationService
from src.utils.consts import Gender, Language, DiagnosisSession


logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

diagnosis_service = DiagnosisService()


def _translate_questions(questions: list[str], lang_code: str) -> list[str]:
    """Translate question list to user language if not English."""
    if not questions or lang_code == "en":
        return questions
    try:
        lang = Language.from_code(lang_code)
        svc = TranslationService(target_language=lang)
        return [svc.to_user_language(q) for q in questions]
    except Exception as e:
        logger.warning("Translation failed for questions: %s", e)
        return questions


def _translate_text_to_user(text: str, lang_code: str) -> str:
    """Translate text to user language if not English."""
    if not text or lang_code == "en":
        return text
    try:
        lang = Language.from_code(lang_code)
        svc = TranslationService(target_language=lang)
        return svc.to_user_language(text)
    except Exception as e:
        logger.warning("Translation failed: %s", e)
        return text


def _translate_text_to_english(text: str, lang_code: str) -> str:
    """Translate text from user language to English for LLM."""
    if not text or lang_code == "en":
        return text
    try:
        lang = Language.from_code(lang_code)
        svc = TranslationService(target_language=lang)
        return svc.to_english(text)
    except Exception as e:
        logger.warning("Translation to English failed: %s", e)
        return text


@router.post("/", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    store: SessionStore = Depends(get_session_store)
):
    """Create new consultation session. Questions returned in user's language."""

    session_id = str(uuid.uuid4())

    with telemetry.span("api_create_session", {"session_id": session_id}):
        patient = PatientInfo(
            age=request.patient_age,
            gender=Gender.from_string(request.patient_gender)
        )
        print(request.initial_complaint)
        if request.initial_complaint:
            session = diagnosis_service.create_session(
                session_id=session_id,
                patient=patient,
                complaint=request.initial_complaint,
            )
        else:
            session = DiagnosisSession(
                session_id=session_id,
                patient=patient,
                initial_complaint=request.initial_complaint or ""
            )
        
        session.language = request.language or "en"
        await store.save(session)

        questions_for_client = _translate_questions(session.questions, session.language)
        logger.info("Created session %s, language=%s", session_id, session.language)

        return SessionResponse(
            session_id=session_id,
            created_at=store.get_created_at(session_id=session_id),
            status=session.status,
            patient_age=session.patient.age,
            patient_gender=session.patient.gender.value,
            language=request.language,
            initial_complaint=session.initial_complaint,
            questions=questions_for_client
        )

@router.get("/{session_id}", response_model=SessionState)
async def get_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Get session state. Questions and conversation returned in user's language."""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lang = getattr(session, "language", "en")
    questions_for_client = _translate_questions(session.questions, lang)
    conversation_for_client = [
        {
            "question": _translate_text_to_user(c.question, lang),
            "answer": _translate_text_to_user(c.answer, lang),
        }
        for c in session.conversation
    ]
    medication_for_client = _translate_text_to_user(session.medication or "", lang) or session.medication

    prescription_path = None
    if session.status == "completed":
        prescription_file_path = settings.prescription_dir / f"prescription_{session_id}.txt"
        if prescription_file_path.exists():
            prescription_path = str(prescription_file_path)

    return SessionState(
        session_id=session.session_id,
        status=session.status,
        patient_age=session.patient.age,
        patient_gender=session.patient.gender.value,
        language=lang,
        initial_complaint=session.initial_complaint,
        questions=questions_for_client,
        conversation=conversation_for_client,
        current_question_index=session.current_question_index,
        medication=medication_for_client,
        prescription_path=prescription_path
    )

@router.post("/{session_id}/answer")
async def submit_answer(
    session_id: str,
    request: SubmitAnswer,
    store: SessionStore = Depends(get_session_store)
):
    """Submit an answer. User's answer is translated to English for the LLM; next question returned in user's language."""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")

    lang = getattr(session, "language", "en")
    answer_for_llm = _translate_text_to_english(request.answer, lang)

    with telemetry.span("api_submit_answer", {"session_id": session_id}):
        diagnosis_service.add_response(
            session=session,
            question_index=request.question_index,
            answer=answer_for_llm
        )

        await store.save(session)

        next_question = None
        if session.current_question_index < len(session.questions):
            next_question_en = session.questions[session.current_question_index]
            next_question = _translate_text_to_user(next_question_en, lang)

        return {
            "status": "accepted",
            "current_index": session.current_question_index,
            "is_complete": session.is_complete,
            "next_question": next_question
        }

@router.post("/{session_id}/complete", response_model=MedicationResponse)
async def complete_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Complete session and get medication in user's language; medication_english when language != en."""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lang = getattr(session, "language", "en")

    if session.status == "completed" and session.medication:
        med_en = session.medication
        med_user = _translate_text_to_user(med_en, lang) if lang != "en" else med_en
        return MedicationResponse(
            session_id=session_id,
            medication=med_user,
            medication_english=med_en if lang != "en" else None
        )

    with telemetry.span("api_complete_session", {"session_id": session_id}):
        medication_en = diagnosis_service.complete_session(session)
        await store.save(session)

        medication_user = _translate_text_to_user(medication_en, lang) if lang != "en" else medication_en
        return MedicationResponse(
            session_id=session_id,
            medication=medication_user,
            medication_english=medication_en if lang != "en" else None
        )

@router.post("/{session_id}/complete/stream")
async def complete_session_stream(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Complete session with streaming medication in user's language; then medication_english if lang != en."""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lang = getattr(session, "language", "en")

    async def generate():
        full_en = []
        async for chunk in diagnosis_service.complete_session_stream(session):
            full_en.append(chunk)
            if lang == "en":
                yield f"data: {chunk}\n\n"
        await store.save(session)

        if lang != "en":
            medication_en = "".join(full_en)
            medication_user = _translate_text_to_user(medication_en, lang)
            yield f"data: {medication_user}\n\n"
            yield f"data: {json.dumps({'medication_english': medication_en})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Delete a session"""

    delete = await store.delete(session_id)
    if not delete:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "deleted", "session_id": session_id}
