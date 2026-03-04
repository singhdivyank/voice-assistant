import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, BackgroundTasks
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    MedicationResponse,
    SessionResponse, 
    SessionCreate, 
    SessionState
)
from src.config.monitoring import telemetry
from src.integration.route_handlers import MultiAgentRouteHandlers
from src.services.session_store import SessionStore, get_session_store
from src.utils.file_handler import FileHandler

logger = logging.getLogger(__name__)

router = APIRouter()
multi_agent_handlers = MultiAgentRouteHandlers()
file_handler = FileHandler()


@router.post("/", response_model=SessionResponse)
async def create_multi_agent_session(
    request: SessionCreate,
    store: SessionStore = Depends(get_session_store)
):
    """Consultation session with multi-agent system"""

    with telemetry.span("create_session_v2", {"language": request.language}):
        try:
            result = await multi_agent_handlers.create_session_handler(
                patient_age=request.patient_age,
                patient_gender=request.patient_gender,
                language=request.language or "en",
                initial_complaint=request.initial_complaint,
                session_store=store
            )

            logger.info("v2 session created: %s", result["session_id"])
            return SessionResponse(**result)
        except Exception as e:
            logger.error("v2 session creation failed: %s", e)
            telemetry.increment_counter("v2_session_creation_errors")
            raise HTTPException(status_code=500, detail=f"Multi-agent session creation failed: {str(e)}")

@router.post("/{session_id}/transcribe")
async def transcribe_audio_multi_agent(
    session_id: str,
    audio_file: UploadFile = File(...),
    question_index: int = 0,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    store: SessionStore = Depends(get_session_store)
):
    """Process audio input through multi-agent STT pipeline"""

    temp_audio_path = None

    try:
        with telemetry.span("transcribe_v2", {"session_id": session_id, "question_index": question_index}):
            if not audio_file.content_type or "audio" not in audio_file.content_type.lower():
                raise HTTPException(status_code=400, detail="Invalid audio file format")
            
            if audio_file.size and audio_file.size > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Audio file too large (max 10MB)")
            
            file_extension = Path(audio_file.filename or "audio.wav").suffix or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                content = await audio_file.read()
                temp_file.write(content)
                temp_audio_path = Path(temp_file.name)

            result = await multi_agent_handlers.transcribe_and_respond_handler(
                session_id=session_id,
                audio_file_path=temp_audio_path,
                question_index=question_index,
                session_store=store
            )
            
            background_tasks.add_task(file_handler.safe_delete, temp_audio_path)
            response = {
                **result,
                "api_version": "v2",
                "processing_method": "multi_agent",
                "agents_used": ["stt", "translation", "qa", "tts"]
            }

            logger.info("v2 transcription completed for session %s, question %d", session_id, question_index)
            return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("v2 transcription failed for session %s:%s", session_id, e)
        telemetry.increment_counter("v2_transcription_error")
        raise HTTPException(status_code=500, detail=f"Multi-agent transcription failed: {str(e)}")
    finally:
        if temp_audio_path.exists():
            try:
                temp_audio_path.unlink()
            except Exception as cleanup_error:
                logger.warning("Failed to cleanup temp file: %s", cleanup_error)

@router.get("/{session_id}", response_model=SessionState)
async def get_multi_agent_session(session_id: str):
    """Get detailed session state"""

    with telemetry.span("get_session_v2", {"session_id": session_id}):
        session_data = await multi_agent_handlers.get_session_handler(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        enhanced_response = {
            **session_data,
            "api_version": "v2",
            "multi_agent_metadata": {
                "execution_id": session_data.get("execution_id"),
                "agents_complete": session_data.get("agent_results", {}).keys(),
                "performance_metrics": session_data.get("agent_results", {})
            }
        }

        return SessionState(**enhanced_response)

@router.post("/{session_id}/answer")
async def submit_answer_multi_agent(session_id: str):
    """Submit text answer through multi-agent processing"""

    with telemetry.span("submit_answer_v2", {"session_id": session_id}):
        from src.integration.muti_agent_service import MultiAgentService

        try:
            service = MultiAgentService()
            result = await service.get_session_state(session_id=session_id)
            return {
                **result,
                "api_version": "v2",
                "processing_method": "multi_agent"
            }
        except Exception as e:
            logger.error("v2 answer submission failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/complete", response_model=MedicationResponse)
async def complete_multi_agent_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """complete session using multi-agent diagnosis and medication pipeline"""

    with telemetry.span("completed_session_v2", {"session_id": session_id}):
        try:
            result = await multi_agent_handlers.complete_session_handler(
                session_id=session_id,
                session_store=store
            )
            enhanced_result = {
                **result,
                "api_version": "v2",
                "processing_agents": ["diagnosis", "medication", "prescription", "translation"],
                "disclaimer": "This is AI-generated advice from a multi-agent system, please consult a physician"
            }

            logger.info("v2 session completed: %s", session_id)
            return MedicationResponse(**enhanced_result)
        except Exception as e:
            logger.error("v2 session completion failed: %s", e)
            telemetry.increment_counter("v2_completion_errors")
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/complete/stream")
async def complete_session_stream_v2(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """complete session with streaming response from multi-agent system"""

    with telemetry.span("complete_session_stream_v2", {"session_id": session_id}):
        try:
            async def enhanced_stream():
                yield f"data: {{'api_version': 'v2', 'processing_method': 'multi_agent_stream'}}\n\n"
                
                # Stream the actual response
                async for chunk in multi_agent_handlers.complete_session_stream_handler(
                    session_id=session_id,
                    session_store=store
                ):
                    yield chunk
            
            return StreamingResponse(
                enhanced_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-API-Version": "v2"
                }
            )
        except Exception as e:
            logger.error("v2 streaming completion failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/speak")
async def generate_speech_v2(session_id: str):
    """Generate speech using multi-agent TTS system"""

    with telemetry.span("generate_speech_v2", {"session_id": session_id}):
        try:
            audio_base64 = await multi_agent_handlers.speak_recommendations_handler(session_id)
            return {
                "audio": audio_base64,
                "api_version": "v2",
                "tts_agent": "multi_agent_tts",
                "format": "mp3_base64"
            }
        except Exception as e:
            logger.error("v2 TTS generated failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_multi_agent_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """delete session and cleanup resources"""

    from src.integration.muti_agent_service import MultiAgentService

    with telemetry.span("delete_session_v2", {"session_id": session_id}):
        try:
            service = MultiAgentService()
            if session_id in service._active_sessions:
                del service._active_sessions[session_id]

            deleted = await store.delete(session_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Session not found")
            
            logger.info("v2 session deleted: %s", session_id)
            return {
                "status": "deleted",
                "session_id": session_id,
                "api_version": "v2"
            }
        except Exception:
            raise
        except Exception as e:
            logger.error("v2 session deletion failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))
