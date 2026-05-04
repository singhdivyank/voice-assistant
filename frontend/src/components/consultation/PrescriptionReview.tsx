import React, { useState } from 'react';
import { ClipboardCheck, Mail, Clock, CheckCircle, XCircle, AlertTriangle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';
import { Button, Alert, Spinner, Card } from '../ui/';
import { useConsultationStore } from '@/utils/consultationStore';
import type { DoctorAction } from '@/utils/';

const ACTION_CONFIG: Record<
  DoctorAction,
  { label: string; icon: React.ReactNode; variant: 'success' | 'error' | 'warning' | 'info' }
> = {
  APPROVED: {
    label: 'Prescription approved by doctor',
    icon: <CheckCircle className="w-5 h-5" />,
    variant: 'success',
  },
  MODIFIED: {
    label: 'Doctor approved with modifications',
    icon: <CheckCircle className="w-5 h-5" />,
    variant: 'success',
  },
  REJECTED: {
    label: 'Prescription rejected by doctor',
    icon: <XCircle className="w-5 h-5" />,
    variant: 'error',
  },
  TIMEOUT: {
    label: 'Doctor did not respond in time',
    icon: <AlertTriangle className="w-5 h-5" />,
    variant: 'warning',
  },
  UNCLEAR: {
    label: 'Doctor response could not be parsed',
    icon: <AlertTriangle className="w-5 h-5" />,
    variant: 'warning',
  },
  ERROR: {
    label: 'An error occurred processing the response',
    icon: <XCircle className="w-5 h-5" />,
    variant: 'error',
  },
};

export const PrescriptionReview: React.FC = () => {
  const {
    mcpReview,
    medicationRecommendations,
    medicationEnglish,
    patientData,
    isProcessing,
    error,
    submitDoctorResponse,
    sendPrescriptionForReview,
    reset,
    setError,
  } = useConsultationStore();

  const [emailContent, setEmailContent] = useState('');
  const [showRec, setShowRec] = useState(false);
  const [showInstructions, setShowInstructions] = useState(true);

  const { reviewId, doctorEmail, estimatedMinutes, action, modifications, rejectionReason, sentAt } =
    mcpReview;

  const handleSubmitResponse = async () => {
    if (!emailContent.trim()) {
      toast.error('Please paste the doctor\'s email reply before submitting.');
      return;
    }
    setError(null);
    try {
      await submitDoctorResponse(emailContent.trim());
      toast.success('Doctor response processed successfully.');
    } catch {
      toast.error('Failed to process doctor response. Please try again.');
    }
  };

  const handleResend = async () => {
    setError(null);
    try {
      await sendPrescriptionForReview();
      toast.success('Prescription resent to doctor.');
    } catch {
      toast.error('Failed to resend prescription.');
    }
  };

  const sentTime = sentAt ? new Date(sentAt).toLocaleTimeString() : null;

  if (action) {
    const cfg = ACTION_CONFIG[action];
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <Alert variant={cfg.variant} title="Doctor Review Complete">
          <div className="flex items-center gap-2">
            {cfg.icon}
            <span>{cfg.label}</span>
          </div>
        </Alert>

        {action === 'MODIFIED' && modifications && (
          <Card>
            <h4 className="font-semibold text-gray-800 mb-2">Doctor's Modifications</h4>
            <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 rounded p-3">
              {modifications}
            </pre>
          </Card>
        )}

        {action === 'REJECTED' && rejectionReason && (
          <Card>
            <h4 className="font-semibold text-gray-800 mb-2">Reason for Rejection</h4>
            <p className="text-sm text-gray-700">{rejectionReason}</p>
          </Card>
        )}

        {(action === 'REJECTED' || action === 'TIMEOUT') && (
          <div className="flex gap-3">
            <Button variant="secondary" onClick={handleResend} isLoading={isProcessing}>
              Resend for Review
            </Button>
            <Button variant="ghost" onClick={reset}>
              New Consultation
            </Button>
          </div>
        )}

        {(action === 'APPROVED' || action === 'MODIFIED') && (
          <div className="text-center space-y-4">
            <p className="text-green-700 font-medium">
              ✓ Your consultation is complete. Please follow the prescription as directed.
            </p>
            <Alert variant="warning" title="Medical Disclaimer">
              This AI-generated prescription has been reviewed by a medical professional.
              Always follow the instructions of your treating physician.
            </Alert>
            <Button onClick={reset} variant="secondary">
              Start New Consultation
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">

      {/* Status banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
            <Mail className="w-5 h-5 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-blue-900">Prescription Sent for Review</h3>
            <p className="text-sm text-blue-700 mt-1">
              Your prescription has been sent to{' '}
              <span className="font-medium">{doctorEmail ?? 'the reviewing physician'}</span>{' '}
              via Gmail for human oversight.
            </p>
            <div className="flex flex-wrap gap-4 mt-3 text-xs text-blue-600">
              {reviewId && (
                <span className="flex items-center gap-1">
                  <ClipboardCheck className="w-3.5 h-3.5" />
                  Review ID: <strong>{reviewId}</strong>
                </span>
              )}
              {sentTime && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Sent at {sentTime}
                </span>
              )}
              {estimatedMinutes && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Estimated response: {estimatedMinutes} min
                </span>
              )}
            </div>
          </div>
          {isProcessing && <Spinner size="sm" />}
        </div>
      </div>

      {/* Instructions accordion */}
      <Card>
        <button
          className="flex items-center justify-between w-full text-left"
          onClick={() => setShowInstructions((v) => !v)}
        >
          <h4 className="font-semibold text-gray-800">How to Submit the Doctor's Response</h4>
          {showInstructions ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </button>

        {showInstructions && (
          <div className="mt-4 space-y-3 text-sm text-gray-600">
            <p>The doctor will reply to the email with one of these commands:</p>
            <div className="space-y-2 font-mono text-xs bg-gray-50 rounded-lg p-4">
              <div className="text-green-700">
                <strong>APPROVE #{reviewId ?? 'REVIEW_ID'}</strong>
                <span className="text-gray-500 font-sans ml-2">— approve as written</span>
              </div>
              <div className="text-blue-700">
                <strong>MODIFY #{reviewId ?? 'REVIEW_ID'} - [changes]</strong>
                <span className="text-gray-500 font-sans ml-2">— approve with changes</span>
              </div>
              <div className="text-red-700">
                <strong>REJECT #{reviewId ?? 'REVIEW_ID'} - [reason]</strong>
                <span className="text-gray-500 font-sans ml-2">— reject</span>
              </div>
            </div>
            <p>Once you receive the reply, paste the email body below and click Submit.</p>
          </div>
        )}
      </Card>

      {/* Email paste area */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Paste Doctor's Email Reply
        </label>
        <textarea
          value={emailContent}
          onChange={(e) => setEmailContent(e.target.value)}
          rows={6}
          placeholder={`Paste the doctor's email reply here.\n\nExample:\nAPPROVE #${reviewId ?? 'rev-001'}`}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     disabled:bg-gray-100 resize-y font-mono"
          disabled={isProcessing}
        />
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <Button
          onClick={handleSubmitResponse}
          isLoading={isProcessing}
          disabled={!emailContent.trim()}
          leftIcon={<ClipboardCheck className="w-4 h-4" />}
        >
          Submit Doctor Response
        </Button>
        <Button
          variant="secondary"
          onClick={handleResend}
          isLoading={isProcessing}
          leftIcon={<RefreshCw className="w-4 h-4" />}
        >
          Resend Prescription
        </Button>
        <Button variant="ghost" onClick={reset}>
          Cancel Consultation
        </Button>
      </div>

      {/* Show recommendations for reference */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <button
          className="flex items-center justify-between w-full px-4 py-3 bg-gray-50 text-left"
          onClick={() => setShowRec((v) => !v)}
        >
          <span className="text-sm font-medium text-gray-700">
            View Prescription / Recommendations
          </span>
          {showRec ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </button>
        {showRec && (
          <div className="p-4 space-y-4">
            <pre className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
              {medicationRecommendations}
            </pre>
            {patientData.language !== 'en' && medicationEnglish && (
              <details className="border border-gray-200 rounded p-3 bg-gray-50">
                <summary className="text-sm font-medium text-gray-600 cursor-pointer">
                  English version
                </summary>
                <pre className="mt-2 whitespace-pre-wrap text-xs text-gray-600">
                  {medicationEnglish}
                </pre>
              </details>
            )}
          </div>
        )}
      </div>

      {/* Error display */}
      {error && (
        <Alert variant="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Alert variant="warning" title="Important">
        No prescription is finalised without explicit doctor approval via Gmail MCP.
        This ensures proper human oversight of all AI-generated medical recommendations.
      </Alert>
    </div>
  );
};