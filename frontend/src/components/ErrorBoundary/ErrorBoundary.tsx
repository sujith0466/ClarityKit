import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log unexpected runtime errors safely
    if (import.meta.env.MODE !== "test") {
      console.error("ErrorBoundary caught an error:", error, errorInfo);
    }
  }

  public override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div
          className="card"
          role="alert"
          aria-live="assertive"
          data-testid="error-boundary-fallback"
        >
          <h2>Application Error</h2>
          <p>
            An unexpected error occurred while rendering the application shell.
            Please refresh the page to reload.
          </p>
        </div>
      );
    }

    return this.props.children;
  }
}
