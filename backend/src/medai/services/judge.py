"""Claude-based Judge Agent — validates consensus across specialist outputs.

Implements the Evaluator-Optimizer pattern from Anthropic's best practices.
Checks for contradictions, low confidence, missing context, and guideline adherence.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from anthropic import AsyncAnthropic

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

Respond with a JSON object matching this exact schema:
{{
    "verdict": "consensus" or "conflict",
    "confidence": float between 0.0 and 1.0,
    "reasoning": "Brief explanation of your judgment",
    "contradictions": ["list of contradictions found, empty if none"],
    "low_confidence_items": ["list of items below confidence threshold"],
    "missing_context": ["list of missing information that would improve analysis"],
    "requery_tools": ["tool names to re-run if verdict is conflict"]
}}

CRITICAL: Respond with ONLY the raw JSON object. Do NOT wrap it in markdown
code fences (```). Do NOT add any text before or after the JSON.
"""


class ClaudeJudge(BaseJudge):
    """Judge Agent powered by Claude.

    Evaluates specialist tool outputs for consistency and reliability.
    Returns CONSENSUS if all checks pass, CONFLICT if re-analysis is needed.
    """

    def __init__(self, client: AsyncAnthropic, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def evaluate(
        self,
        request: CaseAnalysisRequest,
        specialist_results: SpecialistResults,
    ) -> JudgmentResult:
        """Evaluate specialist results using Claude as judge."""
        # Serialize specialist results for Claude
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
            f"Evaluate these results for consensus or conflict. "
            f"Return your judgment as JSON."
        )

        logger.info("judge_evaluating", patient_id=request.patient_id)

        try:
            response = await self._client.messages.create(
                model=self._settings.orchestrator_model,
                max_tokens=self._settings.judge_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            # Parse Claude's response — strip markdown fences if present
            response_text = response.content[0].text.strip()  # type: ignore
            if response_text.startswith("```"):
                # Remove ```json ... ``` wrapper
                response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text[3:]
                response_text = response_text.rsplit("```", 1)[0].strip()
            judgment_data = json.loads(response_text)

            result = JudgmentResult(
                verdict=JudgeVerdict(judgment_data["verdict"]),
                confidence=judgment_data.get("confidence", 0.5),
                reasoning=judgment_data.get("reasoning", ""),
                contradictions=judgment_data.get("contradictions", []),
                low_confidence_items=judgment_data.get("low_confidence_items", []),
                missing_context=judgment_data.get("missing_context", []),
                requery_tools=[
                    ToolName(t) for t in judgment_data.get("requery_tools", [])
                ],
            )

            logger.info(
                "judge_verdict",
                verdict=result.verdict.value,
                confidence=result.confidence,
            )
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("judge_parse_error", error=str(e))
            # Fail-safe: if we can't parse judge output, default to consensus
            # but with low confidence so the doctor knows to review carefully
            return JudgmentResult(
                verdict=JudgeVerdict.CONSENSUS,
                confidence=0.5,
                reasoning=f"Judge evaluation encountered a parsing error: {e}. Defaulting to consensus with low confidence.",
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
