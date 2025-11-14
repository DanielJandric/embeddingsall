#!/usr/bin/env python3
"""
Ultimate MCP tools for Swiss real-estate due diligence.

This module centralises advanced data-access and analytics capabilities that
can be exposed to the MCP server.  Each tool returns a response following the
standard format requested by the user:

{
    "success": bool,
    "data": Any,
    "metadata": {
        "execution_time_ms": float,
        "cached": bool,
        "data_sources": list[str],
        "count": int,
        "query_cost": int,
        "warnings": list[str]
    },
    "error": {
        "code": str,
        "message": str,
        "details": dict
    } | None
}
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import statistics
import time
import unicodedata
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from supabase import create_client, Client

# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------


@dataclass
class ToolResponse:
    success: bool
    data: Any = None
    execution_time_ms: Optional[float] = None
    cached: bool = False
    data_sources: Optional[List[str]] = None
    count: Optional[int] = None
    query_cost: int = 0
    warnings: Optional[List[str]] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "metadata": {
                "execution_time_ms": self.execution_time_ms,
                "cached": self.cached,
                "data_sources": self.data_sources or [],
                "count": self.count,
                "query_cost": self.query_cost,
                "warnings": self.warnings or [],
            },
            "error": self.error,
        }


# -----------------------------------------------------------------------------
# Ultimate tools implementation
# -----------------------------------------------------------------------------


class UltimateTools:
    """
    Central facility exposing all the analytical tools required by the MCP server.
    Where data is not yet available, the methods return a structured “not_available”
    error so that the client can react accordingly.
    """

    SUPPORTED_DATA_SOURCES = ["supabase"]
    ADDRESS_MARKERS = [
        " loyers",
        "loyers",
        "miete",
        "beilagen",
        "état",
        "etat",
        "annexe",
        "annexes",
        "periode",
        "période",
        "detail",
        "détail",
        "objet",
        "locataire",
        "gestionnaire",
        "verwalter",
        "payable",
        "en faveur",
        "reference",
        "référence",
        "procimmo",
        "domicim",
        "tableau",
    ]
    COMMUNE_STOPWORDS = {
        "loyers",
        "annexes",
        "miete",
        "état",
        "etat",
        "detail",
        "détail",
        "tableau",
        "resume",
        "résumé",
        "domicim",
    }

    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("Supabase credentials are missing in environment variables.")
        self.client: Client = create_client(url, key)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now_ms() -> float:
        return time.time() * 1000.0

    def _response(
        self,
        success: bool,
        data: Any = None,
        *,
        start_ms: Optional[float] = None,
        warnings: Optional[List[str]] = None,
        error: Optional[Dict[str, Any]] = None,
        query_cost: int = 0,
    ) -> Dict[str, Any]:
        end_ms = self._now_ms()
        exec_time = (end_ms - start_ms) if start_ms is not None else None
        count = None
        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            count = len(data["items"])
        resp = ToolResponse(
            success=success,
            data=self._to_serializable(data),
            execution_time_ms=exec_time,
            cached=False,
            data_sources=self.SUPPORTED_DATA_SOURCES.copy(),
            count=count,
            query_cost=query_cost,
            warnings=warnings,
            error=error,
        )
        return resp.to_dict()

    @staticmethod
    def _error(code: str, message: str, *, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"code": code, "message": message, "details": details or {}}

    def _not_available(self, feature: str, start_ms: float) -> Dict[str, Any]:
        return self._response(
            False,
            data=None,
            start_ms=start_ms,
            error=self._error("not_available", f"La fonctionnalité « {feature} » n'est pas encore disponible."),
        )

    def _query_table(self, table: str, *, filters: Optional[Dict[str, Any]] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        query = self.client.table(table).select("*")
        if filters:
            for key, value in filters.items():
                if value is None:
                    continue
                if isinstance(value, str) and "%" in value:
                    query = query.ilike(key, value)
                else:
                    query = query.eq(key, value)
        if limit:
            query = query.limit(limit)
        result = query.execute()
        return result.data or []

    @staticmethod
    def _to_serializable(data: Any) -> Any:
        if isinstance(data, dict):
            return {k: UltimateTools._to_serializable(v) for k, v in data.items()}
        if isinstance(data, list):
            return [UltimateTools._to_serializable(v) for v in data]
        if isinstance(data, (pd.Series, pd.DataFrame)):
            return json.loads(data.to_json(orient="records"))
        if isinstance(data, (pd.Timestamp, pd.Timedelta)):
            return data.isoformat()
        return data

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        if not value:
            return ""
        value = unicodedata.normalize("NFKD", value)
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.lower()
        value = re.sub(r"[^\w\s-]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @classmethod
    def _slugify(cls, value: Optional[str]) -> str:
        normalized = cls._normalize_text(value)
        if not normalized:
            return ""
        normalized = unicodedata.normalize("NFKD", normalized)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = normalized.lower()
        normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
        tokens = [tok for tok in normalized.split("-") if tok]
        deduped: List[str] = []
        for tok in tokens:
            if deduped and tok == deduped[-1]:
                continue
            deduped.append(tok)
        if len(deduped) > 8:
            deduped = deduped[:8]
        return "-".join(deduped)

    @staticmethod
    def _jsonify_field(row: Dict[str, Any], field: str) -> None:
        value = row.get(field)
        if isinstance(value, str):
            try:
                row[field] = json.loads(value)
            except Exception:
                pass

    def _clean_fragment(self, value: Optional[str]) -> str:
        text = self._normalize_text(value)
        lowered = text.lower()
        for marker in self.ADDRESS_MARKERS:
            idx = lowered.find(marker)
            if idx != -1:
                text = text[:idx]
                lowered = text[:idx].lower()
        text = re.sub(r"\b(n°|no|numero|numéro)\b.*", "", text, flags=re.IGNORECASE)
        return text.strip()

    def _clean_commune(self, value: Optional[str]) -> str:
        text = self._normalize_text(value)
        lowered = text.lower()
        for marker in self.COMMUNE_STOPWORDS:
            idx = lowered.find(marker)
            if idx > 0:
                text = text[:idx]
                break
        return text.strip()

    def _canonical_property_signature(self, row: Dict[str, Any]) -> Tuple[str, str]:
        address = self._clean_fragment(
            row.get("immeuble_adresse")
            or row.get("address")
            or row.get("file_path")
        )
        ville = self._clean_commune(row.get("immeuble_ville"))
        canton = self._clean_fragment(row.get("immeuble_canton"))
        nom = self._clean_fragment(row.get("immeuble_nom"))
        reference = self._clean_fragment(row.get("immeuble_ref"))

        slug_source = " ".join(
            part for part in [nom, address, ville, canton, reference] if part
        )
        slug = self._slugify(slug_source)
        if not slug:
            fallback = row.get("id")
            slug = f"etat-{fallback}" if fallback is not None else ""

        label_parts = [part for part in [nom, address, ville] if part]
        label = " | ".join(label_parts) or slug or "immeuble-inconnu"
        return slug, label

    def _fetch_related_documents(self, property_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            query = (
                self.client.table("documents_full")
                .select("id, file_name, metadata, updated_at")
                .eq("metadata->>property_key", property_key)
                .limit(limit)
            )
            result = query.execute()
            documents = result.data or []
            for doc in documents:
                meta = doc.get("metadata")
                if isinstance(meta, str):
                    try:
                        doc["metadata"] = json.loads(meta)
                    except Exception:
                        doc["metadata"] = {}
            return documents
        except Exception:
            return []

    def _fetch_linked_etat(
        self, property_key: str, property_record: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        if not property_key:
            return None
        try:
            result = (
                self.client.table("etats_locatifs")
                .select("*")
                .eq("metadata->>property_key", property_key)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
        except Exception:
            pass
        patterns: List[str] = []
        slug_pattern = property_key.replace("-", "%")
        patterns.append(slug_pattern)
        tokens = [tok for tok in property_key.split("-") if tok]
        stop_tokens = {"avenue", "av", "de", "la", "le", "les", "baujahr", "immeuble", "suisse"}
        core_tokens = [tok for tok in tokens if tok and tok not in stop_tokens]
        if core_tokens:
            patterns.append("%".join(core_tokens))
        numeric_tokens = [tok for tok in core_tokens if any(ch.isdigit() for ch in tok)]
        textual_tokens = [tok for tok in core_tokens if tok not in numeric_tokens]
        if textual_tokens and numeric_tokens:
            compact = numeric_tokens + textual_tokens
            patterns.append("%".join(compact))
        if property_record:
            addresses = property_record.get("addresses") or []
            for addr in addresses:
                if not isinstance(addr, str):
                    continue
                normalized = unicodedata.normalize("NFKD", addr).encode("ascii", "ignore").decode("ascii")
                normalized = normalized.lower()
                normalized = normalized.replace("avenue", "av")
                normalized = re.sub(r"[^a-z0-9]+", "%", normalized)
                normalized = re.sub(r"%+", "%", normalized).strip("%")
                if normalized:
                    patterns.append(normalized)
        base_tokens = [
            tok
            for tok in core_tokens
            if tok in {"gare", "martigny"} or any(ch.isdigit() for ch in tok)
        ]
        if len(base_tokens) >= 2:
            for size in range(len(base_tokens), 1, -1):
                for start in range(0, len(base_tokens) - size + 1):
                    slice_tokens = base_tokens[start : start + size]
                    if "martigny" not in slice_tokens:
                        continue
                    if not any(any(ch.isdigit() for ch in tok) for tok in slice_tokens):
                        continue
                    patterns.append("%".join(slice_tokens))
        patterns.extend(core_tokens)
        deduped: List[str] = []
        seen: set[str] = set()
        for raw in patterns:
            trimmed = raw.strip("%")
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            deduped.append(trimmed)
        patterns = deduped
        for pattern in patterns:
            try:
                fallback = (
                    self.client.table("etats_locatifs")
                    .select("*")
                    .ilike("file_path", f"%{pattern}%")
                    .limit(1)
                    .execute()
                )
                if fallback.data:
                    return fallback.data[0]
            except Exception:
                continue
        return None

    async def _run_async(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # ------------------------------------------------------------------
    # Category 1 – structured data access
    # ------------------------------------------------------------------

    def get_registre_foncier(self, **kwargs) -> Dict[str, Any]:
        """
        Récupère les informations du registre foncier pour une parcelle/commune/adresse.

        Args (via kwargs):
            parcelle_id (Optional[str]): Numéro de parcelle à rechercher.
            commune (Optional[str]): Commune ciblée.
            adresse (Optional[str]): Filtre libre sur le nom de fichier/adresse.
            include_history (bool): Inclure l'historique des mutations (défaut False).

        Returns:
            Dict[str, Any]: Réponse standardisée contenant les enregistrements trouvés.

        Example:
            >>> tools.get_registre_foncier(commune="Fribourg", include_history=False)
        """
        start = self._now_ms()
        parcelle_id = kwargs.get("parcelle_id")
        commune = kwargs.get("commune")
        adresse = kwargs.get("adresse")
        include_history = bool(kwargs.get("include_history", False))

        filters = {}
        if parcelle_id:
            filters["no_parcelle"] = parcelle_id
        if commune:
            filters["commune"] = commune
        if adresse:
            filters["file_name"] = f"%{adresse}%"
        rows = self._query_table("registres_fonciers", filters=filters, limit=50)
        if not rows:
            return self._response(
                True,
                data=[],
                start_ms=start,
                warnings=[f"Aucun registre foncier trouvé pour les critères fournis."],
            )
        # Flatten servitudes/gages to make consumption easier.
        for row in rows:
            if row.get("servitudes") and isinstance(row["servitudes"], str):
                try:
                    row["servitudes"] = json.loads(row["servitudes"])
                except Exception:
                    pass
            if row.get("gages_immobiliers") and isinstance(row["gages_immobiliers"], str):
                try:
                    row["gages_immobiliers"] = json.loads(row["gages_immobiliers"])
                except Exception:
                    pass
            if not include_history:
                row.pop("mutations", None)
        return self._response(True, data=rows, start_ms=start)

    def search_servitudes(self, **kwargs) -> Dict[str, Any]:
        """
        Recherche les servitudes depuis les registres fonciers.

        Args (via kwargs):
            type_servitude (Optional[str]): Filtre sur le type de servitude.
            commune (Optional[str]): Commune ciblée.
            impactant_valeur (Optional[bool]): Filtre sur l'impact financier.

        Returns:
            Dict[str, Any]: Liste des servitudes correspondantes.
        """
        start = self._now_ms()
        type_servitude = kwargs.get("type_servitude")
        commune = kwargs.get("commune")
        impactant_valeur = kwargs.get("impactant_valeur")

        filters: Dict[str, Any] = {}
        if commune:
            filters["commune"] = commune
        rows = self._query_table("registres_fonciers", filters=filters, limit=200)
        servitudes: List[Dict[str, Any]] = []
        for row in rows:
            data = row.get("servitudes")
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = []
            if not isinstance(data, list):
                continue
            for item in data:
                if type_servitude and item.get("type") != type_servitude:
                    continue
                if impactant_valeur is not None:
                    impacts = item.get("impact_valeur")
                    if bool(impacts) != impactant_valeur:
                        continue
                servitudes.append(
                    {
                        "parcelle": row.get("no_parcelle"),
                        "commune": row.get("commune"),
                        "type": item.get("type"),
                        "description": item.get("description"),
                        "fonds_servant": item.get("fonds_servant"),
                        "fonds_dominant": item.get("fonds_dominant"),
                        "date": item.get("date_constitution"),
                        "document_id": row.get("id"),
                    }
                )
        return self._response(True, data=servitudes, start_ms=start, warnings=[] if servitudes else ["Aucune servitude correspondante."])

    def analyze_charges_foncieres(self, **kwargs) -> Dict[str, Any]:
        """
        Analyse les charges foncières d'une parcelle (gages, servitudes).

        Args (via kwargs):
            parcelle_id (str): Numéro de parcelle (obligatoire).

        Returns:
            Dict[str, Any]: Informations financières liées à la parcelle.
        """
        start = self._now_ms()
        parcelle_id = kwargs.get("parcelle_id")

        if not parcelle_id:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "parcelle_id est obligatoire."),
            )
        rows = self._query_table("registres_fonciers", filters={"no_parcelle": parcelle_id}, limit=1)
        if not rows:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("not_found", f"Aucun registre foncier pour la parcelle {parcelle_id}."),
            )
        row = rows[0]
        gages = row.get("gages_immobiliers")
        if isinstance(gages, str):
            try:
                gages = json.loads(gages)
            except Exception:
                gages = []
        total_gages = 0.0
        if isinstance(gages, list):
            for g in gages:
                try:
                    total_gages += float(g.get("montant", 0))
                except Exception:
                    continue
        servitudes = row.get("servitudes")
        if isinstance(servitudes, str):
            try:
                servitudes = json.loads(servitudes)
            except Exception:
                servitudes = []
        data = {
            "parcelle": parcelle_id,
            "commune": row.get("commune"),
            "charges_foncieres_estimees_chf": total_gages,
            "nb_servitudes": len(servitudes) if isinstance(servitudes, list) else 0,
            "detail_gages": gages,
            "detail_servitudes": servitudes,
        }
        return self._response(True, data=data, start_ms=start)

    # ------------------- États locatifs ---------------------------------

    def get_etat_locatif_complet(self, **kwargs) -> Dict[str, Any]:
        """
        Retourne l'état locatif complet pour un immeuble avec KPI calculés.

        Args (via kwargs):
            immeuble_id (Optional[str]): Identifiant de l'état locatif.
            adresse (Optional[str]): Filtre sur le nom/adresse.
            date_reference (Optional[str]): Non utilisé actuellement, conservé pour compatibilité.

        Returns:
            Dict[str, Any]: Liste d'états locatifs enrichis.
        """
        start = self._now_ms()
        immeuble_id = kwargs.get("immeuble_id")
        adresse = kwargs.get("adresse")
        # date_reference accepté mais inutilisé pour l'instant

        filters = {}
        if immeuble_id:
            filters["id"] = immeuble_id
        if adresse:
            filters["file_name"] = f"%{adresse}%"
        rows = self._query_table("etats_locatifs", filters=filters, limit=5)
        if not rows:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("not_found", "Aucun état locatif trouvé pour les critères fournis."),
            )
        df = pd.DataFrame(rows)
        numeric_cols = [
            "loyer_annuel_total",
            "loyer_annuel_effectif",
            "charges_annuelles",
            "surface_totale_m2",
            "surface_louee_m2",
            "surface_vacante_m2",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["loyer_net"] = df["loyer_annuel_effectif"] - df["charges_annuelles"].fillna(0)
        df["taux_occupation_surface"] = df["taux_occupation_surface"].fillna(
            (df["surface_louee_m2"] / df["surface_totale_m2"]).replace([math.inf, -math.inf], 0)
        )
        df["taux_occupation_unites"] = df["taux_occupation_unites"].fillna(
            (df["nb_unites_louees"] / (df["nb_unites_louees"] + df["nb_unites_vacantes"])).replace([math.inf, -math.inf], 0)
        )
        result = df.to_dict(orient="records")
        return self._response(True, data=result, start_ms=start)

    def analyze_loyers_marche(self, **kwargs) -> Dict[str, Any]:
        """
        Compare les loyers observés à la moyenne de marché dans un rayon donné.

        Args (via kwargs):
            adresse (str): Adresse de référence (obligatoire).
            usage (Optional[str]): Type d'usage (bureau, commerce, etc.).
            rayon_km (float): Rayon de recherche en km (défaut 2.0).

        Returns:
            Dict[str, Any]: Statistiques agrégées (moyenne, médiane, percentiles).
        """
        start = self._now_ms()
        adresse = kwargs.get("adresse")
        usage = kwargs.get("usage")
        try:
            rayon_km = float(kwargs.get("rayon_km", 2.0))
        except (TypeError, ValueError):
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "rayon_km doit être un nombre."),
            )

        if not adresse:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "adresse est obligatoire."),
            )

        rows = self._query_table("etats_locatifs", filters=None, limit=1000)
        if not rows:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("not_found", "Aucun état locatif disponible pour l'analyse."),
            )
        df = pd.DataFrame(rows)
        for col in ["loyer_annuel_effectif", "surface_totale_m2"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["loyer_m2"] = df["loyer_annuel_effectif"] / df["surface_totale_m2"].replace(0, pd.NA)

        # Filtre basique par commune incluant l'adresse si possible
        commune_mask = df["immeuble_ville"].str.contains(adresse.split(" ")[0], case=False, na=False)
        subset = df[commune_mask] if commune_mask.any() else df

        stats = {
            "loyer_m2_moyen": float(subset["loyer_m2"].mean(skipna=True)),
            "loyer_m2_mediane": float(subset["loyer_m2"].median(skipna=True)),
            "loyer_m2_p90": float(subset["loyer_m2"].quantile(0.9)),
            "loyer_m2_p10": float(subset["loyer_m2"].quantile(0.1)),
            "echantillon": int(len(subset)),
            "rayon_km": rayon_km,
            "usage": usage,
        }
        return self._response(True, data=stats, start_ms=start, warnings=[] if subset.size else ["Filtre trop restreint, utilisation des données nationales."])

    def detect_anomalies_locatives(self, **kwargs) -> Dict[str, Any]:
        """
        Détecte les anomalies locatives (loyer sous marché, vacance élevée).

        Args (via kwargs):
            immeuble_id (str): Identifiant de l'état locatif (obligatoire).

        Returns:
            Dict[str, Any]: Liste d'anomalies identifiées.
        """
        start = self._now_ms()
        immeuble_id = kwargs.get("immeuble_id")

        if not immeuble_id:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "immeuble_id est obligatoire."),
            )
        rows = self._query_table("etats_locatifs", filters={"id": immeuble_id}, limit=1)
        if not rows:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("not_found", f"Aucun état locatif pour l'immeuble {immeuble_id}."),
            )
        target = rows[0]
        commune = target.get("immeuble_ville")
        comparables = self._query_table("etats_locatifs", filters={"immeuble_ville": commune}, limit=200)
        df = pd.DataFrame(comparables)
        for col in ["loyer_annuel_effectif", "surface_totale_m2"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["loyer_m2"] = df["loyer_annuel_effectif"] / df["surface_totale_m2"].replace(0, pd.NA)
        benchmark = df["loyer_m2"].median(skipna=True)
        target_loyer_m2 = (
            pd.to_numeric(target.get("loyer_annuel_effectif"), errors="coerce")
            / pd.to_numeric(target.get("surface_totale_m2"), errors="coerce")
            if target.get("surface_totale_m2")
            else None
        )
        anomalies = []
        if benchmark and target_loyer_m2:
            if target_loyer_m2 < benchmark * 0.8:
                anomalies.append(
                    {
                        "type": "loyer_sous_marche",
                        "loyer_m2": target_loyer_m2,
                        "benchmark_median": benchmark,
                        "delta_pct": (target_loyer_m2 / benchmark) - 1,
                    }
                )
        if target.get("nb_unites_vacantes"):
            vacantes = int(target["nb_unites_vacantes"])
            total = vacantes + int(target.get("nb_unites_louees") or 0)
            taux = vacantes / total if total else 0
            if taux > 0.1:
                anomalies.append(
                    {
                        "type": "vacance_elevee",
                        "taux_vacance": taux,
                        "nb_vacantes": vacantes,
                        "total_unites": total,
                    }
                )
        return self._response(True, data=anomalies, start_ms=start)

    # ------------------- Property & stakeholder insights -----------------

    def get_property_insight(self, **kwargs) -> Dict[str, Any]:
        """
        Récupère la fiche d'un immeuble agrégé par la phase 2.

        Args (via kwargs):
            property_key (Optional[str]): Identifiant unique (slug).
            property_label (Optional[str]): Libellé lisible pour recherche approximative.
            adresse (Optional[str]): Adresse brute pour retrouver l'immeuble.
            include_documents (bool): Inclure la liste des documents associés (défaut True).
            include_etat_locatif (bool): Ajouter l'état locatif lié (défaut True).
        """
        start = self._now_ms()
        property_key = kwargs.get("property_key")
        property_label = kwargs.get("property_label")
        adresse = kwargs.get("adresse")
        include_documents = kwargs.get("include_documents", True)
        include_etat = kwargs.get("include_etat_locatif", True)

        query = self.client.table("property_insights").select("*")
        if property_key:
            query = query.eq("property_key", property_key)
        elif property_label:
            query = query.ilike("property_label", f"%{property_label}%")
        elif adresse:
            slug = self._slugify(adresse)
            if slug:
                query = query.eq("property_key", slug)
        else:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "property_key, property_label ou adresse doit être fourni."),
            )

        try:
            result = query.limit(1).execute()
        except Exception as exc:
            return self._response(False, data=None, start_ms=start, error=self._error("query_failed", str(exc)))

        if not result.data:
            hint = property_key or property_label or adresse
            return self._response(
                True,
                data=None,
                start_ms=start,
                warnings=[f"Aucun insight disponible pour « {hint} »."],
            )

        record = result.data[0]
        for field in ["addresses", "cantons", "communes", "postal_codes", "document_ids", "document_types", "tenants", "landlords", "organisations"]:
            self._jsonify_field(record, field)

        key = record.get("property_key")
        complement = {}

        if include_documents and key:
            documents = self._fetch_related_documents(key, limit=10)
            complement["documents"] = [
                {
                    "id": doc.get("id"),
                    "file_name": doc.get("file_name"),
                    "summary": (doc.get("metadata") or {}).get("summary_short"),
                    "updated_at": doc.get("updated_at"),
                }
                for doc in documents
            ]

        if include_etat and key:
            etat = self._fetch_linked_etat(key, record)
            if etat:
                complement["etat_locatif"] = {
                    "immeuble_nom": etat.get("immeuble_nom"),
                    "immeuble_adresse": etat.get("immeuble_adresse"),
                    "loyer_annuel_total": etat.get("loyer_annuel_total"),
                    "taux_occupation_surface": etat.get("taux_occupation_surface"),
                    "taux_vacance_financier": etat.get("taux_vacance_financier"),
                    "nb_unites_louees": etat.get("nb_unites_louees"),
                    "nb_unites_vacantes": etat.get("nb_unites_vacantes"),
                }

        payload = {"property": record, **complement}
        return self._response(True, data=payload, start_ms=start)

    def get_stakeholder_profile(self, **kwargs) -> Dict[str, Any]:
        """
        Récupère la fiche d'un acteur (locataire/bailleur) agrégé.

        Args (via kwargs):
            name (str): Nom du stakeholder (obligatoire).
            stakeholder_type (Optional[str]): "tenant" ou "landlord".
            include_properties (bool): Joindre les insights immeuble (défaut True).
        """
        start = self._now_ms()
        name = kwargs.get("name")
        stakeholder_type = kwargs.get("stakeholder_type")
        include_properties = kwargs.get("include_properties", True)

        if not name:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "name est obligatoire."),
            )

        query = self.client.table("stakeholder_insights").select("*")
        query = query.ilike("stakeholder_name", f"%{name}%")
        if stakeholder_type:
            query = query.eq("stakeholder_type", stakeholder_type)

        try:
            result = query.limit(5).execute()
        except Exception as exc:
            return self._response(False, data=None, start_ms=start, error=self._error("query_failed", str(exc)))

        rows = result.data or []
        if not rows:
            return self._response(
                True,
                data=[],
                start_ms=start,
                warnings=[f"Aucun stakeholder correspondant à « {name} »."],
            )

        for row in rows:
            for field in ["properties", "document_ids"]:
                self._jsonify_field(row, field)

        payload = []
        for row in rows:
            entry = {"stakeholder": row}
            if include_properties:
                linked_props = []
                properties = row.get("properties") or []
                for prop_key in properties[:5]:
                    if isinstance(prop_key, str):
                        prop_resp = self.client.table("property_insights").select("property_key, property_label, cantons, communes").eq("property_key", prop_key).limit(1).execute()
                        if prop_resp.data:
                            detail = prop_resp.data[0]
                            for field in ["cantons", "communes"]:
                                self._jsonify_field(detail, field)
                            linked_props.append(detail)
                entry["linked_properties"] = linked_props
            payload.append(entry)

        return self._response(True, data=payload, start_ms=start)

    def find_vacancy_alerts(self, **kwargs) -> Dict[str, Any]:
        """
        Identifie les immeubles avec un risque de vacance élevé.

        Args (via kwargs):
            canton (Optional[str]): Filtrer par canton.
            commune (Optional[str]): Filtrer par commune.
            seuil_vacance (float): Taux de vacance financier seuil (défaut 0.1 = 10%).
            limit (int): Nombre max de résultats (défaut 25).
        """
        start = self._now_ms()
        canton = kwargs.get("canton")
        commune = kwargs.get("commune")
        limit = int(kwargs.get("limit", 25))
        try:
            seuil_vacance = float(kwargs.get("seuil_vacance", 0.1))
        except (TypeError, ValueError):
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "seuil_vacance doit être numérique."),
            )

        filters = {}
        if canton:
            filters["immeuble_canton"] = canton
        if commune:
            filters["immeuble_ville"] = commune

        rows = self._query_table("etats_locatifs", filters=filters, limit=1000)
        aggregated: Dict[str, Dict[str, Any]] = {}

        for row in rows:
            try:
                taux_financier = row.get("taux_vacance_financier")
                if taux_financier is None:
                    vacantes = float(row.get("nb_unites_vacantes") or 0)
                    total = vacantes + float(row.get("nb_unites_louees") or 0)
                    taux_financier = vacantes / total if total else 0.0
                taux_financier = float(taux_financier)
            except (TypeError, ValueError):
                continue

            if taux_financier < seuil_vacance:
                continue

            slug, label = self._canonical_property_signature(row)
            if not slug:
                slug = f"etat-{row.get('id')}"

            entry = aggregated.setdefault(
                slug,
                {
                    "property_key": slug,
                    "property_label": label,
                    "ville": self._clean_commune(row.get("immeuble_ville")) or row.get("immeuble_ville"),
                    "canton": self._clean_fragment(row.get("immeuble_canton")) or row.get("immeuble_canton"),
                    "source_ids": [],
                    "max_vacance": 0.0,
                    "max_loyer": 0.0,
                    "max_vacantes": 0.0,
                    "max_total_units": 0.0,
                },
            )

            entry["source_ids"].append(row.get("id"))
            entry["max_vacance"] = max(entry["max_vacance"], taux_financier)
            try:
                loyer = float(row.get("loyer_annuel_total") or 0)
            except (TypeError, ValueError):
                loyer = 0.0
            entry["max_loyer"] = max(entry["max_loyer"], loyer)

            try:
                vacantes = float(row.get("nb_unites_vacantes") or 0)
            except (TypeError, ValueError):
                vacantes = 0.0
            try:
                louees = float(row.get("nb_unites_louees") or 0)
            except (TypeError, ValueError):
                louees = 0.0
            entry["max_vacantes"] = max(entry["max_vacantes"], vacantes)
            entry["max_total_units"] = max(entry["max_total_units"], vacantes + louees)

        alerts = [
            {
                "property_key": data["property_key"],
                "property_label": data["property_label"],
                "ville": data["ville"],
                "canton": data["canton"],
                "taux_vacance_financier": data["max_vacance"],
                "loyer_annuel_total_max": data["max_loyer"],
                "nb_unites_vacantes_max": data["max_vacantes"],
                "nb_unites_total_max": data["max_total_units"],
                "source_count": len(data["source_ids"]),
                "source_ids": data["source_ids"],
            }
            for data in aggregated.values()
        ]
        alerts.sort(key=lambda item: item.get("taux_vacance_financier", 0), reverse=True)
        if limit:
            alerts = alerts[:limit]

        warnings = []
        if not alerts:
            warnings.append("Aucune vacance significative trouvée avec les filtres fournis.")

        return self._response(True, data=alerts, start_ms=start, warnings=warnings)

    def get_echeancier_baux(self, **kwargs) -> Dict[str, Any]:
        """
        Échéancier des baux pour un immeuble (placeholder).

        Args (via kwargs):
            immeuble_id (Optional[str]): Identifiant de l'immeuble.
            periode_mois (int): Période de projection en mois (défaut 24).

        Returns:
            Dict[str, Any]: Placeholder indiquant la non disponibilité actuelle.
        """
        start = self._now_ms()
        # TODO: Need dedicated table (baux) not yet available.
        return self._not_available("get_echeancier_baux", start)

    # ------------------------------------------------------------------
    # Category 2 – SQL & analytics
    # ------------------------------------------------------------------

    def query_table(self, **kwargs) -> Dict[str, Any]:
        """
        Requête flexible sur une table Supabase.

        Args (via kwargs):
            table_name (str): Nom de la table (obligatoire).
            filters (Optional[dict]): Dictionnaire de filtres colonne -> valeur.
            select (str): Colonnes à sélectionner (défaut "*").
            joins (Optional[list]): Non supporté pour le moment.
            order_by (Optional[str]): Clause ORDER BY (ex: "created_at desc").
            limit (int): Limite de lignes (défaut 100).
            offset (int): Offset de pagination (défaut 0).

        Returns:
            Dict[str, Any]: Résultats de la requête.
        """
        start = self._now_ms()
        table_name = kwargs.get("table_name")
        if not table_name:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "table_name est obligatoire."),
            )
        filters = kwargs.get("filters") or {}
        select = kwargs.get("select", "*")
        joins = kwargs.get("joins")
        order_by = kwargs.get("order_by")
        limit = int(kwargs.get("limit", 100))
        offset = int(kwargs.get("offset", 0))

        if joins:
            return self._not_available("query_table (joins)", start)
        try:
            query = self.client.table(table_name).select(select)
            if filters:
                for key, value in filters.items():
                    if isinstance(value, str) and value.startswith("%"):
                        query = query.ilike(key, value)
                    else:
                        query = query.eq(key, value)
            if order_by:
                parts = order_by.split()
                col = parts[0]
                ascending = len(parts) == 1 or parts[1].lower() != "desc"
                query = query.order(col, desc=not ascending)
            if offset:
                query = query.range(offset, offset + limit - 1)
            else:
                query = query.limit(limit)
            result = query.execute()
            return self._response(True, data=result.data, start_ms=start)
        except Exception as exc:
            return self._response(False, data=None, start_ms=start, error=self._error("query_failed", str(exc)))

    def execute_raw_sql(self, **kwargs) -> Dict[str, Any]:
        """
        Exécute une requête SQL brute (placeholder).

        Args (via kwargs):
            query (str): Requête SQL.
            params (Optional[dict]): Paramètres.
            read_only (bool): Lecture seule (défaut True).

        Returns:
            Dict[str, Any]: Placeholder indiquant la non disponibilité.
        """
        start = self._now_ms()
        return self._not_available("execute_raw_sql", start)

    def bulk_update(self, **kwargs) -> Dict[str, Any]:
        """
        Met à jour en masse des enregistrements (placeholder).

        Args (via kwargs):
            table_name (str): Nom de la table.
            updates (list[dict]): Updates à appliquer.

        Returns:
            Dict[str, Any]: Placeholder.
        """
        start = self._now_ms()
        return self._not_available("bulk_update", start)

    def aggregate_data(self, **kwargs) -> Dict[str, Any]:
        """
        Réalise des agrégations groupées sur une table.

        Args (via kwargs):
            table_name (str): Table cible (obligatoire).
            group_by (list[str]): Colonnes de groupement (obligatoire).
            aggregations (dict): Spécification des agrégations (obligatoire).
            filters (Optional[dict]): Filtres simples.
            having (Optional[dict]): Conditions HAVING.

        Returns:
            Dict[str, Any]: Résultats agrégés.
        """
        start = self._now_ms()
        table_name = kwargs.get("table_name")
        group_by = kwargs.get("group_by") or []
        aggregations = kwargs.get("aggregations") or {}
        filters = kwargs.get("filters")
        having = kwargs.get("having")

        if not table_name or not group_by or not aggregations:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "table_name, group_by et aggregations sont obligatoires."),
            )

        rows = self._query_table(table_name, filters=filters, limit=5000)
        if not rows:
            return self._response(
                True,
                data=[],
                start_ms=start,
                warnings=["Aucune donnée disponible pour calculer l'agrégation."],
            )
        df = pd.DataFrame(rows)
        try:
            grouped = df.groupby(group_by)
            agg_spec = {}
            for alias, cfg in aggregations.items():
                col = cfg.get("column")
                func = cfg.get("function")
                if func == "count" and col == "*":
                    agg_spec[alias] = ("id", "count")
                else:
                    agg_spec[alias] = (col, func)
            result = grouped.agg(**agg_spec).reset_index()
            if having:
                for col, condition in having.items():
                    op = condition.get("op")
                    value = condition.get("value")
                    if op == "gt":
                        result = result[result[col] > value]
                    elif op == "ge":
                        result = result[result[col] >= value]
                    elif op == "lt":
                        result = result[result[col] < value]
                    elif op == "le":
                        result = result[result[col] <= value]
                    elif op == "eq":
                        result = result[result[col] == value]
            return self._response(True, data=result, start_ms=start)
        except Exception as exc:
            return self._response(False, data=None, start_ms=start, error=self._error("aggregation_failed", str(exc)))

    def pivot_table(self, **kwargs) -> Dict[str, Any]:
        """
        Crée un tableau croisé dynamique.

        Args (via kwargs):
            table_name (str): Table cible (obligatoire).
            rows (list[str]): Colonnes en lignes (obligatoire).
            columns (str): Colonne en colonnes (obligatoire).
            values (str): Colonne de valeur (obligatoire).
            aggfunc (str): Fonction d'agrégation (défaut "sum").

        Returns:
            Dict[str, Any]: Tableau pivoté.
        """
        start = self._now_ms()
        table_name = kwargs.get("table_name")
        rows = kwargs.get("rows")
        columns = kwargs.get("columns")
        values = kwargs.get("values")
        aggfunc = kwargs.get("aggfunc", "sum")

        if not all([table_name, rows, columns, values]):
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "table_name, rows, columns et values sont obligatoires."),
            )

        rows_data = self._query_table(table_name, limit=5000)
        if not rows_data:
            return self._response(
                True,
                data=[],
                start_ms=start,
                warnings=["Aucune donnée pour créer un pivot."],
            )
        df = pd.DataFrame(rows_data)
        try:
            pivot = pd.pivot_table(df, values=values, index=rows, columns=columns, aggfunc=aggfunc, fill_value=0)
            pivot = pivot.reset_index()
            return self._response(True, data=pivot, start_ms=start)
        except Exception as exc:
            return self._response(False, data=None, start_ms=start, error=self._error("pivot_failed", str(exc)))

    def time_series_analysis(self, **kwargs) -> Dict[str, Any]:
        """
        Analyse une série temporelle (agrégations + taux de croissance).

        Args (via kwargs):
            table_name (str): Table cible (obligatoire).
            date_column (str): Colonne date (obligatoire).
            value_column (str): Colonne de valeur numérique (obligatoire).
            interval (str): Intervalle ("month", "quarter", "year") (défaut "month").
            aggregation (str): Fonction ("sum", "avg", "median", etc.) (défaut "sum").

        Returns:
            Dict[str, Any]: Résultats temporels.
        """
        start = self._now_ms()
        table_name = kwargs.get("table_name")
        date_column = kwargs.get("date_column")
        value_column = kwargs.get("value_column")
        interval = kwargs.get("interval", "month")
        aggregation = kwargs.get("aggregation", "sum")

        if not all([table_name, date_column, value_column]):
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", "table_name, date_column et value_column sont obligatoires."),
            )

        rows = self._query_table(table_name, limit=5000)
        if not rows:
            return self._response(
                True,
                data=[],
                start_ms=start,
                warnings=["Aucune donnée temporelle disponible."],
            )
        df = pd.DataFrame(rows)
        if date_column not in df.columns or value_column not in df.columns:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_schema", "Colonnes temporelles introuvables."),
            )
        df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
        df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
        df = df.dropna(subset=[date_column, value_column])
        if df.empty:
            return self._response(True, data=[], start_ms=start, warnings=["Aucune donnée exploitable."])
        rule = {"month": "M", "quarter": "Q", "year": "A"}.get(interval.lower(), "M")
        grouped = df.set_index(date_column).resample(rule)[value_column]
        agg_map = {
            "sum": grouped.sum(),
            "avg": grouped.mean(),
            "mean": grouped.mean(),
            "median": grouped.median(),
            "max": grouped.max(),
            "min": grouped.min(),
        }
        series = agg_map.get(aggregation.lower())
        if series is None:
            return self._response(
                False,
                data=None,
                start_ms=start,
                error=self._error("invalid_parameters", f"Aggregation {aggregation} non supportée."),
            )
        result = series.reset_index().rename(columns={value_column: f"{value_column}_{aggregation.lower()}"})
        result["growth_rate"] = result[f"{value_column}_{aggregation.lower()}"].pct_change()
        return self._response(True, data=result, start_ms=start)

    # ------------------------------------------------------------------
    # Categories 3 – 15: placeholders (to be implemented)
    # ------------------------------------------------------------------

    def calculate_dcf(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("calculate_dcf", self._now_ms())

    def sensitivity_analysis(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("sensitivity_analysis", self._now_ms())

    def calculate_rendements(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("calculate_rendements", self._now_ms())

    def simulate_scenarios(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("simulate_scenarios", self._now_ms())

    def risk_assessment(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("risk_assessment", self._now_ms())

    def stress_test(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("stress_test", self._now_ms())

    def covenant_compliance(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("covenant_compliance", self._now_ms())

    def get_cash_flows(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("get_cash_flows", self._now_ms())

    def get_valorisations(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("get_valorisations", self._now_ms())

    def get_charges_exploitation(self, **kwargs) -> Dict[str, Any]:
        return self._not_available("get_charges_exploitation", self._now_ms())

    # Placeholder for remaining categories (4 → 15)
    def placeholder_tool(self, name: str) -> Dict[str, Any]:
        return self._not_available(name, self._now_ms())

    # Convenience for MCP wrappers to call synchronously
    def run_sync(self, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        method = getattr(self, method_name, None)
        if not method:
            return self._not_available(method_name, self._now_ms())
        return method(*args, **kwargs)


