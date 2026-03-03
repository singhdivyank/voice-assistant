import logging
from typing import Dict, List

from langchain.prompts import ChatPromptTemplate

from .base_agent import BaseAgent
from src.core.multi_agent.workflow.state_manager import AgentExecutionState
from src.utils.consts import AGENT_DIAGNOSIS_PROMPT

logger = logging.getLogger(__name__)


class DiagnosisAgent(BaseAgent):
    """Medical Diagnosis Agent"""

    def __init__(self):
        super().__init__("diagnosis_agent")
        self.dianosis_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a medical diagnosis assistant. Provide clear and structured analysis"), 
            ("human", AGENT_DIAGNOSIS_PROMPT)
        ])
    
    async def _execute_logic(self, state: AgentExecutionState) -> AgentExecutionState:
        """Perform medical diagnosis analysis"""

        if not state.conversation_complete:
            logger.info("Conversation incomplete, skipping diagnosis")
            return state
        
        qa_summary = ""
        for idx, (question, answer) in enumerate(zip(state.questions, state.answers), 1):
            qa_summary += f"Q{idx}: {question}\nA{idx}: {answer}\n\n"
        
        init_complaint = state.translated_content.get("transcribed_to_english", state.transcribed_texts[0])
        complaint = " ".join(init_complaint)
        prompt = self.analysis_prompt.format(
            age=state.patient.age,
            gender=state.patient.gender.value,
            complaint=complaint,
            qa_summary=qa_summary
        )

        response = await self.llm_manager.call_llm(
            prompt,
            {"agent": "diagnosis", "patient_age": state.patient.age}
        )
        parsed_response = self.parse_response(response)

        state.symptom_analysis = parsed_response.get('symptom_analysis')
        state.differential_diagnosis = parsed_response.get('differential_diagnosis')
        state.final_diagnosis = parsed_response.get('final_diagnosis')
        state.agent_results['diagnosis'] = {
            "diagnosis_complete": True,
            "sections_analyzed": parsed_response.get('sections_analysed')
        }
        
        logger.info("Diagnosis analysis completed")
        return state
    
    def parse_response(self, response: List) -> Dict[str, str | int]:
        """Parse LLM response for state manager"""
        
        parsed_response = {
            "symptom_analysis": "",
            "differential_diagnosis": "",
            "final_diagnosis": "",
            "sections_analysed": 0,
        }

        sections = response.split("\n\n")
        parsed_response.update({"sectios_analysed": len(sections)})
        if len(sections) > 0:
            parsed_response.update({"symptom_analysis": sections[0]})
        if len(sections) > 1:
            parsed_response.update({"differential_diagnosis": sections[1]})
        if len(sections) > 2:
            parsed_response.update({"final_diagnosis": sections[2]})
        
        return parsed_response
