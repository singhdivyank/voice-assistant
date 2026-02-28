import { useState, useRef, useCallback } from 'react';
import { AudioRecordingHook, AudioRecordingOptions, ERROR_MESSAGES } from '@/utils/';

export const useAudioRecording = (options: AudioRecordingOptions = {}): AudioRecordingHook => {
    const { onRecordingComplete, onError } = options;

    const [isRecording, setIsRecording] = useState(false);
    const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
    const mediaRecordRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);

    const isSupported = typeof window !== 'undefined' && 'MediaRecorder' in window;

    const startRecording = useCallback(async () => {
        if (!isSupported) {
            onError?.('Audio recording not supported in this browser');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            audioChunksRef.current = [];
            setAudioBlob(null);
            let mimeType = 'audio/webm;codecs=opus'
            if (MediaRecorder.isTypeSupported('audio/wav')) {
                mimeType = 'audio/wav';
            } else if (MediaRecorder.isTypeSupported('audio/webm')) {
                mimeType = 'audio/webm';
            }

            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: mimeType
            });
            
            mediaRecordRef.current = mediaRecorder;
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                let finalMimeType = mimeType;
                if (mimeType === 'audio/webm') {
                    finalMimeType = 'audio/webm';
                }

                const audioBlob = new Blob(audioChunksRef.current, {
                    type: finalMimeType
                });
                setAudioBlob(audioBlob);
                onRecordingComplete?.(audioBlob);
                stream.getTracks().forEach(track => track.stop())
            };

            mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event);
                onError?.('Recorder failed');
                setIsRecording(false);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start(100);
            setIsRecording(true);
        } catch (error) {
            console.error('Failed to start recording:', error);
            if (error instanceof Error) {
                if (error.name === ERROR_MESSAGES.MICROPHONE_DENIED) {
                    onError?.(ERROR_MESSAGES['MICROPHONE_DENIED']);
                } else if (error.name === ERROR_MESSAGES.NOT_FOUND) {
                    onError?.(ERROR_MESSAGES['NOT_FOUND'])
                } else if (error.name === ERROR_MESSAGES.ACCESS_DENIED) {
                    onError?.(ERROR_MESSAGES['ACCESS_DENIED'])
                } else {
                    onError?.(ERROR_MESSAGES['RECORDING_ERROR'])
                }
            }
        }
    }, [isSupported, onError, onRecordingComplete]);

    const stopRecording = useCallback(() => {
        if (mediaRecordRef.current && isRecording) {
            mediaRecordRef.current.stop();
            setIsRecording(false);
        }
    }, [isRecording]);
    
    return {
        isRecording,
        isSupported,
        startRecording,
        stopRecording,
        audioBlob
    };
};