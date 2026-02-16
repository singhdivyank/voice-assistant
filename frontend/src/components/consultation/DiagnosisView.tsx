import React, { useEffect } from 'react';
import { Brain, AlertTriangle } from 'lucide-react';
import { useConsultationStore } from '../../store/consultationStore';
import { Card } from '../ui/Card';
import { Alert } from '../ui/Alert';
import { Spinner } from '../ui/Spinner';
import { SpeechControls } from '../speech/SpeechControls';

export const DiagnosisView: React.FC = () => {
    const {
        completeDiagnosis,
        streamedMedication,
        isLoading,
        isStreaming,
        error,
        patientData
    } = useConsultationStore();

    useEffect(() => {
        completeDiagnosis(true);
    }, [completeDiagnosis]);

    const languageCode = patientData.language == 'en' ? 'en-US' : patientData.language;
    return (
        <div className="space-y-6 max-w-2xl mx-auto animate-fade-in">
            <div className="text-center mb-6">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Brain className="w-8 h-8 text-blue-600" />
                </div>
                <h2 className="text-2xl font-semibold text-gray-800">Diagnosis & Recommendations</h2>
                <p className="text-gray-500 mt-2">
                Based on our conversation
                </p>
            </div>

            {(isLoading || isStreaming) && !streamedMedication && (
                <Card className="text-center py-12">
                <Spinner size="lg" className="mx-auto mb-4" />
                <p className="text-gray-600 font-medium">Analyzing your symptoms...</p>
                <p className="text-sm text-gray-400 mt-2">
                    This may take a moment
                </p>
                </Card>
            )}

            {streamedMedication && (
                <Card>
                <div className="flex items-start justify-between mb-4">
                    <h3 className="font-semibold text-gray-800">Medical Assessment</h3>
                    {!isStreaming && (
                    <SpeechControls 
                        text={streamedMedication} 
                        language={languageCode}
                    />
                    )}
                </div>
                <div className="prose-medication">
                    <pre className="whitespace-pre-wrap font-sans text-gray-800 leading-relaxed">
                    {streamedMedication}
                    {isStreaming && (
                        <span className="inline-block w-2 h-5 bg-blue-500 ml-1 animate-pulse" />
                    )}
                    </pre>
                </div>
                </Card>
            )}

            {error && (
                <Alert variant="error" title="Error">
                {error}
                </Alert>
            )}

            <Alert variant="warning" title="Important Disclaimer">
                <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                    <p>This is AI-generated advice for informational purposes only.</p>
                    <p className="mt-2 font-medium">
                    Please consult a licensed healthcare provider before making health decisions.
                    </p>
                </div>
                </div>
            </Alert>
        </div>
    );
};