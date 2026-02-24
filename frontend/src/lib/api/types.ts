/* ──────────────────────────────────────────────────────────────
 *  API request/response types — mirrors backend schemas.py
 * ────────────────────────────────────────────────────────────── */

// ── Health ──────────────────────────────────────────────────
export interface ApiHealthResponse {
  status: string;
  version: string;
  tools_registered: string[];
  debug: boolean;
  db_connected: boolean;
}

// ── Auth ────────────────────────────────────────────────────
export interface ApiUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

export interface ApiLoginRequest {
  email: string;
  password: string;
}

export interface ApiRegisterRequest {
  email: string;
  password: string;
  name: string;
  role?: string;
}

export interface ApiAuthResponse {
  access_token: string;
  token_type: string;
  user: ApiUser;
}

// ── Patient ─────────────────────────────────────────────────
export interface ApiPatientSummary {
  id: string;
  name: string;
  date_of_birth: string;
  gender: string;
  medical_record_number?: string;
  created_at: string;
}

export interface ApiCreatePatientRequest {
  name: string;
  date_of_birth: string;
  gender: string;
  medical_record_number?: string;
}

export interface ApiPatientListResponse {
  patients: ApiPatientSummary[];
  count: number;
}

// ── Timeline ────────────────────────────────────────────────
export interface ApiTimelineEvent {
  id: string;
  date: string;
  event_type: string;
  summary: string;
  source_type?: string;
  source_id?: string;
  metadata: Record<string, unknown>;
}

export interface ApiPatientTimelineResponse {
  patient_id: string;
  events: ApiTimelineEvent[];
  count: number;
}

// ── Case Analysis ───────────────────────────────────────────
export interface ApiCaseAnalysisRequest {
  patient_id: string;
  encounter_id?: string;
  image_urls?: string[];
  audio_urls?: string[];
  document_urls?: string[];
  clinical_context?: string;
  doctor_query: string;
  patient_history_text?: string;
  lab_results?: Record<string, unknown>[];
}

export interface ApiFinding {
  finding: string;
  confidence: number;
  explanation: string;
  severity: string;
  region_bbox?: number[];
  metadata?: Record<string, unknown>;
}

export interface ApiJudgmentResult {
  verdict: "consensus" | "conflict";
  confidence: number;
  reasoning: string;
  contradictions: string[];
  low_confidence_items: string[];
  missing_context: string[];
  requery_tools: string[];
}

export interface ApiPipelineMetrics {
  tools_s: number;
  judge_s: number;
  report_s: number;
  total_s: number;
  tool_timings: Record<string, number>;
  requery_cycles: number;
  tools_called: string[];
  tools_failed: string[];
}

export interface ApiCaseAnalysisResponse {
  report_id: string;
  encounter_id: string;
  patient_id: string;
  diagnosis: string;
  confidence: number;
  confidence_method: string;
  evidence_summary: string;
  timeline_impact: string;
  plan: string[];
  findings: ApiFinding[];
  reasoning_trace: Record<string, unknown>[];
  judge_verdict: ApiJudgmentResult | null;
  approval_status: string;
  created_at: string;
  heatmap_urls: string[];
  image_urls?: string[];
  specialist_summaries: Record<string, string>;
  /** Rich structured tool outputs with condition_scores, heatmaps, reasoning chains. */
  specialist_outputs: Record<string, Record<string, unknown>>;
  pipeline_metrics: ApiPipelineMetrics | null;
}

// ── Report Approval ─────────────────────────────────────────
export interface ApiReportApprovalRequest {
  report_id: string;
  status: string;
  doctor_notes?: string;
  edits?: Record<string, unknown>;
}

export interface ApiReportApprovalResponse {
  report_id: string;
  status: string;
  updated_at: string;
}

// ── File Upload ─────────────────────────────────────────────
export interface ApiUploadedFileInfo {
  id: string;
  original_name: string;
  category: "image" | "audio" | "document";
  content_type: string;
  size: number;
  url: string;
}

export interface ApiUploadResponse {
  files: ApiUploadedFileInfo[];
  image_urls: string[];
  audio_urls: string[];
  document_urls: string[];
}
