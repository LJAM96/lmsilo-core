import React from 'react';
import type { JobStatus } from '../types';

interface StatusBadgeProps {
  status: JobStatus | string;
  className?: string;
}

const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
  pending: { bg: '#fef3c7', text: '#92400e', label: 'Pending' },
  queued: { bg: '#e0e7ff', text: '#3730a3', label: 'Queued' },
  processing: { bg: '#dbeafe', text: '#1e40af', label: 'Processing' },
  completed: { bg: '#dcfce7', text: '#166534', label: 'Completed' },
  failed: { bg: '#fee2e2', text: '#dc2626', label: 'Failed' },
  cancelled: { bg: '#f3f4f6', text: '#6b7280', label: 'Cancelled' },
  success: { bg: '#dcfce7', text: '#166534', label: 'Success' },
  error: { bg: '#fee2e2', text: '#dc2626', label: 'Error' },
};

/**
 * StatusBadge component for displaying job/task status.
 */
export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = statusConfig[status] || { bg: '#f3f4f6', text: '#6b7280', label: status };

  return (
    <span
      className={`status-badge ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        fontSize: '12px',
        fontWeight: 500,
        borderRadius: '9999px',
        backgroundColor: config.bg,
        color: config.text,
      }}
    >
      {config.label}
    </span>
  );
}
