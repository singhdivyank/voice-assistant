import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .state import AgentState
from src.config.monitoring import telemetry
from src.core.multi_agent.llm_manager import LLMManager
from src.core.multi_agent.tools.voice_tools import transcribe_audio, generate_voice_response
from src.core.multi_agent.tools.analysis_tools import analyze_symptoms_and_diagnose, recommend_medications
from src.core.multi_agent.tools.prescription_tools import create_prescription_document
from src.utils.consts import AGENTIC_DIAGNOSIS_PROMPT
from src.utils.exceptions import DocJarvisError

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """LangGraph-based workflow orchestration"""

    def __init__(self):
        self.llm_manager = LLMManager()
        self.tools = [
            transcribe_audio, 
            generate_voice_response,
            analyze_symptoms_and_diagnose, 
            recommend_medications,
            create_prescription_document
        ]
        self.model = self.llm_manager.llm.bind_tools(self.tools)

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self.call_model)
        workflow.add_node("action", ToolNode(self.tools))
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {"continue": "action", "end": END}
        )
        workflow.add_edge("action", "agent")

        self.memory=MemorySaver()
        self.app = workflow.compile(
            checkpointer=self.memory,
            interrupt_before=["create_prescription"]
        )
    
    def should_continue(self, state: AgentState) -> str:
        """Determines if the agent needs to call a tool or if it is done thinking"""
        last_message = state["messages"][-1]
        if not last_message.tool_calls:
            return "end"
        return "continue"
    
    async def call_model(self, state: AgentState) -> None:
        """Execute the complete workflow"""

        messages = state["messages"]
        state.total_start_time = datetime.now()
        state.execution_id = str(uuid.uuid4())

        telemetry.increment_counter("workflow_executions")
        try:
            with telemetry.span("workflow_execution", {"execution_id": state.execution_id}):
                logger.debug("Workflow state: %s", list(state.keys()))
                
                if not any(isinstance(m, SystemMessage) for m in messages):
                    messages = [SystemMessage(content=AGENTIC_DIAGNOSIS_PROMPT)] + messages
                
                response = await self.model.ainvoke(messages)
                total_duration = (datetime.now() - state.total_start_time).total_seconds()
                telemetry.record_histogram(
                    "workflow_duration",
                    total_duration * 1000,
                    attributes={"execution_id": state.execution_id}
                )
                logger.info("Workflow completed in %.2fs", total_duration)
                    
                return {"messages": [response]}
        except Exception as e:
            telemetry.increment_counter("workflow_errors")
            logger.error("Workflow execution failed: %s", e)
            raise DocJarvisError(f"Workflow execution failed: {e}") from e
    
    async def process_user_input(
            self, 
            user_input: str, 
            session_id: str, 
            patient_info: Dict[str, Any]
        ) -> str:
        """Entry point for FastAPI route to talk to agent"""

        config = {"configurable": {"thread_id": session_id}}
        inputs = {
            "messages": [HumanMessage(content=user_input)],
            "patient_info": patient_info,
            "session_id": session_id,
            "is_approved": False
        }

        final_state = None
        async for event in self.app.astream(inputs, config, stream_mode="values"):
            final_state = event
        
        return final_state["messages"][-1].content
