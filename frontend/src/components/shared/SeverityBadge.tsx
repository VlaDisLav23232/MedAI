"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, ShieldAlert, Info } from "lucide-react";

type Severity = "low" | "moderate" | "high" | "critical" | "normal" | "warning" | (string & {});

const severityConfig: Record<
  Severity,
  { icon: React.ElementType; bg: string; text: string; border: string; label: string }
> = {
  low: {
    icon: Info,
    bg: "bg-gray-50 dark:bg-gray-900/30",
    text: "text-gray-600 dark:text-gray-400",
    border: "border-gray-200 dark:border-gray-700",
    label: "Low",
  },
  normal: {
    icon: CheckCircle2,
    bg: "bg-emerald-50 dark:bg-emerald-900/20",
    text: "text-emerald-700 dark:text-emerald-400",
    border: "border-emerald-200 dark:border-emerald-800",
    label: "Normal",
  },
  moderate: {
    icon: AlertTriangle,
    bg: "bg-amber-50 dark:bg-amber-900/20",
    text: "text-amber-700 dark:text-amber-400",
    border: "border-amber-200 dark:border-amber-800",
    label: "Moderate",
  },
  warning: {
    icon: AlertTriangle,
    bg: "bg-amber-50 dark:bg-amber-900/20",
    text: "text-amber-700 dark:text-amber-400",
    border: "border-amber-200 dark:border-amber-800",
    label: "Warning",
  },
  high: {
    icon: ShieldAlert,
    bg: "bg-orange-50 dark:bg-orange-900/20",
    text: "text-orange-700 dark:text-orange-400",
    border: "border-orange-200 dark:border-orange-800",
    label: "High",
  },
  critical: {
    icon: ShieldAlert,
    bg: "bg-rose-50 dark:bg-rose-900/20",
    text: "text-rose-700 dark:text-rose-400",
    border: "border-rose-200 dark:border-rose-800",
    label: "Critical",
  },
};

interface SeverityBadgeProps {
  severity: Severity;
  size?: "sm" | "md";
  className?: string;
}

export function SeverityBadge({ severity, size = "sm", className }: SeverityBadgeProps) {
  if (!severity) return null;
  const config = severityConfig[severity] ?? severityConfig.low;
  if (!config) return null;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-lg border font-medium",
        config.bg,
        config.text,
        config.border,
        size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-2.5 py-1",
        className
      )}
    >
      <Icon size={size === "sm" ? 12 : 14} />
      {config.label}
    </span>
  );
}
