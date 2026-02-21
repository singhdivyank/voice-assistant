import React from 'react';
import { Mic } from 'lucide-react';
import { useConsultationStore } from '../../store/consultationStore';
import { GENDERS, Gender } from '../../api/types';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';

export const PatientForm: React.FC = () => {
    const { patientData, setPatientData, startVoiceConsultation, isLoading, error } = useConsultationStore();
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        startVoiceConsultation();
    };

    const genderOptions = Object.entries(GENDERS).map(([value, label]) => ({
        value,
        label
    }));

    return (
        <div className="space-y-6 max-w-md mx-auto">
            <div className="text-center mb-8">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Mic className="w-8 h-8 text-blue-600" />
                </div>
                <h2 className="text-2xl font-semibold text-gray-800">DocJarvis Voice Consultation</h2>
                <p className="text-gray-600 mt-2">
                    Enter your basic information to begin voice-guided medical consultation
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                    label="Age"
                    type="number"
                    min={1}
                    max={120}
                    value={patientData.age.toString()}
                    onChange={(e) => setPatientData({ age: parseInt(e.target.value) || 1 })}
                    required
                />
                <Select
                    label="Gender"
                    options={genderOptions}
                    value={patientData.gender}
                    onChange={(value) => setPatientData({ gender: value as Gender })}
                />
                {error && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                        {error}
                    </div>
                )}
                <Button
                    type="submit"
                    fullWidth
                    size="lg"
                    isLoading={isLoading}
                    leftIcon={<Mic className="w-5 h-5" />}
                    className="mt-6"
                >
                    {isLoading ? 'Starting...' : 'Begin Voice Consultation'}
                </Button>
            </form>

            <div className="text-center text-sm text-gray-500 mt-6">
                <p>Make sure your microphone is enabled for the best experience</p>
            </div>
        </div>
    );
};