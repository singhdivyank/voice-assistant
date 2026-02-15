/**
 * Typescript types for API communication
 */

export type Gender = 'male' | 'female' | 'other' | 'undisclosed';

export type Language = 
    | 'en' | 'hi' | 'bn' | 'gu' | 'kn'
    | 'ml' | 'ta' | 'te' | 'ur' | 'es'
    | 'fr' | 'zh' | 'ja' | 'ko' | 'mr';

export type SessionStatus = 'active' | 'completed' | 'cancelled';

export interface SessionCreate {
    patient_age: number;
    patient_gender: Gender;
    language: Language;
    initial_complaint: string;
}

export interface AnswerSubmit {
    question_index: number;
    answer: string;
}

export interface DiagnosisRequest {
    complaint: string;
}

export interface SessionResponse {
    session_id: string;
    created_at: string;
    status: SessionStatus;
    patient_age: number;
    patient_gender: Gender;
    language: Language;
    initial_complaint: string;
    questions: string[];
}

export interface ConversationTurn {
    question: string;
    answer: string;
}

export interface SessionState {
    session_id: string;
    status: SessionStatus;
    patient_age: number;
    patient_gender: Gender;
    language: Language;
    initial_complaint: string;
    questions: string[];
    conversation: ConversationTurn[];
    current_question_index: number;
    medication: string | null;
    prescription_path: string | null;
}

export interface DiagnosisQuestion {
    index: number;
    question: string;
    answered?: boolean;
}

export interface MedicationResponse {
    session_id: string;
    medication: string;
    disclaimer?: string;
}

export interface PrescriptionResponse {
    session_id: string;
    prescription_path: string;
    download_url: string;
}

export interface StreamingChunk {
    type: 'question' | 'medication' | 'error';
    contet: string;
    index?: number;
    is_final: boolean;
}

export interface ApiError {
    error: string;
    type: string;
}

export interface PatientFormData {
    age: number;
    gender: Gender;
    language: Language;
}

export interface ConsultationStep {
    id: number;
    name: string;
    description: string;
    completed: boolean;
    active: boolean;
}

export const LANGUAGES: Record<Language, string> = {
    en: 'English',
    hi: 'Hindi',
    bn: 'Bengali',
    gu: 'Gujrati',
    kn: 'Kannda',
    ml: 'Malayalam',
    mr: 'Marathi',
    ta: 'Tamil',
    te: 'Telugu',
    ur: 'Urdu',
    es: 'Spanish',
    fr: 'French',
    zh: 'Chinese',
    ja: 'Japanese',
    ko: 'Korean'
}

export const GENDERS: Record<Gender, string> = {
    male: 'Male',
    female: 'Female',
    other: 'Other',
    undisclosed: 'Prefer not to say',
};
