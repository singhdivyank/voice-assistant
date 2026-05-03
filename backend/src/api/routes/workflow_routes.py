"""FastAPI routes for sequential medical workflow"""

import logging
import os
import tempfile
import uuid

from typing import Optional

from fastapi import Form, HTTPException, UploadFile
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse

from src.api.schemas import SessionState
from src.core.crew_ai.medical_crew import medical_crew
from src.utils.exceptions import DocJarvisError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflow", tags=["Sequential Medical Workflow"])
active_sessions = {}

@router.post("/welcome-audio")
async def generate_welcome_audio(language: str = Form(default="en")):
    """Step1: generate welcome audio"""

    try:
        if not medical_crew._initialised:
            await medical_crew.initialise()
        
        result = await medical_crew.generate_welcome_audio(language=language)
        return JSONResponse(content=result)
    except DocJarvisError as e:
        logger.error(f"Welcome audio generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error(f"Unexpected error in welcome audio generation: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/process-initial-symptom")
async def process_initial_symptom(
    session_id: Optional[str] = Form(None),
    patient_age: int = Form(...),
    patient_gender: str = Form(...),
    language: str = Form(default="en"),
    initial_complaint: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = Form(None)
):
    """Steps 2-4: Process initial symptom and generate diagnostic questions"""

    audio_file_path = None
    
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    if audio_file:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                content = await audio_file.read()
                temp_file.write(content)
                audio_file_path = temp_file.name
        except Exception as e:
            logger.error(f"Audio file processing failed: {e}")
            raise HTTPException(status_code=400, detail="Audio file processing failed")
    
    session_state = SessionState(
        session_id=session_id,
        status='active',
        patient_age=patient_age,
        patient_gender=patient_gender,
        language=language,
        initial_complaint=initial_complaint or "",
        questions=[],
        conversation=[],
        current_question_index=0
    )

    try:
        if not medical_crew._initialised:
            await medical_crew.initialise()
        
        result = await medical_crew.process_initial_symptom(
            session_state=session_state, 
            audio_file_path=audio_file_path
        )
        active_sessions[session_id] = session_state
        return JSONResponse(result)
    except DocJarvisError as e:
        logger.error(f"Initial symptom processing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in initial symptom processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if audio_file_path and os.path.exists(audio_file_path):
            try:
                os.unlink(audio_file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp audio file: {e}")

@router.post("/answer-question/{session_id}")
async def answer_question(
    session_id: str,
    question_index: int = Form(...),
    answer: str = Form(...)
):
    """Steps 5-6: Process Q&A responses"""

    try:
        if not medical_crew._initialised:
            await medical_crew.initialise()
        
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session_state = active_sessions[session_id]
        result = await medical_crew.process_qa_answer(
            session_state=session_state, 
            question_index=question_index, 
            answer=answer
        )
        active_sessions[session_id] = session_state
        return JSONResponse(content=result)
    except DocJarvisError as e:
        logger.error(f"Q&A processing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in Q&A processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.post("/generate-recommendations/{session_id}")
async def generate_recommendations(session_id: str):
    """Step 7: generate medica; recommendations"""

    try:
        if not medical_crew._initialised:
            await medical_crew.initialise()
        
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_state = active_sessions[session_id]
        result = await medical_crew.generate_recommednations(session_state=session_state)
        return JSONResponse(content=result)
    except DocJarvisError as e:
        logger.error(f"Recommendations generation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in recommendations generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/recommendations-audio")
async def generate_recommendations_audio(
    recommendations: str = Form(...),
    language: str = Form(default="en")
):
    """Step 8: Generate audio of recommendations"""

    try:
        if not medical_crew._initialised:
            await medical_crew.initialise()
        
        result = await medical_crew.generate_recommendations_audio(
            recommendations=recommendations, 
            language=language
        )
        return JSONResponse(content=result)
    except DocJarvisError as e:
        logger.error(f"Audio generation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in audio generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/generate-prescription/{session_id}")
async def gen_prescription(
    session_id: str,
    recommendations: str = Form(...),
):
    """Step 9-10 generate prescription and send for doctor review"""

    try:
        if not medical_crew._initialised:
            await medical_crew.initialise()
        
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_state = active_sessions[session_id]
        result = await medical_crew.generate_and_review_prescriptions(
            session_state=session_state, 
            recommendations=recommendations
        )
        return JSONResponse(content=result)
    except DocJarvisError as e:
        logger.error(f"Prescription generation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in prescription generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")    

@router.post("/doctor-response")
async def process_doctor_response(
    review_id: str = Form(...),
    email_content: str = Form(...)
):
    """Process doctor's response"""

    try:
        if not medical_crew._initialised:
            await medical_crew.initialise()
        
        result = await medical_crew.process_doctor_response(
            review_id=review_id, 
            email_content=email_content
        )
        return JSONResponse(content=result)
    except DocJarvisError as e:
        logger.error(f"Doctor response processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in doctor response processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Get session status and progress"""

    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_state = active_sessions[session_id]
        total_questions = len(session_state.questions)
        answered_questions = sum(
            1 for turn in session_state.conversation
            if turn.answer and turn.answer.strip()
        )
        
        return JSONResponse(content={
            "session_id": session_id,
            "status": session_state.status,
            "patient_age": session_state.patient_age,
            "patient_gender": session_state.patient_gender,
            "language": session_state.language,
            "initial_complaint": session_state.initial_complaint,
            "questions": session_state.questions,
            "conversation": [
                {"question": turn.question, "answer": turn.answer}
                for turn in session_state.conversation
            ],
            "progress": {
                "total_questions": total_questions,
                "answered_questions": answered_questions,
                "completion_percentage": (answered_questions / total_questions * 100) if total_questions > 0 else 0,
                "all_answered": answered_questions >= total_questions and total_questions > 0
            }
        })
    except Exception as e:
        logger.error(f"Session status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sessions/active")
async def get_active_sessions():
    """Get all active sessions (for debugging/monitoring)"""
    
    try:
        sessions_info = {}
        for session_id, session_state in active_sessions.items():
            sessions_info[session_id] = {
                "patient_age": session_state.patient_age,
                "patient_gender": session_state.patient_gender,
                "language": session_state.language,
                "questions_count": len(session_state.questions),
                "answers_count": len([turn for turn in session_state.conversation if turn.answer]),
                "status": session_state.status
            }
        
        return JSONResponse(content={
            "total_active_sessions": len(active_sessions),
            "sessions": sessions_info
        })
    except Exception as e:
        logger.error(f"Active sessions retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/session/{session_id}")
async def del_session(session_id: str):
    """Delete a session (cleanup)"""
    
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        del active_sessions[session_id]
        return JSONResponse(content={
            "message": f"Session {session_id} deleted successfully"
        })
    except Exception as e:
        logger.error(f"Session deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def workflow_health():
    """Health check for workflow system"""
    
    try:
        return JSONResponse(content={
            "status": "healthy",
            "crew_initialized": medical_crew._initialised,
            "active_sessions": len(active_sessions),
            "components": {
                "medical_crew": "operational" if medical_crew._initialised else "initializing",
                "session_storage": "operational",
                "active_sessions_count": len(active_sessions)
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "crew_initialized": medical_crew._initialised if hasattr(medical_crew, '_initialised') else False
            }
        )