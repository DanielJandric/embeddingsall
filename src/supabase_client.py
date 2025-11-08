"""
Module pour le transfert de données vers Supabase
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SupabaseUploader:
    """
    Client pour uploader des données avec embeddings vers Supabase.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None
    ):
        """
        Initialise le client Supabase.

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upload_document(
        self,
        table_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload un document unique vers Supabase.

        Args:
            table_name: Nom de la table
            data: Données à uploader

        Returns:
            Réponse de Supabase
        """
        try:
            response = self.client.table(table_name).insert(data).execute()
            logger.info(f"Document uploadé dans {table_name}")
            return response.data

        except Exception as e:
            logger.error(f"Erreur lors de l'upload: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upload_batch(
        self,
        table_name: str,
        data_list: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Upload un lot de documents vers Supabase.

        Args:
            table_name: Nom de la table
            data_list: Liste de données à uploader
            batch_size: Taille des batches

        Returns:
            Liste des réponses de Supabase
        """
        results = []

        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]

            logger.info(
                f"Upload du batch {i // batch_size + 1} "
                f"({len(batch)} documents) vers {table_name}"
            )

            try:
                response = self.client.table(table_name).insert(batch).execute()
                results.extend(response.data)

                logger.info(
                    f"Batch {i // batch_size + 1} uploadé avec succès "
                    f"({len(response.data)} documents)"
                )

            except Exception as e:
                logger.error(f"Erreur lors de l'upload du batch {i // batch_size + 1}: {e}")
                # Continuer avec le prochain batch
                continue

        return results

    def upload_embeddings(
        self,
        table_name: str,
        embeddings_data: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Upload des embeddings vers Supabase avec métadonnées.

        Args:
            table_name: Nom de la table
            embeddings_data: Liste de dicts avec embeddings et métadonnées
            batch_size: Taille des batches

        Returns:
            Liste des réponses de Supabase
        """
        # Préparer les données pour Supabase
        prepared_data = []

        for item in embeddings_data:
            # Créer l'entrée pour Supabase
            entry = {
                "content": item.get("chunk_text", ""),
                "embedding": item.get("embedding", []),
                "metadata": {
                    "file_path": item.get("file_path", ""),
                    "chunk_index": item.get("chunk_index", 0),
                    "page_count": item.get("page_count", 0),
                    **item.get("metadata", {})
                },
                "created_at": datetime.utcnow().isoformat()
            }

            prepared_data.append(entry)

        logger.info(f"Préparation de {len(prepared_data)} entrées pour upload")

        # Upload par batches
        return self.upload_batch(table_name, prepared_data, batch_size)

    def create_documents_table(self, table_name: str = "documents") -> bool:
        """
        Crée la table documents dans Supabase (si elle n'existe pas).
        Note: Cette opération nécessite des permissions appropriées.

        Args:
            table_name: Nom de la table à créer

        Returns:
            True si succès
        """
        # Note: La création de table se fait généralement via l'interface Supabase
        # ou des migrations SQL. Voici un exemple de requête SQL à exécuter:

        sql = f"""
        -- Créer la table si elle n'existe pas
        CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGSERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            embedding VECTOR(1536),  -- Ajuster la dimension selon le modèle
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Créer un index pour la recherche vectorielle
        CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx
        ON {table_name}
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);

        -- Créer un index sur les métadonnées
        CREATE INDEX IF NOT EXISTS {table_name}_metadata_idx
        ON {table_name}
        USING GIN (metadata);
        """

        logger.info(f"SQL pour créer la table {table_name}:")
        logger.info(sql)

        return True

    def search_similar(
        self,
        table_name: str,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Recherche les documents similaires dans Supabase.

        Args:
            table_name: Nom de la table
            query_embedding: Embedding de la requête
            limit: Nombre de résultats max
            threshold: Seuil de similarité

        Returns:
            Liste des documents similaires
        """
        try:
            # Utiliser la fonction RPC de Supabase pour la recherche vectorielle
            response = self.client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": limit
                }
            ).execute()

            logger.info(f"Trouvé {len(response.data)} documents similaires")
            return response.data

        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            raise

    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        Récupère des statistiques sur une table.

        Args:
            table_name: Nom de la table

        Returns:
            Dict avec les statistiques
        """
        try:
            # Compter le nombre total de documents
            count_response = self.client.table(table_name)\
                .select("id", count="exact")\
                .execute()

            total = count_response.count if hasattr(count_response, 'count') else 0

            return {
                "table_name": table_name,
                "total_documents": total,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {e}")
            return {
                "table_name": table_name,
                "error": str(e)
            }

    def delete_by_file_path(
        self,
        table_name: str,
        file_path: str
    ) -> int:
        """
        Supprime tous les documents associés à un fichier.

        Args:
            table_name: Nom de la table
            file_path: Chemin du fichier

        Returns:
            Nombre de documents supprimés
        """
        try:
            response = self.client.table(table_name)\
                .delete()\
                .eq("metadata->>file_path", file_path)\
                .execute()

            deleted_count = len(response.data) if response.data else 0
            logger.info(f"Supprimé {deleted_count} documents pour {file_path}")

            return deleted_count

        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            raise
