"use client";

import React from "react";
import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/lib/types";
import {
  Image,
  FileText,
  AudioLines,
  History,
  Scale,
  FileCheck,
  Route,
  CircleDot,
  AlertCircle,
} from "lucide-react";

const statusConfig: Record<
  AgentStatus,
  { label: string; icon: React.ElementType; color: string }
> = {
  idle: { label: "Ready", icon: CircleDot, color: "text-gray-400" },
  routing: { label: "Routing query…", icon: Route, color: "text-brand-500" },
  analyzing_image: { label: "Analyzing image…", icon: Image, color: "text-accent-cyan" },
  analyzing_text: { label: "Reasoning…", icon: FileText, color: "text-accent-violet" },
  analyzing_audio: { label: "Processing audio…", icon: AudioLines, color: "text-accent-amber" },
  searching_history: { label: "Searching history…", icon: History, color: "text-brand-400" },
  judging: { label: "Consensus check…", icon: Scale, color: "text-accent-emerald" },
  generating_report: { label: "Generating report…", icon: FileCheck, color: "text-brand-500" },
  complete: { label: "Complete", icon: CircleDot, color: "text-accent-emerald" },
  error: { label: "Error", icon: AlertCircle, color: "text-accent-rose" },
};

interface AgentStatusIndicatorProps {
  status: AgentStatus;
  className?: string;
}

export function AgentStatusIndicator({ status, className }: AgentStatusIndicatorProps) {
  const config = statusConfig[status];
  const Icon = config.icon;
  const isActive = !["idle", "complete", "error"].includes(status);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="relative">
        <Icon size={16} className={cn(config.color, isActive && "animate-pulse")} />
        {isActive && (
          <div className="absolute -inset-1 rounded-full bg-brand-500/20 animate-ping" />
        )}
      </div>
      <span className={cn("text-xs font-medium", config.color)}>
        {config.label}
      </span>
    </div>
  );
}
