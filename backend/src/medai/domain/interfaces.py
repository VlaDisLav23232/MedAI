"""Abstract interfaces — the OOAD backbone.

Open for Extension, Closed for Modification.
Every concrete service implements one of these interfaces.
New tools, orchestrators, or storage backends can be added
without modifying existing code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from medai.domain.entities import (
    FinalReport,
    JudgmentResult,
    Patient,
    SpecialistResults,
    TimelineEvent,
    ToolName,
    ToolOutput,
)
from medai.domain.schemas import CaseAnalysisRequest


# ═══════════════════════════════════════════════════════════════
#  Tool Interface
# ═══════════════════════════════════════════════════════════════

class BaseTool(ABC):
    """Abstract specialist tool.

    Every medical analysis tool (image, text, audio, history)
    must implement this interface.

    Properties:
        name: unique ToolName identifier
        description: human-readable description (used in Claude's tool schema)
        input_schema: JSON Schema dict (used in Claude's tool definition)
    """

    @property
    @abstractmethod
    def name(self) -> ToolName:
        """Unique tool identifier."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for the orchestrator."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for tool input parameters."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolOutput:
        """Run the tool with given parameters and return structured output."""
        ...

    def to_claude_tool_definition(self) -> dict[str, Any]:
        """Convert to Anthropic tool-use format with strict validation.

        Uses `strict: true` so Claude validates tool inputs against the
        JSON schema at generation time — no malformed tool calls.
        """
        schema = self.input_schema.copy()
        # Ensure additionalProperties is set for strict mode
        schema.setdefault("additionalProperties", False)
        return {
            "name": self.name.value,
            "description": self.description,
            "input_schema": schema,
            "strict": True,
        }


# ═══════════════════════════════════════════════════════════════
#  Orchestrator Interface
# ═══════════════════════════════════════════════════════════════

class BaseOrchestrator(ABC):
    """Abstract orchestrator — plans, routes, and aggregates.

    The orchestrator receives a case analysis request, decides
    which tools to invoke, collects results, and produces a report.
    """

    @abstractmethod
    async def analyze_case(self, request: CaseAnalysisRequest) -> FinalReport:
        """Full case analysis pipeline: route → dispatch → collect → judge → report."""
        ...

    @abstractmethod
    async def dispatch_tools(
        self,
        tool_names: list[ToolName],
        tool_inputs: dict[ToolName, dict[str, Any]],
    ) -> SpecialistResults:
        """Dispatch selected tools in parallel and collect results."""
        ...


# ═══════════════════════════════════════════════════════════════
#  Judge Interface
# ═══════════════════════════════════════════════════════════════

class BaseJudge(ABC):
    """Abstract judge — validates consensus across specialist outputs.

    Checks for contradictions, low confidence, missing context,
    and guideline adherence.
    """

    @abstractmethod
    async def evaluate(
        self,
        request: CaseAnalysisRequest,
        specialist_results: SpecialistResults,
    ) -> JudgmentResult:
        """Evaluate specialist results and return verdict."""
        ...


# ═══════════════════════════════════════════════════════════════
#  Repository Interfaces
# ═══════════════════════════════════════════════════════════════

class BasePatientRepository(ABC):
    """Abstract patient data access."""

    @abstractmethod
    async def get(self, patient_id: str) -> Patient | None:
        ...

    @abstractmethod
    async def create(self, patient: Patient) -> Patient:
        ...

    @abstractmethod
    async def list_all(self) -> list[Patient]:
        ...


class BaseTimelineRepository(ABC):
    """Abstract timeline data access."""

    @abstractmethod
    async def get_for_patient(self, patient_id: str) -> list[TimelineEvent]:
        ...

    @abstractmethod
    async def add_event(self, event: TimelineEvent) -> TimelineEvent:
        ...


class BaseReportRepository(ABC):
    """Abstract report data access."""

    @abstractmethod
    async def get(self, report_id: str) -> FinalReport | None:
        ...

    @abstractmethod
    async def save(self, report: FinalReport) -> FinalReport:
        ...

    @abstractmethod
    async def update_approval(
        self, report_id: str, status: str, doctor_notes: str | None = None
    ) -> FinalReport | None:
        ...

    @abstractmethod
    async def list_for_patient(self, patient_id: str) -> list[FinalReport]:
        ...
