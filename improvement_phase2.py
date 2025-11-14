#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Improvement Phase 2 – Property & Stakeholder Insights
=====================================================

This script leverages the cleaned entity layer (produced by
`build_structured_insights.py`) to build higher-level real-estate views:

 1. Aggregates documents by property (using address/canton/commune signals).
 2. Summarises recurring tenants, landlords, organisations, and total CHF flows.
 3. Produces stakeholder-centric snapshots (top tenants/landlords by volume).
 4. Optionally upserts the results into Supabase tables:
        - property_insights
        - stakeholder_insights
    (tables must exist; SQL definition is printed on request).
 5. Always writes JSON previews locally for quick QA:
        property_insights_preview.json
        stakeholder_insights_preview.json

Usage:
    python improvement_phase2.py --upsert

Arguments:
    --dry-run           Only produce local JSON previews, no Supabase writes.
    --upsert            Upsert into Supabase (requires service role key).
    --limit N           Process only the first N documents (debugging).
    --batch-size N      Pagination size for Supabase queries (default 1000).
    --print-sql         Output CREATE TABLE statements for convenience.

Environment variables:
    SUPABASE_URL
    SUPABASE_SERVICE_KEY (service role, required for upserts)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

SUPABASE_DEFAULT_URL = "https://ugbfpxjpgtbxvcmimsap.supabase.co"
SUPABASE_DEFAULT_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVnYmZweGpwZ3RieHZjbWltc2FwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjkyMjAzOCwiZXhwIjoyMDc4NDk4MDM4fQ."
    "aTAMaBHhOqSb8mQsAOEeT7d4k21kmlLliM7moUNAkLY"
)

try:
    from supabase import Client, create_client
    from postgrest.exceptions import APIError as PostgrestAPIError
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "[ERROR] Python package 'supabase' is required. Install with 'pip install supabase'"
    ) from exc


# --------------------------------------------------------------------------- #
# Logging & helpers
# --------------------------------------------------------------------------- #

LOG_PATH = Path("improvement_phase2.log")


def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
        ],
    )


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalise_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[\r\n\t]+", " ", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(c for c in normalized if not unicodedata.combining(c))


ADDRESS_STOP_MARKERS = [
    " loyers",
    "loyers",
    "miete",
    "beilagen",
    "etat",
    "état",
    "annexes",
    "periode",
    "période",
    "detail",
    "détail",
    "objet",
    "locataire",
    "gestionnaire",
    "verwalter",
    "en faveur",
    "payable",
    "procimmo",
    "bq",
    "reference",
    "référence",
    "newsat",
    "dbs group",
    "integrated-report",
]

ADDRESS_PREFIXES = {
    "avenue",
    "av",
    "av.",
    "rue",
    "route",
    "chemin",
    "impasse",
    "allee",
    "allée",
    "boulevard",
    "bd",
    "place",
    "quai",
    "sentier",
    "passage",
    "esplanade",
    "parc",
    "cours",
    "square",
    "grand-rue",
}

ADDRESS_REGEX = re.compile(
    r"\b("
    r"avenue|av\.?|rue|route|chemin|impasse|allee|allée|boulevard|bd|place|quai|sentier|passage|esplanade|parc|cours|square"
    r")\s+[A-Za-zÀ-ÿ'’\-\s]*?\d{1,4}(?:[A-Za-z]?)(?:\s*(?:-|/|au|à)\s*\d{1,4}[A-Za-z]?)?",
    re.IGNORECASE,
)

COMMUNE_REGEX = re.compile(
    r"(?:[A-Z][a-zÀ-ÿ']{2,}(?:[-\s][A-Z][a-zÀ-ÿ']{2,})*|[A-Z]{3,})",
    re.UNICODE,
)

COMMUNE_STOPWORDS = {
    "loyers",
    "annexes",
    "miete",
    "état",
    "etat",
    "detail",
    "détail",
    "tableau",
    "resumé",
    "résumé",
    "domicim",
    "representé",
    "representé",
    "représenté",
    "représente",
    "services",
    "service",
    "immobilier",
    "immobiliers",
    "bonjour",
    "contrat",
    "investis",
    "gérance",
    "gerance",
    "otis",
    "suisse",
    "baujahr",
}

COMMUNE_NOISE_TOKENS = {
    "sa",
    "ag",
    "sas",
    "sa.",
    "ltd",
    "inc",
    "sas.",
    "la",
    "le",
    "les",
}

POSTAL_REGEX = re.compile(r"\b(\d{4})\b")


def clean_address_fragment(value: Optional[str]) -> str:
    if not value:
        return ""
    text = normalise_text(value)
    match = ADDRESS_REGEX.search(text)
    if match:
        text = match.group(0)
    lowered = text.lower()
    for marker in ADDRESS_STOP_MARKERS:
        idx = lowered.find(marker)
        if idx != -1:
            text = text[:idx]
            lowered = text.lower()
    text = re.sub(r"\b(n°|no|numero|numéro)\b.*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[,:;].*$", "", text)
    text = text.strip(" -_,")
    return text


def clean_commune_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = normalise_text(value)
    if not text:
        return None
    matches = COMMUNE_REGEX.findall(text)
    for match in reversed(matches):
        lower = match.lower()
        if lower in COMMUNE_STOPWORDS:
            continue
        if lower in ADDRESS_PREFIXES or lower in COMMUNE_NOISE_TOKENS:
            continue
        if len(lower) <= 1:
            continue
        return match
    text = re.sub(r"[0-9\-_/]", " ", text)
    tokens = [tok for tok in text.split() if tok.isalpha()]
    for tok in tokens:
        lowered = tok.lower()
        if lowered in COMMUNE_STOPWORDS or lowered in ADDRESS_PREFIXES or lowered in COMMUNE_NOISE_TOKENS:
            continue
        if len(tok) > 1:
            return tok.title()
    return None


def clean_canton_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = normalise_text(value)
    if not text:
        return None
    text = re.sub(r"(?i)\bcanton\s+de\s+", "", text)
    text = re.sub(r"[0-9]", "", text).strip(" -_,")
    if not text:
        return None
    if len(text) > 20:
        text = text[:20]
    return text.title()


def extract_postal_code(*values: Optional[Any]) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = normalise_text(str(value))
        match = POSTAL_REGEX.search(text)
        if match:
            return match.group(1)
    return None


def _slugify_parts(parts: List[Optional[str]]) -> str:
    tokens: List[str] = []
    for part in parts:
        if not part:
            continue
        normalized = strip_accents(part.lower())
        normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
        for tok in normalized.split("-"):
            if tok and (not tokens or tok != tokens[-1]):
                tokens.append(tok)
    if len(tokens) > 8:
        tokens = tokens[:8]
    return "-".join(tokens)


def normalise_address(*parts: Optional[str]) -> str:
    address_candidate: Optional[str] = None
    commune_candidate: Optional[str] = None
    canton_candidate: Optional[str] = None
    postal_candidate: Optional[str] = None
    fallback_parts: List[str] = []

    for raw in parts:
        if raw is None:
            continue
        text = normalise_text(str(raw))
        if not text:
            continue

        if not address_candidate:
            candidate = clean_address_fragment(text)
            if candidate:
                address_candidate = candidate
                postal_candidate = postal_candidate or extract_postal_code(text)
                continue

        if not commune_candidate:
            commune = clean_commune_name(text)
            if commune:
                commune_candidate = commune
                continue

        if not postal_candidate:
            postal = extract_postal_code(text)
            if postal:
                postal_candidate = postal
                continue

        if not canton_candidate:
            canton = clean_canton_name(text)
            if canton:
                canton_candidate = canton
                continue

        fallback_parts.append(text)

    slug = _slugify_parts([address_candidate, commune_candidate, postal_candidate, canton_candidate])
    if slug:
        return slug
    return _slugify_parts(fallback_parts)


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value)
    cleaned = cleaned.replace("'", "").replace(" ", "").replace("\u00a0", "")
    cleaned = cleaned.replace("CHF", "").replace("chf", "")
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


INVALID_NAME_TOKENS = {"vacant", "résilié", "resilie", "inconnu", "resilié"}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(?: 00:00:00)?$")


def is_valid_stakeholder_name(name: str) -> bool:
    if not name:
        return False
    name = normalise_text(name)
    if not name or len(name) < 2:
        return False
    lowered = name.lower()
    if lowered in INVALID_NAME_TOKENS:
        return False
    if DATE_PATTERN.fullmatch(name):
        return False
    if all(ch.isdigit() or ch in " .:/-" for ch in name):
        return False
    if len([ch for ch in name if ch.isalpha()]) < 2:
        return False
    return True


def chunked(iterable: List[Any], size: int) -> Iterable[List[Any]]:
    for idx in range(0, len(iterable), size):
        yield iterable[idx : idx + size]


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #


@dataclass
class DocumentSnapshot:
    document_id: int
    file_name: str
    document_type: Optional[str]
    canton: Optional[str]
    commune: Optional[str]
    postal_code: Optional[str]
    address: Optional[str]
    montant_total: Optional[float]
    montant_principal: Optional[float]
    tenants: Set[str] = field(default_factory=set)
    landlords: Set[str] = field(default_factory=set)
    organisations: Set[str] = field(default_factory=set)
    when: Optional[str] = None


@dataclass
class PropertyAggregate:
    property_key: str
    addresses: Set[str] = field(default_factory=set)
    cantons: Set[str] = field(default_factory=set)
    communes: Set[str] = field(default_factory=set)
    postal_codes: Set[str] = field(default_factory=set)
    document_ids: Set[int] = field(default_factory=set)
    document_types: Counter = field(default_factory=Counter)
    tenants: Counter = field(default_factory=Counter)
    landlords: Counter = field(default_factory=Counter)
    organisations: Counter = field(default_factory=Counter)
    rent_total: float = 0.0
    rent_principal: float = 0.0
    document_dates: List[str] = field(default_factory=list)

    def register_document(self, doc: DocumentSnapshot) -> None:
        self.document_ids.add(doc.document_id)
        if doc.document_type:
            self.document_types[doc.document_type] += 1
        if doc.address:
            self.addresses.add(doc.address)
        if doc.canton:
            self.cantons.add(doc.canton)
        if doc.commune:
            self.communes.add(doc.commune)
        if doc.postal_code:
            self.postal_codes.add(doc.postal_code)
        if doc.when:
            self.document_dates.append(doc.when)

        for tenant in doc.tenants:
            self.tenants[tenant] += 1
        for landlord in doc.landlords:
            self.landlords[landlord] += 1
        for org in doc.organisations:
            self.organisations[org] += 1

        if doc.montant_total:
            self.rent_total += doc.montant_total
        if doc.montant_principal:
            self.rent_principal += doc.montant_principal

    def as_record(self) -> Dict[str, Any]:
        dates_sorted = sorted(d for d in self.document_dates if d)
        last_seen = dates_sorted[-1] if dates_sorted else None
        return {
            "property_key": self.property_key,
            "addresses": sorted(self.addresses),
            "cantons": sorted(self.cantons),
            "communes": sorted(self.communes),
            "postal_codes": sorted(self.postal_codes),
            "document_ids": sorted(self.document_ids),
            "document_types": dict(self.document_types),
            "tenants": self.tenants.most_common(20),
            "landlords": self.landlords.most_common(20),
            "organisations": self.organisations.most_common(20),
            "rent_total_chf": round(self.rent_total, 2),
            "rent_principal_chf": round(self.rent_principal, 2),
            "document_count": len(self.document_ids),
            "last_document_date": last_seen,
            "updated_at": iso_now(),
        }


@dataclass
class StakeholderAggregate:
    name: str
    stakeholder_type: str
    properties: Set[str] = field(default_factory=set)
    documents: Set[int] = field(default_factory=set)
    rent_total: float = 0.0
    appearances: int = 0

    def register(self, property_key: str, document_id: int, rent: Optional[float]) -> None:
        self.properties.add(property_key)
        self.documents.add(document_id)
        if rent:
            self.rent_total += rent
        self.appearances += 1

    def as_record(self) -> Dict[str, Any]:
        return {
            "stakeholder_name": self.name,
            "stakeholder_type": self.stakeholder_type,
            "properties": sorted(self.properties),
            "document_ids": sorted(self.documents),
            "rent_total_chf": round(self.rent_total, 2),
            "appearance_count": self.appearances,
            "updated_at": iso_now(),
        }


# --------------------------------------------------------------------------- #
# Supabase fetching
# --------------------------------------------------------------------------- #


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL") or SUPABASE_DEFAULT_URL
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or SUPABASE_DEFAULT_SERVICE_KEY
    )
    if not url or not key:
        raise SystemExit(
            "[ERROR] Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables."
        )
    return create_client(url, key)


def fetch_documents(
    client: Client, limit: Optional[int], batch_size: int
) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    offset = 0
    while True:
        end = offset + batch_size - 1
        resp = (
            client.table("documents_full")
            .select("id, file_name, metadata")
            .range(offset, end)
            .execute()
        )
        batch = resp.data or []
        documents.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
        if limit is not None and len(documents) >= limit:
            documents = documents[:limit]
            break
    logging.info("Fetched %s documents", len(documents))
    return documents


def fetch_entities(client: Client) -> Dict[int, Dict[str, Any]]:
    entities: Dict[int, Dict[str, Any]] = {}
    offset = 0
    batch_size = 1000
    while True:
        resp = (
            client.table("entities")
            .select("id, entity_type, entity_value, entity_normalized")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        batch = resp.data or []
        for row in batch:
            entities[row["id"]] = row
        if len(batch) < batch_size:
            break
        offset += batch_size
    logging.info("Fetched %s entities", len(entities))
    return entities


def fetch_mentions(client: Client, batch_size: int = 2000) -> List[Dict[str, Any]]:
    mentions: List[Dict[str, Any]] = []
    offset = 0
    while True:
        resp = (
            client.table("entity_mentions")
            .select("entity_id, document_id, mention_text, created_at")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        batch = resp.data or []
        mentions.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    logging.info("Fetched %s entity mentions", len(mentions))
    return mentions


def fetch_etats_locatifs(client: Client, batch_size: int = 500) -> List[Dict[str, Any]]:
    etats: List[Dict[str, Any]] = []
    offset = 0
    while True:
        resp = (
            client.table("etats_locatifs")
            .select(
                "id, document_id, immeuble_ref, immeuble_nom, immeuble_adresse, immeuble_ville, immeuble_canton, proprietaire, unites_locatives, loyer_annuel_total"
            )
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        batch = resp.data or []
        etats.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    logging.info("Fetched %s etats locatifs", len(etats))
    return etats


# --------------------------------------------------------------------------- #
# Core aggregation
# --------------------------------------------------------------------------- #


def build_document_snapshots(
    documents: List[Dict[str, Any]],
    entity_lookup: Dict[int, Dict[str, Any]],
    mentions: List[Dict[str, Any]],
) -> Tuple[List[DocumentSnapshot], Dict[int, DocumentSnapshot]]:
    snap_map: Dict[int, DocumentSnapshot] = {}

    for doc in documents:
        doc_id = doc["id"]
        metadata = doc.get("metadata") or {}
        swiss = metadata.get("swiss_metadata") or {}

        raw_address = (
            swiss.get("adresse_principale")
            or swiss.get("adresse")
            or metadata.get("address")
            or ""
        )
        address = clean_address_fragment(raw_address)

        raw_commune = swiss.get("commune") or metadata.get("commune")
        commune = clean_commune_name(raw_commune)

        postal_code = extract_postal_code(
            swiss.get("code_postal"),
            metadata.get("postal_code"),
            raw_address,
        )

        snapshot = DocumentSnapshot(
            document_id=doc_id,
            file_name=doc.get("file_name"),
            document_type=metadata.get("document_type") or swiss.get("type_document"),
            canton=normalise_text(swiss.get("canton") or metadata.get("canton")) or None,
            commune=commune,
            postal_code=postal_code,
            address=address,
            montant_total=safe_float(swiss.get("montant_total")),
            montant_principal=safe_float(swiss.get("montant_principal")),
            when=metadata.get("generated_at") or swiss.get("date_principale"),
        )
        snap_map[doc_id] = snapshot

    for mention in mentions:
        doc_id = mention.get("document_id")
        entity_id = mention.get("entity_id")
        if doc_id is None or entity_id is None:
            continue
        snapshot = snap_map.get(doc_id)
        if not snapshot:
            continue
        entity = entity_lookup.get(entity_id)
        if not entity:
            continue
        value = entity.get("entity_value") or mention.get("mention_text")
        if not value:
            continue
        cleaned = normalise_text(value)
        if not cleaned:
            continue

        etype = entity.get("entity_type")
        if etype in {"tenant", "locataire"}:
            snapshot.tenants.add(cleaned)
        elif etype in {"landlord", "owner", "bailleur"}:
            snapshot.landlords.add(cleaned)
        else:
            snapshot.organisations.add(cleaned)

    snapshots = list(snap_map.values())
    logging.info("Built %s document snapshots", len(snapshots))
    return snapshots, snap_map


def aggregate_properties(snapshots: List[DocumentSnapshot]) -> Dict[str, PropertyAggregate]:
    properties: Dict[str, PropertyAggregate] = {}
    for snap in snapshots:
        key = normalise_address(snap.address, snap.commune, snap.canton, snap.postal_code)
        if not key:
            key = f"doc-{snap.document_id}"
        if key not in properties:
            properties[key] = PropertyAggregate(property_key=key)
        properties[key].register_document(snap)
    logging.info("Aggregated %s property profiles", len(properties))
    return properties


def aggregate_stakeholders(
    properties: Dict[str, PropertyAggregate],
    snapshot_map: Dict[int, DocumentSnapshot],
    etats_locatifs: List[Dict[str, Any]],
) -> Dict[str, StakeholderAggregate]:
    stakeholders: Dict[Tuple[str, str], StakeholderAggregate] = {}

    for prop_key, agg in properties.items():
        # Nous n'utilisons plus les organisations des documents car elles sont trop bruitées.
        for doc_id in agg.document_ids:
            snapshot = snapshot_map.get(doc_id)
            if not snapshot:
                continue
            rent = snapshot.montant_principal or snapshot.montant_total

            for tenant in snapshot.tenants:
                if not is_valid_stakeholder_name(tenant):
                    continue
                key = (tenant, "tenant")
                if key not in stakeholders:
                    stakeholders[key] = StakeholderAggregate(name=tenant, stakeholder_type="tenant")
                stakeholders[key].register(prop_key, doc_id, rent)

    # Intégrer les informations issues des états locatifs
    for etat in etats_locatifs:
        property_key = normalise_address(
            etat.get("immeuble_adresse"),
            etat.get("immeuble_ville"),
            etat.get("immeuble_canton"),
            etat.get("immeuble_ref"),
            etat.get("immeuble_nom"),
        )
        if not property_key:
            property_key = f"etat-{etat.get('id')}"

        doc_id = etat.get("document_id")
        if not doc_id:
            etat_id = etat.get("id")
            try:
                doc_id = -abs(int(etat_id))
            except (TypeError, ValueError):
                continue
        if doc_id is None:
            continue

        owner_name = normalise_text(etat.get("proprietaire"))
        if owner_name:
            if not is_valid_stakeholder_name(owner_name):
                owner_name = ""
        if owner_name:
            key = (owner_name, "landlord")
            if key not in stakeholders:
                stakeholders[key] = StakeholderAggregate(
                    name=owner_name, stakeholder_type="landlord"
                )
            stakeholders[key].register(
                property_key,
                doc_id,
                safe_float(etat.get("loyer_annuel_total")),
            )

        units = etat.get("unites_locatives") or []
        if isinstance(units, str):
            try:
                units = json.loads(units)
                if isinstance(units, str):
                    units = json.loads(units)
            except json.JSONDecodeError:
                units = []

        if not isinstance(units, list):
            continue

        for unit in units:
            if not isinstance(unit, dict):
                continue

            status = (unit.get("statut") or unit.get("status") or "").lower()
            if status in {"vacant", "vacante"}:
                continue

            locataire_entry = unit.get("locataire")
            tenant_name = None
            if isinstance(locataire_entry, dict):
                tenant_name = (
                    locataire_entry.get("nom")
                    or locataire_entry.get("entreprise")
                    or locataire_entry.get("name")
                )
            elif isinstance(locataire_entry, str):
                tenant_name = locataire_entry

            tenant_name = normalise_text(tenant_name) if tenant_name else ""
            if not is_valid_stakeholder_name(tenant_name):
                continue

            rent_info = unit.get("loyer") or {}
            unit_rent = None
            if isinstance(rent_info, dict):
                unit_rent = safe_float(
                    rent_info.get("loyer_annuel")
                    or rent_info.get("annuel")
                    or rent_info.get("loyer_net")
                    or rent_info.get("loyer_brut")
                )
                # Si c'est un loyer mensuel plausible, le convertir en annuel
                if unit_rent and unit_rent < 500:
                    unit_rent *= 12

            key = (tenant_name, "tenant")
            if key not in stakeholders:
                stakeholders[key] = StakeholderAggregate(
                    name=tenant_name, stakeholder_type="tenant"
                )
            stakeholders[key].register(property_key, doc_id, unit_rent)

    logging.info("Aggregated %s stakeholder profiles", len(stakeholders))
    return stakeholders


# --------------------------------------------------------------------------- #
# Persistence helpers
# --------------------------------------------------------------------------- #


PROPERTY_SQL = """
CREATE TABLE IF NOT EXISTS public.property_insights (
    property_key TEXT PRIMARY KEY,
    addresses JSONB,
    cantons JSONB,
    communes JSONB,
    postal_codes JSONB,
    document_ids JSONB,
    document_types JSONB,
    tenants JSONB,
    landlords JSONB,
    organisations JSONB,
    rent_total_chf NUMERIC,
    rent_principal_chf NUMERIC,
    document_count INT,
    last_document_date TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);
"""

STAKEHOLDER_SQL = """
CREATE TABLE IF NOT EXISTS public.stakeholder_insights (
    stakeholder_name TEXT,
    stakeholder_type TEXT,
    properties JSONB,
    document_ids JSONB,
    rent_total_chf NUMERIC,
    appearance_count INT,
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (stakeholder_name, stakeholder_type)
);
"""


def upsert_records(
    client: Client, table: str, records: List[Dict[str, Any]], batch_size: int = 500
) -> None:
    for batch in chunked(records, batch_size):
        client.table(table).upsert(batch).execute()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Improvement phase 2 insights builder.")
    parser.add_argument("--dry-run", action="store_true", help="Produce JSON only.")
    parser.add_argument("--upsert", action="store_true", help="Upsert results into Supabase.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of documents.")
    parser.add_argument("--batch-size", type=int, default=1000, help="Pagination size.")
    parser.add_argument("--print-sql", action="store_true", help="Print helper SQL statements.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging()

    if args.print_sql:
        print(PROPERTY_SQL.strip())
        print()
        print(STAKEHOLDER_SQL.strip())
        if not args.upsert and not args.dry_run:
            return

    client = get_supabase_client()

    try:
        documents = fetch_documents(client, args.limit, args.batch_size)
        entities = fetch_entities(client)
        mentions = fetch_mentions(client)
        etats_locatifs = fetch_etats_locatifs(client)

        snapshots, snapshot_map = build_document_snapshots(documents, entities, mentions)
        properties = aggregate_properties(snapshots)
        stakeholders = aggregate_stakeholders(properties, snapshot_map, etats_locatifs)

        property_records = [prop.as_record() for prop in properties.values()]
        stakeholder_records = [st.as_record() for st in stakeholders.values()]

        Path("property_insights_preview.json").write_text(
            json.dumps(property_records[:200], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        Path("stakeholder_insights_preview.json").write_text(
            json.dumps(stakeholder_records[:200], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logging.info("Wrote JSON previews (first 200 records).")

        if not args.dry_run and args.upsert:
            logging.info("Upserting %s property records …", len(property_records))
            upsert_records(client, "property_insights", property_records)
            logging.info("Upserting %s stakeholder records …", len(stakeholder_records))
            upsert_records(client, "stakeholder_insights", stakeholder_records)

        summary = {
            "timestamp": iso_now(),
            "total_documents": len(documents),
            "property_records": len(property_records),
            "stakeholder_records": len(stakeholder_records),
            "dry_run": args.dry_run,
            "upserted": args.upsert and not args.dry_run,
        }
        Path("improvement_phase2_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logging.info("Summary written to improvement_phase2_summary.json")

    except PostgrestAPIError as exc:
        logging.error("Supabase error: %s", exc)
        raise


if __name__ == "__main__":
    main()

