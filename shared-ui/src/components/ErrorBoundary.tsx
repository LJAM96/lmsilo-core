import React, { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Fallback UI when error occurs */
  fallback?: ReactNode;
  /** Callback when error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary component for catching React errors.
 * 
 * Usage:
 * ```tsx
 * <ErrorBoundary fallback={<div>Something went wrong</div>}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary">
          <div className="error-boundary-content">
            <h2>Something went wrong</h2>
            <p>{this.state.error?.message || 'An unexpected error occurred'}</p>
            <button 
              onClick={() => this.setState({ hasError: false, error: null })}
              className="retry-button"
            >
              Try again
            </button>
          </div>
          <style>{`
            .error-boundary {
              padding: 24px;
              border: 1px solid #fee2e2;
              border-radius: 8px;
              background: #fef2f2;
            }
            .error-boundary h2 {
              color: #dc2626;
              margin: 0 0 8px;
            }
            .error-boundary p {
              color: #7f1d1d;
              margin: 0 0 16px;
            }
            .retry-button {
              padding: 8px 16px;
              background: #dc2626;
              color: white;
              border: none;
              border-radius: 4px;
              cursor: pointer;
            }
            .retry-button:hover {
              background: #b91c1c;
            }
          `}</style>
        </div>
      );
    }

    return this.props.children;
  }
}
