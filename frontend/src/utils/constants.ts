export type AlertVariant = 'info' | 'success' | 'warning' | 'error';
export type ButtonVariant = 'primary' | 'secondary' | 'success' | 'danger' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';
export type ConsultationPhase = 'patient-info' | 'voice-consultation' | 'prescription-review';
export type Language =
  | 'en' | 'hi' | 'bn' | 'gu' | 'kn'
  | 'ml' | 'ta' | 'te' | 'ur' | 'es'
  | 'fr' | 'zh' | 'ja' | 'ko' | 'mr';
export type Gender = 'male' | 'female' | 'other' | 'undisclosed';
export type SessionStatus = 'active' | 'completed' | 'cancelled';
export type WorkflowStep =
  | 'welcome'
  | 'initial_symptom'
  | 'questions_generated'
  | 'qa_in_progress'
  | 'qa_complete'
  | 'recommendations_generated'
  | 'audio_generated'
  | 'prescription_sent'
  | 'doctor_review'
  | 'completed'
  | 'error';

export type DoctorAction = 'APPROVED' | 'MODIFIED' | 'REJECTED' | 'TIMEOUT' | 'UNCLEAR'| 'ERROR';
export const API_BASE_V1 = import.meta.env.VITE_API_URL_V1 || 'http://localhost:8000/api/v1';
export const API_BASE_V2 = import.meta.env.VITE_API_URL_V2 || 'http://localhost:8000/api/v2';
export const API_BASE_URL = API_BASE_V1;
export const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const introText =
  "Welcome to your consultation. Your details have been confirmed. " +
  "Please describe your main symptoms clearly when you're ready. " +
  "Click start speaking, tell me about your symptoms, then click stop when you're finished.";

export const ERROR_MESSAGES: Record<string, string> = {
  NotAllowedError: 'Microphone access denied. Please allow microphone access and start again.',
  NotFoundError: 'No microphone found. Please check your microphone connection.',
  OverconstrainedError: 'Failed to access microphone. Please check your browser permissions.',
  default: 'Failed to start recording.',
};

export const VALIDATION = {
  MIN_COMPLAINT_LENGTH: 10,
  MAX_COMPLAINT_LENGTH: 2000,
  MIN_ANSWER_LENGTH: 1,
  MAX_ANSWER_LENGTH: 1000,
  MIN_AGE: 1,
  MAX_AGE: 90,
};

export const alertStyles: Record<AlertVariant, string> = {
  info:    'bg-blue-50 border-blue-200 text-blue-800',
  success: 'bg-green-50 border-green-200 text-green-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  error:   'bg-red-50 border-red-200 text-red-800',
};

export const paddingStyles = {
  none: '',
  sm:   'p-4',
  md:   'p-6',
  lg:   'p-8',
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
  primary:   'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
  secondary: 'bg-gray-200 text-gray-700 hover:bg-gray-300 focus:ring-gray-500',
  success:   'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500',
  danger:    'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
  ghost:     'bg-transparent text-gray-600 hover:bg-gray-100 focus:ring-gray-500',
};

export const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
};

export const LANGUAGE_MAP: Record<Language, string> = {
  en: 'en-US', hi: 'hi-IN', bn: 'bn-IN', mr: 'mr-IN', ta: 'ta-IN',
  te: 'te-IN', kn: 'kn-IN', ml: 'ml-IN', gu: 'gu-IN', ur: 'ur-PK',
  es: 'es-ES', fr: 'fr-FR', zh: 'zh-CN', ja: 'ja-JP', ko: 'ko-KR',
};

export const GENDERS_MAP: Record<Gender, string> = {
  male:        'Male',
  female:      'Female',
  other:       'Other',
  undisclosed: 'Prefer not to say',
};

export const errorMessages: Record<string, string> = {
  'no-speech':           'No speech detected. Please try again.',
  'audio-capture':       'Microphone not available.',
  'not-allowed':         'Microphone permission denied.',
  'network':             'Network error occurred.',
  'aborted':             'Speech recognition was aborted.',
  'service-not-allowed': "Speech service not allowed. Make sure you're using HTTPS.",
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

export interface ConversationDisplayProps {
  conversations: ConversationTurn[];
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

export interface PrescriptionPaneProps {
  content: string | null;
  medicationEnglish?: string | null;
  language?: string;
  isLoading?: boolean;
  className?: string;
}

export interface AudioRecordingOptions {
  onRecordingComplete?: (audioBlob: Blob) => void;
  onError?: (error: string) => void;
}

export interface AudioRecordingHook {
  isRecording: boolean;
  isSupported: boolean;
  startRecording: () => void;
  stopRecording: () => void;
  audioBlob: Blob | null;
}

export interface PatientFormData {
  name: string;
  email: string;
  age: number;
  gender: Gender;
  language: Language;
}

export interface ConversationTurn {
  question: string;
  answer: string;
}

export interface ConversationEntry {
  speaker: 'you' | 'doc';
  text: string;
}

export interface ConversationPaneProps {
  entries: ConversationEntry[];
  className?: string;
}

export interface AnswerSubmit {
  question_index: number;
  answer: string;
}

export interface DiagnosisRequest {
  complaint: string;
}

export interface DiagnosisQuestion {
  index: number;
  question: string;
  answered?: boolean;
}

export interface MedicationResponse {
  session_id: string;
  medication: string;
  medication_english?: string | null;
  disclaimer?: string;
}

export interface PrescriptionResponse {
  session_id: string;
  prescription_path: string;
  download_url: string;
}

export interface ApiError {
  error: string;
  type: string;
}

export interface StreamingChunk {
  type: 'question' | 'medication' | 'error';
  content: string;
  index?: number;
  is_final: boolean;
}

export interface SessionCreate {
  patient_name: string;
  patient_email: string;
  patient_age: number;
  patient_gender: Gender;
  language: Language;
  initial_complaint: string;
}

export interface SessionResponse {
  session_id: string;
  created_at: string;
  status: SessionStatus;
  patient_name: string;
  patient_email: string;
  patient_age: number;
  patient_gender: Gender;
  language: Language;
  initial_complaint: string;
  questions: string[];
}

export interface SessionState {
  session_id: string;
  status: SessionStatus;
  patient_name: string;
  patient_email: string;
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

export interface V2InitialSymptomRequest {
  session_id?: string;
  patient_age: number;
  patient_gender: string;
  language: string;
  initial_complaint?: string;
  audio_file?: File | Blob;
}

export interface V2InitialSymptomResponse {
  status: string;
  questions: string[];
  questions_english: string[];
  transcribed_text: string | null;
  step: string;
  session_id: string;
}

export interface V2WelcomeAudioResponse {
  status: string;
  audio_base64: string;
  message: string;
  step: string;
}

export interface V2AnswerResponse {
  status: string;
  question_index: number;
  answer_recorded: boolean;
  answered_questions: number;
  total_questions: number;
  all_questions_answered: boolean;
  next_step: string;
}

export interface V2RecommendationsResponse {
  status: string;
  recommendations: string;
  recommendations_english: string;
  diagnosis: {
    symptom_analysis: string;
    differential_diagnosis: string;
    final_diagnosis: string;
  };
  step: string;
}

export interface V2RecommendationsAudioResponse {
  status: string;
  audio_base64: string;
  step: string;
}

export interface V2PrescriptionResponse {
  status: string;
  prescription_generated: boolean;
  review_requested: boolean;
  review_id: string | null;
  doctor_email: string | null;
  estimated_review_time: number | null;
  step: string;
}

export interface V2DoctorResponseResult {
  status: string;
  review_id: string;
  doctor_action: DoctorAction;
  modifications: string | null;
  rejection_reason: string | null;
  step: string;
}

export interface V2SessionStatus {
  session_id: string;
  status: string;
  patient_age: number;
  patient_gender: string;
  language: string;
  initial_complaint: string;
  questions: string[];
  conversation: ConversationTurn[];
  progress: {
    total_questions: number;
    answered_questions: number;
    completion_percentage: number;
    all_answered: boolean;
  };
}

/** V2 MCP review state tracked in the store */
export interface MCPReviewState {
  reviewId: string | null;
  doctorEmail: string | null;
  estimatedMinutes: number | null;
  action: DoctorAction | null;
  modifications: string | null;
  rejectionReason: string | null;
  sentAt: string | null;
}
