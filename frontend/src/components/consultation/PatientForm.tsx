import React from 'react';
import { useConsultationStore } from '../../store/consultationStore';
import { LANGUAGES, GENDERS, Gender, Language } from '../../api/types';

export const PatientForm: React.FC = () => {
    const { patientData, setPatientData, setPhase } = useConsultationStore();

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setPhase('complaint');
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6 max-w-md mx-auto">
            <h2 className="text-2xl font-semibold text-gray-800">Patient Information</h2>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Age</label>
                <input
                    type="number"
                    min={1}
                    max={120}
                    value={patientData.age}
                    onChange={(e) => setPatientData({ age: parseInt(e.target.value) || 30})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Gender</label>
                <select 
                    value={patientData.gender}
                    onChange={(e) => setPatientData({  gender: e.target.value as Gender })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500"
                >
                    {Object.entries(GENDERS).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                    ))}
                </select>
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Language</label>
                <select 
                    value={patientData.language}
                    onChange={(e) => setPatientData({  language: e.target.value as Language })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus: ring-2 focus:ring-blue-500"
                >
                    {Object.entries(LANGUAGES).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                    ))}
                </select>
            </div>

            <button 
                type="submit" 
                className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
                Continue
            </button>
        </form>
    );
};