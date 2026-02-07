"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ImageViewer } from "@/components/case/ImageViewer";
import { FindingsPanel } from "@/components/case/FindingsPanel";
import { ReasoningTrace } from "@/components/case/ReasoningTrace";
import { ApprovalBar } from "@/components/case/ApprovalBar";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import {
  mockReport,
  mockFindings,
  mockReasoningSteps,
  mockPatient,
} from "@/lib/mock-data";
import {
  ArrowLeft,
  Clock,
  User,
  CheckCircle2,
  FileText,
  Stethoscope,
  AlertTriangle,
} from "lucide-react";

export default function CasePage() {
  const [approvalStatus, setApprovalStatus] = useState<
    "pending" | "approved" | "rejected" | "edited"
  >("pending");

  const report = mockReport;

  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark">
      {/* Sticky header */}
      <div className="sticky top-16 z-30 bg-white/80 dark:bg-surface-dark/80 backdrop-blur-lg border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/agent"
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-2 transition"
              >
                <ArrowLeft size={18} className="text-gray-400" />
              </Link>
              <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" />
              <div className="flex items-center gap-2">
                <User size={14} className="text-brand-500" />
                <span className="text-sm font-semibold text-gray-900 dark:text-white">
                  {mockPatient.name}
                </span>
                <span className="text-xs text-gray-400">
                  {mockPatient.medical_record_number}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <Clock size={12} />
                Feb 7, 2026
              </span>
              <ConfidenceBadge confidence={report.confidence} />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Diagnosis banner */}
        <div className="mb-6 p-5 rounded-2xl bg-gradient-to-r from-brand-500/10 via-accent-cyan/5 to-accent-violet/10 border border-brand-200 dark:border-brand-800">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-brand-500/20 flex items-center justify-center flex-shrink-0">
              <Stethoscope size={24} className="text-brand-500" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-lg font-bold text-gray-900 dark:text-white">
                  {report.diagnosis}
                </h1>
                <ConfidenceBadge confidence={report.confidence} />
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {report.evidence_summary}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <CheckCircle2 size={14} className="text-accent-emerald" />
                <span className="text-xs font-medium text-accent-emerald">
                  Consensus reached — all modalities aligned
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Main content: Split view */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Left: Image viewer */}
          <ImageViewer
            imageUrl="/mock/cxr.png"
            findings={mockFindings}
          />

          {/* Right: Findings */}
          <div className="space-y-6">
            <FindingsPanel
              findings={mockFindings}
              differentialDiagnoses={
                report.specialist_outputs.image_analysis?.differential_diagnoses
              }
              recommendedFollowup={
                report.specialist_outputs.image_analysis?.recommended_followup
              }
            />
          </div>
        </div>

        {/* Treatment plan */}
        <div className="mb-6 p-5 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800 neo-shadow">
          <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <FileText size={16} className="text-brand-500" />
            Suggested Plan
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {report.plan.map((item, i) => (
              <div
                key={i}
                className="flex items-start gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-surface-dark-3"
              >
                <span className="w-5 h-5 rounded-full bg-brand-500/10 text-brand-500 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {item}
                </span>
              </div>
            ))}
          </div>

          {/* Contraindication check */}
          {report.specialist_outputs.text_reasoning?.contraindication_check && (
            <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-800">
              <CheckCircle2 size={14} className="text-accent-emerald" />
              <span className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                No contraindications flagged
              </span>
            </div>
          )}
        </div>

        {/* Reasoning trace */}
        <div className="mb-6">
          <ReasoningTrace steps={mockReasoningSteps} />
        </div>

        {/* Timeline context */}
        {report.specialist_outputs.history_search && (
          <div className="mb-6 p-5 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800 neo-shadow">
            <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
              <Clock size={16} className="text-brand-500" />
              Historical Context
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 italic">
              &ldquo;{report.specialist_outputs.history_search.timeline_context}&rdquo;
            </p>
            <div className="space-y-2">
              {report.specialist_outputs.history_search.relevant_records.map(
                (rec, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 px-3 py-2 rounded-lg bg-gray-50 dark:bg-surface-dark-3"
                  >
                    <span className="text-xs font-mono text-gray-400 whitespace-nowrap mt-0.5">
                      {rec.date}
                    </span>
                    <div className="flex-1">
                      <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                        {rec.summary}
                      </span>
                      <p className="text-[10px] text-gray-500 mt-0.5">
                        {rec.clinical_relevance}
                      </p>
                    </div>
                    <span className="text-[10px] text-gray-400 font-mono">
                      {(rec.similarity_score * 100).toFixed(0)}% match
                    </span>
                  </div>
                )
              )}
            </div>
            <div className="mt-3 text-right">
              <Link
                href={`/timeline/${mockPatient.id}`}
                className="text-xs text-brand-500 hover:text-brand-600 font-medium"
              >
                View Full Timeline →
              </Link>
            </div>
          </div>
        )}

        {/* Approval bar */}
        <ApprovalBar
          status={approvalStatus}
          onApprove={() => setApprovalStatus("approved")}
          onReject={() => setApprovalStatus("rejected")}
          onEdit={() => setApprovalStatus("edited")}
        />

        {/* Disclaimer */}
        <div className="mt-6 mb-8 flex items-start gap-2 px-4 py-3 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
          <AlertTriangle size={16} className="text-amber-500 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-700 dark:text-amber-400">
            <strong>Disclaimer:</strong> This AI-generated analysis is for
            clinical decision support only. All findings must be independently
            verified by a qualified healthcare professional. Not intended for
            direct patient care without physician review.
          </p>
        </div>
      </div>
    </div>
  );
}
