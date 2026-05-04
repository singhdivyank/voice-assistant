import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Mic, MicOff, Volume2, VolumeX, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { ConversationPane, PrescriptionPane } from '../consultation/';
import { Alert, Button, ProgressBar } from '../ui/';
import { useSpeechRecognition } from '@/hooks/';
import type { ConversationEntry, Language } from '@/utils/';
import { LANGUAGE_MAP } from '@/utils/';
import { useConsultationStore } from '@/utils/consultationStore';

export const VoiceConsultation: React.FC = () => {
  const {
    currentQuestion,
    isProcessing,
    isProcessingAudio,
    conversationHistory,
    medicationRecommendations,
    medicationEnglish,
    isComplete,
    submitAnswer,
    processInitialSymptom,
    sendPrescriptionForReview,
    reset,
    error,
    setError,
    patientData,
    currentQuestionIndex,
    totalQuestions,
    isSpeaking,
    questions,
    workflowStep,
    stopAudio,
  } = useConsultationStore();

  const [isCollectingInitialSymptoms, setIsCollectingInitialSymptoms] = useState(true);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const hasProcessedInitialRef = useRef(false);
  const liveTranscriptRef = useRef('');

  const { startListening, stopListening, resetTranscript, isSupported } = useSpeechRecognition({
    language: LANGUAGE_MAP[patientData.language as Language] ?? 'en-US',
    continuous: true,
    onResult: (text) => {
      setLiveTranscript(text);
      liveTranscriptRef.current = text;
    },
    onError: (err) => {
      toast.error(err);
      setError(err);
    },
  });

  const handleStartSpeaking = useCallback(() => {
    resetTranscript();
    setLiveTranscript('');
    liveTranscriptRef.current = '';
    setIsListening(true);
    startListening();
  }, [startListening, resetTranscript]);

  const handleStopSpeaking = useCallback(async () => {
    stopListening();
    setIsListening(false);

    // Read from ref — always latest, never stale
    const finalText = liveTranscriptRef.current.trim();
    if (!finalText) {
      toast.error('No speech detected. Please try again.');
      return;
    }

    setError(null);
    try {
      if (isCollectingInitialSymptoms && !hasProcessedInitialRef.current) {
        hasProcessedInitialRef.current = true;
        await processInitialSymptom(undefined, finalText);
        setIsCollectingInitialSymptoms(false);
        toast.success('Symptoms recorded — generating questions...');
      } else {
        await submitAnswer(finalText);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process';
      setError(message);
      toast.error(message);
      if (isCollectingInitialSymptoms) hasProcessedInitialRef.current = false;
    }
  }, [
    isCollectingInitialSymptoms,
    processInitialSymptom,
    submitAnswer,
    setError,
    stopListening,
  ]);

  useEffect(() => {
    setIsCollectingInitialSymptoms(!currentQuestion && !isComplete && questions.length === 0);
  }, [currentQuestion, isComplete, questions]);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error]);

  const conversationEntries: ConversationEntry[] = [];
  if (isCollectingInitialSymptoms) {
    conversationEntries.push({
      speaker: 'doc',
      text: 'Please describe your main symptoms. Take your time and be as detailed as possible.',
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

  const showProcessing = isProcessingAudio || (isProcessing && !isComplete);
  const canRecord = !showProcessing && !isComplete && !isSpeaking;
  const prescriptionLoading = isProcessing && !medicationRecommendations;
  const qaProgress =
    totalQuestions > 0 ? Math.round((currentQuestionIndex / totalQuestions) * 100) : 0;

  if (!isSupported) {
    return (
      <Alert variant="error" title="Speech Recognition Not Supported">
        Your browser does not support speech recognition. Please use Chrome, Edge, or Safari
        over HTTPS.
      </Alert>
    );
  }

  return (
    <div className="space-y-4">

      {/* Q&A progress bar */}
      {totalQuestions > 0 && !isComplete && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-500">
            <span>
              Question {Math.min(currentQuestionIndex + 1, totalQuestions)} of {totalQuestions}
            </span>
            <span>{qaProgress}% complete</span>
          </div>
          <ProgressBar value={qaProgress} max={100} size="sm" />
        </div>
      )}

      {/* Main two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[320px] w-full">
        <div className="lg:col-start-1 lg:col-end-2 min-h-[280px] order-1">
          <ConversationPane
            entries={conversationEntries}
            className="h-full min-h-[280px] lg:min-h-[360px]"
          />
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

        {/* Mic indicator */}
        <div className="flex flex-col items-center">
          <div
            className={`w-20 h-20 rounded-full flex items-center justify-center border-4 transition-colors ${
              isListening
                ? 'bg-red-50 border-red-400 animate-pulse'
                : showProcessing
                ? 'bg-blue-50 border-blue-400'
                : isSpeaking
                ? 'bg-green-50 border-green-400'
                : 'bg-gray-50 border-gray-200'
            }`}
          >
            {isListening ? (
              <Mic className="w-10 h-10 text-red-600" />
            ) : isSpeaking ? (
              <Volume2 className="w-10 h-10 text-green-600 animate-bounce" />
            ) : (
              <MicOff className="w-10 h-10 text-gray-400" />
            )}
          </div>

          <p className="text-sm text-gray-600 mt-2 text-center max-w-md">
            {isListening
              ? isCollectingInitialSymptoms
                ? 'Listening to symptoms... click Stop when finished'
                : 'Listening to answer... click Stop when finished'
              : isSpeaking
              ? 'Playing response...'
              : showProcessing
              ? workflowStep === 'recommendations_generated' ||
                workflowStep === 'audio_generated'
                ? 'Generating recommendations via AI agents...'
                : isCollectingInitialSymptoms
                ? 'Processing symptoms and generating questions...'
                : 'Processing your response...'
              : isComplete
              ? 'Consultation complete — review your prescription below'
              : isCollectingInitialSymptoms
              ? 'Click start to describe your symptoms'
              : 'Click start to answer the question'}
          </p>
        </div>

        {/* Live transcript while speaking */}
        {isListening && liveTranscript && (
          <div className="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-3 max-w-md text-center w-full">
            <span className="text-red-500 mr-1">●</span>
            {liveTranscript}
          </div>
        )}

        {/* Waveform animation while listening */}
        {isListening && (
          <div className="flex items-center justify-center space-x-1 h-8">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-red-400 rounded animate-pulse"
                style={{
                  height: `${[18, 26, 14, 24, 16][i]}px`,
                  animationDelay: `${i * 100}ms`,
                }}
              />
            ))}
          </div>
        )}

        {/* Recording controls */}
        {canRecord && (
          <Button
            onClick={isListening ? handleStopSpeaking : handleStartSpeaking}
            variant={isListening ? 'danger' : 'primary'}
            size="lg"
            leftIcon={
              isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />
            }
          >
            {isListening
              ? 'Stop Speaking'
              : isCollectingInitialSymptoms
              ? 'Start Describing Symptoms'
              : 'Start Answering'}
          </Button>
        )}

        {/* Send for MCP review */}
        {medicationRecommendations && !isComplete && (
          <Button
            onClick={sendPrescriptionForReview}
            isLoading={isProcessing}
            variant="success"
            size="lg"
            leftIcon={<FileText className="w-5 h-5" />}
          >
            Send Prescription for Doctor Review
          </Button>
        )}

        {/* New consultation */}
        {(isComplete || error) && (
          <Button
            onClick={() => {
              if (isListening) {
                stopListening();
                setIsListening(false);
              }
              reset();
              hasProcessedInitialRef.current = false;
              setIsCollectingInitialSymptoms(true);
              setLiveTranscript('');
              liveTranscriptRef.current = '';
            }}
            variant="secondary"
            size="lg"
          >
            New Consultation
          </Button>
        )}

        {/* Error */}
        {error && (
          <Alert variant="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Processing indicator */}
        {showProcessing && (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
            <span>
              {workflowStep === 'recommendations_generated'
                ? 'AI agents generating recommendations...'
                : isCollectingInitialSymptoms
                ? 'Analyzing symptoms...'
                : 'Processing your answer...'}
            </span>
          </div>
        )}

        {/* Speaking indicator with stop button */}
        {isSpeaking && (
          <div className="flex items-center gap-2 text-sm text-green-600">
            <Volume2 className="w-4 h-4" />
            <span>Playing response audio...</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={stopAudio}
              leftIcon={<VolumeX className="w-3 h-3" />}
            >
              Stop
            </Button>
          </div>
        )}

        <Alert variant="warning" title="Important">
          This AI consultation is for informational purposes only. All prescriptions require
          doctor approval before finalisation.
        </Alert>
      </div>
    </div>
  );
};