"use client";

import React from "react";
import { cn } from "@/lib/utils";
import type { ToolResult } from "@/lib/types";
import {
  Image as ImageIcon,
  FileText,
  AudioLines,
  History,
  Scale,
  CheckCircle2,
  Loader2,
  AlertCircle,
} from "lucide-react";

interface ToolProgressProps {
  toolResults: ToolResult[];
  className?: string;
}

const toolIcons: Record<string, React.ElementType> = {
  "Image Analysis": ImageIcon,
  "Text Reasoning": FileText,
  "Audio Analysis": AudioLines,
  "History Search": History,
  "Judge": Scale,
};

function getToolIcon(toolName: string) {
  for (const [key, Icon] of Object.entries(toolIcons)) {
    if (toolName.toLowerCase().includes(key.toLowerCase())) return Icon;
  }
  return FileText;
}

export function ToolProgress({ toolResults, className }: ToolProgressProps) {
  if (toolResults.length === 0) return null;

  return (
    <div
      className={cn(
        "flex flex-col gap-2 p-4 rounded-xl bg-gray-50/50 dark:bg-surface-dark-2/50 border border-gray-100 dark:border-gray-800",
        className
      )}
    >
      <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">
        Agent Pipeline
      </span>
      <div className="space-y-1.5">
        {toolResults.map((result, i) => {
          const Icon = getToolIcon(result.tool);
          const statusIcon = {
            running: <Loader2 size={14} className="animate-spin text-brand-500" />,
            complete: <CheckCircle2 size={14} className="text-accent-emerald" />,
            error: <AlertCircle size={14} className="text-accent-rose" />,
          }[result.status];

          return (
            <div
              key={i}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-all",
                result.status === "running" && "bg-brand-50 dark:bg-brand-900/10 border border-brand-200 dark:border-brand-800",
                result.status === "complete" && "bg-white dark:bg-surface-dark-2 border border-gray-100 dark:border-gray-800",
                result.status === "error" && "bg-rose-50 dark:bg-rose-900/10 border border-rose-200 dark:border-rose-800"
              )}
            >
              <Icon size={14} className="text-gray-400" />
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 flex-1">
                {result.tool}
              </span>
              {result.duration_ms && (
                <span className="text-[10px] text-gray-400 font-mono">
                  {(result.duration_ms / 1000).toFixed(1)}s
                </span>
              )}
              {statusIcon}
            </div>
          );
        })}
      </div>
    </div>
  );
}
