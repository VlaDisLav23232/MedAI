"use client";

import React from "react";
import { cn, getConfidenceBg } from "@/lib/utils";

interface ConfidenceBadgeProps {
  confidence: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export function ConfidenceBadge({
  confidence,
  size = "md",
  showLabel = true,
  className,
}: ConfidenceBadgeProps) {
  const pct = Math.round(confidence * 100);
  const colorClasses = getConfidenceBg(confidence);

  const sizeClasses = {
    sm: "text-xs px-1.5 py-0.5",
    md: "text-sm px-2.5 py-1",
    lg: "text-base px-3 py-1.5",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-mono font-semibold rounded-lg border",
        colorClasses,
        sizeClasses[size],
        className
      )}
    >
      {pct}%{showLabel && <span className="font-normal opacity-70">conf</span>}
    </span>
  );
}
