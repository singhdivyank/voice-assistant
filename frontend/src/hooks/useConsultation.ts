import { useCallback } from 'react';
import { useConsultationStore } from '../store/consultationStore';
import type { Gender, Language } from '../api/types';

export const useConsultation = () => {
    const store = useConsultationStore();

    const updatePatient = useCallback((field: string, value: number | Gender | Language) => {
        store.setPatientData({ [field]: value });
    }, [store]);

    const nextStep = useCallback(() => {
        const phases = ['patient-info', 'complaint', 'questions', 'diagnosis', 'prescription', 'complete'] as const;
        const currentIndex = phases.indexOf(store.phase);
        if (currentIndex < phases.length - 1) {
            store.setPhase(phases[currentIndex + 1]);
        }
    }, [store]);

    const previousStep = useCallback(() => {
        const phases = ['patient-info', 'complaint', 'questions', 'diagnosis', 'prescription', 'complete'] as const;
        const currentIndex = phases.indexOf(store.phase);
        if (currentIndex > 0) {
            store.setPhase(phases[currentIndex - 1]);
        }
    }, [store]);

    const currentQuestion = store.sessionState?.questions[store.currentQuestionIndex] || null;
    const totalQuestions = store.sessionState?.questions.length || 0;
    const progress = totalQuestions > 0 ? (store.currentQuestionIndex / totalQuestions) : 0;

    return {
        ...store,
        updatePatient,
        nextStep,
        previousStep,
        currentQuestion,
        totalQuestions,
        progress,
    };
};