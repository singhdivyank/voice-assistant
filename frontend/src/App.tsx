import React from 'react';
import {useConsultationStore, ConsultationPhase} from './store/consultationStore';
import { PatientForm } from './components/consultation/PatientForm';
import { ComplaintInput } from './components/consultation/ComplaintInput';
import { QuestionAnswer } from './components/consultation/QuestionAnswer';
import { DiagnosisView } from './components/consultation/DiagnosisView';
import { PrescriptionCard } from './components/consultation/PrescriptionCard';

const STEPS: { phase: ConsultationPhase; label: string }[] = [
    { phase: 'patient-info', label: 'Patient Info' },
    { phase: 'complaint', label: 'Symptoms' },
    { phase: 'questions', label: 'Questions' },
    { phase: 'diagnosis', label: 'Diagnosis' },
    { phase: 'prescription', label: 'Prescription' },
];

const ProgressSteps: React.FC<{ currentPhase: ConsultationPhase }> = ({ currentPhase }) => {
    const phaseOrder = STEPS.map(s => s.phase);
    const currentIndex = phaseOrder.indexOf(currentPhase);

    return (
        <div className="flex items-center justify-center mb-8">
            {STEPS.map((step, index) => (
                <React.Fragment key={step.phase}>
                    <div className="flex flex-col items-center">
                        <div
                            className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                                index <= currentIndex ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
                            }`}
                        >
                            {index < currentIndex ? '✓' : index + 1}
                        </div>
                        <span className={`mt-2 text-xs ${
                            index <= currentIndex ? 'text-blue-600 font-medium': 'text-gray-400'
                        }`}>
                            {step.label}
                        </span>
                    </div>
                    {index < STEPS.length - 1 && (
                        <div 
                        className={`w-16 h-1 mx-2 ${
                            index < currentIndex ? 'bg-blue-600': 'bg-gray-200'
                        }`}
                        />
                    )}
                </React.Fragment>
            ))}
        </div>
    );
};

const Header: React.FC = () => (
    <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                    <span className="text-white text-xl">🏥</span>
                </div>
                <div>
                    <h1 className="text-xl font-bold text-gray-800">DocJarvis</h1>
                    <p className="text-xs text-gray-500">AI Medical Assistant</p>
                </div>
            </div>
        </div>
    </header>
);

const Footer: React.FC = () => (
    <footer className="bg-gray-50 border-t border-gray-200 mt-auto">
        <div className="max-w-4xl mx-auto px-4 py-4">
            <p className="text-center text-xs text-gray-500">
                For informational purpose only. Not a substitute for professional medical advice.
            </p>
        </div>
    </footer>
);

const ConsultationContent: React.FC = () => {
    const { phase } = useConsultationStore();

    switch (phase) {
        case 'patient-info':
            return <PatientForm />;
        case 'complaint':
            return <ComplaintInput />;
        case 'questions':
            return <QuestionAnswer />;
        case 'diagnosis':
            return <DiagnosisView />;
        case 'prescription':
        case 'complete':
            return <PrescriptionCard />;
        default:
            return <PatientForm />;
    }
};

function App() {
    const { phase } = useConsultationStore();

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <Header />
            <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
                <ProgressSteps currentPhase={phase} />
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
                    <ConsultationContent />
                </div>
            </main>
            <Footer />
        </div>
    );
}

export default App;
