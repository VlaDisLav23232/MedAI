"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[MedAI] Unhandled error:", error);
  }, [error]);

  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <div className="w-16 h-16 rounded-2xl bg-rose-500/10 flex items-center justify-center mx-auto mb-4">
          <AlertTriangle size={32} className="text-rose-500" />
        </div>
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
          Something went wrong
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          An unexpected error occurred. This is likely a temporary issue. Please
          try again.
        </p>
        {error.message && (
          <pre className="mb-6 px-4 py-3 rounded-xl bg-gray-100 dark:bg-surface-dark-2 text-xs text-gray-600 dark:text-gray-400 text-left overflow-auto max-h-32">
            {error.message}
          </pre>
        )}
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition shadow-lg shadow-brand-500/25 active:scale-[0.98]"
        >
          <RotateCcw size={16} />
          Try Again
        </button>
      </div>
    </div>
  );
}
