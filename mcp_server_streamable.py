#!/usr/bin/env python3
import asyncio
import json
import os
import logging
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
load_dotenv()

# SDK MCP (transport HTTP "streamable" recommandé)
from mcp.server.fastmcp import FastMCP

# Tes modules
from src.semantic_search import SemanticSearchEngine
from src.supabase_client import SupabaseUploader
from src.embeddings import EmbeddingGenerator
from src.supabase_client_v2 import SupabaseUploaderV2
from src.azure_ocr import AzureOCRProcessor
from src.ultimate_tools import UltimateTools
from mcp_real_estate import (
    AgenticRAGRouter,
    ValidationChain,
    CorrectiveRAG,
    SelfReflectiveAgent,
    QueryPlanner,
    ConfidenceScorer,
)

# ASGI / HTTP
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("mcp_streamable")

# -----------------------------------------------------------------------------
# Initialisations applicatives
# -----------------------------------------------------------------------------
log.info("✅ Moteur de recherche sémantique initialisé")
try:
    search = SemanticSearchEngine()
except Exception as e:
    # OpenAI key or Supabase config may be missing; keep server alive
    log.warning(f"⚠️ Search engine disabled: {e}")
    search = None
supabase = SupabaseUploader()

try:
    embedder = EmbeddingGenerator()
    uploader_v2 = SupabaseUploaderV2()
    log.info("✅ Embeddings + Uploader V2 prêts")
except Exception as e:
    log.warning(f"⚠️ Uploader V2 indisponible: {e}")
    embedder = None
    uploader_v2 = None

try:
    ocr = AzureOCRProcessor()
    log.info("✅ Azure OCR prêt")
except Exception as e:
    log.warning(f"⚠️ Azure OCR indisponible: {e}")
    ocr = None

try:
    ultimate_tools = UltimateTools()
    log.info("✅ Ultimate tools initialisés")
except Exception as e:
    log.warning(f"⚠️ Ultimate tools indisponibles: {e}")
    ultimate_tools = None

# -----------------------------------------------------------------------------
# MCP Server (FastMCP)
# -----------------------------------------------------------------------------
mcp = FastMCP("documents-search-server", stateless_http=True)  # simple pour ChatGPT Dev Mode

# ---- TOOLS -------------------------------------------------------------------
@mcp.tool()
def search_documents(query: str, limit: int = 5, threshold: float = 0.3) -> str:
    """Recherche sémantique dans la base de documents (embeddings)."""
    if not search:
        return "❌ Recherche indisponible: configurez OPENAI_API_KEY et SUPABASE_URL/SUPABASE_KEY."
    results = search.search(query=query, limit=limit, threshold=threshold)
    if not results:
        return "Aucun résultat."
    lines = [f"🔍 Requête: {query}", f"📊 {len(results)} résultats", "=" * 60]
    for r in results:
        content = r["content"]
        if len(content) > 800:
            content = content[:800] + "..."
        lines += [
            f"\n#{r['rank']} - {r['file_name']}",
            f"   Similarité: {r['similarity']:.2%}",
            f"   Chunk: {r['chunk_index']}",
            "   Contenu:",
            *[f"   {ln}" for ln in content.splitlines() if ln.strip()],
        ]
    return "\n".join(lines)

@mcp.tool()
def get_context_for_rag(query: str, limit: int = 5, threshold: float = 0.3) -> str:
    """Retourne un contexte formaté pour RAG."""
    if not search:
        return "❌ RAG indisponible: configurez OPENAI_API_KEY et SUPABASE_URL/SUPABASE_KEY."
    return search.get_context_for_rag(query=query, limit=limit, threshold=threshold)

@mcp.tool()
def get_database_stats() -> str:
    """Statistiques de la base Supabase."""
    if not uploader_v2:
        return "❌ Uploader V2 non initialisé."
    stats = uploader_v2.get_database_stats()
    out = [
        "📊 STATISTIQUES", "=" * 60,
        f"📁 Total documents : {stats.get('total_documents', 0)}",
        f"📦 Total chunks    : {stats.get('total_chunks', 0)}",
        f"📊 Moy. chunks/doc : {stats.get('avg_chunks_per_document', 0):.1f}",
        f"📏 Taille moyenne  : {stats.get('avg_chunk_size', 0):.0f} caractères",
        f"🕐 Date            : {stats.get('timestamp', 'N/A')}",
    ]
    return "\n".join(out)

@mcp.tool()
def upload_document(file_path: str) -> str:
    """Upload un document (PDF/TXT/MD/CSV) avec extraction/embeddings."""
    if not file_path:
        return "❌ file_path requis"
    if embedder is None or uploader_v2 is None:
        return "❌ Composants d'upload non initialisés"
    try:
        from process_v2 import process_single_file
        result = process_single_file(
            file_path=file_path,
            embedding_gen=embedder,
            uploader=uploader_v2,
            ocr_processor=ocr,
            upload=True,
        )
        if result["status"] == "success":
            out = [
                "✅ UPLOAD RÉUSSI", "=" * 60,
                f"📄 Fichier            : {result['file_name']}",
                f"📝 Texte extrait      : {result['full_text_length']} caractères",
                f"🔢 Chunks créés       : {result['chunks_count']}",
                f"🧠 Embeddings générés : {result['embeddings_count']}",
                f"⚙️ Méthode            : {result['method']}",
            ]
            if result.get("page_count"):
                out.append(f"📄 Pages              : {result['page_count']}")
            return "\n".join(out)
        return f"❌ Erreur upload:\n{result.get('error','Inconnue')}"
    except Exception as e:
        return f"❌ Exception upload:\n{e}"

@mcp.tool()
def read_file(file_path: str, max_chars: int = 10000) -> str:
    """Lecture (aperçu) d'un fichier texte."""
    if not file_path:
        return "❌ file_path requis"
    if not os.path.exists(file_path):
        return f"❌ Fichier introuvable: {file_path}"
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    truncated = ""
    if len(content) > max_chars:
        content = content[:max_chars]
        truncated = f"\n⚠️ Contenu tronqué à {max_chars} caractères"
    size_kb = os.path.getsize(file_path) / 1024
    return f"📖 {Path(file_path).name} ({size_kb:.2f} KB){truncated}\n\n{content}"

@mcp.tool()
def write_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """Écrit/écrase un fichier texte."""
    if not file_path:
        return "❌ file_path requis"
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding=encoding) as f:
        f.write(content)
    size_kb = os.path.getsize(file_path) / 1024
    return (
        "✅ FICHIER ÉCRIT\n" + "=" * 60
        + f"\n📄 {Path(file_path).name}\n📍 {file_path}\n📊 {size_kb:.2f} KB\n📝 {len(content)} caractères\n🔤 {encoding}"
    )

@mcp.tool()
def list_files(directory: str, pattern: str = "*", recursive: bool = False) -> str:
    """Liste les fichiers d'un dossier (pattern + récursif)."""
    if not directory:
        return "❌ directory requis"
    import fnmatch
    if not os.path.exists(directory):
        return f"❌ Dossier introuvable: {directory}"
    if not os.path.isdir(directory):
        return f"❌ Chemin non dossier: {directory}"
    files = []
    base = Path(directory)
    if recursive:
        for root, _dirs, names in os.walk(directory):
            for name in names:
                if fnmatch.fnmatch(name, pattern):
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, directory)
                    files.append((rel, full))
    else:
        for item in base.iterdir():
            if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                files.append((item.name, str(item)))
    files.sort()
    out = [f"📂 {directory} | {len(files)} fichier(s)\n"]
    for rel, full in files:
        try:
            size_kb = os.path.getsize(full) / 1024
            out.append(f"📄 {rel} ({size_kb:.2f} KB)")
        except Exception:
            out.append(f"📄 {rel}")
    return "\n".join(out)

# -----------------------------------------------------------------------------
# Ultimate due diligence tools (dynamic registration)
# -----------------------------------------------------------------------------

def format_result(result: Dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def _merge_params(payload: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if isinstance(kwargs, dict):
        params.update(kwargs)
    if isinstance(payload, str) and payload.strip():
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                params.update(parsed)
        except Exception as exc:  # noqa: BLE001
            params.setdefault("__parse_error__", str(exc))
    elif isinstance(payload, dict):
        params.update(payload)
    return params


async def call_ultimate(method_name: str, payload: Any = None, **kwargs) -> str:
    if not ultimate_tools:
        return format_result(
            {
                "success": False,
                "data": None,
                "metadata": {
                    "execution_time_ms": 0,
                    "cached": False,
                    "data_sources": [],
                    "count": 0,
                    "query_cost": 0,
                    "warnings": ["Ultimate tools non initialisés sur le serveur."],
                },
                "error": {"code": "not_initialized", "message": "Ultimate tools indisponibles.", "details": {}},
            }
        )
    params = _merge_params(payload, kwargs)
    parse_warning = params.pop("__parse_error__", None)
    result = await asyncio.to_thread(ultimate_tools.run_sync, method_name, **params)
    if parse_warning and isinstance(result, dict):
        meta = result.setdefault("metadata", {})
        warnings = meta.setdefault("warnings", [])
        warnings.append(f"Payload JSON non parsé: {parse_warning}")

    return format_result(result)


def register_tool(method_name: str, description: str):
    async def tool_wrapper(payload: str = "{}", **kwargs):
        return await call_ultimate(method_name, payload, **kwargs)

    tool_wrapper.__name__ = method_name
    tool_wrapper.__doc__ = description
    mcp.tool()(tool_wrapper)


# Category 1 – registres fonciers & états locatifs
register_tool(
    "get_registre_foncier",
    "Récupère les informations de registre foncier (parcelle, commune, adresse).",
)
register_tool(
    "search_servitudes",
    "Recherche des servitudes par type, commune et impact sur la valeur.",
)
register_tool(
    "analyze_charges_foncieres",
    "Analyse les charges foncières pour une parcelle (gages, servitudes).",
)
register_tool(
    "get_etat_locatif_complet",
    "Retourne l'état locatif complet avec KPI et ratios calculés.",
)
register_tool(
    "analyze_loyers_marche",
    "Compare les loyers à la moyenne de marché dans le voisinage.",
)
register_tool(
    "detect_anomalies_locatives",
    "Détecte les anomalies locatives (loyers sous marché, vacance élevée).",
)
register_tool(
    "get_echeancier_baux",
    "Échéancier des fins de bail pour un immeuble (si disponible).",
)

# Property & stakeholder insights
register_tool(
    "get_property_insight",
    "Fiche complète d'un immeuble (insights agrégés, documents liés, état locatif).",
)
register_tool(
    "get_stakeholder_profile",
    "Profil d'un acteur (locataire/bailleur) avec ses propriétés et volumes.",
)
register_tool(
    "find_vacancy_alerts",
    "Détecte les immeubles avec vacance ou risques élevés selon les seuils définis.",
)

# Agentic orchestrator -------------------------------------------------------


async def _tool_runner(method_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not ultimate_tools:
        raise RuntimeError("Ultimate tools non initialisés.")
    return await asyncio.to_thread(ultimate_tools.run_sync, method_name, **params)


def _serialize_validation(validation) -> Dict[str, Any]:
    return {
        "passed": validation.passed,
        "confidence": validation.confidence,
        "checks": [
            {
                "name": check.name,
                "passed": check.passed,
                "details": check.details,
                "severity": check.severity,
                "requires_requery": check.requires_requery,
                "score": check.score,
            }
            for check in validation.checks
        ],
        "contradictions": validation.contradictions,
        "requires_requery": validation.requires_requery,
        "suggested_corrections": validation.suggested_corrections,
        "db_doc_alignment_score": validation.db_doc_alignment_score,
        "numerical_coherence_score": validation.numerical_coherence_score,
    }


@register_tool(
    "agentic_query",
    "Agentic RAG avec validation, correction et boucle réflexive.",
)
async def agentic_query(payload: str = "{}", **kwargs) -> str:
    params = _merge_params(payload, kwargs)
    query = params.get("query")
    if not query:
        return format_result(
            {
                "success": False,
                "data": None,
                "metadata": {"warnings": ["Paramètre 'query' obligatoire."]},
                "error": {"code": "invalid_parameters", "message": "query manquant."},
            }
        )

    confidence_threshold = float(params.get("confidence_threshold", 0.75))
    max_iterations = int(params.get("max_iterations", 3))
    enable_reflection = bool(params.get("enable_reflection", True))

    try:
        router = AgenticRAGRouter()
        planner = QueryPlanner()
        plan = await router.route_query(query, {"intent": params.get("intent")})

        crag = CorrectiveRAG(
            tool_runner=_tool_runner,
            validator=ValidationChain(),
            scorer=ConfidenceScorer(),
            planner=planner,
        )

        result = await crag.execute_with_correction(plan, max_iterations=max_iterations)

        if enable_reflection and result.confidence < confidence_threshold:
            reflector = SelfReflectiveAgent()
            reflection = reflector.reflect_on_answer(query, result.data, result.sources)
            if reflection.should_continue:
                new_plan = await router.replan_from_reflection(plan, reflection)
                result = await crag.execute_with_correction(new_plan, max_iterations=1)

        validation_payload = _serialize_validation(result.validation)

        return format_result(
            {
                "success": result.validation.passed,
                "data": {
                    "answer": result.data,
                    "confidence": result.confidence,
                    "sources": result.sources,
                    "iterations": result.iterations,
                    "warnings": result.warnings,
                    "corrections_applied": result.corrections_applied,
                    "confidence_breakdown": result.confidence_score.factors,
                    "confidence_flags": result.confidence_score.flags,
                    "validation": validation_payload,
                },
                "metadata": {
                    "query": query,
                    "plan_metadata": plan.metadata,
                },
                "error": None
                if result.validation.passed
                else {
                    "code": "validation_failed",
                    "message": "Certaines vérifications n'ont pas été validées.",
                    "details": validation_payload,
                },
            }
        )
    except Exception as exc:
        return format_result(
            {
                "success": False,
                "data": None,
                "metadata": {"warnings": ["Exception pendant l'agentic query."]},
                "error": {"code": "agentic_error", "message": str(exc)},
            }
        )

# Category 1.3 & 2
register_tool("get_cash_flows", "Récupère ou projette les flux de trésorerie d'un immeuble.")
register_tool("get_valorisations", "Valorisations (DCF, capitalisation, comparables) pour un immeuble.")
register_tool("get_charges_exploitation", "Analyse détaillée des charges d'exploitation d'un immeuble.")

register_tool("query_table", "Requête flexible sur une table Supabase avec filtres et tri.")
register_tool("execute_raw_sql", "Exécute une requête SQL brute (lecture seule par défaut).")
register_tool("bulk_update", "Met à jour en masse des enregistrements dans une table.")
register_tool("aggregate_data", "Agrégations complexes avec group by / having.")
register_tool("pivot_table", "Génère un tableau croisé dynamique à partir d'une table.")
register_tool("time_series_analysis", "Analyse temporelle avec agrégations et taux de croissance.")

# Category 3 – Analyses financières
register_tool("calculate_dcf", "Calcul de DCF complet avec scénarios et sensibilité.")
register_tool("sensitivity_analysis", "Analyse de sensibilité multi-variables.")
register_tool("calculate_rendements", "Calcule les rendements (brut, net, TRI, multiple).")
register_tool("simulate_scenarios", "Simulations de scénarios financiers (Monte Carlo).")

# Category 3.2 – Risques
register_tool("risk_assessment", "Évaluation des risques pour un immeuble (locataires, technique, marché).")
register_tool("stress_test", "Stress tests financiers sur différents chocs.")
register_tool("covenant_compliance", "Vérifie la conformité aux covenants bancaires.")

# Remaining categories – placeholders via placeholder_tool
PLACEHOLDER_METHODS = [
    "analyze_charges_foncieres",
    "get_cash_flows",
    "get_valorisations",
    "get_charges_exploitation",
    "calculate_dcf",
    "sensitivity_analysis",
    "calculate_rendements",
    "simulate_scenarios",
    "risk_assessment",
    "stress_test",
    "covenant_compliance",
    "find_comparables",
    "benchmark_market",
    "market_trends",
    "zone_analysis",
    "score_immeuble",
    "classify_assets",
    "geospatial_query",
    "proximity_analysis",
    "heatmap_data",
    "extract_document_data",
    "document_similarity",
    "batch_document_analysis",
    "document_qa",
    "cross_document_validation",
    "predict_loyer_marche",
    "predict_valorisation",
    "predict_vacance_risk",
    "detect_opportunities",
    "churn_analysis",
    "generate_due_diligence_report",
    "generate_investment_memo",
    "export_to_excel",
    "generate_presentation",
    "create_dashboard_data",
    "create_alert",
    "schedule_analysis",
    "bulk_valuation_update",
    "data_pipeline",
    "fetch_cadastre_data",
    "fetch_market_data",
    "geocode_address",
    "fetch_climate_risk",
    "fetch_transport_score",
    "validate_data_quality",
    "detect_duplicates",
    "audit_trail",
    "data_lineage",
    "find_related_entities",
    "ownership_structure",
    "tenant_network",
    "cache_query_result",
    "invalidate_cache",
    "get_query_performance",
    "get_database_schema",
    "get_table_metadata",
    "get_column_statistics",
    "suggest_indexes",
    "convert_units",
    "calculate_distance",
    "format_address",
    "parse_swiss_date",
    "generate_uuid",
]

def register_placeholder(name: str):
    async def placeholder(payload: str = "{}", **kwargs):
        params = _merge_params(payload, kwargs)
        if not ultimate_tools:
            return await call_ultimate("placeholder_tool", payload=params, name=name)
        result = ultimate_tools.placeholder_tool(name)
        return format_result(result)

    placeholder.__name__ = name
    placeholder.__doc__ = f"Fonctionnalité « {name} » (en cours d'implémentation)."
    mcp.tool()(placeholder)


for placeholder_name in PLACEHOLDER_METHODS:
    if placeholder_name in {
        "analyze_charges_foncieres",
        "get_cash_flows",
        "get_valorisations",
        "get_charges_exploitation",
        "calculate_dcf",
        "sensitivity_analysis",
        "calculate_rendements",
        "simulate_scenarios",
        "risk_assessment",
        "stress_test",
        "covenant_compliance",
    }:
        continue
    register_placeholder(placeholder_name)

# -----------------------------------------------------------------------------
# ASGI App (FastMCP streamable HTTP → expose /mcp)
# -----------------------------------------------------------------------------
app = mcp.streamable_http_app()

# Ajouter /health et / directement sur l'app MCP (sans sous-app/mount -> garde lifespan)
try:
    @app.route("/health")
    async def health(_: Request):
        return JSONResponse({"ok": True})

    @app.route("/", methods=["GET", "HEAD"])
    async def root_ok(_: Request):
        return JSONResponse({"ok": True, "endpoint": "/mcp"})
except Exception:
    # Si l'objet retourné ne supporte pas .route, on ignore (le /mcp reste fonctionnel)
    pass

# CORS large pour clients MCP (ChatGPT/Claude)
app = CORSMiddleware(
    app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
async def main():
    port = int(os.getenv("PORT", "3000"))
    log.info(f"🚀 MCP (Streamable HTTP) sur /mcp - Port {port}")
    config = uvicorn.Config(app=app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("🛑 Arrêt du serveur")
