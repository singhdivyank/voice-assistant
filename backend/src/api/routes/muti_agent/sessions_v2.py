import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from src.api.schemas import SessionResponse, SessionCreate
from src.config.monitoring import telemetry
from src.core.multi_agent.coordinator.agent_coordinator import AgentCoordinator
from src.services.session_store import SessionStore, get_session_store

logger = logging.getLogger(__name__)

router = APIRouter()
coordinator = AgentCoordinator()


@router.post("/", response_model=SessionResponse)
async def create_agentic_session(request: SessionCreate):
    """Consultation session with multi-agent system"""

    with telemetry.span("create_session_v2", {"language": request.language}):
        
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        patient_info = {
            "age": request.patient_age,
            "gender": request.patient_gender,
            "complaint": request.initial_complaint
        }

        try:
            response_text = await coordinator.process_user_input(
                user_input=request.initial_complaint,
                session_id=session_id,
                patient_info=patient_info
            )
            logger.info("v2 session created: %s", response_text["session_id"])
            response = SessionResponse(
                session_id=session_id,
                created_at=datetime.now(),
                status="active",
                patient_age=request.patient_age,
                patient_gender=request.patient_gender,
                language=request.language,
                initial_complaint=request.initial_complaint,
                questions=response_text
            )
            return response
        except Exception as e:
            logger.error("v2 session creation failed: %s", e)
            telemetry.increment_counter("v2_session_creation_errors")
            raise HTTPException(status_code=500, detail=f"Multi-agent session creation failed: {str(e)}")

@router.post("/{session_id}/chat")
async def chat_with_agent(session_id: str, user_input: str, request_data: dict):
    """main loop for conversation"""

    patient_info = request_data.get("patient_info", {})
    response = await coordinator.process_user_input(
        user_input=user_input,
        session_id=session_id,
        patient_info=patient_info
    )
    return {"reply": response}

@router.post("/{session_id}/approve")
async def approve_prescription(session_id: str):
    """called by a doctor to resume the agent graph after review (HITL)"""
    config = {"configurable": {"thread_id": session_id}}
    await coordinator.app.update_state(config, {"is_approved": True})
    result = await coordinator.app.ainvoke(None, config)
    return {"status": "approved", "final_output": result["messages"][-1].content}

@router.delete("/{session_id}")
async def delete_multi_agent_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """delete session and cleanup resources"""

    with telemetry.span("delete_session_v2", {"session_id": session_id}):
        try:
            deleted = await store.delete(session_id)
            if not deleted:
                logger.warning("Session metadata not found in store for ID: %s", session_id)
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
