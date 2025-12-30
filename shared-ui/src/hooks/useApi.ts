import { useState, useCallback } from 'react';
import type { ApiError } from '../types';

interface UseApiOptions {
  /** Base URL for API calls */
  baseUrl?: string;
  /** Default headers */
  headers?: Record<string, string>;
}

interface UseApiReturn<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  fetch: (url: string, options?: RequestInit) => Promise<T | null>;
  post: (url: string, body: unknown) => Promise<T | null>;
  put: (url: string, body: unknown) => Promise<T | null>;
  del: (url: string) => Promise<boolean>;
  reset: () => void;
}

/**
 * useApi hook for making API calls with loading/error state.
 * 
 * Usage:
 * ```tsx
 * const { data, loading, error, fetch } = useApi<Job[]>();
 * 
 * useEffect(() => {
 *   fetch('/api/jobs');
 * }, []);
 * ```
 */
export function useApi<T = unknown>(options: UseApiOptions = {}): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);

  const { baseUrl = '', headers: defaultHeaders = {} } = options;

  const handleResponse = async (response: Response): Promise<T | null> => {
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        error: 'unknown_error',
        code: 'ERR_UNKNOWN',
        message: `HTTP ${response.status}`,
      }));
      throw errorData as ApiError;
    }
    
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      return response.json();
    }
    return null;
  };

  const fetchData = useCallback(async (
    url: string,
    requestOptions: RequestInit = {}
  ): Promise<T | null> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${baseUrl}${url}`, {
        ...requestOptions,
        headers: {
          ...defaultHeaders,
          ...requestOptions.headers,
        },
      });
      
      const result = await handleResponse(response);
      setData(result);
      return result;
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError);
      return null;
    } finally {
      setLoading(false);
    }
  }, [baseUrl, defaultHeaders]);

  const post = useCallback(async (url: string, body: unknown): Promise<T | null> => {
    return fetchData(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }, [fetchData]);

  const put = useCallback(async (url: string, body: unknown): Promise<T | null> => {
    return fetchData(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }, [fetchData]);

  const del = useCallback(async (url: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${baseUrl}${url}`, {
        method: 'DELETE',
        headers: defaultHeaders,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          error: 'delete_failed',
          code: 'ERR_DELETE',
          message: 'Delete failed',
        }));
        throw errorData as ApiError;
      }
      
      return true;
    } catch (err) {
      setError(err as ApiError);
      return false;
    } finally {
      setLoading(false);
    }
  }, [baseUrl, defaultHeaders]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, error, loading, fetch: fetchData, post, put, del, reset };
}
