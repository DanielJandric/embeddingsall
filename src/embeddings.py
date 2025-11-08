"""
Module pour générer des embeddings via OpenAI
"""

import os
import logging
from typing import List, Dict, Optional
import time
from tenacity import retry, stop_after_attempt, wait_exponential

from openai import OpenAI
from .chunking_config import chunking_manager, get_chunking_params

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Générateur d'embeddings utilisant l'API OpenAI.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small"
    ):
        """
        Initialise le générateur d'embeddings.

        Args:
            api_key: Clé API OpenAI
            model: Modèle d'embedding à utiliser
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        if not self.api_key:
            raise ValueError(
                "OpenAI API key doit être fournie via le paramètre "
                "ou la variable d'environnement OPENAI_API_KEY"
            )

        self.client = OpenAI(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding pour un texte donné.

        Args:
            text: Texte à encoder

        Returns:
            Liste de floats représentant l'embedding
        """
        if not text or not text.strip():
            logger.warning("Texte vide, retour d'un embedding vide")
            return []

        # Limiter la taille du texte (OpenAI a des limites)
        max_length = 8000  # Limite de tokens approximative
        text = text[:max_length]

        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )

            embedding = response.data[0].embedding
            logger.debug(f"Embedding généré pour texte de longueur {len(text)}")

            return embedding

        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'embedding: {e}")
            raise

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Génère des embeddings pour une liste de textes en batch.

        Args:
            texts: Liste de textes à encoder
            batch_size: Taille des batches pour l'API

        Returns:
            Liste d'embeddings
        """
        embeddings = []

        # Traiter par batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            logger.info(f"Traitement du batch {i // batch_size + 1} ({len(batch)} textes)")

            try:
                # Filtrer les textes vides
                valid_texts = [t for t in batch if t and t.strip()]

                if not valid_texts:
                    logger.warning(f"Batch {i // batch_size + 1} ne contient que des textes vides")
                    embeddings.extend([[]] * len(batch))
                    continue

                # Limiter la taille des textes
                max_length = 8000
                valid_texts = [t[:max_length] for t in valid_texts]

                response = self.client.embeddings.create(
                    input=valid_texts,
                    model=self.model
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                # Respecter les limites de taux
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Erreur lors du traitement du batch {i // batch_size + 1}: {e}")
                # Ajouter des embeddings vides en cas d'erreur
                embeddings.extend([[]] * len(batch))

        return embeddings

    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[str]:
        """
        Découpe un texte long en chunks avec chevauchement.

        Args:
            text: Texte à découper
            chunk_size: Taille approximative de chaque chunk en caractères
                       (utilise la configuration globale si None)
            overlap: Nombre de caractères de chevauchement entre chunks
                    (utilise la configuration globale si None)

        Returns:
            Liste de chunks de texte
        """
        # Utiliser la configuration globale si non spécifié
        if chunk_size is None or overlap is None:
            default_chunk_size, default_overlap = get_chunking_params()
            chunk_size = chunk_size or default_chunk_size
            overlap = overlap or default_overlap
        if not text or len(text) <= chunk_size:
            return [text] if text else []

        chunks = []
        start = 0

        while start < len(text):
            # Calculer la fin du chunk
            end = min(start + chunk_size, len(text))

            # Si ce n'est pas le dernier chunk, essayer de couper à un espace
            if end < len(text):
                # Chercher le dernier espace avant la fin
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Avancer avec chevauchement - S'ASSURER qu'on progresse toujours
            if end < len(text):
                new_start = end - overlap
                # Si on ne progresse pas, forcer la progression
                if new_start <= start:
                    new_start = start + max(1, chunk_size // 2)
                start = new_start
            else:
                start = end  # Fin du texte

        logger.info(f"Texte découpé en {len(chunks)} chunks")
        return chunks

    def process_ocr_result(
        self,
        ocr_result: Dict[str, any],
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[Dict[str, any]]:
        """
        Traite un résultat OCR pour générer des embeddings par chunks.

        Args:
            ocr_result: Résultat OCR du module azure_ocr
            chunk_size: Taille des chunks de texte (utilise la configuration globale si None)
            overlap: Chevauchement entre chunks (utilise la configuration globale si None)

        Returns:
            Liste de dicts avec texte et embeddings
        """
        # Utiliser la configuration globale si non spécifié
        if chunk_size is None or overlap is None:
            default_chunk_size, default_overlap = get_chunking_params()
            chunk_size = chunk_size or default_chunk_size
            overlap = overlap or default_overlap
        full_text = ocr_result.get("full_text", "")

        if not full_text:
            logger.warning(f"Pas de texte dans {ocr_result.get('file_path', 'unknown')}")
            return []

        # Découper le texte
        chunks = self.chunk_text(full_text, chunk_size, overlap)

        # Générer les embeddings
        embeddings = self.generate_embeddings_batch(chunks)

        # Créer les résultats
        results = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            results.append({
                "file_path": ocr_result.get("file_path"),
                "chunk_index": idx,
                "chunk_text": chunk,
                "embedding": embedding,
                "page_count": ocr_result.get("page_count"),
                "metadata": {
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                }
            })

        logger.info(f"Généré {len(results)} embeddings pour {ocr_result.get('file_path')}")
        return results
