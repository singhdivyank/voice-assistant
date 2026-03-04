import logging

from langchain.prompts import ChatPromptTemplate

from .base_agent import BaseAgent
from src.core.multi_agent.workflow.state_manager import AgentExecutionState
from src.utils.consts import AGENT_MEDICATION_PROMPT

logger = logging.getLogger(__name__)


class MedicationAgent(BaseAgent):
    """Medication Agent"""

    def __init__(self):
        super().__init__('medication_agent')
        self.medication_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a medical advisor. Please clear, actionable medical guidance"), 
            ("human", AGENT_MEDICATION_PROMPT)
        ])
    
    async def _execute_logic(self, state: AgentExecutionState) -> AgentExecutionState:
        """Generate medication recommendations"""

        if not state.conversation_complete:
            logger.info("Conversation incomplete, skipping medication")
            return state
        
        prompt = self.medication_prompt.format(
            age=state.patient.age,
            gender=state.patient.gender.value,
            diagnosis=state.final_diagnosis,
            symptoms=state.symptom_analysis or "No detailed symptoms analysis"
        )
        recommendations = await self.llm_manager.call_llm(
            prompt,
            {"agent": "prescription", "patient_age": state.patient.age}
        )

        state.medication_recommendations = recommendations
        return state
