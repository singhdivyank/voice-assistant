import React, { useEffect, useState } from 'react';
import { Mic, Brain, Volume2, MicOff } from 'lucide-react';
import { useConsultationStore } from '../../store/consultationStore';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { useSpeechSynthesis } from '../../hooks/useSpeechSynthesis';
import { ConversationDisplay } from './ConversationDisplay';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Spinner } from '../ui/Spinner';
import { Alert } from '../ui/Alert';

export const VoiceConsultation: React.FC = () => {
    const {
        currentQuestion,
        isListening,
        isSpeaking,
        isProcessing,
        conversationHistory,
        streamedMedication,
        isComplete,
        submitVoiceAnswer,
        reset,
        error
    } = useConsultationStore();

    const [userResponse, setUserResponse] = useState('');
    
    const { speak, isSpeaking: synthesisSpeaking, cancel: cancelSpeech } = useSpeechSynthesis({
        language: 'en-US',
        rate: 0.9,
        onEnd: () => {
            if (currentQuestion && !isComplete) {
                setTimeout(() => {
                    startListening();
                }, 1000);
            }
        }
    });

    const {
        isListening: recognitionListening,
        transcript,
        startListening,
        stopListening,
        resetTranscript,
        isSupported
    } = useSpeechRecognition({
        language: 'en-US',
        continuous: false,
        onResult: (text, isFinal) => {
            if (isFinal && text.trim()) {
                setUserResponse(text);
                handleSubmitAnswer(text);
            }
        },
        onError: (error) => {
            console.error('Speech recognition error:', error);
        }
    });

    // Speak current question when it changes
    useEffect(() => {
        if (currentQuestion && !synthesisSpeaking && !isProcessing) {
            speak(currentQuestion);
        }
    }, [currentQuestion, speak, synthesisSpeaking, isProcessing]);

    // Speak final medication recommendations
    useEffect(() => {
        if (isComplete && streamedMedication && !synthesisSpeaking) {
            const introText = "Here are your medical recommendations: ";
            speak(introText + streamedMedication);
        }
    }, [isComplete, streamedMedication, speak, synthesisSpeaking]);

    const handleSubmitAnswer = async (answer: string) => {
        stopListening();
        resetTranscript();
        setUserResponse('');
        await submitVoiceAnswer(answer);
    };

    const handleStartListening = () => {
        if (synthesisSpeaking) {
            cancelSpeech();
        }
        resetTranscript();
        startListening();
    };

    const handleNewConsultation = () => {
        cancelSpeech();
        stopListening();
        reset();
    };

    if (!isSupported) {
        return (
            <Alert variant="error" title="Speech Not Supported">
                Your browser doesn't support speech recognition. Please use Chrome, Edge, or Safari for the voice consultation feature.
            </Alert>
        );
    }

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    {isProcessing ? (
                        <Brain className="w-8 h-8 text-blue-600" />
                    ) : synthesisSpeaking ? (
                        <Volume2 className="w-8 h-8 text-blue-600" />
                    ) : recognitionListening ? (
                        <Mic className="w-8 h-8 text-red-600 animate-pulse" />
                    ) : (
                        <MicOff className="w-8 h-8 text-gray-400" />
                    )}
                </div>
                <h2 className="text-2xl font-semibold text-gray-800">Voice Consultation</h2>
                <p className="text-gray-600 mt-2">
                    {isProcessing
                        ? 'Processing your responses...'
                        : synthesisSpeaking
                        ? 'AI is speaking...'
                        : recognitionListening
                        ? 'Listening to your response...'
                        : isComplete
                        ? 'Consultation complete'
                        : 'Waiting to begin...'}
                </p>
            </div>

            {/* Conversation History */}
            <ConversationDisplay conversations={conversationHistory} />

            {/* Current Question */}
            {currentQuestion && !isComplete && (
                <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
                    <div className="flex items-start justify-between">
                        <div className="flex-1">
                            <p className="text-sm font-medium text-blue-600 mb-2">Current Question</p>
                            <p className="text-lg text-gray-800">{currentQuestion}</p>
                        </div>
                    </div>
                </Card>
            )}

            {/* Live Transcript */}
            {recognitionListening && transcript && (
                <Card className="bg-yellow-50 border-yellow-200">
                    <p className="text-sm font-medium text-yellow-600 mb-2">You are saying...</p>
                    <p className="text-gray-800">{transcript}</p>
                </Card>
            )}

            {/* Processing State */}
            {isProcessing && (
                <Card className="text-center py-12">
                    <Spinner size="lg" className="mx-auto mb-4" />
                    <p className="text-gray-600 font-medium">AI is analyzing your responses...</p>
                    <p className="text-sm text-gray-400 mt-2">This may take a few moments</p>
                </Card>
            )}

            {/* Final Recommendations */}
            {isComplete && streamedMedication && (
                <Card>
                    <h3 className="font-semibold text-gray-800 mb-4">Medical Recommendations</h3>
                    <div className="prose-medication">
                        <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed">
                            {streamedMedication}
                        </pre>
                    </div>
                </Card>
            )}

            {/* Error Display */}
            {error && (
                <Alert variant="error">{error}</Alert>
            )}

            {/* Control Buttons */}
            <div className="flex justify-center gap-4">
                {!isComplete && !isProcessing && currentQuestion && (
                    <Button
                        onClick={handleStartListening}
                        variant={recognitionListening ? 'danger' : 'primary'}
                        size="lg"
                        leftIcon={recognitionListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                        disabled={synthesisSpeaking}
                    >
                        {recognitionListening ? 'Stop Listening' : 'Start Speaking'}
                    </Button>
                )}

                {(isComplete || error) && (
                    <Button
                        onClick={handleNewConsultation}
                        variant="secondary"
                        size="lg"
                    >
                        New Consultation
                    </Button>
                )}
            </div>

            {/* Medical Disclaimer */}
            <Alert variant="warning" title="Important">
                This AI consultation is for informational purposes only. Always consult a licensed healthcare provider for medical advice.
            </Alert>
        </div>
    );
};