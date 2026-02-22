import { useState, useCallback, useRef, useEffect } from 'react';
import { SpeechRecognitionEvent, speechRecognitionHook, SpeechRecognitionOptions } from '@utils/constants';

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

    const isSupported = 
        typeof window != 'undefined' && (
            'webkitSpeechRecognition' in window ||
            'speechRecognition' in window
        ) && 
        (
            location.protocol === 'https:' ||
            location.hostname === 'localhost' ||
            location.hostname === '127.0.0.1'
        );
    useEffect(() => {
        if (!isSupported) {
            console.warn('Speech recognition not supported. Requirements:');
            console.warn('1. HTTPS connection (or localhost)');
            console.warn('2. Modern browser (Chrome, Edge, Safari)');
            console.warn('3. Microphone permissions');
            return;
        };

        const SpeechRecognition = 
            (window as any).webkitSpeechRecognition ||
            (window as any).SpeechRecognition;
        
        recognitionRef.current = new SpeechRecognition();

        const recognition = recognitionRef.current;
        recognition.continuous = continuous;
        recognition.language = language;
        recognition.interimResults = true;

        recognition.onstart = () => {
            console.log('Speech recognition started');
        };

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
                'aborted': 'Speech recognition was aborted.',
                'service-not-allowed': 'Speech service not allowed. Make sure you\'re using HTTPS.',
            };
            
            const errorMessage = errorMessages[event.error] || `Speech recognition error: ${event.error}`;
            onError?.(errorMessage);
            setIsListening(false);
        };

        recognition.onend = () => {
            console.log('Speech recognition ended');
            setIsListening(false);
            onEnd?.();
        };

        return () => {
            if (recognition) {
                recognition.abort();
            }
        };
    }, [isSupported, language, continuous, onResult, onError, onEnd]);

    const startListening = useCallback(() => {
        if (!isSupported) {
            onError?.(`Speech recognition not supported. Please use HTTPS and a modern browser.`);
            return;
        }
        
        if (!recognitionRef.current) {
            onError?.(`Speech recognition not initialized.`);
            return;
        }
        
        setTranscript('');
        setIsListening(true);
        try {
            recognitionRef.current.start();
        } catch (error) {
            console.error('Failed to start speech recognition:', error);
            onError?.('Failed to start speech recognition.');
            setIsListening(false);
        }
    }, [isSupported]);

    const stopListening = useCallback(() => {
        if (!recognitionRef.current) {
            recognitionRef.current.stop();
        }
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