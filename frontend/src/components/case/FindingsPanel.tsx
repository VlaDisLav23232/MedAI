"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import type { Finding } from "@/lib/types";
import { Target, ArrowRight } from "lucide-react";

interface FindingsPanelProps {
  findings: Finding[];
  differentialDiagnoses?: string[];
  recommendedFollowup?: string[];
  className?: string;
}

export function FindingsPanel({
  findings,
  differentialDiagnoses,
  recommendedFollowup,
  className,
}: FindingsPanelProps) {
  return (
    <div className={cn("space-y-4", className)} role="region" aria-label="AI findings">
      {/* Findings */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-2">
          <Target size={12} aria-hidden="true" />
          Findings
        </h3>
        <ul className="space-y-3 list-none m-0 p-0" aria-label="Finding list">
          {findings.map((finding, i) => (
            <li
              key={i}
              className="p-4 rounded-xl bg-white dark:bg-surface-dark-2 border border-gray-100 dark:border-gray-800 neo-shadow hover:neo-shadow-lg transition-all duration-200"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <h4 className="text-sm font-bold text-gray-900 dark:text-white">
                  {finding.finding}
                </h4>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <SeverityBadge severity={finding.severity} />
                  <ConfidenceBadge confidence={finding.confidence} size="sm" />
                </div>
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                {finding.explanation}
              </p>
              {finding.region_bbox && (
                <div className="flex items-center gap-1 mt-2 text-[10px] text-accent-cyan font-mono">
                  <span>Region: [{finding.region_bbox.join(", ")}]</span>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      {/* Differential diagnoses */}
      {differentialDiagnoses && differentialDiagnoses.length > 0 && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
            Differential Diagnoses
          </h3>
          <div className="flex flex-wrap gap-2">
            {differentialDiagnoses.map((dx, i) => (
              <span
                key={i}
                className="px-3 py-1.5 rounded-lg bg-accent-violet/10 border border-accent-violet/20 text-accent-violet text-xs font-medium capitalize"
              >
                {dx}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Recommended follow-up */}
      {recommendedFollowup && recommendedFollowup.length > 0 && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
            Recommended Follow-up
          </h3>
          <div className="space-y-1.5">
            {recommendedFollowup.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-50 dark:bg-brand-900/10 border border-brand-200 dark:border-brand-800"
              >
                <ArrowRight size={12} className="text-brand-500 flex-shrink-0" />
                <span className="text-xs text-gray-700 dark:text-gray-300">
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
