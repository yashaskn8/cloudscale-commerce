import React, { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface RetryBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  maxRetries?: number;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface RetryBoundaryState {
  hasError: boolean;
  error: Error | null;
  retryCount: number;
}

export class RetryBoundary extends Component<RetryBoundaryProps, RetryBoundaryState> {
  constructor(props: RetryBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, retryCount: 0 };
  }

  static getDerivedStateFromError(error: Error): Partial<RetryBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.props.onError?.(error, errorInfo);
    console.error("[RetryBoundary] Caught error:", error, errorInfo);
  }

  handleRetry = () => {
    const maxRetries = this.props.maxRetries ?? 3;
    if (this.state.retryCount < maxRetries) {
      this.setState((prev) => ({
        hasError: false,
        error: null,
        retryCount: prev.retryCount + 1,
      }));
    }
  };

  render() {
    const maxRetries = this.props.maxRetries ?? 3;

    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const canRetry = this.state.retryCount < maxRetries;

      return (
        <div
          role="alert"
          className="flex flex-col items-center justify-center gap-4 p-8 text-center border border-destructive/20 rounded-2xl bg-destructive/5"
        >
          <div className="p-3 rounded-full bg-destructive/10">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-foreground">Something went wrong</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              {this.state.error?.message || "An unexpected error occurred in this section."}
            </p>
          </div>
          {canRetry ? (
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-primary text-white hover:bg-primary/90 transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <RefreshCw className="h-4 w-4" />
              Retry ({this.state.retryCount}/{maxRetries})
            </button>
          ) : (
            <p className="text-xs text-destructive font-semibold">
              Maximum retry attempts reached. Please refresh the page.
            </p>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
