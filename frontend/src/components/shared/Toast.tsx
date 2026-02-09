"use client";

import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  X,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────

export type ToastVariant = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
  duration?: number; // ms, 0 = persistent
}

interface ToastContextType {
  toast: (opts: Omit<Toast, "id">) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  warning: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

// ─── Hook ────────────────────────────────────────────────

export function useToast(): ToastContextType {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Fallback no-op so components don't crash if used outside provider
    return {
      toast: () => {},
      success: () => {},
      error: () => {},
      warning: () => {},
      info: () => {},
      dismiss: () => {},
    };
  }
  return ctx;
}

// ─── Single Toast Component ─────────────────────────────

const variantConfig: Record<
  ToastVariant,
  {
    icon: React.ElementType;
    iconColor: string;
    bgClass: string;
    borderClass: string;
  }
> = {
  success: {
    icon: CheckCircle2,
    iconColor: "text-emerald-500",
    bgClass: "bg-emerald-50 dark:bg-emerald-900/20",
    borderClass: "border-emerald-200 dark:border-emerald-800",
  },
  error: {
    icon: AlertCircle,
    iconColor: "text-rose-500",
    bgClass: "bg-rose-50 dark:bg-rose-900/20",
    borderClass: "border-rose-200 dark:border-rose-800",
  },
  warning: {
    icon: AlertTriangle,
    iconColor: "text-amber-500",
    bgClass: "bg-amber-50 dark:bg-amber-900/20",
    borderClass: "border-amber-200 dark:border-amber-800",
  },
  info: {
    icon: Info,
    iconColor: "text-blue-500",
    bgClass: "bg-blue-50 dark:bg-blue-900/20",
    borderClass: "border-blue-200 dark:border-blue-800",
  },
};

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: () => void;
}) {
  const config = variantConfig[toast.variant];
  const Icon = config.icon;

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg",
        "animate-slide-up transition-all duration-300",
        "max-w-sm w-full",
        config.bgClass,
        config.borderClass
      )}
    >
      <Icon size={18} className={cn("flex-shrink-0 mt-0.5", config.iconColor)} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 dark:text-white">
          {toast.title}
        </p>
        {toast.description && (
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 leading-relaxed">
            {toast.description}
          </p>
        )}
      </div>
      <button
        onClick={onDismiss}
        className="p-0.5 rounded hover:bg-white/50 dark:hover:bg-gray-800/50 transition flex-shrink-0"
        aria-label="Dismiss notification"
      >
        <X size={14} className="text-gray-400" />
      </button>
    </div>
  );
}

// ─── Provider ────────────────────────────────────────────

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (opts: Omit<Toast, "id">) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      const duration = opts.duration ?? (opts.variant === "error" ? 8000 : 5000);

      setToasts((prev) => [...prev.slice(-4), { ...opts, id }]); // Keep max 5

      if (duration > 0) {
        const timer = setTimeout(() => dismiss(id), duration);
        timersRef.current.set(id, timer);
      }
    },
    [dismiss]
  );

  const contextValue: ToastContextType = {
    toast: addToast,
    success: (title, description) =>
      addToast({ variant: "success", title, description }),
    error: (title, description) =>
      addToast({ variant: "error", title, description }),
    warning: (title, description) =>
      addToast({ variant: "warning", title, description }),
    info: (title, description) =>
      addToast({ variant: "info", title, description }),
    dismiss,
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}

      {/* Toast container — fixed bottom-right */}
      {toasts.length > 0 && (
        <div
          aria-live="polite"
          aria-label="Notifications"
          className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-auto"
        >
          {toasts.map((t) => (
            <ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}
