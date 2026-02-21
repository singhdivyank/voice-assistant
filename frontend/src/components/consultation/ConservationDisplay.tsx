import React, { useEffect, useRef } from 'react';
import { Bot, User } from 'lucide-react';
import { Card } from '../ui/Card'; 
import { ConversationDisplayProps } from '@/utils';

export const ConversationDisplay: React.FC<ConversationDisplayProps> = ({ conversations }) => {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [conversations]);

    if (conversations.length == 0) {
        return (
            <Card className='text-center py-8 bg-gray-50'>
                <p className="text-gray-500">Conversation will appear here</p>
            </Card>
        );
    }

    return (
        <Card>
            <h3 className="font-semibold text-gray-800 mb-4">Conversation History</h3>
            <div
                ref={scrollRef}
                className="max-h-96 overflow-y-auto space-y-4 pr-2"
            >
                {conversations.map((turn, index) => (
                    <div key={index} className="space-y-3">
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                                <Bot className="w-4 h-4 text-blue-600"/>
                            </div>
                            <div className="bg-blue-50 rounded-lg p-3">
                                <p className="text-gray-800">{turn.question}</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                                <User className="w-4 h-4 text-green-600"/>
                            </div>
                            <div className="flex-1">
                                <p className="text-sm font-medium text-green-600 mb-1">You</p>
                                <div className="bg-green-50 rounded-lg p-3">
                                    <p className="text-gray-800">{turn.answer}</p>
                                </div>
                            </div>
                        </div>
                        {index < conversations.length - 1 && (
                            <div className="border-b border-gray-100 my-4"></div>
                        )}
                    </div>
                ))}
            </div>
        </Card>
    );
};