import React, { useState, useEffect } from 'react';
import type { Job, JobStatus } from '../types';
import { StatusBadge } from './StatusBadge';

interface JobListProps {
  /** API endpoint to fetch jobs */
  apiUrl: string;
  /** Status filter (optional) */
  status?: JobStatus;
  /** Maximum jobs to display */
  limit?: number;
  /** Enable auto-refresh */
  autoRefresh?: boolean;
  /** Refresh interval in ms */
  refreshInterval?: number;
  /** Custom CSS class */
  className?: string;
  /** Callback when job is clicked */
  onJobClick?: (job: Job) => void;
  /** Callback when delete is clicked */
  onDeleteClick?: (job: Job) => void;
}

/**
 * JobList component for displaying and managing jobs.
 */
export function JobList({
  apiUrl,
  status,
  limit = 20,
  autoRefresh = false,
  refreshInterval = 5000,
  className = '',
  onJobClick,
  onDeleteClick,
}: JobListProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      const params = new URLSearchParams({ limit: String(limit) });
      if (status) params.append('status', status);
      
      const response = await fetch(`${apiUrl}?${params}`);
      if (!response.ok) throw new Error('Failed to fetch jobs');
      
      const data = await response.json();
      setJobs(data.items || data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    
    if (autoRefresh) {
      const interval = setInterval(fetchJobs, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [apiUrl, status, limit, autoRefresh, refreshInterval]);

  if (loading) {
    return (
      <div className={`job-list loading ${className}`}>
        <div className="loading-spinner">Loading jobs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`job-list error ${className}`}>
        <div className="error-message">Error: {error}</div>
        <button onClick={fetchJobs}>Retry</button>
      </div>
    );
  }

  return (
    <div className={`job-list ${className}`}>
      <div className="job-list-header">
        <span className="job-count">{jobs.length} jobs</span>
        <button onClick={fetchJobs} className="refresh-btn">Refresh</button>
      </div>
      
      <ul className="job-items">
        {jobs.map((job) => (
          <li 
            key={job.id}
            className={`job-item status-${job.status}`}
            onClick={() => onJobClick?.(job)}
          >
            <div className="job-info">
              <span className="job-filename">{job.filename || job.id}</span>
              <span className="job-time">
                {new Date(job.created_at).toLocaleString()}
              </span>
            </div>
            
            <div className="job-status">
              <StatusBadge status={job.status} />
              {job.progress !== undefined && job.status === 'processing' && (
                <span className="job-progress">{job.progress}%</span>
              )}
            </div>
            
            {onDeleteClick && (
              <button 
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteClick(job);
                }}
              >
                ×
              </button>
            )}
          </li>
        ))}
      </ul>
      
      {jobs.length === 0 && (
        <div className="no-jobs">No jobs found</div>
      )}
    </div>
  );
}
