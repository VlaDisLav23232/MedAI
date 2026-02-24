/* ──────────────────────────────────────────────────────────────
 *  Shared frontend types — mirrors backend domain entities
 * ────────────────────────────────────────────────────────────── */

export type Theme = "light" | "dark" | "system";

export type AgentStatus =
  | "idle"
  | "routing"
  | "analyzing_image"
  | "analyzing_text"
  | "analyzing_audio"
  | "searching_history"
  | "judging"
  | "generating_report"
  | "complete"
  | "error";

export interface Patient {
  id: string;
  name: string;
  medical_record_number: string;
  date_of_birth?: string;
  gender?: string;
  created_at?: string;
}

export interface TimelineEvent {
  id: string;
  patient_id: string;
  date: string;
  event_type:
    | "imaging"
    | "lab"
    | "encounter"
    | "ai_report"
    | "procedure"
    | "medication"
    | "note"
    | "audio"
    | "prescription"
    | "referral"
    | "vital_signs"
    | "diagnosis";
  summary: string;
  source_id?: string;
  source_type?: string;
  severity?: string;
  metadata?: Record<string, unknown>;
}

export interface Attachment {
  id: string;
  type: string;
  name: string;
  url: string;
}

export interface Citation {
  id: string;
  type: "finding" | "imaging" | "lab" | "history" | "guideline";
  title: string;
  content: string;
  source: string;
  confidence?: number;
}

export interface ToolResult {
  tool: string;
  status: "running" | "complete" | "error";
  duration_ms?: number;
  summary?: string;
}

export interface Finding {
  finding: string;
  confidence: number;
  explanation: string;
  severity: string;
  region_bbox?: number[];
  metadata?: Record<string, unknown>;
}

export interface ReasoningStep {
  step: number;
  action: string;
  observation: string;
  reasoning: string;
  tool?: string;
  timestamp?: string;
}

export interface JudgeVerdict {
  status: "consensus" | "conflict";
  confidence: number;
  reasoning: string;
  contradictions?: string[];
  low_confidence_items?: string[];
  missing_context?: string[];
  requery_tools?: string[];
}

export interface HistoryRecord {
  date: string;
  summary: string;
  clinical_relevance: string;
  similarity_score: number;
}

/* ── Condition Score (from MedSigLIP zero-shot classification) ── */
export interface ConditionScore {
  label: string;
  /** Softmax probability (relative ranking across all labels) */
  probability: number;
  /** Sigmoid score (independent per-label probability) */
  sigmoid_score?: number;
  /** Raw logit from the model before activation */
  raw_logit?: number;
  /** URL to per-condition GradCAM attention heatmap */
  heatmap_data_uri?: string;
}

/* ── Image Explainability (from MedSigLIP) ── */
export interface ImageExplainability {
  tool: string;
  modality_detected?: string;
  condition_scores: ConditionScore[];
  attention_heatmap_url?: string;
  inference?: {
    model_id?: string;
    latency_ms?: number;
    tokens_used?: number;
  };
}

/* ── Image Analysis (from MedGemma 4B) ── */
export interface ImageAnalysisOutput {
  tool: string;
  modality_detected?: string;
  findings: Finding[];
  differential_diagnoses: string[];
  recommended_followup: string[];
  attention_heatmap_url?: string;
  inference?: {
    model_id?: string;
    latency_ms?: number;
  };
}

/* ── Text Reasoning (from MedGemma 27B) ── */
export interface TextReasoningOutput {
  tool: string;
  assessment?: string;
  confidence?: number;
  reasoning_chain?: Array<{
    step: number;
    thought: string;
    action: string;
    observation: string;
  }>;
  evidence_citations?: string[];
  plan_suggestions?: string[];
  contraindication_flags?: string[];
  inference?: {
    model_id?: string;
    latency_ms?: number;
  };
}

/* ── History Search ── */
export interface HistorySearchOutput {
  tool: string;
  timeline_context: string;
  relevant_records: HistoryRecord[];
}

/* ── Pipeline Metrics ── */
export interface PipelineMetrics {
  tools_s: number;
  judge_s: number;
  report_s: number;
  total_s: number;
  tool_timings: Record<string, number>;
  requery_cycles: number;
  tools_called: string[];
  tools_failed: string[];
}

export interface SpecialistOutputs {
  image_analysis?: ImageAnalysisOutput;
  image_explainability?: ImageExplainability;
  text_reasoning?: TextReasoningOutput;
  history_search?: HistorySearchOutput;
}

export interface AIReport {
  id: string;
  diagnosis: string;
  confidence: number;
  confidence_method?: string;
  evidence_summary: string;
  timeline_impact: string;
  plan: string[];
  judge_verdict?: JudgeVerdict;
  explainability?: {
    heatmap_url?: string;
  };
  specialist_outputs?: SpecialistOutputs;
  pipeline_metrics?: PipelineMetrics;
  /** Original uploaded medical image URL (for overlay in viewer) */
  original_image_url?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  timestamp: string;
  attachments?: Attachment[];
  report?: AIReport;
  citations?: Citation[];
  toolResults?: ToolResult[];
}
