import { useState, useCallback, useRef, useEffect } from 'react';
import { errorMessages } from '@/utils/';
import type { speechRecognitionHook, ISpeechRecognition, SpeechRecognitionResultListEvent, SpeechRecognitionOptions, SpeechRecognitionErrorEvent } from '@/utils/';

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
    } = options;

    const onResultRef = useRef(options.onResult);
    const onErrorRef  = useRef(options.onError);
    const onEndRef    = useRef(options.onEnd);

    useEffect(() => { onResultRef.current = options.onResult; });
    useEffect(() => { onErrorRef.current  = options.onError;  });
    useEffect(() => { onEndRef.current    = options.onEnd;    });
 
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript]   = useState('');
    const recognitionRef  = useRef<ISpeechRecognition | null>(null);
    
    const accumulatedRef  = useRef('');
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
            setIsListening(true);
        };
 
        recognition.onresult = (event: SpeechRecognitionResultListEvent) => {
            let finalChunk   = '';
            let interimChunk = '';
 
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalChunk += result[0].transcript;
                } else {
                    interimChunk += result[0].transcript;
                }
            }
 
            if (finalChunk) {
                accumulatedRef.current = (accumulatedRef.current + ' ' + finalChunk).trim();
            }

            const display = interimChunk
                ? (accumulatedRef.current + ' ' + interimChunk).trim()
                : accumulatedRef.current;
 
            setTranscript(display);
            onResultRef.current?.(display, !!finalChunk);
        };
 
        recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
            if (event.error !== 'aborted') {
                const message = errorMessages[event.error] ?? `Speech recognition error: ${event.error}`;
                onErrorRef.current?.(message);
            }
            setIsListening(false);
        };
 
        recognition.onend = () => {
            setIsListening(false);
            onEndRef.current?.();
        };
 
        return () => {
            recognition.abort();
        };
    // Only rebuild when language or continuous changes — NOT on callback changes
    }, [isSupported, language, continuous]);
 
    const startListening = useCallback(() => {
        if (!recognitionRef.current) {
            onErrorRef.current?.('Speech recognition not supported. Please use HTTPS and a modern browser.');
            return;
        }
        // Reset accumulator for fresh session
        accumulatedRef.current = '';
        setTranscript('');
        try {
            recognitionRef.current.start();
        } catch (error) {
            console.error('Failed to start speech recognition:', error);
            onErrorRef.current?.('Failed to start speech recognition.');
            setIsListening(false);
        }
    }, []);
 
    const stopListening = useCallback(() => {
        if (recognitionRef.current) {
            try {
                recognitionRef.current.stop();
            } catch (error) {
                console.warn('Error stopping recognition:', error);
            }
        }
    }, []);
 
    const resetTranscript = useCallback(() => {
        accumulatedRef.current = '';
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