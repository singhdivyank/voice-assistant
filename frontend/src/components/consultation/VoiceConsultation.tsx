import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Mic, MicOff } from 'lucide-react';
import { ReactMic } from 'react-mic-recorder';
import toast from 'react-hot-toast';
import { ConversationPane, PrescriptionPane } from '../consultation/';
import { Alert, Button } from '../ui/';
import { useSpeechRecognition, useSpeechSynthesis } from '@/hooks/';
import { LANGUAGE_MAP, ConversationEntry, useConsultationStore } from '@/utils/';

export const VoiceConsultation: React.FC = () => {
  const {
    currentQuestion,
    isProcessing,
    conversationHistory,
    streamedMedication,
    streamedMedicationEnglish,
    isComplete,
    submitVoiceAnswer,
    processInitialSymptoms,
    reset,
    error,
    setError,
    patientData,
    sessionId,
  } = useConsultationStore();

  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingAnswer, setIsProcessingAnswer] = useState(false);
  const [isCollectingInitialSymptoms, setIsCollectingInitialSymptoms] = useState(true);
  const [questionsGenerated, setQuestionsGenerated] = useState(false);
  const hasSpokenFirstRef = useRef(false);
  
  const getSpeechLang = () => LANGUAGE_MAP[patientData.language] || 'en-US';

  const handleSpeechResult = useCallback((text: string) => {
    console.log('Speech result:', text);
  }, []);

  const {
    transcript,
    startListening,
    stopListening,
    resetTranscript,
    isSupported,
  } = useSpeechRecognition({
    language: getSpeechLang(),
    continuous: true,
    onResult: handleSpeechResult,
    onError: (err) => {
      toast.error(err);
      setIsRecording(false);
    },
  });

  const { speak, cancel: cancelSpeech } = useSpeechSynthesis({
    language: getSpeechLang(),
    rate: 0.9,
    onEnd: () => {
      if (currentQuestion && !isComplete && !isProcessing && !isProcessingAnswer) {
        setTimeout(() => {
          console.log('Speech ended, ready to start recording');
        }, 800);
      }
    },
  });

  const handleStartRecording = useCallback(() => {
    console.log('Starting recording...');
    resetTranscript();
    setIsRecording(true);
    setIsProcessingAnswer(false);
    startListening();
  }, [resetTranscript, startListening]);

  const handleStopRecording = useCallback(async () => {
    console.log('Stop recording clicked');
    console.log('Transcript:', transcript);
    console.log('Transcript.length:', transcript.length);
    
    const text = transcript.trim();
    console.log('Trimmed text:', text);
    console.log('Text length:', text.length);
    stopListening();
    setIsRecording(false);
    resetTranscript();
    
    if (text.length === 0) {
      toast.error('No speech detected. Please try again.');
      return;
    }

    setIsProcessingAnswer(true);
    setError(null);

    try {
      if (isCollectingInitialSymptoms) {
        console.log('Collecting initial symptoms:', text);
        
        try {
          await processInitialSymptoms(text);
          console.log('Symptoms processed successfully');
          setIsCollectingInitialSymptoms(false);
          setQuestionsGenerated(true);
          toast.success('Questions generated! Starting consultation ...');
        } catch (err) {
          throw err;
        }
      } else {
        await submitVoiceAnswer(text);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process your input';
      setError(message);
      toast.error(message);
    } finally {
      setIsProcessingAnswer(false);
    }
  }, [transcript, stopListening, resetTranscript, isCollectingInitialSymptoms, speak, submitVoiceAnswer, setError]);

  useEffect(() => {
    const shouldCollectSymptoms = !currentQuestion && !isComplete && !questionsGenerated;
    setIsCollectingInitialSymptoms(shouldCollectSymptoms);
  }, [currentQuestion, isComplete, questionsGenerated]);

  useEffect(() => {
    if (!isProcessing && isProcessingAnswer) {
      setIsProcessingAnswer(false);
    }
  }, [isProcessing, isProcessingAnswer]);

  useEffect(() => {
    if (currentQuestion && !hasSpokenFirstRef.current && !isProcessing && !isProcessingAnswer) {
      console.log('Speaking question:', currentQuestion);
      hasSpokenFirstRef.current = true;
      speak(currentQuestion);
    }
  }, [currentQuestion, isProcessing, isProcessingAnswer, speak]);

  useEffect(() => {
    if (isComplete && streamedMedication) {
      const intro = 'Here are your medical recommendations. ';
      speak(intro + streamedMedication);
    }
  }, [isComplete, streamedMedication, speak]);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error]);

  const handleNewConsultation = () => {
    cancelSpeech();
    if (isRecording) {
      stopListening();
      setIsRecording(false);
    }
    reset();
    hasSpokenFirstRef.current = false;
    setIsProcessingAnswer(false);
    setIsCollectingInitialSymptoms(true);
    setQuestionsGenerated(false);
  };

  const conversationEntries: ConversationEntry[] = [];
  
  if (isCollectingInitialSymptoms) {
    conversationEntries.push({ 
      speaker: 'doc', 
      text: 'Please describe your main symptoms. Take your time and be as detailed as possible.' 
    });
  } else {
    conversationHistory.forEach((turn) => {
      conversationEntries.push({ speaker: 'doc', text: turn.question });
      conversationEntries.push({ speaker: 'you', text: turn.answer });
    });
    if (currentQuestion && !isComplete) {
      conversationEntries.push({ speaker: 'doc', text: currentQuestion });
    }
  }

  const prescriptionLoading = (isProcessing || isProcessingAnswer) && !currentQuestion && !isComplete;
  const showProcessing = isProcessingAnswer || (isProcessing && currentQuestion);

  if (!isSupported) {
    return (
      <Alert variant="error" title="Speech Not Supported">
        Your browser does not support speech recognition. Please use Chrome, Edge, or Safari for the voice consultation feature.
      </Alert>
    );
  }

  if (!sessionId) {
    return (
      <Alert variant="error" title="Session Error">
        No active session found. Please restart the consultation.
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[320px] w-full">
        <div className="lg:col-start-1 lg:col-end-2 min-h-[280px] order-1">
          <ConversationPane entries={conversationEntries} className="h-full min-h-[280px] lg:min-h-[360px]" />
        </div>
        <div className="lg:col-start-2 lg:col-end-3 min-h-[280px] order-2">
          <PrescriptionPane
            content={streamedMedication || null}
            medicationEnglish={streamedMedicationEnglish}
            language={patientData.language}
            isLoading={prescriptionLoading}
            className="h-full min-h-[280px] lg:min-h-[360px]"
          />
        </div>
      </div>

      <div className="flex flex-col items-center gap-4">
        <div className="flex flex-col items-center">
          <div
            className={`w-20 h-20 rounded-full flex items-center justify-center border-4 ${
              isRecording 
                ? 'bg-red-50 border-red-400' 
                : showProcessing 
                  ? 'bg-blue-50 border-blue-400' 
                  : 'bg-gray-50 border-gray-200'
            }`}
          >
            {isRecording ? (
              <Mic className="w-10 h-10 text-red-600 animate-pulse" />
            ) : (
              <MicOff className="w-10 h-10 text-gray-400" />
            )}
          </div>
          <p className="text-sm text-gray-600 mt-2 text-center">
            {isRecording
              ? isCollectingInitialSymptoms 
                ? 'Describing symptoms... Click stop when finished'
                : 'Speaking... Click stop when finished'
              : showProcessing
              ? isCollectingInitialSymptoms
                ? 'Processing symptoms and generating questions...'
                : 'Processing your response...'
              : isComplete
              ? 'Consultation complete'
              : isCollectingInitialSymptoms
              ? 'Click start to describe your symptoms'
              : 'Click start to answer the question'}
          </p>
          {transcript && isRecording && (
            <p className="text-xs text-gray-500 mt-1 max-w-md text-center">
              "{transcript}"
            </p>
          )}
        </div>

        {isRecording && (
          <div className="w-full max-w-md rounded-lg overflow-hidden border border-gray-200 bg-white">
            <ReactMic
              record={true}
              className="w-full"
              strokeColor="#ef4444"
              backgroundColor="rgba(255,255,255,0.8)"
              onStop={() => {}}
            />
          </div>
        )}

        {!isComplete && !showProcessing && (
          <Button
            onClick={isRecording ? handleStopRecording : handleStartRecording}
            variant={isRecording ? 'danger' : 'primary'}
            size="lg"
            leftIcon={isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          >
            {isRecording 
              ? 'Stop Speaking' 
              : isCollectingInitialSymptoms 
                ? 'Start Describing Symptoms' 
                : 'Start Speaking'}
          </Button>
        )}

        {(isComplete || error) && (
          <Button onClick={handleNewConsultation} variant="secondary" size="lg">
            New Consultation
          </Button>
        )}

        {error && (
          <Alert variant="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Alert variant="warning" title="Important">
          This AI consultation is for informational purposes only. Always consult a licensed healthcare provider for medical advice.
        </Alert>
      </div>
    </div>
  );
};