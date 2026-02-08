"use client";

import React, { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import type { ReasoningStep } from "@/lib/types";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  ChevronsUpDown,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface ReasoningTraceProps {
  steps: ReasoningStep[];
  className?: string;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ReasoningTrace({ steps, className }: ReasoningTraceProps) {
  const [expanded, setExpanded] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(
    () => new Set(steps.slice(0, 2).map((s) => s.step))
  );

  const toggleStep = useCallback((step: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(step)) next.delete(step);
      else next.add(step);
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedSteps(new Set(steps.map((s) => s.step)));
  }, [steps]);

  const collapseAll = useCallback(() => {
    setExpandedSteps(new Set());
  }, []);

  const allExpanded = expandedSteps.size === steps.length;

  return (
    <div
      className={cn(
        "rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-surface-dark-2 overflow-hidden neo-shadow",
        className
      )}
      role="region"
      aria-label="AI reasoning trace"
    >
      {/* ── Header ─────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-800">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-2 hover:opacity-80 transition"
          aria-expanded={expanded}
          aria-controls="reasoning-steps"
        >
          <Brain size={16} className="text-accent-violet" aria-hidden="true" />
          <span className="text-sm font-bold text-gray-900 dark:text-white">
            Reasoning Trace
          </span>
          <span className="text-[10px] font-medium text-gray-400 bg-gray-100 dark:bg-surface-dark-3 px-2 py-0.5 rounded-full">
            {steps.length} steps
          </span>
          <ChevronDown
            size={14}
            className={cn(
              "text-gray-400 transition-transform duration-200",
              !expanded && "-rotate-90"
            )}
          />
        </button>

        {expanded && steps.length > 2 && (
          <button
            onClick={allExpanded ? collapseAll : expandAll}
            className="flex items-center gap-1 text-[10px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
            aria-label={allExpanded ? "Collapse all steps" : "Expand all steps"}
          >
            <ChevronsUpDown size={12} />
            {allExpanded ? "Collapse all" : "Expand all"}
          </button>
        )}
      </div>

      {/* ── Steps list ─────────────────────────────── */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id="reasoning-steps"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <ol className="list-none m-0 p-0" aria-label="Reasoning steps">
              {steps.map((step, i) => {
                const isOpen = expandedSteps.has(step.step);
                const isLast = i === steps.length - 1;
                // First sentence for collapsed view
                const firstSentence =
                  step.thought.split(/(?<=\.)\s/)[0] || step.thought;
                const hasMore = step.thought.length > firstSentence.length;

                return (
                  <li
                    key={step.step}
                    className="border-b border-gray-100 dark:border-gray-800 last:border-b-0"
                  >
                    <button
                      onClick={() => toggleStep(step.step)}
                      className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition group"
                      aria-expanded={isOpen}
                      aria-controls={`step-content-${step.step}`}
                    >
                      {/* ── Step indicator + connecting line ── */}
                      <div className="relative flex flex-col items-center flex-shrink-0 pt-0.5">
                        <div
                          className={cn(
                            "w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold transition-colors",
                            isLast
                              ? "bg-accent-emerald/20 text-accent-emerald border border-accent-emerald/30"
                              : isOpen
                                ? "bg-brand-500/15 text-brand-500 border border-brand-300 dark:border-brand-700"
                                : "bg-gray-100 dark:bg-surface-dark-3 text-gray-500 border border-gray-200 dark:border-gray-700"
                          )}
                        >
                          {isLast ? (
                            <CheckCircle2 size={14} />
                          ) : (
                            step.step
                          )}
                        </div>
                        {/* Vertical connector */}
                        {!isLast && (
                          <div className="absolute top-8 w-px h-[calc(100%-8px)] bg-gray-200 dark:bg-gray-700" />
                        )}
                      </div>

                      {/* ── Content ─────────────────────── */}
                      <div className="flex-1 min-w-0 py-0.5">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "text-xs font-semibold truncate transition-colors",
                              isOpen
                                ? "text-gray-900 dark:text-white"
                                : "text-gray-600 dark:text-gray-400"
                            )}
                          >
                            Step {step.step}
                            {!isOpen && `: ${firstSentence}`}
                          </span>
                          {hasMore && (
                            <ChevronRight
                              size={12}
                              className={cn(
                                "text-gray-400 transition-transform flex-shrink-0",
                                isOpen && "rotate-90"
                              )}
                            />
                          )}
                        </div>

                        <AnimatePresence initial={false}>
                          {isOpen && (
                            <motion.p
                              id={`step-content-${step.step}`}
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.15 }}
                              className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed mt-1.5 overflow-hidden"
                            >
                              {step.thought}
                            </motion.p>
                          )}
                        </AnimatePresence>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ol>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
