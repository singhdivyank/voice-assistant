/**
 * Zustand store for voice-first consultation state management
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { SessionState, PatientFormData, Gender, Language, ConsultationPhase, ConversationTurn, DiagnosisQuestion } from '@/utils/';
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
    streamedMedicationEnglish: string | null;
    questions: string[],

    // Actions
    setPatientData: (data: Partial<PatientFormData>) => void;
    startVoiceConsultation: () => Promise<void>;
    submitVoiceAnswer: (answer: string) => Promise<void>;
    processInitialSymptoms: (symptoms: string) => Promise<void>;
    reset: () => void;
    setPhase: (phase: ConsultationPhase) => void;
    setError: (error: string | null) => void;
    setListening: (listening: boolean) => void;
    setSpeaking: (speaking: boolean) => void;
    setCurrentQuestion: (question: string) => void;
    setQuestions: (questions: DiagnosisQuestion[]) => void;
    updateInitialComplaint: (complaint: string) => void;
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
                streamedMedicationEnglish: null,
                questions: [],

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
                            initial_complaint: ""
                        });

                        set({
                            sessionId: response.session_id,
                            phase: 'voice-consultation',
                            isLoading: false,
                            conversationHistory: [],
                        });
                    } catch (err) {
                        const message = err instanceof Error ? err.message : 'Failed to start consultation';
                        set({ error: message, isLoading: false });
                        throw err;
                    }
                },

                processInitialSymptoms: async (symptoms: string) => {
                    const { sessionId } = get();
                    if (!sessionId) {
                        throw new Error('No active session');
                    }

                    set ({ isProcessing: true, error: null });
                    try {
                        const questionsResponse = await apiClient.generateQuestions(symptoms);
                        const questionStrings = questionsResponse.map(q => q.question);
                        set({
                            questions: questionStrings,
                            currentQuestion: questionStrings[0] || null,
                            currentQuestionIndex: 0,
                            isProcessing: false,
                        });
                        
                        await get().updateInitialComplaint(symptoms);
                    } catch (err) {
                        const message = err instanceof Error ? err.message: 'Failed to process symptoms';
                        set ({ error: message, isProcessing: false });
                        throw err;
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
                                () => {
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
                                },
                                (medicationEnglish) => {
                                    set({ streamedMedicationEnglish: medicationEnglish });
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
                    } catch (err) {
                        const message = err instanceof Error ? err.message : 'Failed to submit answer';
                        set({ error: message, isProcessing: false });
                        throw err;
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
                    streamedMedicationEnglish: null,
                }),

                setPhase: (phase) => set({ phase }),
                setError: (error) => set({ error }),
                setListening: (isListening) => set({ isListening }),
                setSpeaking: (isSpeaking) => set({ isSpeaking }),
                setCurrentQuestion: (question) => set({ currentQuestion: question }),
                setQuestions: (questions) => set({
                    questions: questions.map(q => q.question),
                    currentQuestion: questions[0]?.question || null,
                    currentQuestionIndex: 0
                }),
                updateInitialComplaint: async (complaint: string) => {
                    set((state) => ({
                        sessionState: state.sessionState ? {
                            ...state.sessionState,
                            initial_complaint: complaint
                        } : null
                    }))
                }
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