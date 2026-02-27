import React, { useState } from 'react';
import { Mic, VolumeX } from 'lucide-react';
import toast from 'react-hot-toast';
import { useSpeechSynthesis } from '@/hooks/';
import { 
  GENDERS_MAP, 
  LANGUAGE_MAP,
  useConsultationStore,
  introText,
} from '@/utils/';
import { Button, Input, Select } from '../ui/';

const languageOptions = Object.entries(LANGUAGE_MAP).map(([value, label]) => ({ value, label }));
const genderOptions = Object.entries(GENDERS_MAP).map(([value, label]) => ({ value, label }));

export const PatientForm: React.FC = () => {
  const {
    patientData,
    setPatientData,
    startVoiceConsultation,
    isLoading,
    setError,
  } = useConsultationStore();

  console.log('PatientForm - Current phase:', patientData, isLoading);

  const [step, setStep] = useState<'details' | 'introduction'>('details');
  const [introductionSpoken, setIntroductionSpoken] = useState(false);

  const getSpeechLang = () => {
    return LANGUAGE_MAP[patientData.language] || 'en-US';
  };

  const { speak, isSpeaking, cancel } = useSpeechSynthesis({
    language: getSpeechLang(),
    onEnd: () => setIntroductionSpoken(true),
    onError: (err) => {
      console.error("Speech Error:", err);
      setIntroductionSpoken(true);
    }
  });

  const handleConfirmDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (patientData.age < 1 || patientData.age > 90) {
      toast.error('Please enter a valid age (1-90)');
      return;
    }
    
    setStep('introduction');
    speak(introText);
    setTimeout(() => setIntroductionSpoken(true), 8000);
  };

  const onStartSpeaking = async () => {
    cancel();
    try {
      await startVoiceConsultation();
    } catch (err: any) {
      setError(err.message || 'Failed to start session');
    }
  };

  if (step === 'details') {
    return (
      <div className="max-w-md mx-auto">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Patient Details</h2>
        <form onSubmit={handleConfirmDetails} className="space-y-4">
          <Input
            label="Age"
            type="number"
            value={patientData.age}
            onChange={(e) => setPatientData({ age: parseInt(e.target.value) || 0 })}
            min="1"
            max="90"
            required
          />
          <Select
            label="Gender"
            options={genderOptions}
            value={patientData.gender}
            onChange={(val) => setPatientData({ gender: val as any })}
          />
          <Select
            label="Preferred Language"
            options={languageOptions}
            value={patientData.language}
            onChange={(val) => setPatientData({ language: val as any })}
          />
          <Button type="submit" fullWidth size="lg" isLoading={isLoading}>
            Confirm Details
          </Button>
        </form>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto text-center">
      <div className="mb-6 flex justify-center">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
          <Mic className={`w-8 h-8 ${isSpeaking ? 'text-blue-600 animate-bounce' : 'text-blue-400'}`} />
        </div>
      </div>

      <h2 className="text-2xl font-bold text-gray-800 mb-2">Ready to Start?</h2>
      <p className="text-gray-600 mb-8">{introText}</p>

      <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-6 text-left">
        <h3 className="font-medium text-blue-900 mb-2">Instructions:</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>1. Click <strong>"Start Speaking"</strong> below</li>
          <li>2. Describe your symptoms clearly</li>
          <li>3. Click <strong>"Stop Speaking"</strong> when finished</li>
        </ul>
      </div>

      {isSpeaking ? (
        <div className="space-y-4">
          <div className="text-blue-600 animate-pulse font-medium">
            🔊 Speaking introduction...
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setIntroductionSpoken(true)}
            leftIcon={<VolumeX className="w-4 h-4" />}
          >
            Skip Audio
          </Button>
        </div>
      ) : (
        (introductionSpoken || !isSpeaking) && (
          <Button
            onClick={onStartSpeaking}
            fullWidth
            size="lg"
            leftIcon={<Mic className="w-5 h-5" />}
            isLoading={isLoading}
          >
            Start Speaking
          </Button>
        )
      )}
    </div>
  );
};