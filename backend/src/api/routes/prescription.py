"""Prescription API routes"""

import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from src.api.schemas import PrescriptionResponse
from src.core.prescription import PrescriptionService
from src.services.session_store import SessionStore, get_session_store
from src.config.monitoring import telemetry
from src.config.settings import get_settings


logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

prescription_service = PrescriptionService()


@router.post("/{session_id}/generate", response_model=PrescriptionResponse)
async def generate_prescription(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Generate prescription document for completed session"""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="Session must be completed before generating prescription"
        )
    
    if not session.medication:
        raise HTTPException(
            status_code=400,
            detail="No medication recommendations available"
        )
    
    with telemetry.span("api_generate_prescription", {"session_id": session_id}):
        try:
            file_path = prescription_service.create_prescription(session)
            download_url = f"/api/v1/prescription/{session_id}/download"

            return PrescriptionResponse(
                session_id=session_id,
                prescription_path=str(file_path),
                download_url=download_url
            )
        except Exception as e:
            logger.error("Failed to generate prescription: %s", e)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/download")
async def download_prescription(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Download prescription file"""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    file_path = settings.prescription_dir / f"prescription_{session_id}.txt"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    return FileResponse(
        path=file_path,
        filename=f"prescription_{session_id}.txt",
        media_type="text/plain"
    )


@router.get("/{session_id}/preview")
async def preview_prescription(
    session_id: str,
    store: SessionStore = Depends(get_session_store)
):
    """Preview prescription content"""

    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    file_path = settings.prescription_dir / f"prescription_{session_id}.txt"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    content = file_path.read_text()
    return {"session_id": session_id, "content": content}


@router.delete("/{session_id}")
async def delete_prescription(session_id: str):
    """Delete prescription file"""

    file_path = settings.prescription_dir / f"prescription_{session_id}.txt"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    file_path.unlink()
    return {"status": "deleted", "session_id": session_id}
