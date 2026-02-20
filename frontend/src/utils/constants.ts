export const API_BASE_URL = import .meta.env.VITA_API_URL || 'http://localhost:8000/api/v1';

export const API_CONFIG = {
    name: 'DocJarvis',
    version: '2.0.0',
    description: 'AI Medical Consultation Assistant'
};

export const CONSULTATION_PHASES = [
    { id: 'patient-info', label: 'Patient Info', description: 'Basic patient information' },
    { id: 'complaint', label: 'Symptoms', description: 'Describe your symptoms' },
    { id: 'questions', label: 'Questions', description: 'Answer follow-up questions' },
    { id: 'diagnosis', label: 'Diagnosis', description: 'AI-powered diagnosis' },
    { id: 'prescription', label: 'Prescription', description: 'Get your prescription' },
] as const;

export const ERROR_MESSAGES = {
    NETWORK_ERROR: 'Unable to connect to server',
    SESSION_EXPIRED: 'Your session has expired',
    INVALID_INPUT: 'Please check your input and try again',
    SERVER_ERROR: 'An unexpected error',
    SPEECH_NOT_SUPPORTED: 'Speech recognition is not supported in your browser',
    MICROPHONE_DENIED: 'Microphone access denied',
};

export const VALIDATION = {
    MIN_COMPLAINT_LENGTH: 10,
    MAX_COMPLAINT_LENGTH: 2000,
    MIN_ANSWER_LENGTH: 1,
    MAX_ANSWER_LENGTH: 1000,
    MIN_AGE: 1,
    MAX_AGE: 90
};

export const ANIMATION_DURATION = {
    fast: 150,
    normal: 300,
    slow: 500
};