from __future__ import annotations

from typing import Any, Dict, Optional

from .strategies import ComparativeStrategy, FinancialStrategy, FactualStrategy
from .types import ExecutionPlan


class QueryPlanner:
    """
    Builds or enriches execution plans for complex requests.
    """

    def __init__(self) -> None:
        self.factual_strategy = FactualStrategy()
        self.financial_strategy = FinancialStrategy()
        self.comparative_strategy = ComparativeStrategy()

    async def plan_complex_query(self, query: str) -> ExecutionPlan:
        """
        Compose a multi-branch plan by merging strategies.
        """
        base_plan = self.factual_strategy.build_plan(query, {"intent": "factual"})
        financial_plan = self.financial_strategy.build_plan(query, {"intent": "financial"})
        comparative_plan = self.comparative_strategy.build_plan(query, {"intent": "comparative"})

        combined_phases = (
            base_plan.phases[:-1]
            + financial_plan.phases[:-1]
            + comparative_plan.phases[:-1]
        )
        combined_phases.extend(base_plan.phases[-1:])

        return ExecutionPlan(
            query=query,
            phases=combined_phases,
            output_step=base_plan.output_step,
            validation_rules=base_plan.validation_rules,
            confidence_threshold=max(
                base_plan.confidence_threshold,
                financial_plan.confidence_threshold,
                comparative_plan.confidence_threshold,
            ),
            metadata={"composed": True},
        )

    def enrich_plan(self, plan: ExecutionPlan, reason: Optional[str] = None) -> ExecutionPlan:
        """
        Adds a fallback factual phase to increase recall.
        """
        supplemental_plan = self.factual_strategy.build_plan(
            plan.query, {"intent": "factual", "mode": "supplemental"}
        )
        metadata = dict(plan.metadata)
        metadata.setdefault("enrichment_notes", []).append(reason or "supplemental-search")
        new_phases = plan.phases + supplemental_plan.phases[:-1]
        return plan.clone(phases=new_phases, metadata=metadata)

