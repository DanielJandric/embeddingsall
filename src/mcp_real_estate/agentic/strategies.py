from __future__ import annotations

import json
import re
import unicodedata
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


def _make_aggregate_step(
    name: str,
    aggregator: Callable[[ExecutionContext], Dict[str, Any]],
) -> ExecutionStep:
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


def _extract_data(entry: Dict[str, Any]) -> Any:
    data = entry.get("data")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return data
    if isinstance(data, dict) and "data" in data:
        return data.get("data")
    return data


STOPWORDS = {
    "analyse",
    "analysis",
    "complete",
    "complète",
    "complet",
    "de",
    "des",
    "du",
    "le",
    "la",
    "les",
    "d",
    "l",
    "rapport",
    "synthese",
    "synthèse",
    "immeuble",
    "limmeuble",
    "batiment",
    "bâtiment",
    "etude",
    "étude",
    "evaluation",
    "évaluation",
    "due",
    "diligence",
    "full",
}

ADDRESS_LEADS = {
    "avenue",
    "av",
    "av.",
    "route",
    "rue",
    "chemin",
    "cheminement",
    "impasse",
    "allee",
    "allée",
    "boulevard",
    "bd",
    "place",
    "square",
    "quai",
    "cours",
    "sentier",
    "passage",
    "esplanade",
    "parc",
    "villa",
    "clos",
    "grand-rue",
    "grand",
}

ADDRESS_CONNECTORS = {
    "de",
    "du",
    "des",
    "la",
    "le",
    "les",
    "d",
    "l",
    "sur",
    "a",
    "à",
    "au",
}

TRAILING_BREAK_WORDS = {
    "caracteristiques",
    "caractéristiques",
    "surface",
    "surfaces",
    "loyer",
    "loyers",
    "locataire",
    "locataires",
    "valorisation",
    "etat",
    "état",
    "locatif",
    "rent",
    "financier",
    "analyse",
}

NUMERIC_PATTERN = re.compile(r"^\d{1,4}(?:-\d{1,4})?$")


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _slugify(value: str, *, max_tokens: int = 8) -> str:
    normalized = _normalize(value)
    if not normalized:
        return ""
    normalized = normalized.replace(" ", "-")
    normalized = re.sub(r"-+", "-", normalized)
    tokens = [tok for tok in normalized.split("-") if tok]
    if max_tokens and len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return "-".join(tokens)


def _split_tokens_until_break(tokens: List[str]) -> List[str]:
    collected: List[str] = []
    for tok in tokens:
        if tok in TRAILING_BREAK_WORDS:
            break
        collected.append(tok)
    return collected


def _extract_terms(query: str) -> Dict[str, Any]:
    normalized = _normalize(query)
    tokens = normalized.split()

    candidate_communes = re.findall(r"\b([A-Z][a-zÀ-ÿ\-']{2,})\b", query)
    commune = candidate_communes[-1] if candidate_communes else ""
    normalized_commune = _normalize(commune) if commune else ""
    commune_slug = _slugify(commune) if commune else ""

    street_number_idx = -1
    for idx, tok in enumerate(tokens):
        if NUMERIC_PATTERN.match(tok):
            street_number_idx = idx
            break

    street_start_idx = 0
    if street_number_idx != -1:
        for idx in range(street_number_idx - 1, -1, -1):
            if tokens[idx] in ADDRESS_LEADS:
                street_start_idx = idx
                break
        else:
            street_start_idx = max(0, street_number_idx - 3)
        raw_address_tokens = tokens[street_start_idx : street_number_idx + 1]
    else:
        street_start_idx = next(
            (idx for idx, tok in enumerate(tokens) if tok in ADDRESS_LEADS), 0
        )
        raw_address_tokens = tokens[street_start_idx:]

    address_tokens = _split_tokens_until_break(raw_address_tokens)
    address_tokens = [tok for tok in address_tokens if tok]

    if not address_tokens and tokens:
        address_tokens = tokens[: min(len(tokens), 5)]

    slug_tokens = [
        tok
        for tok in address_tokens
        if tok
        and (
            tok not in STOPWORDS
            or tok in ADDRESS_LEADS
            or tok in ADDRESS_CONNECTORS
            or NUMERIC_PATTERN.match(tok)
        )
        and (len(tok) > 1 or tok.isdigit())
    ]
    if normalized_commune:
        slug_tokens.append(normalized_commune)
    property_slug_source = " ".join(slug_tokens or address_tokens)
    property_slug = _slugify(property_slug_source) or _slugify(normalized)

    keywords = [
        tok
        for tok in address_tokens
        if tok
        and (
            tok not in STOPWORDS
            or tok in ADDRESS_LEADS
            or NUMERIC_PATTERN.match(tok)
        )
        and (len(tok) > 1 or tok.isdigit())
    ]
    if commune_slug and commune_slug not in keywords:
        keywords.append(commune_slug)

    pattern_tokens = keywords.copy()
    if normalized_commune and normalized_commune not in pattern_tokens:
        pattern_tokens.append(normalized_commune)

    pattern_tokens = [tok for tok in pattern_tokens if tok]
    file_pattern = "%" + "%".join(pattern_tokens) + "%" if pattern_tokens else ""

    term = " ".join(pattern_tokens).strip() or normalized

    street_number = ""
    street_words: List[str] = []
    for tok in address_tokens:
        if NUMERIC_PATTERN.match(tok) and not street_number:
            street_number = tok
            continue
        if tok not in ADDRESS_CONNECTORS:
            street_words.append(tok)
    street = " ".join(street_words)

    return {
        "term": term,
        "commune": commune.strip(),
        "keywords": keywords or pattern_tokens,
        "file_pattern": file_pattern or (f"%{normalized.replace(' ', '%')}%" if normalized else ""),
        "property_slug": property_slug,
        "street": street,
        "street_number": street_number,
    }


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
        terms = _extract_terms(query)

        def documents_params(_: ExecutionContext) -> Dict[str, Any]:
            filters: Dict[str, Any] = {}
            pattern = terms.get("file_pattern")
            if isinstance(pattern, str) and pattern.strip("%"):
                filters["file_name"] = pattern
            else:
                filters["file_name"] = f"%{terms['term']}%"
            return {
                "table_name": "documents_full",
                "filters": filters,
                "limit": 20,
            }

        def properties_params(_: ExecutionContext) -> Dict[str, Any]:
            slug = terms.get("property_slug") or ""
            pattern = f"%{slug}%" if slug else f"%{terms['term'].replace(' ', '-') }%"
            return {
                "table_name": "property_insights",
                "filters": {"property_key": pattern},
                "limit": 15,
            }

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            documents = _extract_data(ctx.memory.get("documents_lookup", {})) or []
            properties = _extract_data(ctx.memory.get("property_lookup", {})) or []
            sources = _collect_sources(documents, properties)
            property_keys = [
                str(item.get("property_key"))
                for item in properties
                if isinstance(item, dict) and item.get("property_key")
            ]
            for key in property_keys:
                src = f"property:{key}"
                if src not in sources:
                    sources.append(src)
            summary = f"Recherche factuelle pour '{query}' avec {len(properties)} propriétés et {len(documents)} documents."
            return {
                "summary": summary,
                "details": {"documents": documents, "properties": properties},
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
            [_make_aggregate_step("factual_summary", aggregate)],
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
        terms = _extract_terms(query)

        def cashflow_params(_: ExecutionContext) -> Dict[str, Any]:
            slug = terms.get("property_slug") or ""
            pattern = f"%{slug}%" if slug else f"%{terms['term'].replace(' ', '-') }%"
            return {
                "table_name": "property_insights",
                "filters": {"property_key": pattern},
                "select": "property_key, rent_total_chf, rent_principal_chf, document_ids",
                "limit": 20,
            }

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            overview = _extract_data(ctx.memory.get("financial_overview", {})) or []
            metrics = []
            for item in overview:
                if isinstance(item, dict):
                    rent_total = item.get("rent_total_chf")
                    if isinstance(rent_total, (int, float)):
                        metrics.append(float(rent_total))
            sources = _collect_sources(overview)
            property_keys = [
                str(item.get("property_key"))
                for item in overview
                if isinstance(item, dict) and item.get("property_key")
            ]
            for key in property_keys:
                src = f"property:{key}"
                if src not in sources:
                    sources.append(src)
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
        terms = _extract_terms(query)

        def market_params(_: ExecutionContext) -> Dict[str, Any]:
            filters: Dict[str, Any] = {}
            if terms.get("commune"):
                filters["immeuble_ville"] = terms["commune"]
            pattern = terms.get("file_pattern")
            if isinstance(pattern, str) and pattern.strip("%"):
                filters["immeuble_nom"] = pattern
            else:
                filters["immeuble_nom"] = f"%{terms['term']}%"
            return {
                "table_name": "etats_locatifs",
                "filters": filters,
                "limit": 30,
            }

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            market = _extract_data(ctx.memory.get("market_snapshot", {})) or []
            rents = [
                float(item.get("loyer_annuel_total"))
                for item in market
                if isinstance(item, dict) and isinstance(item.get("loyer_annuel_total"), (int, float))
            ]
            avg_rent = sum(rents) / len(rents) if rents else 0.0
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
        terms = _extract_terms(query)

        def risk_params(_: ExecutionContext) -> Dict[str, Any]:
            params = {
                "seuil_vacance": float(context.get("seuil_vacance") or 0.1),
                "limit": int(context.get("limit") or 25),
            }
            if terms.get("commune"):
                params["commune"] = terms["commune"]
            return params

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            alerts = _extract_data(ctx.memory.get("risk_alerts", {})) or []
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


class LandRegistryStrategy(BaseStrategy):
    name = "land_registry"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        terms = _extract_terms(query)

        def registry_params(_: ExecutionContext) -> Dict[str, Any]:
            pattern = terms.get("file_pattern")
            filters: Dict[str, Any] = {}
            if isinstance(pattern, str) and pattern.strip("%"):
                filters["file_name"] = pattern
            else:
                filters["file_name"] = f"%{terms['term']}%"
            if terms.get("commune"):
                filters["commune"] = terms["commune"]
            return {
                "table_name": "registres_fonciers",
                "filters": filters,
                "limit": 25,
            }

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            registres = _extract_data(ctx.memory.get("land_registry_lookup", {})) or []
            servitudes = []
            for entry in registres:
                if isinstance(entry, dict):
                    data = entry.get("servitudes")
                    if isinstance(data, list):
                        servitudes.extend(data)
            sources = _collect_sources(registres)
            summary = f"Analyse registre foncier pour '{query}'."
            return {
                "summary": summary,
                "details": {"registres": registres, "servitudes": servitudes},
                "metrics": [len(registres), len(servitudes)],
                "sources": sources,
            }

        phases = [
            [
                _make_tool_step(
                    "land_registry_lookup",
                    "query_table",
                    registry_params,
                    "Recherche des registres fonciers pertinents",
                )
            ],
            [_make_aggregate_step("land_registry_summary", aggregate)],
        ]

        return ExecutionPlan(
            query=query,
            phases=phases,
            output_step="land_registry_summary",
            validation_rules=self._default_validation_rules(),
            confidence_threshold=0.75,
        )


class StakeholderStrategy(BaseStrategy):
    name = "stakeholder"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        terms = _extract_terms(query)

        def stakeholders_params(_: ExecutionContext) -> Dict[str, Any]:
            filters: Dict[str, Any] = {}
            pattern = terms.get("file_pattern")
            if isinstance(pattern, str) and pattern.strip("%"):
                filters["stakeholder_name"] = pattern
            else:
                filters["stakeholder_name"] = f"%{terms['term']}%"
            return {
                "table_name": "stakeholder_insights",
                "filters": filters,
                "limit": 25,
            }

        def aggregate(ctx: ExecutionContext) -> Dict[str, Any]:
            stakeholders = _extract_data(ctx.memory.get("stakeholder_lookup", {})) or []
            rents = [
                float(item.get("rent_total_chf") or 0)
                for item in stakeholders
                if isinstance(item, dict)
            ]
            max_rent = max(rents) if rents else 0.0
            sources = _collect_sources(stakeholders)
            summary = f"Analyse stakeholders pour '{query}'."
            return {
                "summary": summary,
                "details": {"stakeholders": stakeholders},
                "metrics": [len(stakeholders), max_rent],
                "sources": sources,
            }

        phases = [
            [
                _make_tool_step(
                    "stakeholder_lookup",
                    "query_table",
                    stakeholders_params,
                    "Recherche des stakeholders pertinents",
                )
            ],
            [_make_aggregate_step("stakeholder_summary", aggregate)],
        ]

        return ExecutionPlan(
            query=query,
            phases=phases,
            output_step="stakeholder_summary",
            validation_rules=self._default_validation_rules(),
            confidence_threshold=0.75,
        )


class SynthesisStrategy(BaseStrategy):
    name = "synthesis"

    def build_plan(self, query: str, context: Dict[str, Any]) -> ExecutionPlan:
        factual = FactualStrategy().build_plan(query, context)
        financial = FinancialStrategy().build_plan(query, context)
        comparative = ComparativeStrategy().build_plan(query, context)
        land = LandRegistryStrategy().build_plan(query, context)
        stakeholder = StakeholderStrategy().build_plan(query, context)

        async def property_details_runner(ctx: ExecutionContext) -> Dict[str, Any]:
            summary = ctx.memory.get("factual_summary") or {}
            properties = (
                summary.get("details", {}).get("properties", [])
                if isinstance(summary, dict)
                else []
            )
            details = []
            seen: set[str] = set()
            for prop in properties[:5]:
                if not isinstance(prop, dict):
                    continue
                key = prop.get("property_key")
                if not key or key in seen:
                    continue
                seen.add(key)
                raw = await ctx.call_tool(
                    "get_property_insight",
                    {
                        "property_key": key,
                        "include_documents": True,
                        "include_etat_locatif": True,
                    },
                )
                payload = _parse_tool_payload(raw)
                if payload:
                    property_info = payload.get("property") or {}
                    documents = payload.get("documents") or []
                    if not documents:
                        doc_ids = property_info.get("document_ids") or []
                        doc_details = []
                        for doc_id in doc_ids[:5]:
                            try:
                                raw_doc = await ctx.call_tool(
                                    "query_table",
                                    {
                                        "table_name": "documents_full",
                                        "filters": {"id": doc_id},
                                        "limit": 1,
                                    },
                                )
                                doc_payload = _parse_tool_payload(raw_doc)
                                if isinstance(doc_payload, list) and doc_payload:
                                    record = doc_payload[0]
                                elif isinstance(doc_payload, dict):
                                    record = doc_payload
                                else:
                                    record = None
                                if isinstance(record, dict):
                                    meta = record.get("metadata")
                                    if isinstance(meta, str):
                                        try:
                                            record["metadata"] = json.loads(meta)
                                        except Exception:
                                            record["metadata"] = {}
                                    doc_details.append(
                                        {
                                            "id": record.get("id"),
                                            "file_name": record.get("file_name"),
                                            "summary": (record.get("metadata") or {}).get(
                                                "summary_short"
                                            ),
                                            "updated_at": record.get("updated_at"),
                                        }
                                    )
                            except Exception:
                                continue
                        if doc_details:
                            payload["documents"] = doc_details
                    details.append({"property_key": key, "payload": payload})
            ctx.memory["property_details"] = {"properties": details}
            return {"properties": details}

        async def stakeholder_details_runner(ctx: ExecutionContext) -> Dict[str, Any]:
            summary = ctx.memory.get("stakeholder_summary") or {}
            stakeholders = (
                summary.get("details", {}).get("stakeholders", [])
                if isinstance(summary, dict)
                else []
            )
            details = []
            seen: set[str] = set()
            for entry in stakeholders[:5]:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("stakeholder_name") or entry.get("stakeholder")
                if not name or name in seen:
                    continue
                seen.add(name)
                raw = await ctx.call_tool(
                    "get_stakeholder_profile",
                    {"name": name, "include_properties": True},
                )
                payload = _parse_tool_payload(raw)
                if payload:
                    details.append({"stakeholder": name, "payload": payload})
            ctx.memory["stakeholder_details"] = {"stakeholders": details}
            return {"stakeholders": details}

        def _parse_tool_payload(raw: Any) -> Optional[Dict[str, Any]]:
            if raw is None:
                return None
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except Exception:
                    return None
            elif isinstance(raw, dict):
                parsed = raw
            else:
                return None
            if isinstance(parsed, dict):
                if parsed.get("success") is False:
                    return None
                return parsed.get("data") or parsed
            return None

        property_details_step = ExecutionStep(
            name="property_details",
            func=property_details_runner,
            description="Collecte détaillée des fiches immeuble",
        )

        stakeholder_details_step = ExecutionStep(
            name="stakeholder_details",
            func=stakeholder_details_runner,
            description="Profilage détaillé des stakeholders",
        )

        synthesis_step = _make_aggregate_step(
            "synthesis_summary",
            lambda ctx: _build_synthesis_summary(ctx, query),
        )

        phases: List[List[ExecutionStep]] = []
        phases.extend(factual.phases)
        phases.append([property_details_step])
        phases.extend(financial.phases)
        phases.extend(comparative.phases)
        phases.extend(land.phases)
        phases.extend(stakeholder.phases)
        phases.append([stakeholder_details_step])
        phases.append([synthesis_step])

        return ExecutionPlan(
            query=query,
            phases=phases,
            output_step="synthesis_summary",
            validation_rules=self._default_validation_rules(),
            confidence_threshold=max(
                factual.confidence_threshold,
                financial.confidence_threshold,
                comparative.confidence_threshold,
                land.confidence_threshold,
                stakeholder.confidence_threshold,
            ),
            metadata={"strategy": "synthesis", "query": query},
        )


def _build_synthesis_summary(ctx: ExecutionContext, query: str) -> Dict[str, Any]:
    factual = ctx.memory.get("factual_summary") or {}
    financial = ctx.memory.get("financial_summary") or {}
    comparative = ctx.memory.get("comparative_summary") or {}
    land = ctx.memory.get("land_registry_summary") or {}
    stakeholders = ctx.memory.get("stakeholder_summary") or {}
    property_details = ctx.memory.get("property_details") or {}
    stakeholder_details = ctx.memory.get("stakeholder_details") or {}

    properties_payload = []
    financial_rollup_total = 0.0
    financial_rollup_base = 0.0
    vacancy_flags: List[Dict[str, Any]] = []
    documents_payload = []

    for entry in property_details.get("properties", []):
        if not isinstance(entry, dict):
            continue
        key = entry.get("property_key")
        payload = entry.get("payload") or {}
        property_info = payload.get("property") or {}
        etat = payload.get("etat_locatif") or {}
        documents = payload.get("documents") or []
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            doc_entry = {
                "file_name": doc.get("file_name"),
                "document_id": doc.get("id"),
                "summary": doc.get("summary"),
                "updated_at": doc.get("updated_at"),
                "source": key,
            }
            if doc_entry not in documents_payload:
                documents_payload.append(doc_entry)
        rent_total = (
            property_info.get("rent_total_chf")
            or (etat.get("loyer_annuel_total"))
            or 0.0
        )
        rent_principal = property_info.get("rent_principal_chf") or 0.0
        try:
            rent_total = float(rent_total or 0.0)
        except (TypeError, ValueError):
            rent_total = 0.0
        try:
            rent_principal = float(rent_principal or 0.0)
        except (TypeError, ValueError):
            rent_principal = 0.0
        financial_rollup_total += rent_total
        financial_rollup_base += rent_principal

        if etat:
            vacance = etat.get("taux_vacance_financier")
            try:
                vacance = float(vacance)
            except (TypeError, ValueError):
                vacance = None
            if vacance and vacance > 0.1:
                vacancy_flags.append(
                    {
                        "property_key": key,
                        "taux_vacance_financier": vacance,
                        "nb_unites_vacantes": etat.get("nb_unites_vacantes"),
                        "nb_unites_louees": etat.get("nb_unites_louees"),
                    }
                )

        properties_payload.append(
            {
                "property_key": key,
                "addresses": property_info.get("addresses"),
                "cantons": property_info.get("cantons"),
                "communes": property_info.get("communes"),
                "postal_codes": property_info.get("postal_codes"),
                "document_count": property_info.get("document_count"),
                "rent_total_chf": rent_total,
                "rent_principal_chf": rent_principal,
                "etat_locatif": etat,
            }
        )

    stakeholder_payload = stakeholder_details.get("stakeholders") or []

    metrics = {
        "property_count": len(properties_payload),
        "document_count": len(documents_payload),
        "stakeholder_count": len(stakeholder_payload),
        "rent_total_chf": round(financial_rollup_total, 2),
        "rent_principal_chf": round(financial_rollup_base, 2),
    }

    summary_lines = [
        f"Analyse exhaustive pour « {query} »",
        f"- Propriétés identifiées : {metrics['property_count']}",
        f"- Documents indexés : {metrics['document_count']}",
        f"- Loyers annuels (totaux estimés) : {metrics['rent_total_chf']:.2f} CHF",
    ]
    if vacancy_flags:
        summary_lines.append(
            f"- Risques vacance : {len(vacancy_flags)} propriétés dépassent 10% de vacance"
        )

    sources = _collect_sources(factual, financial, comparative, land, stakeholders)
    for entry in properties_payload:
        key = entry.get("property_key")
        if key:
            pk_source = f"property:{key}"
            if pk_source not in sources:
                sources.append(pk_source)
    for doc in documents_payload:
        file_name = doc.get("file_name")
        if file_name:
            doc_source = f"doc:{file_name}"
            if doc_source not in sources:
                sources.append(doc_source)

    return {
        "summary": "\n".join(summary_lines),
        "details": {
            "factual": factual,
            "financial": financial,
            "comparative": comparative,
            "land_registry": land,
            "stakeholders": stakeholders,
            "properties": properties_payload,
            "property_details": property_details,
            "stakeholder_details": stakeholder_payload,
            "documents": documents_payload,
            "vacancy_flags": vacancy_flags,
        },
        "metrics": metrics,
        "sources": sources,
    }


STRATEGIES: Dict[str, BaseStrategy] = {
    "factual": FactualStrategy(),
    "financial": FinancialStrategy(),
    "comparative": ComparativeStrategy(),
    "risk": RiskAssessmentStrategy(),
    "land_registry": LandRegistryStrategy(),
    "stakeholder": StakeholderStrategy(),
    "synthesis": SynthesisStrategy(),
}

