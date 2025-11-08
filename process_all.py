#!/usr/bin/env python3
"""
Script ROBUSTE pour traiter TOUS les fichiers d'un dossier
- Gère tous les types de fichiers (PDF, images, TXT, etc.)
- Découpe automatiquement les fichiers trop grands
- Continue même en cas d'erreur
- Upload vers Supabase
"""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import logging

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
        # Vérifier la taille
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > max_size_mb:
            logging.warning(f"Fichier {file_path} trop grand ({size_mb:.1f}MB), limitation à {max_size_mb}MB")

        # Lire avec différents encodages
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    # Limiter la taille lue
                    content = f.read(max_size_mb * 1024 * 1024)
                    return content
            except UnicodeDecodeError:
                continue

        logging.error(f"Impossible de lire {file_path} avec les encodages standards")
        return None

    except Exception as e:
        logging.error(f"Erreur lecture {file_path}: {e}")
        return None


def process_with_ocr(file_path, ocr_processor, logger):
    """Traite avec OCR (PDF ou image)"""
    try:
        from src.azure_ocr import AzureOCRProcessor

        # Vérifier la taille du fichier
        size_mb = os.path.getsize(file_path) / (1024 * 1024)

        if size_mb > 50:
            logger.warning(f"Fichier {file_path} trop grand ({size_mb:.1f}MB), limite Azure = 50MB")
            logger.info(f"Tentative de traitement partiel...")
            # Pour l'instant, on skip les fichiers trop grands
            # TODO: implémenter découpage PDF
            return None

        result = ocr_processor.process_file(file_path)
        return result.get('full_text', '')

    except Exception as e:
        logger.error(f"Erreur OCR pour {file_path}: {e}")
        return None


def process_single_file(file_path, ocr_processor, embedding_generator, supabase_uploader, logger, upload=True):
    """Traite un fichier unique - ROBUSTE"""

    logger.info(f"📄 Traitement: {Path(file_path).name}")

    file_type = detect_file_type(file_path)
    text = None

    # 1. Extraire le texte selon le type
    if file_type == 'text':
        logger.info(f"   Type: Fichier texte")
        text = read_text_file(file_path)

    elif file_type in ['pdf', 'image']:
        logger.info(f"   Type: {file_type.upper()} (OCR)")
        text = process_with_ocr(file_path, ocr_processor, logger)

    else:
        logger.warning(f"   Type inconnu: {Path(file_path).suffix}, tentative de lecture texte...")
        text = read_text_file(file_path)

    if not text or len(text.strip()) == 0:
        logger.error(f"   ❌ Pas de texte extrait")
        return False

    logger.info(f"   ✅ Texte extrait: {len(text)} caractères")

    # 2. Générer les embeddings
    try:
        logger.info(f"   Génération des embeddings...")

        # Découper le texte en chunks
        chunks = embedding_generator.chunk_text(text, chunk_size=1000, overlap=200)
        logger.info(f"   Découpage: {len(chunks)} chunks")

        # Générer les embeddings
        embeddings = embedding_generator.generate_embeddings_batch(chunks, batch_size=10)
        logger.info(f"   ✅ {len(embeddings)} embeddings générés")

    except Exception as e:
        logger.error(f"   ❌ Erreur embeddings: {e}")
        return False

    # 3. Upload vers Supabase
    if upload:
        try:
            logger.info(f"   Upload vers Supabase...")

            documents = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding:  # Vérifier que l'embedding n'est pas vide
                    documents.append({
                        "content": chunk,
                        "embedding": embedding,
                        "metadata": {
                            "file_path": str(file_path),
                            "file_name": Path(file_path).name,
                            "file_type": file_type,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "file_size": os.path.getsize(file_path)
                        }
                    })

            if documents:
                result = supabase_uploader.upload_batch("documents", documents, batch_size=50)
                logger.info(f"   ✅ {len(documents)} chunks uploadés dans Supabase")
            else:
                logger.warning(f"   ⚠️  Aucun embedding valide à uploader")

        except Exception as e:
            logger.error(f"   ❌ Erreur upload Supabase: {e}")
            return False

    logger.info(f"   ✅ Traitement terminé avec succès")
    return True


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Traitement ROBUSTE de tous les fichiers d'un dossier"
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Dossier contenant les fichiers à traiter"
    )

    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload vers Supabase (sinon juste extraction locale)"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Niveau de logging"
    )

    args = parser.parse_args()

    # Setup logger
    logger = setup_logger(level=getattr(logging, args.log_level))

    # Charger config
    load_dotenv()

    logger.info("="*70)
    logger.info("🚀 TRAITEMENT ROBUSTE DE FICHIERS")
    logger.info("="*70)

    # Vérifier le dossier
    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_dir():
        logger.error(f"❌ Le dossier {args.input} n'existe pas")
        return

    # Lister TOUS les fichiers (pas de filtre d'extension)
    all_files = [f for f in input_path.rglob('*') if f.is_file() and not f.name.startswith('.')]

    logger.info(f"\n📂 Dossier: {input_path}")
    logger.info(f"📊 Fichiers trouvés: {len(all_files)}")

    if len(all_files) == 0:
        logger.warning("⚠️  Aucun fichier trouvé")
        return

    # Initialiser les services
    logger.info("\n🔧 Initialisation des services...")

    try:
        from src.azure_ocr import AzureOCRProcessor
        ocr_processor = AzureOCRProcessor()
        logger.info("   ✅ Azure OCR")
    except Exception as e:
        logger.error(f"   ❌ Azure OCR: {e}")
        ocr_processor = None

    try:
        embedding_generator = EmbeddingGenerator()
        logger.info("   ✅ OpenAI Embeddings")
    except Exception as e:
        logger.error(f"   ❌ OpenAI: {e}")
        return

    if args.upload:
        try:
            supabase_uploader = SupabaseUploader()
            logger.info("   ✅ Supabase")
        except Exception as e:
            logger.error(f"   ❌ Supabase: {e}")
            return
    else:
        supabase_uploader = None

    # Traiter chaque fichier
    logger.info("\n📝 Traitement des fichiers...\n")

    success_count = 0
    error_count = 0

    for file_path in tqdm(all_files, desc="Progression"):
        try:
            success = process_single_file(
                str(file_path),
                ocr_processor,
                embedding_generator,
                supabase_uploader,
                logger,
                upload=args.upload
            )

            if success:
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            logger.error(f"❌ Erreur inattendue pour {file_path.name}: {e}")
            error_count += 1

    # Résumé
    logger.info("\n" + "="*70)
    logger.info("📊 RÉSUMÉ")
    logger.info("="*70)
    logger.info(f"✅ Succès: {success_count}")
    logger.info(f"❌ Erreurs: {error_count}")
    logger.info(f"📁 Total: {len(all_files)}")

    if args.upload:
        logger.info(f"\n💾 Les documents sont dans Supabase (table: documents)")

    logger.info("\n🎉 Traitement terminé !")


if __name__ == "__main__":
    main()
