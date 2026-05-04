import { useState, useCallback, useRef, useEffect } from 'react';
import { errorMessages } from '@/utils/';
import type { speechRecognitionHook, ISpeechRecognition, SpeechRecognitionResultListEvent, SpeechRecognitionOptions } from '@/utils/';

type SpeechRecognitionCtor = new () => ISpeechRecognition;

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
    if (typeof window === 'undefined') return null;
    const w = window as Window & {
        webkitSpeechRecognition?: SpeechRecognitionCtor;
        SpeechRecognition?: SpeechRecognitionCtor;
    };
    return w.webkitSpeechRecognition ?? w.SpeechRecognition ?? null;
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
    const recognitionRef = useRef<ISpeechRecognition | null>(null);

    const isSupported = getSpeechRecognitionCtor() !== null;

    useEffect(() => {
        const Ctor = getSpeechRecognitionCtor();
        if (!Ctor) {
            console.warn('Speech recognition not supported. Requires HTTPS and Chrome/Edge/Safari.');
            return;
        }

        const recognition = new Ctor();
        recognitionRef.current = recognition;

        recognition.continuous = continuous;
        recognition.lang = language;
        recognition.interimResults = true;

        recognition.onstart = () => {
            console.warn('Speech recognition started');
            setIsListening(true);
        };

        recognition.onresult = (event: SpeechRecognitionResultListEvent) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript;
                } else {
                    interimTranscript += result[0].transcript;
                }
            }

            const currTranscript = finalTranscript || interimTranscript;
            setTranscript(currTranscript);
            onResult?.(currTranscript, !!finalTranscript);
        };

        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            if (event.error !== 'aborted') {
                const message = errorMessages[event.error] ?? `Speech recognition error: ${event.error}`;
                onError?.(message);
            }
            setIsListening(false);
        };

        recognition.onend = () => {
            console.warn('Speech recognition ended');
            setIsListening(false);
            onEnd?.();
        };

        return () => {
            recognition.abort();
        };
    }, [isSupported, language, continuous, onResult, onError, onEnd]);

    const startListening = useCallback(() => {
        if (!recognitionRef.current) {
            onError?.('Speech recognition not supported. Please use HTTPS and a modern browser.');
            return;
        }
        console.warn('Starting to listen');
        setTranscript('');
        try {
            recognitionRef.current.start();
        } catch (error) {
            console.error('Failed to start speech recognition:', error);
            onError?.('Failed to start speech recognition.');
            setIsListening(false);
        }
    }, [onError]);

    const stopListening = useCallback(() => {
        if (recognitionRef.current && isListening) {
            console.warn('Stopping listening...');
            try {
                recognitionRef.current.stop();
            } catch (error) {
                console.warn('Error stopping recognition:', error);
            }
        }
    }, [isListening]);

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