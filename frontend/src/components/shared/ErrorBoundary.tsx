"use client";

import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional fallback UI. If omitted, a default error card is rendered. */
  fallback?: ReactNode;
  /** Section name for the error log. */
  label?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Reusable React error boundary.
 * Catches render errors in child components and shows a recovery UI.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(
      `[MedAI ErrorBoundary${this.props.label ? ` — ${this.props.label}` : ""}]`,
      error,
      info.componentStack
    );
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center p-6 rounded-2xl bg-rose-50 dark:bg-rose-900/10 border border-rose-200 dark:border-rose-800 text-center">
          <AlertTriangle size={28} className="text-rose-500 mb-3" />
          <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-1">
            {this.props.label ? `${this.props.label} failed to load` : "Something went wrong"}
          </h3>
          {this.state.error?.message && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4 max-w-sm">
              {this.state.error.message}
            </p>
          )}
          <button
            onClick={this.handleReset}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-500 text-white text-xs font-medium hover:bg-brand-600 transition active:scale-[0.98]"
          >
            <RotateCcw size={14} />
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
