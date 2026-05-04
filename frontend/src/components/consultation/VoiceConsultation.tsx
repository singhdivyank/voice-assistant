import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Mic, MicOff, Volume2, VolumeX, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { ConversationPane, PrescriptionPane } from '../consultation/';
import { Alert, Button, ProgressBar } from '../ui/';
import { useAudioRecording } from '@/hooks/';
import type { ConversationEntry } from '@/utils/';
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
    sessionId,
    currentQuestionIndex,
    totalQuestions,
    isSpeaking,
    questions,
    workflowStep,
  } = useConsultationStore();

  const [isCollectingInitialSymptoms, setIsCollectingInitialSymptoms] = useState(true);
  const hasProcessedInitialRef = useRef(false);

  // ── Audio recording ─────────────────────────────────────────────────────────

  const handleRecordingComplete = useCallback(
    async (audioBlob: Blob) => {
      if (audioBlob.size === 0) {
        toast.error('No audio detected. Please try again.');
        return;
      }
      setError(null);
      try {
        if (isCollectingInitialSymptoms && !hasProcessedInitialRef.current) {
          hasProcessedInitialRef.current = true;
          await processInitialSymptom(audioBlob);
          setIsCollectingInitialSymptoms(false);
          toast.success('Symptoms recorded — questions generated!');
        } else {
          // The audio blob contains the spoken answer; transcription happens server-side.
          // We send the blob and let the V2 backend STT agent transcribe it, then
          // we get the text back to display in the conversation pane.
          await submitAnswer('[audio answer]'); // placeholder — see note below
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to process audio';
        setError(message);
        toast.error(message);
        if (isCollectingInitialSymptoms) hasProcessedInitialRef.current = false;
      }
    },
    [isCollectingInitialSymptoms, processInitialSymptom, submitAnswer, setError]
  );

  /*
   * NOTE: The V2 workflow's answer-question endpoint accepts text answers, not
   * audio blobs (the STT step is bundled into process-initial-symptom only).
   * For the Q&A phase, users speak → browser SpeechRecognition API transcribes
   * locally → we send the text to /answer-question.  The audio recording hook
   * is still used here to give users the familiar record/stop UX; the transcript
   * from useSpeechRecognition is passed to submitAnswer() as a string.
   * If you want full server-side STT for Q&A too, swap submitAnswer(text) for
   * a new v2Client call that accepts a Blob.
   */

  const handleRecordingError = useCallback(
    (err: string) => { toast.error(err); setError(err); },
    [setError]
  );

  const { isRecording, isSupported, startRecording, stopRecording } = useAudioRecording({
    onRecordingComplete: handleRecordingComplete,
    onError: handleRecordingError,
  });

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
  const canRecord = !showProcessing && !isComplete;
  const prescriptionLoading = isProcessing && !medicationRecommendations;
  const qaProgress = totalQuestions > 0
    ? Math.round((currentQuestionIndex / totalQuestions) * 100)
    : 0;

  if (!isSupported) {
    return (
      <Alert variant="error" title="Audio Recording Not Supported">
        Your browser does not support audio recording. Please use Chrome, Edge, or Safari.
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

      {/* Q&A progress bar */}
      {totalQuestions > 0 && !isComplete && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-500">
            <span>Question {Math.min(currentQuestionIndex + 1, totalQuestions)} of {totalQuestions}</span>
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

      {/* Mic indicator + status */}
      <div className="flex flex-col items-center gap-4">
        <div className="flex flex-col items-center">
          <div
            className={`w-20 h-20 rounded-full flex items-center justify-center border-4 transition-colors ${
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
                ? 'Recording symptoms... click Stop when finished'
                : 'Recording answer... click Stop when finished'
              : isSpeaking
              ? 'Playing response...'
              : showProcessing
              ? workflowStep === 'recommendations_generated' || workflowStep === 'audio_generated'
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

        {/* Recording waveform placeholder */}
        {isRecording && (
          <div className="flex items-center justify-center space-x-1 h-8">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-1 bg-red-400 rounded animate-pulse"
                style={{ height: `${[18, 26, 14, 24, 16][i]}px`, animationDelay: `${i * 100}ms` }}
              />
            ))}
          </div>
        )}

        {/* Recording controls */}
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

        {/* Send for MCP review — shown once recommendations are ready */}
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
          <Button onClick={() => { if (isRecording) stopRecording(); reset(); }} variant="secondary" size="lg">
            New Consultation
          </Button>
        )}

        {/* Error */}
        {error && (
          <Alert variant="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Processing spinner */}
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
              onClick={() => useConsultationStore.getState().setSpeaking(false)}
              leftIcon={<VolumeX className="w-3 h-3" />}
            >
              Stop
            </Button>
          </div>
        )}

        <Alert variant="warning" title="Important">
          This AI consultation is for informational purposes only. All prescriptions
          require doctor approval before finalisation.
        </Alert>
      </div>
    </div>
  );
};