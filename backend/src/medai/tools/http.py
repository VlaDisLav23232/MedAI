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

import base64
import io
import mimetypes
import structlog
from pathlib import Path
from typing import Any

import httpx

from medai.config import Settings, get_settings
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

logger = structlog.get_logger()

# ── Modality normalization ────────────────────────────────────────

_MODALITY_ALIASES: dict[str, Modality] = {
    "chest x-ray": Modality.XRAY,
    "chest_xray": Modality.XRAY,
    "chest xray": Modality.XRAY,
    "x-ray": Modality.XRAY,
    "x ray": Modality.XRAY,
    "radiograph": Modality.XRAY,
    "ct scan": Modality.CT,
    "ct_scan": Modality.CT,
    "computed tomography": Modality.CT,
    "magnetic resonance": Modality.MRI,
    "mri scan": Modality.MRI,
    "ultrasound scan": Modality.ULTRASOUND,
    "us": Modality.ULTRASOUND,
    "sonography": Modality.ULTRASOUND,
    "fundoscopy": Modality.FUNDUS,
    "fundus photo": Modality.FUNDUS,
    "retinal": Modality.FUNDUS,
    "dermoscopy": Modality.DERMATOLOGY,
    "skin": Modality.DERMATOLOGY,
    "pathology": Modality.HISTOPATHOLOGY,
    "biopsy": Modality.HISTOPATHOLOGY,
    "histology": Modality.HISTOPATHOLOGY,
}


def _normalize_modality(raw: str) -> Modality:
    """Normalize free-text modality strings to the Modality enum.

    Handles common aliases like 'chest x-ray' → XRAY that models
    may produce despite the enum constraint in the tool schema.
    """
    lowered = raw.strip().lower()
    try:
        return Modality(lowered)
    except ValueError:
        match = _MODALITY_ALIASES.get(lowered)
        if match:
            return match
        logger.warning("unknown_modality_normalized", raw=raw, fallback="other")
        return Modality.OTHER


def _parse_inference_metadata(data: dict[str, Any]) -> InferenceMetadata | None:
    """Extract InferenceMetadata from a Modal response if present."""
    raw = data.get("inference")
    if not isinstance(raw, dict):
        return None
    try:
        return InferenceMetadata(
            model_id=raw.get("model_id", "unknown"),
            temperature=float(raw.get("temperature", 0.0)),
            token_count=int(raw.get("token_count", 0)),
            inference_time_ms=float(raw.get("inference_time_ms", 0.0)),
            sequence_fluency_score=raw.get("sequence_fluency_score"),
        )
    except (ValueError, TypeError):
        return None


def _clean_assessment_text(
    assessment: str,
    raw_output: str = "",
    reasoning_chain: list[dict[str, Any]] | None = None,
) -> str:
    """Extract clean natural-language assessment from MedGemma output.

    Handles several failure modes:
    1. Assessment is valid clean text → return as-is
    2. Assessment looks like raw JSON → try to parse and extract the
       actual "assessment" field from within
    3. Assessment is truncated JSON (max_tokens hit) → extract readable
       text from reasoning steps or raw output
    4. Assessment wrapped in markdown code fences → strip them
    """
    import json as _json

    if not assessment or assessment == "No assessment available":
        # Try raw_output if assessment was empty
        if raw_output:
            assessment = raw_output
        else:
            return "No assessment available"

    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    cleaned = assessment.strip()
    if cleaned.startswith("```"):
        # Remove first line (```json or ```)
        lines = cleaned.split("\n", 1)
        cleaned = lines[1] if len(lines) > 1 else cleaned
        if "```" in cleaned:
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    # Check if it looks like JSON (starts with { or [)
    if cleaned.startswith("{") or cleaned.startswith("["):
        # Try to parse as valid JSON first
        try:
            parsed = _json.loads(cleaned)
            if isinstance(parsed, dict):
                # Extract the assessment field from the parsed JSON
                inner_assessment = parsed.get("assessment", "")
                if inner_assessment and isinstance(inner_assessment, str):
                    return inner_assessment.strip()
                # If no assessment field, try to build from reasoning_chain
                inner_chain = parsed.get("reasoning_chain", [])
                if inner_chain:
                    thoughts = [
                        step.get("thought", "") for step in inner_chain
                        if isinstance(step, dict)
                    ]
                    return " ".join(t for t in thoughts if t).strip() or cleaned
        except _json.JSONDecodeError:
            # Truncated JSON — try partial extraction
            pass

        # Try regex extraction of "assessment": "..." from truncated JSON
        import re
        match = re.search(r'"assessment"\s*:\s*"((?:[^"\\]|\\.)*)(?:"|$)', cleaned)
        if match:
            extracted = match.group(1)
            # Unescape JSON string escapes
            try:
                extracted = _json.loads(f'"{extracted}"')
            except (ValueError, _json.JSONDecodeError):
                pass
            if extracted and len(extracted) > 20:
                return extracted.strip()

        # Fall back: extract readable text from reasoning chain
        if reasoning_chain:
            thoughts = [
                step.get("thought", "") for step in reasoning_chain
                if isinstance(step, dict) and step.get("thought")
            ]
            if thoughts:
                return " ".join(thoughts).strip()

        # Last resort: strip JSON punctuation and return readable portion
        readable = re.sub(r'[{}\[\]"\\]', ' ', cleaned)
        readable = re.sub(r'\s+', ' ', readable).strip()
        if len(readable) > 50:
            return readable[:2000]

    return cleaned


# ── Retry / timeout defaults ──────────────────────────────

DEFAULT_TIMEOUT = 300.0  # seconds (Modal cold starts can take 2-5 min)
MAX_RETRIES = 2
RETRY_BACKOFF = 2.0  # base seconds for exponential backoff

# ── Image pre-processing for inference ─────────────────────
# Models resize internally (SigLIP → 384², MedGemma → 448²).
# Sending a 4000×4000 DICOM as raw base64 wastes bandwidth and
# memory.  We downscale to MAX_INFERENCE_EDGE before encoding.
# Quality 85 JPEG is visually lossless for AI inference.

MAX_INFERENCE_EDGE = 512   # px — covers all current model input sizes
JPEG_QUALITY = 85          # good balance: ~10× smaller than PNG, minimal loss


def _resize_for_inference(raw_bytes: bytes, *, max_edge: int = MAX_INFERENCE_EDGE) -> tuple[bytes, str]:
    """Resize an image so its longest edge ≤ max_edge.

    Returns (jpeg_bytes, mime_type).  Falls back to original bytes
    if Pillow can't decode the image.
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw_bytes))

        # Convert palette / RGBA → RGB for JPEG encoding
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        # Only downscale, never upscale
        if max(img.size) > max_edge:
            img.thumbnail((max_edge, max_edge), Image.LANCZOS)
            logger.debug("image_resized_for_inference", original=img.size, target=max_edge)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning("image_resize_failed_using_original", error=str(e))
        mime = mimetypes.guess_type("img.jpg")[0] or "image/jpeg"
        return raw_bytes, mime


def _resolve_local_image_to_base64(image_url: str) -> str | None:
    """If image_url is a relative /storage/... path, read from disk,
    resize for inference, and return a data-URI base64 string.

    Returns None if the URL is external or the file doesn't exist.

    Production note: replace this with a signed S3/GCS URL approach —
    Modal fetches the image directly, no base64 in the payload at all.
    """
    if not image_url or not image_url.startswith("/storage/"):
        return None
    try:
        settings = get_settings()
        # /storage/uploads/xxx.jpg → ./storage/uploads/xxx.jpg
        relative = image_url.lstrip("/").removeprefix("storage/")
        local_path = settings.storage_local_path / relative
        if not local_path.exists():
            logger.warning("local_image_not_found", path=str(local_path))
            return None
        raw = local_path.read_bytes()
        resized, mime = _resize_for_inference(raw)
        logger.info(
            "local_image_resolved",
            url=image_url,
            original_kb=round(len(raw) / 1024, 1),
            resized_kb=round(len(resized) / 1024, 1),
        )
        return f"data:{mime};base64,{base64.b64encode(resized).decode()}"
    except Exception as e:
        logger.warning("local_image_read_failed", error=str(e))
        return None


def _resolve_local_audio_to_base64(audio_url: str) -> str | None:
    """Read a local /storage/ audio file and return as base64 data URI."""
    if not audio_url or not audio_url.startswith("/storage/"):
        return None
    try:
        settings = get_settings()
        relative = audio_url.lstrip("/").removeprefix("storage/")
        local_path = settings.storage_local_path / relative
        if not local_path.exists():
            logger.warning("local_audio_not_found", path=str(local_path))
            return None
        raw = local_path.read_bytes()
        # Guess MIME type from extension
        ext = local_path.suffix.lower()
        mime_map = {
            ".ogg": "audio/ogg", ".mp3": "audio/mpeg", ".wav": "audio/wav",
            ".m4a": "audio/mp4", ".flac": "audio/flac", ".webm": "audio/webm",
            ".aac": "audio/aac", ".wma": "audio/x-ms-wma",
        }
        mime = mime_map.get(ext, "audio/ogg")
        logger.info(
            "local_audio_resolved",
            url=audio_url,
            size_kb=round(len(raw) / 1024, 1),
            mime=mime,
        )
        return f"data:{mime};base64,{base64.b64encode(raw).decode()}"
    except Exception as e:
        logger.warning("local_audio_read_failed", error=str(e))
        return None


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
        """Call the remote endpoint with retry + structured parsing.

        Automatically resolves local /storage/... image paths to base64
        so Modal endpoints can access them.
        """
        # Resolve local storage paths → base64 for remote endpoints
        image_url = kwargs.get("image_url", "")
        if image_url and image_url.startswith("/storage/"):
            b64 = _resolve_local_image_to_base64(image_url)
            if b64:
                kwargs["image_base64"] = b64
                logger.info("local_image_resolved_to_base64", url=image_url)

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
                # Log response body for debugging (Modal returns helpful error messages)
                body_preview = ""
                try:
                    body_preview = e.response.text[:300]
                except Exception:
                    pass
                logger.warning(
                    "tool_http_error",
                    tool=self.name.value,
                    attempt=attempt + 1,
                    status=e.response.status_code,
                    url=url,
                    body=body_preview,
                )
                # Don't retry 4xx client errors (except 408 Request Timeout and 429 Rate Limit)
                if 400 <= e.response.status_code < 500 and e.response.status_code not in (408, 429):
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

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "image_url": kwargs.get("image_url", ""),
            "clinical_context": kwargs.get("clinical_context", ""),
            "modality_hint": kwargs.get("modality_hint", "other"),
        }
        # Forward base64 image if resolved from local storage
        image_base64 = kwargs.get("image_base64", "")
        if image_base64:
            payload["image_base64"] = image_base64
        return payload

    def _parse_response(self, data: dict[str, Any]) -> ImageAnalysisOutput:
        """Parse MedGemma image analysis response into structured output."""
        inference = _parse_inference_metadata(data)
        logprob_score = data.get("logprob_confidence")

        findings = [
            Finding(
                finding=f.get("finding", "Unknown finding"),
                confidence=float(f.get("confidence", 0.5)),
                explanation=f.get("explanation", ""),
                severity=Severity(f.get("severity", "none")),
                metadata={
                    k: v for k, v in {
                        "sequence_fluency_score": f.get("logprob_confidence", logprob_score),
                        "model_self_reported_confidence": f.get("model_self_reported_confidence"),
                        "confidence_note": (
                            "confidence is model self-reported (not calibrated); "
                            "sequence_fluency_score is token-level predictability (not clinical accuracy)"
                        ),
                    }.items() if v is not None
                },
            )
            for f in data.get("findings", [])
        ]

        return ImageAnalysisOutput(
            modality_detected=_normalize_modality(data.get("modality_detected", "other")),
            findings=findings,
            attention_heatmap_url=data.get("attention_heatmap_url"),
            embedding_id=data.get("embedding_id"),
            differential_diagnoses=data.get("differential_diagnoses", []),
            recommended_followup=data.get("recommended_followup", []),
            inference=inference,
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
            "additionalProperties": False,
        }

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "patient_history": kwargs.get("patient_history", ""),
            "lab_results": kwargs.get("lab_results", ""),
            "clinical_context": kwargs.get("clinical_context", ""),
            "imaging_findings": kwargs.get("imaging_findings", ""),
        }

    def _parse_response(self, data: dict[str, Any]) -> TextReasoningOutput:
        """Parse MedGemma text reasoning response.

        Handles multiple failure modes from the Modal endpoint:
        - Properly parsed JSON with clean assessment text
        - JSON parsing failed on Modal → raw_output present, assessment is raw text
        - Truncated JSON from model hitting max_new_tokens limit
        """
        from datetime import datetime

        inference = _parse_inference_metadata(data)

        def _safe_parse_date(raw: str | None) -> datetime | None:
            """Parse date strings robustly — MedGemma may return
            free-text dates like 'Feb 2026' instead of ISO format."""
            if not raw:
                return None
            # 1. Try ISO format first (fast path)
            try:
                return datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                pass
            # 2. Try common informal formats MedGemma produces
            from dateutil import parser as dateutil_parser
            try:
                return dateutil_parser.parse(raw, fuzzy=True)
            except Exception:
                pass
            # 3. Give up gracefully — never crash the whole tool
            logger.debug("unparseable_date_skipped", raw=raw)
            return None

        evidence = [
            EvidenceCitation(
                source=c.get("source", "unknown"),
                source_type=c.get("source_type", "unknown"),
                relevant_excerpt=c.get("relevant_excerpt", ""),
                date=_safe_parse_date(c.get("date")),
            )
            for c in data.get("evidence_citations", [])
        ]

        confidence = float(data.get("confidence", 0.5))
        reasoning_chain = data.get("reasoning_chain", [])

        # ── Robust assessment extraction ──────────────────
        # MedGemma 27B sometimes returns the whole JSON response as
        # `assessment` when the Modal endpoint can't parse JSON (e.g.
        # model output truncated by max_new_tokens).  Detect and fix.
        assessment = data.get("assessment", "No assessment available")
        raw_output = data.get("raw_output", "")

        assessment = _clean_assessment_text(assessment, raw_output, reasoning_chain)

        return TextReasoningOutput(
            reasoning_chain=reasoning_chain,
            assessment=assessment,
            confidence=confidence,
            evidence_citations=evidence,
            plan_suggestions=data.get("plan_suggestions", []),
            contraindication_flags=data.get("contraindication_flags", []),
            inference=inference,
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
            "additionalProperties": False,
        }

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "audio_url": kwargs.get("audio_url", ""),
            "audio_type": kwargs.get("audio_type", "breathing"),
            "clinical_context": kwargs.get("clinical_context", ""),
        }
        audio_base64 = kwargs.get("audio_base64", "")
        if audio_base64:
            payload["audio_base64"] = audio_base64
        return payload

    async def execute(self, **kwargs: Any) -> ToolOutput:
        """Override to resolve local audio files to base64."""
        audio_url = kwargs.get("audio_url", "")
        if audio_url and audio_url.startswith("/storage/"):
            b64 = _resolve_local_audio_to_base64(audio_url)
            if b64:
                kwargs["audio_base64"] = b64
                logger.info("local_audio_resolved_to_base64", url=audio_url)
        return await super().execute(**kwargs)

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
            "additionalProperties": False,
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

        def _safe_parse_date_hs(raw: str | None) -> datetime:
            """Robust date parsing for history records."""
            if not raw:
                return datetime.now()
            try:
                return datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                pass
            from dateutil import parser as dateutil_parser
            try:
                return dateutil_parser.parse(raw, fuzzy=True)
            except Exception:
                return datetime.now()

        records = [
            HistoryRecord(
                date=_safe_parse_date_hs(r.get("date")),
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
#  HttpSigLipTool (Image Explainability)
# ═══════════════════════════════════════════════════════════════

# Taxonomy loader — cached after first load
_taxonomy_cache: dict[str, list[str]] | None = None


def _load_taxonomy(taxonomy_path: str | None = None) -> dict[str, list[str]]:
    """Load per-modality condition labels from JSON taxonomy file.

    Cached after first call. Falls back to minimal defaults if file missing.
    """
    global _taxonomy_cache
    if _taxonomy_cache is not None:
        return _taxonomy_cache

    import json
    from pathlib import Path

    if taxonomy_path is None:
        taxonomy_path = str(Path(__file__).parent / "condition_taxonomy.json")

    try:
        with open(taxonomy_path) as f:
            data = json.load(f)
        # Filter out _meta key
        _taxonomy_cache = {k: v for k, v in data.items() if not k.startswith("_")}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning("taxonomy_load_failed", path=taxonomy_path, error=str(e))
        _taxonomy_cache = {
            "other": ["abnormality or lesion", "normal anatomy"],
        }

    return _taxonomy_cache


class HttpSigLipTool(_HttpToolBase):
    """Calls SigLIP endpoint for zero-shot medical image explainability.

    Produces per-condition sigmoid probabilities (real contrastive scores,
    not LLM-generated) and spatial activation heatmaps. Each heatmap is a
    pure activation map — no original image overlay.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        taxonomy_path: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        super().__init__(endpoint, timeout=timeout, max_retries=max_retries)
        self._taxonomy_path = taxonomy_path

    @property
    def name(self) -> ToolName:
        return ToolName.IMAGE_EXPLAINABILITY

    @property
    def description(self) -> str:
        return (
            "Generate visual explainability heatmaps for medical images using "
            "zero-shot classification. Returns per-condition similarity probabilities "
            "(real sigmoid scores, not LLM-generated) and spatial activation maps. "
            "IMPORTANT: You MUST provide case-specific condition_labels tailored to the "
            "body part and clinical question (e.g. for a hand X-ray: 'phalangeal fracture', "
            "'joint dislocation', 'soft tissue swelling'). Also set the correct modality_hint."
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
                    "description": (
                        "REQUIRED: Case-specific condition labels to score against. "
                        "Provide 5-10 descriptive clinical phrases relevant to the "
                        "body part and clinical question. Examples for hand X-ray: "
                        "['phalangeal fracture', 'metacarpal fracture', 'joint dislocation', "
                        "'normal bone alignment']. Do NOT rely on defaults."
                    ),
                },
            },
            "required": ["image_url"],
            "additionalProperties": False,
        }

    def _build_request_payload(self, **kwargs: Any) -> dict[str, Any]:
        """Build request with taxonomy-based labels + optional overrides."""
        modality_hint = kwargs.get("modality_hint", "other")

        # Load taxonomy labels for this modality
        taxonomy = _load_taxonomy(self._taxonomy_path)
        default_labels = taxonomy.get(modality_hint, taxonomy.get("other", []))

        # Request-provided labels override OR extend defaults
        custom_labels = kwargs.get("condition_labels")
        if custom_labels and isinstance(custom_labels, list) and len(custom_labels) > 0:
            labels = custom_labels
        else:
            labels = default_labels

        payload: dict[str, Any] = {
            "image_url": kwargs.get("image_url", ""),
            "condition_labels": labels,
            "modality_hint": modality_hint,
            "return_embedding": False,
            "top_k_heatmaps": 5,
        }

        # Forward base64 image if provided (avoids remote fetch failures)
        image_base64 = kwargs.get("image_base64", "")
        if image_base64:
            payload["image_base64"] = image_base64

        return payload

    def _parse_response(self, data: dict[str, Any]) -> ImageExplainabilityOutput:
        """Parse SigLIP explainability response into structured output."""
        modality_hint = data.get("modality_hint", "other")

        # Build condition scores from response
        condition_scores = []
        # Map label→heatmap for lookup
        heatmap_map: dict[str, str] = {}
        for hm in data.get("heatmaps", []):
            b64 = hm.get("heatmap_base64", "")
            if b64:
                heatmap_map[hm["label"]] = f"data:image/png;base64,{b64}"

        for score_entry in data.get("scores", []):
            label = score_entry.get("label", "")
            prob = float(score_entry.get("probability", 0.0))
            sigmoid = score_entry.get("sigmoid_score")
            logit = score_entry.get("raw_logit")
            condition_scores.append(ConditionScore(
                label=label,
                probability=prob,
                sigmoid_score=float(sigmoid) if sigmoid is not None else None,
                raw_logit=float(logit) if logit is not None else None,
                heatmap_data_uri=heatmap_map.get(label),
            ))

        # Top-scoring condition's heatmap → attention_heatmap_url
        # (triggers auto-extraction in cases.py)
        top_heatmap_url = None
        if condition_scores:
            top = max(condition_scores, key=lambda c: c.probability)
            top_heatmap_url = top.heatmap_data_uri

        # Image embedding — omitted from reports to save space
        embedding = None

        # Inference metadata
        inference = None
        model_id = data.get("model_id")
        inference_ms = data.get("inference_time_ms")
        if model_id:
            inference = InferenceMetadata(
                model_id=model_id,
                temperature=0.0,  # deterministic forward pass
                token_count=0,    # not a generative model
                inference_time_ms=float(inference_ms) if inference_ms else 0.0,
            )

        return ImageExplainabilityOutput(
            modality_detected=_normalize_modality(modality_hint),
            condition_scores=condition_scores,
            attention_heatmap_url=top_heatmap_url,
            embedding=embedding,
            inference=inference,
        )


# ═══════════════════════════════════════════════════════════════
#  Factory — create all HTTP tools from Settings
# ═══════════════════════════════════════════════════════════════


def register_http_tools(settings: Settings) -> dict[ToolName, BaseTool]:
    """Create HTTP-backed tool instances from application settings.

    Maps config endpoints to the correct tool implementation:
    - medgemma_4b_endpoint → image analysis
    - medgemma_27b_endpoint → text reasoning (skipped if enable_27b_reasoning=False)
    - hear_endpoint → audio analysis
    - medgemma_27b_endpoint → history search (RAG + LLM)
    - medsiglip_endpoint → image explainability (SigLIP)
    """
    tools: dict[ToolName, BaseTool] = {
        ToolName.IMAGE_ANALYSIS: HttpImageAnalysisTool(
            endpoint=settings.medgemma_4b_endpoint,
        ),
        ToolName.AUDIO_ANALYSIS: HttpAudioAnalysisTool(
            endpoint=settings.hear_endpoint,
        ),
        ToolName.HISTORY_SEARCH: HttpHistorySearchTool(
            endpoint=settings.medgemma_27b_endpoint,
        ),
        ToolName.IMAGE_EXPLAINABILITY: HttpSigLipTool(
            endpoint=settings.medsiglip_endpoint,
            taxonomy_path=str(settings.siglip_taxonomy_path),
        ),
    }

    if settings.enable_27b_reasoning:
        tools[ToolName.TEXT_REASONING] = HttpTextReasoningTool(
            endpoint=settings.medgemma_27b_endpoint,
        )
    else:
        logger.info("⏭️  TEXT_REASONING_DISABLED (enable_27b_reasoning=false)")

    return tools
