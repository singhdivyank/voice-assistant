export type AlertVariant = 'info' | 'success' | 'warning' | 'error';
export type ButtonVariant = 'primary' | 'secondary' | 'success' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';
export type ConsultationPhase = 'patient-info' | 'voice-consultation';

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

export const alertStyles: Record<AlertVariant, string> = {
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  success: 'bg-green-50 border-green-200 text-green-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  error: 'bg-red-50 border-red-200 text-red-800',
};

export const paddingStyles = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export const progressSizes = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
};

export const spinnerSizes = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-4',
};

export const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
  secondary: 'bg-gray-200 text-gray-700 hover:bg-gray-300 focus:ring-gray-500',
  success: 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
  ghost: 'bg-transparent text-gray-600 hover:bg-gray-100 focus:ring-gray-500',
};

export const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};

export interface HeaderProps {
    onSettingsClick?: () => void;
    onHelpClick?: () => void;
}

export interface SpeechControlProps {
    text: string;
    language?: string;
    autoPlay?: boolean;
    onStart?: () => void;
    onEnd?: () => void;
}

export interface VoiceInputProps {
    onTranscript: (text: string) => void;
    onError?: (error: string) => void;
    language?: string;
    placeholder?: string;
    disabled?: boolean;
}

export interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  onClose?: () => void;
}

export interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export interface ProgressBarProps {
  value: number;
  max?: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export interface SelectOption {
  value: string;
  label: string;
}

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export interface ConversationTurn {
  question: string,
  answer: string
}

export interface ConversationDisplayProps {
  conversations: ConversationTurn[]
}

export interface SpeechSynthesisOptions {
    language?: string;
    pitch?: number;
    rate?: number;
    volume?: number;
    voice?: string;
    onStart?: () => void;
    onEnd?: () => void;
    onError?: (error: string) => void;
}

export interface SpeechSynthesisHook {
    isSupported: boolean;
    isSpeaking: boolean;
    isPaused: boolean;
    voices: SpeechSynthesisVoice[];
    speak: (text: string) => void;
    pause: () => void;
    resume: () => void;
    cancel: () => void;
}

export interface SpeechRecognitionOptions {
    language?: string;
    continuous?: boolean;
    onResult?: (transcript: string, isFinal: boolean) => void;
    onError?: (error: string) => void;
    onEnd?: () => void;
}

export interface speechRecognitionHook {
    isListening: boolean;
    isSupported: boolean;
    transcript: string;
    startListening: () => void;
    stopListening: () => void;
    resetTranscript: () => void;
}

export interface SpeechRecognitionEvent extends Event {
    results: SpeechRecognitionResultList;
    resultIndex: number;
}
