"""Mock tool implementations for testing and development.

These return realistic-looking structured data without
calling any real model endpoints. Essential for:
- Unit testing the orchestration pipeline
- Frontend development against stable API
- CI/CD without GPU access
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from medai.domain.entities import (
    AudioAnalysisOutput,
    AudioSegment,
    ConditionScore,
    EvidenceCitation,
    Finding,
    HistoryRecord,
    HistorySearchOutput,
    ImageAnalysisOutput,
    ImageExplainabilityOutput,
    InferenceMetadata,
    Modality,
    Severity,
    TextReasoningOutput,
    ToolName,
    ToolOutput,
)
from medai.domain.interfaces import BaseTool


class MockImageAnalysisTool(BaseTool):
    """Mock image analysis — returns realistic CXR findings."""

    @property
    def name(self) -> ToolName:
        return ToolName.IMAGE_ANALYSIS

    @property
    def description(self) -> str:
        return (
            "Analyze a medical image (X-ray, CT, MRI, etc.) and return "
            "structured findings with confidence scores and severity levels. "
            "Supports chest X-ray, GI tract MRI, dermatology, ophthalmology, "
            "and histopathology images."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL or path to the medical image to analyze",
                },
                "clinical_context": {
                    "type": "string",
                    "description": "Clinical context from the doctor (symptoms, question)",
                },
                "modality_hint": {
                    "type": "string",
                    "description": "Expected image modality (xray, ct, mri, etc.)",
                    "enum": [m.value for m in Modality],
                },
            },
            "required": ["image_url"],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> ImageAnalysisOutput:
        return ImageAnalysisOutput(
            modality_detected=Modality.XRAY,
            findings=[
                Finding(
                    finding="Right lower lobe consolidation",
                    confidence=0.89,
                    explanation=(
                        "Dense opacity in the right lower zone with air bronchograms, "
                        "consistent with pneumonia. No pleural effusion seen."
                    ),
                    severity=Severity.MODERATE,
                ),
                Finding(
                    finding="Mild cardiomegaly",
                    confidence=0.72,
                    explanation="Cardiothoracic ratio slightly above 0.5, suggesting mild enlargement.",
                    severity=Severity.MILD,
                ),
            ],
            attention_heatmap_url="/api/v1/artifacts/mock-heatmap-001/heatmap.png",
            embedding_id="emb-img-mock-001",
            differential_diagnoses=["pneumonia", "atelectasis", "pleural_effusion"],
            recommended_followup=["Lateral CXR", "CBC with differential", "Sputum culture"],
        )


class MockTextReasoningTool(BaseTool):
    """Mock text reasoning — returns realistic clinical assessment."""

    @property
    def name(self) -> ToolName:
        return ToolName.TEXT_REASONING

    @property
    def description(self) -> str:
        return (
            "Analyze patient history, lab results, and clinical context to produce "
            "a structured medical assessment with reasoning chain, evidence citations, "
            "and treatment plan suggestions. Checks for contraindications."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_history": {
                    "type": "string",
                    "description": "Full patient history text",
                },
                "lab_results": {
                    "type": "string",
                    "description": "Lab results in text or JSON format",
                },
                "clinical_context": {
                    "type": "string",
                    "description": "Current clinical context and doctor's question",
                },
                "imaging_findings": {
                    "type": "string",
                    "description": "Summary of imaging findings from image analysis tool",
                },
            },
            "required": ["clinical_context"],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> TextReasoningOutput:
        return TextReasoningOutput(
            reasoning_chain=[
                {
                    "step": 1,
                    "thought": (
                        "Patient presents with 3-week history of productive cough, "
                        "fever (38.5°C), and right-sided chest pain."
                    ),
                },
                {
                    "step": 2,
                    "thought": (
                        "Lab values show elevated WBC (14.2k) with left shift and CRP (45mg/L), "
                        "indicating acute bacterial infection."
                    ),
                },
                {
                    "step": 3,
                    "thought": (
                        "Imaging findings of RLL consolidation with air bronchograms "
                        "combined with clinical presentation strongly suggest community-acquired pneumonia."
                    ),
                },
            ],
            assessment="Community-acquired pneumonia (CAP), likely bacterial, right lower lobe",
            confidence=0.87,
            evidence_citations=[
                EvidenceCitation(
                    source="patient_history_2024-03-15",
                    source_type="patient_history",
                    relevant_excerpt="Previous CXR showed clear lung fields, no prior respiratory issues",
                    date=datetime(2024, 3, 15),
                ),
                EvidenceCitation(
                    source="lab_result_2026-02-07",
                    source_type="lab_result",
                    relevant_excerpt="WBC 14.2k (H), CRP 45 mg/L (H), Procalcitonin 0.8 ng/mL",
                    date=datetime(2026, 2, 7),
                ),
            ],
            plan_suggestions=[
                "Amoxicillin-clavulanate 875/125mg BID × 7 days",
                "Follow-up CXR in 6 weeks",
                "Consider sputum culture if no improvement in 48h",
                "Antipyretics PRN for fever",
            ],
            contraindication_flags=[],
        )


class MockAudioAnalysisTool(BaseTool):
    """Mock audio analysis — returns realistic respiratory sound findings."""

    @property
    def name(self) -> ToolName:
        return ToolName.AUDIO_ANALYSIS

    @property
    def description(self) -> str:
        return (
            "Analyze a health audio recording (cough, breathing, lung sounds) "
            "and return segment-by-segment classification with confidence scores. "
            "Detects wheezes, crackles, stridor, and abnormal breathing patterns."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "audio_url": {
                    "type": "string",
                    "description": "URL or path to the audio recording (16kHz mono WAV)",
                },
                "audio_type": {
                    "type": "string",
                    "description": "Type of audio: breathing, cough, lung_sounds",
                    "enum": ["breathing", "cough", "lung_sounds"],
                },
                "clinical_context": {
                    "type": "string",
                    "description": "Clinical context for the audio analysis",
                },
            },
            "required": ["audio_url"],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> AudioAnalysisOutput:
        return AudioAnalysisOutput(
            audio_type=kwargs.get("audio_type", "breathing"),
            segments=[
                AudioSegment(time_start=0.0, time_end=2.0, classification="normal", confidence=0.92),
                AudioSegment(time_start=2.0, time_end=4.0, classification="wheeze", confidence=0.78),
                AudioSegment(time_start=4.0, time_end=6.0, classification="crackle", confidence=0.65),
                AudioSegment(time_start=6.0, time_end=8.0, classification="normal", confidence=0.88),
            ],
            summary="Intermittent wheezing and fine crackles detected in mid-recording segments, consistent with lower respiratory tract involvement.",
            abnormal_segment_timestamps=[2.0, 4.0],
            embedding_id="emb-audio-mock-001",
        )


class MockHistorySearchTool(BaseTool):
    """Mock history search — returns realistic patient timeline data."""

    @property
    def name(self) -> ToolName:
        return ToolName.HISTORY_SEARCH

    @property
    def description(self) -> str:
        return (
            "Search a patient's longitudinal health history using semantic similarity. "
            "Returns relevant past encounters, imaging studies, lab results, and notes "
            "ranked by relevance to the current clinical question."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier",
                },
                "query": {
                    "type": "string",
                    "description": "Clinical query to search patient history for",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of historical records to return",
                    "default": 5,
                },
            },
            "required": ["patient_id", "query"],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> HistorySearchOutput:
        patient_id = kwargs.get("patient_id", "PT-UNKNOWN")
        return HistorySearchOutput(
            patient_id=patient_id,
            relevant_records=[
                HistoryRecord(
                    date=datetime(2024, 3, 15),
                    record_type="imaging",
                    summary="Chest X-ray: clear lung fields bilaterally, normal cardiac silhouette",
                    similarity_score=0.87,
                    clinical_relevance=(
                        "Comparison baseline — current consolidation represents "
                        "a new acute finding not present 11 months ago"
                    ),
                ),
                HistoryRecord(
                    date=datetime(2023, 11, 20),
                    record_type="lab",
                    summary="Baseline labs: WBC 7.2k, CRP <5, all within normal limits",
                    similarity_score=0.72,
                    clinical_relevance=(
                        "Current WBC 14.2k and CRP 45 represent significant elevation "
                        "from patient's known baseline values"
                    ),
                ),
                HistoryRecord(
                    date=datetime(2025, 8, 10),
                    record_type="encounter",
                    summary="Annual physical: no respiratory complaints, lungs clear on auscultation",
                    similarity_score=0.61,
                    clinical_relevance="No prior respiratory issues documented",
                ),
            ],
            timeline_context=(
                "Patient has no prior history of pneumonia or significant respiratory disease. "
                "Last imaging 11 months ago showed clear lungs. "
                "Baseline inflammatory markers were normal as of November 2023."
            ),
        )


class MockImageExplainabilityTool(BaseTool):
    """Mock image explainability — returns realistic SigLIP-style condition scores.

    Probabilities are drawn from a realistic distribution (not all 0.9).
    Heatmap URIs use placeholder paths — the real endpoint returns base64 PNGs.
    """

    @property
    def name(self) -> ToolName:
        return ToolName.IMAGE_EXPLAINABILITY

    @property
    def description(self) -> str:
        return (
            "Generate visual explainability heatmaps for medical images using "
            "zero-shot classification. Highlights which image regions match "
            "clinical conditions. Returns per-condition similarity probabilities "
            "(real sigmoid scores, not LLM-generated) and spatial activation maps."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL or path to the medical image to analyze",
                },
                "modality_hint": {
                    "type": "string",
                    "description": "Image modality — determines which condition labels to check",
                    "enum": [m.value for m in Modality],
                },
                "clinical_context": {
                    "type": "string",
                    "description": "Clinical context (used for additional label context)",
                },
                "condition_labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional override: custom condition labels to score against.",
                },
            },
            "required": ["image_url"],
            "additionalProperties": False,
        }

    async def execute(self, **kwargs: Any) -> ImageExplainabilityOutput:
        return ImageExplainabilityOutput(
            modality_detected=Modality.XRAY,
            condition_scores=[
                ConditionScore(
                    label="consolidation consistent with pneumonia",
                    probability=0.42,
                    sigmoid_score=3.2e-05,
                    raw_logit=-10.35,
                    heatmap_data_uri="/api/v1/artifacts/mock-heatmap-siglip-001/pneumonia.png",
                ),
                ConditionScore(
                    label="cardiomegaly with enlarged heart silhouette",
                    probability=0.28,
                    sigmoid_score=2.1e-05,
                    raw_logit=-10.77,
                    heatmap_data_uri="/api/v1/artifacts/mock-heatmap-siglip-001/cardiomegaly.png",
                ),
                ConditionScore(
                    label="pleural effusion with blunting of costophrenic angle",
                    probability=0.15,
                    sigmoid_score=1.1e-05,
                    raw_logit=-11.42,
                    heatmap_data_uri="/api/v1/artifacts/mock-heatmap-siglip-001/effusion.png",
                ),
                ConditionScore(
                    label="normal lung fields with no abnormality",
                    probability=0.10,
                    sigmoid_score=7.5e-06,
                    raw_logit=-11.80,
                    heatmap_data_uri=None,
                ),
                ConditionScore(
                    label="pneumothorax with absent lung markings",
                    probability=0.05,
                    sigmoid_score=3.8e-06,
                    raw_logit=-12.48,
                    heatmap_data_uri=None,
                ),
            ],
            attention_heatmap_url="/api/v1/artifacts/mock-heatmap-siglip-001/pneumonia.png",
            embedding=[0.012, -0.034, 0.056, 0.078, -0.091],  # truncated mock
            inference=InferenceMetadata(
                model_id="google/medsiglip-448",
                temperature=0.0,
                token_count=0,
                inference_time_ms=142.3,
            ),
        )


def register_mock_tools() -> dict[ToolName, BaseTool]:
    """Factory function: create all mock tools.

    Returns dict for easy registration with ToolRegistry.
    """
    tools: dict[ToolName, BaseTool] = {
        ToolName.IMAGE_ANALYSIS: MockImageAnalysisTool(),
        ToolName.TEXT_REASONING: MockTextReasoningTool(),
        ToolName.AUDIO_ANALYSIS: MockAudioAnalysisTool(),
        ToolName.HISTORY_SEARCH: MockHistorySearchTool(),
        ToolName.IMAGE_EXPLAINABILITY: MockImageExplainabilityTool(),
    }
    return tools
