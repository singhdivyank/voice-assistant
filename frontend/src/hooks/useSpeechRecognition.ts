import { useState, useCallback, useRef, useEffect } from 'react';
import { errorMessages, SpeechRecognitionEvent, speechRecognitionHook, SpeechRecognitionOptions } from '@/utils/';

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
            setIsListening(true);
        };

        recognition.onResult = (event: SpeechRecognitionEvent) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (!result.isFinal) {
                    interimTranscript += result[0].transcript;
                } else {
                    finalTranscript += result[0].transcript;
                }
            }

            const currTranscript = finalTranscript || interimTranscript;
            setTranscript(currTranscript);

            if (onResult) {
                onResult(currTranscript, !!finalTranscript);
            }
        };

        recognition.onerror = (event: any) => {
            if (event.error !== 'aborted') {
                const errorMessage = errorMessages[event.error] || `Speech recognition error: ${event.error}`;
                onError?.(errorMessage);
            }
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
        if (!isSupported || !recognitionRef.current) {
            onError?.(`Speech recognition not supported. Please use HTTPS and a modern browser.`);
            return;
        }
        
        console.log('Starting to listen');
        setTranscript('');
        try {
            recognitionRef.current.start();
        } catch (error) {
            console.error('Failed to start speech recognition:', error);
            onError?.('Failed to start speech recognition.');
            setIsListening(false);
        }
    }, [isSupported, onError]);

    const stopListening = useCallback(() => {
        if (recognitionRef.current && isListening) {
            console.log('Stopping listening ...');
            try {
                recognitionRef.current.stop();
            } catch (error) {
                console.log('Error stopping recognition: ', error);
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