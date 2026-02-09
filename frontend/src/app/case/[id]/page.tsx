"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { ImageViewer } from "@/components/case/ImageViewer";
import { FindingsPanel } from "@/components/case/FindingsPanel";
import { ConditionScoresChart } from "@/components/case/ConditionScoresChart";
import { ReasoningTrace } from "@/components/case/ReasoningTrace";
import { PipelineMetricsBar } from "@/components/case/PipelineMetricsBar";
import { ApprovalBar, type ReportEdits } from "@/components/case/ApprovalBar";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { LoadingAnimation } from "@/components/shared/LoadingAnimation";
import { ExplainabilityTooltip } from "@/components/shared/ExplainabilityTooltip";
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
  ChevronDown,
  Brain,
  Eye,
  Activity,
  Shield,
  Download,
} from "lucide-react";

/* ══════════════════════════════════════════════════════════════
 *  Case Report Page — Full AI Analysis Report
 * ══════════════════════════════════════════════════════════════ */

export default function CasePage({
  params,
}: {
  params: { id: string };
}) {
  const { id: reportId } = params;
  const [approvalStatus, setApprovalStatus] = useState<
    "pending" | "approved" | "rejected" | "edited"
  >("pending");
  const [selectedConditionLabel, setSelectedConditionLabel] = useState<
    string | undefined
  >();

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
      setApprovalStatus(
        reportQuery.data.approval_status as typeof approvalStatus,
      );
    }
  }, [reportQuery.data]);

  // ── Specialist data shortcuts ──────────────────────────────
  const explainability = report?.specialist_outputs?.image_explainability;
  const imageAnalysis = report?.specialist_outputs?.image_analysis;
  const textReasoning = report?.specialist_outputs?.text_reasoning;
  const historySearch = report?.specialist_outputs?.history_search;
  const conditionScores = explainability?.condition_scores ?? [];

  // ── Plain-text report export ───────────────────────────────
  const exportPlainText = () => {
    if (!report) return;

    const sep = "=".repeat(60);
    const sub = "-".repeat(40);
    const lines: string[] = [];

    const add = (s: string) => lines.push(s);
    const blank = () => lines.push("");

    add(sep);
    add("  MEDAI CLINICAL REPORT");
    add(sep);
    blank();
    add(`Report ID    : ${report.id}`);
    add(`Patient      : ${patient?.name ?? "Unknown"}`);
    add(`MRN          : ${patient?.medical_record_number ?? "—"}`);
    if (patient?.date_of_birth) add(`DOB          : ${patient.date_of_birth}`);
    if (patient?.gender) add(`Gender       : ${patient.gender}`);
    add(`Generated    : ${reportQuery.data?.created_at ? new Date(reportQuery.data.created_at).toLocaleString() : "N/A"}`);
    add(`Exported     : ${new Date().toLocaleString()}`);
    blank();

    add(sep);
    add("  DIAGNOSIS");
    add(sep);
    blank();
    add(`Diagnosis    : ${report.diagnosis}`);
    add(`Confidence   : ${(report.confidence * 100).toFixed(1)}%`);
    if (report.confidence_method) add(`Method       : ${report.confidence_method}`);
    blank();

    add(sub);
    add("  Evidence Summary");
    add(sub);
    add(report.evidence_summary || "N/A");
    blank();

    add(sub);
    add("  Timeline Impact");
    add(sub);
    add(report.timeline_impact || "N/A");
    blank();

    if (report.plan?.length) {
      add(sub);
      add("  Treatment Plan");
      add(sub);
      report.plan.forEach((step, i) => add(`  ${i + 1}. ${step}`));
      blank();
    }

    if (findings.length) {
      add(sep);
      add("  FINDINGS");
      add(sep);
      blank();
      findings.forEach((f, i) => {
        add(`  ${i + 1}. ${f.finding}`);
        add(`     Confidence : ${(f.confidence * 100).toFixed(0)}%`);
        add(`     Severity   : ${f.severity}`);
        if (f.explanation) add(`     Detail     : ${f.explanation}`);
        blank();
      });
    }

    if (conditionScores.length) {
      add(sep);
      add("  CONDITION SCORES (MedSigLIP Zero-Shot)");
      add(sep);
      blank();
      conditionScores.forEach((cs) => {
        add(`  • ${cs.label.padEnd(30)} ${(cs.probability * 100).toFixed(2)}%`);
      });
      blank();
    }

    if (imageAnalysis) {
      add(sep);
      add("  IMAGE ANALYSIS (MedGemma 4B)");
      add(sep);
      blank();
      if (imageAnalysis.modality_detected) add(`Modality          : ${imageAnalysis.modality_detected}`);
      if (imageAnalysis.inference?.model_id) add(`Model             : ${imageAnalysis.inference.model_id}`);
      if (imageAnalysis.inference?.latency_ms) add(`Latency           : ${imageAnalysis.inference.latency_ms}ms`);
      blank();
      if (imageAnalysis.findings?.length) {
        add("Findings:");
        imageAnalysis.findings.forEach((f, i) => {
          add(`  ${i + 1}. ${f.finding} (confidence: ${(f.confidence * 100).toFixed(0)}%, severity: ${f.severity})`);
          if (f.explanation) add(`     ${f.explanation}`);
        });
        blank();
      }
      if (imageAnalysis.differential_diagnoses?.length) {
        add("Differential Diagnoses:");
        imageAnalysis.differential_diagnoses.forEach((d) => add(`  • ${d}`));
        blank();
      }
      if (imageAnalysis.recommended_followup?.length) {
        add("Recommended Follow-up:");
        imageAnalysis.recommended_followup.forEach((r) => add(`  • ${r}`));
        blank();
      }
    }

    if (textReasoning) {
      add(sep);
      add("  TEXT REASONING (MedGemma 27B)");
      add(sep);
      blank();
      if (textReasoning.assessment) {
        add("Assessment:");
        add(textReasoning.assessment);
        blank();
      }
      if (textReasoning.confidence != null) add(`Confidence        : ${(textReasoning.confidence * 100).toFixed(1)}%`);
      if (textReasoning.inference?.model_id) add(`Model             : ${textReasoning.inference.model_id}`);
      blank();
      if (textReasoning.evidence_citations?.length) {
        add("Evidence Citations:");
        textReasoning.evidence_citations.forEach((c) => add(`  • ${c}`));
        blank();
      }
      if (textReasoning.plan_suggestions?.length) {
        add("Plan Suggestions:");
        textReasoning.plan_suggestions.forEach((p) => add(`  • ${p}`));
        blank();
      }
      if (textReasoning.contraindication_flags?.length) {
        add("Contraindication Flags:");
        textReasoning.contraindication_flags.forEach((f) => add(`  ⚠ ${f}`));
        blank();
      }
      if (textReasoning.reasoning_chain?.length) {
        add("Reasoning Chain:");
        textReasoning.reasoning_chain.forEach((s) => {
          add(`  Step ${s.step}: [${s.action}] ${s.thought}`);
          if (s.observation) add(`    → ${s.observation}`);
        });
        blank();
      }
    }

    if (historySearch) {
      add(sep);
      add("  PATIENT HISTORY CONTEXT");
      add(sep);
      blank();
      if (historySearch.timeline_context) {
        add(historySearch.timeline_context);
        blank();
      }
      if (historySearch.relevant_records?.length) {
        add("Relevant Records:");
        historySearch.relevant_records.forEach((r) => {
          add(`  [${r.date}] ${r.summary}`);
          add(`    Relevance: ${r.clinical_relevance} (score: ${r.similarity_score.toFixed(2)})`);
        });
        blank();
      }
    }

    if (reasoningSteps.length) {
      add(sep);
      add("  REASONING TRACE");
      add(sep);
      blank();
      reasoningSteps.forEach((s) => {
        add(`  Step ${s.step}: ${s.action}`);
        if (s.reasoning) add(`    Reasoning  : ${s.reasoning}`);
        if (s.observation) add(`    Observation: ${s.observation}`);
        if (s.tool) add(`    Tool       : ${s.tool}`);
      });
      blank();
    }

    if (report.judge_verdict) {
      add(sep);
      add("  JUDGE VERDICT");
      add(sep);
      blank();
      add(`Status          : ${report.judge_verdict.status.toUpperCase()}`);
      add(`Confidence      : ${(report.judge_verdict.confidence * 100).toFixed(1)}%`);
      add(`Reasoning       : ${report.judge_verdict.reasoning}`);
      blank();
      if (report.judge_verdict.contradictions?.length) {
        add("Contradictions:");
        report.judge_verdict.contradictions.forEach((c) => add(`  ⚠ ${c}`));
        blank();
      }
      if (report.judge_verdict.low_confidence_items?.length) {
        add("Low Confidence Items:");
        report.judge_verdict.low_confidence_items.forEach((i) => add(`  • ${i}`));
        blank();
      }
      if (report.judge_verdict.missing_context?.length) {
        add("Missing Context:");
        report.judge_verdict.missing_context.forEach((m) => add(`  ? ${m}`));
        blank();
      }
    }

    if (report.pipeline_metrics) {
      const pm = report.pipeline_metrics;
      add(sep);
      add("  PIPELINE METRICS");
      add(sep);
      blank();
      add(`Total time      : ${pm.total_s.toFixed(1)}s`);
      add(`Tools phase     : ${pm.tools_s.toFixed(1)}s`);
      add(`Judge phase     : ${pm.judge_s.toFixed(1)}s`);
      add(`Report phase    : ${pm.report_s.toFixed(1)}s`);
      if (pm.tools_called?.length) add(`Tools called    : ${pm.tools_called.join(", ")}`);
      if (pm.tools_failed?.length) add(`Tools failed    : ${pm.tools_failed.join(", ")}`);
      add(`Requery cycles  : ${pm.requery_cycles}`);
      blank();
      if (pm.tool_timings && Object.keys(pm.tool_timings).length) {
        add("Tool Timings:");
        Object.entries(pm.tool_timings).forEach(([tool, time]) => {
          add(`  ${tool.padEnd(25)} ${Number(time).toFixed(2)}s`);
        });
        blank();
      }
    }

    add(sep);
    add("  DISCLAIMER");
    add(sep);
    blank();
    add("This report was generated by an AI system and is intended for");
    add("informational purposes only. It does NOT constitute medical advice,");
    add("diagnosis, or treatment recommendation. A qualified healthcare");
    add("professional must review and validate all findings before any");
    add("clinical decision is made.");
    blank();
    add(sep);
    add("  END OF REPORT");
    add(sep);

    // Download as .txt file
    const text = lines.join("\n");
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `MedAI_Report_${report.id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // ── Approval handlers (API-backed) ─────────────────────

  const handleApproval = async (
    status: "approved" | "rejected" | "edited",
    notes?: string,
    edits?: Record<string, unknown>,
  ) => {
    if (!report) return;
    approveReportMutation.mutate(
      { report_id: report.id, status, doctor_notes: notes, edits },
      {
        onSuccess: () => setApprovalStatus(status),
      },
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
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            Report not found
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            No data available for report &quot;{reportId}&quot;
          </p>
          <Link
            href="/agent"
            className="inline-flex items-center gap-1.5 mt-4 text-sm font-medium text-brand-500 hover:text-brand-600"
          >
            <ArrowLeft size={14} /> Back to Co-Pilot
          </Link>
        </div>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────

  return (
    <div className="min-h-screen pt-16 bg-gray-50 dark:bg-surface-dark">
      {/* ══ Top bar ═══════════════════════════════════════ */}
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
              <div
                className="h-5 w-px bg-gray-200 dark:bg-gray-700"
                aria-hidden="true"
              />
              <div className="flex items-center gap-2">
                <User
                  size={14}
                  className="text-brand-500"
                  aria-hidden="true"
                />
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
              <button
                onClick={exportPlainText}
                className="print:hidden flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-surface-dark-3 hover:bg-gray-200 dark:hover:bg-surface-dark transition"
                title="Export report as plain text"
              >
                <Download size={14} />
                Export TXT
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* ══ Print-only header ═══════════════════════════ */}
        <div className="hidden print:block mb-6 pb-4 border-b-2 border-gray-300">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold">MedAI Clinical Report</h1>
              <p className="text-sm text-gray-600 mt-1">
                Patient: {patient?.name ?? "Unknown"} · MRN: {patient?.medical_record_number ?? "—"} · Report: {report.id}
              </p>
            </div>
            <div className="text-right text-xs text-gray-500">
              <p>Generated: {new Date(reportQuery.data?.created_at ?? "").toLocaleString()}</p>
              <p>Printed: {new Date().toLocaleString()}</p>
            </div>
          </div>
        </div>
        {/* ══ 1. Diagnosis Summary ════════════════════════ */}
        <section className="p-5 rounded-2xl bg-gradient-to-r from-brand-500/10 via-accent-cyan/5 to-accent-violet/10 border border-brand-200 dark:border-brand-800">
          <div className="flex items-start gap-4">
            <div
              className="w-12 h-12 rounded-xl bg-brand-500/20 flex items-center justify-center flex-shrink-0"
              aria-hidden="true"
            >
              <Stethoscope size={24} className="text-brand-500" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-lg font-bold text-gray-900 dark:text-white">
                  {report.diagnosis}
                </h1>
                <ConfidenceBadge confidence={report.confidence} />
                <ExplainabilityTooltip
                  content={`Confidence (${report.confidence_method?.replace(/_/g, " ") || "model-reported"})`}
                  detail="Overall confidence in the diagnosis. Computed as a weighted average of individual tool confidences, validated by the Judge module."
                  size={12}
                />
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {report.evidence_summary}
              </p>
              {/* Judge verdict */}
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
                <ExplainabilityTooltip
                  content="Multi-modal consensus check"
                  detail="The Judge module compares outputs from all specialist tools (image analysis, text reasoning, etc.) to verify they agree. Conflicts require careful review."
                  size={11}
                  position="right"
                />
              </div>
            </div>
          </div>
        </section>

        {/* ══ 2. Image Explainability Section ═════════════ */}
        {(conditionScores.length > 0 ||
          explainability?.attention_heatmap_url) && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Eye size={16} className="text-brand-500" aria-hidden="true" />
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">
                Image Explainability
              </h2>
              <ExplainabilityTooltip
                content="MedSigLIP vision analysis"
                detail="Zero-shot contrastive image classification using a medical vision-language model. Each condition is evaluated independently, and GradCAM attention maps show model focus areas."
              />
              {explainability?.modality_detected && (
                <span className="ml-auto px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-[10px] font-medium text-gray-500">
                  {explainability.modality_detected}
                </span>
              )}
              {explainability?.inference?.model_id && (
                <span className="px-2 py-0.5 rounded-md bg-brand-500/10 text-[10px] font-medium text-brand-500">
                  {explainability.inference.model_id}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Image Viewer — 3 cols */}
              <div className="lg:col-span-3">
                <ImageViewer
                  originalImageUrl={report.original_image_url}
                  conditionScores={conditionScores}
                  selectedLabel={selectedConditionLabel}
                  onSelectLabel={setSelectedConditionLabel}
                />
              </div>

              {/* Condition Scores Chart — 2 cols */}
              <div className="lg:col-span-2 space-y-4">
                <div className="p-4 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800 neo-shadow">
                  <ConditionScoresChart
                    scores={conditionScores}
                    selectedLabel={selectedConditionLabel}
                    onSelect={setSelectedConditionLabel}
                    maxVisible={8}
                  />
                </div>

                {/* Image analysis modality + top prediction callout */}
                {conditionScores.length > 0 && (
                  <TopPredictionCard
                    scores={conditionScores}
                    modality={explainability?.modality_detected}
                  />
                )}
              </div>
            </div>
          </section>
        )}

        {/* ══ 3. Findings + Follow-up ═════════════════════ */}
        {(findings.length > 0 ||
          (imageAnalysis?.differential_diagnoses?.length ?? 0) > 0) && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Activity
                size={16}
                className="text-brand-500"
                aria-hidden="true"
              />
              <h2 className="text-sm font-bold text-gray-900 dark:text-white">
                Clinical Findings
              </h2>
              <ExplainabilityTooltip
                content="Structured findings from AI analysis"
                detail="Individual clinical observations extracted by the image analysis model (MedGemma 4B), each with severity levels and confidence scores."
              />
            </div>
            <FindingsPanel
              findings={findings}
              differentialDiagnoses={imageAnalysis?.differential_diagnoses}
              recommendedFollowup={imageAnalysis?.recommended_followup}
            />
          </section>
        )}

        {/* ══ 4. Suggested Plan ═══════════════════════════ */}
        <section className="p-5 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800 neo-shadow">
          <div className="flex items-center gap-2 mb-3">
            <FileText
              size={16}
              className="text-brand-500"
              aria-hidden="true"
            />
            <h2 className="text-sm font-bold text-gray-900 dark:text-white">
              Suggested Plan
            </h2>
            <ExplainabilityTooltip
              content="AI-generated treatment plan"
              detail="A suggested plan based on the diagnosis, evidence, and clinical guidelines. Must be reviewed and approved by the attending physician."
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {report.plan.map((item, i) => (
              <div
                key={i}
                className="flex items-start gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-surface-dark-3"
              >
                <span
                  className="w-5 h-5 rounded-full bg-brand-500/10 text-brand-500 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5"
                  aria-hidden="true"
                >
                  {i + 1}
                </span>
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {item}
                </span>
              </div>
            ))}
          </div>

          {/* Contraindication check */}
          {textReasoning?.contraindication_flags &&
            textReasoning.contraindication_flags.length > 0 && (
              <div className="mt-3 space-y-1">
                {textReasoning.contraindication_flags.map((flag, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800"
                  >
                    <AlertTriangle
                      size={14}
                      className="text-amber-500 flex-shrink-0"
                    />
                    <span className="text-xs text-amber-700 dark:text-amber-400 font-medium">
                      {flag}
                    </span>
                  </div>
                ))}
              </div>
            )}
          {textReasoning &&
            (!textReasoning.contraindication_flags ||
              textReasoning.contraindication_flags.length === 0) && (
              <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-800">
                <CheckCircle2 size={14} className="text-accent-emerald" />
                <span className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                  No contraindications flagged
                </span>
              </div>
            )}
        </section>

        {/* ══ 5. Reasoning Trace ══════════════════════════ */}
        <CollapsibleSection
          icon={Brain}
          title="AI Reasoning Trace"
          tooltip="Step-by-step AI reasoning"
          tooltipDetail="Shows each reasoning step the orchestrator took, including which tools were invoked, observations made, and how conclusions were reached. Provides full transparency into the AI decision process."
        >
          <ReasoningTrace steps={reasoningSteps} />
        </CollapsibleSection>

        {/* ══ 6. Judge Verdict Detail ════════════════════ */}
        {report.judge_verdict && (
          <CollapsibleSection
            icon={Shield}
            title="Judge Verdict"
            tooltip="Automated cross-validation"
            tooltipDetail="The Judge module reviews all specialist outputs for consistency. It identifies contradictions, low-confidence items, and missing context to inform clinical decision-making."
            defaultOpen={report.judge_verdict.status !== "consensus"}
            badge={
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  report.judge_verdict.status === "consensus"
                    ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400"
                    : "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                }`}
              >
                {report.judge_verdict.status}
              </span>
            }
          >
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              {report.judge_verdict.reasoning}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {report.judge_verdict.contradictions &&
                report.judge_verdict.contradictions.length > 0 && (
                  <VerdictList
                    title="Contradictions"
                    items={report.judge_verdict.contradictions}
                    color="rose"
                  />
                )}
              {report.judge_verdict.low_confidence_items &&
                report.judge_verdict.low_confidence_items.length > 0 && (
                  <VerdictList
                    title="Low Confidence"
                    items={report.judge_verdict.low_confidence_items}
                    color="amber"
                  />
                )}
              {report.judge_verdict.missing_context &&
                report.judge_verdict.missing_context.length > 0 && (
                  <VerdictList
                    title="Missing Context"
                    items={report.judge_verdict.missing_context}
                    color="sky"
                  />
                )}
            </div>
          </CollapsibleSection>
        )}

        {/* ══ 7. Pipeline Performance ════════════════════ */}
        {report.pipeline_metrics && (
          <div className="print:hidden">
            <CollapsibleSection
              icon={Activity}
              title="Pipeline Performance"
              tooltip="Execution timing"
              tooltipDetail="Breakdown of how long each phase of the analysis pipeline took. Useful for understanding system performance and bottlenecks."
            >
              <PipelineMetricsBar metrics={report.pipeline_metrics} />
            </CollapsibleSection>
          </div>
        )}

        {/* ══ 8. Historical Context ══════════════════════ */}
        {historySearch && (
          <CollapsibleSection
            icon={Clock}
            title="Historical Context"
            tooltip="Patient history embeddings search"
            tooltipDetail="Semantic search through the patient's medical history using vector embeddings. Finds the most relevant prior records to contextualize the current diagnosis."
            defaultOpen
          >
            {historySearch.timeline_context && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 italic">
                &ldquo;{historySearch.timeline_context}&rdquo;
              </p>
            )}
            <div className="space-y-2">
              {historySearch.relevant_records.map((rec, i) => (
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
              ))}
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
          </CollapsibleSection>
        )}

        {/* ══ 9. Approval Bar ════════════════════════════ */}
        <section className="print:hidden">
          <ApprovalBar
            status={approvalStatus}
            loading={approveReportMutation.isPending}
            onApprove={(notes) => handleApproval("approved", notes)}
            onReject={(notes) => handleApproval("rejected", notes)}
            onEditApprove={handleEditApprove}
            onRevise={() => setApprovalStatus("pending")}
            currentReport={
              report
                ? {
                    diagnosis: report.diagnosis,
                    evidence_summary: report.evidence_summary,
                    plan: report.plan,
                    timeline_impact: report.timeline_impact,
                  }
                : undefined
            }
          />
          {approveReportMutation.error && (
            <div className="mt-2 flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-50 dark:bg-rose-900/10 border border-rose-200 dark:border-rose-800">
              <AlertTriangle
                size={14}
                className="text-accent-rose flex-shrink-0"
              />
              <p className="text-xs text-rose-700 dark:text-rose-400">
                {approveReportMutation.error.message}
              </p>
            </div>
          )}
        </section>

        {/* ══ 10. Disclaimer ════════════════════════════= */}
        <aside
          className="mb-8 flex items-start gap-2 px-4 py-3 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800"
          role="note"
        >
          <AlertTriangle
            size={16}
            className="text-amber-500 flex-shrink-0 mt-0.5"
            aria-hidden="true"
          />
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

/* ══════════════════════════════════════════════════════════════
 *  Sub-components
 * ══════════════════════════════════════════════════════════════ */

/** Collapsible section wrapper with expand/collapse state */
function CollapsibleSection({
  icon: Icon,
  title,
  tooltip,
  tooltipDetail,
  defaultOpen = false,
  badge,
  children,
}: {
  icon: React.ElementType;
  title: string;
  tooltip?: string;
  tooltipDetail?: string;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800 neo-shadow overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-surface-dark-3 transition-colors"
        aria-expanded={open}
      >
        <Icon size={16} className="text-brand-500 flex-shrink-0" aria-hidden="true" />
        <h2 className="text-sm font-bold text-gray-900 dark:text-white flex-1">
          {title}
        </h2>
        {tooltip && (
          <ExplainabilityTooltip content={tooltip} detail={tooltipDetail ?? ""} />
        )}
        {badge}
        <ChevronDown
          size={16}
          className={`text-gray-400 transition-transform duration-200 ${open ? "rotate-0" : "-rotate-90"}`}
        />
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </section>
  );
}

/** Top prediction callout card */
function TopPredictionCard({
  scores,
  modality,
}: {
  scores: Array<{ label: string; probability: number }>;
  modality?: string;
}) {
  const sorted = [...scores].sort((a, b) => b.probability - a.probability);
  const top = sorted[0];
  if (!top) return null;

  const isHighConfidence = top.probability >= 0.3;

  return (
    <div className="p-4 rounded-2xl bg-white dark:bg-surface-dark-2 border border-gray-200 dark:border-gray-800 neo-shadow">
      <div className="flex items-center gap-2 mb-2">
        <div
          className={`w-3 h-3 rounded-full ${isHighConfidence ? "bg-rose-500" : "bg-sky-500"}`}
        />
        <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
          Top Prediction
        </span>
        <ExplainabilityTooltip
          content="Highest-probability condition"
          detail="The condition with the highest softmax probability from the MedSigLIP zero-shot classification. This does not constitute a diagnosis — it indicates what the vision model considers most likely."
          size={10}
        />
      </div>
      <p className="text-base font-bold text-gray-900 dark:text-white capitalize">
        {top.label}
      </p>
      <div className="flex items-center gap-2 mt-1">
        <div className="flex-1 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${isHighConfidence ? "bg-rose-500" : "bg-sky-500"}`}
            style={{ width: `${top.probability * 100}%` }}
          />
        </div>
        <span
          className={`text-sm font-mono font-bold ${isHighConfidence ? "text-rose-500" : "text-sky-500"}`}
        >
          {(top.probability * 100).toFixed(1)}%
        </span>
      </div>
      {modality && (
        <p className="text-[10px] text-gray-400 mt-2">
          Modality: {modality}
        </p>
      )}
      {sorted.length > 1 && (
        <p className="text-[10px] text-gray-400 mt-0.5">
          Runner-up: {sorted[1].label} ({(sorted[1].probability * 100).toFixed(1)}%)
        </p>
      )}
    </div>
  );
}

/** Judge verdict sub-list */
function VerdictList({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color: "rose" | "amber" | "sky";
}) {
  const colorMap = {
    rose: "bg-rose-50 dark:bg-rose-900/10 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-400",
    amber:
      "bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400",
    sky: "bg-sky-50 dark:bg-sky-900/10 border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-400",
  };

  return (
    <div
      className={`px-3 py-2 rounded-lg border ${colorMap[color]}`}
    >
      <p className="text-[10px] font-bold uppercase tracking-wider mb-1 opacity-70">
        {title}
      </p>
      <ul className="space-y-0.5">
        {items.map((item, i) => (
          <li key={i} className="text-xs">
            • {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
