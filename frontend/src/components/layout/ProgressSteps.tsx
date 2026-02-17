import React from 'react';
import { Check } from 'lucide-react';
import { ConsultationPhase } from '../../store/consultationStore';

interface Step {
    phase: ConsultationPhase;
    label: string;
    icon?: React.ReactNode;
}

interface ProgressStepsProps {
    currentPhase: ConsultationPhase;
    steps?: Step[];
}

const DEFAULT_STEPS: Step[] = [
    { phase: 'patient-info', label: 'Patient Info' },
    { phase: 'complaint', label: 'Symptoms' },
    { phase: 'questions', label: 'Questions' },
    { phase: 'diagnosis', label: 'Diagnosis' },
    { phase: 'prescription', label: 'Prescription' },
];

export const ProgressSteps: React.FC<ProgressStepsProps> = ({
    currentPhase,
    steps = DEFAULT_STEPS
}) => {
    const phaseOrder = steps.map((s) => s.phase);
    const currentIndex = phaseOrder.indexOf(currentPhase);

    return (
        <nav aria-label="Progress" className="mb-8">
            <div className="hidden md:flex items-center justify-center">
                {steps.map((step, index) => {
                    const isCompleted = index < currentIndex;
                    const isCurrent = index === currentIndex;
                    const isUpcoming = index > currentIndex;

                    return (
                        <React.Fragment key={step.phase}>
                            <div className="flex flex-col items-center">
                                <div
                                className={`
                                    w-10 h-10 rounded-full flex items-center justify-center
                                    text-sm font-medium transition-all duration-300
                                    ${isCompleted ? 'bg-blue-600 text-white' : ''}
                                    ${isCurrent ? 'bg-blue-600 text-white ring-4 ring-blue-100' : ''}
                                    ${isUpcoming ? 'bg-gray-200 text-gray-500' : ''}
                                `}
                                >
                                {isCompleted ? (
                                    <Check className="w-5 h-5" />
                                ) : (index + 1)}
                                </div>
                                <span
                                className={`
                                    mt-2 text-xs font-medium
                                    ${isCurrent ? 'text-blue-600' : ''}
                                    ${isCompleted ? 'text-gray-700' : ''}
                                    ${isUpcoming ? 'text-gray-400' : ''}
                                `}
                                >
                                {step.label}
                                </span>
                            </div>

                            {index < steps.length - 1 && (
                                <div
                                className={`
                                    w-16 h-1 mx-2 rounded transition-colors duration-300
                                    ${index < currentIndex ? 'bg-blue-600' : 'bg-gray-200'}
                                `}
                                />
                            )}
                        </React.Fragment>
                    );
                })}
            </div>
        </nav>
    );
};