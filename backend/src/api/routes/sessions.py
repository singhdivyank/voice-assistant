"""Session management API routes."""

import logging
import uuid

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    SessionCreate, SessionResponse, SessionState,
    SubmitAnswer, MedicationResponse
)
from src.core.diagnosis import DiagnosisService, PatientInfo
from src.core.prescription import PrescriptionService
from src.config.settings import get_settings
from src.config.monitoring import telemetry
from src.services.session_store import SessionStore, get_session_store
from src.utils.consts import Gender


logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

diagnosis_service = DiagnosisService()


@router.post("/", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    store: SessionStore = Depends(get_session_store)
):
    """Create new consultation session"""

    session_id = str(uuid.uuid4())

    with telemetry.span("api_create_session", {"session_id": session_id}):
        patient = PatientInfo(
            age=request.patient_age,
            gender=Gender.from_string(request.patient_gender)
        )
        session = diagnosis_service.create_session(
            session_id=session_id,
            patient=patient,
            complaint=request.initial_complaint,
        )

        await store.save(session)

        logger.info("Created session %s", session_id)

        return SessionResponse(
            session_id=session_id,
            created_at=store.get_created_at(session_id=session_id),
            status=session.status,
            patient_age=session.patient.age,
            patient_gender=session.patient.gender.value,
            language=request.language,
            initial_complaint=session.initial_complaint,
            questions=session.questions
        )

@router.get("/{session_id}", response_model=SessionState)
async def get_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Get session state"""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    prescription_path = None
    if session.status == "completed":
        prescription_file_path = settings.prescription_dir / f"prescription_{session_id}.txt"
        if prescription_file_path.exists():
            prescription_path = str(prescription_path)
    
    return SessionState(
        session_id=session.session_id,
        status=session.status,
        patient_age=session.patient.age,
        patient_gender=session.patient.gender.value,
        language=getattr(session, 'language', 'en'),
        initial_complaint=session.initial_complaint,
        questions=session.questions,
        conversation=[
            {"question": conversation.question, "answer": conversation.answer}
            for conversation in session.conversation
        ],
        current_question_idx=session.current_question_index,
        medication=session.medication,
        prescription_path=prescription_path
    )

@router.post("/{session_id}/answer")
async def submit_answer(
    session_id: str,
    request: SubmitAnswer,
    store: SessionStore = Depends(get_session_store)
):
    """Submit an answer to a diagnostic question"""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")
    
    with telemetry.span("api_submit_answer", {"session_id": session_id}):
        diagnosis_service.add_response(
            session=session,
            question_idx=request.question_idx,
            answer=request.answer
        )

        await store.save(session)

        next_question = None
        if session.current_question_index < len(session.questions):
            next_question = session.questions[session.current_question_index]
        
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
    """Complete session and get medication recommendation"""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status == "completed" and session.medication:
        return MedicationResponse(
            session_id=session_id,
            medication=session.medication
        )
    
    with telemetry.span("api_complete_session", {"session_id": session_id}):
        medication = diagnosis_service.complete_session(session)
        await store.save(session)
        
        return MedicationResponse(
            session_id=session_id,
            medication=medication
        )

@router.post("/{session_id}/complete/stream")
async def complete_session_stream(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Complete session with streaming medication response"""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    async def generate():
        async for chunk in diagnosis_service.complete_session_stream(session):
            yield f"data: {chunk}\n\n"
        await store.save(session)
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
