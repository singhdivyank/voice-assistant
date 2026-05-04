/**
 * Zustand store — V2 CrewAI multi-agent + Gmail MCP workflow
 *
 * Audio: browser Web Speech Synthesis only — no server TTS calls.
 *
 * Workflow:
 *   1. startVoiceConsultation  — set phase
 *   2-4. processInitialSymptom → questions[] → speak Q1 (browser)
 *   5-6. submitAnswer (repeated) → speak next question (browser)
 *   7. generateRecommendations (background) → speak recommendations (browser)
 *   9-10. sendPrescriptionForReview → Gmail MCP
 *   MCP. submitDoctorResponse
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  ConsultationPhase,
  ConversationTurn,
  DoctorAction,
  Gender,
  Language,
  MCPReviewState,
  PatientFormData,
  WorkflowStep,
} from '@/utils/';
import { v2Client, stopCurrentAudio, playBase64Audio } from '@/api/client';

interface ConsultationState {
  sessionId: string | null;
  workflowStep: WorkflowStep;
  patientData: PatientFormData;
  phase: ConsultationPhase;
  questions: string[];
  questionsEnglish: string[];
  conversationHistory: ConversationTurn[];
  currentQuestion: string | null;
  currentQuestionIndex: number;
  totalQuestions: number;
  medicationRecommendations: string;
  medicationEnglish: string;
  diagnosisInfo: {
    symptom_analysis: string;
    differential_diagnosis: string;
    final_diagnosis: string;
  } | null;
  mcpReview: MCPReviewState;
  prescriptionContent: string | null;
  isLoading: boolean;
  isProcessingAudio: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  isComplete: boolean;
  error: string | null;
  setPatientData: (data: Partial<PatientFormData>) => void;
  startVoiceConsultation: () => Promise<void>;
  processInitialSymptom: (audioBlob?: Blob, textComplaint?: string) => Promise<void>;
  submitAnswer: (answer: string) => Promise<void>;
  generateRecommendations: () => Promise<void>;
  sendPrescriptionForReview: () => Promise<void>;
  submitDoctorResponse: (emailContent: string) => Promise<void>;
  stopAudio: () => void;
  reset: () => void;
  setError: (error: string | null) => void;
  setSpeaking: (speaking: boolean) => void;
}

const initialPatientData: PatientFormData = {
  name: 'Guest User',
  email: 'guest.user@example.com',
  age: 30,
  gender: 'undisclosed' as Gender,
  language: 'en' as Language,
};

const initialMcpReview: MCPReviewState = {
  reviewId: null,
  doctorEmail: null,
  estimatedMinutes: null,
  action: null,
  modifications: null,
  rejectionReason: null,
  sentAt: null,
};

const initialState = {
  sessionId: null,
  workflowStep: 'welcome' as WorkflowStep,
  patientData: initialPatientData,
  phase: 'patient-info' as ConsultationPhase,
  questions: [],
  questionsEnglish: [],
  conversationHistory: [],
  currentQuestion: null,
  currentQuestionIndex: 0,
  totalQuestions: 0,
  medicationRecommendations: '',
  medicationEnglish: '',
  diagnosisInfo: null,
  mcpReview: initialMcpReview,
  prescriptionContent: null,
  isLoading: false,
  isProcessingAudio: false,
  isProcessing: false,
  isSpeaking: false,
  isComplete: false,
  error: null,
};

export const useConsultationStore = create<ConsultationState>()(
  devtools(
    persist(
      (set, get) => {

      // ── Browser TTS helper ──────────────────────────────────────────────
      // Speaks text immediately using Web Speech Synthesis.
      // Synchronous kick-off — no await, no server call.
      const speakText = (text: string): void => {
        const lang = get().patientData.language;

        // For non-English, backend gTTS gives guaranteed multilingual support.
        // Browser TTS is used for English only where it's universally reliable.
        if (lang !== 'en') {
          set({ isSpeaking: true });  // ← move this INSIDE the if block, BEFORE the void call
          void v2Client.generateRecommendationsAudio(text, lang)
            .then(r => { if (r.audio_base64) return playBase64Audio(r.audio_base64); })
            .catch(() => null)
            .finally(() => set({ isSpeaking: false }));
          return;
        }

        // English — use browser TTS instantly
        if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = 'en-US';
          utterance.rate = 0.9;
          utterance.onstart = () => set({ isSpeaking: true });
          utterance.onend   = () => set({ isSpeaking: false });
          utterance.onerror = () => set({ isSpeaking: false });
          window.speechSynthesis.speak(utterance);
        };

        return {
          ...initialState,

          setPatientData: (data) =>
            set((state) => ({ patientData: { ...state.patientData, ...data } })),

          setError: (error) => set({ error }),

          setSpeaking: (isSpeaking) => set({ isSpeaking }),

          stopAudio: () => {
            if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
              window.speechSynthesis.cancel();
            }
            stopCurrentAudio();
            set({ isSpeaking: false });
          },

          startVoiceConsultation: async () => {
            set({ isLoading: true, error: null });
            try {
              set({
                isLoading: false,
                phase: 'voice-consultation',
                workflowStep: 'initial_symptom',
              });
            } catch (err) {
              const message = err instanceof Error ? err.message : 'Failed to start consultation';
              set({ error: message, isLoading: false });
              throw err;
            }
          },

          processInitialSymptom: async (audioBlob?: Blob, textComplaint?: string) => {
            const { patientData, sessionId } = get();
            set({ isProcessingAudio: true, error: null });

            try {
              const result = await v2Client.processInitialSymptom({
                sessionId: sessionId ?? undefined,
                patientAge: patientData.age,
                patientGender: patientData.gender,
                language: patientData.language,
                initialComplaint: textComplaint,
                audioFile: audioBlob,
              });

              const firstQuestion = result.questions[0] ?? null;

              set({
                sessionId: result.session_id,
                questions: result.questions,
                questionsEnglish: result.questions_english,
                currentQuestion: firstQuestion,
                currentQuestionIndex: 0,
                totalQuestions: result.questions.length,
                workflowStep: 'questions_generated',
                isProcessingAudio: false,
                conversationHistory: result.transcribed_text
                  ? [{ question: 'Please describe your main symptoms', answer: result.transcribed_text }]
                  : [],
              });

              // Speak first question immediately via browser
              if (firstQuestion) speakText(firstQuestion);

            } catch (err) {
              const message = err instanceof Error ? err.message : 'Failed to process symptoms';
              set({ error: message, isProcessingAudio: false });
              throw err;
            }
          },

          submitAnswer: async (answer: string) => {
            const {
              sessionId,
              currentQuestion,
              currentQuestionIndex,
              conversationHistory,
              questions,
            } = get();

            if (!sessionId || !currentQuestion) return;

            set({ isProcessingAudio: true, error: null, workflowStep: 'qa_in_progress' });

            try {
              const result = await v2Client.answerQuestion(
                sessionId,
                currentQuestionIndex,
                answer
              );

              const newTurn: ConversationTurn = {
                question: currentQuestion,
                answer,
              };
              const updatedHistory = [...conversationHistory, newTurn];

              if (result.all_questions_answered) {
                set({
                  conversationHistory: updatedHistory,
                  currentQuestion: null,
                  workflowStep: 'qa_complete',
                  isProcessingAudio: false,
                });
                // Run recommendations in background — UI stays responsive
                void get().generateRecommendations();
              } else {
                const nextIndex = currentQuestionIndex + 1;
                const nextQuestion = questions[nextIndex] ?? null;
                set({
                  conversationHistory: updatedHistory,
                  currentQuestion: nextQuestion,
                  currentQuestionIndex: nextIndex,
                  workflowStep: 'qa_in_progress',
                  isProcessingAudio: false,
                });
                // Speak next question immediately via browser
                if (nextQuestion) speakText(nextQuestion);
              }
            } catch (err) {
              const message = err instanceof Error ? err.message : 'Failed to submit answer';
              set({ error: message, isProcessingAudio: false });
              throw err;
            }
          },

          generateRecommendations: async () => {
            const { sessionId } = get();
            if (!sessionId) return;

            set({ isProcessing: true, error: null, workflowStep: 'recommendations_generated' });

            try {
              const recResult = await v2Client.generateRecommendations(sessionId);

              set({
                medicationRecommendations: recResult.recommendations,
                medicationEnglish: recResult.recommendations_english,
                diagnosisInfo: recResult.diagnosis,
                isProcessing: false,
                workflowStep: 'audio_generated',
              });

              // Speak recommendations via browser TTS
              if (recResult.recommendations) {
                speakText(recResult.recommendations);
              }

            } catch (err) {
              const message = err instanceof Error ? err.message : 'Failed to generate recommendations';
              set({ error: message, isProcessing: false });
              throw err;
            }
          },

          sendPrescriptionForReview: async () => {
            const { sessionId, medicationRecommendations } = get();
            if (!sessionId || !medicationRecommendations) {
              set({ error: 'No session or recommendations available for prescription' });
              return;
            }

            set({ isProcessing: true, error: null });

            try {
              const result = await v2Client.generateAndReviewPrescription(
                sessionId,
                medicationRecommendations
              );

              set({
                workflowStep: 'prescription_sent',
                phase: 'prescription-review' as ConsultationPhase,
                isProcessing: false,
                mcpReview: {
                  reviewId: result.review_id,
                  doctorEmail: result.doctor_email,
                  estimatedMinutes: result.estimated_review_time,
                  action: null,
                  modifications: null,
                  rejectionReason: null,
                  sentAt: new Date().toISOString(),
                },
              });
            } catch (err) {
              const message = err instanceof Error ? err.message : 'Failed to send prescription for review';
              set({ error: message, isProcessing: false });
              throw err;
            }
          },

          submitDoctorResponse: async (emailContent: string) => {
            const { mcpReview } = get();
            if (!mcpReview.reviewId) {
              set({ error: 'No active prescription review found' });
              return;
            }

            set({ isProcessing: true, error: null });

            try {
              const result = await v2Client.processDoctorResponse(
                mcpReview.reviewId,
                emailContent
              );

              const action: DoctorAction = result.doctor_action;

              set({
                workflowStep: 'completed',
                isComplete: action === 'APPROVED' || action === 'MODIFIED',
                isProcessing: false,
                mcpReview: {
                  ...get().mcpReview,
                  action,
                  modifications: result.modifications,
                  rejectionReason: result.rejection_reason,
                },
              });
            } catch (err) {
              const message = err instanceof Error ? err.message : 'Failed to process doctor response';
              set({ error: message, isProcessing: false });
              throw err;
            }
          },

          reset: () => {
            if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
              window.speechSynthesis.cancel();
            }
            stopCurrentAudio();
            set({ ...initialState, patientData: get().patientData });
          },
        };
      },

      {
        name: 'consultation-storage-v2',
        partialize: (state) => ({
          patientData: state.patientData,
        }),
      }
    ),
    { name: 'ConsultationStoreV2' }
  )
);