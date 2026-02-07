"""Claude-based Orchestrator — the brain of the agentic system.

Implements the Orchestrator-Workers pattern:
1. ROUTE: Classify the case → decide which tools are needed
2. DISPATCH: Call tools in parallel
3. COLLECT: Gather structured results
4. JUDGE: Validate consensus (delegate to Judge agent)
5. REPORT: Generate final structured report

Uses Anthropic's tool-use API with parallel tool calls.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from anthropic.types import Message, ContentBlock, ToolUseBlock, TextBlock

from medai.config import Settings
from medai.domain.entities import (
    Finding,
    FinalReport,
    JudgeVerdict,
    SpecialistResults,
    ToolName,
    ToolOutput,
)
from medai.domain.interfaces import BaseJudge, BaseOrchestrator
from medai.domain.schemas import CaseAnalysisRequest
from medai.services.tool_registry import ToolRegistry

logger = structlog.get_logger()

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
5. You may call multiple tools in parallel.
6. After receiving all tool results, synthesize a final diagnosis.

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
        """Full case analysis pipeline."""
        logger.info(
            "case_analysis_started",
            patient_id=request.patient_id,
            has_images=bool(request.image_urls),
            has_audio=bool(request.audio_urls),
        )

        # Build tool definitions for Claude
        tool_definitions = self._registry.get_claude_tool_definitions()

        # Build the user message with all case data
        user_content = self._build_user_message(request)

        system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
            tool_descriptions=self._format_tool_descriptions(),
        )

        # ── Step 1-3: Let Claude decide tools and invoke them ──
        specialist_results = await self._run_tool_loop(
            system_prompt=system_prompt,
            user_content=user_content,
            tool_definitions=tool_definitions,
        )

        logger.info(
            "tools_completed",
            successful=list(specialist_results.results.keys()),
            errors=list(specialist_results.errors.keys()),
        )

        # ── Step 4: Judge evaluates consensus ──
        judgment = await self._judge.evaluate(request, specialist_results)

        # ── Step 4b: Re-query if conflict (up to max cycles) ──
        cycle = 0
        while (
            judgment.verdict == JudgeVerdict.CONFLICT
            and judgment.requery_tools
            and cycle < self._settings.max_judgment_cycles
        ):
            cycle += 1
            logger.info("requery_cycle", cycle=cycle, tools=judgment.requery_tools)

            additional_results = await self.dispatch_tools(
                tool_names=judgment.requery_tools,
                tool_inputs={
                    tool: self._build_requery_input(tool, request, specialist_results)
                    for tool in judgment.requery_tools
                },
            )
            # Merge new results
            specialist_results.results.update(additional_results.results)
            specialist_results.errors.update(additional_results.errors)

            judgment = await self._judge.evaluate(request, specialist_results)

        # ── Step 5: Generate final report ──
        report = await self._generate_report(request, specialist_results, judgment)

        logger.info(
            "case_analysis_completed",
            report_id=report.id,
            diagnosis=report.diagnosis,
            confidence=report.confidence,
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

            # Add assistant's response to conversation
            messages.append({"role": "assistant", "content": response.content})  # type: ignore

            # Execute all tool calls in parallel
            tool_results = await self._execute_tool_calls(tool_calls, results)

            # Add tool results back to conversation
            messages.append({"role": "user", "content": tool_results})

        return results

    async def _execute_tool_calls(
        self,
        tool_calls: list[ToolUseBlock],
        results: SpecialistResults,
    ) -> list[dict[str, Any]]:
        """Execute tool calls from Claude and format results for conversation."""
        tool_result_blocks = []

        for tool_call in tool_calls:
            tool_name_str = tool_call.name
            tool_input = tool_call.input  # type: ignore

            logger.info("executing_tool", tool=tool_name_str, input_keys=list(tool_input.keys()) if isinstance(tool_input, dict) else [])

            try:
                tool_name = ToolName(tool_name_str)
                tool = self._registry.get_required(tool_name)
                output = await tool.execute(**tool_input if isinstance(tool_input, dict) else {})

                # Store in results
                results.results[tool_name_str] = output

                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": output.model_dump_json(),
                })

            except Exception as e:
                logger.error("tool_call_failed", tool=tool_name_str, error=str(e))
                results.errors[tool_name_str] = str(e)
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps({"error": str(e)}),
                    "is_error": True,
                })

        return tool_result_blocks

    async def _generate_report(
        self,
        request: CaseAnalysisRequest,
        specialist_results: SpecialistResults,
        judgment: Any,
    ) -> FinalReport:
        """Generate the final structured report from specialist results."""
        # Aggregate findings from all tools
        all_findings: list[Finding] = []
        reasoning_trace: list[dict[str, Any]] = []
        plan: list[str] = []
        specialist_outputs: dict[str, Any] = {}

        for tool_name, output in specialist_results.results.items():
            if tool_name.startswith("_"):
                continue  # Skip internal entries like _synthesis
            specialist_outputs[tool_name] = output.model_dump() if hasattr(output, "model_dump") else output

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

        # Get timeline context from history
        timeline_impact = "No historical context available"
        history_result = specialist_results.results.get(ToolName.HISTORY_SEARCH.value)
        if history_result and hasattr(history_result, "timeline_context"):
            timeline_impact = history_result.timeline_context

        return FinalReport(
            encounter_id=request.encounter_id or "ENC-ADHOC",
            patient_id=request.patient_id,
            diagnosis=diagnosis,
            confidence=confidence,
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
