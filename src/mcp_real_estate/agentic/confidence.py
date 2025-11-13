from __future__ import annotations

from typing import Any, Dict, List

from .types import ConfidenceScore, ValidationResult


class ConfidenceScorer:
    """
    Combines validation metrics and heuristic factors into a single score.
    """

    def calculate_confidence(
        self,
        response: Dict[str, Any],
        sources: List[str],
        validation: ValidationResult,
    ) -> ConfidenceScore:
        factors: Dict[str, float] = {}

        factors["source_quality"] = self._score_source_quality(sources)
        factors["source_agreement"] = self._score_source_agreement(validation)
        factors["db_doc_alignment"] = validation.db_doc_alignment_score
        factors["numerical_coherence"] = validation.numerical_coherence_score
        factors["completeness"] = self._score_completeness(response)
        factors["recency"] = self._score_recency(response)

        weights = {
            "source_quality": 0.25,
            "source_agreement": 0.20,
            "db_doc_alignment": 0.20,
            "numerical_coherence": 0.15,
            "completeness": 0.15,
            "recency": 0.05,
        }

        overall = sum(factors[key] * weights[key] for key in factors)
        flags = self._generate_flags(factors, threshold=0.6)

        return ConfidenceScore(overall=overall, factors=factors, flags=flags)

    # --- factor scorers -------------------------------------------------

    def _score_source_quality(self, sources: List[str]) -> float:
        if not sources:
            return 0.2
        unique = {src for src in sources if src}
        return min(1.0, 0.5 + len(unique) * 0.1)

    def _score_source_agreement(self, validation: ValidationResult) -> float:
        contradictions = [c for c in validation.contradictions if c.get("severity") == "error"]
        if not contradictions:
            return 0.85
        if len(contradictions) == 1:
            return 0.6
        return 0.4

    def _score_completeness(self, response: Dict[str, Any]) -> float:
        required = {"summary", "details", "sources"}
        missing = required - response.keys()
        if missing:
            return 0.5
        return 0.95

    def _score_recency(self, response: Dict[str, Any]) -> float:
        timestamps = response.get("source_timestamps") or []
        if not timestamps:
            return 0.6
        return 0.8

    # --- helpers --------------------------------------------------------

    def _generate_flags(self, factors: Dict[str, float], threshold: float) -> List[str]:
        return [name for name, value in factors.items() if value < threshold]

