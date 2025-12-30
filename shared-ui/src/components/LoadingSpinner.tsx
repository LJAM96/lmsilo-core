import React from 'react';

interface LoadingSpinnerProps {
  /** Size: 'sm', 'md', 'lg' */
  size?: 'sm' | 'md' | 'lg';
  /** Loading message */
  message?: string;
  /** Custom CSS class */
  className?: string;
}

/**
 * LoadingSpinner component for indicating loading state.
 */
export function LoadingSpinner({
  size = 'md',
  message,
  className = '',
}: LoadingSpinnerProps) {
  const sizeMap = {
    sm: '16px',
    md: '32px',
    lg: '48px',
  };

  return (
    <div className={`loading-spinner-container ${className}`}>
      <div 
        className="loading-spinner"
        style={{
          width: sizeMap[size],
          height: sizeMap[size],
          border: `3px solid #e5e7eb`,
          borderTopColor: '#3b82f6',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }}
      />
      {message && <span className="loading-message">{message}</span>}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .loading-spinner-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
        }
        .loading-message {
          color: #6b7280;
          font-size: 14px;
        }
      `}</style>
    </div>
  );
}
