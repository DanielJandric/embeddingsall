from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .planner import QueryPlanner
from .types import (
    CorrectedResponse,
    ExecutionContext,
    ExecutionOutcome,
    ExecutionPlan,
)
from .validation import ValidationChain
from .confidence import ConfidenceScorer


class CorrectiveRAG:
    """
    Executes an execution plan, validates the outcome and retries with corrections if needed.
    """

    def __init__(
        self,
        tool_runner,
        validator: Optional[ValidationChain] = None,
        scorer: Optional[ConfidenceScorer] = None,
        planner: Optional[QueryPlanner] = None,
    ) -> None:
        self.tool_runner = tool_runner
        self.validator = validator or ValidationChain()
        self.scorer = scorer or ConfidenceScorer()
        self.planner = planner or QueryPlanner()
        self.correction_history: List[str] = []

    async def execute_with_correction(
        self,
        plan: ExecutionPlan,
        max_iterations: int = 3,
    ) -> CorrectedResponse:
        last_outcome: Optional[ExecutionOutcome] = None

        for iteration in range(max_iterations):
            context = ExecutionContext(
                query=plan.query,
                tool_runner=self.tool_runner,
                metadata={"iteration": iteration},
            )
            outcome = await self._execute_plan(plan, context)
            last_outcome = outcome

            validation = await self.validator.validate_response(
                outcome.data,
                outcome.sources,
                plan.query,
                context,
            )
            confidence_score = self.scorer.calculate_confidence(
                outcome.data,
                outcome.sources,
                validation,
            )

            if validation.passed and confidence_score.overall >= plan.confidence_threshold:
                return CorrectedResponse(
                    data=outcome.data,
                    confidence=confidence_score.overall,
                    iterations=iteration + 1,
                    sources=outcome.sources,
                    contradictions=validation.contradictions,
                    validation=validation,
                    confidence_score=confidence_score,
                    warnings=[],
                    corrections_applied=self.correction_history.copy(),
                )

            # attempt correction
            if validation.contradictions:
                reason = ", ".join(
                    f"{c.get('rule')}: {c.get('details')}" for c in validation.contradictions
                )
                self.correction_history.append(reason)
                plan = self.planner.enrich_plan(plan, reason=reason)

            if validation.requires_requery and iteration + 1 < max_iterations:
                self.correction_history.append("Requête supplémentaire demandée par la validation.")
                await asyncio.sleep(0)  # allow event loop to refresh
                continue
            else:
                break

        # Fallback result with warnings
        assert last_outcome is not None
        validation = await self.validator.validate_response(
            last_outcome.data,
            last_outcome.sources,
            plan.query,
        )
        confidence_score = self.scorer.calculate_confidence(
            last_outcome.data,
            last_outcome.sources,
            validation,
        )
        warnings = ["Max iterations atteintes", "Confiance inférieure au seuil"]
        return CorrectedResponse(
            data=last_outcome.data,
            confidence=confidence_score.overall,
            iterations=max_iterations,
            sources=last_outcome.sources,
            contradictions=validation.contradictions,
            validation=validation,
            confidence_score=confidence_score,
            warnings=warnings,
            corrections_applied=self.correction_history.copy(),
        )

    async def _execute_plan(self, plan: ExecutionPlan, ctx: ExecutionContext) -> ExecutionOutcome:
        for phase in plan.phases:
            tasks = [step.run(ctx) for step in phase]
            # run sequentially to preserve order while allowing future parallelisation
            for task in tasks:
                await task

        output = ctx.memory.get(plan.output_step, {})
        if not isinstance(output, dict):
            output = {"summary": "Aucune donnée disponible", "sources": [], "details": {}}
        sources = output.get("sources") or []

        return ExecutionOutcome(
            query=plan.query,
            data=output,
            sources=list(sources),
            raw_results=ctx.memory,
        )

