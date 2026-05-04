import React from 'react';

import { paddingStyles } from '@/utils/';
import type { CardProps, CardHeaderProps } from '@/utils/';

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  padding = 'md',
}) => {
  return (
    <div
      className={`
        bg-white rounded-xl shadow-sm border border-gray-200
        ${paddingStyles[padding]}
        ${className}
      `}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  action,
}) => {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
};
