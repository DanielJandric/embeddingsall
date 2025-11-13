from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .types import ExecutionContext, ExecutionPlan, ExecutionStep
from .validation import (
    SourceConsistencyRule,
    NumericalCoherenceRule,
    TemporalConsistencyRule,
    StructuralCompletenessRule,
)


def _make_tool_step(
    name: str,
    method: str,
    params_builder: Callable[[ExecutionContext], Dict[str, Any]],
    description: str = "",
) -> ExecutionStep:
    async def runner(ctx: ExecutionContext) -> Dict[str, Any]:
        params = params_builder(ctx)
        data = await ctx.call_tool(method, params)
        return {
            "method": method,
            "params": params,
            "data": data,
        }

    return ExecutionStep(name=name, func=runner, description=description)


def _make_aggregate_step(name: str, aggregator: Callable[[ExecutionContext], Dict[str, Any]]) -> ExecutionStep:
    async def runner(ctx: ExecutionContext) -> Dict[str, Any]:
        return aggregator(ctx)

    return ExecutionStep(name=name, func=runner, description="Synthèse et agrégation des résultats")


def _collect_sources(*payloads: Any) -> List[str]:
    sources: List[str] = []
    for payload in payloads:
        if isinstance(payload, dict):
            if "sources" in payload and isinstance(payload["sources"], list):
                sources.extend(str(src) for src in payload["sources"])
            if "data" in payload:
                sources.extend(_collect_sources(payload["data"]))
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    if "file_name" in item:
                        sources.append(str(item["file_name"]))
                    sources.extend(_collect_sources(item))
    return list(dict.fromkeys(src for src in sources if src))


class BaseStrategy:
    name: str = "base"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        raise NotImplementedError

    def _default_validation_rules(self):
        return [
            SourceConsistencyRule(),
            NumericalCoherenceRule(),
            TemporalConsistencyRule(),
            StructuralCompletenessRule(),
        ]


class FactualStrategy(BaseStrategy):
    name = "factual"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        lowered = query.lower()

        def documents_params(_: ExecutionContext) -> Dict[str, Any]:
            return {
                "table_name": "documents_full",
                "filters": {"file_name": f"%{lowered}%"},
                "limit": 20,
            }

        def properties_params(_: ExecutionContext) -> Dict[str, Any]:
            return {
                "table_name": "property_insights",
                "filters": {"property_key": f"%{lowered.replace(' ', '-') }%"},
                "limit": 10,
            }

        def extract(entry: Dict[str, Any]) -> Any:
            data = entry.get("data")
            if isinstance(data, dict) and "data" in data:
                return data.get("data")
            return data

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            documents_entry = ctx.memory.get("documents_lookup", {})
            properties_entry = ctx.memory.get("property_lookup", {})
            documents = extract(documents_entry) or []
            properties = extract(properties_entry) or []
            sources = _collect_sources(documents, properties)
            summary = f"Recherche factuelle pour '{query}' avec {len(properties)} propriétés et {len(documents)} documents."
            return {
                "summary": summary,
                "details": {
                    "documents": documents,
                    "properties": properties,
                },
                "metrics": [len(properties), len(documents)],
                "sources": sources,
                "source_timestamps": [
                    item.get("updated_at")
                    for item in properties
                    if isinstance(item, dict) and item.get("updated_at")
                ],
            }

        phases = [
            [
                _make_tool_step("documents_lookup", "query_table", documents_params, "Recherche de documents bruts"),
                _make_tool_step("property_lookup", "query_table", properties_params, "Recherche dans property_insights"),
            ],
            [
                _make_aggregate_step("factual_summary", aggregate),
            ],
        ]

        return ExecutionPlan(
            query=query,
            phases=phases,
            output_step="factual_summary",
            validation_rules=self._default_validation_rules(),
            confidence_threshold=0.7,
        )


class FinancialStrategy(BaseStrategy):
    name = "financial"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        term = query.lower()

        def cashflow_params(_: ExecutionContext) -> Dict[str, Any]:
            return {
                "table_name": "property_insights",
                "filters": {"property_key": f"%{term.replace(' ', '-') }%"},
                "select": "property_key, rent_total_chf, rent_principal_chf, document_ids",
                "limit": 10,
            }

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            entry = ctx.memory.get("financial_overview", {})
            data = entry.get("data")
            if isinstance(data, dict) and "data" in data:
                overview = data["data"] or []
            else:
                overview = data or []
            metrics = []
            for item in overview:
                if isinstance(item, dict):
                    rent_total = item.get("rent_total_chf") or 0
                    metrics.append(float(rent_total))
            sources = _collect_sources(overview)
            summary = f"Analyse financière pour '{query}'."
            return {
                "summary": summary,
                "details": {"financials": overview},
                "metrics": metrics,
                "sources": sources,
            }

        phases = [
            [
                _make_tool_step(
                    "financial_overview",
                    "query_table",
                    cashflow_params,
                    "Extraction des flux financiers",
                )
            ],
            [_make_aggregate_step("financial_summary", aggregate)],
        ]

        return ExecutionPlan(
            query=query,
            phases=phases,
            output_step="financial_summary",
            validation_rules=self._default_validation_rules(),
            confidence_threshold=0.75,
        )


class ComparativeStrategy(BaseStrategy):
    name = "comparative"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        target_city = query.lower()

        def market_params(_: ExecutionContext) -> Dict[str, Any]:
            return {
                "table_name": "etats_locatifs",
                "filters": {"immeuble_ville": target_city.title()},
                "limit": 25,
            }

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            entry = ctx.memory.get("market_snapshot", {})
            data = entry.get("data")
            if isinstance(data, dict) and "data" in data:
                market = data["data"] or []
            else:
                market = data or []
            avg_rent = 0.0
            rents = []
            for item in market:
                if isinstance(item, dict):
                    rent = item.get("loyer_annuel_total")
                    if isinstance(rent, (int, float)):
                        rents.append(float(rent))
            if rents:
                avg_rent = sum(rents) / len(rents)
            sources = _collect_sources(market)
            summary = f"Comparaison de marché pour '{query}'."
            return {
                "summary": summary,
                "details": {"market": market},
                "metrics": [avg_rent] if rents else [],
                "sources": sources,
            }

        phases = [
            [
                _make_tool_step(
                    "market_snapshot",
                    "query_table",
                    market_params,
                    "Récupération des états locatifs pour la comparaison de marché",
                )
            ],
            [_make_aggregate_step("comparative_summary", aggregate)],
        ]

        return ExecutionPlan(
            query=query,
            phases=phases,
            output_step="comparative_summary",
            validation_rules=self._default_validation_rules(),
            confidence_threshold=0.7,
        )


class RiskAssessmentStrategy(BaseStrategy):
    name = "risk"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        lowered = query.lower()

        def risk_params(_: ExecutionContext) -> Dict[str, Any]:
            return {
                "seuil_vacance": 0.1,
                "limit": 20,
                "commune": lowered.title(),
            }

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            entry = ctx.memory.get("risk_alerts", {})
            data = entry.get("data")
            if isinstance(data, dict) and "data" in data:
                alerts = data["data"] or []
            else:
                alerts = data or []
            sources = _collect_sources(alerts)
            summary = f"Analyse de risques pour '{query}'."
            return {
                "summary": summary,
                "details": {"alerts": alerts},
                "metrics": [len(alerts)],
                "sources": sources,
            }

        phases = [
            [
                _make_tool_step(
                    "risk_alerts",
                    "find_vacancy_alerts",
                    risk_params,
                    "Recherche des alertes de vacance",
                )
            ],
            [_make_aggregate_step("risk_summary", aggregate)],
        ]

        return ExecutionPlan(
            query=query,
            phases=phases,
            output_step="risk_summary",
            validation_rules=self._default_validation_rules(),
            confidence_threshold=0.75,
        )


class SynthesisStrategy(BaseStrategy):
    name = "synthesis"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        factual = FactualStrategy().build_plan(query, context)
        financial = FinancialStrategy().build_plan(query, context)
        comparative = ComparativeStrategy().build_plan(query, context)

        synthesis_step = _make_aggregate_step(
            "synthesis_summary",
            lambda ctx: {
                "summary": f"Synthèse multi-volets pour '{query}'.",
                "details": {
                    "factual": ctx.memory.get("factual_summary"),
                    "financial": ctx.memory.get("financial_summary"),
                    "comparative": ctx.memory.get("comparative_summary"),
                },
                "metrics": [],
                "sources": _collect_sources(
                    ctx.memory.get("factual_summary"),
                    ctx.memory.get("financial_summary"),
                    ctx.memory.get("comparative_summary"),
                ),
            },
        )

        phases = factual.phases[:-1] + financial.phases[:-1] + comparative.phases[:-1]
        phases.append([synthesis_step])

        return ExecutionPlan(
            query=query,
            phases=phases,
            output_step="synthesis_summary",
            validation_rules=self._default_validation_rules(),
            confidence_threshold=0.8,
        )


STRATEGIES: Dict[str, BaseStrategy] = {
    "factual": FactualStrategy(),
    "financial": FinancialStrategy(),
    "comparative": ComparativeStrategy(),
    "risk": RiskAssessmentStrategy(),
    "synthesis": SynthesisStrategy(),
}

