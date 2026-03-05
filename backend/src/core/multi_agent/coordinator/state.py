from collections import TypedDict
from typing import Annotated, Any, Dict, List
from operator import add

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """state of medical agentic graph"""

    messages: Annotated[List[BaseMessage], add]
    patient_info: Dict[str, Any]
    session_id: str
    is_approved: bool

def get_initial_state(session_id: str, patient_info: Dict[str, Any]) -> AgentState:
    """Utility to initialize the state for a new session."""
    
    return {
        "messages": [],
        "patient_info": patient_info,
        "session_id": session_id,
        "is_approved": False
    }
