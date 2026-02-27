import React from 'react';
import { Activity } from 'lucide-react';
import { HeaderProps } from '@/utils/';

export const Header: React.FC<HeaderProps> = () => {
    return (
        <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
            <div className="max-w-6xl mx-auto px-4 py-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center shadow-md">
                        <Activity className="w-6 h-6 text-white" />
                        </div>
                        <div>
                        <h1 className="text-xl font-bold text-gray-800">DocJarvis</h1>
                        <p className="text-xs text-gray-500">AI Medical Assistant</p>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
};