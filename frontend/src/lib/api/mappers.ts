/* ──────────────────────────────────────────────────────────────
 *  Mappers — convert raw API responses to frontend types
 * ────────────────────────────────────────────────────────────── */

import type { ApiPatientSummary, ApiCaseAnalysisResponse, ApiFinding, ApiTimelineEvent } from "./types";
import type { Patient, AIReport, Finding, ReasoningStep, TimelineEvent } from "@/lib/types";

/** Map backend PatientSummary → frontend Patient */
export function mapApiPatient(p: ApiPatientSummary): Patient {
  return {
    id: p.id,
    name: p.name,
    medical_record_number: p.medical_record_number ?? "",
    date_of_birth: p.date_of_birth,
    gender: p.gender,
    created_at: p.created_at,
  };
}

/** Map backend TimelineEventResponse → frontend TimelineEvent */
export function mapApiTimelineEvent(e: ApiTimelineEvent): TimelineEvent {
  return {
    id: e.id,
    patient_id: "",
    date: e.date,
    event_type: e.event_type as TimelineEvent["event_type"],
    summary: e.summary,
    source_type: e.source_type,
    source_id: e.source_id ?? (e.metadata?.source_id as string) ?? e.id,
    metadata: e.metadata,
  };
}

/** Strip JSON / code-block artifacts from AI-generated text. */
function cleanJsonArtifacts(text: string): string {
  if (!text) return text;
  let cleaned = text;

  // 1. Remove fenced code blocks with optional language tag (```json ... ``` or ``` ... ```)
  cleaned = cleaned.replace(/```[\w]*\s*\n?[\s\S]*?```/g, "");

  // 2. Remove standalone JSON objects (with known AI keys) even outside code fences
  cleaned = cleaned.replace(
    /\{[\s\S]*?"(?:reasoning_chain|evidence_citations|plan_suggestions|contraindication_flags|tool_timings|diagnosis|confidence|assessment|findings|timeline_context|specialist_outputs)"[\s\S]*?\}/g,
    ""
  );

  // 3. Remove JSON arrays that look like reasoning chains
  cleaned = cleaned.replace(
    /\[[\s\S]*?\{[\s\S]*?"(?:step|thought|action|observation)"[\s\S]*?\}[\s\S]*?\]/g,
    ""
  );

  // 4. Remove leftover empty code fences
  cleaned = cleaned.replace(/```\s*```/g, "");

  // 5. Remove orphaned "Historical:" prefix followed by date + raw AI dump
  cleaned = cleaned.replace(
    /Historical:.*?\[\d{4}-\d{2}-\d{2}[^\]]*?\]\s*AI Analysis:\s*/gi,
    "Historical context considered. "
  );

  // 6. Clean up excessive whitespace
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");
  cleaned = cleaned.replace(/\s{2,}/g, " ");

  return cleaned.trim();
}

/** Map backend CaseAnalysisResponse → frontend AIReport */
export function mapApiResponseToAIReport(r: ApiCaseAnalysisResponse): AIReport {
  // ── Extract rich specialist outputs ────────────────────────
  const rawOutputs = r.specialist_outputs ?? {};

  const imageExplainability = rawOutputs.image_explainability
    ? {
        tool: String(rawOutputs.image_explainability.tool ?? "image_explainability"),
        modality_detected: rawOutputs.image_explainability.modality_detected as string | undefined,
        condition_scores: Array.isArray(rawOutputs.image_explainability.condition_scores)
          ? (rawOutputs.image_explainability.condition_scores as Array<Record<string, unknown>>)
              .map((cs) => ({
                label: String(cs.label ?? ""),
                probability: Number(cs.probability ?? 0),
                sigmoid_score: cs.sigmoid_score != null ? Number(cs.sigmoid_score) : undefined,
                raw_logit: cs.raw_logit != null ? Number(cs.raw_logit) : undefined,
                heatmap_data_uri: cs.heatmap_data_uri as string | undefined,
              }))
              .filter((cs) => cs.probability >= 0.001) // Filter out near-zero scores
          : [],
        attention_heatmap_url: rawOutputs.image_explainability.attention_heatmap_url as string | undefined,
        inference: rawOutputs.image_explainability.inference as { model_id?: string; latency_ms?: number } | undefined,
      }
    : undefined;

  const imageAnalysis = rawOutputs.image_analysis
    ? {
        tool: String(rawOutputs.image_analysis.tool ?? "image_analysis"),
        modality_detected: rawOutputs.image_analysis.modality_detected as string | undefined,
        findings: Array.isArray(rawOutputs.image_analysis.findings)
          ? (rawOutputs.image_analysis.findings as Array<Record<string, unknown>>).map(
              (f) => ({
                finding: String(f.finding ?? ""),
                confidence: Number(f.confidence ?? 0),
                explanation: String(f.explanation ?? ""),
                severity: String(f.severity ?? "low"),
                region_bbox: f.region_bbox as number[] | undefined,
              })
            )
          : [],
        differential_diagnoses: (rawOutputs.image_analysis.differential_diagnoses as string[]) ?? [],
        recommended_followup: (rawOutputs.image_analysis.recommended_followup as string[]) ?? [],
        attention_heatmap_url: rawOutputs.image_analysis.attention_heatmap_url as string | undefined,
        inference: rawOutputs.image_analysis.inference as { model_id?: string; latency_ms?: number } | undefined,
      }
    : undefined;

  const textReasoning = rawOutputs.text_reasoning
    ? {
        tool: String(rawOutputs.text_reasoning.tool ?? "text_reasoning"),
        assessment: rawOutputs.text_reasoning.assessment as string | undefined,
        confidence: rawOutputs.text_reasoning.confidence as number | undefined,
        reasoning_chain: rawOutputs.text_reasoning.reasoning_chain as Array<{
          step: number; thought: string; action: string; observation: string;
        }> | undefined,
        evidence_citations: (rawOutputs.text_reasoning.evidence_citations as string[]) ?? [],
        plan_suggestions: (rawOutputs.text_reasoning.plan_suggestions as string[]) ?? [],
        contraindication_flags: (rawOutputs.text_reasoning.contraindication_flags as string[]) ?? [],
        inference: rawOutputs.text_reasoning.inference as { model_id?: string; latency_ms?: number } | undefined,
      }
    : undefined;

  const historySearch = rawOutputs.history_search
    ? {
        tool: String(rawOutputs.history_search.tool ?? "history_search"),
        timeline_context: cleanJsonArtifacts(String(rawOutputs.history_search.timeline_context ?? "")),
        relevant_records: Array.isArray(rawOutputs.history_search.relevant_records)
          ? (rawOutputs.history_search.relevant_records as Array<Record<string, unknown>>).map(
              (rec) => ({
                date: String(rec.date ?? ""),
                summary: String(rec.summary ?? ""),
                clinical_relevance: String(rec.clinical_relevance ?? ""),
                similarity_score: Number(rec.similarity_score ?? 0),
              })
            )
          : [],
      }
    : undefined;

  // ── Pipeline metrics ───────────────────────────────────────
  const pipelineMetrics = r.pipeline_metrics
    ? {
        tools_s: r.pipeline_metrics.tools_s,
        judge_s: r.pipeline_metrics.judge_s,
        report_s: r.pipeline_metrics.report_s,
        total_s: r.pipeline_metrics.total_s,
        tool_timings: r.pipeline_metrics.tool_timings,
        requery_cycles: r.pipeline_metrics.requery_cycles,
        tools_called: r.pipeline_metrics.tools_called,
        tools_failed: r.pipeline_metrics.tools_failed,
      }
    : undefined;

  return {
    id: r.report_id,
    diagnosis: r.diagnosis,
    confidence: r.confidence,
    confidence_method: r.confidence_method,
    evidence_summary: cleanJsonArtifacts(r.evidence_summary),
    timeline_impact: cleanJsonArtifacts(r.timeline_impact),
    plan: r.plan,
    judge_verdict: r.judge_verdict
      ? {
          status: r.judge_verdict.verdict as "consensus" | "conflict",
          confidence: r.judge_verdict.confidence,
          reasoning: r.judge_verdict.reasoning,
          contradictions: r.judge_verdict.contradictions,
          low_confidence_items: r.judge_verdict.low_confidence_items,
          missing_context: r.judge_verdict.missing_context,
          requery_tools: r.judge_verdict.requery_tools,
        }
      : undefined,
    explainability: {
      heatmap_url: imageExplainability?.attention_heatmap_url ?? r.heatmap_urls?.[0],
    },
    specialist_outputs: {
      image_analysis: imageAnalysis,
      image_explainability: imageExplainability,
      text_reasoning: textReasoning,
      history_search: historySearch,
    },
    pipeline_metrics: pipelineMetrics,
    original_image_url: r.image_urls?.[0],
  };
}

/** Map backend Finding → frontend Finding */
export function mapApiFinding(f: ApiFinding): Finding {
  return {
    finding: f.finding,
    confidence: f.confidence,
    explanation: f.explanation,
    severity: f.severity,
    region_bbox: f.region_bbox,
    metadata: f.metadata,
  };
}

/** Map backend reasoning_trace → frontend ReasoningStep[] */
export function mapApiReasoningTrace(
  trace: Record<string, unknown>[]
): ReasoningStep[] {
  if (!trace || !Array.isArray(trace)) return [];
  return trace.map((entry, index) => ({
    step: (entry.step as number) ?? index + 1,
    action: (entry.action as string) ?? (entry.tool as string) ?? "",
    observation: (entry.observation as string) ?? (entry.result as string) ?? "",
    reasoning: (entry.reasoning as string) ?? (entry.thought as string) ?? "",
    tool: entry.tool as string | undefined,
    timestamp: entry.timestamp as string | undefined,
  }));
}
