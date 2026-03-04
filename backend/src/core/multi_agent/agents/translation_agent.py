from .base_agent import BaseAgent
from src.core.multi_agent.workflow.state_manager import AgentExecutionState


class TranslationAgent(BaseAgent):
    """Translation Agent to translate between user langauge and English"""

    def __init__(self):
        super().__init__("translation")

    async def _execute_logic(self, state: AgentExecutionState) -> AgentExecutionState:
        """Handle all translation needs"""

        from src.services.translation import TranslationService

        translated_content = {
            "transcribed_to_english": [],
            "questions_to_user": [],
            "recommendations_to_user": "",
        }

        translator = TranslationService(state.source_language)
        if state.transcribed_texts:
            english_texts = []
            for text in state.transcribed_texts:
                text = text.strip()
                if not text:
                    english_texts.append("")
                else:
                    english_text = translator.to_english(text)
                    english_texts.append(english_text)
            
            translated_content["transcribed_to_english"].extend(english_texts)
        
        if state.questions:
            user_questions = []
            for question in state.questions:
                user_question = translator.to_user_language(question)
                user_questions.append(user_question)
            
            translated_content["questions_to_user"].extend(user_questions)
        
        if state.medication_recommendations:
            user_recommendations = translator.to_user_language(state.medication_recommendations)
            translated_content["recommendations_to_user"] = user_recommendations
        
        state.translated_content.update(translated_content)
        state.agent_results["translation"] = {
            "translations_completed": len(translated_content),
            "target_language": state.source_language.value,
        }

        return state
