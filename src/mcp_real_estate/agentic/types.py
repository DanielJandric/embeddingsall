from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence


StepCallable = Callable[["ExecutionContext"], Awaitable[Any]]


@dataclass
class ExecutionStep:
    """
    One executable element of a plan.
    """

    name: str
    func: StepCallable
    description: str = ""
    optional: bool = False

    async def run(self, ctx: "ExecutionContext") -> Any:
        if asyncio.iscoroutinefunction(self.func):  # type: ignore[arg-type]
            result = await self.func(ctx)  # type: ignore[misc]
        else:
            maybe_coro = self.func(ctx)
            if asyncio.iscoroutine(maybe_coro):
                result = await maybe_coro
            else:
                result = maybe_coro
        ctx.memory[self.name] = result
        return result


@dataclass
class ExecutionPlan:
    """
    Ordered collection of phases with validation rules.
    """

    query: str
    phases: List[List[ExecutionStep]]
    output_step: str
    validation_rules: Sequence["ValidationRule"] = field(default_factory=tuple)
    confidence_threshold: float = 0.75
    max_retries: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)

    def clone(self, **updates: Any) -> "ExecutionPlan":
        return replace(self, **updates)

    def append_phase(self, steps: List[ExecutionStep]) -> "ExecutionPlan":
        return self.clone(phases=self.phases + [steps])


@dataclass
class ExecutionContext:
    query: str
    tool_runner: Callable[[str, Dict[str, Any]], Awaitable[Any]]
    memory: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    async def call_tool(self, method: str, params: Dict[str, Any]) -> Any:
        return await self.tool_runner(method, params)


@dataclass
class ExecutionOutcome:
    query: str
    data: Dict[str, Any]
    sources: List[str]
    raw_results: Dict[str, Any]


@dataclass
class ValidationCheckResult:
    name: str
    passed: bool
    details: str = ""
    severity: str = "info"
    requires_requery: bool = False
    score: float = 1.0


@dataclass
class ValidationResult:
    passed: bool
    confidence: float
    checks: List[ValidationCheckResult]
    contradictions: List[Dict[str, Any]]
    requires_requery: bool
    suggested_corrections: List[str]
    db_doc_alignment_score: float
    numerical_coherence_score: float


@dataclass
class ConfidenceScore:
    overall: float
    factors: Dict[str, float]
    flags: List[str]


@dataclass
class CorrectedResponse:
    data: Dict[str, Any]
    confidence: float
    iterations: int
    sources: List[str]
    contradictions: List[Dict[str, Any]]
    validation: ValidationResult
    confidence_score: ConfidenceScore
    warnings: List[str] = field(default_factory=list)
    corrections_applied: List[str] = field(default_factory=list)


class ValidationRule:
    """
    Base class for validation rules.
    """

    name: str = "base-rule"

    async def run(
        self,
        response: Dict[str, Any],
        sources: List[str],
        query: str,
        context: Optional[ExecutionContext] = None,
    ) -> ValidationCheckResult:
        raise NotImplementedError

