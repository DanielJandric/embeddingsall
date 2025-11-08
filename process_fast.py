#!/usr/bin/env python3
"""
Script ULTRA-RAPIDE pour traiter les fichiers en PARALLÈLE
Jusqu'à 10x plus rapide que process_all.py
"""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.logger import setup_logger
from src.embeddings import EmbeddingGenerator
from src.supabase_client import SupabaseUploader


def detect_file_type(file_path):
    """Détecte le type de fichier"""
    ext = Path(file_path).suffix.lower()

    if ext in ['.txt', '.md', '.csv', '.json', '.xml', '.html']:
        return 'text'
    elif ext in ['.pdf']:
        return 'pdf'
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
        return 'image'
    else:
        return 'unknown'


def read_text_file(file_path, max_size_mb=10):
    """Lit un fichier texte"""
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > max_size_mb:
            return None

        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read(max_size_mb * 1024 * 1024)
                    return content
            except UnicodeDecodeError:
                continue
        return None
    except Exception:
        return None


def process_with_ocr(file_path, ocr_processor):
    """Traite avec OCR"""
    try:
        if ocr_processor is None:
            raise Exception("Azure OCR non disponible - vérifiez vos credentials")

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 50:
            raise Exception(f"Fichier trop grand: {size_mb:.1f} MB (max 50 MB)")

        result = ocr_processor.process_file(file_path)
        text = result.get('full_text', '')

        if not text or len(text.strip()) == 0:
            raise Exception("OCR n'a extrait aucun texte du PDF")

        return text
    except Exception as e:
        raise Exception(f"Erreur OCR: {str(e)}")


def process_single_file(file_path, ocr_processor, embedding_generator, supabase_uploader, upload=True):
    """Traite un fichier - VERSION THREAD-SAFE"""

    try:
        file_type = detect_file_type(file_path)
        text = None

        # 1. Extraction
        if file_type == 'text':
            text = read_text_file(file_path)
            if not text:
                raise Exception("Impossible de lire le fichier texte")
        elif file_type in ['pdf', 'image']:
            text = process_with_ocr(file_path, ocr_processor)
        else:
            # Essayer de lire comme texte pour les fichiers sans extension
            text = read_text_file(file_path)
            if not text:
                raise Exception(f"Type de fichier non supporté: {file_type}")

        if not text or len(text.strip()) == 0:
            raise Exception("Aucun texte extrait")

        # 2. Embeddings
        chunks = embedding_generator.chunk_text(text, chunk_size=1000, overlap=200)

        # IMPORTANT : Limiter le nombre de chunks pour éviter de surcharger l'API
        if len(chunks) > 100:
            chunks = chunks[:100]  # Limiter à 100 chunks max par fichier

        embeddings = embedding_generator.generate_embeddings_batch(chunks, batch_size=20)

        # 3. Upload
        if upload and embeddings:
            documents = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding:
                    documents.append({
                        "content": chunk,
                        "embedding": embedding,
                        "metadata": {
                            "file_path": str(file_path),
                            "file_name": Path(file_path).name,
                            "file_type": file_type,
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        }
                    })

            if documents:
                supabase_uploader.upload_batch("documents", documents, batch_size=100)

        return {'success': True, 'file': file_path, 'chunks': len(chunks)}

    except Exception as e:
        return {'success': False, 'file': file_path, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Traitement RAPIDE en parallèle"
    )

    parser.add_argument("-i", "--input", required=True, help="Dossier à traiter")
    parser.add_argument("--upload", action="store_true", help="Upload vers Supabase")
    parser.add_argument("--workers", type=int, default=5, help="Nombre de threads (défaut: 5)")
    parser.add_argument("--max-files", type=int, default=None, help="Limiter le nombre de fichiers")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()

    logger = setup_logger(level=getattr(logging, args.log_level))
    load_dotenv()

    print("="*70)
    print("🚀 TRAITEMENT ULTRA-RAPIDE EN PARALLÈLE")
    print("="*70)

    # Lister les fichiers
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Dossier {args.input} n'existe pas")
        return

    all_files = [f for f in input_path.rglob('*') if f.is_file() and not f.name.startswith('.')]

    if args.max_files:
        all_files = all_files[:args.max_files]

    print(f"\n📂 Dossier: {input_path}")
    print(f"📊 Fichiers: {len(all_files)}")
    print(f"⚡ Workers: {args.workers}")

    if len(all_files) == 0:
        print("⚠️  Aucun fichier")
        return

    # Initialiser les services
    print("\n🔧 Initialisation...")

    try:
        from src.azure_ocr import AzureOCRProcessor
        ocr_processor = AzureOCRProcessor()
        print("✅ Azure OCR initialisé")
    except Exception as e:
        print(f"⚠️  Azure OCR non disponible: {str(e)}")
        print("   → Les PDFs et images ne pourront pas être traités")
        print("   → Seuls les fichiers texte (.txt, .md, etc.) seront traités")
        ocr_processor = None

    embedding_generator = EmbeddingGenerator()

    if args.upload:
        supabase_uploader = SupabaseUploader()
    else:
        supabase_uploader = None

    # Traitement PARALLÈLE
    print(f"\n⚡ Traitement parallèle ({args.workers} workers)...\n")

    success_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Soumettre tous les fichiers
        futures = {
            executor.submit(
                process_single_file,
                str(f),
                ocr_processor,
                embedding_generator,
                supabase_uploader,
                args.upload
            ): f for f in all_files
        }

        # Progress bar
        with tqdm(total=len(all_files), desc="Progression") as pbar:
            for future in as_completed(futures):
                result = future.result()

                if result['success']:
                    success_count += 1
                    logger.info(f"✅ {Path(result['file']).name} ({result.get('chunks', 0)} chunks)")
                else:
                    error_count += 1
                    logger.error(f"❌ {Path(result['file']).name}: {result.get('error', 'Unknown')}")

                pbar.update(1)

    # Résumé
    print("\n" + "="*70)
    print("📊 RÉSUMÉ")
    print("="*70)
    print(f"✅ Succès: {success_count}")
    print(f"❌ Erreurs: {error_count}")
    print(f"📁 Total: {len(all_files)}")

    if args.upload:
        print(f"\n💾 Documents dans Supabase (table: documents)")

    print("\n🎉 Terminé !")


if __name__ == "__main__":
    main()
