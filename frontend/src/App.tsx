import React from 'react';
import { useConsultationStore } from './store/consultationStore';
import { PatientForm } from './components/consultation/PatientForm';
import { VoiceConsultation } from './components/consultation/VoiceConsultation';
import { Header } from './components/layout';
import { Footer } from './components/layout';

const ConsultationContent: React.FC = () => {
    const { phase } = useConsultationStore();
    switch (phase) {
        case 'voice-consultation':
            return <VoiceConsultation />;
        default:
            return <PatientForm />;
    }
};

function App() {
    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <Header />
            <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
                    <ConsultationContent />
                </div>
            </main>
            <Footer />
        </div>
    );
}

export default App;
