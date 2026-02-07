"""HTTP-based tool implementations for real model endpoints.

These tools call actual inference servers (Modal, HuggingFace, Vertex AI)
via HTTP. They implement the same BaseTool interface as mock tools,
so they can be swapped in via dependency injection without changing
any orchestrator or route code.

Each tool includes:
- Retry logic with exponential backoff
- Configurable timeout
- Structured response parsing
- Graceful error handling (returns error in output, never crashes)
"""

from __future__ import annotations

import structlog
from typing import Any

import httpx

from medai.config import Settings
from medai.domain.entities import (
    AudioAnalysisOutput,
    AudioSegment,
    EvidenceCitation,
    Finding,
    HistoryRecord,
    HistorySearchOutput,
    ImageAnalysisOutput,
    Modality,
    Severity,
    TextReasoningOutput,
    ToolName,
    ToolOutput,
)
from medai.domain.interfaces import BaseTool

logger = structlog.get_logger()

# ── Retry / timeout defaults ──────────────────────────────

DEFAULT_TIMEOUT = 300.0  # seconds (Modal cold starts can take 2-5 min)
MAX_RETRIES = 2
RETRY_BACKOFF = 2.0  # base seconds for exponential backoff


class _HttpToolBase(BaseTool):
    """Common HTTP plumbing shared by all remote tools.

    Subclasses only need to implement:
    - name / description / input_schema (tool identity)
    - _build_request_payload  (kwargs → HTTP body)
    - _parse_response         (HTTP body → ToolOutput)
    """

    def __init__(
        self,
        endpoint: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries

    # ── Template method: subclasses override these ─────────

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        """Convert tool kwargs to the HTTP request body."""
        return kwargs

    def _parse_response(self, data: dict[str, Any]) -> ToolOutput:
        """Parse the JSON response body into a typed ToolOutput."""
        raise NotImplementedError

    def _get_path(self) -> str:
        """URL path for this tool's inference endpoint.

        Modal @fastapi_endpoint embeds the function name in the subdomain,
        so the actual endpoint is at the root path '/'.
        """
        return ""

    # ── Core HTTP execution with retry ─────────────────────

    async def execute(self, **kwargs: Any) -> ToolOutput:
        """Call the remote endpoint with retry + structured parsing."""
        url = f"{self._endpoint}{self._get_path()}"
        payload = self._build_request_payload(**kwargs)

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_response(data)
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    "tool_http_timeout",
                    tool=self.name.value,
                    attempt=attempt + 1,
                    url=url,
                )
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    "tool_http_error",
                    tool=self.name.value,
                    attempt=attempt + 1,
                    status=e.response.status_code,
                    url=url,
                )
                # Don't retry 4xx client errors
                if 400 <= e.response.status_code < 500:
                    break
            except Exception as e:
                last_error = e
                logger.warning(
                    "tool_http_unexpected",
                    tool=self.name.value,
                    attempt=attempt + 1,
                    error=str(e),
                )

            # Exponential backoff before retry
            if attempt < self._max_retries:
                import asyncio
                await asyncio.sleep(RETRY_BACKOFF * (2 ** attempt))

        # All retries exhausted — return a minimal error output
        raise RuntimeError(
            f"Tool {self.name.value} failed after {self._max_retries + 1} attempts: {last_error}"
        )


# ═══════════════════════════════════════════════════════════════
#  HttpImageAnalysisTool
# ═══════════════════════════════════════════════════════════════


class HttpImageAnalysisTool(_HttpToolBase):
    """Calls MedGemma 4B / MedSigLIP for medical image analysis."""

    @property
    def name(self) -> ToolName:
        return ToolName.IMAGE_ANALYSIS

    @property
    def description(self) -> str:
        return (
            "Analyze a medical image (X-ray, CT, MRI, etc.) and return "
            "structured findings with confidence scores, severity levels, "
            "and region bounding boxes. Supports chest X-ray, GI tract MRI, "
            "dermatology, ophthalmology, and histopathology images."
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
        }

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "image_url": kwargs.get("image_url", ""),
            "clinical_context": kwargs.get("clinical_context", ""),
            "modality_hint": kwargs.get("modality_hint", "other"),
        }

    def _parse_response(self, data: dict[str, Any]) -> ImageAnalysisOutput:
        """Parse MedGemma image analysis response into structured output."""
        findings = [
            Finding(
                finding=f.get("finding", "Unknown finding"),
                confidence=float(f.get("confidence", 0.5)),
                explanation=f.get("explanation", ""),
                severity=Severity(f.get("severity", "none")),
                region_bbox=f.get("region_bbox"),
            )
            for f in data.get("findings", [])
        ]

        return ImageAnalysisOutput(
            modality_detected=Modality(data.get("modality_detected", "other")),
            findings=findings,
            attention_heatmap_url=data.get("attention_heatmap_url"),
            embedding_id=data.get("embedding_id"),
            differential_diagnoses=data.get("differential_diagnoses", []),
            recommended_followup=data.get("recommended_followup", []),
        )


# ═══════════════════════════════════════════════════════════════
#  HttpTextReasoningTool
# ═══════════════════════════════════════════════════════════════


class HttpTextReasoningTool(_HttpToolBase):
    """Calls MedGemma 27B Text IT for clinical reasoning."""

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
        }

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "patient_history": kwargs.get("patient_history", ""),
            "lab_results": kwargs.get("lab_results", ""),
            "clinical_context": kwargs.get("clinical_context", ""),
            "imaging_findings": kwargs.get("imaging_findings", ""),
        }

    def _parse_response(self, data: dict[str, Any]) -> TextReasoningOutput:
        """Parse MedGemma text reasoning response."""
        from datetime import datetime

        evidence = [
            EvidenceCitation(
                source=c.get("source", "unknown"),
                source_type=c.get("source_type", "unknown"),
                relevant_excerpt=c.get("relevant_excerpt", ""),
                date=datetime.fromisoformat(c["date"]) if c.get("date") else None,
            )
            for c in data.get("evidence_citations", [])
        ]

        return TextReasoningOutput(
            reasoning_chain=data.get("reasoning_chain", []),
            assessment=data.get("assessment", "No assessment available"),
            confidence=float(data.get("confidence", 0.5)),
            evidence_citations=evidence,
            plan_suggestions=data.get("plan_suggestions", []),
            contraindication_flags=data.get("contraindication_flags", []),
        )


# ═══════════════════════════════════════════════════════════════
#  HttpAudioAnalysisTool
# ═══════════════════════════════════════════════════════════════


class HttpAudioAnalysisTool(_HttpToolBase):
    """Calls HeAR / audio model for respiratory sound analysis."""

    @property
    def name(self) -> ToolName:
        return ToolName.AUDIO_ANALYSIS

    @property
    def description(self) -> str:
        return (
            "Analyze a medical audio recording (breathing sounds, cough, "
            "heart sounds) and return classified segments with timestamps, "
            "confidence scores, and an overall summary."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "audio_url": {
                    "type": "string",
                    "description": "URL or path to the audio recording",
                },
                "audio_type": {
                    "type": "string",
                    "description": "Type of audio (breathing, cough, lung_sounds)",
                },
                "clinical_context": {
                    "type": "string",
                    "description": "Clinical context for the audio analysis",
                },
            },
            "required": ["audio_url"],
        }

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "audio_url": kwargs.get("audio_url", ""),
            "audio_type": kwargs.get("audio_type", "breathing"),
            "clinical_context": kwargs.get("clinical_context", ""),
        }

    def _parse_response(self, data: dict[str, Any]) -> AudioAnalysisOutput:
        """Parse HeAR audio analysis response."""
        segments = [
            AudioSegment(
                time_start=float(s.get("time_start", 0)),
                time_end=float(s.get("time_end", 0)),
                classification=s.get("classification", "unknown"),
                confidence=float(s.get("confidence", 0.5)),
            )
            for s in data.get("segments", [])
        ]

        return AudioAnalysisOutput(
            audio_type=data.get("audio_type", "unknown"),
            segments=segments,
            summary=data.get("summary", "No summary available"),
            abnormal_segment_timestamps=data.get("abnormal_segment_timestamps", []),
            embedding_id=data.get("embedding_id"),
        )


# ═══════════════════════════════════════════════════════════════
#  HttpHistorySearchTool
# ═══════════════════════════════════════════════════════════════


class HttpHistorySearchTool(_HttpToolBase):
    """Calls RAG/vector endpoint for patient history search."""

    @property
    def name(self) -> ToolName:
        return ToolName.HISTORY_SEARCH

    @property
    def description(self) -> str:
        return (
            "Search a patient's medical history for relevant prior records, "
            "imaging studies, lab results, and encounters. Returns the most "
            "clinically relevant records with similarity scores."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "Patient identifier to search history for",
                },
                "query": {
                    "type": "string",
                    "description": "Clinical query to search (e.g., 'prior chest imaging')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of records to return",
                    "default": 10,
                },
            },
            "required": ["patient_id", "query"],
        }

    def _get_path(self) -> str:
        return "/search"

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "patient_id": kwargs.get("patient_id", ""),
            "query": kwargs.get("query", ""),
            "max_results": kwargs.get("max_results", 10),
        }

    def _parse_response(self, data: dict[str, Any]) -> HistorySearchOutput:
        """Parse history search response."""
        from datetime import datetime

        records = [
            HistoryRecord(
                date=datetime.fromisoformat(r["date"]) if r.get("date") else datetime.now(),
                record_type=r.get("record_type", "unknown"),
                summary=r.get("summary", ""),
                similarity_score=float(r.get("similarity_score", 0.5)),
                clinical_relevance=r.get("clinical_relevance", ""),
            )
            for r in data.get("relevant_records", [])
        ]

        return HistorySearchOutput(
            patient_id=data.get("patient_id", ""),
            relevant_records=records,
            timeline_context=data.get("timeline_context", "No context available"),
        )


# ═══════════════════════════════════════════════════════════════
#  Factory — create all HTTP tools from Settings
# ═══════════════════════════════════════════════════════════════


def register_http_tools(settings: Settings) -> dict[ToolName, BaseTool]:
    """Create HTTP-backed tool instances from application settings.

    Maps config endpoints to the correct tool implementation:
    - medgemma_4b_endpoint → image analysis
    - medgemma_27b_endpoint → text reasoning
    - hear_endpoint → audio analysis
    - medgemma_27b_endpoint → history search (RAG + LLM)
    """
    return {
        ToolName.IMAGE_ANALYSIS: HttpImageAnalysisTool(
            endpoint=settings.medgemma_4b_endpoint,
        ),
        ToolName.TEXT_REASONING: HttpTextReasoningTool(
            endpoint=settings.medgemma_27b_endpoint,
        ),
        ToolName.AUDIO_ANALYSIS: HttpAudioAnalysisTool(
            endpoint=settings.hear_endpoint,
        ),
        ToolName.HISTORY_SEARCH: HttpHistorySearchTool(
            endpoint=settings.medgemma_27b_endpoint,
        ),
    }
