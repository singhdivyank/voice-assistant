import React, { useState } from 'react';
import { useConsultationStore } from '../../store/consultationStore';

export const ComplaintInput: React.FC = () => {
    const { complaint, setComplaint, startConsultation, isLoading, error } = useConsultationStore();
    const [localComplaint, setLocalComplaint] = useState(complaint);
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setComplaint(localComplaint);
        await startConsultation();
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6 max-w-md mx-auto">
            <h2 className="text-2xl font-semibold text-gray-800">Describe your symptoms</h2>
            <p className="text-gray-600">Please describe your main health concern in detail.</p>

            <textarea 
                value={localComplaint}
                onChange={(e) => setLocalComplaint(e.target.value)}
                placeholder="E.g., I've been experiencing stomach ache for the past ... days"
                rows={6}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                disabled={isLoading}
            />

            {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                    {error}
                </div>
            )}

            <button
                type="submit"
                disabled=(isLoading || !localComplaint.trim())
                className="w-full px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
            {isLoading ? (
                <>
                    <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"/>
                    Analyzing...
                </>
            ) : 'Start Consultation'}
            </button>
        </form>
    );
};