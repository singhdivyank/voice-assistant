"""Sequential medical workflow"""

import logging
from typing import Any, Dict, List, Optional

from crewai import Task, Crew

from src.api.schemas import SessionState, ConversationTurnSchema
from src.core.crew_ai.medical_agents import (
    speech_processor, translator, qna_generator,
    medication, prescription_specialist
)
from src.core.crew_ai.workflows import MCPWorkflowManager, SessionWorkflowManager
from src.utils.consts import MESSAGES
from src.utils.exceptions import DocJarvisError
from src.utils.task_descriptions import (
    DIAGNOSIS_TASK_DESCRIPTION,
    INTRO_TASK_DESCRIPTION,
    MEDICATION_TASK_DESCRIPTION,
    STT_TASK_DESCRIPTION,
    TRANSLATION_TASK_DESCRIPTION,
    TRANSLATION_DESCRIPTION,
    PRESCRIPTION_TASK_DESCRIPTION,
    PROCESS_RESPONSE_TASK_DESCRIPTION,
    QUESTION_TASK_DESCRIPTION,
    RECOMMENDATIONS_TASK_DESCRIPTION,
)

logger = logging.getLogger(__name__)


class MedicalCrew:
    """Unified medical assistant crew - handles all workflow logic and orchestration"""

    def __init__(self):
        self.agents = self._initialise_agents()
        self.session_manager = SessionWorkflowManager()
        self.mcp_manager = MCPWorkflowManager()
        self._initialised = False

    def _initialise_agents(self) -> Dict[str, Any]:
        """Initialise all agents"""
        return {
            "speech_processor": speech_processor,
            "translator": translator,
            "interviewer": qna_generator,
            "diagnostician": qna_generator,
            "pharmacist": medication,
            "prescription_agent": prescription_specialist,
        }
    
    async def initialise(self):
        """Initialise the medical crew and all components"""

        if self._initialised:
            return 
        
        try:
            await self.mcp_manager.initialise()
            self._initialised = True
            logger.info("Medical Assistant Crew initialised successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Medical Assistant Crew: {e}")
            raise DocJarvisError(f"Crew initialization failed: {str(e)}")
    
    async def generate_welcome_audio(self, language: str = "en") -> Dict[str, Any]:
        """Generate welcome message audio"""

        from src.utils.helpers import _extract_audio

        welcome_message = MESSAGES['intro'] + MESSAGES['instruction']
        welcome_task = Task(
            description=INTRO_TASK_DESCRIPTION.format(
                language=language,
                welcome_message=welcome_message,
            ),
            expected_output="Base64 encoded audio of welcome message",
            agent=self.agents['speech_agent']
        )
        crew = Crew(
            agents=[self.agents['speech_agent']],
            tasks=[welcome_task],
            verbose=True
        )

        try:
            result = crew.kickoff()
            audio_base64 = _extract_audio(str(result))
            logger.info("Welcome audio generated successfully")
            return {
                "status": "success",
                "audio_base64": audio_base64,
                "message": welcome_message,
                "step": "welcome_message_generation"
            }
        except Exception as e:
            logger.error(f"Failed to generate welcome audio: {e}")
            raise DocJarvisError(f"Welcome audio generation failed: {str(e)}")

    async def process_initial_symptom(
        self, 
        session_state: SessionState, 
        audio_file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Steps 2-4: Process initial symptom and generate 3 questions"""

        from src.utils.helpers import _extract_questions, _extract_transcription

        tasks = []
        context_data = {}
        
        try:
            if not audio_file_path:
                context_data['initial_complaint'] = session_state.initial_complaint
            else:
                stt_task = Task(
                    description=STT_TASK_DESCRIPTION.format(
                        audio_file_path=audio_file_path,
                        patient_language=session_state.language,
                    ),
                    expected_output="Clear transcription of patient's initial symptom description",
                    agent=self.agents['speech_processor']
                )
                tasks.append(stt_task)
                context_data['has_audio'] = True
            
            if session_state.language.lower() != 'en':
                translation_task = Task(
                    description=TRANSLATION_TASK_DESCRIPTION.format(
                        source_langauage=session_state.language,
                        initial_complaint=session_state.initial_complaint or 'From audio transcription'
                    ),
                    expected_output="Accurate English translation of patient complaint",
                    agent=self.agents['translation_agent'],
                    context=tasks if tasks else None
                )
                tasks.append(translation_task)
                context_data['needs_translation'] = True
            
            question_task = Task(
                description=QUESTION_TASK_DESCRIPTION.format(
                    patient_age = session_state.patient_age,
                    patient_gender = session_state.patient_gender,
                    initial_complaint = session_state.initial_complaint or 'Will be provided from previous tasks'
                ),
                expected_output="Exactly 3 relevant medical questions in JSON format",
                agent=self.agents['interviewer'],
                context=tasks if tasks else None
            )
            tasks.append(question_task)

            # Execute workflow
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=tasks,
                verbose=True,
                planning=True
            )
            result = crew.kickoff()

            # Extract and process results
            questions_english = _extract_questions(str(result))
            transcribed_text = _extract_transcription(str(result)) if audio_file_path else None

            questions_user_lang = questions_english if session_state.language.lower() == 'en' else await self._translate_questions_to_user_language(
                questions_english, session_state.language
            )

            logger.info(f"Generated {len(questions_english)} questions for session {session_state.session_id}")
            return {
                "status": "success",
                "questions": questions_user_lang,
                "questions_english": questions_english,
                "transcribed_text": transcribed_text,
                "step": "questions_generated",
                "session_id": session_state.session_id
            }
        except Exception as e:
            logger.error(f"Failed to process initial symptom: {e}")
            raise DocJarvisError(f"Initial symptom processing failed: {str(e)}")
    
    async def process_qa_answer(
        self, 
        session_state: SessionState, 
        question_index: int, 
        answer: str
    ) -> Dict[str, Any]:
        """Steps 5-6: Process individual Q&A answers"""

        try:
            while len(session_state.conversation) <= question_index:
                session_state.conversation.append(
                    ConversationTurnSchema(question="", answer="")
                )
            
            if question_index < len(session_state.questions):
                question = session_state.questions[question_index]
                session_state.conversation[question_index].question = question

            english_answer = answer if session_state.language.lower() == 'en' else await self._translate_text(answer, session_state.language, 'en')
            # store the English answer
            session_state.conversation[question_index].answer = english_answer
            # check if all questions have been answered
            answered_questions = sum(
                1 for turn in session_state.conversation[:len(session_state.questions)]
                if turn.answer and turn.answer.strip()
            )
            all_answered = answered_questions >= len(session_state.questions)

            logger.info(f"Q&A progress: {answered_questions}/{len(session_state.questions)} for {session_state.session_id}")
            return {
                "status": "success",
                "question_index": question_index,
                "answer_recorded": True,
                "answered_questions": answered_questions,
                "total_questions": len(session_state.questions),
                "all_questions_answered": all_answered,
                "next_step": "generate_recommendations" if all_answered else "continue_qa"
            }
        except Exception as e:
            logger.error(f"Failed to process Q&A answer: {e}")
            raise DocJarvisError(f"Q&A processing failed: {str(e)}")

    async def generate_recommednations(self, session_state: SessionState) -> Dict[str, Any]:
        """Step 7: Generate medication recommendations after all Q&A completed"""

        from src.utils.helpers import _format_qa_summary, _extract_diagnosis

        try:
            lines = [f"Initial complaint: {session_state.initial_complaint}"]
            conversation = session_state.conversation
            qa_summary = _format_qa_summary(lines, conversation)
            
            diagnosis_task = Task(
                description=DIAGNOSIS_TASK_DESCRIPTION.format(
                    age=session_state.patient_age,
                    gender=session_state.patient_gender,
                    initial_complaint=session_state.initial_complaint,
                    qa_summary=qa_summary
                ),
                expected_output="Comprehensive medical diagnosis with symptom analysis and differential diagnosis",
                agent=self.agents['diagnostician']
            )

            medication_task = Task(
                description=MEDICATION_TASK_DESCRIPTION.format(
                    age=session_state.patient_age,
                    gender=session_state.patient_gender
                ),
                expected_output="Comprehensive medication recommendations with safety guidelines",
                agent=self.agents['pharmacist'],
                context=[diagnosis_task]
            )

            crew = Crew(
                agents=[self.agents['diagnostician'], self.agents['pharmacist']],
                tasks=[diagnosis_task, medication_task],
                verbose=True,
                planning=True
            )
            result = crew.kickoff()

            recommendations = str(result)
            diagnosis_info = _extract_diagnosis(recommendations)
            recommendations_usr_lang = recommendations \
                if session_state.language.lower() == 'en' else await self._translate_text(
                    text=recommendations, 
                    source_lang='en', 
                    target_lang=session_state.language
                )

            logger.info(f"Generated medication recommendations for session {session_state.session_id}")
            return {
                "status": "success",
                "recommendations": recommendations_usr_lang,
                "recommendations_english": recommendations,
                "diagnosis": diagnosis_info,
                "step": "recommendations_generated"
            }
        except Exception as e:
            logger.error(f"Failed to generate medication recommendations: {e}")
            raise DocJarvisError(f"Medication recommendation generation failed: {str(e)}")
    
    async def generate_recommendations_audio(self, recommendations: str, language: str = "en") -> Dict[str, Any]:
        """Step 8: convert recommendations to audio for patient"""

        from src.utils.helpers import _extract_audio

        try:
            task = Task(
                description=RECOMMENDATIONS_TASK_DESCRIPTION.format(
                    lang=language,
                    recommendations=recommendations,
                ),
                expected_output="High-quality audio file of spoken recommendations",
                agent=self.agents['speech_processor']
            )

            crew = Crew(
                agents=[self.agents['speech_processor']],
                tasks=[task],
                verbose=True
            )
            result = crew.kickoff()

            audio_b64 = _extract_audio(str(result))
            logger.info("Recommendations audio generated successfully")
            return {
                "status": "success",
                "audio_base64": audio_b64,
                "step": "audio_recommendations_generated"
            }
        except Exception as e:
            logger.error(f"Failed to generate recommendations audio: {e}")
            raise DocJarvisError(f"Audio generation failed: {str(e)}")
    
    async def generate_and_review_prescriptions(
        self, 
        session_state: SessionState, 
        recommendations: str
    ) -> Dict[str, Any]:
        """Steps 9-10: Generate prescription and send GMail MCP review"""

        from src.utils.helpers import _extract_review, _format_conversation
        
        try:
            conversation_summary = _format_conversation(conversation=session_state.conversation)
            prescription_task = Task(
                description=PRESCRIPTION_TASK_DESCRIPTION.format(
                    session_id=session_state.session_id,
                    patient_age=session_state.patient_age,
                    patient_gender=session_state.patient_gender,
                    initial_complaint=session_state.initial_complaint,
                    conversation_summary=conversation_summary,
                    recommendations=recommendations
                ),
                expected_output="Prescription generated and sent for GMail MCP review with tracking information",
                agent=self.agents['prescription_agent']
            )
            
            crew = Crew(
                agents=[self.agents['prescription_agent']],
                tasks=[prescription_task],
                verbose=True
            )
            result = crew.kickoff()

            review_info = _extract_review(str(result))
            logger.info(f"Prescription sent for review: {review_info.get('review_id')} for session {session_state.session_id}")
            
            return {
                "status": "success",
                "prescription_generated": True,
                "review_requested": True,
                "review_id": review_info.get("review_id"),
                "doctor_email": review_info.get("doctor_email"),
                "estimated_review_time": review_info.get("estimated_time"),
                "step": "prescription_sent_for_review"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate and review prescription: {e}")
            raise DocJarvisError(f"Prescription generation and review failed: {str(e)}")

    async def process_doctor_response(self, review_id: str, email_content: str) -> Dict[str, Any]:
        """Process doctor's GMail response and finalise prescription"""

        from src.utils.helpers import _extract_doctor_response

        try:
            task = Task(
                description = PROCESS_RESPONSE_TASK_DESCRIPTION.format(
                    review_id=review_id,
                    email_content=email_content
                ),
                expected_output="Processed doctor response with recommended actions",
                agent=self.agents['prescription_agent']
            )

            crew = Crew(
                agents=[self.agents['prescription_agent']],
                tasks=[task],
                verbose=True
            )
            result = crew.kickoff()

            response_data = _extract_doctor_response(str(result))
            logger.info(f"Processed doctor response for review {review_id}: {response_data.get('action')}")
            return {
                "status": "success",
                "review_id": review_id,
                "doctor_action": response_data.get("action"),
                "modifications": response_data.get("modifications"),
                "rejection_reason": response_data.get("rejection_reason"),
                "step": "doctor_response_processed"
            }
        except Exception as e:
            logger.error(f"Failed to process doctor response: {e}")
            raise DocJarvisError(f"Doctor response processing failed: {str(e)}")
    
    async def _translate_questions_to_user_language(self, questions: List[str], target_language: str) -> List[str]:
        """Translate questions to user's language"""

        translated_questions = []

        for question in questions:
            try:
                translated = await self._translate_text(question, 'en', target_language)
                translated_questions.append(translated)
            except Exception as e:
                logger.warning(f"Translation failed for question, using original: {e}")
                translated_questions.append(question)
        
        return translated_questions

    def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Simple text translation using translation agent"""

        if source_lang.lower() == target_lang.lower():
            return text
        
        try:
            task = Task(
                description=TRANSLATION_DESCRIPTION.format(
                    source_lang=source_lang,
                    target_lang=target_lang,
                    text=text
                ),
                expected_output="Accurately translate text",
                agent=self.agents['translator']
            )
            crew = Crew(
                agents=[self.agents['translator']],
                tasks=[task],
                verbose=False
            )

            result = crew.kickoff()
            return str(result).strip()
        except Exception as e:
            logger.warning(f"Translation failed, returning original text: {e}")
            return text

medical_crew = MedicalCrew()
