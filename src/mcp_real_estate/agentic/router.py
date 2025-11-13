from __future__ import annotations

import re
from typing import Dict, Optional

from .strategies import STRATEGIES, BaseStrategy, SynthesisStrategy
from .types import ExecutionPlan


INTENT_KEYWORDS = {
    "financial": {"rendement", "finance", "cashflow", "tri", "dcf"},
    "risk": {"risque", "vacance", "covenant", "stress", "exposition"},
    "comparative": {"compar", "benchmark", "marché", "vs "},
    "land_registry": {"registre", "servitude", "parcelle", "foncier"},
    "stakeholder": {"stakeholder", "locataire", "bailleur", "tenant", "exposition"},
    "synthesis": {"rapport", "synthèse", "due diligence", "analyse complète"},
}


class AgenticRAGRouter:
    """
    Simple intent-based router that selects a strategy and builds a plan.
    """

    def __init__(
        self,
        default_strategy: Optional[BaseStrategy] = None,
    ) -> None:
        self.default_strategy = default_strategy or STRATEGIES["factual"]

    def _classify_intent(self, query: str) -> str:
        lowered = query.lower()
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return intent
        # fallback keywords
        if re.search(r"\b(rendement|rentabilité|cash)\b", lowered):
            return "financial"
        if re.search(r"\b(vacance|risque|stress)\b", lowered):
            return "risk"
        if re.search(r"\b(registre|servitude|foncier|parcelle)\b", lowered):
            return "land_registry"
        if re.search(r"\b(locataire|tenant|bailleur|stakeholder)\b", lowered):
            return "stakeholder"
        return "factual"

    async def route_query(self, query: str, context: Dict[str, str]) -> ExecutionPlan:
        intent = context.get("intent") or self._classify_intent(query)
        strategy = STRATEGIES.get(intent, self.default_strategy)
        return strategy.build_plan(query, context)

    async def replan_from_reflection(
        self,
        plan: ExecutionPlan,
        reflection: "ReflectionResult",
        strategy_override: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Rebuild the plan with a more exhaustive strategy when reflection suggests it.
        """
        target_strategy: BaseStrategy
        if strategy_override:
            target_strategy = STRATEGIES.get(strategy_override, self.default_strategy)
        else:
            target_strategy = (
                STRATEGIES.get("synthesis", SynthesisStrategy())
                if reflection.should_continue
                else self.default_strategy
            )
        query = plan.query
        new_plan = target_strategy.build_plan(query, {"intent": target_strategy.name})
        metadata = dict(plan.metadata)
        metadata["reflection"] = reflection.improvement_actions
        return new_plan.clone(metadata=metadata)

