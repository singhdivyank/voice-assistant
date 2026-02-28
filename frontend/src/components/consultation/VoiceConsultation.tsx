import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import toast from 'react-hot-toast';
import { ConversationPane, PrescriptionPane } from '../consultation/';
import { Alert, Button } from '../ui/';
import { useAudioRecording } from '@/hooks/';
import { ConversationEntry, useConsultationStore } from '@/utils/';

export const VoiceConsultation: React.FC = () => {
  const {
    currentQuestion,
    isProcessing,
    isProcessingAudio,
    conversationHistory,
    medicationRecommendations,
    medicationEnglish,
    isComplete,
    submitAudioAnswer,
    processInitialAudio,
    reset,
    error,
    setError,
    patientData,
    sessionId,
    currentQuestionIndex,
    isSpeaking,
  } = useConsultationStore();

  const [isCollectingInitialSymptoms, setIsCollectingInitialSymptoms] = useState(true);
  const [questionsGenerated, setQuestionsGenerated] = useState(false);
  const hasProcessedInitialRef = useRef(false);

  const handleRecordingComplete = useCallback(async (audioBlob: Blob) => {
    console.log('Recording completed, audio blob size:', audioBlob.size);
    
    if (audioBlob.size === 0) {
      toast.error('No audio detected. Please try again.');
      return;
    }

    setError(null);

    try {
      if (isCollectingInitialSymptoms && !hasProcessedInitialRef.current) {
        console.log('Processing initial symptoms audio');
        hasProcessedInitialRef.current = true;
        await processInitialAudio(audioBlob);
        setIsCollectingInitialSymptoms(false);
        setQuestionsGenerated(true);
        toast.success('Initial symptoms processed! Starting consultation...');
      } else {
        console.log('Processing follow-up answer audio');
        await submitAudioAnswer(audioBlob);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process your audio';
      setError(message);
      toast.error(message);
      if (isCollectingInitialSymptoms) {
        hasProcessedInitialRef.current = false;
      }
    }
  }, [isCollectingInitialSymptoms, processInitialAudio, submitAudioAnswer, currentQuestionIndex, setError]);

  const handleRecordingError = useCallback((error: string) => {
    toast.error(error);
    setError(error);
  }, [setError]);

  const {
    isRecording,
    isSupported,
    startRecording,
    stopRecording,
  } = useAudioRecording({
    onRecordingComplete: handleRecordingComplete,
    onError: handleRecordingError,
  });

  useEffect(() => {
    const shouldCollectSymptoms = !currentQuestion && !isComplete && !questionsGenerated;
    setIsCollectingInitialSymptoms(shouldCollectSymptoms);
  }, [currentQuestion, isComplete, questionsGenerated]);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error]);

  const handleNewConsultation = () => {
    if (isRecording) {
      stopRecording();
    }
    reset();
    hasProcessedInitialRef.current = false;
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

  const prescriptionLoading = (isProcessing || isProcessingAudio) && !currentQuestion && !isComplete;
  const showProcessing = isProcessingAudio || (isProcessing && currentQuestion);
  const canRecord = !showProcessing && !isComplete;

  if (!isSupported) {
    return (
      <Alert variant="error" title="Audio Recording Not Supported">
        Your browser does not support audio recording. Please use Chrome, Edge, or Safari for the voice consultation feature.
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
            content={medicationRecommendations || null}
            medicationEnglish={medicationEnglish}
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
                ? 'bg-red-50 border-red-400 animate-pulse' 
                : showProcessing 
                  ? 'bg-blue-50 border-blue-400' 
                  : isSpeaking
                    ? 'bg-green-50 border-green-400'
                    : 'bg-gray-50 border-gray-200'
            }`}
          >
            {isRecording ? (
              <Mic className="w-10 h-10 text-red-600" />
            ) : isSpeaking ? (
              <Volume2 className="w-10 h-10 text-green-600 animate-bounce" />
            ) : (
              <MicOff className="w-10 h-10 text-gray-400" />
            )}
          </div>
          
          <p className="text-sm text-gray-600 mt-2 text-center max-w-md">
            {isRecording
              ? isCollectingInitialSymptoms 
                ? 'Recording symptoms... Click stop when finished'
                : 'Recording answer... Click stop when finished'
              : isSpeaking
              ? 'Playing response...'
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
        </div>

        {/* Audio visualization placeholder */}
        {isRecording && (
          <div className="flex items-center justify-center space-x-1 h-8">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-red-400 rounded animate-pulse"
                style={{
                  height: `${Math.random() * 20 + 10}px`,
                  animationDelay: `${i * 100}ms`,
                  animationDuration: '1s'
                }}
              />
            ))}
          </div>
        )}

        {/* Recording Controls */}
        {canRecord && (
          <div className="flex gap-3">
            <Button
              onClick={isRecording ? stopRecording : startRecording}
              variant={isRecording ? 'danger' : 'primary'}
              size="lg"
              leftIcon={isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            >
              {isRecording 
                ? 'Stop Recording' 
                : isCollectingInitialSymptoms 
                  ? 'Start Describing Symptoms' 
                  : 'Start Recording Answer'}
            </Button>
          </div>
        )}

        {/* New Consultation Button */}
        {(isComplete || error) && (
          <Button onClick={handleNewConsultation} variant="secondary" size="lg">
            New Consultation
          </Button>
        )}

        {/* Error Display */}
        {error && (
          <Alert variant="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Processing Status */}
        {showProcessing && (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span>
              {isCollectingInitialSymptoms 
                ? 'Analyzing symptoms...' 
                : 'Processing your answer...'}
            </span>
          </div>
        )}

        {/* Audio Status */}
        {isSpeaking && (
          <div className="flex items-center gap-2 text-sm text-green-600">
            <Volume2 className="w-4 h-4" />
            <span>Playing response audio...</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {}}
              leftIcon={<VolumeX className="w-3 h-3" />}
            >
              Stop
            </Button>
          </div>
        )}

        {/* Important Disclaimer */}
        <Alert variant="warning" title="Important">
          This AI consultation is for informational purposes only. Always consult a licensed healthcare provider for medical advice.
        </Alert>
      </div>
    </div>
  );
};