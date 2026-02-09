"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { ExplainabilityTooltip } from "@/components/shared/ExplainabilityTooltip";
import type { ConditionScore } from "@/lib/types";
import { BarChart3, ChevronDown, ChevronUp } from "lucide-react";

/* ──────────────────────────────────────────────────────────────
 *  ConditionScoresChart
 *  Horizontal probability bars for MedSigLIP condition scores.
 *  Clickable bars to switch the active heatmap in the viewer.
 * ────────────────────────────────────────────────────────────── */

interface ConditionScoresChartProps {
  scores: ConditionScore[];
  /** Currently selected condition label (for heatmap sync) */
  selectedLabel?: string;
  /** Callback when a condition bar is clicked */
  onSelect?: (label: string) => void;
  /** Show all scores or top N */
  maxVisible?: number;
  className?: string;
}

/** Map probability 0-1 → tailwind-compatible color */
function getBarColor(prob: number): string {
  if (prob >= 0.5) return "bg-rose-500";
  if (prob >= 0.3) return "bg-amber-500";
  if (prob >= 0.15) return "bg-yellow-500";
  if (prob >= 0.05) return "bg-sky-500";
  return "bg-slate-400";
}

function getBarGlow(prob: number): string {
  if (prob >= 0.5) return "shadow-rose-500/30";
  if (prob >= 0.3) return "shadow-amber-500/30";
  return "";
}

export function ConditionScoresChart({
  scores,
  selectedLabel,
  onSelect,
  maxVisible = 6,
  className,
}: ConditionScoresChartProps) {
  const [expanded, setExpanded] = useState(false);

  // Sort by probability descending
  const sorted = [...scores].sort((a, b) => b.probability - a.probability);
  const visible = expanded ? sorted : sorted.slice(0, maxVisible);
  const hasMore = sorted.length > maxVisible;

  // Find the max probability for relative bar width
  const maxProb = Math.max(...sorted.map((s) => s.probability), 0.01);

  if (scores.length === 0) return null;

  return (
    <div className={cn("space-y-2", className)}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <BarChart3 size={14} className="text-brand-500" aria-hidden="true" />
        <h3 className="text-xs font-bold text-gray-900 dark:text-white">
          Condition Probability
        </h3>
        <ExplainabilityTooltip
          content="Zero-shot contrastive classification"
          detail="Probabilities from MedSigLIP comparing the medical image against candidate condition labels. Softmax-normalized across all labels — values are relative, not absolute."
          position="right"
        />
      </div>

      {/* Bars */}
      <div className="space-y-1.5">
        <AnimatePresence mode="popLayout">
          {visible.map((score, idx) => {
            const isSelected = selectedLabel === score.label;
            const barWidth = Math.max((score.probability / maxProb) * 100, 2);

            return (
              <motion.button
                key={score.label}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -12 }}
                transition={{ delay: idx * 0.04, duration: 0.25 }}
                onClick={() => onSelect?.(score.label)}
                className={cn(
                  "w-full group flex items-center gap-2 py-1 px-2 rounded-lg transition-all text-left",
                  isSelected
                    ? "bg-brand-500/10 ring-1 ring-brand-500/40"
                    : "hover:bg-gray-100 dark:hover:bg-surface-dark-3",
                )}
                aria-label={`${score.label}: ${(score.probability * 100).toFixed(1)}% probability`}
              >
                {/* Rank badge */}
                <span
                  className={cn(
                    "w-4 h-4 flex-shrink-0 rounded text-[9px] font-bold flex items-center justify-center",
                    idx === 0
                      ? "bg-rose-500/20 text-rose-500"
                      : "bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400",
                  )}
                >
                  {idx + 1}
                </span>

                {/* Label */}
                <span
                  className={cn(
                    "text-[11px] font-medium w-28 truncate flex-shrink-0",
                    isSelected
                      ? "text-brand-600 dark:text-brand-400"
                      : "text-gray-700 dark:text-gray-300",
                  )}
                  title={score.label}
                >
                  {score.label}
                </span>

                {/* Bar container */}
                <div className="flex-1 h-3 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden relative">
                  <motion.div
                    className={cn(
                      "h-full rounded-full",
                      getBarColor(score.probability),
                      isSelected && "shadow-md " + getBarGlow(score.probability),
                    )}
                    initial={{ width: 0 }}
                    animate={{ width: `${barWidth}%` }}
                    transition={{ delay: idx * 0.04 + 0.1, duration: 0.5, ease: "easeOut" }}
                  />
                </div>

                {/* Percentage */}
                <span
                  className={cn(
                    "text-[11px] font-mono w-12 text-right flex-shrink-0",
                    score.probability >= 0.3
                      ? "text-rose-600 dark:text-rose-400 font-semibold"
                      : "text-gray-500",
                  )}
                >
                  {(score.probability * 100).toFixed(1)}%
                </span>
              </motion.button>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Expand / collapse */}
      {hasMore && (
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? "Show fewer" : `Show all ${sorted.length} conditions`}
        </button>
      )}

      {/* Sigmoid/logit detail for selected */}
      {selectedLabel && (
        <SelectedDetail
          score={sorted.find((s) => s.label === selectedLabel)}
        />
      )}
    </div>
  );
}

/* ── Detail panel for the selected condition ──────────────── */

function SelectedDetail({ score }: { score?: ConditionScore }) {
  if (!score) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="px-2 py-2 rounded-lg bg-gray-50 dark:bg-surface-dark-3 space-y-1"
    >
      <p className="text-[10px] font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
        {score.label} — Detail
      </p>
      <div className="grid grid-cols-3 gap-2">
        <MetricCell
          label="Softmax"
          value={`${(score.probability * 100).toFixed(2)}%`}
          tooltip="Relative probability across all labels (sums to 100%)"
        />
        {score.sigmoid_score != null && (
          <MetricCell
            label="Sigmoid"
            value={`${(score.sigmoid_score * 100).toFixed(4)}%`}
            tooltip="Independent per-label probability — not normalized. Reflects absolute model confidence for this specific condition."
          />
        )}
        {score.raw_logit != null && (
          <MetricCell
            label="Logit"
            value={score.raw_logit.toFixed(2)}
            tooltip="Raw model output before activation. Negative values indicate low confidence; positive values indicate high confidence."
          />
        )}
      </div>
    </motion.div>
  );
}

function MetricCell({
  label,
  value,
  tooltip,
}: {
  label: string;
  value: string;
  tooltip: string;
}) {
  return (
    <div className="text-center">
      <div className="flex items-center justify-center gap-0.5">
        <span className="text-[9px] text-gray-400 uppercase tracking-wider">{label}</span>
        <ExplainabilityTooltip content={tooltip} size={10} />
      </div>
      <span className="text-xs font-mono font-semibold text-gray-900 dark:text-white">
        {value}
      </span>
    </div>
  );
}
