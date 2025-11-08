#!/usr/bin/env python3
"""
Process V2 - Upload avec architecture optimisée
- Chunks plus petits (forte granularité)
- Document complet stocké séparément
- Nouvelle structure Supabase (2 tables)
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from src.azure_ocr import AzureOCRProcessor
from src.embeddings import EmbeddingGenerator
from src.supabase_client_v2 import SupabaseUploaderV2
from src.pdf_extractor import extract_text_from_pdf
from src.chunking_config import chunking_manager, get_chunking_params

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION DE LA GRANULARITÉ
# ============================================================================

# Configuration automatique via chunking_config
# Par défaut : FINE (chunk_size=400, overlap=100)
# Peut être modifié via GRANULARITY_LEVEL dans .env
# Options : ULTRA_FINE, FINE, MEDIUM, STANDARD, COARSE

config = chunking_manager.get_config()
logger.info(f"Configuration de chunking : {config}")
logger.info(f"Niveau de granularité : {chunking_manager.get_granularity_level().value.upper()}")
logger.info(f"Chunks attendus pour 10k caractères : ~{config.chunks_per_10k}")


def extract_text_from_file(file_path: str, ocr_processor: Optional[AzureOCRProcessor] = None) -> tuple:
    """
    Extrait le texte d'un fichier (PDF, TXT, etc.).

    Returns:
        (texte_complet, méthode_utilisée, page_count)
    """
    file_name = Path(file_path).name
    file_ext = Path(file_path).suffix.lower()

    # 1. Fichiers texte
    if file_ext in ['.txt', '.md', '.csv']:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            # Nettoyer les caractères null
            text = text.replace('\u0000', '').replace('\x00', '')

            if text.strip():
                return text, 'text_file', 0
        except Exception as e:
            raise Exception(f"Erreur lecture fichier texte: {e}")

    # 2. Fichiers PDF
    elif file_ext == '.pdf':
        # 2a. Essayer extraction directe d'abord
        text = extract_text_from_pdf(file_path)

        if text and len(text.strip()) > 100:
            # Compter les pages si possible
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                page_count = len(reader.pages)
            except:
                page_count = 0

            return text, 'pdf_direct', page_count

        # 2b. Fallback vers OCR si PDF scanné
        if ocr_processor is None:
            raise Exception("PDF scanné mais Azure OCR non disponible")

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 50:
            raise Exception(f"PDF scanné trop grand pour OCR: {size_mb:.1f} MB (max 50 MB)")

        try:
            result = ocr_processor.process_file(file_path)
            text = result.get('full_text', '')

            if not text or len(text.strip()) == 0:
                raise Exception("OCR n'a extrait aucun texte")

            # Nettoyer
            text = text.replace('\u0000', '').replace('\x00', '')

            return text, 'azure_ocr', result.get('page_count', 0)

        except Exception as e:
            raise Exception(f"Erreur OCR: {e}")

    else:
        raise Exception(f"Type de fichier non supporté: {file_ext}")


def process_single_file(
    file_path: str,
    embedding_gen: EmbeddingGenerator,
    uploader: SupabaseUploaderV2,
    ocr_processor: Optional[AzureOCRProcessor] = None,
    upload: bool = True
) -> Dict:
    """
    Traite un seul fichier avec la nouvelle architecture.

    Returns:
        Dict avec les résultats du traitement
    """
    file_name = Path(file_path).name

    try:
        print(f"\n{'='*70}")
        print(f"📄 {file_name}")
        print(f"{'='*70}")

        # 1. Extraction du texte
        print(f"📥 Extraction du texte...")
        full_text, method, page_count = extract_text_from_file(file_path, ocr_processor)

        print(f"✅ Texte extrait: {len(full_text)} caractères ({method})")
        if page_count:
            print(f"📄 Pages: {page_count}")

        # 2. Découpage en chunks (utilise la configuration globale)
        chunk_size, chunk_overlap = get_chunking_params()
        print(f"🔢 Découpage en chunks (taille: {chunk_size}, overlap: {chunk_overlap})...")
        chunks = embedding_gen.chunk_text(full_text)

        print(f"✅ {len(chunks)} chunks créés (granularité fine)")

        # 3. Génération des embeddings
        print(f"🧠 Génération de {len(chunks)} embeddings...")
        embeddings = embedding_gen.generate_embeddings_batch(chunks, batch_size=100)

        print(f"✅ {len(embeddings)} embeddings générés")

        # 4. Préparer les données
        chunks_with_embeddings = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunks_with_embeddings.append({
                "chunk_index": idx,
                "chunk_text": chunk,
                "embedding": embedding,
                "metadata": {
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                }
            })

        # 5. Upload vers Supabase
        if upload:
            print(f"📤 Upload vers Supabase...")

            result = uploader.upload_document_with_chunks(
                file_path=file_path,
                full_content=full_text,
                chunks_with_embeddings=chunks_with_embeddings,
                file_type=Path(file_path).suffix.lstrip('.'),
                page_count=page_count,
                processing_method=method,
                additional_metadata={
                    "original_file_name": file_name,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "granularity_level": chunking_manager.get_granularity_level().value
                }
            )

            print(f"✅ Upload terminé: {result['chunks_count']} chunks")

        return {
            "status": "success",
            "file_name": file_name,
            "full_text_length": len(full_text),
            "chunks_count": len(chunks),
            "embeddings_count": len(embeddings),
            "method": method,
            "page_count": page_count
        }

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Erreur: {error_msg}")

        return {
            "status": "error",
            "file_name": file_name,
            "error": error_msg
        }


def process_files_parallel(
    file_paths: List[str],
    embedding_gen: EmbeddingGenerator,
    uploader: SupabaseUploaderV2,
    ocr_processor: Optional[AzureOCRProcessor] = None,
    upload: bool = True,
    workers: int = 3
) -> Dict:
    """
    Traite plusieurs fichiers en parallèle.
    """
    results = {
        "success": [],
        "errors": []
    }

    total = len(file_paths)

    chunk_size, chunk_overlap = get_chunking_params()
    granularity = chunking_manager.get_granularity_level().value.upper()

    print(f"\n{'='*70}")
    print(f"🚀 TRAITEMENT DE {total} FICHIERS")
    print(f"   Workers: {workers}")
    print(f"   Niveau de granularité: {granularity}")
    print(f"   Taille chunk: {chunk_size} caractères (overlap {chunk_overlap})")
    print(f"   Upload: {'OUI' if upload else 'NON'}")
    print(f"{'='*70}\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Soumettre tous les fichiers
        future_to_file = {
            executor.submit(
                process_single_file,
                file_path,
                embedding_gen,
                uploader,
                ocr_processor,
                upload
            ): file_path
            for file_path in file_paths
        }

        # Traiter les résultats au fur et à mesure
        completed = 0
        for future in as_completed(future_to_file):
            completed += 1
            file_path = future_to_file[future]

            try:
                result = future.result()

                if result["status"] == "success":
                    results["success"].append(result)
                    print(f"\n[{completed}/{total}] ✅ {result['file_name']}: {result['chunks_count']} chunks")
                else:
                    results["errors"].append(result)
                    print(f"\n[{completed}/{total}] ❌ {result['file_name']}: {result['error']}")

            except Exception as e:
                results["errors"].append({
                    "status": "error",
                    "file_name": Path(file_path).name,
                    "error": str(e)
                })
                print(f"\n[{completed}/{total}] ❌ {Path(file_path).name}: {e}")

    return results


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Process V2 - Upload avec forte granularité et architecture optimisée"
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Dossier ou fichier à traiter"
    )

    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload vers Supabase"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Nombre de workers parallèles (défaut: 3)"
    )

    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Nombre maximum de fichiers à traiter"
    )

    parser.add_argument(
        "--extensions",
        type=str,
        default="pdf,txt,md,csv",
        help="Extensions de fichiers à traiter (séparées par des virgules)"
    )

    args = parser.parse_args()

    # Initialiser les composants
    try:
        print("🔧 Initialisation...")

        # Embeddings
        embedding_gen = EmbeddingGenerator()
        print("✅ Générateur d'embeddings initialisé")

        # Supabase V2
        uploader = SupabaseUploaderV2()
        print("✅ Client Supabase V2 initialisé")

        # Azure OCR (optionnel)
        ocr_processor = None
        try:
            ocr_processor = AzureOCRProcessor()
            print("✅ Azure OCR initialisé")
        except:
            print("⚠️  Azure OCR non disponible (PDFs scannés non supportés)")

    except Exception as e:
        print(f"❌ Erreur initialisation: {e}")
        sys.exit(1)

    # Collecter les fichiers
    input_path = Path(args.input)
    file_paths = []

    extensions = args.extensions.split(',')
    extensions = [ext.strip().lower() for ext in extensions]

    if input_path.is_file():
        file_paths = [str(input_path)]
    elif input_path.is_dir():
        for ext in extensions:
            pattern = f"**/*.{ext}" if not ext.startswith('.') else f"**/*{ext}"
            file_paths.extend([str(f) for f in input_path.glob(pattern)])

        # Limiter si demandé
        if args.max_files:
            file_paths = file_paths[:args.max_files]
    else:
        print(f"❌ Chemin invalide: {input_path}")
        sys.exit(1)

    if not file_paths:
        print(f"❌ Aucun fichier trouvé dans {input_path}")
        sys.exit(1)

    print(f"📁 {len(file_paths)} fichiers trouvés\n")

    # Traiter
    results = process_files_parallel(
        file_paths=file_paths,
        embedding_gen=embedding_gen,
        uploader=uploader,
        ocr_processor=ocr_processor,
        upload=args.upload,
        workers=args.workers
    )

    # Résumé
    print(f"\n{'='*70}")
    print(f"📊 RÉSUMÉ")
    print(f"{'='*70}")
    print(f"✅ Succès: {len(results['success'])}")
    print(f"❌ Erreurs: {len(results['errors'])}")
    print(f"📁 Total: {len(results['success']) + len(results['errors'])}")

    if results['success']:
        total_chunks = sum(r['chunks_count'] for r in results['success'])
        print(f"\n🔢 Total embeddings créés: {total_chunks}")
        print(f"📊 Moyenne par document: {total_chunks / len(results['success']):.1f}")

    if results['errors']:
        print(f"\n❌ Fichiers en erreur:")
        for error in results['errors']:
            print(f"   - {error['file_name']}: {error['error']}")

    if args.upload:
        # Afficher les stats
        stats = uploader.get_database_stats()
        print(f"\n💾 Statistiques Supabase:")
        print(f"   Documents: {stats.get('total_documents', 0)}")
        print(f"   Chunks: {stats.get('total_chunks', 0)}")
        print(f"   Moyenne chunks/doc: {stats.get('avg_chunks_per_document', 0):.1f}")
        print(f"   Taille moyenne chunk: {stats.get('avg_chunk_size', 0)} caractères")

    print(f"\n🎉 Terminé !")


if __name__ == "__main__":
    main()
