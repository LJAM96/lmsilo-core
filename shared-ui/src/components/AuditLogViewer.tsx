import React, { useState, useEffect } from 'react';
import type { AuditLogEntry } from '../types';

interface AuditLogViewerProps {
  /** API endpoint to fetch audit logs */
  apiUrl: string;
  /** Service filter (optional) */
  service?: string;
  /** Maximum entries to display */
  limit?: number;
  /** Custom CSS class */
  className?: string;
  /** Callback when entry is clicked */
  onEntryClick?: (entry: AuditLogEntry) => void;
}

/**
 * AuditLogViewer component for displaying audit logs.
 * 
 * Usage:
 * ```tsx
 * <AuditLogViewer 
 *   apiUrl="/api/audit"
 *   service="transcribe"
 *   limit={50}
 * />
 * ```
 */
export function AuditLogViewer({
  apiUrl,
  service,
  limit = 50,
  className = '',
  onEntryClick,
}: AuditLogViewerProps) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams({ limit: String(limit) });
        if (service) params.append('service', service);
        
        const response = await fetch(`${apiUrl}?${params}`);
        if (!response.ok) throw new Error('Failed to fetch audit logs');
        
        const data = await response.json();
        setLogs(data.items || data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [apiUrl, service, limit]);

  if (loading) {
    return (
      <div className={`audit-log-viewer loading ${className}`}>
        <div className="loading-spinner">Loading audit logs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`audit-log-viewer error ${className}`}>
        <div className="error-message">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className={`audit-log-viewer ${className}`}>
      <table className="audit-log-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Service</th>
            <th>Action</th>
            <th>User</th>
            <th>Status</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr 
              key={log.id}
              onClick={() => onEntryClick?.(log)}
              className={onEntryClick ? 'clickable' : ''}
            >
              <td>{new Date(log.timestamp).toLocaleString()}</td>
              <td>{log.service}</td>
              <td>{log.action}</td>
              <td>{log.username || 'anonymous'}</td>
              <td>
                <span className={`status-badge status-${log.status}`}>
                  {log.status}
                </span>
              </td>
              <td>
                {log.file_name && <span className="file-name">{log.file_name}</span>}
                {log.processing_time_ms && (
                  <span className="processing-time">
                    {(log.processing_time_ms / 1000).toFixed(2)}s
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {logs.length === 0 && (
        <div className="no-logs">No audit logs found</div>
      )}
    </div>
  );
}
