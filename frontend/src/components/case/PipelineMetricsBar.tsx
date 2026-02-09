"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { ExplainabilityTooltip } from "@/components/shared/ExplainabilityTooltip";
import type { PipelineMetrics } from "@/lib/types";
import { Timer, Cpu, AlertTriangle } from "lucide-react";

/* ──────────────────────────────────────────────────────────────
 *  PipelineMetricsBar — subtle timing breakdown of the AI pipeline
 * ────────────────────────────────────────────────────────────── */

interface PipelineMetricsBarProps {
  metrics: PipelineMetrics;
  className?: string;
}

export function PipelineMetricsBar({ metrics, className }: PipelineMetricsBarProps) {
  const total = metrics.total_s;
  if (!total || total <= 0) return null;

  // Build stacked segments from tool_timings
  const segments = Object.entries(metrics.tool_timings)
    .map(([tool, seconds]) => ({
      tool: formatToolName(tool),
      seconds,
      pct: (seconds / total) * 100,
    }))
    .sort((a, b) => b.seconds - a.seconds);

  // Add judge time as a segment if it exists
  if (metrics.judge_s > 0) {
    segments.push({
      tool: "Judge",
      seconds: metrics.judge_s,
      pct: (metrics.judge_s / total) * 100,
    });
  }

  const colors = [
    "bg-brand-500",
    "bg-accent-cyan",
    "bg-accent-violet",
    "bg-accent-emerald",
    "bg-amber-500",
    "bg-rose-400",
    "bg-indigo-400",
  ];

  return (
    <div
      className={cn(
        "p-4 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Timer size={14} className="text-gray-400" aria-hidden="true" />
        <h3 className="text-xs font-bold text-gray-900 dark:text-white">
          Pipeline Performance
        </h3>
        <ExplainabilityTooltip
          content="AI pipeline execution metrics"
          detail="Shows how long each specialist tool took to process this case. Total includes orchestration overhead."
        />
        <span className="ml-auto text-xs font-mono text-gray-500">
          {total.toFixed(1)}s total
        </span>
      </div>

      {/* Stacked bar */}
      <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden flex">
        {segments.map((seg, i) => (
          <div
            key={seg.tool}
            className={cn("h-full transition-all", colors[i % colors.length])}
            style={{ width: `${Math.max(seg.pct, 1)}%` }}
            title={`${seg.tool}: ${seg.seconds.toFixed(1)}s (${seg.pct.toFixed(0)}%)`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
        {segments.map((seg, i) => (
          <div key={seg.tool} className="flex items-center gap-1.5">
            <div
              className={cn("w-2 h-2 rounded-full", colors[i % colors.length])}
              aria-hidden="true"
            />
            <span className="text-[10px] text-gray-500">{seg.tool}</span>
            <span className="text-[10px] font-mono text-gray-400">
              {seg.seconds.toFixed(1)}s
            </span>
          </div>
        ))}
      </div>

      {/* Status badges */}
      <div className="flex items-center gap-3 mt-2">
        <div className="flex items-center gap-1">
          <Cpu size={10} className="text-gray-400" />
          <span className="text-[10px] text-gray-400">
            {metrics.tools_called.length} tools called
          </span>
        </div>
        {metrics.tools_failed.length > 0 && (
          <div className="flex items-center gap-1">
            <AlertTriangle size={10} className="text-amber-400" />
            <span className="text-[10px] text-amber-500">
              {metrics.tools_failed.length} failed
            </span>
          </div>
        )}
        {metrics.requery_cycles > 0 && (
          <span className="text-[10px] text-gray-400">
            {metrics.requery_cycles} requery cycle{metrics.requery_cycles > 1 ? "s" : ""}
          </span>
        )}
      </div>
    </div>
  );
}

function formatToolName(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
