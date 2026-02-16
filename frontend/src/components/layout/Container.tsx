import React from 'react';

interface ContainerProps {
    children: React.ReactNode;
    size?: 'sm' | 'md' | 'lg' | 'xl';
    className?: string;
}

const containerSizes = {
    sm: 'max-w-xl',
    md: 'max-w-2xl',
    lg: 'max-w-4xl',
    xl: 'max-w-6xl',
};

export const Container: React.FC<ContainerProps> = (
    children,
    size = 'lg',
    className = '',
) => {
    return (
        <div className={`${containerSizes[size]} mx-auto px-4 ${className}`}>
            {children}
        </div>
    );
};
