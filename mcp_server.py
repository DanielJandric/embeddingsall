#!/usr/bin/env python3
"""
Serveur MCP (Model Context Protocol) pour la recherche sémantique
Expose les fonctionnalités de recherche dans la base de données Supabase

Ce serveur peut être utilisé avec Claude Desktop, Cline, ou tout autre
client compatible MCP.
"""

import asyncio
import logging
import json
from typing import Any, Sequence
from pathlib import Path

from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

from src.semantic_search import SemanticSearchEngine
from src.supabase_client import SupabaseUploader

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialiser le moteur de recherche
search_engine = SemanticSearchEngine()
supabase = SupabaseUploader()

# Créer le serveur MCP
app = Server("documents-search-server")


@app.list_resources()
async def list_resources() -> list[Resource]:
    """
    Liste les ressources disponibles (statistiques de la base de données).
    """
    try:
        stats = supabase.get_table_stats("documents")

        return [
            Resource(
                uri="supabase://documents/stats",
                name="Database Statistics",
                mimeType="application/json",
                description=f"Statistics about the documents database. Total: {stats.get('total_documents', 0)} documents"
            )
        ]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des ressources: {e}")
        return []


@app.read_resource()
async def read_resource(uri: str) -> str:
    """
    Lit une ressource spécifique (statistiques).
    """
    if uri == "supabase://documents/stats":
        try:
            stats = supabase.get_table_stats("documents")
            return json.dumps(stats, indent=2)
        except Exception as e:
            logger.error(f"Erreur lecture ressource: {e}")
            return json.dumps({"error": str(e)})

    return json.dumps({"error": "Resource not found"})


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    Liste les outils disponibles (fonctions de recherche).
    """
    return [
        Tool(
            name="search_documents",
            description=(
                "Recherche sémantique dans la base de données de documents. "
                "Utilise les embeddings pour trouver les passages les plus pertinents "
                "par rapport à une question ou requête. "
                "Retourne les meilleurs résultats avec leur score de similarité."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Question ou requête de recherche"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre maximum de résultats (défaut: 5)",
                        "default": 5
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Seuil de similarité entre 0 et 1 (défaut: 0.7)",
                        "default": 0.7
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_context_for_rag",
            description=(
                "Récupère le contexte pertinent pour RAG (Retrieval Augmented Generation). "
                "Recherche les passages les plus pertinents et les retourne sous forme de "
                "contexte formaté, prêt à être utilisé dans un prompt pour un LLM."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Question ou sujet de recherche"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre de chunks à récupérer (défaut: 5)",
                        "default": 5
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Seuil de similarité (défaut: 0.7)",
                        "default": 0.7
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_database_stats",
            description=(
                "Récupère les statistiques de la base de données: "
                "nombre total de documents, nombre de fichiers uniques, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """
    Exécute un outil (fonction de recherche).
    """
    try:
        if name == "search_documents":
            query = arguments.get("query")
            limit = arguments.get("limit", 5)
            threshold = arguments.get("threshold", 0.7)

            logger.info(f"🔍 Recherche: {query} (limit={limit}, threshold={threshold})")

            # Effectuer la recherche
            results = search_engine.search(
                query=query,
                limit=limit,
                threshold=threshold
            )

            if not results:
                return [TextContent(
                    type="text",
                    text="Aucun résultat trouvé pour cette requête."
                )]

            # Formater les résultats
            output = []
            output.append(f"🔍 Requête: {query}")
            output.append(f"📊 {len(results)} résultats trouvés\n")
            output.append("=" * 70)

            for result in results:
                output.append(f"\n#{result['rank']} - {result['file_name']}")
                output.append(f"   Similarité: {result['similarity']:.2%}")
                output.append(f"   Chunk: {result['chunk_index']}")
                output.append(f"\n   Contenu:")

                # Limiter l'affichage du contenu
                content = result['content']
                if len(content) > 800:
                    content = content[:800] + "..."

                # Indenter le contenu
                for line in content.split('\n'):
                    if line.strip():
                        output.append(f"   {line}")

                output.append("")

            return [TextContent(
                type="text",
                text="\n".join(output)
            )]

        elif name == "get_context_for_rag":
            query = arguments.get("query")
            limit = arguments.get("limit", 5)
            threshold = arguments.get("threshold", 0.7)

            logger.info(f"📚 Contexte RAG pour: {query}")

            # Récupérer le contexte
            context = search_engine.get_context_for_rag(
                query=query,
                limit=limit,
                threshold=threshold
            )

            return [TextContent(
                type="text",
                text=context
            )]

        elif name == "get_database_stats":
            logger.info("📊 Récupération des statistiques")

            stats = supabase.get_table_stats("documents")

            output = []
            output.append("📊 STATISTIQUES DE LA BASE DE DONNÉES")
            output.append("=" * 70)
            output.append(f"📁 Total documents: {stats.get('total_documents', 0)}")
            output.append(f"🕐 Date: {stats.get('timestamp', 'N/A')}")

            return [TextContent(
                type="text",
                text="\n".join(output)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Outil inconnu: {name}"
            )]

    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de {name}: {e}")
        import traceback
        traceback.print_exc()

        return [TextContent(
            type="text",
            text=f"Erreur: {str(e)}"
        )]


async def main():
    """
    Point d'entrée principal du serveur MCP.
    """
    logger.info("🚀 Démarrage du serveur MCP de recherche documentaire")
    logger.info("📚 Moteur de recherche sémantique initialisé")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt du serveur MCP")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
