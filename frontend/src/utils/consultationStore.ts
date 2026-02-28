/**
 * Enhanced Zustand store with direct medication API call (no streaming)
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { SessionState, PatientFormData, Gender, Language, ConsultationPhase, ConversationTurn, DiagnosisQuestion } from '@/utils/';
import apiClient, { STTResponse } from '../api/client';
import { API_BASE_URL } from '@/utils/';

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
    medicationRecommendations: string;
    medicationEnglish: string | null;
    questions: string[];

    // Audio-specific state
    isRecording: boolean;
    isProcessingAudio: boolean;

    // Actions
    setPatientData: (data: Partial<PatientFormData>) => void;
    startVoiceConsultation: () => Promise<void>;
    submitAudioAnswer: (audioBlob: Blob) => Promise<void>;
    processInitialAudio: (audioBlob: Blob) => Promise<void>;
    reset: () => void;
    setPhase: (phase: ConsultationPhase) => void;
    setError: (error: string | null) => void;
    setRecording: (recording: boolean) => void;
    setSpeaking: (speaking: boolean) => void;
    setCurrentQuestion: (question: string) => void;
    setQuestions: (questions: DiagnosisQuestion[]) => void;
    playResponseAudio: (base64Audio: string) => Promise<void>;
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
                medicationRecommendations: '',
                medicationEnglish: null,
                questions: [],
                isRecording: false,
                isProcessingAudio: false,

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
                            currentQuestionIndex: 0,
                        });
                    } catch (err) {
                        const message = err instanceof Error ? err.message : 'Failed to start consultation';
                        set({ error: message, isLoading: false });
                        throw err;
                    }
                },

                processInitialAudio: async (audioBlob: Blob) => {
                    const { sessionId } = get();
                    if (!sessionId) {
                        throw new Error('No active session');
                    }

                    set({ isProcessingAudio: true, error: null });
                    try {
                        const response: STTResponse = await apiClient.transcribeAndRespond(
                            sessionId, 
                            audioBlob, 
                            0
                        );

                        const newConversation: ConversationTurn = {
                            question: "Please describe your main symptoms",
                            answer: response.transcribed_text
                        };

                        set({
                            conversationHistory: [newConversation],
                            currentQuestion: response.next_question,
                            currentQuestionIndex: response.current_index,
                            isProcessingAudio: false,
                        });
                        
                        if (response.response_audio) {
                            await get().playResponseAudio(response.response_audio);
                        }
                    } catch (err) {
                        const message = err instanceof Error ? err.message : 'Failed to process audio';
                        set({ error: message, isProcessingAudio: false });
                        throw err;
                    }
                },

                submitAudioAnswer: async (audioBlob: Blob) => {
                    const { sessionId, currentQuestion, conversationHistory, currentQuestionIndex } = get();
                    if (!sessionId || !currentQuestion) return;

                    set({ isProcessingAudio: true, error: null });

                    try {
                        console.log(`Question index at start in store: ${currentQuestionIndex}`)
                        const actualQuestionIndex = currentQuestionIndex;
                        console.log(`Submitting answer for question index: ${actualQuestionIndex}`);
                        
                        const response: STTResponse = await apiClient.transcribeAndRespond(
                            sessionId, 
                            audioBlob, 
                            actualQuestionIndex
                        );

                        const newConversation: ConversationTurn = {
                            question: currentQuestion,
                            answer: response.transcribed_text
                        };

                        const updatedHistory = [...conversationHistory, newConversation];

                        if (response.should_generate_recommendations) {
                            set({
                                conversationHistory: updatedHistory,
                                currentQuestion: null,
                                isProcessingAudio: false,
                                isProcessing: true,
                            });

                            try {
                                const medicationResponse = await apiClient.completeSession(sessionId);
                                
                                set({
                                    medicationRecommendations: medicationResponse.medication,
                                    medicationEnglish: medicationResponse.medication_english,
                                    isProcessing: false,
                                });
                                
                                try {
                                    const ttsResponse = await fetch(`${API_BASE_URL}/sessions/${sessionId}/speak-recommendations`, {
                                        method: 'POST'
                                    });
                                    const { audio } = await ttsResponse.json();
                                    await apiClient.playBase64Audio(audio);
                                } catch (ttsError) {
                                    console.error('Failed to speak recommendations:', ttsError);
                                }

                                set({
                                    isComplete: true,
                                });

                            } catch (medicationError) {
                                const message = medicationError instanceof Error ? medicationError.message : 'Failed to generate recommendations';
                                set({
                                    error: message,
                                    isProcessing: false,
                                });
                                throw medicationError;
                            }
                        } else {
                            const nextQuestionIndex = currentQuestionIndex + 1;
                            set({
                                conversationHistory: updatedHistory,
                                currentQuestion: response.next_question,
                                currentQuestionIndex: nextQuestionIndex,
                                isProcessingAudio: false,
                            });

                            if (response.response_audio) {
                                await get().playResponseAudio(response.response_audio);
                            }
                        }
                    } catch (err) {
                        const message = err instanceof Error ? err.message : 'Failed to submit audio answer';
                        set({ error: message, isProcessingAudio: false });
                        throw err;
                    }
                },

                playResponseAudio: async (base64Audio: string) => {
                    set({ isSpeaking: true });
                    try {
                        await apiClient.playBase64Audio(base64Audio);
                    } catch (err) {
                        console.error('Failed to play response audio:', err);
                    } finally {
                        set({ isSpeaking: false });
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
                    medicationRecommendations: '',
                    medicationEnglish: null,
                    questions: [],
                    isRecording: false,
                    isProcessingAudio: false,
                }),

                setPhase: (phase) => set({ phase }),
                setError: (error) => set({ error }),
                setRecording: (isRecording) => set({ isRecording }),
                setSpeaking: (isSpeaking) => set({ isSpeaking }),
                setCurrentQuestion: (question) => set({ currentQuestion: question }),
                setQuestions: (questions) => set({
                    questions: questions.map(q => q.question),
                    currentQuestion: questions[0]?.question || null,
                    currentQuestionIndex: 0
                }),
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