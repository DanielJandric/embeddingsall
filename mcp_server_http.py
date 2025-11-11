#!/usr/bin/env python3
"""
Serveur MCP avec transport HTTP/SSE pour ChatGPT (Developer Mode) et Claude Desktop.

- Endpoints HTTP utilitaires: /mcp, /mcp/, /health, /
- Transport MCP SSE: /sse
- Tolérant aux méthodes GET/POST/HEAD/OPTIONS sur /mcp et /mcp/
- A exposer via ngrok: ngrok http 3000 --host-header=localhost:3000
"""

import asyncio
import logging
import json
import os
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv
load_dotenv()

# MCP SDK
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Resource, Tool, TextContent

# Tes modules applicatifs
from src.semantic_search import SemanticSearchEngine
from src.supabase_client import SupabaseUploader
from src.embeddings import EmbeddingGenerator
from src.supabase_client_v2 import SupabaseUploaderV2
from src.azure_ocr import AzureOCRProcessor

# HTTP layer
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import uvicorn

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_server_http")

# -----------------------------------------------------------------------------
# Initialisations applicatives
# -----------------------------------------------------------------------------
logger.info("✅ Moteur de recherche sémantique initialisé")
search_engine = SemanticSearchEngine()
supabase = SupabaseUploader()

try:
    embedding_gen = EmbeddingGenerator()
    uploader_v2 = SupabaseUploaderV2()
    logger.info("✅ Générateur d'embeddings et uploader V2 initialisés")
except Exception as e:
    logger.warning(f"⚠️ Impossible d'initialiser l'uploader V2: {e}")
    embedding_gen = None
    uploader_v2 = None

try:
    ocr_processor = AzureOCRProcessor()
    logger.info("✅ Azure OCR initialisé")
except Exception as e:
    logger.warning(f"⚠️ Azure OCR non disponible: {e}")
    ocr_processor = None

# -----------------------------------------------------------------------------
# Serveur MCP (SDK)
# -----------------------------------------------------------------------------
mcp_server = Server("documents-search-server")

@mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    try:
        if uploader_v2:
            stats = uploader_v2.get_database_stats()
        else:
            stats = {"total_documents": 0, "total_chunks": 0}
        return [
            Resource(
                uri="supabase://documents/stats",
                name="Database Statistics",
                mimeType="application/json",
                description=(
                    "Statistics about the documents database. "
                    f"Total: {stats.get('total_documents', 0)} documents, "
                    f"{stats.get('total_chunks', 0)} chunks"
                ),
            )
        ]
    except Exception as e:
        logger.error(f"Erreur list_resources: {e}")
        return []

@mcp_server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "supabase://documents/stats":
        try:
            if uploader_v2:
                stats = uploader_v2.get_database_stats()
            else:
                stats = {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "error": "Uploader V2 non initialise",
                }
            return json.dumps(stats, indent=2)
        except Exception as e:
            logger.error(f"Erreur read_resource: {e}")
            return json.dumps({"error": str(e)})
    return json.dumps({"error": "Resource not found"})

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_documents",
            description="Recherche sémantique dans la base de documents (embeddings).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "threshold": {"type": "number", "default": 0.3},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_context_for_rag",
            description="Retourne un contexte formaté pour RAG à partir de la requête.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "threshold": {"type": "number", "default": 0.3},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_database_stats",
            description="Statistiques de la base Supabase.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="upload_document",
            description="Upload un document (PDF/TXT/MD/CSV) avec extraction/embeddings.",
            inputSchema={
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
        ),
        Tool(
            name="read_file",
            description="Lit un fichier texte (aperçu).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "max_chars": {"type": "integer", "default": 10000},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="write_file",
            description="Écrit/écrase un fichier texte.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "required": ["file_path", "content"],
            },
        ),
        Tool(
            name="list_files",
            description="Liste les fichiers d'un dossier (pattern + récursif).",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "pattern": {"type": "string", "default": "*"},
                    "recursive": {"type": "boolean", "default": False},
                },
                "required": ["directory"],
            },
        ),
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    try:
        if name == "search_documents":
            query = arguments.get("query")
            limit = arguments.get("limit", 5)
            threshold = arguments.get("threshold", 0.3)
            logger.info(f"🔍 Recherche: {query} (limit={limit}, threshold={threshold})")
            results = search_engine.search(query=query, limit=limit, threshold=threshold)
            if not results:
                return [TextContent(type="text", text="Aucun résultat trouvé.")]
            lines: list[str] = []
            lines.append(f"🔍 Requête: {query}")
            lines.append(f"📊 {len(results)} résultats\n")
            lines.append("=" * 70)
            for r in results:
                lines.append(f"\n#{r['rank']} - {r['file_name']}")
                lines.append(f"   Similarité: {r['similarity']:.2%}")
                lines.append(f"   Chunk: {r['chunk_index']}")
                lines.append("   Contenu:")
                content = r["content"]
                if len(content) > 800:
                    content = content[:800] + "..."
                for line in content.split("\n"):
                    if line.strip():
                        lines.append(f"   {line}")
            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_context_for_rag":
            query = arguments.get("query")
            limit = arguments.get("limit", 5)
            threshold = arguments.get("threshold", 0.3)
            logger.info(f"📚 Contexte RAG pour: {query}")
            context = search_engine.get_context_for_rag(query=query, limit=limit, threshold=threshold)
            return [TextContent(type="text", text=context)]

        elif name == "get_database_stats":
            logger.info("📊 Stats DB")
            if uploader_v2:
                stats = uploader_v2.get_database_stats()
            else:
                return [TextContent(type="text", text="❌ Uploader V2 non initialisé.")]
            out = []
            out.append("📊 STATISTIQUES DE LA BASE")
            out.append("=" * 70)
            out.append(f"📁 Total documents : {stats.get('total_documents', 0)}")
            out.append(f"📦 Total chunks    : {stats.get('total_chunks', 0)}")
            out.append(f"📊 Moy. chunks/doc : {stats.get('avg_chunks_per_document', 0):.1f}")
            out.append(f"📏 Taille moyenne  : {stats.get('avg_chunk_size', 0):.0f} caractères")
            out.append(f"🕐 Date            : {stats.get('timestamp', 'N/A')}")
            return [TextContent(type="text", text="\n".join(out))]

        elif name == "upload_document":
            file_path = arguments.get("file_path")
            if not file_path:
                return [TextContent(type="text", text="❌ file_path est requis")]
            if embedding_gen is None or uploader_v2 is None:
                return [TextContent(type="text", text="❌ Composants d'upload non initialisés")]
            logger.info(f"📤 Upload: {file_path}")
            try:
                from process_v2 import process_single_file
                result = process_single_file(
                    file_path=file_path,
                    embedding_gen=embedding_gen,
                    uploader=uploader_v2,
                    ocr_processor=ocr_processor,
                    upload=True,
                )
                if result["status"] == "success":
                    out = []
                    out.append("✅ UPLOAD RÉUSSI")
                    out.append("=" * 70)
                    out.append(f"📄 Fichier             : {result['file_name']}")
                    out.append(f"📝 Texte extrait       : {result['full_text_length']} caractères")
                    out.append(f"🔢 Chunks créés        : {result['chunks_count']}")
                    out.append(f"🧠 Embeddings générés  : {result['embeddings_count']}")
                    out.append(f"⚙️ Méthode             : {result['method']}")
                    if result.get("page_count"):
                        out.append(f"📄 Pages               : {result['page_count']}")
                    return [TextContent(type="text", text="\n".join(out))]
                else:
                    return [TextContent(type="text", text=f"❌ Erreur upload:\n{result.get('error', 'Inconnue')}")]
            except Exception as e:
                logger.exception("Erreur upload")
                return [TextContent(type="text", text=f"❌ Erreur upload:\n{str(e)}")]

        elif name == "read_file":
            file_path = arguments.get("file_path")
            max_chars = arguments.get("max_chars", 10000)
            if not file_path:
                return [TextContent(type="text", text="❌ file_path est requis")]
            logger.info(f"📖 Lecture: {file_path}")
            try:
                if not os.path.exists(file_path):
                    return [TextContent(type="text", text=f"❌ Fichier introuvable: {file_path}")]
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                truncated = False
                if len(content) > max_chars:
                    content = content[:max_chars]
                    truncated = True
                file_name = Path(file_path).name
                size_kb = os.path.getsize(file_path) / 1024
                out = []
                out.append(f"📖 {file_name}")
                out.append("=" * 70)
                out.append(f"📍 {file_path}")
                out.append(f"📊 {size_kb:.2f} KB")
                out.append(f"📝 {len(content)} caractères")
                if truncated:
                    out.append(f"⚠️ Contenu tronqué à {max_chars} caractères")
                out.append("")
                out.append(content)
                return [TextContent(type="text", text="\n".join(out))]
            except Exception as e:
                logger.exception("Erreur lecture")
                return [TextContent(type="text", text=f"❌ Erreur lecture:\n{str(e)}")]

        elif name == "write_file":
            file_path = arguments.get("file_path")
            content = arguments.get("content")
            encoding = arguments.get("encoding", "utf-8")
            if not file_path or content is None:
                return [TextContent(type="text", text="❌ file_path et content sont requis")]
            logger.info(f"✍️ Écriture: {file_path}")
            try:
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding=encoding) as f:
                    f.write(content)
                size_kb = os.path.getsize(file_path) / 1024
                out = []
                out.append("✅ FICHIER ÉCRIT")
                out.append("=" * 70)
                out.append(f"📄 {Path(file_path).name}")
                out.append(f"📍 {file_path}")
                out.append(f"📊 {size_kb:.2f} KB")
                out.append(f"📝 {len(content)} caractères")
                out.append(f"🔤 {encoding}")
                return [TextContent(type="text", text="\n".join(out))]
            except Exception as e:
                logger.exception("Erreur écriture")
                return [TextContent(type="text", text=f"❌ Erreur écriture:\n{str(e)}")]

        elif name == "list_files":
            directory = arguments.get("directory")
            pattern = arguments.get("pattern", "*")
            recursive = arguments.get("recursive", False)
            if not directory:
                return [TextContent(type="text", text="❌ directory est requis")]
            logger.info(f"📂 Listage: {directory} (pattern={pattern}, recursive={recursive})")
            try:
                import fnmatch
                if not os.path.exists(directory):
                    return [TextContent(type="text", text=f"❌ Dossier introuvable: {directory}")]
                if not os.path.isdir(directory):
                    return [TextContent(type="text", text=f"❌ Chemin non dossier: {directory}")]
                files: list[tuple[str, str]] = []
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
                out = []
                out.append("📂 CONTENU")
                out.append("=" * 70)
                out.append(f"📍 {directory}")
                out.append(f"🔍 {pattern}")
                out.append(f"🔄 Récursif: {'Oui' if recursive else 'Non'}")
                out.append(f"📊 {len(files)} fichier(s)")
                out.append("")
                for rel, full in files:
                    try:
                        size_kb = os.path.getsize(full) / 1024
                        out.append(f"📄 {rel} ({size_kb:.2f} KB)")
                    except Exception:
                        out.append(f"📄 {rel}")
                return [TextContent(type="text", text="\n".join(out))]
            except Exception as e:
                logger.exception("Erreur listage")
                return [TextContent(type="text", text=f"❌ Erreur listage:\n{str(e)}")]

        else:
            return [TextContent(type="text", text=f"Outil inconnu: {name}")]
    except Exception as e:
        logger.exception("Erreur call_tool")
        return [TextContent(type="text", text=f"Erreur: {str(e)}")]

# -----------------------------------------------------------------------------
# HTTP app (FastAPI) + SSE (Starlette)
# -----------------------------------------------------------------------------
http_app = FastAPI()
http_app.router.redirect_slashes = False  # ne pas réécrire /mcp -> /mcp/

@http_app.api_route("/mcp", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def mcp_entry(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    if request.method == "OPTIONS":
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET,POST,HEAD,OPTIONS",
            },
        )
    return JSONResponse({"ok": True, "endpoint": "/mcp"})

@http_app.api_route("/mcp/", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def mcp_entry_slash(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    if request.method == "OPTIONS":
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "GET,POST,HEAD,OPTIONS",
            },
        )
    return JSONResponse({"ok": True, "endpoint": "/mcp/"})

@http_app.api_route("/", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def root_redirect():
    return RedirectResponse(url="/mcp/", status_code=307)

@http_app.get("/health")
def health():
    return {"ok": True}

# Transport SSE MCP
async def handle_sse(request):
    async with SseServerTransport("/messages") as transport:
        await mcp_server.run(
            transport.read_stream,
            transport.write_stream,
            mcp_server.create_initialization_options(),
        )
    return Response(status_code=200)

# ASGI composite: /sse (SSE) + / (FastAPI)
starlette_app = Starlette(
    routes=[
        Route("/sse", handle_sse),
        Mount("/", app=http_app),
    ]
)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
async def main():
    logger.info("🚀 Démarrage du serveur MCP HTTP/SSE de recherche documentaire")
    logger.info("🌐 Transport: SSE (/sse) + HTTP utilitaires (/mcp, /health)")
    config = uvicorn.Config(
        app=starlette_app,
        host="0.0.0.0",
        port=3000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt du serveur MCP HTTP/SSE")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
