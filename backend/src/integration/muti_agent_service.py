import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import HTTPException

from src.config.monitoring import telemetry
from src.core.multi_agent import (
    AgentExecutionState, 
    WorkflowFactory, 
    llm_manager
)
from src.services.session_store import SessionStore
from src.utils.consts import (
    ConversationTurn, 
    DiagnosisSession, 
    Gender, 
    Language, 
    PatientInfo
)

logger = logging.getLogger(__name__)


class MultiAgentService:
    """Service layer that bridges FastAPI routes with the multi-agent system."""

    def __init__(self):
        self.workflow = WorkflowFactory.get_workflow()
        self._active_sessions: Dict[str, AgentExecutionState] = {}
        self._init_agents()
    
    def _init_agents(self):
        """Initialise workflow agents"""
        agents = self.workflow.agents
        self.qa_agent = agents["qa"]
        self.stt_agent = agents["stt"]
        self.tss_agent = agents["tss"]
        self.translation_agent = agents["translation"]
        self.diagnosis_agent = agents["diagnosis"]
        self.prescription_agent = agents["prescription"]
    
    async def create_session(
        self, 
        patient_age: int, 
        patient_gender: str, 
        language: str,
        initial_complaint: Optional[str] = None,
        session_store: Optional[SessionStore] = None
    ) -> Dict[str, Any]:
        """Create a new consultation session using the multi-agent system"""

        session_id = str(uuid.uuid4())

        with telemetry.span("create_session_multi_agent", {"session_id": session_id}):
            try:
                state = self._new_session_state(
                    session_id, patient_age, patient_gender, language
                )

                if initial_complaint:
                    await self._bootstrap_with_complaint(state, initial_complaint)
                
                await self._persistent_session_state(state, session_store)
                
                user_questions = state.translated_content.get(
                    "questions_to_user", state.questions
                )
                return {
                    "session_id": session_id,
                    "created_at": datetime.now(),
                    "status": "active",
                    "patient_age": patient_age,
                    "patient_gender": patient_gender,
                    "language": language,
                    "initial_complaint": initial_complaint or "",
                    "questions": user_questions,
                    "execution_id": state.execution_id
                }
            except Exception as e:
                logger.error("Failed to create session: %s", e)
                telemetry.increment_counter("session_creation_errors")
                raise HTTPException(status_code=500, detail=f"Session creation failed: {e}")
    
    async def transcribe_and_respond(
        self, 
        session_id: str, 
        audio_file_path: Path,
        question_index: int = 0,
        session_store: Optional[SessionStore] = None
    ) -> Dict[str, Any]:
        """Process audio input using STT and generate next response"""

        state = self.require_session_state(session_id)
        
        try:
            with telemetry.span("transcribe_and_respond_multi_agent", {"session_id": session_id}):
                transcribed_text = await self._run_stt_and_translation(state, audio_file_path)

                if not any(state.questions) and transcribed_text:
                    return await self._handle_initial_turn(
                        state, transcribed_text, session_store
                    )
                
                if question_index < len(state.questions) and transcribed_text:
                    return await self._handle_followup_turn(
                        state, transcribed_text, question_index, session_store
                    )
                
                raise HTTPException(status_code=400, detail="Invalid question index or missing transcription")
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Transcribe and respond failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
    
    async def handle_initial_turn(
        self,
        state: AgentExecutionState,
        transcribed_text: str,
        session_store: Optional[SessionStore],
    ) -> Dict[str, Any]:
        """"""

        state.translated_content["transcribed_to_english"] = [transcribed_text]
        state = await self.qa_agent.execute(state)
        state = await self.translation_agent.execute(state)
        state = await self.tss_agent.execute(state)

        await self._persist_session_state(state, session_store)
        next_question = state.translated_content.get(
            "questions_to_user", state.questions
        )[0] if state.questions else None

        return {
            "transcribed_text": transcribed_text,
            "next_question": next_question,
            "response_audio": state.response_audio,
            "is_complete": False,
            "should_generate_recommendations": False,
            "current_index": 0
        }
    
    async def complete_session(
        self, 
        session_id: str, 
        session_store: Optional[SessionStore] = None,
    ) -> Dict[str, Any]:
        """Complete session and generate final recommendations"""

        state = self._require_session_state(session_id)
        
        try:
            with telemetry.span("complete_session_multi_agent", {"session_id": session_id}):
                state = await self._run_final_agents(state)
                await self._mark_completed(state, session_store)
                
                user_recommendations = state.translated_content.get(
                    "recommendations_to_user",
                    state.medication_recommendations
                )

                medication_english = (
                    state.medication_recommendations 
                    if state.source_language != Language.ENGLISH 
                    else None
                )
                return {
                    "session_id": session_id,
                    "medication": user_recommendations,
                    "medication_english": medication_english
                }
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Session completion failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Session completion failed: {e}")
    
    async def complete_session_stream(
        self, 
        session_id: str, 
        session_store: Optional[SessionStore] = None
    ) -> AsyncIterator[str]:
        """Complete session with streaming recommendations"""

        state = self._require_session_state(session_id)
        
        from src.core.multi_agent.agents import PrescriptionAgent

        try:
            prescription_agent = PrescriptionAgent()
            state = await self.diagnosis_agent.execute(state)
            prompt = prescription_agent.medication_prompt.format(
                age=state.patient.age,
                gender=state.patient.gender.value,
                diagnosis=state.final_diagnosis,
                symptoms=state.symptom_analysis or "No detailed symptoms analysis"
            )

            full_response = []
            async for chunk in llm_manager.stream_llm(
                prompt,
                {"agent": "prescription_stream", "session_id": session_id}
            ):
                full_response.append(chunk)
                if state.source_language == Language.ENGLISH:
                    yield f"data: {chunk} \n\n"
                
            state.medication_recommendations = "".join(full_response)
            async for streamed_recommendations in self._stream_translated_recommendations(state):
                yield streamed_recommendations
            
            state = await self.prescription_agent.execute(state)
            await self._mark_completed(state, session_store)
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Streaming session completion failed: %s", e)
            yield f"data: [ERROR: {str(e)}]\n\n"
    
    async def generate_speech_response(
        self, 
        session_id: str, 
        text: Optional[str] = None
    ) -> str:
        """Generate TTS audio for recommendations"""

        state = self._require_session_state(session_id)
        
        try:
            text = text or state.translated_content.get(
                "recommendations_to_user",
                state.medication_recommendations,
            )
            
            if not text:
                raise HTTPException(status_code=404, detail="No recommendations found")

            temp_state = AgentExecutionState(**state.__dict__)
            temp_state.medication_recommendations = text
            temp_state = await self.tss_agent.execute(temp_state)
            return temp_state.response_audio or ""
        except HTTPException:
            raise
        except Exception as e:
            logger.error("TTS generation failed: %s", e)
            raise HTTPException(status_code=500, detail=f"TTS genration failed: {e}")
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session state for API responses"""

        state = self._get_session_state(session_id)
        if not state:
            return None
        
        user_questions = state.translated_content.get(
            "questions_to_user", state.questions
        )
        user_recommendations = state.translated_content.get(
            "recommendations_to_user", state.medication_recommendations
        )

        conversations = []
        for idx, (question, answer) in enumerate(
            zip(state.questions[:len(state.answers)], state.answers)
        ):
            user_question = user_questions[idx] if idx < len(user_questions) else question
            conversations.append({
                "question": user_question,
                "answer": answer
            })
        
        return {
            "session_id": session_id,
            "status": "completed" 
            if state.conversation_complete and state.medication_recommendations 
            else "active",
            "patient_age": state.patient.age,
            "patient_gender": state.patient.gender.value,
            "language": state.source_language.value,
            "initial_complaint": state.transcribed_texts[0] 
            if state.transcribed_texts 
            else "",
            "questions": user_questions,
            "conversation": conversations,
            "current_question_index": len(state.answers),
            "medication": user_recommendations,
            "prescription_path": str(state.prescription_path) 
            if state.prescription_path 
            else None,
            "agent_results": state.agent_results,
            "execution_id": state.execution_id
        }
    
    def _new_session_state(
        self,
        session_id: str,
        patient_age: int,
        patient_gender: str,
        language: str
    ) -> AgentExecutionState:
        """"""
        
        patient = PatientInfo(
            name="",
            email="",
            age=patient_age,
            gender=Gender.from_string(patient_gender)
        )
        return AgentExecutionState(
            patient=patient,
            session_id=session_id,
            source_language=Language.from_code(language),
            audio_files=[],
            transcribed_texts=[],
            questions=[],
            answers=[],
            conversation_complete=False,
            translated_content={},
            tts_files=[],
            response_audio=None,
            symptoms_analysis=None,
            differential_diagnosis=None,
            final_diagnosis=None,
            medication_recommendations=None,
            prescription_path=None,
            current_step="initial",
            errors=[],
            metadata={"created_at": datetime.now().isoformat()}
        )
    
    async def _bootstrap_with_complaint(
        self, 
        state: AgentExecutionState, 
        initial_complaint: str
    ) -> None:
        """"""

        state.transcribed_texts = [initial_complaint]
        state.transcribed_content["transcribed_to_english"] = [initial_complaint]
        state = await self.qa_agent.execute(state)
        state = await self.translation_agent.execute(state)
        self._active_sessions[state.session_id] = state
    
    async def _persist_session_state(
        self, 
        state: AgentExecutionState, 
        session_store: Optional[SessionStore]
    ) -> None:
        """Store in memory + optional legacy SessionStore"""

        self._active_sessions[state.session_id] = state
        if session_store:
            legacy_session = self._convert_to_legacy_session(state)
            await session_store.save(legacy_session)
    
    async def _run_stt_and_translaion(
        self, 
        state: AgentExecutionState, 
        audio_file_path: Path
    ) -> str:
        """"""
        state.audio_files = [audio_file_path]
        state = await self.stt_agent.execute(state)
        state = await self.translation_agent.execute(state)
        self._active_sessions[self.session_id] = state
        return state.transcribed_texts[0] if state.transcribed_texts else ""

    async def _handle_followup_turn(
        self,
        state: AgentExecutionState,
        transcribed_text: str,
        question_index: int,
        session_store: Optional[SessionStore]
    ) -> Dict[str, Any]:
        """"""

        while len(state.answers) <= question_index:
            state.answers.append("")
                
        english_answer = state.translated_content.get("transcribed_to_english", [transcribed_text])[0]
        state.answers[question_index] = english_answer

        if question_index + 1 >= len(state.questions):
            state.conversation_complete = True
            await self._persist_session_state(state, session_store)
            return {
                "transcribed_text": transcribed_text,
                "next_question": None,
                "response_audio": None,
                "is_complete": True,
                "should_generate_recommendations": True,
                "current_index": question_index + 1
            }
        
        state = self.tss_agent.execute(state)
        next_question_idx = question_index + 1
        next_question = state.translated_content.get("questions_to_user", state.questions)[next_question_idx]
        await self._persistent_session_state(state, session_store)

        return {
            "transcribed_text": transcribed_text,
            "next_question": next_question,
            "response_audio": state.response_audio,
            "is_complete": False,
            "should_generate_recommendations": False,
            "current_index": next_question_idx
        }
    
    async def _run_final_agents(self, state: AgentExecutionState) -> AgentExecutionState:
        """"""
        state = await self.diagnosis_agent.execute(state)
        state = await self.prescription_agent.execute(state)
        state = await self.translation_agent.execute(state)
        self._active_sessions[state.session_id] = state
        return state
    
    async def _mark_completed(
        self,
        state: AgentExecutionState,
        session_store: Optional[SessionStore]
    ) -> None:
        """"""

        if not session_store:
            return
        
        legacy_session = self._convert_to_legacy_session(state)
        legacy_session.status = "completed"
        await session_store.save(legacy_session)

    async def _stream_translated_recommendations(
        self, state: AgentExecutionState
    ) -> AsyncIterator[str]:
        """yield translated recommendations if needed."""

        if state.source_language == Language.ENGLISH:
                return
        
        state = await self.translation_agent.execute(state)
        user_recommendations = state.translated_content.get(
            "recommendations_to_user",
            self.medication_recommendations
        )
        yield f"data: {user_recommendations}\n\n"
        yield f"data: {json.dumps({'medication_english': state.medication_recommendations})}\n\n"

    def _get_session_state(self, session_id: str) -> Optional[AgentExecutionState]:
        """Get session state from memory"""
        return self._active_sessions.get(session_id)

    def _require_session_state(self, session_id: str) -> AgentExecutionState:
        state = self._get_session_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        return state
    
    def _convert_to_legacy_session(self, state: AgentExecutionState) -> DiagnosisSession:
        """Convert agent state to legacy DiagnosisSession format"""

        conversation = []
        for _, (question, answer) in enumerate(zip(state.questions[: len(state.answers)], state.answers)):
            conversation.append(ConversationTurn(question=question, answer=answer))
        
        return DiagnosisSession(
            session_id=state.session_id,
            patient=state.patient,
            initial_complaint=state.transcribed_texts[0] if state.transcribed_texts else "",
            conversation=conversation,
            questions=state.questions,
            medication=state.medication_recommendations,
            current_question_index=len(state.answers),
            status="completed" if state.conversation_complete and state.medication_recommendations else "active",
            language=state.source_language.value
        )
    
    def _get_session_state(self, session_id: str) -> Optional[AgentExecutionState]:
        return self._active_sessions.get(session_id)

    def _require_session_state(self, session_id: str) -> AgentExecutionState:
        state = self._get_session_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        return state
