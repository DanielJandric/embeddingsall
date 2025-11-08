#!/usr/bin/env python3
"""
Exemples d'utilisation des modules
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.azure_ocr import AzureOCRProcessor
from src.embeddings import EmbeddingGenerator
from src.supabase_client import SupabaseUploader


def example_ocr():
    """Exemple d'utilisation de l'OCR Azure"""
    print("\n=== Exemple OCR ===\n")

    load_dotenv()

    # Initialiser le processeur OCR
    ocr = AzureOCRProcessor()

    # Traiter une image
    result = ocr.process_file("data/input/exemple.pdf")

    print(f"Fichier: {result['file_path']}")
    print(f"Nombre de pages: {result['page_count']}")
    print(f"Texte extrait (100 premiers caractères):")
    print(result['full_text'][:100])
    print("...")


def example_embeddings():
    """Exemple de génération d'embeddings"""
    print("\n=== Exemple Embeddings ===\n")

    load_dotenv()

    # Initialiser le générateur
    embedder = EmbeddingGenerator()

    # Générer un embedding pour un texte
    text = "Ceci est un exemple de texte pour générer un embedding."
    embedding = embedder.generate_embedding(text)

    print(f"Texte: {text}")
    print(f"Dimension de l'embedding: {len(embedding)}")
    print(f"Premiers 5 éléments: {embedding[:5]}")


def example_chunking():
    """Exemple de découpage de texte"""
    print("\n=== Exemple Chunking ===\n")

    load_dotenv()

    embedder = EmbeddingGenerator()

    # Texte long
    long_text = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit.
    """ * 100  # Répéter pour créer un texte long

    # Découper en chunks
    chunks = embedder.chunk_text(long_text, chunk_size=500, overlap=100)

    print(f"Longueur du texte original: {len(long_text)} caractères")
    print(f"Nombre de chunks: {len(chunks)}")
    print(f"Longueur moyenne des chunks: {sum(len(c) for c in chunks) / len(chunks):.0f} caractères")


def example_supabase():
    """Exemple d'utilisation de Supabase"""
    print("\n=== Exemple Supabase ===\n")

    load_dotenv()

    # Initialiser le client
    uploader = SupabaseUploader()

    # Exemple de données
    sample_data = [
        {
            "file_path": "exemple.pdf",
            "chunk_index": 0,
            "chunk_text": "Ceci est un exemple de texte.",
            "embedding": [0.1] * 1536,  # Embedding factice
            "page_count": 1,
            "metadata": {"total_chunks": 1}
        }
    ]

    # Upload (commenté pour ne pas polluer la base)
    # results = uploader.upload_embeddings("documents", sample_data)
    # print(f"Uploadé {len(results)} documents")

    # Obtenir les statistiques
    stats = uploader.get_table_stats("documents")
    print(f"Statistiques: {stats}")


def example_complete_workflow():
    """Exemple de workflow complet"""
    print("\n=== Workflow Complet ===\n")

    load_dotenv()

    # 1. OCR
    print("1. Extraction de texte via OCR...")
    ocr = AzureOCRProcessor()
    ocr_result = ocr.process_file("data/input/exemple.pdf")

    # 2. Embeddings
    print("2. Génération d'embeddings...")
    embedder = EmbeddingGenerator()
    embeddings_data = embedder.process_ocr_result(ocr_result, chunk_size=500)

    print(f"   - Généré {len(embeddings_data)} chunks avec embeddings")

    # 3. Sauvegarde locale
    print("3. Sauvegarde locale...")
    import json
    output_file = "data/processed/exemple_embeddings.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
    print(f"   - Sauvegardé dans {output_file}")

    # 4. Upload vers Supabase (optionnel)
    print("4. Upload vers Supabase...")
    uploader = SupabaseUploader()
    # results = uploader.upload_embeddings("documents", embeddings_data)
    # print(f"   - Uploadé {len(results)} entrées")
    print("   - Commenté pour l'exemple")

    print("\n✅ Workflow terminé!")


def example_search():
    """Exemple de recherche sémantique"""
    print("\n=== Exemple Recherche Sémantique ===\n")

    load_dotenv()

    # Générer l'embedding de la requête
    embedder = EmbeddingGenerator()
    query = "intelligence artificielle"
    query_embedding = embedder.generate_embedding(query)

    print(f"Requête: {query}")
    print(f"Embedding généré: {len(query_embedding)} dimensions")

    # Rechercher dans Supabase
    uploader = SupabaseUploader()

    try:
        results = uploader.search_similar(
            table_name="documents",
            query_embedding=query_embedding,
            limit=5,
            threshold=0.7
        )

        print(f"\nTrouvé {len(results)} résultats:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Similarité: {result.get('similarity', 0):.2f}")
            print(f"   Contenu: {result.get('content', '')[:100]}...")

    except Exception as e:
        print(f"Erreur lors de la recherche: {e}")
        print("Assurez-vous que la fonction match_documents existe dans Supabase")


if __name__ == "__main__":
    print("🎯 Exemples d'utilisation\n")
    print("Choisissez un exemple:")
    print("1. OCR")
    print("2. Embeddings")
    print("3. Chunking")
    print("4. Supabase")
    print("5. Workflow complet")
    print("6. Recherche sémantique")
    print("0. Tous les exemples")

    choice = input("\nVotre choix (0-6): ")

    examples = {
        "1": example_ocr,
        "2": example_embeddings,
        "3": example_chunking,
        "4": example_supabase,
        "5": example_complete_workflow,
        "6": example_search
    }

    if choice == "0":
        for func in examples.values():
            try:
                func()
            except Exception as e:
                print(f"\n❌ Erreur: {e}\n")
    elif choice in examples:
        try:
            examples[choice]()
        except Exception as e:
            print(f"\n❌ Erreur: {e}\n")
    else:
        print("Choix invalide!")
