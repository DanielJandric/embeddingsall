"""
Client Supabase Enhanced - Pour le nouveau schéma amélioré
- Supporte tous les nouveaux champs métadonnées
- Upload des chunks enrichis avec contexte
- Gestion des entités et tags
"""

import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SupabaseClientEnhanced:
    """
    Client pour uploader vers la nouvelle structure Supabase Enhanced.
    Gère les tables: documents_full, document_chunks, extracted_entities, document_tags
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None
    ):
        """
        Initialise le client Supabase Enhanced.

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
        logger.info("✅ Client Supabase Enhanced initialisé")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upload_document(self, document_data: Dict[str, Any]) -> int:
        """
        Upload un document complet dans documents_full avec tous les champs enrichis.

        Args:
            document_data: Données du document incluant tous les nouveaux champs

        Returns:
            ID du document créé/mis à jour
        """

        try:
            file_path = document_data.get('file_path')
            checksum = document_data.get('checksum')

            # 1) Chercher par checksum si disponible (plus fiable)
            doc_id = None
            if checksum:
                by_checksum = self.client.table("documents_full")\
                    .select("id")\
                    .eq("checksum", checksum)\
                    .execute()
                if by_checksum.data:
                    doc_id = by_checksum.data[0]['id']

            # 2) Sinon, fallback par file_path
            if doc_id is None and file_path:
                by_path = self.client.table("documents_full")\
                    .select("id")\
                    .eq("file_path", file_path)\
                    .execute()
                if by_path.data:
                    doc_id = by_path.data[0]['id']

            if doc_id is not None:
                # Mettre à jour
                self.client.table("documents_full")\
                    .update(document_data)\
                    .eq("id", doc_id)\
                    .execute()
                logger.info(f"📝 Document mis à jour: {document_data['file_name']} (ID: {doc_id})")
                return doc_id

            # Créer nouveau
            response = self.client.table("documents_full")\
                .insert(document_data)\
                .execute()

            if response.data:
                doc_id = response.data[0]['id']
                logger.info(f"✅ Document créé: {document_data['file_name']} (ID: {doc_id})")
                return doc_id

        except Exception as e:
            logger.error(f"❌ Erreur upload document {document_data.get('file_name')}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upload_chunks_batch(
        self,
        chunks_data: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        Upload des chunks enrichis avec contexte et métadonnées.

        Args:
            chunks_data: Liste de chunks enrichis
            batch_size: Taille des batches

        Returns:
            Nombre de chunks uploadés
        """

        if not chunks_data:
            return 0

        total_uploaded = 0
        document_id = chunks_data[0].get('document_id')

        # Supprimer les anciens chunks du document si mise à jour
        try:
            self.client.table("document_chunks")\
                .delete()\
                .eq("document_id", document_id)\
                .execute()
        except Exception as e:
            logger.warning(f"Impossible de supprimer anciens chunks: {e}")

        # Upload par batches
        for i in range(0, len(chunks_data), batch_size):
            batch = chunks_data[i:i + batch_size]

            logger.info(
                f"📤 Upload batch {i // batch_size + 1} "
                f"({len(batch)} chunks) pour document ID {document_id}"
            )

            try:
                response = self.client.table("document_chunks")\
                    .insert(batch)\
                    .execute()

                if response.data:
                    total_uploaded += len(response.data)
                    logger.info(f"✅ {len(response.data)} chunks uploadés")

            except Exception as e:
                logger.error(f"❌ Erreur upload batch: {e}")
                # Continuer avec le prochain batch
                continue

        return total_uploaded

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def upload_entities(
        self,
        document_id: int,
        entities: List[Dict[str, Any]]
    ) -> int:
        """
        Upload les entités extraites d'un document.

        Args:
            document_id: ID du document
            entities: Liste des entités extraites

        Returns:
            Nombre d'entités uploadées
        """

        if not entities:
            return 0

        # Préparer les données
        prepared_entities = []
        for entity in entities:
            entity_data = {
                'document_id': document_id,
                'entity_type': entity.get('type'),
                'entity_value': entity.get('value'),
                'entity_normalized': entity.get('value', '').lower().strip(),
                'context': entity.get('context'),
                'chunk_ids': entity.get('chunk_ids', []),
                'mention_count': entity.get('mention_count', 1),
                'entity_metadata': entity.get('metadata', {})
            }
            prepared_entities.append(entity_data)

        try:
            response = self.client.table("extracted_entities")\
                .insert(prepared_entities)\
                .execute()

            if response.data:
                logger.info(f"✅ {len(response.data)} entités uploadées")
                return len(response.data)

        except Exception as e:
            logger.error(f"❌ Erreur upload entités: {e}")
            return 0

        return 0

    def create_or_get_tag(self, tag_name: str, tag_category: str = None) -> int:
        """
        Crée ou récupère un tag.

        Args:
            tag_name: Nom du tag
            tag_category: Catégorie du tag

        Returns:
            ID du tag
        """

        try:
            # Vérifier si le tag existe
            existing = self.client.table("document_tags")\
                .select("id")\
                .eq("tag_name", tag_name)\
                .execute()

            if existing.data:
                return existing.data[0]['id']

            # Créer le tag
            response = self.client.table("document_tags")\
                .insert({
                    'tag_name': tag_name,
                    'tag_category': tag_category,
                    'usage_count': 0
                })\
                .execute()

            if response.data:
                return response.data[0]['id']

        except Exception as e:
            logger.error(f"❌ Erreur création tag {tag_name}: {e}")
            return None

    def link_tags_to_document(
        self,
        document_id: int,
        tags: List[str],
        tag_category: str = 'auto'
    ):
        """
        Lie des tags à un document.

        Args:
            document_id: ID du document
            tags: Liste de noms de tags
            tag_category: Catégorie des tags
        """

        for tag_name in tags:
            tag_id = self.create_or_get_tag(tag_name, tag_category)

            if tag_id:
                try:
                    self.client.table("document_tag_relations")\
                        .insert({
                            'document_id': document_id,
                            'tag_id': tag_id,
                            'confidence': 1.0
                        })\
                        .execute()

                    # Incrémenter usage_count
                    self.client.table("document_tags")\
                        .update({'usage_count': self.client.table("document_tags")
                                .select("usage_count")
                                .eq("id", tag_id)
                                .execute().data[0]['usage_count'] + 1})\
                        .eq("id", tag_id)\
                        .execute()

                except Exception as e:
                    # Relation déjà existante probablement
                    pass

    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        filter_type_document: str = None,
        filter_categorie: str = None,
        filter_commune: str = None,
        filter_canton: str = None,
        filter_tags: List[str] = None,
        min_date: str = None,
        max_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique avec filtres enrichis.

        Args:
            query_embedding: Embedding de la requête
            limit: Nombre de résultats max
            threshold: Seuil de similarité
            filter_type_document: Filtrer par type de document
            filter_categorie: Filtrer par catégorie
            filter_commune: Filtrer par commune
            filter_canton: Filtrer par canton
            filter_tags: Filtrer par tags
            min_date: Date minimum
            max_date: Date maximum

        Returns:
            Liste des chunks similaires avec métadonnées enrichies
        """

        try:
            # Utiliser la fonction RPC enhanced
            response = self.client.rpc(
                "match_document_chunks_enhanced",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": limit,
                    "filter_type_document": filter_type_document,
                    "filter_categorie": filter_categorie,
                    "filter_commune": filter_commune,
                    "filter_canton": filter_canton,
                    "filter_tags": filter_tags,
                    "min_date": min_date,
                    "max_date": max_date
                }
            ).execute()

            logger.info(f"🔍 Trouvé {len(response.data)} chunks similaires")
            return response.data

        except Exception as e:
            logger.error(f"❌ Erreur recherche: {e}")
            raise

    def search_fulltext(
        self,
        search_query: str,
        limit: int = 20,
        filter_type_document: str = None,
        filter_categorie: str = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche full-text avec PostgreSQL tsvector.

        Args:
            search_query: Texte de recherche
            limit: Nombre de résultats
            filter_type_document: Filtrer par type
            filter_categorie: Filtrer par catégorie

        Returns:
            Liste des documents correspondants avec extraits
        """

        try:
            response = self.client.rpc(
                "search_documents_fulltext",
                {
                    "search_query": search_query,
                    "match_count": limit,
                    "filter_type_document": filter_type_document,
                    "filter_categorie": filter_categorie
                }
            ).execute()

            logger.info(f"🔍 Trouvé {len(response.data)} documents (full-text)")
            return response.data

        except Exception as e:
            logger.error(f"❌ Erreur recherche full-text: {e}")
            raise

    def search_hybrid(
        self,
        search_text: str,
        query_embedding: List[float],
        limit: int = 10,
        semantic_weight: float = 0.6,
        fulltext_weight: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Recherche hybride combinant sémantique et full-text.

        Args:
            search_text: Texte de recherche
            query_embedding: Embedding de la requête
            limit: Nombre de résultats
            semantic_weight: Poids de la recherche sémantique
            fulltext_weight: Poids de la recherche full-text

        Returns:
            Liste des résultats combinés
        """

        try:
            response = self.client.rpc(
                "search_hybrid",
                {
                    "search_text": search_text,
                    "query_embedding": query_embedding,
                    "match_count": limit,
                    "semantic_weight": semantic_weight,
                    "fulltext_weight": fulltext_weight
                }
            ).execute()

            logger.info(f"🔍 Trouvé {len(response.data)} résultats (hybride)")
            return response.data

        except Exception as e:
            logger.error(f"❌ Erreur recherche hybride: {e}")
            raise

    def get_stats_by_category(self) -> List[Dict[str, Any]]:
        """Récupère les statistiques par catégorie"""
        try:
            response = self.client.table("stats_by_category").select("*").execute()
            return response.data
        except Exception as e:
            logger.error(f"❌ Erreur stats par catégorie: {e}")
            return []

    def get_stats_by_location(self) -> List[Dict[str, Any]]:
        """Récupère les statistiques par localisation"""
        try:
            response = self.client.table("stats_by_location").select("*").execute()
            return response.data
        except Exception as e:
            logger.error(f"❌ Erreur stats par localisation: {e}")
            return []

    def refresh_materialized_views(self):
        """Rafraîchit les vues matérialisées pour stats à jour"""
        try:
            self.client.rpc("refresh_all_materialized_views", {}).execute()
            logger.info("✅ Vues matérialisées rafraîchies")
        except Exception as e:
            logger.error(f"❌ Erreur rafraîchissement vues: {e}")


# Alias pour compatibilité avec les anciens scripts
SupabaseClient = SupabaseClientEnhanced
