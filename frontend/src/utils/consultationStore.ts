/**
 * Zustand store — V2 CrewAI multi-agent + Gmail MCP workflow
 *
 * Workflow steps (mirrors backend WorkflowStep enum):
 *   1. generateWelcomeAudio
 *   2-4. processInitialSymptom  → questions[]
 *   5-6. answerQuestion (repeated until all_questions_answered)
 *   7. generateRecommendations
 *   8. generateRecommendationsAudio
 *   9-10. generateAndReviewPrescription  → review_id (MCP sends email to doctor)
 *   MCP. processDoctorResponse (APPROVE / MODIFY / REJECT)
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import {
  ConsultationPhase,
  ConversationTurn,
  DoctorAction,
  Gender,
  Language,
  MCPReviewState,
  PatientFormData,
  WorkflowStep,
} from '@/utils/';
import { v2Client, playBase64Audio } from '@/api/client';

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

  // initial session creation
  isLoading: boolean;
  // STT in progress
  isProcessingAudio: boolean;
  // any crew agent working
  isProcessing: boolean;
  // TTS playback in progress
  isSpeaking: boolean;
  // consultation fully done
  isComplete: boolean;
  error: string | null;

  setPatientData: (data: Partial<PatientFormData>) => void;
  /** Step 1: welcome audio + create V2 session via process-initial-symptom */
  startVoiceConsultation: () => Promise<void>;
  /** Steps 2-4: send audio or text complaint → receive questions */
  processInitialSymptom: (audioBlob?: Blob, textComplaint?: string) => Promise<void>;
  /** Steps 5-6: answer one Q&A question */
  submitAnswer: (answer: string) => Promise<void>;
  /** Step 7+8: generate recommendations text then TTS */
  generateRecommendations: () => Promise<void>;
  //Moves phase to 'prescription-review'.
  sendPrescriptionForReview: () => Promise<void>;

  //MCP: submit the doctor's email reply.
  submitDoctorResponse: (emailContent: string) => Promise<void>;

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
      (set, get) => ({
        ...initialState,

        setPatientData: (data) =>
          set((state) => ({ patientData: { ...state.patientData, ...data } })),

        setError: (error) => set({ error }),

        setSpeaking: (isSpeaking) => set({ isSpeaking }),

        startVoiceConsultation: async () => {
          set({ isLoading: true, error: null });
          try {
            // Play welcome audio (best-effort — don't block on failure)
            try {
              const welcome = await v2Client.generateWelcomeAudio(
                get().patientData.language
              );
              if (welcome.audio_base64) {
                set({ isSpeaking: true });
                await playBase64Audio(welcome.audio_base64).catch(() => null);
                set({ isSpeaking: false });
              }
            } catch {
              // Welcome audio is optional — continue even if it fails
            }

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
              // Seed conversation with the initial symptom turn
              conversationHistory: result.transcribed_text
                ? [{ question: 'Please describe your main symptoms', answer: result.transcribed_text }]
                : [],
            });
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
              // All Q&A done — move to recommendations
              set({
                conversationHistory: updatedHistory,
                currentQuestion: null,
                workflowStep: 'qa_complete',
                isProcessingAudio: false,
              });
              // Automatically kick off recommendations
              await get().generateRecommendations();
            } else {
              // Advance to next question
              const nextIndex = currentQuestionIndex + 1;
              const nextQuestion = questions[nextIndex] ?? null;
              set({
                conversationHistory: updatedHistory,
                currentQuestion: nextQuestion,
                currentQuestionIndex: nextIndex,
                workflowStep: 'qa_in_progress',
                isProcessingAudio: false,
              });
            }
          } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to submit answer';
            set({ error: message, isProcessingAudio: false });
            throw err;
          }
        },

        generateRecommendations: async () => {
          const { sessionId, patientData } = get();
          if (!sessionId) return;

          set({ isProcessing: true, error: null, workflowStep: 'recommendations_generated' });

          try {
            const recResult = await v2Client.generateRecommendations(sessionId);

            set({
              medicationRecommendations: recResult.recommendations,
              medicationEnglish: recResult.recommendations_english,
              diagnosisInfo: recResult.diagnosis,
            });

            try {
              const audioResult = await v2Client.generateRecommendationsAudio(
                recResult.recommendations,
                patientData.language
              );
              if (audioResult.audio_base64) {
                set({ isSpeaking: true, workflowStep: 'audio_generated' });
                await playBase64Audio(audioResult.audio_base64).catch(() => null);
                set({ isSpeaking: false });
              }
            } catch {
              // TTS failure is non-fatal
            }

            set({ isProcessing: false });
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
              phase: 'prescription-review',
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
        reset: () => set({ ...initialState, patientData: get().patientData }),
      }),

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