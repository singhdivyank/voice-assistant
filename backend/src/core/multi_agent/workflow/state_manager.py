import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from src.utils.consts import Language, PatientInfo


class AgentState(TypedDict):
    """Multi-agent state definition."""

    # Patient Information
    patient: PatientInfo
    session_id: str

    # Audio Processing
    audio_files: List[Path]
    transcribed_texts: List[str]

    # Conversation Flow
    questions: List[str]
    answers: List[str]
    conversation_complete: bool

    # Medical Analysis
    symptoms_analysis: Optional[str]
    differential_diagnosis: Optional[str]
    final_diagnosis: Optional[str]

    # Translation
    source_language: Language
    translated_content: Dict[str, str]

    # Voice Synthesis
    tts_files: List[Path]
    response_audio: Optional[str]

    # Prescription
    medication_recommendations: Optional[str]
    prescription_path: Optional[Path]

    # Control Flow
    current_step: str
    errors: List[str]
    metadata: Dict


@dataclass
class AgentExecutionState(AgentState):
    """Extended state for agent execution tracking"""

    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_agent: Optional[str] = None
    completed_agents: List[str] = field(default_factory=list)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    agen_latencies: Dict[str, float] = field(default_factory=dict)
    total_start_time: Optional[datetime] = None
    retry_count: Dict[str, int] = field(default_factory=dict)
    max_retries: int = 3
