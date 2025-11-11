#!/usr/bin/env python3
import asyncio
import json
import os
import logging
from pathlib import Path

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
