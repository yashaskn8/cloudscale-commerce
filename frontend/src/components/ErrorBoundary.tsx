import { Component } from "react";
import type { ReactNode, ErrorInfo } from "react";
import { AlertTriangle, RefreshCw, RotateCcw } from "lucide-react";
import { observability } from "@/lib/observability";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, info: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorCount: number;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorCount: 0 };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState((prev) => ({ errorCount: prev.errorCount + 1 }));

    // Log to observability system with correlation context
    observability.logError(error, {
      componentStack: info.componentStack,
      errorCount: this.state.errorCount + 1,
      correlationId: observability.getCorrelationId(),
    });

    this.props.onError?.(error, info);
  }

  handleRetryInPlace = () => {
    this.setState({ hasError: false, error: null });
  };

  handleFullReload = () => {
    this.setState({ hasError: false, error: null, errorCount: 0 });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      const canRetryInPlace = this.state.errorCount < 3;

      return (
        <div className="flex flex-col items-center justify-center py-20 px-4 text-center" role="alert" aria-live="assertive">
          <div className="rounded-full bg-destructive/10 p-4 mb-4">
            <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-2">Something went wrong</h2>
          <p className="text-sm text-muted-foreground max-w-md mb-2">
            An unexpected error occurred in the application. Your data is safe.
          </p>
          {this.state.error?.message && (
            <details className="text-xs text-muted-foreground max-w-md mb-6 cursor-pointer">
              <summary className="hover:text-foreground transition-colors">Technical details</summary>
              <code className="block mt-2 p-2 bg-muted rounded text-left break-all">
                {this.state.error.message}
              </code>
            </details>
          )}
          <div className="flex items-center gap-3">
            {canRetryInPlace && (
              <button
                onClick={this.handleRetryInPlace}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Try Again
              </button>
            )}
            <button
              onClick={this.handleFullReload}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Reload Page
            </button>
          </div>
          {this.state.errorCount >= 3 && (
            <p className="text-xs text-muted-foreground mt-4">
              This error has occurred multiple times. A full page reload is recommended.
            </p>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
