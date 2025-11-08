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
from src.embeddings import EmbeddingGenerator
from src.supabase_client_v2 import SupabaseUploaderV2
from src.azure_ocr import AzureOCRProcessor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialiser le moteur de recherche
search_engine = SemanticSearchEngine()
supabase = SupabaseUploader()

# Initialiser les composants pour l'upload
try:
    embedding_gen = EmbeddingGenerator()
    uploader_v2 = SupabaseUploaderV2()
    logger.info("✅ Générateur d'embeddings et uploader V2 initialisés")
except Exception as e:
    logger.warning(f"⚠️ Impossible d'initialiser l'uploader: {e}")
    embedding_gen = None
    uploader_v2 = None

# Azure OCR (optionnel)
try:
    ocr_processor = AzureOCRProcessor()
    logger.info("✅ Azure OCR initialisé")
except Exception as e:
    logger.warning(f"⚠️ Azure OCR non disponible: {e}")
    ocr_processor = None

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
        ),
        Tool(
            name="upload_document",
            description=(
                "Upload un document vers la base de données. "
                "Le document sera traité (extraction de texte, chunking, embeddings) "
                "puis uploadé dans Supabase. "
                "Supporte les formats: PDF, TXT, MD, CSV. "
                "Pour les PDFs scannés, utilise Azure OCR automatiquement."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Chemin absolu du fichier à uploader"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="read_file",
            description=(
                "Lit le contenu d'un fichier local. "
                "Supporte: TXT, MD, CSV, JSON, Python, etc. "
                "Pour les fichiers PDF, affiche un résumé (utilisez upload_document pour traiter complètement)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Chemin absolu du fichier à lire"
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Nombre maximum de caractères à retourner (défaut: 10000)",
                        "default": 10000
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="write_file",
            description=(
                "Crée ou modifie un fichier local. "
                "Si le fichier existe, il sera écrasé. "
                "Supporte tous les formats texte: TXT, MD, CSV, JSON, Python, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Chemin absolu du fichier à créer/modifier"
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenu à écrire dans le fichier"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Encodage du fichier (défaut: utf-8)",
                        "default": "utf-8"
                    }
                },
                "required": ["file_path", "content"]
            }
        ),
        Tool(
            name="list_files",
            description=(
                "Liste les fichiers d'un dossier. "
                "Utile pour explorer la structure de fichiers avant de lire/écrire. "
                "Peut filtrer par extension."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Chemin du dossier à lister"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Pattern de filtre (ex: '*.pdf', '*.txt')",
                        "default": "*"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Recherche récursive dans les sous-dossiers",
                        "default": False
                    }
                },
                "required": ["directory"]
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

        elif name == "upload_document":
            file_path = arguments.get("file_path")

            if not file_path:
                return [TextContent(
                    type="text",
                    text="❌ Erreur: file_path est requis"
                )]

            # Vérifier que les composants sont initialisés
            if embedding_gen is None or uploader_v2 is None:
                return [TextContent(
                    type="text",
                    text="❌ Erreur: Les composants d'upload ne sont pas initialisés"
                )]

            logger.info(f"📤 Upload du document: {file_path}")

            try:
                # Importer la fonction de traitement
                from process_v2 import process_single_file

                # Traiter le fichier
                result = process_single_file(
                    file_path=file_path,
                    embedding_gen=embedding_gen,
                    uploader=uploader_v2,
                    ocr_processor=ocr_processor,
                    upload=True
                )

                # Formater la réponse
                if result["status"] == "success":
                    output = []
                    output.append("✅ UPLOAD RÉUSSI")
                    output.append("=" * 70)
                    output.append(f"📄 Fichier: {result['file_name']}")
                    output.append(f"📝 Texte extrait: {result['full_text_length']} caractères")
                    output.append(f"🔢 Chunks créés: {result['chunks_count']}")
                    output.append(f"🧠 Embeddings générés: {result['embeddings_count']}")
                    output.append(f"⚙️ Méthode: {result['method']}")
                    if result.get('page_count'):
                        output.append(f"📄 Pages: {result['page_count']}")

                    return [TextContent(
                        type="text",
                        text="\n".join(output)
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"❌ Erreur lors de l'upload:\n{result.get('error', 'Erreur inconnue')}"
                    )]

            except Exception as e:
                logger.error(f"Erreur upload: {e}")
                import traceback
                traceback.print_exc()

                return [TextContent(
                    type="text",
                    text=f"❌ Erreur lors de l'upload:\n{str(e)}"
                )]

        elif name == "read_file":
            file_path = arguments.get("file_path")
            max_chars = arguments.get("max_chars", 10000)

            if not file_path:
                return [TextContent(
                    type="text",
                    text="❌ Erreur: file_path est requis"
                )]

            logger.info(f"📖 Lecture du fichier: {file_path}")

            try:
                import os
                from pathlib import Path

                # Vérifier que le fichier existe
                if not os.path.exists(file_path):
                    return [TextContent(
                        type="text",
                        text=f"❌ Erreur: Le fichier n'existe pas:\n{file_path}"
                    )]

                # Lire le fichier
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Limiter la taille
                truncated = False
                if len(content) > max_chars:
                    content = content[:max_chars]
                    truncated = True

                # Formater la réponse
                file_name = Path(file_path).name
                file_size = os.path.getsize(file_path)
                file_size_kb = file_size / 1024

                output = []
                output.append(f"📖 LECTURE DU FICHIER: {file_name}")
                output.append("=" * 70)
                output.append(f"📍 Chemin: {file_path}")
                output.append(f"📊 Taille: {file_size_kb:.2f} KB")
                output.append(f"📝 Caractères: {len(content)}")
                if truncated:
                    output.append(f"⚠️ Contenu tronqué à {max_chars} caractères")
                output.append("=" * 70)
                output.append("")
                output.append(content)

                return [TextContent(
                    type="text",
                    text="\n".join(output)
                )]

            except Exception as e:
                logger.error(f"Erreur lecture: {e}")
                return [TextContent(
                    type="text",
                    text=f"❌ Erreur lors de la lecture:\n{str(e)}"
                )]

        elif name == "write_file":
            file_path = arguments.get("file_path")
            content = arguments.get("content")
            encoding = arguments.get("encoding", "utf-8")

            if not file_path or content is None:
                return [TextContent(
                    type="text",
                    text="❌ Erreur: file_path et content sont requis"
                )]

            logger.info(f"✍️ Écriture dans le fichier: {file_path}")

            try:
                import os
                from pathlib import Path

                # Créer les dossiers parents si nécessaire
                parent_dir = Path(file_path).parent
                parent_dir.mkdir(parents=True, exist_ok=True)

                # Vérifier si le fichier existe déjà
                file_exists = os.path.exists(file_path)
                action = "modifié" if file_exists else "créé"

                # Écrire le fichier
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)

                # Confirmer
                file_name = Path(file_path).name
                file_size = os.path.getsize(file_path)
                file_size_kb = file_size / 1024

                output = []
                output.append(f"✅ FICHIER {action.upper()}")
                output.append("=" * 70)
                output.append(f"📄 Fichier: {file_name}")
                output.append(f"📍 Chemin: {file_path}")
                output.append(f"📊 Taille: {file_size_kb:.2f} KB")
                output.append(f"📝 Caractères écrits: {len(content)}")
                output.append(f"🔤 Encodage: {encoding}")
                output.append(f"✨ Action: Fichier {action} avec succès")

                return [TextContent(
                    type="text",
                    text="\n".join(output)
                )]

            except Exception as e:
                logger.error(f"Erreur écriture: {e}")
                import traceback
                traceback.print_exc()

                return [TextContent(
                    type="text",
                    text=f"❌ Erreur lors de l'écriture:\n{str(e)}"
                )]

        elif name == "list_files":
            directory = arguments.get("directory")
            pattern = arguments.get("pattern", "*")
            recursive = arguments.get("recursive", False)

            if not directory:
                return [TextContent(
                    type="text",
                    text="❌ Erreur: directory est requis"
                )]

            logger.info(f"📂 Listage du dossier: {directory}")

            try:
                import os
                from pathlib import Path
                import fnmatch

                # Vérifier que le dossier existe
                if not os.path.exists(directory):
                    return [TextContent(
                        type="text",
                        text=f"❌ Erreur: Le dossier n'existe pas:\n{directory}"
                    )]

                if not os.path.isdir(directory):
                    return [TextContent(
                        type="text",
                        text=f"❌ Erreur: Le chemin n'est pas un dossier:\n{directory}"
                    )]

                # Lister les fichiers
                files = []
                dir_path = Path(directory)

                if recursive:
                    # Recherche récursive
                    for root, dirs, filenames in os.walk(directory):
                        for filename in filenames:
                            if fnmatch.fnmatch(filename, pattern):
                                full_path = os.path.join(root, filename)
                                rel_path = os.path.relpath(full_path, directory)
                                files.append((rel_path, full_path))
                else:
                    # Recherche non-récursive
                    for item in dir_path.iterdir():
                        if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                            files.append((item.name, str(item)))

                # Trier par nom
                files.sort()

                # Formater la réponse
                output = []
                output.append(f"📂 CONTENU DU DOSSIER")
                output.append("=" * 70)
                output.append(f"📍 Dossier: {directory}")
                output.append(f"🔍 Pattern: {pattern}")
                output.append(f"🔄 Récursif: {'Oui' if recursive else 'Non'}")
                output.append(f"📊 Fichiers trouvés: {len(files)}")
                output.append("=" * 70)
                output.append("")

                if files:
                    for rel_path, full_path in files:
                        try:
                            size = os.path.getsize(full_path)
                            size_kb = size / 1024
                            output.append(f"📄 {rel_path} ({size_kb:.2f} KB)")
                        except:
                            output.append(f"📄 {rel_path}")
                else:
                    output.append("(Aucun fichier trouvé)")

                return [TextContent(
                    type="text",
                    text="\n".join(output)
                )]

            except Exception as e:
                logger.error(f"Erreur listage: {e}")
                return [TextContent(
                    type="text",
                    text=f"❌ Erreur lors du listage:\n{str(e)}"
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
