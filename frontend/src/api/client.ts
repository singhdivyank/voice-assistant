/**
 * API client for DocJarvis backend
*/

import { 
    API_BASE_URL,
    AnswerSubmit,  
    ApiError, 
    DiagnosisQuestion, 
    MedicationResponse,
    PrescriptionResponse,
    SessionCreate, 
    SessionResponse, 
    SessionState, 
    STTResponse,
} from '@/utils/';

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;
        const config: RequestInit = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        };

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const error: ApiError = await response.json().catch(() => ({
                    error: 'Request failed',
                    type: 'NetworkError'
                }));
                throw new Error(error.error || `HTTP ${response.status}`);
            }
            return response.json()
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            }
            throw new Error('Network request failed');
        }
    }

    // Session endpoints
    async createSession(data: SessionCreate): Promise<SessionResponse> {
        return this.request<SessionResponse>('/sessions/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async getSession(sessionId: string): Promise<SessionState> {
        return this.request<SessionState>(`/sessions/${sessionId}`)
    }

    async transcribeAndRespond(
        sessionId: string,
        audioBlob: Blob,
        questionIndex: number = 0
    ): Promise<STTResponse> {
        const url = `${this.baseUrl}/sessions/${sessionId}/transcribe?question_index=${questionIndex}`;
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'audio.wav');

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const error: ApiError = await response.json().catch(() => ({
                    error: 'Request failed',
                    type: 'NetworkError'
                }));
                throw new Error(error.error || `HTTP ${response.status}`)
            }

            return response.json();
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            }

            throw new Error('STT request failed');
        }
    }

    async submitAnswer(sessionId: string, data: AnswerSubmit): Promise<{
        status: string,
        current_index: number,
        is_complete: boolean,
        next_question: string | null;
    }>{
        return this.request(`/sessions/${sessionId}/answer`, {
            method: 'POST',
            body: JSON.stringify({
                question_index: data.question_index,
                answer: data.answer,
            }),
        });
    }

    async completeSession(sessionId: string): Promise<MedicationResponse> {
        return this.request<MedicationResponse>(`/sessions/${sessionId}/complete`, {
            method: 'POST',
        });
    }

    async completeSessionStream(
        sessionId: string,
        onChunk: (chunk: string) => void,
        onComplete: () => void,
        onError: (error: Error) => void,
        onEnglishParaphrase?: (medicationEnglish: string) => void
    ): Promise<void> {
        const url = `${this.baseUrl}/sessions/${sessionId}/complete/stream`;

        try {
            const response = await fetch(url, { method: 'POST' });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error('No response body');
            }

            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const lines = decoder.decode(value).split('\n');
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                        onComplete();
                        return;
                    }
                    try {
                        const parsed = JSON.parse(data) as { medication_english?: string };
                        if (parsed?.medication_english != null && onEnglishParaphrase) {
                            onEnglishParaphrase(parsed.medication_english);
                            continue;
                        }
                    } catch {
                        // not JSON, treat as text chunk
                    }
                    onChunk(data);
                }
            }

            onComplete();
        } catch (error) {
            onError(error instanceof Error ? error : new Error('Stream failed'));
        }
    }

    async deleteSession(sessionId: string): Promise<void> {
        return this.request(`/session/${sessionId}`, {method: 'DELETE'});
    }

    async generateQuestions(complaint: string): Promise<DiagnosisQuestion[]> {
        return this.request<DiagnosisQuestion[]>('/diagnosis/questions', {
            method: 'POST',
            body: JSON.stringify({ complaint }),
        });
    }

    async generatePrescription(sessionId: string): Promise<PrescriptionResponse> {
        return this.request<PrescriptionResponse>(`/prescription/${sessionId}/generate`, {
            method: 'POST',
        });
    }

    async previewPrescription(sessionId: string): Promise<{ session_id: string; content: string}>{
        return this.request(`/prescription/${sessionId}/promise`)
    }

    getPrescriptionDownloadUrl(sessionId: string): string {
        return `${this.baseUrl}/prescription/${sessionId}/download`;
    }

    async healthCheck(): Promise<{ status: string; version: string }> {
        return this.request('/health');
    }

    playBase64Audio(base64Audio: string): Promise<void>{
        return new Promise((resolve, reject) => {
            try {
                const byteCharacters = atob(base64Audio);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }

                const byteArray = new Uint8Array(byteNumbers);
                const audioBlob = new Blob([byteArray], { type: 'audio/mp3' });
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);

                audio.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                    resolve();
                };

                audio.onerror = () => {
                    URL.revokeObjectURL(audioUrl);
                    reject(new Error('Audio playback failed'));
                };

                audio.play();
            } catch (error) {
                reject(error);
            }
        });
    }
}

export const apiClient = new ApiClient();
export default apiClient;
export type { STTResponse };
