from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from .types import (
    ExecutionContext,
    ValidationCheckResult,
    ValidationResult,
    ValidationRule,
)


class SourceConsistencyRule(ValidationRule):
    name = "source-consistency"

    async def run(
        self,
        response: Dict[str, Any],
        sources: List[str],
        query: str,
        context: Optional[ExecutionContext] = None,
    ) -> ValidationCheckResult:
        unique_sources = {src for src in sources if src}
        if not unique_sources:
            return ValidationCheckResult(
                name=self.name,
                passed=False,
                severity="warning",
                details="Aucune source explicite disponible.",
                requires_requery=True,
                score=0.2,
            )
        return ValidationCheckResult(
            name=self.name,
            passed=True,
            details=f"{len(unique_sources)} sources référencées.",
            score=min(1.0, 0.5 + len(unique_sources) * 0.1),
        )


class NumericalCoherenceRule(ValidationRule):
    name = "numerical-coherence"

    async def run(
        self,
        response: Dict[str, Any],
        sources: List[str],
        query: str,
        context: Optional[ExecutionContext] = None,
    ) -> ValidationCheckResult:
        metrics = response.get("metrics") or []
        if not isinstance(metrics, list) or not metrics:
            return ValidationCheckResult(
                name=self.name,
                passed=True,
                details="Pas de métriques numériques détectées.",
                score=0.7,
            )

        negative = [m for m in metrics if isinstance(m, (int, float)) and m < 0]
        if negative:
            return ValidationCheckResult(
                name=self.name,
                passed=False,
                severity="error",
                details=f"Métriques négatives détectées: {negative[:3]}",
                requires_requery=True,
                score=0.1,
            )

        return ValidationCheckResult(
            name=self.name,
            passed=True,
            details="Cohérence numérique basique respectée.",
            score=0.9,
        )


class TemporalConsistencyRule(ValidationRule):
    name = "temporal-consistency"

    async def run(
        self,
        response: Dict[str, Any],
        sources: List[str],
        query: str,
        context: Optional[ExecutionContext] = None,
    ) -> ValidationCheckResult:
        timestamps = response.get("source_timestamps") or []
        if not timestamps:
            return ValidationCheckResult(
                name=self.name,
                passed=True,
                details="Pas d'information temporelle pour jugement.",
                score=0.6,
            )

        now = dt.datetime.utcnow()
        stale = []
        for ts in timestamps:
            try:
                parsed = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if (now - parsed).days > 365 * 5:
                stale.append(ts)

        if stale:
            return ValidationCheckResult(
                name=self.name,
                passed=False,
                severity="warning",
                details=f"Sources anciennes (>5 ans): {stale[:3]}",
                requires_requery=False,
                score=0.4,
            )

        return ValidationCheckResult(
            name=self.name,
            passed=True,
            details="Sources récentes.",
            score=0.85,
        )


class StructuralCompletenessRule(ValidationRule):
    name = "structural-completeness"

    required_fields = ("summary", "sources")

    async def run(
        self,
        response: Dict[str, Any],
        sources: List[str],
        query: str,
        context: Optional[ExecutionContext] = None,
    ) -> ValidationCheckResult:
        missing = [field for field in self.required_fields if field not in response]
        if missing:
            return ValidationCheckResult(
                name=self.name,
                passed=False,
                severity="warning",
                details=f"Champs manquants: {', '.join(missing)}",
                requires_requery=False,
                score=0.3,
            )
        return ValidationCheckResult(
            name=self.name,
            passed=True,
            details="Structure de réponse complète.",
            score=0.95,
        )


class ValidationChain:
    """
    Aggregates validation rules and produces a global verdict.
    """

    def __init__(
        self,
        rules: Optional[List[ValidationRule]] = None,
    ) -> None:
        self.rules = rules or [
            SourceConsistencyRule(),
            NumericalCoherenceRule(),
            TemporalConsistencyRule(),
            StructuralCompletenessRule(),
        ]

    async def validate_response(
        self,
        response: Dict[str, Any],
        sources: List[str],
        query: str,
        context: Optional[ExecutionContext] = None,
    ) -> ValidationResult:
        checks: List[ValidationCheckResult] = []
        contradictions: List[Dict[str, Any]] = []

        for rule in self.rules:
            result = await rule.run(response, sources, query, context)
            checks.append(result)
            if not result.passed:
                contradictions.append(
                    {
                        "rule": rule.name,
                        "details": result.details,
                        "severity": result.severity,
                    }
                )

        overall_score = sum(check.score for check in checks) / max(len(checks), 1)
        requires_requery = any(check.requires_requery for check in checks)
        suggested = [
            f"Revoir règle {check.name}: {check.details}"
            for check in checks
            if not check.passed
        ]

        # Derive specialised scores
        db_doc_score = next(
            (check.score for check in checks if check.name == "source-consistency"), 0.5
        )
        numerical_score = next(
            (check.score for check in checks if check.name == "numerical-coherence"), 0.5
        )

        return ValidationResult(
            passed=all(check.passed for check in checks),
            confidence=max(overall_score, 0.0),
            checks=checks,
            contradictions=contradictions,
            requires_requery=requires_requery,
            suggested_corrections=suggested,
            db_doc_alignment_score=db_doc_score,
            numerical_coherence_score=numerical_score,
        )

