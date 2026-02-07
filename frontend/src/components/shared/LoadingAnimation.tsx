"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface LoadingAnimationProps {
  label?: string;
  variant?: "dots" | "pulse" | "orbital";
  className?: string;
}

export function LoadingAnimation({
  label = "Processing",
  variant = "orbital",
  className,
}: LoadingAnimationProps) {
  if (variant === "dots") {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-brand-500"
              style={{
                animation: `pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
        {label && (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {label}
          </span>
        )}
      </div>
    );
  }

  if (variant === "pulse") {
    return (
      <div className={cn("flex items-center gap-3", className)}>
        <div className="relative w-5 h-5">
          <div className="absolute inset-0 rounded-full bg-brand-500/30 animate-ping" />
          <div className="absolute inset-1 rounded-full bg-brand-500" />
        </div>
        {label && (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {label}
          </span>
        )}
      </div>
    );
  }

  // orbital
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative w-6 h-6">
        <div className="absolute inset-0 rounded-full border-2 border-brand-200 dark:border-brand-900" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-brand-500 animate-spin" />
      </div>
      {label && (
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {label}
        </span>
      )}
    </div>
  );
}
