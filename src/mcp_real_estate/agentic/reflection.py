from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ReflectionResult:
    should_continue: bool
    missing_checks: List[str]
    contradictions_found: List[str]
    improvement_actions: List[str]
    confidence: float


class SelfReflectiveAgent:
    """
    Lightweight self-critique layer (heuristic, no external LLM call).
    """

    def reflect_on_answer(
        self,
        query: str,
        answer: Dict[str, Any],
        sources: List[str],
    ) -> ReflectionResult:
        missing_checks: List[str] = []
        contradictions: List[str] = []
        actions: List[str] = []

        summary = answer.get("summary") or ""
        details = answer.get("details") or {}

        if not summary:
            missing_checks.append("Ajouter un résumé synthétique.")
            actions.append("Générer une synthèse courte à partir des données brutes.")

        if len(sources) < 1:
            missing_checks.append("Pas de sources référencées.")
            actions.append("Inclure au moins un document source.")

        metrics = answer.get("metrics") or []
        if isinstance(metrics, list) and not metrics:
            missing_checks.append("Aucune métrique chiffrée.")
            actions.append("Calculer au moins un indicateur financier ou opérationnel.")

        if isinstance(details, dict) and details.get("warnings"):
            contradictions.extend(details["warnings"])

        confidence = 10.0
        if missing_checks or contradictions:
            confidence -= 3.0
        if not sources:
            confidence -= 2.0
        confidence = max(0.0, min(10.0, confidence))

        should_continue = confidence < 8.0

        return ReflectionResult(
            should_continue=should_continue,
            missing_checks=missing_checks,
            contradictions_found=contradictions,
            improvement_actions=actions,
            confidence=confidence,
        )

