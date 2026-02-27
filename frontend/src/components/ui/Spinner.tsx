import React from 'react';

import { spinnerSizes, SpinnerProps } from '@/utils/';

export const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className = '' }) => {
  return (
    <div
      className={`
        animate-spin rounded-full
        border-blue-600 border-t-transparent
        ${spinnerSizes[size]}
        ${className}
      `}
      role="status"
      aria-label="Loading"
    />
  );
};