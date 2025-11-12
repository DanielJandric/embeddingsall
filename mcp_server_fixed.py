#!/usr/bin/env python3
"""
MCP Server corrigé pour Claude - accepte les requêtes POST sur /
"""
import asyncio
import json
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# SDK MCP
from mcp.server.fastmcp import FastMCP

# Modules locaux
from src.semantic_search import SemanticSearchEngine
from src.supabase_client import SupabaseUploader
from src.embeddings import EmbeddingGenerator
from src.supabase_client_v2 import SupabaseUploaderV2
from src.azure_ocr import AzureOCRProcessor

# ASGI / HTTP
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from starlette.requests import Request
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("mcp_fixed")

# -----------------------------------------------------------------------------
# Initialisations
# -----------------------------------------------------------------------------
log.info("✅ Initialisation du moteur de recherche...")
try:
    search = SemanticSearchEngine()
    log.info("✅ Moteur de recherche prêt")
except Exception as e:
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
# MCP Server
# -----------------------------------------------------------------------------
mcp = FastMCP("documents-search-server")

# ---- TOOLS -------------------------------------------------------------------
@mcp.tool()
def search_documents(query: str, limit: int = 5, threshold: float = 0.3) -> str:
    """Recherche sémantique dans la base de documents."""
    if not search:
        return "❌ Recherche indisponible: configurez OPENAI_API_KEY et SUPABASE_URL/SUPABASE_KEY."
    
    try:
        results = search.search(query=query, limit=limit, threshold=threshold)
        if not results:
            return f"Aucun résultat pour: {query}"
        
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
    except Exception as e:
        log.error(f"Erreur recherche: {e}")
        return f"❌ Erreur lors de la recherche: {str(e)}"

@mcp.tool()
def get_context_for_rag(query: str, limit: int = 5, threshold: float = 0.3) -> str:
    """Retourne un contexte formaté pour RAG."""
    if not search:
        return "❌ RAG indisponible."
    
    try:
        return search.get_context_for_rag(query=query, limit=limit, threshold=threshold)
    except Exception as e:
        return f"❌ Erreur RAG: {str(e)}"

@mcp.tool()
def get_database_stats() -> str:
    """Statistiques de la base Supabase."""
    if not uploader_v2:
        return "❌ Stats indisponibles."
    
    try:
        stats = uploader_v2.get_database_stats()
        return f"""📊 STATISTIQUES
{'='*60}
📁 Total documents : {stats.get('total_documents', 0)}
📦 Total chunks    : {stats.get('total_chunks', 0)}
📊 Moy. chunks/doc : {stats.get('avg_chunks_per_document', 0):.1f}
📏 Taille moyenne  : {stats.get('avg_chunk_size', 0):.0f} caractères
🕐 Date            : {stats.get('timestamp', 'N/A')}"""
    except Exception as e:
        return f"❌ Erreur stats: {str(e)}"

@mcp.tool()
def list_files(directory: str = "/mnt/user-data/uploads") -> str:
    """Liste les fichiers dans un répertoire."""
    try:
        path = Path(directory)
        if not path.exists():
            # Si le dossier n'existe pas, lister les documents de Supabase
            if uploader_v2:
                try:
                    docs = supabase.client.table('documents_full').select('file_name,created_at').limit(20).execute()
                    if docs.data:
                        lines = [f"📂 Documents dans Supabase ({len(docs.data)} premiers):\n"]
                        for doc in docs.data:
                            lines.append(f"📄 {doc['file_name']}")
                        return "\n".join(lines)
                except:
                    pass
            return f"❌ Le dossier {directory} n'existe pas"
        
        files = []
        for item in path.rglob("*"):
            if item.is_file():
                rel = str(item.relative_to(path))
                files.append((rel, str(item)))
        
        files.sort()
        out = [f"📂 {directory} | {len(files)} fichier(s)\n"]
        for rel, full in files:
            try:
                size_kb = os.path.getsize(full) / 1024
                out.append(f"📄 {rel} ({size_kb:.2f} KB)")
            except:
                out.append(f"📄 {rel}")
        return "\n".join(out)
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

# -----------------------------------------------------------------------------
# Application Starlette avec routes personnalisées
# -----------------------------------------------------------------------------
async def handle_mcp_request(request: Request):
    """Gère les requêtes MCP sur toutes les routes"""
    # Obtenir le handler MCP
    mcp_handler = mcp.get_asgi_handler()
    
    # Passer la requête au handler MCP
    return await mcp_handler(request.scope, request.receive, request.send)

async def health_check(request: Request):
    """Endpoint de santé"""
    return JSONResponse({"status": "healthy", "service": "mcp-server"})

async def root_info(request: Request):
    """Info sur le service"""
    return JSONResponse({
        "service": "MCP Document Search Server",
        "version": "1.0",
        "status": "running",
        "endpoints": {
            "/": "Service info",
            "/health": "Health check",
            "/mcp": "MCP endpoint"
        }
    })

# Routes
routes = [
    Route("/", endpoint=root_info, methods=["GET"]),
    Route("/health", endpoint=health_check, methods=["GET"]),
    Route("/mcp", endpoint=handle_mcp_request, methods=["GET", "POST", "OPTIONS"]),
    # Route catch-all pour les requêtes MCP directes
    Route("/{path:path}", endpoint=handle_mcp_request, methods=["POST", "OPTIONS"]),
]

app = Starlette(routes=routes)

# CORS pour Claude/ChatGPT
app = CORSMiddleware(
    app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
async def main():
    port = int(os.getenv("PORT", "10000"))
    log.info(f"🚀 MCP Server démarré sur port {port}")
    log.info(f"📍 Endpoints: /, /health, /mcp")
    
    config = uvicorn.Config(
        app=app, 
        host="0.0.0.0", 
        port=port, 
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("🛑 Arrêt du serveur")
