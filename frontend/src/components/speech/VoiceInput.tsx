import React, { useState, useCallback } from 'react';
import { Mic, Square } from 'lucide-react';
import { useSpeechRecognition } from '@/hooks/';
import { Button } from '../ui/';
import { VoiceInputProps } from '@/utils/';

export const VoiceInput: React.FC<VoiceInputProps> = ({
    onTranscript,
    onError,
    language = 'en-US',
    placeholder = 'Click the microphone to start speaking ...',
    disabled = false,
}) => {
    const [transcript, setTranscript] = useState('');
    
    const handleResult = useCallback((text: string, isFinal: boolean) => {
        setTranscript(text);
        if (isFinal) {
            onTranscript(text);
        }
    }, [onTranscript]);

    const handleError = useCallback((error: string) => {
        onError?.(error);
    }, [onError]);

    const {
        isListening,
        isSupported,
        startListening,
        stopListening
    } = useSpeechRecognition({
        language,
        continuous: true,
        onResult: handleResult,
        onError: handleError,
    });

    const toggleListening = () => {
        if (!isListening) {
            setTranscript('');
            startListening();
        } else {
            stopListening();
        }
    };

    if (!isSupported) {
        return (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">
                Please use Chrome, Edge, or Safari.
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div
                className={`
                min-h-[100px] p-4 border rounded-lg transition-colors
                ${isListening ? 'border-red-300 bg-red-50' : 'border-gray-300 bg-gray-50'}
                `}
            >
                {transcript ? (
                    <p className="text-gray-800">{transcript}</p>
                ) : (
                    <p className="text-gray-400 italic">{placeholder}</p>
                )}
                {isListening && (
                    <span className="inline-block w-2 h-4 bg-red-500 ml-1 animate-pulse" />
                )}
            </div>

            <div className="flex items-center justify-center gap-4">
                <Button
                onClick={toggleListening}
                variant={isListening ? 'danger' : 'primary'}
                disabled={disabled}
                className={`
                    rounded-full w-16 h-16 p-0
                    ${isListening ? 'animate-pulse' : ''}
                `}
                aria-label={isListening ? 'Stop recording' : 'Start recording'}
                >
                {isListening ? (
                    <Square className="w-6 h-6" />
                ) : (
                    <Mic className="w-6 h-6" />
                )}
                </Button>
            </div>

            <p className="text-center text-sm text-gray-500">
                {isListening ? (
                <span className="text-red-600 font-medium">● Recording...</span>
                ) : (
                'Tap the microphone to speak'
                )}
            </p>
        </div>
    );
};