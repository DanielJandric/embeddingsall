"""
Module pour la recherche sémantique dans Supabase
Combine génération d'embeddings et recherche vectorielle
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.embeddings import EmbeddingGenerator
from src.supabase_client import SupabaseUploader

try:
    from src.supabase_client_v2 import SupabaseUploaderV2
    HAS_V2 = True
except:
    HAS_V2 = False

logger = logging.getLogger(__name__)


class SemanticSearchEngine:
    """
    Moteur de recherche sémantique qui combine:
    1. Génération d'embeddings pour les requêtes
    2. Recherche vectorielle dans Supabase
    3. Post-traitement des résultats
    """

    def __init__(
        self,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        supabase_uploader: Optional[SupabaseUploader] = None
    ):
        """
        Initialise le moteur de recherche sémantique.

        Args:
            embedding_generator: Générateur d'embeddings (créé si None)
            supabase_uploader: Client Supabase (créé si None)
        """
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.supabase_uploader = supabase_uploader or SupabaseUploader()

        logger.info("✅ Moteur de recherche sémantique initialisé")

    def search(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.7,
        table_name: str = "documents"
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique dans la base de données.

        Args:
            query: Question ou requête de recherche
            limit: Nombre maximum de résultats
            threshold: Seuil de similarité (0-1)
            table_name: Nom de la table à interroger

        Returns:
            Liste de résultats avec contenu et métadonnées
        """
        logger.info(f"🔍 Recherche: '{query}'")

        # 1. Générer l'embedding de la requête
        query_embedding = self.embedding_generator.generate_embedding(query)

        if not query_embedding:
            logger.error("❌ Impossible de générer l'embedding de la requête")
            return []

        logger.info(f"✅ Embedding généré ({len(query_embedding)} dimensions)")

        # 2. Rechercher dans Supabase
        try:
            results = self.supabase_uploader.search_similar(
                table_name=table_name,
                query_embedding=query_embedding,
                limit=limit,
                threshold=threshold
            )

            logger.info(f"✅ {len(results)} résultats trouvés")

            # 3. Post-traiter les résultats
            processed_results = []
            for i, result in enumerate(results, 1):
                processed_results.append({
                    "rank": i,
                    "content": result.get("content", ""),
                    "similarity": result.get("similarity", 0),
                    "metadata": result.get("metadata", {}),
                    "file_name": result.get("metadata", {}).get("file_name", "Inconnu"),
                    "file_path": result.get("metadata", {}).get("file_path", ""),
                    "chunk_index": result.get("metadata", {}).get("chunk_index", 0)
                })

            return processed_results

        except Exception as e:
            logger.error(f"❌ Erreur lors de la recherche: {e}")
            return []

    def search_and_format(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.7
    ) -> str:
        """
        Recherche et formate les résultats pour affichage.

        Args:
            query: Question ou requête de recherche
            limit: Nombre maximum de résultats
            threshold: Seuil de similarité

        Returns:
            Résultats formatés en texte
        """
        results = self.search(query, limit, threshold)

        if not results:
            return "Aucun résultat trouvé."

        output = []
        output.append(f"\n🔍 Requête: {query}")
        output.append(f"📊 {len(results)} résultats trouvés\n")
        output.append("=" * 70)

        for result in results:
            output.append(f"\n#{result['rank']} - {result['file_name']}")
            output.append(f"   Similarité: {result['similarity']:.2%}")
            output.append(f"   Chunk: {result['chunk_index']}")
            output.append(f"\n   Contenu:")

            # Limiter l'affichage du contenu
            content = result['content']
            if len(content) > 500:
                content = content[:500] + "..."

            # Indenter le contenu
            for line in content.split('\n'):
                output.append(f"   {line}")

            output.append("")

        return "\n".join(output)

    def get_context_for_rag(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.7
    ) -> str:
        """
        Récupère le contexte pour RAG (Retrieval Augmented Generation).

        Args:
            query: Question ou requête
            limit: Nombre de chunks à récupérer
            threshold: Seuil de similarité

        Returns:
            Contexte concaténé des meilleurs résultats
        """
        results = self.search(query, limit, threshold)

        if not results:
            return "Aucun contexte trouvé dans la base de données."

        # Construire le contexte
        context_parts = []
        for result in results:
            file_name = result['file_name']
            content = result['content']
            context_parts.append(f"[Source: {file_name}]\n{content}\n")

        context = "\n---\n\n".join(context_parts)

        logger.info(f"📚 Contexte RAG généré: {len(context)} caractères de {len(results)} sources")

        return context


def test_search():
    """
    Fonction de test pour la recherche sémantique.
    """
    print("\n" + "=" * 70)
    print("TEST DE RECHERCHE SÉMANTIQUE")
    print("=" * 70)

    # Initialiser le moteur
    engine = SemanticSearchEngine()

    # Exemple de recherche
    query = "Quels sont les principaux sujets abordés dans les documents?"

    print(f"\n🔍 Recherche: {query}\n")

    formatted_results = engine.search_and_format(query, limit=3)
    print(formatted_results)

    # Test du contexte RAG
    print("\n" + "=" * 70)
    print("TEST DU CONTEXTE RAG")
    print("=" * 70)

    context = engine.get_context_for_rag(query, limit=3)
    print(f"\n📚 Contexte généré ({len(context)} caractères):\n")
    print(context[:1000] + "..." if len(context) > 1000 else context)


if __name__ == "__main__":
    # Configurer le logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test_search()
