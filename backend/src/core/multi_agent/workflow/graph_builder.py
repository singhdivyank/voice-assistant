import logging
import uuid
from datetime import datetime
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from .state_manager import AgentExecutionState
from src.config.monitoring import telemetry
from src.core.multi_agent.agents import (
    DiagnosisAgent,
    PrescriptionAgent,
    QuestionAnswerAgent,
    STTAgent, 
    TranslationAgent, 
    TTSAgent
)
from src.utils.exceptions import DocJarvisError

logger = logging.getLogger(__name__)


class AgentWorkflow:
    """LangGraph-based workflow orchestration"""

    def __init__(self):
        self.agents = {
            "stt": STTAgent(),
            "translation": TranslationAgent(),
            "qa": QuestionAnswerAgent(),
            "diagnosis": DiagnosisAgent(),
            "prescription": PrescriptionAgent(),
            "tts": TTSAgent(),
        }
        self.graph = self._build_graph()
        self.checkpointer = MemorySaver()
    
    def _build_graph(self) -> StateGraph:
        """Core logic of LangGraph workflow"""

        workflow = StateGraph(AgentExecutionState)
        for agent_name, agent in self.agents.items():
            workflow.add_node(agent_name, agent.execute)
        
        workflow.add_edge("stt", "translation")
        workflow.add_edge("translation", "qa")
        workflow.add_conditional_edges(
            "qa", 
            self._should_continue_qa, 
            {
                "continue": "tts",
                "complete": "diagnosis"
            }
        )
        workflow.add_edge("tts", END)
        workflow.add_edge("diagnosis", "prescription")
        workflow.add_edge("prescription", "translation")
        workflow.add_edge("translation", "tts")
        workflow.set_entry_point("stt")

        return workflow.compile(checkpointer=self.checkpointer)

    def _should_continue_qa(self, state: AgentExecutionState) -> str:
        """Determine if Q&A should continue or proceed to diagnosis"""
        if state.conversation_complete:
            return "complete"
        return "continue"
    
    async def execute_workflow(self, initial_state: AgentExecutionState) -> AgentExecutionState:
        """Execute the complete workflow"""

        initial_state.total_start_time = datetime.now()
        initial_state.execution_id = str(uuid.uuid4())

        telemetry.increment_counter("workflow_executions")
        try:
            with telemetry.span("workflow_execution", {"execution_id": initial_state.execution_id}):
                config = {"configurable": {"thread_id": initial_state.execution_id}}
                final_state = None
                
                async for state in self.graph.astream(initial_state, config):
                    final_state = state
                    logger.debug("Workflow state: %s", list(state.keys()))
                
                if initial_state.total_start_time:
                    total_duration = (datetime.now() - initial_state.total_start_time).total_seconds()
                    telemetry.record_histogram(
                        "workflow_duration",
                        total_duration * 1000,
                        attributes={"execution_id": initial_state.execution_id}
                    )
                    logger.info("Workflow completed in %.2fs", total_duration)
                    
                return final_state or initial_state
        except Exception as e:
            telemetry.increment_counter("workflow_errors")
            logger.error("Workflow execution failed: %s", e)
            raise DocJarvisError(f"Workflow execution failed: {e}") from e


class WorkflowFactory:
    """Factory for creating and managing workflows"""

    _workflow: Optional[AgentWorkflow] = None

    @classmethod
    def get_workflow(cls) -> AgentWorkflow:
        """Get or create workflow instance"""
        if cls._workflow is None:
            cls._workflow = AgentWorkflow()
            logger.info("AgentWorkflow initialised")
        return cls._workflow
    
    @classmethod
    def reset_factory(cls) -> None:
        """Reset workflow instance (for testing)"""
        cls._workflow = None
