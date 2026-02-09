"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import {
  BookOpen,
  FlaskConical,
  Image as ImageIcon,
  History,
  FileCheck,
  ChevronRight,
  ExternalLink,
  X,
} from "lucide-react";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import type { Citation } from "@/lib/types";

type SidebarTab = "citations" | "findings" | "history" | "guidelines";

interface CitationsSidebarProps {
  citations: Citation[];
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

const tabConfig: { id: SidebarTab; label: string; icon: React.ElementType }[] = [
  { id: "citations", label: "Evidence", icon: BookOpen },
  { id: "findings", label: "Findings", icon: FlaskConical },
  { id: "history", label: "History", icon: History },
  { id: "guidelines", label: "Guidelines", icon: FileCheck },
];

function getCitationIcon(type: Citation["type"]) {
  switch (type) {
    case "imaging":
      return ImageIcon;
    case "lab":
      return FlaskConical;
    case "finding":
      return FlaskConical;
    case "history":
      return History;
    case "guideline":
      return FileCheck;
    default:
      return BookOpen;
  }
}

function getCitationColor(type: Citation["type"]) {
  switch (type) {
    case "imaging":
      return "bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20";
    case "lab":
      return "bg-accent-violet/10 text-accent-violet border-accent-violet/20";
    case "finding":
      return "bg-accent-amber/10 text-accent-amber border-accent-amber/20";
    case "history":
      return "bg-brand-500/10 text-brand-500 border-brand-500/20";
    case "guideline":
      return "bg-accent-emerald/10 text-accent-emerald border-accent-emerald/20";
    default:
      return "bg-gray-100 text-gray-600 border-gray-200";
  }
}

export function CitationsSidebar({
  citations,
  isOpen,
  onClose,
  className,
}: CitationsSidebarProps) {
  const [activeTab, setActiveTab] = useState<SidebarTab>("citations");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filteredCitations =
    activeTab === "citations"
      ? citations
      : citations.filter((c) => {
          if (activeTab === "findings") return c.type === "finding" || c.type === "imaging";
          if (activeTab === "history") return c.type === "history" || c.type === "lab";
          if (activeTab === "guidelines") return c.type === "guideline";
          return true;
        });

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-white dark:bg-surface-dark border-r border-gray-200 dark:border-gray-800 transition-all duration-300",
        isOpen ? "w-80 min-w-[320px]" : "w-0 min-w-0 overflow-hidden",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <h3 className="text-sm font-bold text-gray-900 dark:text-white">
          Evidence Panel
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-2 transition"
        >
          <X size={16} className="text-gray-400" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-gray-200 dark:border-gray-800 px-2 pt-2" role="tablist" aria-label="Evidence categories">
        {tabConfig.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            role="tab"
            aria-selected={activeTab === id}
            aria-controls={`panel-${id}`}
            title={label}
            className={cn(
              "flex items-center gap-1.5 flex-1 min-w-0 justify-center px-2 py-2 text-xs font-medium rounded-t-lg transition-all",
              activeTab === id
                ? "bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 border-b-2 border-brand-500"
                : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            )}
          >
            <Icon size={13} className="flex-shrink-0" />
            <span className="truncate">{label}</span>
          </button>
        ))}
      </div>

      {/* Citation list */}
      <div id={`panel-${activeTab}`} role="tabpanel" aria-label={`${activeTab} list`} className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
        {filteredCitations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 dark:text-gray-600">
            <BookOpen size={32} className="mb-2 opacity-50" />
            <p className="text-sm">No evidence available yet</p>
            <p className="text-xs mt-1">Citations will appear here as the agent analyzes data</p>
          </div>
        ) : (
          filteredCitations.map((citation) => {
            const Icon = getCitationIcon(citation.type);
            const colorClass = getCitationColor(citation.type);
            const isExpanded = expandedId === citation.id;

            return (
              <button
                type="button"
                key={citation.id}
                className={cn(
                  "w-full text-left rounded-xl border transition-all duration-200",
                  "bg-white dark:bg-surface-dark-2 border-gray-100 dark:border-gray-800",
                  "hover:border-brand-200 dark:hover:border-brand-800",
                  isExpanded && "ring-1 ring-brand-500/20"
                )}
                onClick={() => setExpandedId(isExpanded ? null : citation.id)}
                aria-expanded={isExpanded}
              >
                <div className="flex items-start gap-3 p-3">
                  <div
                    className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 border",
                      colorClass
                    )}
                  >
                    <Icon size={14} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="text-xs font-semibold text-gray-900 dark:text-white truncate">
                        {citation.title}
                      </h4>
                      <ChevronRight
                        size={14}
                        className={cn(
                          "text-gray-400 transition-transform flex-shrink-0",
                          isExpanded && "rotate-90"
                        )}
                      />
                    </div>
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {(citation as any).date ? (
                      <span className="text-[10px] text-gray-400 dark:text-gray-500">
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {String((citation as any).date)}
                      </span>
                    ) : null}
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-3 pb-3 pt-0 border-t border-gray-100 dark:border-gray-800 mt-0">
                    <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed mt-2">
                      {citation.content}
                    </p>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-[10px] text-gray-400 flex items-center gap-1">
                        <ExternalLink size={10} />
                        {citation.source}
                      </span>
                      {citation.confidence !== undefined && (
                        <ConfidenceBadge
                          confidence={citation.confidence}
                          size="sm"
                          showLabel={false}
                        />
                      )}
                    </div>
                  </div>
                )}
              </button>
            );
          })
        )}
      </div>

      {/* Bottom summary */}
      {filteredCitations.length > 0 && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-surface-dark-2">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{filteredCitations.length} source(s)</span>
            <span className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-accent-emerald" />
              Cross-referenced
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
