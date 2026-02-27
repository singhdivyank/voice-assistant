import React, { useEffect, useRef } from 'react';
import { Bot, User } from 'lucide-react';
import { Card } from '../ui/';
import { ConversationPaneProps } from '@/utils/';

export const ConversationPane: React.FC<ConversationPaneProps> = ({ entries, className = '' }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  return (
    <Card className={`flex flex-col h-full min-h-[280px] ${className}`} padding="none">
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50/50">
        <h3 className="font-semibold text-gray-800">Conversation</h3>
        <p className="text-xs text-gray-500 mt-0.5">Your dialogue with the assistant</p>
      </div>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0"
      >
        {entries.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-8">Conversation will appear here</p>
        ) : (
          entries.map((entry, index) => (
            <div
              key={index}
              className={`flex items-start gap-3 ${entry.speaker === 'you' ? 'flex-row-reverse' : ''}`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  entry.speaker === 'you' ? 'bg-green-100' : 'bg-blue-100'
                }`}
              >
                {entry.speaker === 'you' ? (
                  <User className="w-4 h-4 text-green-600" />
                ) : (
                  <Bot className="w-4 h-4 text-blue-600" />
                )}
              </div>
              <div
                className={`flex-1 min-w-0 rounded-lg p-3 max-w-[85%] ${
                  entry.speaker === 'you' ? 'bg-green-50' : 'bg-blue-50'
                }`}
              >
                <p className="text-xs font-medium text-gray-500 mb-1">
                  {entry.speaker === 'you' ? 'You' : 'Doc'}
                </p>
                <p className="text-gray-800 text-sm whitespace-pre-wrap break-words">
                  {entry.text}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
};
