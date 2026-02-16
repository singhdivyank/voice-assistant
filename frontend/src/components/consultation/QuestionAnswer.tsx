import React, { useState } from 'react';
import { MessageCircle, ArrowRight, Mic } from 'lucide-react';
import { useConsultationStore } from '../../store/consultationStore';
import { Button } from '../ui/Button';
import { TextArea } from '../ui/TextArea';
import { Card } from '../ui/Card';
import { Alert } from '../ui/Alert';
import { ProgressBar } from '../ui/ProgressBar';
import { VoiceInput } from '../speech/VoiceInput';
import { SpeechControls } from '../speech/SpeechControls';

export const QuestionAnswer: React.FC = () => {
    const {
        sessionState,
        currentQuestionIndex,
        submitAnswer,
        isLoading,
        error,
        patientData
    } = useConsultationStore();

    const [answer, setAnswer] = useState('');
    const [useVoice, setUseVoice] = useState(false);

    if (!sessionState) return null;

    const currentQuestion = sessionState.questions[currentQuestionIndex];
    const progress = ((currentQuestionIndex) / sessionState.questions.length) * 100;
    const isLastQuestion = currentQuestionIndex == sessionState.questions.length - 1;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!answer.trim()) return;
        await submitAnswer(answer);
        setAnswer('');
    };

    const handleVoiceTranscript = (text: string) => { setAnswer(text); };
    const langCode = patientData.language == 'en' ? 'en-US' : patientData.language;
    return (
        <div className="space-y-6 max-w-2xl mx-auto animate-fade-in">
            <div className="text-center mb-6">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MessageCircle className="w-8 h-8 text-blue-600" />
                </div>
                <h2 className="text-2xl font-semibold text-gray-800">Follow-up Questions</h2>
                <p className="text-gray-500 mt-2">
                Please answer these questions to help with the diagnosis
                </p>
            </div>

            <div className="space-y-2">
                <div className="flex justify-between text-sm text-gray-600">
                <span>Question {currentQuestionIndex + 1} of {sessionState.questions.length}</span>
                <span>{Math.round(progress)}% complete</span>
                </div>
            <ProgressBar value={progress} />
            </div>

            {sessionState.conversation.length > 0 && (
                <Card className="max-h-40 overflow-y-auto" padding="sm">
                <p className="text-xs font-medium text-gray-500 mb-2">Previous Answers</p>
                <div className="space-y-2">
                    {sessionState.conversation.map((turn, idx) => (
                    <div key={idx} className="text-sm">
                        <p className="text-gray-600">
                        <span className="font-medium">Q{idx + 1}:</span> {turn.question}
                        </p>
                        <p className="text-gray-800 pl-4">→ {turn.answer}</p>
                    </div>
                    ))}
                </div>
                </Card>
            )}

            <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
                <div className="flex items-start justify-between">
                <p className="text-lg text-gray-800 font-medium flex-1">
                    {currentQuestion}
                </p>
                <SpeechControls 
                    text={currentQuestion} 
                    language={langCode}
                />
                </div>
            </Card>

            <form onSubmit={handleSubmit} className="space-y-4">
                <Card>
                <div className="flex gap-2 mb-4">
                    <Button 
                    type="button" 
                    variant={!useVoice ? 'primary' : 'secondary'} 
                    size="sm" onClick={() => setUseVoice(false)}
                    >
                    Type
                    </Button>
                    <Button
                    type="button"
                    variant={useVoice ? 'primary' : 'secondary'}
                    size="sm"
                    onClick={() => setUseVoice(true)}
                    leftIcon={<Mic className="w-4 h-4" />}
                    >
                    Voice
                    </Button>
                </div>

                {useVoice ? (
                    <VoiceInput
                    onTranscript={handleVoiceTranscript}
                    language={langCode}
                    placeholder="Click the microphone and speak your answer..."
                    disabled={isLoading}
                    />
                ) : (
                    <TextArea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Type your answer here..."
                    rows={3}
                    disabled={isLoading}
                    />
                )}

                {useVoice && answer && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-700">{answer}</p>
                    </div>
                )}
                </Card>

                {error && ( <Alert variant="error">{error}</Alert> )}

                <Button
                type="submit"
                fullWidth
                isLoading={isLoading}
                disabled={!answer.trim() || isLoading}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                {isLoading 
                    ? 'Processing...' 
                    : isLastQuestion 
                    ? 'Complete & Get Diagnosis' 
                    : 'Next Question'
                }
                </Button>
            </form>
        </div>
    );
};