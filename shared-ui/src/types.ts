/**
 * Shared types for LMSilo UI components.
 */

export type JobStatus = 
  | 'pending'
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface Job {
  id: string;
  filename?: string;
  status: JobStatus;
  progress?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface AuditLogEntry {
  id: string;
  service: string;
  action: string;
  timestamp: string;
  username?: string;
  ip_address?: string;
  file_name?: string;
  file_hash?: string;
  status: string;
  processing_time_ms?: number;
  model_used?: string;
  metadata?: Record<string, unknown>;
}

export interface ApiError {
  error: string;
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}
