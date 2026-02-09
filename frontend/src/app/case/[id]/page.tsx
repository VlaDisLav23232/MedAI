"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { ImageViewer } from "@/components/case/ImageViewer";
import { FindingsPanel } from "@/components/case/FindingsPanel";
import { ReasoningTrace } from "@/components/case/ReasoningTrace";
import { ApprovalBar, type ReportEdits } from "@/components/case/ApprovalBar";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { LoadingAnimation } from "@/components/shared/LoadingAnimation";
import { useReport, useApproveReport, usePatient } from "@/lib/hooks";
import {
  mapApiResponseToAIReport,
  mapApiFinding,
  mapApiReasoningTrace,
  mapApiPatient,
} from "@/lib/api/mappers";
import type { AIReport, Finding, ReasoningStep } from "@/lib/types";
import {
  ArrowLeft,
  Clock,
  User,
  CheckCircle2,
  FileText,
  Stethoscope,
  AlertTriangle,
  ChevronRight,
} from "lucide-react";

export default function CasePage({
  params,
}: {
  params: { id: string };
}) {
  const { id: reportId } = params;
  const [approvalStatus, setApprovalStatus] = useState<
    "pending" | "approved" | "rejected" | "edited"
  >("pending");

  // React Query
  const reportQuery = useReport(reportId);
  const approveReportMutation = useApproveReport();

  // Derive patient ID from the report so we can fetch patient info
  const patientIdFromReport = reportQuery.data?.patient_id;
  const patientQuery = usePatient(patientIdFromReport);

  const loading = reportQuery.isLoading;

  // Map API data → frontend types
  const report: AIReport | null = useMemo(() => {
    if (reportQuery.data) {
      return mapApiResponseToAIReport(reportQuery.data);
    }
    return null;
  }, [reportQuery.data]);

  const findings: Finding[] = useMemo(() => {
    if (reportQuery.data) {
      return reportQuery.data.findings.map(mapApiFinding);
    }
    return [];
  }, [reportQuery.data]);

  const reasoningSteps: ReasoningStep[] = useMemo(() => {
    if (reportQuery.data) {
      return mapApiReasoningTrace(reportQuery.data.reasoning_trace);
    }
    return [];
  }, [reportQuery.data]);

  const patient = useMemo(() => {
    if (patientQuery.data) {
      return mapApiPatient(patientQuery.data);
    }
    return null;
  }, [patientQuery.data]);

  // Sync approval status from API data
  useMemo(() => {
    if (reportQuery.data) {
      setApprovalStatus(reportQuery.data.approval_status as typeof approvalStatus);
    }
  }, [reportQuery.data]);

  // ── Approval handlers (API-backed) ─────────────────────

  const handleApproval = async (
    status: "approved" | "rejected" | "edited",
    notes?: string,
    edits?: Record<string, unknown>
  ) => {
    if (!report) return;
    approveReportMutation.mutate(
      { report_id: report.id, status, doctor_notes: notes, edits },
      {
        onSuccess: () => setApprovalStatus(status),
      }
    );
  };

  const handleEditApprove = (edits: ReportEdits, notes?: string) => {
    handleApproval("edited", notes, edits as Record<string, unknown>);
  };

  // ── Loading ────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark flex items-center justify-center">
        <div className="text-center">
          <LoadingAnimation label="Loading case report…" variant="orbital" />
          <p className="text-xs text-gray-400 mt-3">
            Fetching AI analysis and findings
          </p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle size={40} className="mx-auto mb-3 text-amber-400" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Report not found</h2>
          <p className="text-sm text-gray-500 mt-1">No data available for report &quot;{reportId}&quot;</p>
          <Link href="/agent" className="inline-flex items-center gap-1.5 mt-4 text-sm font-medium text-brand-500 hover:text-brand-600">
            <ArrowLeft size={14} /> Back to Co-Pilot
          </Link>
        </div>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────

  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark">
      {/* ── Top bar ────────────────────────────────── */}
      <header className="sticky top-16 z-30 bg-white/80 dark:bg-surface-dark/80 backdrop-blur-lg border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/agent"
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-2 transition"
                aria-label="Back to co-pilot"
              >
                <ArrowLeft size={18} className="text-gray-400" />
              </Link>
              <div className="h-5 w-px bg-gray-200 dark:bg-gray-700" aria-hidden="true" />
              <div className="flex items-center gap-2">
                <User size={14} className="text-brand-500" aria-hidden="true" />
                <span className="text-sm font-semibold text-gray-900 dark:text-white">
                  {patient?.name ?? "Unknown Patient"}
                </span>
                <span className="text-xs text-gray-400">
                  {patient?.medical_record_number ?? ""}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <Clock size={12} aria-hidden="true" />
                {new Date().toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
              <ConfidenceBadge confidence={report.confidence} />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* ── Diagnosis summary ────────────────────── */}
        <section className="mb-6 p-5 rounded-2xl bg-gradient-to-r from-brand-500/10 via-accent-cyan/5 to-accent-violet/10 border border-brand-200 dark:border-brand-800">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-brand-500/20 flex items-center justify-center flex-shrink-0" aria-hidden="true">
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
                {report.judge_verdict?.status === "consensus" ? (
                  <>
                    <CheckCircle2 size={14} className="text-accent-emerald" />
                    <span className="text-xs font-medium text-accent-emerald">
                      Consensus reached — all modalities aligned
                    </span>
                  </>
                ) : (
                  <>
                    <AlertTriangle size={14} className="text-accent-amber" />
                    <span className="text-xs font-medium text-accent-amber">
                      Conflict detected — review findings carefully
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* ── Split view: Image + Findings ─────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <ImageViewer
            imageUrl={report.explainability.heatmap_url || "/placeholder-scan.svg"}
            heatmapUrl={report.explainability.heatmap_url}
            findings={findings}
          />
          <div className="space-y-6">
            <FindingsPanel
              findings={findings}
              differentialDiagnoses={
                report.specialist_outputs?.image_analysis?.differential_diagnoses
              }
              recommendedFollowup={
                report.specialist_outputs?.image_analysis?.recommended_followup
              }
            />
          </div>
        </div>

        {/* ── Suggested Plan ──────────────────────── */}
        <section className="mb-6 p-5 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800 neo-shadow">
          <h2 className="text-sm font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <FileText size={16} className="text-brand-500" aria-hidden="true" />
            Suggested Plan
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {report.plan.map((item, i) => (
              <div
                key={i}
                className="flex items-start gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-surface-dark-3"
              >
                <span className="w-5 h-5 rounded-full bg-brand-500/10 text-brand-500 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5" aria-hidden="true">
                  {i + 1}
                </span>
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {item}
                </span>
              </div>
            ))}
          </div>

          {!!report.specialist_outputs?.text_reasoning?.contraindication_check && (
            <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-800">
              <CheckCircle2 size={14} className="text-accent-emerald" />
              <span className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                No contraindications flagged
              </span>
            </div>
          )}
        </section>

        {/* ── Reasoning Trace ─────────────────────── */}
        <section className="mb-6">
          <ReasoningTrace steps={reasoningSteps} />
        </section>

        {/* ── Historical Context ──────────────────── */}
        {report.specialist_outputs?.history_search && (
          <section className="mb-6 p-5 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800 neo-shadow">
            <h2 className="text-sm font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
              <Clock size={16} className="text-brand-500" aria-hidden="true" />
              Historical Context
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 italic">
              &ldquo;
              {report.specialist_outputs?.history_search?.timeline_context}
              &rdquo;
            </p>
            <div className="space-y-2">
              {report.specialist_outputs?.history_search?.relevant_records.map(
                (rec, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 px-3 py-2 rounded-lg bg-gray-50 dark:bg-surface-dark-3"
                  >
                    <time
                      dateTime={rec.date}
                      className="text-xs font-mono text-gray-400 whitespace-nowrap mt-0.5"
                    >
                      {rec.date}
                    </time>
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
                href={`/timeline/${patient?.id ?? patientIdFromReport}`}
                className="text-xs text-brand-500 hover:text-brand-600 font-medium inline-flex items-center gap-1"
              >
                View Full Timeline
                <ChevronRight size={12} />
              </Link>
            </div>
          </section>
        )}

        {/* ── Approval Bar ────────────────────────── */}
        <section>
          <ApprovalBar
            status={approvalStatus}
            loading={approveReportMutation.isPending}
            onApprove={(notes) => handleApproval("approved", notes)}
            onReject={(notes) => handleApproval("rejected", notes)}
            onEditApprove={handleEditApprove}
            currentReport={report ? {
              diagnosis: report.diagnosis,
              evidence_summary: report.evidence_summary,
              plan: report.plan,
              timeline_impact: report.timeline_impact,
            } : undefined}
          />
          {approveReportMutation.error && (
            <div className="mt-2 flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-50 dark:bg-rose-900/10 border border-rose-200 dark:border-rose-800">
              <AlertTriangle size={14} className="text-accent-rose flex-shrink-0" />
              <p className="text-xs text-rose-700 dark:text-rose-400">
                {approveReportMutation.error.message}
              </p>
            </div>
          )}
        </section>

        {/* ── Disclaimer ──────────────────────────── */}
        <aside className="mt-6 mb-8 flex items-start gap-2 px-4 py-3 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800" role="note">
          <AlertTriangle size={16} className="text-amber-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-xs text-amber-700 dark:text-amber-400">
            <strong>Disclaimer:</strong> This AI-generated analysis is for
            clinical decision support only. All findings must be independently
            verified by a qualified healthcare professional. Not intended for
            direct patient care without physician review.
          </p>
        </aside>
      </main>
    </div>
  );
}
