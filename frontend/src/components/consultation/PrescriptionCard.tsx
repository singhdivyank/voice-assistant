import React, { useState } from 'react';
import { FileText, Download, RefreshCw, CheckCircle } from 'lucide-react';
import { useConsultationStore } from '../../store/consultationStore';
import { apiClient } from '../../api/client';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Alert } from '../ui/Alert';

export const PrescriptionCard: React.FC = () => {
    const {
        sessionId,
        sessionState,
        streamedMedication,
        generatePrescription,
        isLoading,
        reset,
        error
    } = useConsultationStore();

    const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
    const [generated, setGenerated] = useState(false);

    const handleGeneratePrescription = async () => {
        try {
            await generatePrescription();
            setDownloadUrl(apiClient.getPrescriptionDownloadUrl(sessionId!));
            setGenerated(true);
        } catch (err) {}
    };

    const handleNewConsultation = () => { reset(); };
    return (
        <div className="space-y-6 max-w-2xl mx-auto animate-fade-in">
            <div className="text-center mb-6">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                {generated ? (
                    <CheckCircle className="w-8 h-8 text-green-600" />
                ) : (
                    <FileText className="w-8 h-8 text-green-600" />
                )}
                </div>
                <h2 className="text-2xl font-semibold text-gray-800">
                {generated ? 'Prescription Ready' : 'Your Consultation Summary'}
                </h2>
                <p className="text-gray-500 mt-2">
                {generated 
                    ? 'Your prescription document has been generated'
                    : 'Review your diagnosis and generate a prescription'
                }
                </p>
            </div>

            {sessionState && (
                <Card padding="sm" className="bg-gray-50">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <p className="text-gray-500">Patient</p>
                            <p className="font-medium">
                                {sessionState.patient_age} years, {sessionState.patient_gender}
                            </p>
                        </div>
                        <div>
                            <p className="text-gray-500">Questions Answered</p>
                            <p className="font-medium">{sessionState.conversation.length}</p>
                        </div>
                    </div>
                </Card>
            )}

            <Card>
                <h3 className="font-semibold text-gray-800 mb-3">Diagnosis & Recommendations</h3>
                    <div className="prose-medication max-h-64 overflow-y-auto">
                        <pre className="whitespace-pre-wrap font-sans text-gray-700 text-sm leading-relaxed">
                            {streamedMedication}
                        </pre>
                    </div>
            </Card>

            {error && (
                <Alert variant="error">{error}</Alert>
            )}

            <div className="flex flex-col sm:flex-row gap-3">
                {!downloadUrl ? (
                <Button
                    onClick={handleGeneratePrescription}
                    isLoading={isLoading}
                    fullWidth
                    variant="success"
                    leftIcon={<FileText className="w-4 h-4" />}
                >
                    {isLoading ? 'Generating...' : 'Generate Prescription'}
                </Button>
                ) : (
                <a
                    href={downloadUrl}
                    download={`prescription_${sessionId}.txt`}
                    className="flex-1"
                >
                    <Button
                    fullWidth
                    variant="success"
                    leftIcon={<Download className="w-4 h-4" />}
                    >
                    Download Prescription
                    </Button>
                </a>
                )}

                <Button
                onClick={handleNewConsultation}
                variant="secondary"
                leftIcon={<RefreshCw className="w-4 h-4" />}
                >
                New Consultation
                </Button>
            </div>

            <Alert variant="warning" title="Important">
                <p>This AI-generated prescription is for reference only.</p>
            </Alert>
        </div>
    );
};