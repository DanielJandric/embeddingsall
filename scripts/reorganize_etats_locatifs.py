#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reorganise the `etats_locatifs` table into a normalised structure.

This script parses the JSON payload stored in `unites_locatives`, creates
canonical unit-level records, recomputes KPI totals, and enriches the parent
table with standardised metadata (slug, property name, commune, etc.).

Usage:
    python scripts/reorganize_etats_locatifs.py --preview
    python scripts/reorganize_etats_locatifs.py --upsert

Environment variables:
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from supabase import Client, create_client
    from postgrest.exceptions import APIError as PostgrestAPIError
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "[ERROR] Python package 'supabase' is required. Install with 'pip install supabase'"
    ) from exc


DEFAULT_SUPABASE_URL = "https://ugbfpxjpgtbxvcmimsap.supabase.co"
DEFAULT_SUPABASE_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVnYmZweGpwZ3RieHZjbWltc2FwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjkyMjAzOCwiZXhwIjoyMDc4NDk4MDM4fQ."
    "aTAMaBHhOqSb8mQsAOEeT7d4k21kmlLliM7moUNAkLY"
)


# --------------------------------------------------------------------------- #
# Text normalisation helpers (adapted from improvement_phase2.py)
# --------------------------------------------------------------------------- #


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


def normalise_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[\r\n\t]+", " ", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(c for c in normalized if not unicodedata.combining(c))


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
        if lower in COMMUNE_NOISE_TOKENS:
            continue
        if len(lower) <= 1:
            continue
        return match
    text = re.sub(r"[0-9\-_/]", " ", text)
    tokens = [tok for tok in text.split() if tok.isalpha()]
    for tok in tokens:
        lowered = tok.lower()
        if lowered in COMMUNE_STOPWORDS or lowered in COMMUNE_NOISE_TOKENS:
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


def _slugify_parts(parts: Sequence[Optional[str]]) -> str:
    tokens: List[str] = []
    for part in parts:
        if not part:
            continue
        normalized = strip_accents(str(part).lower())
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


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #


TENANT_COMPANY_HINTS = {
    "sa",
    "ag",
    "sas",
    "sarl",
    "sàrl",
    "gmbh",
    "sa.",
    "holding",
    "group",
    "suisse",
    "company",
    "ltd",
    "inc",
    "llc",
    "succursale",
    "assurance",
    "centre",
    "société",
}


def coerce_units(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [unit for unit in raw if isinstance(unit, dict)]
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return []
        if isinstance(data, list):
            return [unit for unit in data if isinstance(unit, dict)]
        if isinstance(data, dict):
            return [data]
    return []


def parse_date(value: Optional[Any]) -> Optional[str]:
    if not value:
        return None
    text = normalise_text(str(value))
    if not text:
        return None
    text = text.replace(" 00:00:00", "")
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    # detect ISO prefix
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    return None


def standardise_floor(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = normalise_text(str(value)).lower()
    if not text:
        return None
    replacements = {
        "rez-de-ch": "RDC",
        "rez": "RDC",
        "rdc": "RDC",
        "sous-sol": "SS",
        "1er": "1",
        "2ème": "2",
        "3ème": "3",
        "4ème": "4",
        "5ème": "5",
        "6ème": "6",
        "7ème": "7",
        "8ème": "8",
        "9ème": "9",
        "10ème": "10",
    }
    for needle, replacement in replacements.items():
        if needle in text:
            return replacement
    match = re.search(r"(-?\d+)", text)
    if match:
        return match.group(1)
    return text.upper()


def clean_usage(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = normalise_text(str(value))
    if not text:
        return None
    return text.title()


def clean_status(unit: Dict[str, Any]) -> Optional[str]:
    status = unit.get("statut") or unit.get("status")
    if status:
        text = normalise_text(str(status))
        if text:
            return text.lower()
    return None


def is_vacant(unit: Dict[str, Any], tenant_name: str, status: Optional[str]) -> bool:
    if not tenant_name:
        return True
    lowered = tenant_name.lower()
    if "vacant" in lowered or "frei" in lowered or "leer" in lowered:
        return True
    if status and "vacant" in status:
        return True
    return False


def split_tenant_name(name: str) -> Tuple[Optional[str], Optional[str], bool]:
    if not name:
        return (None, None, False)
    lowered = name.lower()
    for hint in TENANT_COMPANY_HINTS:
        if hint in lowered:
            return (None, None, True)
    parts = name.split()
    if len(parts) == 1:
        return (parts[0].title(), None, False)
    first = " ".join(parts[:-1]).title()
    last = parts[-1].title()
    return (first, last, False)


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


def flatten_units(record: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    units = []
    raw_units = coerce_units(record.get("unites_locatives"))
    file_name = record.get("file_name") or record.get("file_path")
    file_slug = Path(str(file_name)).name if file_name else None
    property_slug = normalise_address(
        record.get("immeuble_adresse"),
        record.get("file_name"),
        record.get("immeuble_nom"),
        record.get("immeuble_ville"),
    )
    property_name = normalise_text(record.get("immeuble_nom") or record.get("property_name") or "")
    property_commune = clean_commune_name(record.get("immeuble_ville") or record.get("property_commune"))
    property_canton = clean_canton_name(record.get("immeuble_canton"))
    property_postal = extract_postal_code(record.get("immeuble_adresse"), record.get("file_name"))

    total_loyer_net = 0.0
    total_loyer_brut = 0.0
    total_surface = 0.0
    tenant_names: List[str] = []

    for index, unit in enumerate(raw_units):
        locataire = unit.get("locataire") or {}
        if isinstance(locataire, str):
            locataire = {"nom": locataire}
        tenant_name_raw = locataire.get("nom")
        if isinstance(tenant_name_raw, dict):
            tenant_name_raw = tenant_name_raw.get("principal") or tenant_name_raw.get("value")
        if not isinstance(tenant_name_raw, str):
            tenant_name_raw = unit.get("locataire")
        if isinstance(tenant_name_raw, dict):
            tenant_name_raw = tenant_name_raw.get("nom") or tenant_name_raw.get("principal")
        tenant_name = normalise_text(str(tenant_name_raw or ""))
        tenant_company_raw = locataire.get("entreprise")
        if isinstance(tenant_company_raw, dict):
            tenant_company_raw = tenant_company_raw.get("nom") or tenant_company_raw.get("principal")
        tenant_company = normalise_text(str(tenant_company_raw or ""))
        first_name, last_name, is_company = split_tenant_name(tenant_name)
        surface = safe_float(unit.get("surface_m2"))
        loyer_net = safe_float(unit.get("loyer", {}).get("loyer_net") if isinstance(unit.get("loyer"), dict) else unit.get("loyer_net"))
        charges = safe_float(unit.get("loyer", {}).get("charges") if isinstance(unit.get("loyer"), dict) else unit.get("charges"))
        loyer_brut = safe_float(unit.get("loyer", {}).get("loyer_brut") if isinstance(unit.get("loyer"), dict) else unit.get("loyer_brut"))
        loyer_m2 = safe_float(unit.get("loyer", {}).get("loyer_m2_an") if isinstance(unit.get("loyer"), dict) else unit.get("loyer_m2_an"))
        if loyer_m2 is None and loyer_brut and surface:
            loyer_m2 = (loyer_brut * 12) / surface if loyer_brut < 1000 else loyer_brut / surface

        status = clean_status(unit)
        vacant = is_vacant(unit, tenant_name, status)
        if tenant_name and not vacant:
            tenant_names.append(tenant_name)

        total_loyer_net += loyer_net or 0.0
        total_loyer_brut += loyer_brut or 0.0
        total_surface += surface or 0.0

        units.append(
            {
                "unit_id": f"{record.get('id')}-{index}",
                "etat_id": record.get("id"),
                "unit_index": index,
                "reference": normalise_text(unit.get("reference")),
                "floor_label": standardise_floor(unit.get("etage")),
                "usage_type": clean_usage(unit.get("type")),
                "rooms": safe_float(unit.get("pieces")),
                "surface_m2": surface,
                "tenant_name": tenant_name if not vacant else None,
                "tenant_first_name": None if is_company else first_name,
                "tenant_last_name": None if is_company else last_name,
                "tenant_company": tenant_company if tenant_company else (tenant_name if is_company else None),
                "tenant_is_company": is_company or bool(tenant_company),
                "vacant": vacant,
                "status": status,
                "lease_start": parse_date(locataire.get("debut_bail")),
                "lease_end": parse_date(locataire.get("fin_bail")),
                "loyer_net_chf": loyer_net,
                "charges_chf": charges,
                "loyer_brut_chf": loyer_brut,
                "loyer_m2_chf": loyer_m2,
                "source_file": file_slug,
                "property_slug": property_slug,
                "raw_payload": unit,
            }
        )

    metadata = {
        "property_slug": property_slug,
        "property_name": property_name or None,
        "property_commune": property_commune,
        "property_canton": property_canton,
        "property_postal_code": property_postal,
        "source_file": file_slug,
        "parsed_unit_count": len(units),
        "parsed_surface_m2": total_surface or None,
        "parsed_loyer_net_chf": total_loyer_net or None,
        "parsed_loyer_brut_chf": total_loyer_brut or None,
        "tenants_sample": tenant_names[:10] or None,
    }

    return units, metadata


# --------------------------------------------------------------------------- #
# Supabase helpers
# --------------------------------------------------------------------------- #


def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL", DEFAULT_SUPABASE_URL)
    key = os.environ.get("SUPABASE_SERVICE_KEY", DEFAULT_SUPABASE_SERVICE_KEY)
    return create_client(url, key)


def fetch_etats(client: Client, offset: int, limit: int) -> List[Dict[str, Any]]:
    response = (
        client.table("etats_locatifs")
        .select("*")
        .order("id", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data or []


def upsert_units(client: Client, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    client.table("etats_locatifs_units").upsert(rows, on_conflict="unit_id").execute()


def update_parent(client: Client, etat_id: int, payload: Dict[str, Any]) -> None:
    payload = {k: v for k, v in payload.items() if v is not None}
    if not payload:
        return
    payload["normalized_at"] = datetime.utcnow().isoformat()
    client.table("etats_locatifs").update(payload).eq("id", etat_id).execute()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def iter_batches(client: Client, batch_size: int) -> Iterable[List[Dict[str, Any]]]:
    offset = 0
    while True:
        batch = fetch_etats(client, offset, batch_size)
        if not batch:
            break
        yield batch
        if len(batch) < batch_size:
            break
        offset += batch_size


def run(args: argparse.Namespace) -> None:
    client = get_supabase_client()
    all_units: List[Dict[str, Any]] = []
    parent_updates: List[Tuple[int, Dict[str, Any]]] = []

    try:
        for batch in iter_batches(client, args.batch_size):
            for record in batch:
                units, metadata = flatten_units(record)
                if args.preview:
                    all_units.extend(units)
                    parent_updates.append((record["id"], metadata))
                if args.upsert:
                    if units:
                        upsert_units(client, units)
                    update_parent(client, record["id"], metadata)

    except PostgrestAPIError as exc:
        raise SystemExit(f"[Supabase] {exc}") from exc

    if args.preview:
        preview_dir = Path("previews")
        preview_dir.mkdir(parents=True, exist_ok=True)
        Path(preview_dir / "etats_locatifs_units_preview.json").write_text(
            json.dumps(all_units[:500], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        Path(preview_dir / "etats_locatifs_parent_preview.json").write_text(
            json.dumps(
                [
                    {"etat_id": etat_id, **meta}
                    for etat_id, meta in parent_updates[:500]
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[preview] wrote {len(all_units[:500])} unit rows and {len(parent_updates[:500])} parent rows to previews/")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalise etats_locatifs data.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Supabase pagination size (default: 200)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Only generate local JSON previews, do not upsert.",
    )
    parser.add_argument(
        "--upsert",
        action="store_true",
        help="Apply changes to Supabase (requires service role key).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.preview and not args.upsert:
        parser.error("choose --preview or --upsert (or both)")
    run(args)


if __name__ == "__main__":
    main(sys.argv[1:])


