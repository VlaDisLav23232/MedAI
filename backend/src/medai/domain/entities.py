"""Domain entities — pure data models representing core business concepts.

These are the immutable contracts of the system.
All tools, services and API routes operate on these types.

FRONTEND HANDOFF NOTES:
- Every field has a type and description — use these for UI rendering.
- Enums are exhaustive — switch on them for UI state.
- InferenceMetadata carries model provenance (what model, what settings).
- PipelineMetrics carries timing (for performance dashboards).
- Finding.confidence is NOT a calibrated probability — render with
  a disclaimer tooltip in the UI.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class EncounterType(str, Enum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    IMAGING = "imaging"
    LAB = "lab"
    PROCEDURE = "procedure"
    REFERRAL = "referral"
    TELEMEDICINE = "telemedicine"


class EncounterStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class TimelineEventType(str, Enum):
    ENCOUNTER = "encounter"
    IMAGING = "imaging"
    LAB = "lab"
    AUDIO = "audio"
    AI_REPORT = "ai_report"
    NOTE = "note"
    PROCEDURE = "procedure"
    PRESCRIPTION = "prescription"
    REFERRAL = "referral"
    VITAL_SIGNS = "vital_signs"
    DIAGNOSIS = "diagnosis"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class Severity(str, Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class Modality(str, Enum):
    XRAY = "xray"
    CT = "ct"
    MRI = "mri"
    ULTRASOUND = "ultrasound"
    FUNDUS = "fundus"
    DERMATOLOGY = "dermatology"
    HISTOPATHOLOGY = "histopathology"
    PET = "pet"
    MAMMOGRAPHY = "mammography"
    ENDOSCOPY = "endoscopy"
    OTHER = "other"


class JudgeVerdict(str, Enum):
    CONSENSUS = "consensus"
    CONFLICT = "conflict"


class ToolName(str, Enum):
    """Registered tool identifiers — extend this enum to add new tools."""
    IMAGE_ANALYSIS = "image_analysis"
    TEXT_REASONING = "text_reasoning"
    AUDIO_ANALYSIS = "audio_analysis"
    HISTORY_SEARCH = "history_search"


class ConfidenceMethod(str, Enum):
    """How a confidence value was produced — for UI transparency."""
    MODEL_SELF_REPORTED = "model_self_reported"
    LOGPROB_SEQUENCE = "logprob_sequence"
    JUDGE_ASSESSMENT = "judge_assessment"
    ENSEMBLE_AGREEMENT = "ensemble_agreement"
    NOT_AVAILABLE = "not_available"


# ═══════════════════════════════════════════════════════════════
#  Inference Provenance
# ═══════════════════════════════════════════════════════════════

class InferenceMetadata(BaseModel):
    """Provenance and statistics from a single model inference call.

    This is REAL data from the inference server — not hallucinated.
    Frontend should display this in a "Model Info" expandable section.

    In production these fields come from:
    - model_id: set in the Modal endpoint code (e.g. "google/medgemma-4b-it")
    - temperature: generation config parameter passed to model.generate()
    - token_count: len(generated_ids) after generation
    - inference_time_ms: wall-clock time.monotonic() around model.generate()
    - sequence_fluency_score: geometric mean of per-token log-probabilities
      (measures how predictable each token was, NOT clinical accuracy)
    """
    model_id: str = Field(description="HuggingFace model identifier")
    temperature: float = Field(description="Sampling temperature (0.0 = greedy)")
    token_count: int = Field(ge=0, description="Number of tokens generated")
    inference_time_ms: float = Field(ge=0, description="Wall-clock inference time in milliseconds")
    sequence_fluency_score: float | None = Field(
        default=None,
        ge=0.0, le=1.0,
        description=(
            "Geometric mean of per-token log-probabilities. "
            "Measures generation fluency, NOT clinical accuracy."
        ),
    )


class PipelineMetrics(BaseModel):
    """Timing and cost breakdown for the full analysis pipeline.

    Frontend should display this in a "Performance" panel.
    All times are wall-clock seconds.
    """
    tools_s: float = Field(description="Total time for all tool calls")
    judge_s: float = Field(description="Total time for judge evaluation + requery cycles")
    report_s: float = Field(description="Time for report assembly")
    total_s: float = Field(description="End-to-end pipeline time")
    tool_timings: dict[str, float] = Field(
        default_factory=dict,
        description="Per-tool wall-clock time in seconds (e.g. {'image_analysis': 16.7})",
    )
    requery_cycles: int = Field(default=0, description="Number of judge requery cycles executed")
    tools_called: list[str] = Field(default_factory=list, description="Tool names that were called")
    tools_failed: list[str] = Field(default_factory=list, description="Tool names that errored")


# ═══════════════════════════════════════════════════════════════
#  Core Entities
# ═══════════════════════════════════════════════════════════════

class Patient(BaseModel):
    """Core patient record.

    In production: populated from EHR/FHIR integration (Helsi/eHealth API).
    """
    id: str = Field(default_factory=lambda: f"PT-{uuid.uuid4().hex[:8].upper()}")
    name: str
    date_of_birth: date
    gender: Gender = Gender.UNKNOWN
    medical_record_number: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Encounter(BaseModel):
    """A single patient-doctor interaction."""
    id: str = Field(default_factory=lambda: f"ENC-{uuid.uuid4().hex[:8].upper()}")
    patient_id: str
    date: datetime = Field(default_factory=datetime.utcnow)
    encounter_type: EncounterType = EncounterType.CONSULTATION
    chief_complaint: str | None = None
    status: EncounterStatus = EncounterStatus.IN_PROGRESS


class TimelineEvent(BaseModel):
    """A single entry on the patient timeline.

    `metadata` is a structured dict whose keys depend on `event_type`:

    In production this data comes from:
    - EHR/FHIR integration: Observation, DiagnosticReport, Procedure resources
    - Lab Information System (LIS): lab results with reference ranges
    - Radiology Information System (RIS): imaging reports, DICOM metadata
    - Manual entry by clinicians during consultations

    Example metadata by event_type:
        imaging: {"technique": "PA/Lateral", "kvp": 120, "report_id": "RAD-001"}
        lab:     {"wbc": "14.8", "crp": "92", "units": {"wbc": "×10⁹/L"}, "flags": {"wbc": "H"}}
        encounter: {"vitals": {"bp": "145/92", "hr": 98}, "icd10": ["J18.1"]}
        procedure: {"cpt_code": "31622", "anesthesia": "conscious_sedation"}
        prescription: {"drug": "Amoxicillin", "dose": "500mg", "frequency": "TID"}
    """
    id: str = Field(default_factory=lambda: f"TL-{uuid.uuid4().hex[:8].upper()}")
    patient_id: str
    date: datetime
    event_type: TimelineEventType
    summary: str
    source_id: str | None = Field(default=None, description="ID of the originating resource (encounter, report, etc.)")
    source_type: str | None = Field(default=None, description="Type of source (e.g. 'fhir_observation', 'ris_report')")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
#  Tool Output Contracts
# ═══════════════════════════════════════════════════════════════

class Finding(BaseModel):
    """A single clinical finding from any specialist tool.

    CONFIDENCE DISCLAIMER:
      `confidence` is the model's self-reported certainty expressed as
      text output (the model predicts what number a doctor would write).
      It is NOT a calibrated probability. Treat it as an ordinal ranking
      (higher = model is more sure) NOT as "X% chance of being correct".

    NOTE on `region_bbox`: Reserved for future MedSigLIP/MedSAM
    integration. Currently always None.
    """
    finding: str
    confidence: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Model self-reported certainty (NOT a calibrated probability). "
            "Treat as ordinal ranking, not as P(correct)."
        ),
    )
    explanation: str
    severity: Severity = Severity.NONE
    region_bbox: list[int] | None = Field(
        default=None,
        description="Reserved for future segmentation model integration",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Transparency metadata: sequence_fluency_score, "
            "model_self_reported_confidence, confidence_note, "
            "plus full InferenceMetadata when available."
        ),
    )


class EvidenceCitation(BaseModel):
    """Reference to source data supporting a finding."""
    source: str
    source_type: str = "unknown"  # "patient_history", "lab_result", "imaging", etc.
    relevant_excerpt: str
    date: datetime | None = None


class ImageAnalysisOutput(BaseModel):
    """Contract for Image Analysis Tool output."""
    tool: str = ToolName.IMAGE_ANALYSIS
    modality_detected: Modality
    findings: list[Finding]
    attention_heatmap_url: str | None = None
    embedding_id: str | None = None
    differential_diagnoses: list[str] = Field(default_factory=list)
    recommended_followup: list[str] = Field(default_factory=list)
    inference: InferenceMetadata | None = Field(default=None, description="Model provenance and stats")


class TextReasoningOutput(BaseModel):
    """Contract for Text Reasoning Tool output."""
    tool: str = ToolName.TEXT_REASONING
    reasoning_chain: list[dict[str, Any]]
    assessment: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_citations: list[EvidenceCitation] = Field(default_factory=list)
    plan_suggestions: list[str] = Field(default_factory=list)
    contraindication_flags: list[str] = Field(default_factory=list)
    inference: InferenceMetadata | None = Field(default=None, description="Model provenance and stats")


class AudioSegment(BaseModel):
    """A single analyzed audio segment."""
    time_start: float
    time_end: float
    classification: str
    confidence: float = Field(ge=0.0, le=1.0)


class AudioAnalysisOutput(BaseModel):
    """Contract for Audio Analysis Tool output."""
    tool: str = ToolName.AUDIO_ANALYSIS
    audio_type: str  # "breathing", "cough", "lung_sounds"
    segments: list[AudioSegment]
    summary: str
    abnormal_segment_timestamps: list[float] = Field(default_factory=list)
    embedding_id: str | None = None
    inference: InferenceMetadata | None = Field(default=None, description="Model provenance and stats")


class HistoryRecord(BaseModel):
    """A single retrieved historical record."""
    date: datetime
    record_type: str  # "imaging", "lab", "encounter", etc.
    summary: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    clinical_relevance: str


class HistorySearchOutput(BaseModel):
    """Contract for History Search Tool output."""
    tool: str = ToolName.HISTORY_SEARCH
    patient_id: str
    relevant_records: list[HistoryRecord]
    timeline_context: str


# ═══════════════════════════════════════════════════════════════
#  Aggregated Types
# ═══════════════════════════════════════════════════════════════

# Union of all tool outputs for type-safe handling
ToolOutput = ImageAnalysisOutput | TextReasoningOutput | AudioAnalysisOutput | HistorySearchOutput


class SpecialistResults(BaseModel):
    """Collection of all specialist tool results for a single case."""
    results: dict[str, ToolOutput] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


class JudgmentResult(BaseModel):
    """Output of the Judge Agent."""
    verdict: JudgeVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    contradictions: list[str] = Field(default_factory=list)
    low_confidence_items: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    requery_tools: list[ToolName] = Field(default_factory=list)


class FinalReport(BaseModel):
    """The final structured report presented to the doctor."""
    id: str = Field(default_factory=lambda: f"RPT-{uuid.uuid4().hex[:8].upper()}")
    encounter_id: str
    patient_id: str
    diagnosis: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_method: ConfidenceMethod = Field(
        default=ConfidenceMethod.MODEL_SELF_REPORTED,
        description="How the top-level confidence was determined",
    )
    evidence_summary: str
    timeline_impact: str
    plan: list[str]
    findings: list[Finding]
    reasoning_trace: list[dict[str, Any]] = Field(default_factory=list)
    specialist_outputs: dict[str, Any] = Field(default_factory=dict)
    judge_verdict: JudgmentResult | None = None
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    doctor_notes: str | None = None
    pipeline_metrics: PipelineMetrics | None = Field(
        default=None,
        description="Timing and performance breakdown for the full pipeline",
    )
