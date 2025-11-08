"""
Client Supabase V2 - Architecture optimisée avec 2 tables
- documents_full : Documents complets
- document_chunks : Chunks avec embeddings (haute granularité)
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SupabaseUploaderV2:
    """
    Client pour uploader vers la nouvelle structure Supabase V2.
    Gère 2 tables: documents_full et document_chunks.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None
    ):
        """
        Initialise le client Supabase V2.

        Args:
            url: URL du projet Supabase
            key: Clé API Supabase
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "Supabase URL et key doivent être fournis via les paramètres "
                "ou les variables d'environnement SUPABASE_URL et SUPABASE_KEY"
            )

        self.client: Client = create_client(self.url, self.key)
        logger.info("✅ Client Supabase V2 initialisé")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upload_full_document(
        self,
        file_path: str,
        full_content: str,
        file_type: str = None,
        page_count: int = 0,
        processing_method: str = None,
        additional_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Upload un document complet dans documents_full.

        Args:
            file_path: Chemin complet du fichier
            full_content: Contenu complet du document
            file_type: Type de fichier (pdf, txt, etc.)
            page_count: Nombre de pages
            processing_method: Méthode de traitement utilisée
            additional_metadata: Métadonnées supplémentaires

        Returns:
            Document créé avec son ID
        """
        file_name = Path(file_path).name

        # Calculer des stats
        word_count = len(full_content.split())
        char_count = len(full_content)
        file_size = 0
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
        except:
            pass

        # Préparer les données
        document_data = {
            "file_name": file_name,
            "file_path": file_path,
            "file_type": file_type or Path(file_path).suffix.lstrip('.'),
            "full_content": full_content,
            "file_size_bytes": file_size,
            "page_count": page_count,
            "word_count": word_count,
            "char_count": char_count,
            "processing_method": processing_method,
            "metadata": additional_metadata or {}
        }

        try:
            # Vérifier si le document existe déjà
            existing = self.client.table("documents_full")\
                .select("id")\
                .eq("file_path", file_path)\
                .execute()

            if existing.data:
                # Mettre à jour
                doc_id = existing.data[0]['id']
                response = self.client.table("documents_full")\
                    .update(document_data)\
                    .eq("id", doc_id)\
                    .execute()
                logger.info(f"📝 Document mis à jour: {file_name} (ID: {doc_id})")
                return {"id": doc_id, **document_data}
            else:
                # Créer nouveau
                response = self.client.table("documents_full")\
                    .insert(document_data)\
                    .execute()

                if response.data:
                    doc_id = response.data[0]['id']
                    logger.info(f"✅ Document créé: {file_name} (ID: {doc_id})")
                    return response.data[0]

        except Exception as e:
            logger.error(f"❌ Erreur upload document {file_name}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upload_chunks_batch(
        self,
        document_id: int,
        chunks_data: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Upload des chunks avec embeddings pour un document.

        Args:
            document_id: ID du document dans documents_full
            chunks_data: Liste de chunks avec embeddings
            batch_size: Taille des batches

        Returns:
            Liste des chunks créés
        """
        results = []

        # Préparer les données des chunks
        prepared_chunks = []
        for chunk in chunks_data:
            chunk_entry = {
                "document_id": document_id,
                "chunk_index": chunk.get("chunk_index", 0),
                "chunk_content": chunk.get("chunk_text", ""),
                "chunk_size": len(chunk.get("chunk_text", "")),
                "embedding": chunk.get("embedding", []),
                "chunk_metadata": chunk.get("metadata", {})
            }
            prepared_chunks.append(chunk_entry)

        # Upload par batches
        for i in range(0, len(prepared_chunks), batch_size):
            batch = prepared_chunks[i:i + batch_size]

            logger.info(
                f"📤 Upload batch {i // batch_size + 1} "
                f"({len(batch)} chunks) pour document ID {document_id}"
            )

            try:
                response = self.client.table("document_chunks")\
                    .insert(batch)\
                    .execute()

                if response.data:
                    results.extend(response.data)
                    logger.info(f"✅ {len(response.data)} chunks uploadés")

            except Exception as e:
                logger.error(f"❌ Erreur upload batch: {e}")
                # Continuer avec le prochain batch
                continue

        return results

    def upload_document_with_chunks(
        self,
        file_path: str,
        full_content: str,
        chunks_with_embeddings: List[Dict[str, Any]],
        file_type: str = None,
        page_count: int = 0,
        processing_method: str = None,
        additional_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Upload un document complet avec ses chunks et embeddings.

        Args:
            file_path: Chemin du fichier
            full_content: Contenu complet
            chunks_with_embeddings: Liste des chunks avec embeddings
            file_type: Type de fichier
            page_count: Nombre de pages
            processing_method: Méthode de traitement
            additional_metadata: Métadonnées supplémentaires

        Returns:
            Dict avec info sur l'upload
        """
        logger.info(f"📄 Upload document: {Path(file_path).name}")

        # 1. Upload le document complet
        doc = self.upload_full_document(
            file_path=file_path,
            full_content=full_content,
            file_type=file_type,
            page_count=page_count,
            processing_method=processing_method,
            additional_metadata=additional_metadata
        )

        document_id = doc['id']

        # 2. Supprimer les anciens chunks si mise à jour
        try:
            self.client.table("document_chunks")\
                .delete()\
                .eq("document_id", document_id)\
                .execute()
        except:
            pass

        # 3. Upload les chunks avec embeddings
        chunks_uploaded = self.upload_chunks_batch(
            document_id=document_id,
            chunks_data=chunks_with_embeddings
        )

        logger.info(
            f"✅ Document uploadé: {len(chunks_uploaded)} chunks "
            f"({len(full_content)} caractères)"
        )

        return {
            "document_id": document_id,
            "chunks_count": len(chunks_uploaded),
            "file_name": Path(file_path).name
        }

    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Recherche les chunks similaires.

        Args:
            query_embedding: Embedding de la requête
            limit: Nombre de résultats max
            threshold: Seuil de similarité

        Returns:
            Liste des chunks similaires avec document complet
        """
        try:
            # Utiliser la fonction RPC de Supabase
            response = self.client.rpc(
                "match_document_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": limit
                }
            ).execute()

            logger.info(f"🔍 Trouvé {len(response.data)} chunks similaires")
            return response.data

        except Exception as e:
            logger.error(f"❌ Erreur recherche: {e}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de la base de données.

        Returns:
            Dict avec statistiques
        """
        try:
            response = self.client.rpc("get_database_stats").execute()

            if response.data:
                stats = response.data[0]
                return {
                    "total_documents": stats.get("total_documents", 0),
                    "total_chunks": stats.get("total_chunks", 0),
                    "avg_chunks_per_document": float(stats.get("avg_chunks_per_document", 0)),
                    "total_size_mb": float(stats.get("total_size_mb", 0)),
                    "avg_chunk_size": stats.get("avg_chunk_size", 0)
                }

            return {}

        except Exception as e:
            logger.error(f"❌ Erreur stats: {e}")
            return {"error": str(e)}

    def get_full_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un document complet par son ID.

        Args:
            document_id: ID du document

        Returns:
            Document complet ou None
        """
        try:
            response = self.client.rpc(
                "get_full_document",
                {"document_id_param": document_id}
            ).execute()

            if response.data:
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"❌ Erreur récupération document: {e}")
            return None

    def delete_document_by_path(self, file_path: str) -> Dict[str, Any]:
        """
        Supprime un document et tous ses chunks.

        Args:
            file_path: Chemin du fichier

        Returns:
            Info sur la suppression
        """
        try:
            response = self.client.rpc(
                "delete_document_by_path",
                {"file_path_param": file_path}
            ).execute()

            if response.data:
                result = response.data[0]
                logger.info(
                    f"🗑️  Document supprimé: {result.get('deleted_chunks_count', 0)} chunks"
                )
                return result

            return {"deleted_document_id": None, "deleted_chunks_count": 0}

        except Exception as e:
            logger.error(f"❌ Erreur suppression: {e}")
            raise
