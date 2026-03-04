"""State management for multi-agent execution"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.consts import Language, PatientInfo


@dataclass
class AgentExecutionState:
    """Extended state for agent execution tracking"""

    patient: PatientInfo
    session_id: str
    audio_files: List[Path]
    transcribed_texts: List[str]
    questions: List[str]
    answers: List[str]
    conversation_complete: bool
    symptoms_analysis: Optional[str]
    differential_diagnosis: Optional[str]
    final_diagnosis: Optional[str]
    source_language: Language
    translated_content: Dict[str, str]
    tts_files: List[Path]
    response_audio: Optional[str]
    medication_recommendations: Optional[str]
    prescription_path: Optional[Path]
    current_step: str
    errors: List[str]
    metadata: Dict
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_agent: Optional[str] = None
    completed_agents: List[str] = field(default_factory=list)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    agen_latencies: Dict[str, float] = field(default_factory=dict)
    total_start_time: Optional[datetime] = None
    retry_count: Dict[str, int] = field(default_factory=dict)
    max_retries: int = 3
    metadata = Dict[str, Any] = field(default_factory=dict)
