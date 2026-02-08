"""Claude-based Judge Agent — validates consensus across specialist outputs.

Implements the Evaluator-Optimizer pattern from Anthropic's best practices.
Checks for contradictions, low confidence, missing context, and guideline adherence.

Uses Anthropic Structured Outputs (output_config with json_schema) for guaranteed
valid JSON via constrained decoding — no manual parsing or fence stripping needed.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

import structlog
from anthropic import AsyncAnthropic, transform_schema
from pydantic import BaseModel, Field

from medai.config import Settings
from medai.domain.entities import (
    JudgmentResult,
    JudgeVerdict,
    SpecialistResults,
    ToolName,
)
from medai.domain.interfaces import BaseJudge
from medai.domain.schemas import CaseAnalysisRequest

logger = structlog.get_logger()


# ── Structured Output Schema ──────────────────────────────
# Pydantic model used by Anthropic's constrained decoding.
# Maps 1:1 to JudgmentResult but uses simple types that the
# JSON schema constrained decoder handles reliably.

class JudgmentResponse(BaseModel):
    """Schema for Claude's structured judge output.

    This is the contract between the Judge prompt and the JSON
    schema constrained decoder. Kept separate from JudgmentResult
    (domain entity) so we can evolve them independently.
    """
    verdict: Literal["consensus", "conflict"]
    confidence: float = Field(ge=0.0, le=1.0, description="How confident you are in the verdict")
    reasoning: str = Field(description="Brief explanation of your judgment")
    contradictions: list[str] = Field(default_factory=list, description="Contradictions found between specialist outputs")
    low_confidence_items: list[str] = Field(default_factory=list, description="Items with confidence below threshold")
    missing_context: list[str] = Field(default_factory=list, description="Missing information that would improve analysis")
    requery_tools: list[Literal["image_analysis", "text_reasoning", "audio_analysis", "history_search"]] = Field(
        default_factory=list,
        description="Tool names to re-run if verdict is conflict",
    )


# Pre-compute the JSON schema once at module load
_JUDGMENT_SCHEMA = transform_schema(JudgmentResponse)


JUDGE_SYSTEM_PROMPT = """\
You are a Senior Medical AI Judge. Your role is to evaluate the outputs of multiple \
specialist AI tools that have analyzed a patient case, and determine whether there \
is consensus or conflict.

You must evaluate:
1. CROSS-MODAL CONSISTENCY: Do image findings align with text reasoning and audio analysis?
2. CONFIDENCE LEVELS: Flag any finding with confidence below {confidence_threshold}.
3. HISTORICAL CONSISTENCY: Do current findings make sense given the patient timeline?
4. GUIDELINE ADHERENCE: Does the suggested plan follow standard clinical guidelines?

IMPORTANT: You are NOT diagnosing the patient. You are judging whether the specialist \
tools agree with each other and whether the combined output is reliable enough to \
present to the doctor.
"""


class ClaudeJudge(BaseJudge):
    """Judge Agent powered by Claude with Structured Outputs.

    Uses Anthropic's `output_config` with `json_schema` for guaranteed
    valid JSON via constrained decoding. No manual JSON parsing needed —
    the API enforces the schema at generation time.
    """

    def __init__(self, client: AsyncAnthropic, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def evaluate(
        self,
        request: CaseAnalysisRequest,
        specialist_results: SpecialistResults,
    ) -> JudgmentResult:
        """Evaluate specialist results using Claude as judge with structured output."""
        results_text = self._format_results(specialist_results)

        system_prompt = JUDGE_SYSTEM_PROMPT.format(
            confidence_threshold=self._settings.confidence_threshold,
        )

        user_message = (
            f"## Case Context\n"
            f"Patient ID: {request.patient_id}\n"
            f"Doctor's Query: {request.doctor_query}\n"
            f"Clinical Context: {request.clinical_context}\n\n"
            f"## Specialist Tool Results\n{results_text}\n\n"
            f"## Your Task\n"
            f"Evaluate these results for consensus or conflict."
        )

        logger.info("judge_evaluating", patient_id=request.patient_id)

        try:
            # Use Anthropic Structured Outputs — guaranteed valid JSON
            response = await self._client.messages.create(
                model=self._settings.orchestrator_model,
                max_tokens=self._settings.judge_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": _JUDGMENT_SCHEMA,
                    }
                },
            )

            # Structured output guarantees valid JSON — parse directly
            judgment = JudgmentResponse.model_validate_json(
                response.content[0].text  # type: ignore
            )

            result = JudgmentResult(
                verdict=JudgeVerdict(judgment.verdict),
                confidence=judgment.confidence,
                reasoning=judgment.reasoning,
                contradictions=judgment.contradictions,
                low_confidence_items=judgment.low_confidence_items,
                missing_context=judgment.missing_context,
                requery_tools=[ToolName(t) for t in judgment.requery_tools],
            )

            logger.info(
                "judge_verdict",
                verdict=result.verdict.value,
                confidence=result.confidence,
            )
            return result

        except Exception as e:
            logger.error("judge_evaluation_error", error=str(e))
            # Fail-safe: if anything goes wrong, default to consensus
            # with low confidence so the doctor knows to review carefully
            return JudgmentResult(
                verdict=JudgeVerdict.CONSENSUS,
                confidence=0.5,
                reasoning=f"Judge evaluation error: {e}. Defaulting to consensus with low confidence.",
                contradictions=[],
                low_confidence_items=["Judge output could not be parsed"],
                missing_context=[],
                requery_tools=[],
            )

    def _format_results(self, results: SpecialistResults) -> str:
        """Format specialist results as readable text for Claude."""
        sections = []
        for tool_name, output in results.results.items():
            if tool_name.startswith("_"):
                # Internal entries like _synthesis are plain strings
                sections.append(f"### {tool_name}\n{output}")
            elif hasattr(output, "model_dump_json"):
                sections.append(f"### {tool_name}\n```json\n{output.model_dump_json(indent=2)}\n```")
            else:
                sections.append(f"### {tool_name}\n{output}")
        for tool_name, error in results.errors.items():
            sections.append(f"### {tool_name} (ERROR)\n{error}")
        return "\n\n".join(sections)


class MockJudge(BaseJudge):
    """Mock judge for testing — always returns consensus."""

    async def evaluate(
        self,
        request: CaseAnalysisRequest,
        specialist_results: SpecialistResults,
    ) -> JudgmentResult:
        return JudgmentResult(
            verdict=JudgeVerdict.CONSENSUS,
            confidence=0.85,
            reasoning="Mock judge: all specialist outputs are consistent and above confidence threshold.",
            contradictions=[],
            low_confidence_items=[],
            missing_context=[],
            requery_tools=[],
        )
