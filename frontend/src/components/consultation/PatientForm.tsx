import React, { useState } from 'react';
import { Mic, VolumeX, User, Mail, Calendar } from 'lucide-react';
import toast from 'react-hot-toast';
import { useSpeechSynthesis } from '@/hooks/';
import { 
  GENDERS_MAP, 
  LANGUAGE_MAP,
  useConsultationStore,
  introText,
  emailRegex,
} from '@/utils/';
import type { PatientFormData } from '@/utils/';
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

  const [step, setStep] = useState<'details' | 'introduction'>('details');
  const [introductionSpoken, setIntroductionSpoken] = useState(false);
  const [formData, setFormData] = useState<PatientFormData>({
    name: '',
    email: '',
    age: patientData.age,
    gender: patientData.gender,
    language: patientData.language,
  });

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

  const validateForm = () => {
    if (!formData.name.trim()) {
      toast.error('Please enter your full name');
      return false;
    }

    if (!formData.email.trim()) {
      toast.error('Please enter your email address');
      return false;
    }

    if (!emailRegex.test(formData.email)) {
      toast.error('Please enter a valid email address');
      return false;
    }

    if (formData.age < 1 || formData.age > 90) {
      toast.error('Please enter a valid age (1-90');
      return false;
    }

    return true;
  };

  const handleConfirmDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setPatientData({
      name: formData.name,
      email: formData.email,
      age: formData.age,
      gender: formData.gender,
      language: formData.language,
    });
    
    setStep('introduction');
    speak(`Hello ${formData.name}, ${introText}`);
    setTimeout(() => setIntroductionSpoken(true), 8000);
  };

  const onStartSpeaking = async () => {
    cancel();
    try {
      await startVoiceConsultation();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start session');
    }
  };

  const handleInputChange = (field: keyof PatientFormData, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (step === 'details') {
    return (
      <div className="max-w-md mx-auto">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <User className="w-8 h-8 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-800">Patient Registration</h2>
          <p className="text-gray-600 mt-2">Please provide your details for personalized consultation</p>
        </div>
        
        <form onSubmit={handleConfirmDetails} className="space-y-4">
          <Input
            label="Full Name"
            type="text"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            placeholder="Enter your full name"
            leftIcon={<User className="w-4 h-4 text-gray-400" />}
            required
          />
          
          <Input
            label="Email Address"
            type="email"
            value={formData.email}
            onChange={(e) => handleInputChange('email', e.target.value)}
            placeholder="your.email@example.com"
            leftIcon={<Mail className="w-4 h-4 text-gray-400" />}
            helpText="We'll send your consultation summary to this email"
            required
          />
          
          <Input
            label="Age"
            type="number"
            value={formData.age}
            onChange={(e) => handleInputChange('age', parseInt(e.target.value) || 0)}
            min="1"
            max="90"
            placeholder="25"
            leftIcon={<Calendar className="w-4 h-4 text-gray-400" />}
            required
          />
          
          <Select
            label="Gender"
            options={genderOptions}
            value={formData.gender}
            onChange={(val) => handleInputChange('gender', val)}
          />
          
          <Select
            label="Preferred Language"
            options={languageOptions}
            value={formData.language}
            onChange={(val) => handleInputChange('language', val)}
          />
          
          {/* Privacy Notice */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
            <h4 className="font-medium text-blue-900 mb-1">Privacy & Data Security</h4>
            <p className="text-blue-800">
              Your personal information is encrypted and stored securely. 
              We only use it for your consultation and never share it with third parties.
            </p>
          </div>
          
          <Button 
            type="submit" 
            fullWidth 
            size="lg" 
            isLoading={isLoading}
            className="bg-gradient-to-r from-blue-600 to-blue-700"
          >
            Continue to Consultation
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

      <h2 className="text-2xl font-bold text-gray-800 mb-2">
        Welcome, {formData.name}!
      </h2>
      <p className="text-gray-600 mb-8">
        Ready to start your personalized medical consultation?
      </p>

      {/* Patient Summary Card */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 text-left">
        <h3 className="font-medium text-gray-900 mb-3">Your Information</h3>
        <div className="space-y-2 text-sm text-gray-700">
          <div className="flex justify-between">
            <span>Name:</span>
            <span className="font-medium">{formData.name}</span>
          </div>
          <div className="flex justify-between">
            <span>Age:</span>
            <span className="font-medium">{formData.age}</span>
          </div>
          <div className="flex justify-between">
            <span>Language:</span>
            <span className="font-medium">{LANGUAGE_MAP[formData.language]}</span>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-6 text-left">
        <h3 className="font-medium text-blue-900 mb-2">AI Multi-Agent System</h3>
        <p className="text-sm text-blue-800 mb-3">
          Our advanced AI system uses specialized agents for optimal care:
        </p>
        <ul className="text-xs text-blue-700 space-y-1">
          <li>• <strong>Speech Processing:</strong> Accurate audio transcription</li>
          <li>• <strong>Medical Analysis:</strong> Evidence-based diagnostic reasoning</li>
          <li>• <strong>Translation:</strong> Real-time multilingual support</li>
          <li>• <strong>Prescription:</strong> Personalized treatment recommendations</li>
        </ul>
      </div>

      {isSpeaking ? (
        <div className="space-y-4">
          <div className="text-blue-600 animate-pulse font-medium">
            🔊 Personal introduction in progress...
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
            className="bg-gradient-to-r from-green-600 to-green-700"
          >
            Start AI Consultation
          </Button>
        )
      )}
    </div>
  );
};