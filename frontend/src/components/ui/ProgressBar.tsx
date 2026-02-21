import React from 'react';

import { progressSizes, ProgressBarProps } from '@/utils';

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  showLabel = false,
  size = 'md',
  className = '',
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div className={className}>
      {showLabel && (
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>Progress</span>
          <span>{Math.round(percentage)}%</span>
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full ${progressSizes[size]}`}>
        <div
          className={`bg-blue-600 rounded-full transition-all duration-300 ${progressSizes[size]}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};