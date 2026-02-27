import React from 'react';
import { Card, Spinner } from '../ui/';
import { PrescriptionPaneProps } from '@/utils/';

export const PrescriptionPane: React.FC<PrescriptionPaneProps> = ({
  content,
  medicationEnglish = null,
  language = 'en',
  isLoading = false,
  className = '',
}) => {
  const showEnglishParaphrase = language !== 'en' && medicationEnglish;

  return (
    <Card className={`flex flex-col h-full min-h-[280px] ${className}`} padding="none">
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50/50">
        <h3 className="font-semibold text-gray-800">Prescription</h3>
        <p className="text-xs text-gray-500 mt-0.5">Recommendations will appear here</p>
      </div>
      <div className="flex-1 overflow-y-auto p-4 min-h-0 bg-gray-50/50">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Spinner size="lg" className="mb-4" />
            <p className="text-gray-600 text-sm font-medium">Generating recommendations...</p>
            <p className="text-gray-400 text-xs mt-1">This may take a few moments</p>
          </div>
        ) : content ? (
          <div className="prose prose-sm max-w-none space-y-4">
            <div>
              <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed text-sm">
                {content}
              </pre>
            </div>
            {showEnglishParaphrase && (
              <details className="border border-gray-200 rounded-lg bg-white p-3">
                <summary className="text-sm font-medium text-gray-700 cursor-pointer">
                  English version (paraphrase)
                </summary>
                <pre className="mt-2 whitespace-pre-wrap font-sans text-gray-600 leading-relaxed text-xs">
                  {medicationEnglish}
                </pre>
              </details>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full min-h-[200px] text-gray-400">
            <p className="text-sm">Prescription will appear here after the consultation</p>
          </div>
        )}
      </div>
    </Card>
  );
};
