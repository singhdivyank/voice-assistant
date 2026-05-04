/**
 * API client for DocJarvis backend — V2 CrewAI workflow + MCP
 *
 * V1 endpoints are kept for backwards compatibility but the primary
 * consultation flow now uses V2 (/api/v2/workflow/*).
 */

import { API_BASE_V1, API_BASE_V2 } from '@/utils/';
import type {
  ApiError,
  DiagnosisQuestion,
  MedicationResponse,
  PrescriptionResponse,
  SessionCreate,
  SessionResponse,
  SessionState,
  V2WelcomeAudioResponse,
  V2InitialSymptomResponse,
  V2AnswerResponse,
  V2RecommendationsResponse,
  V2RecommendationsAudioResponse,
  V2PrescriptionResponse,
  V2DoctorResponseResult,
  V2SessionStatus,
} from '@/utils/';

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const config: RequestInit = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      error: 'Request failed',
      type: 'NetworkError',
    }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function requestForm<T>(url: string, formData: FormData): Promise<T> {
  const response = await fetch(url, { method: 'POST', body: formData });

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      error: 'Request failed',
      type: 'NetworkError',
    }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

class V1ApiClient {
  private base = API_BASE_V1;
  private url = (path: string) => `${this.base}${path}`;

  createSession(data: SessionCreate): Promise<SessionResponse> {
    return request(this.url('/sessions/'), {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  getSession(sessionId: string): Promise<SessionState> {
    return request(this.url(`/sessions/${sessionId}`));
  }

  deleteSession(sessionId: string): Promise<void> {
    return request(this.url(`/sessions/${sessionId}`), { method: 'DELETE' });
  }

  generateQuestions(complaint: string): Promise<DiagnosisQuestion[]> {
    return request(this.url('/diagnosis/questions'), {
      method: 'POST',
      body: JSON.stringify({ complaint }),
    });
  }

  generatePrescription(sessionId: string): Promise<PrescriptionResponse> {
    return request(this.url(`/prescription/${sessionId}/generate`), {
      method: 'POST',
    });
  }

  previewPrescription(sessionId: string): Promise<{ session_id: string; content: string }> {
    return request(this.url(`/prescription/${sessionId}/preview`));
  }

  getPrescriptionDownloadUrl(sessionId: string): string {
    return `${this.base}/prescription/${sessionId}/download`;
  }

  completeSession(sessionId: string): Promise<MedicationResponse> {
    return request(this.url(`/sessions/${sessionId}/complete`), { method: 'POST' });
  }

  healthCheck(): Promise<{ status: string; version: string }> {
    return request(this.url('/health'));
  }
}

class V2ApiClient {
  private base = API_BASE_V2;
  private wf = (path: string) => `${this.base}/workflow${path}`;

  /** Step 1 — Generate TTS welcome audio */
  generateWelcomeAudio(language = 'en'): Promise<V2WelcomeAudioResponse> {
    const fd = new FormData();
    fd.append('language', language);
    return requestForm(this.wf('/welcome-audio'), fd);
  }

  /**
   * Steps 2-4 — Send patient details + optional audio/text complaint.
   * Returns 3 diagnostic questions in the patient's language.
   */
  processInitialSymptom(params: {
    sessionId?: string;
    patientAge: number;
    patientGender: string;
    language: string;
    initialComplaint?: string;
    audioFile?: Blob;
  }): Promise<V2InitialSymptomResponse> {
    const fd = new FormData();
    if (params.sessionId) fd.append('session_id', params.sessionId);
    fd.append('patient_age', String(params.patientAge));
    fd.append('patient_gender', params.patientGender);
    fd.append('language', params.language);
    if (params.initialComplaint) fd.append('initial_complaint', params.initialComplaint);
    if (params.audioFile) fd.append('audio_file', params.audioFile, 'audio.wav');
    return requestForm(this.wf('/process-initial-symptom'), fd);
  }

  /**
   * Steps 5-6 — Submit a text answer to a question.
   * The backend's translation agent translates to English before storing.
   */
  answerQuestion(
    sessionId: string,
    questionIndex: number,
    answer: string
  ): Promise<V2AnswerResponse> {
    const fd = new FormData();
    fd.append('question_index', String(questionIndex));
    fd.append('answer', answer);
    return requestForm(this.wf(`/answer-question/${sessionId}`), fd);
  }

  /**
   * Step 7 — Generate medication recommendations via CrewAI diagnosis +
   * pharmacist agents. Call once all_questions_answered is true.
   */
  generateRecommendations(sessionId: string): Promise<V2RecommendationsResponse> {
    return request(this.wf(`/generate-recommendations/${sessionId}`), { method: 'POST' });
  }

  /**
   * Step 8 — Convert recommendations text to TTS audio in the patient's language.
   */
  generateRecommendationsAudio(
    recommendations: string,
    language = 'en'
  ): Promise<V2RecommendationsAudioResponse> {
    const fd = new FormData();
    fd.append('recommendations', recommendations);
    fd.append('language', language);
    return requestForm(this.wf('/recommendations-audio'), fd);
  }

  /**
   * Steps 9-10 — Generate prescription PDF and send to doctor via Gmail MCP.
   * Returns a review_id used to poll for the doctor's response.
   */
  generateAndReviewPrescription(
    sessionId: string,
    recommendations: string
  ): Promise<V2PrescriptionResponse> {
    const fd = new FormData();
    fd.append('recommendations', recommendations);
    return requestForm(this.wf(`/generate-prescription/${sessionId}`), fd);
  }

  /**
   * MCP — Submit doctor's email reply content for parsing.
   * The backend parses APPROVE/MODIFY/REJECT commands.
   */
  processDoctorResponse(
    reviewId: string,
    emailContent: string
  ): Promise<V2DoctorResponseResult> {
    const fd = new FormData();
    fd.append('review_id', reviewId);
    fd.append('email_content', emailContent);
    return requestForm(this.wf('/doctor-response'), fd);
  }

  /** Poll session status — includes Q&A progress */
  getSessionStatus(sessionId: string): Promise<V2SessionStatus> {
    return request(this.wf(`/session/${sessionId}/status`));
  }

  deleteSession(sessionId: string): Promise<{ message: string }> {
    return request(this.wf(`/session/${sessionId}`), { method: 'DELETE' });
  }

  workflowHealth(): Promise<{ status: string; crew_initialized: boolean; active_sessions: number }> {
    return request(this.wf('/health'));
  }
}

export function playBase64Audio(base64Audio: string): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      const byteCharacters = atob(base64Audio);
      const byteArray = new Uint8Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteArray[i] = byteCharacters.charCodeAt(i);
      }
      const blob = new Blob([byteArray], { type: 'audio/mp3' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
      audio.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Audio playback failed')); };
      audio.play();
    } catch (err) {
      reject(err);
    }
  });
}

export const v1Client = new V1ApiClient();
export const v2Client = new V2ApiClient();
export default v2Client;