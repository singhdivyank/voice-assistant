import React from 'react';

export const Footer: React.FC = () => {
    return (
        <footer className="bg-gray-50 border-t border-gray-200 mt-auto">
            <div className="max-w-6xl mx-auto px-4 py-6">
                <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <p className="text-xs text-gray-400 text-center md:text-right max-w-md">
                    This application is for informational purposes only.
                    Always consult a qualified healthcare provider.
                </p>
                </div>
            </div>
        </footer>
    );
};