import { useState, useCallback, useRef, useEffect } from 'react';

interface SpeechRecognitionOptions {
    language?: string;
    continuous?: boolean;
    onResult?: (transcript: string, isFinal: boolean) => void;
    onError?: (error: string) => void;
    onEnd?: () => void;
}

interface speechRecognitionHook {
    isListening: boolean;
    isSupported: boolean;
    transcript: string;
    startListening: () => void;
    stopListening: () => void;
    resetTranscript: () => void;
}

interface SpeechRecognitionEvent extends Event {
    results: SpeechRecognitionResultList;
    resultIndex: number;
}

interface SpeechRecognitionResultList {
    length: number;
    item(index: number): SpeechRecognitionResult;
    [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
    isFinal: boolean;
    length: number;
    item(index: number): SpeechRecognitionAlternative;
    [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
    transcript: string;
    confidence: number;
}

export const useSpeechRecognition = (options: SpeechRecognitionOptions = {}): speechRecognitionHook => {
    const {
        language = 'en-US',
        continuous = false,
        onResult,
        onError,
        onEnd,
    } = options;

    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');
    const recognitionRef = useRef<any>(null);

    const isSupported = typeof window != 'undefined' && 'speechRecognition' in window;
    useEffect(() => {
        if (!isSupported) return;

        const SpeechRecognition = (window as any).SpeechRecognition;
        recognitionRef.current = new SpeechRecognition();

        const recognition = recognitionRef.current;
        recognition.continuous = continuous;
        recognition.language = language;

        recognition.onResult = (event: SpeechRecognitionEvent) => {
            let transcript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (!result.isFinal) {
                    interimTranscript += result[0].transcript;
                } else {
                    transcript += result[0].transcript;
                }
            }

            const currTranscript = transcript || interimTranscript;
            setTranscript(currTranscript);
            onResult?.(currTranscript, !!transcript);
        };

        recognition.onrrror = (event: any) => {
            const errorMessages: Record<string, string> = {
                'no-speech': 'No speech detected. Please try again.',
                'audio-capture': 'Microphone not available.',
                'not-allowed': 'Microphone permission denied.',
                'network': 'Network error occurred.',
            };
            onError?.(errorMessages[event.error] || `Error: ${event.error}`);
            setIsListening(false);
        };

        recognition.onend = () => {
            setIsListening(false);
            onEnd?.();
        };

        return () => {
            recognition.abort();
        };
    }, [isSupported, language, continuous, onResult, onError, onEnd]);

    const startListening = useCallback(() => {
        if (!isSupported || !recognitionRef.current) return;
        
        setTranscript('');
        setIsListening(true);
        recognitionRef.current.start();
    }, [isSupported]);

    const stopListening = useCallback(() => {
        if (!recognitionRef.current) return;

        recognitionRef.current.stop();
        setIsListening(false);
    }, []);

    const resetTranscript = useCallback(() => {
        setTranscript('');
    }, []);

    return {
        isListening,
        isSupported,
        transcript,
        startListening,
        stopListening,
        resetTranscript,
    };
};