import React from 'react';

import { AlertProps, alertStyles } from '@/utils/'; 

export const Alert: React.FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  onClose,
}) => {
  return (
    <div className={`p-4 rounded-lg border ${alertStyles[variant]}`} role="alert">
      <div className="flex items-start justify-between">
        <div>
          {title && <h4 className="font-semibold mb-1">{title}</h4>}
          <div className="text-sm">{children}</div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="ml-4 text-current opacity-70 hover:opacity-100"
            aria-label="Close"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
};