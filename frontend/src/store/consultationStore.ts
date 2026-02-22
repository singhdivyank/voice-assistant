/**
 * Zustand store for voice-first consultation state management
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { SessionState, PatientFormData, Gender, Language } from '../api/types';
import { ConsultationPhase, ConversationTurn } from '@/utils';
import apiClient from '../api/client';

interface ConsultationState {
    // Session data
    sessionId: string | null;
    sessionState: SessionState | null;

    // Form data
    patientData: PatientFormData;

    // UI state
    phase: ConsultationPhase;
    currentQuestionIndex: number;
    isLoading: boolean;
    isProcessing: boolean;
    isListening: boolean;
    isSpeaking: boolean;
    isComplete: boolean;
    error: string | null;

    // Voice consultation state
    conversationHistory: ConversationTurn[];
    currentQuestion: string | null;
    streamedMedication: string;

    // Actions
    setPatientData: (data: Partial<PatientFormData>) => void;
    startVoiceConsultation: () => Promise<void>;
    submitVoiceAnswer: (answer: string) => Promise<void>;
    reset: () => void;
    setPhase: (phase: ConsultationPhase) => void;
    setError: (error: string | null) => void;
    setListening: (listening: boolean) => void;
    setSpeaking: (speaking: boolean) => void;
}

const initialPatientData: PatientFormData = {
    age: 30,
    gender: 'undisclosed' as Gender,
    language: 'en' as Language,
};

export const useConsultationStore = create<ConsultationState>()(
    devtools(
        persist(
            (set, get) => ({
                sessionId: null,
                sessionState: null,
                patientData: initialPatientData,
                phase: 'patient-info',
                currentQuestionIndex: 0,
                isLoading: false,
                isProcessing: false,
                isListening: false,
                isSpeaking: false,
                isComplete: false,
                error: null,
                conversationHistory: [],
                currentQuestion: null,
                streamedMedication: '',

                setPatientData: (data) =>
                    set((state) => ({
                        patientData: { ...state.patientData, ...data }
                    })),

                startVoiceConsultation: async () => {
                    const { patientData } = get();

                    set({ isLoading: true, error: null });

                    try {
                        const response = await apiClient.createSession({
                            patient_age: patientData.age,
                            patient_gender: patientData.gender,
                            language: patientData.language,
                            initial_complaint: "Patient has started describing symptoms"
                        });

                        const sessionState = await apiClient.getSession(response.session_id);
                        const firstQuestion = sessionState.questions[0] || "Please describe your main symptoms";

                        set({
                            sessionId: response.session_id,
                            sessionState,
                            phase: 'voice-consultation',
                            currentQuestion: firstQuestion,
                            currentQuestionIndex: 0,
                            isLoading: false,
                            conversationHistory: [],
                        });
                    } catch (error) {
                        set({
                            error: error instanceof Error ? error.message : 'Failed to start consultation',
                            isLoading: false,
                        });
                    }
                },

                submitVoiceAnswer: async (answer: string) => {
                    const { sessionId, currentQuestion, currentQuestionIndex, conversationHistory } = get();
                    if (!sessionId || !currentQuestion) return;
                    set({ isListening: false, isProcessing: true, error: null });

                    try {
                        const newConversation: ConversationTurn = {
                            question: currentQuestion,
                            answer: answer
                        };

                        const updatedHistory = [...conversationHistory, newConversation];
                        const response = await apiClient.submitAnswer(sessionId, {
                            question_index: currentQuestionIndex,
                            answer,
                        });

                        if (response.is_complete) {
                            set({
                                conversationHistory: updatedHistory,
                                currentQuestion: null,
                                isProcessing: true,
                            });

                            await apiClient.completeSessionStream(
                                sessionId,
                                (chunk) => {
                                    set((state) => ({
                                        streamedMedication: state.streamedMedication + chunk,
                                    }));
                                },
                                async () => {
                                    set({
                                        isComplete: true,
                                        isProcessing: false,
                                    });
                                },
                                (error) => {
                                    set({
                                        error: error.message,
                                        isProcessing: false,
                                    });
                                }
                            );
                        } else {
                            const updatedSession = await apiClient.getSession(sessionId);
                            const nextQuestion = updatedSession.questions[response.current_index];

                            set({
                                conversationHistory: updatedHistory,
                                currentQuestion: nextQuestion,
                                currentQuestionIndex: response.current_index,
                                isProcessing: false,
                            });
                        }
                    } catch (error) {
                        set({
                            error: error instanceof Error ? error.message : 'Failed to submit answer',
                            isProcessing: false,
                        });
                    }
                },

                reset: () => set({
                    sessionId: null,
                    sessionState: null,
                    patientData: initialPatientData,
                    phase: 'patient-info',
                    currentQuestionIndex: 0,
                    isLoading: false,
                    isProcessing: false,
                    isListening: false,
                    isSpeaking: false,
                    isComplete: false,
                    error: null,
                    conversationHistory: [],
                    currentQuestion: null,
                    streamedMedication: '',
                }),

                setPhase: (phase) => set({ phase }),
                setError: (error) => set({ error }),
                setListening: (isListening) => set({ isListening }),
                setSpeaking: (isSpeaking) => set({ isSpeaking }),
            }),
            {
                name: 'consultation-storage',
                partialize: (state) => ({
                    patientData: state.patientData,
                }),
            }
        ),
        { name: 'ConsultationStore' }
    )
);