"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import type { ReasoningStep } from "@/lib/types";
import { Brain, ChevronDown, ChevronRight } from "lucide-react";

interface ReasoningTraceProps {
  steps: ReasoningStep[];
  className?: string;
}

export function ReasoningTrace({ steps, className }: ReasoningTraceProps) {
  const [expanded, setExpanded] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set([1, 2]));

  const toggleStep = (step: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(step)) {
        next.delete(step);
      } else {
        next.add(step);
      }
      return next;
    });
  };

  return (
    <div
      className={cn(
        "rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-surface-dark-2 overflow-hidden",
        className
      )}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition"
      >
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-accent-violet" />
          <span className="text-sm font-bold text-gray-900 dark:text-white">
            Reasoning Trace
          </span>
          <span className="text-[10px] font-medium text-gray-400 bg-gray-100 dark:bg-surface-dark-3 px-2 py-0.5 rounded-full">
            {steps.length} steps
          </span>
        </div>
        <ChevronDown
          size={16}
          className={cn(
            "text-gray-400 transition-transform",
            !expanded && "-rotate-90"
          )}
        />
      </button>

      {/* Steps */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-800">
          {steps.map((step, i) => {
            const isOpen = expandedSteps.has(step.step);
            const isLast = i === steps.length - 1;
            return (
              <div
                key={step.step}
                className={cn(
                  "border-b border-gray-100 dark:border-gray-800 last:border-b-0"
                )}
              >
                <button
                  onClick={() => toggleStep(step.step)}
                  className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition group"
                >
                  {/* Step indicator line */}
                  <div className="relative flex flex-col items-center flex-shrink-0 pt-0.5">
                    <div
                      className={cn(
                        "w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold",
                        isLast
                          ? "bg-accent-emerald/20 text-accent-emerald border border-accent-emerald/30"
                          : "bg-brand-50 dark:bg-brand-900/20 text-brand-500 border border-brand-200 dark:border-brand-800"
                      )}
                    >
                      {step.step}
                    </div>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 truncate">
                        {step.thought.split(".")[0]}.
                      </span>
                      <ChevronRight
                        size={12}
                        className={cn(
                          "text-gray-400 transition-transform flex-shrink-0",
                          isOpen && "rotate-90"
                        )}
                      />
                    </div>
                    {isOpen && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed mt-1.5 animate-fade-in">
                        {step.thought}
                      </p>
                    )}
                  </div>
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
