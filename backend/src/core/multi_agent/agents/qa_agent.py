import logging
from typing import List

from langchain.prompts import ChatPromptTemplate

from .base_agent import BaseAgent
from src.core.multi_agent.workflow.state_manager import AgentExecutionState
from src.utils.consts import DIAGNOSIS_PROMPT

logger = logging.getLogger(__name__)


class QuestionAnswerAgent(BaseAgent):
    """Question-Answer Management Agent"""

    def __init__(self):
        super().__init__("qa")
        self.diagnosis_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a medical assessment assistant. Be thorough but concise"),
                ("human", DIAGNOSIS_PROMPT),
            ]
        )
    
    async def _execute_logic(self, state: AgentExecutionState) -> AgentExecutionState:
        """Generate questions and manage Q&A flow"""

        if not state.questions and state.transcribed_texts:
            translated_complaints = state.translated_content.get("transcribed_to_english", state.transcribed_texts)
            complaint = " ".join(translated_complaints)
            prompt = self.diagnosis_prompt.format(complaint=complaint)
            response = await self.llm_manager.call_llm(
                prompt, 
                {"agent": "qa", "task": "generate_questions"}
            )
            questions = self._parse_questions(response)
            state.questions = questions
            logger.info("Generated %d questions", len(questions))
        
        if len(state.answers) - len(state.questions) > 0:
            state.conversation_complete = True
        else:
            state.conversation_complete = False
        
        state.agent_results["qa"] = {
            "question_generated": len(state.questions),
            "answer_collected": len(state.asnwers),
            "conversation_completed": state.conversation_complete
        }

        return state
    
    def _parse_questions(self, response: str) -> List[str]:
        """Parse questions from LLM response"""

        import re

        questions = []
        for line in response.split("\n"):
            line = line.strip()
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
            if cleaned and len(cleaned) > 10:
                questions.append(cleaned)
        
        parsed_questions = questions[:3] if questions else ["Please describe your main symptoms"]
        return parsed_questions
