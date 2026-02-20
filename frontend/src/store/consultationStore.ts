/**
 *  Zustand store for consultation state management
*/

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import {
    SessionState, PatientFormData, Gender, Language
} from '../api/types';
import apiClient from '../api/client';

export type ConsultationPhase = 
    | 'patient-info'
    | 'complaint'
    | 'questions'
    | 'diagnosis'
    | 'prescription'
    | 'complete';

interface ConsultationState {
    // Session data
    sessionId: string | null;
    sessionState: SessionState | null;

    // Form data
    patientData: PatientFormData;
    complaint: string;

    // UI state
    phase: ConsultationPhase;
    currentQuestionIndex: number;
    isLoading: boolean;
    isStreaming: boolean;
    error: string | null;

    // Streaming medication
    streamedMedication: string;

    // Actions
    setPatientData: (data: Partial<PatientFormData>) => void;
    setComplaint: (complaint: string) => void;
    startConsultation: () => Promise<void>;
    submitAnswer: (answer: string) => Promise<void>
    completeDiagnosis: (streaming?: boolean) => Promise<void>;
    generatePrescription: () => Promise<string>;
    reset: () => void;
    setPhase: (phase: ConsultationPhase) => void;
    setError: (error: string | null) => void;
}

const initialPatientData: PatientFormData = {
    age: 26,
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
                complaint: '',
                phase: 'patient-info',
                currentQuestionIndex: 0,
                isLoading: false,
                isStreaming: false,
                error: null,
                streamedMedication: '',

                setPatientData: (data) => 
                    set((state) => ({
                        patientData: { ...state.patientData, ...data }
                    })),
                
                setComplaint: (complaint) => set({ complaint }),

                startConsultation: async () => {
                    const { patientData, complaint } = get();

                    if (!complaint.trim()) {
                        set({error: "Please describe your symptoms"})
                        return;
                    }

                    set({ isLoading: true, error: null });

                    try {
                        const response = await apiClient.createSession({
                            patient_age: patientData.age,
                            patient_gender: patientData.gender,
                            language: patientData.language,
                            initial_complaint: complaint
                        });

                        const sessionState = await apiClient.getSession(response.session_id);

                        set({
                            sessionId: response.session_id,
                            sessionState,
                            phase: 'questions',
                            currentQuestionIndex: 0,
                            isLoading: false,
                        });
                    } catch (error) {
                        set({
                            error: error instanceof Error ? error.message : 'Failed to start consultation',
                            isLoading: false,
                        });
                    }
                },

                submitAnswer: async (answer: string) => {
                    const { sessionId, currentQuestionIndex, sessionState } = get();

                    if (!sessionId || !sessionState) return;

                    set({ isLoading: true, error: null });

                    try {
                        const response = await apiClient.submitAnswer(sessionId, {
                            question_index: currentQuestionIndex,
                            answer,
                        });

                        const updatedSession = await apiClient.getSession(sessionId);

                        if (response.is_complete) {
                            set({
                                sessionState: updatedSession,
                                phase: 'diagnosis',
                                isLoading: false,
                            });
                        } else {
                            set({
                                sessionState: updatedSession,
                                currentQuestionIndex: response.current_index,
                                isLoading: false
                            });
                        }
                    } catch (error) {
                        set({
                            error: error instanceof Error ? error.message : 'Failed to submit answer',
                            isLoading: false,
                        })
                    }
                },

                completeDiagnosis: async (streaming = true) => {
                    const { sessionId } = get();
                    if (!sessionId) return;

                    set({ isLoading: true, isStreaming: streaming, error: null, streamedMedication: ''});

                    try {
                        if (streaming) {
                            await apiClient.completeSessionStream(
                                sessionId,
                                (chunk) => {
                                    set((state) => ({
                                        streamedMedication: state.streamedMedication + chunk,
                                    }));
                                },
                                async () => {
                                    const updatedSession = await apiClient.getSession(sessionId);
                                    set({
                                        sessionState: updatedSession,
                                        phase: 'prescription',
                                        isLoading: false,
                                        isStreaming: false,
                                    });
                                },
                                (error) => {
                                    set({
                                        error: error.message,
                                        isLoading: false,
                                        isStreaming: false,
                                    });
                                }
                            );
                        } else {
                            const response = await apiClient.completeSession(sessionId);
                            const updatedSession = await apiClient.getSession(sessionId);

                            set({
                                sessionState: updatedSession,
                                streamedMedication: response.medication,
                                phase: 'prescription',
                                isLoading: false,
                            });
                        }
                    } catch (error) {
                        set({
                            error: error instanceof Error ? error.message : 'Failed to complete diagnosis',
                            isLoading: false,
                            isStreaming: false
                        });
                    }
                },

                generatePrescription: async () => {
                    const { sessionId } = get();
                    if (!sessionId) throw new Error('No session');

                    set({ isLoading: true, error: null });

                    try {
                        const response = await apiClient.generatePrescription(sessionId);
                        set ({ phase: 'complete', isLoading: false });
                        return response.download_url;
                    } catch (error) {
                        set({
                            error: error instanceof Error ? error.message : 'Failed to generate prescription',
                            isLoading: false
                        });
                        throw error;
                    }
                },

                reset: () => set({
                    sessionId: null,
                    sessionState: null,
                    patientData: initialPatientData,
                    complaint: '',
                    phase: 'patient-info',
                    currentQuestionIndex: 0,
                    isLoading: false,
                    isStreaming: false,
                    error: null,
                    streamedMedication: '',
                }),

                setPhase: (phase) => set({ phase }),
                setError: (error) => set({ error }),
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
