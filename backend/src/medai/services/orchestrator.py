"""Claude-based Orchestrator — the brain of the agentic system.

Implements the Orchestrator-Workers pattern:
1. ROUTE: Classify the case → decide which tools are needed
2. DISPATCH: Call tools in parallel
3. COLLECT: Gather structured results
4. JUDGE: Validate consensus (delegate to Judge agent)
5. REPORT: Generate final structured report

Uses Anthropic's tool-use API with parallel tool calls.
Structured logging tracks each phase with timing for demo observability.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from anthropic.types import Message, ContentBlock, ToolUseBlock, TextBlock

from medai.config import Settings
from medai.domain.entities import (
    ConfidenceMethod,
    Finding,
    FinalReport,
    JudgmentResult,
    JudgeVerdict,
    PipelineMetrics,
    SpecialistResults,
    ToolName,
    ToolOutput,
)
from medai.domain.interfaces import BaseJudge, BaseOrchestrator
from medai.domain.schemas import CaseAnalysisRequest
from medai.services.tool_registry import ToolRegistry

logger = structlog.get_logger()

# ── Helpers ────────────────────────────────────────────────

# Matches data:image/...;base64,<long_base64>  inside JSON string values.
_BASE64_DATA_URI_RE = re.compile(
    r'"data:image/[^;]+;base64,[A-Za-z0-9+/=]+"'
)


def _strip_base64_data_uris(content: str) -> str:
    """Replace base64 data URIs with a placeholder to save tokens.

    The full binary data is preserved in ``SpecialistResults`` for
    heatmap extraction in ``cases.py``.  Only the serialised text
    sent back to Claude is trimmed.
    """
    return _BASE64_DATA_URI_RE.sub('"[base64_image_data_stripped]"', content)


ORCHESTRATOR_SYSTEM_PROMPT = """\
You are a medical AI orchestrator. A doctor has submitted a patient case for analysis.

Your job is to decide which specialist tools to invoke based on the case data, \
then use those tools to gather information. You have access to the following tools:

{tool_descriptions}

RULES:
1. Always use history_search if a patient_id is provided — past context is critical.
2. Use image_analysis for any provided medical images.
3. Use text_reasoning when patient history, lab results, or complex clinical questions are present.
4. Use audio_analysis only when audio recordings are provided.
5. You may call DIFFERENT tools in parallel (one image_analysis + one history_search, etc.).
5b. Use image_explainability alongside image_analysis when medical images are provided — \
it generates spatial heatmaps showing which regions triggered each finding. Call both in parallel.
6. NEVER call the same tool more than once per turn. One call per tool name per iteration.
7. Call text_reasoning ONCE with all available context — do NOT split into multiple calls.
8. After receiving all tool results, synthesize a BRIEF final diagnosis (under 300 words).

HISTORY INTEGRATION RULES (CRITICAL):
- When history_search returns prior records, you MUST consider them in your synthesis.
- Chronic or recurring conditions found in history (e.g. chronic cough, COPD, diabetes,
  recurring infections) MUST influence the final diagnosis, plan, and confidence.
- Prior AI reports with doctor-approved diagnoses carry strong evidentiary weight.
- If history reveals a known chronic condition that explains current symptoms,
  note that the condition is chronic/recurring rather than treating it as a new finding.
- If history shows prior treatments or medications, ensure the plan accounts for them
  (e.g. do not suggest a medication the patient is already on, or note drug interactions).
- Compare current findings with historical baselines (lab values, imaging) to identify
  trends (improving, worsening, new onset).

Be thorough but efficient. The doctor is waiting.
"""


class ClaudeOrchestrator(BaseOrchestrator):
    """Production orchestrator using Claude's tool-use API.

    Handles the full pipeline: route → dispatch → collect → judge → report.
    Supports parallel tool invocation and judgment cycles.
    """

    def __init__(
        self,
        client: AsyncAnthropic,
        settings: Settings,
        tool_registry: ToolRegistry,
        judge: BaseJudge,
    ) -> None:
        self._client = client
        self._settings = settings
        self._registry = tool_registry
        self._judge = judge

    async def analyze_case(self, request: CaseAnalysisRequest) -> FinalReport:
        """Full case analysis pipeline with phase timing."""
        pipeline_start = time.monotonic()
        self._tool_timings: dict[str, float] = {}  # tool_name → elapsed_s

        logger.info(
            "📋 PIPELINE_START",
            patient_id=request.patient_id,
            has_images=bool(request.image_urls),
            has_audio=bool(request.audio_urls),
            phase="START",
        )

        # Build tool definitions for Claude
        tool_definitions = self._registry.get_claude_tool_definitions()

        # Build the user message with all case data
        user_content = self._build_user_message(request)

        system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
            tool_descriptions=self._format_tool_descriptions(),
        )

        # ── Phase 1-3: ROUTE → DISPATCH → COLLECT ──
        t0 = time.monotonic()
        logger.info("🔀 PHASE: ROUTE → DISPATCH → COLLECT", phase="TOOLS")

        specialist_results = await self._run_tool_loop(
            system_prompt=system_prompt,
            user_content=user_content,
            tool_definitions=tool_definitions,
        )

        tools_elapsed = time.monotonic() - t0
        logger.info(
            "✅ TOOLS_COMPLETE",
            phase="TOOLS",
            elapsed_s=round(tools_elapsed, 1),
            successful=list(specialist_results.results.keys()),
            errors=list(specialist_results.errors.keys()),
        )

        # ── Phase 4: JUDGE ──
        t0 = time.monotonic()
        logger.info("⚖️  PHASE: JUDGE", phase="JUDGE")

        if not self._settings.judge_enabled:
            logger.info("⏭️  JUDGE_SKIPPED (judge_enabled=false)", phase="JUDGE")
            judgment = JudgmentResult(
                verdict=JudgeVerdict.CONSENSUS,
                confidence=0.7,
                reasoning="Judge disabled by configuration — returning default consensus.",
                contradictions=[],
                low_confidence_items=[],
                missing_context=[],
                requery_tools=[],
            )
        else:
            judgment = await self._judge.evaluate(request, specialist_results)

        # ── Phase 4b: Re-query if conflict ──
        cycle = 0
        # Track which tools already produced a valid result — never re-run them
        _succeeded_tools = set(specialist_results.results.keys())
        while (
            self._settings.judge_enabled
            and judgment.verdict == JudgeVerdict.CONFLICT
            and judgment.requery_tools
            and cycle < self._settings.max_judgment_cycles
        ):
            cycle += 1
            # Filter out tools that already succeeded — only re-run failures
            requery_needed = [
                t for t in judgment.requery_tools
                if t.value not in _succeeded_tools
            ]
            if not requery_needed:
                logger.info(
                    "⏭️  REQUERY_SKIPPED — all requested tools already succeeded",
                    phase="JUDGE",
                    cycle=cycle,
                    requested=[t.value for t in judgment.requery_tools],
                )
                break

            logger.info(
                "🔄 REQUERY_CYCLE",
                phase="JUDGE",
                cycle=cycle,
                tools=[t.value for t in requery_needed],
                skipped=[t.value for t in judgment.requery_tools if t not in requery_needed],
            )

            additional_results = await self.dispatch_tools(
                tool_names=requery_needed,
                tool_inputs={
                    tool: self._build_requery_input(tool, request, specialist_results)
                    for tool in requery_needed
                },
            )
            specialist_results.results.update(additional_results.results)
            specialist_results.errors.update(additional_results.errors)
            _succeeded_tools.update(additional_results.results.keys())

            judgment = await self._judge.evaluate(request, specialist_results)

        judge_elapsed = time.monotonic() - t0
        logger.info(
            "✅ JUDGE_COMPLETE",
            phase="JUDGE",
            elapsed_s=round(judge_elapsed, 1),
            verdict=judgment.verdict.value,
            confidence=judgment.confidence,
            requery_cycles=cycle,
        )

        # ── Phase 5: REPORT ──
        t0 = time.monotonic()
        logger.info("📝 PHASE: REPORT", phase="REPORT")

        report = await self._generate_report(request, specialist_results, judgment)

        report_elapsed = time.monotonic() - t0
        total_elapsed = time.monotonic() - pipeline_start

        # Build real pipeline metrics
        metrics = PipelineMetrics(
            tools_s=round(tools_elapsed, 1),
            judge_s=round(judge_elapsed, 1),
            report_s=round(report_elapsed, 1),
            total_s=round(total_elapsed, 1),
            tool_timings=dict(self._tool_timings),
            requery_cycles=cycle,
            tools_called=list(specialist_results.results.keys()),
            tools_failed=list(specialist_results.errors.keys()),
        )
        report.pipeline_metrics = metrics

        logger.info(
            "🏁 PIPELINE_COMPLETE",
            phase="DONE",
            report_id=report.id,
            diagnosis=report.diagnosis[:100],
            confidence=report.confidence,
            findings_count=len(report.findings),
            plan_items=len(report.plan),
            timing=metrics.model_dump(),
        )

        return report

    async def dispatch_tools(
        self,
        tool_names: list[ToolName],
        tool_inputs: dict[ToolName, dict[str, Any]],
    ) -> SpecialistResults:
        """Dispatch multiple tools in parallel."""
        results = SpecialistResults()

        async def _run_tool(name: ToolName) -> tuple[ToolName, ToolOutput | None, str | None]:
            tool = self._registry.get(name)
            if tool is None:
                return name, None, f"Tool '{name.value}' not registered"
            try:
                output = await tool.execute(**tool_inputs.get(name, {}))
                return name, output, None
            except Exception as e:
                logger.error("tool_execution_error", tool=name.value, error=str(e))
                return name, None, str(e)

        # Run all tools concurrently
        tasks = [_run_tool(name) for name in tool_names]
        outcomes = await asyncio.gather(*tasks, return_exceptions=False)

        for name, output, error in outcomes:
            if output is not None:
                results.results[name.value] = output
            if error is not None:
                results.errors[name.value] = error

        return results

    async def _run_tool_loop(
        self,
        system_prompt: str,
        user_content: str,
        tool_definitions: list[dict],
    ) -> SpecialistResults:
        """Run the Claude tool-use loop: Claude decides → we execute → results back.

        This implements the agentic loop described in Anthropic docs.
        """
        results = SpecialistResults()
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_content},
        ]

        # Loop: Claude may request tools multiple times
        max_iterations = 5  # safety guard
        for iteration in range(max_iterations):
            response: Message = await self._client.messages.create(
                model=self._settings.orchestrator_model,
                max_tokens=self._settings.orchestrator_max_tokens,
                system=system_prompt,
                tools=tool_definitions,  # type: ignore
                messages=messages,
            )

            logger.debug(
                "orchestrator_response",
                stop_reason=response.stop_reason,
                content_blocks=len(response.content),
            )

            # ── Guard: max_tokens means Claude was cut off ──
            if response.stop_reason == "max_tokens":
                logger.warning(
                    "⚠️ RESPONSE_TRUNCATED",
                    phase="TOOLS",
                    iteration=iteration,
                    content_blocks=len(response.content),
                )
                # Still try to process any complete tool_use blocks below

            # If Claude is done (no more tool calls), break
            if response.stop_reason == "end_turn":
                # Extract any final text as synthesis
                for block in response.content:
                    if isinstance(block, TextBlock):
                        results.results["_synthesis"] = block.text  # type: ignore
                break

            # Process tool calls
            tool_calls = [b for b in response.content if isinstance(b, ToolUseBlock)]
            if not tool_calls:
                break

            # ── Deduplicate: keep only the FIRST call per tool name ──
            # Claude API requires a tool_result for every tool_use ID.
            # For duplicates, we execute the first and re-send its result
            # for subsequent IDs of the same tool — no stubs, no fakes.
            seen_tools: dict[str, ToolUseBlock] = {}  # name → first block
            unique_calls: list[ToolUseBlock] = []
            duplicate_map: dict[str, str] = {}  # dropped_id → first_id
            for tc in tool_calls:
                if tc.name not in seen_tools:
                    seen_tools[tc.name] = tc
                    unique_calls.append(tc)
                else:
                    duplicate_map[tc.id] = seen_tools[tc.name].id
                    logger.warning(
                        "🚫 DUPLICATE_TOOL_CALL_DROPPED",
                        tool=tc.name,
                        iteration=iteration,
                        duplicate_of=seen_tools[tc.name].id,
                    )
            if duplicate_map:
                logger.info(
                    "🔧 TOOL_DEDUP",
                    original=len(tool_calls),
                    after_dedup=len(unique_calls),
                    dropped=len(duplicate_map),
                )

            # Add assistant's response to conversation
            messages.append({"role": "assistant", "content": response.content})  # type: ignore

            # Execute only unique tool calls
            tool_results = await self._execute_tool_calls(unique_calls, results)

            # For duplicates, copy the real result from the first execution
            # so Claude gets identical data — no stubs, no fakes.
            first_id_to_content: dict[str, str] = {
                tr["tool_use_id"]: tr["content"]
                for tr in tool_results
            }
            for dropped_id, first_id in duplicate_map.items():
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": dropped_id,
                    "content": first_id_to_content.get(first_id, "{}"),
                })

            # Add tool results back to conversation
            messages.append({"role": "user", "content": tool_results})

        return results

    async def _execute_tool_calls(
        self,
        tool_calls: list[ToolUseBlock],
        results: SpecialistResults,
    ) -> list[dict[str, Any]]:
        """Execute tool calls from Claude in parallel with per-tool timing."""

        async def _run_one(tool_call: ToolUseBlock) -> dict[str, Any]:
            tool_name_str = tool_call.name
            tool_input = tool_call.input  # type: ignore
            t0 = time.monotonic()

            logger.info(
                "🔧 TOOL_DISPATCH",
                tool=tool_name_str,
                input_keys=list(tool_input.keys()) if isinstance(tool_input, dict) else [],
            )

            try:
                tool_name = ToolName(tool_name_str)
                tool = self._registry.get_required(tool_name)
                output = await tool.execute(**tool_input if isinstance(tool_input, dict) else {})

                elapsed = time.monotonic() - t0
                results.results[tool_name_str] = output
                self._tool_timings[tool_name_str] = round(elapsed, 2)

                logger.info(
                    "✅ TOOL_COMPLETE",
                    tool=tool_name_str,
                    elapsed_s=round(elapsed, 1),
                )

                content = output.model_dump_json() if hasattr(output, "model_dump_json") else json.dumps(output)
                # Strip base64 data URIs to avoid blowing up the Claude
                # context window. The full data is preserved in results
                # for heatmap extraction in cases.py.
                content = _strip_base64_data_uris(content)
                return {
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": content,
                }

            except Exception as e:
                elapsed = time.monotonic() - t0
                self._tool_timings[tool_name_str] = round(elapsed, 2)
                logger.error(
                    "❌ TOOL_FAILED",
                    tool=tool_name_str,
                    elapsed_s=round(elapsed, 1),
                    error=str(e),
                )
                results.errors[tool_name_str] = str(e)
                return {
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps({"error": str(e)}),
                    "is_error": True,
                }

        # Run all tool calls concurrently
        tool_result_blocks = await asyncio.gather(*[_run_one(tc) for tc in tool_calls])
        return list(tool_result_blocks)

    async def _generate_report(
        self,
        request: CaseAnalysisRequest,
        specialist_results: SpecialistResults,
        judgment: Any,
    ) -> FinalReport:
        """Generate the final structured report from specialist results.

        History context is merged into the evidence summary and timeline
        impact so that chronic conditions, prior treatments, and
        longitudinal trends are visible in the final report.
        """
        # Aggregate findings from all tools
        all_findings: list[Finding] = []
        reasoning_trace: list[dict[str, Any]] = []
        plan: list[str] = []
        specialist_outputs: dict[str, Any] = {}

        for tool_name, output in specialist_results.results.items():
            if tool_name.startswith("_"):
                continue  # Skip internal entries like _synthesis
            # mode="json" ensures datetime/date/enum objects become
            # JSON-safe strings — prevents StatementError on INSERT
            # into JSON columns (specialist_outputs, reasoning_trace, etc.)
            specialist_outputs[tool_name] = (
                output.model_dump(mode="json")
                if hasattr(output, "model_dump")
                else output
            )

            if hasattr(output, "findings"):
                all_findings.extend(output.findings)
            if hasattr(output, "reasoning_chain"):
                reasoning_trace.extend(output.reasoning_chain)
            if hasattr(output, "plan_suggestions"):
                plan.extend(output.plan_suggestions)

        # Get primary assessment from text reasoning if available
        diagnosis = "Assessment pending"
        confidence = 0.5
        evidence_summary = ""

        text_result = specialist_results.results.get(ToolName.TEXT_REASONING.value)
        if text_result and hasattr(text_result, "assessment"):
            diagnosis = text_result.assessment
            confidence = text_result.confidence
            evidence_summary = " | ".join(
                c.relevant_excerpt for c in getattr(text_result, "evidence_citations", [])
            )

        # Get timeline context from history and integrate into evidence
        timeline_impact = "No historical context available"
        history_result = specialist_results.results.get(ToolName.HISTORY_SEARCH.value)
        if history_result and hasattr(history_result, "timeline_context"):
            timeline_impact = history_result.timeline_context
            # Enrich evidence summary with relevant history
            if hasattr(history_result, "relevant_records") and history_result.relevant_records:
                history_evidence = " | ".join(
                    f"[{r.date.strftime('%Y-%m-%d')}] {r.summary[:100]}"
                    for r in history_result.relevant_records[:3]
                )
                if evidence_summary:
                    evidence_summary = f"{evidence_summary} | Historical: {history_evidence}"
                else:
                    evidence_summary = f"Historical: {history_evidence}"

        return FinalReport(
            encounter_id=request.encounter_id or "ENC-ADHOC",
            patient_id=request.patient_id,
            diagnosis=diagnosis,
            confidence=confidence,
            confidence_method=ConfidenceMethod.MODEL_SELF_REPORTED,
            evidence_summary=evidence_summary,
            timeline_impact=timeline_impact,
            plan=plan,
            findings=all_findings,
            reasoning_trace=reasoning_trace,
            specialist_outputs=specialist_outputs,
            judge_verdict=judgment,
            created_at=datetime.utcnow(),
        )

    def _build_user_message(self, request: CaseAnalysisRequest) -> str:
        """Build the user message for Claude from the case request."""
        parts = [
            f"## Case Analysis Request",
            f"**Patient ID**: {request.patient_id}",
            f"**Doctor's Query**: {request.doctor_query}",
        ]

        if request.clinical_context:
            parts.append(f"**Clinical Context**: {request.clinical_context}")
        if request.patient_history_text:
            parts.append(f"**Patient History**:\n{request.patient_history_text}")
        if request.image_urls:
            parts.append(f"**Medical Images**: {', '.join(request.image_urls)}")
        if request.audio_urls:
            parts.append(f"**Audio Recordings**: {', '.join(request.audio_urls)}")
        if request.lab_results:
            parts.append(f"**Lab Results**: {json.dumps(request.lab_results, indent=2)}")

        parts.append(
            "\nPlease analyze this case using the appropriate specialist tools. "
            "Call all relevant tools to gather comprehensive findings."
        )
        return "\n".join(parts)

    def _format_tool_descriptions(self) -> str:
        """Format tool descriptions for the system prompt."""
        lines = []
        for tool_name in self._registry.list_tools():
            tool = self._registry.get_required(tool_name)
            lines.append(f"- **{tool_name.value}**: {tool.description}")
        return "\n".join(lines)

    def _build_requery_input(
        self,
        tool: ToolName,
        request: CaseAnalysisRequest,
        existing_results: SpecialistResults,
    ) -> dict[str, Any]:
        """Build enriched input for a tool re-query after conflict."""
        base_input: dict[str, Any] = {
            "clinical_context": request.clinical_context,
        }

        # Enrich with existing results for cross-referencing
        if tool == ToolName.IMAGE_ANALYSIS and request.image_urls:
            base_input["image_url"] = request.image_urls[0]
            base_input["modality_hint"] = "xray"  # safe default; normalized in http.py
            # Add text findings for context
            text_result = existing_results.results.get(ToolName.TEXT_REASONING.value)
            if text_result and hasattr(text_result, "assessment"):
                base_input["clinical_context"] += f"\n\nPrevious text analysis: {text_result.assessment}"

        elif tool == ToolName.TEXT_REASONING:
            base_input["patient_history"] = request.patient_history_text or ""
            # Add image findings for context
            img_result = existing_results.results.get(ToolName.IMAGE_ANALYSIS.value)
            if img_result and hasattr(img_result, "findings"):
                findings_text = "; ".join(f.finding for f in img_result.findings)
                base_input["imaging_findings"] = findings_text

        elif tool == ToolName.HISTORY_SEARCH:
            base_input["patient_id"] = request.patient_id
            base_input["query"] = request.doctor_query

        elif tool == ToolName.AUDIO_ANALYSIS and request.audio_urls:
            base_input["audio_url"] = request.audio_urls[0]

        elif tool == ToolName.IMAGE_EXPLAINABILITY and request.image_urls:
            base_input["image_url"] = request.image_urls[0]
            base_input["modality_hint"] = "xray"  # safe default

        return base_input


class MockOrchestrator(BaseOrchestrator):
    """Mock orchestrator for testing — bypasses Claude, calls tools directly."""

    def __init__(self, tool_registry: ToolRegistry, judge: BaseJudge) -> None:
        self._registry = tool_registry
        self._judge = judge

    async def analyze_case(self, request: CaseAnalysisRequest) -> FinalReport:
        """Simplified pipeline: call all registered tools → judge → report."""
        # Decide which tools to call based on input
        tools_to_call: list[ToolName] = [ToolName.HISTORY_SEARCH, ToolName.TEXT_REASONING]
        tool_inputs: dict[ToolName, dict[str, Any]] = {
            ToolName.HISTORY_SEARCH: {"patient_id": request.patient_id, "query": request.doctor_query},
            ToolName.TEXT_REASONING: {"clinical_context": request.clinical_context},
        }

        if request.image_urls:
            tools_to_call.append(ToolName.IMAGE_ANALYSIS)
            tool_inputs[ToolName.IMAGE_ANALYSIS] = {
                "image_url": request.image_urls[0],
                "clinical_context": request.clinical_context,
            }
            tools_to_call.append(ToolName.IMAGE_EXPLAINABILITY)
            tool_inputs[ToolName.IMAGE_EXPLAINABILITY] = {
                "image_url": request.image_urls[0],
                "modality_hint": "xray",
            }

        if request.audio_urls:
            tools_to_call.append(ToolName.AUDIO_ANALYSIS)
            tool_inputs[ToolName.AUDIO_ANALYSIS] = {
                "audio_url": request.audio_urls[0],
            }

        # Dispatch
        results = await self.dispatch_tools(tools_to_call, tool_inputs)

        # Judge
        judgment = await self._judge.evaluate(request, results)

        # Report (reuse the same logic)
        all_findings: list[Finding] = []
        reasoning_trace: list[dict[str, Any]] = []
        plan: list[str] = []

        for name, output in results.results.items():
            if hasattr(output, "findings"):
                all_findings.extend(output.findings)
            if hasattr(output, "reasoning_chain"):
                reasoning_trace.extend(output.reasoning_chain)
            if hasattr(output, "plan_suggestions"):
                plan.extend(output.plan_suggestions)

        text_result = results.results.get(ToolName.TEXT_REASONING.value)
        diagnosis = getattr(text_result, "assessment", "Assessment pending")
        confidence = getattr(text_result, "confidence", 0.5)

        history_result = results.results.get(ToolName.HISTORY_SEARCH.value)
        timeline_impact = getattr(history_result, "timeline_context", "No historical context")

        return FinalReport(
            encounter_id=request.encounter_id or "ENC-MOCK",
            patient_id=request.patient_id,
            diagnosis=diagnosis,
            confidence=confidence,
            confidence_method=ConfidenceMethod.MODEL_SELF_REPORTED,
            evidence_summary="Mock evidence summary",
            timeline_impact=timeline_impact,
            plan=plan,
            findings=all_findings,
            reasoning_trace=reasoning_trace,
            specialist_outputs={k: v.model_dump() for k, v in results.results.items()},
            judge_verdict=judgment,
        )

    async def dispatch_tools(
        self,
        tool_names: list[ToolName],
        tool_inputs: dict[ToolName, dict[str, Any]],
    ) -> SpecialistResults:
        results = SpecialistResults()

        async def _run(name: ToolName) -> None:
            tool = self._registry.get(name)
            if tool is None:
                results.errors[name.value] = f"Tool '{name.value}' not registered"
                return
            try:
                output = await tool.execute(**tool_inputs.get(name, {}))
                results.results[name.value] = output
            except Exception as e:
                results.errors[name.value] = str(e)

        await asyncio.gather(*[_run(n) for n in tool_names])
        return results
