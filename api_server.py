#!/usr/bin/env python3
"""
API REST pour exposer les fonctionnalités de recherche sémantique.
Compatible avec ChatGPT via GPT Actions et Function Calling.

Endpoints:
- POST /api/search - Recherche sémantique
- POST /api/upload - Upload de document
- GET /api/stats - Statistiques de la base
- POST /api/files/read - Lire un fichier
- POST /api/files/write - Écrire un fichier
- POST /api/files/list - Lister des fichiers
"""

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import tempfile
from pathlib import Path
import logging
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

from src.semantic_search import SemanticSearchEngine
from src.embeddings import EmbeddingGenerator
from src.supabase_client_v2 import SupabaseUploaderV2
from src.azure_ocr import AzureOCRProcessor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(
    title="Documents Search API",
    description="API REST pour la recherche sémantique dans les documents",
    version="1.0.0"
)

# CORS pour permettre les requêtes depuis ChatGPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, restreindre aux domaines OpenAI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialiser les composants
try:
    search_engine = SemanticSearchEngine()
    embedding_gen = EmbeddingGenerator()
    uploader_v2 = SupabaseUploaderV2()
    logger.info("✅ Composants de recherche et upload initialisés")
except Exception as e:
    logger.error(f"❌ Erreur initialisation: {e}")
    search_engine = None
    embedding_gen = None
    uploader_v2 = None

# Azure OCR (optionnel)
try:
    ocr_processor = AzureOCRProcessor()
    logger.info("✅ Azure OCR initialisé")
except Exception as e:
    logger.warning(f"⚠️ Azure OCR non disponible: {e}")
    ocr_processor = None


# ============================================================================
# Modèles Pydantic pour validation
# ============================================================================

class SearchRequest(BaseModel):
    query: str = Field(..., description="Question ou requête de recherche")
    limit: Optional[int] = Field(5, description="Nombre de résultats", ge=1, le=20)
    threshold: Optional[float] = Field(0.3, description="Seuil de similarité", ge=0.0, le=1.0)

class UploadDocumentRequest(BaseModel):
    file_path: str = Field(..., description="Chemin absolu du fichier à uploader")

class ReadFileRequest(BaseModel):
    file_path: str = Field(..., description="Chemin absolu du fichier à lire")
    max_chars: Optional[int] = Field(10000, description="Nombre max de caractères", ge=100, le=50000)

class WriteFileRequest(BaseModel):
    file_path: str = Field(..., description="Chemin absolu du fichier à créer")
    content: str = Field(..., description="Contenu à écrire")
    encoding: Optional[str] = Field("utf-8", description="Encodage du fichier")

class ListFilesRequest(BaseModel):
    directory: str = Field(..., description="Chemin du dossier à lister")
    pattern: Optional[str] = Field("*", description="Pattern de filtre (ex: '*.pdf')")
    recursive: Optional[bool] = Field(False, description="Recherche récursive")


# ============================================================================
# Endpoints API
# ============================================================================

@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "name": "Documents Search API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "search": "POST /api/search",
            "upload": "POST /api/upload",
            "stats": "GET /api/stats",
            "read_file": "POST /api/files/read",
            "write_file": "POST /api/files/write",
            "list_files": "POST /api/files/list"
        }
    }

@app.get("/api/stats")
async def get_stats():
    """
    Récupère les statistiques de la base de données.
    """
    try:
        if uploader_v2:
            stats = uploader_v2.get_database_stats()
            return {
                "success": True,
                "data": stats
            }
        else:
            raise HTTPException(status_code=500, detail="Uploader non initialisé")
    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search_documents(request: SearchRequest):
    """
    Recherche sémantique dans la base de documents.

    Exemple:
    ```json
    {
        "query": "Combien vaut l'immeuble de Aigle ?",
        "limit": 5,
        "threshold": 0.3
    }
    ```
    """
    try:
        if not search_engine:
            raise HTTPException(status_code=500, detail="Moteur de recherche non initialisé")

        results = search_engine.search(
            query=request.query,
            limit=request.limit,
            threshold=request.threshold
        )

        return {
            "success": True,
            "query": request.query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Erreur recherche: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_document(request: UploadDocumentRequest):
    """
    Upload un document dans la base de données.
    Le document sera traité (OCR, chunking, embeddings) puis indexé.

    Exemple:
    ```json
    {
        "file_path": "C:\\Documents\\rapport.pdf"
    }
    ```
    """
    try:
        if not embedding_gen or not uploader_v2:
            raise HTTPException(status_code=500, detail="Composants d'upload non initialisés")

        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail=f"Fichier non trouvé: {request.file_path}")

        # Importer la fonction de traitement
        from process_v2 import process_single_file

        result = process_single_file(
            file_path=request.file_path,
            embedding_gen=embedding_gen,
            uploader=uploader_v2,
            ocr_processor=ocr_processor,
            upload=True
        )

        if result["status"] == "success":
            return {
                "success": True,
                "file_name": result["file_name"],
                "text_length": result["full_text_length"],
                "chunks_count": result["chunks_count"],
                "embeddings_count": result["embeddings_count"],
                "method": result["method"],
                "page_count": result.get("page_count", 0)
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Erreur inconnue"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/read")
async def read_file(request: ReadFileRequest):
    """
    Lit le contenu d'un fichier local.

    Exemple:
    ```json
    {
        "file_path": "C:\\Documents\\rapport.txt",
        "max_chars": 10000
    }
    ```
    """
    try:
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail=f"Fichier non trouvé: {request.file_path}")

        with open(request.file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        truncated = False
        if len(content) > request.max_chars:
            content = content[:request.max_chars]
            truncated = True

        file_size = os.path.getsize(request.file_path)

        return {
            "success": True,
            "file_name": Path(request.file_path).name,
            "file_path": request.file_path,
            "file_size_bytes": file_size,
            "content": content,
            "truncated": truncated,
            "chars_returned": len(content)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lecture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/write")
async def write_file(request: WriteFileRequest):
    """
    Crée ou modifie un fichier local.

    Exemple:
    ```json
    {
        "file_path": "C:\\Documents\\nouveau.txt",
        "content": "Contenu du fichier",
        "encoding": "utf-8"
    }
    ```
    """
    try:
        # Créer les dossiers parents si nécessaire
        parent_dir = Path(request.file_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        file_exists = os.path.exists(request.file_path)

        with open(request.file_path, 'w', encoding=request.encoding) as f:
            f.write(request.content)

        file_size = os.path.getsize(request.file_path)

        return {
            "success": True,
            "file_name": Path(request.file_path).name,
            "file_path": request.file_path,
            "file_size_bytes": file_size,
            "chars_written": len(request.content),
            "action": "modified" if file_exists else "created",
            "encoding": request.encoding
        }

    except Exception as e:
        logger.error(f"Erreur écriture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/list")
async def list_files(request: ListFilesRequest):
    """
    Liste les fichiers d'un dossier.

    Exemple:
    ```json
    {
        "directory": "C:\\Documents",
        "pattern": "*.pdf",
        "recursive": false
    }
    ```
    """
    try:
        if not os.path.exists(request.directory):
            raise HTTPException(status_code=404, detail=f"Dossier non trouvé: {request.directory}")

        if not os.path.isdir(request.directory):
            raise HTTPException(status_code=400, detail=f"Le chemin n'est pas un dossier: {request.directory}")

        import fnmatch
        files = []
        dir_path = Path(request.directory)

        if request.recursive:
            for root, dirs, filenames in os.walk(request.directory):
                for filename in filenames:
                    if fnmatch.fnmatch(filename, request.pattern):
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, request.directory)
                        try:
                            size = os.path.getsize(full_path)
                            files.append({
                                "name": filename,
                                "relative_path": rel_path,
                                "full_path": full_path,
                                "size_bytes": size
                            })
                        except:
                            pass
        else:
            for item in dir_path.iterdir():
                if item.is_file() and fnmatch.fnmatch(item.name, request.pattern):
                    try:
                        size = os.path.getsize(str(item))
                        files.append({
                            "name": item.name,
                            "relative_path": item.name,
                            "full_path": str(item),
                            "size_bytes": size
                        })
                    except:
                        pass

        files.sort(key=lambda x: x["name"])

        return {
            "success": True,
            "directory": request.directory,
            "pattern": request.pattern,
            "recursive": request.recursive,
            "count": len(files),
            "files": files
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur listage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Point d'entrée
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Démarrer le serveur
    uvicorn.run(
        app,
        host="0.0.0.0",  # Accessible depuis l'extérieur
        port=8000,
        log_level="info"
    )
