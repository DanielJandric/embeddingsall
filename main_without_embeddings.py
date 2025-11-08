#!/usr/bin/env python3
"""
Script pour traiter des documents avec OCR Azure et Supabase
VERSION SANS EMBEDDINGS (pour quand OpenAI n'est pas configuré)
"""

import os
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

from src.logger import setup_logger
from src.azure_ocr import AzureOCRProcessor
from src.supabase_client import SupabaseUploader


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Traitement de documents avec OCR Azure et Supabase (SANS embeddings)"
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Répertoire ou fichier d'entrée"
    )

    parser.add_argument(
        "-o", "--output",
        default="data/processed",
        help="Répertoire de sortie pour les résultats JSON (défaut: data/processed)"
    )

    parser.add_argument(
        "-t", "--table",
        default="documents",
        help="Nom de la table Supabase (défaut: documents)"
    )

    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload les résultats vers Supabase"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Niveau de logging"
    )

    args = parser.parse_args()

    # Setup logger
    logger = setup_logger(level=getattr(__import__('logging'), args.log_level))

    # Charger la configuration
    load_dotenv()

    # Vérifier les paramètres Azure
    if not os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT") or not os.getenv("AZURE_FORM_RECOGNIZER_KEY"):
        logger.error("Configuration Azure manquante! Vérifiez votre fichier .env")
        return

    # Initialiser le processeur OCR
    logger.info("Initialisation d'Azure OCR...")
    ocr_processor = AzureOCRProcessor()

    # Initialiser Supabase si upload demandé
    if args.upload:
        if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
            logger.error("Configuration Supabase manquante! Vérifiez votre fichier .env")
            return

        logger.info("Initialisation de Supabase...")
        supabase_uploader = SupabaseUploader()

    # Traiter le fichier ou répertoire
    input_path = Path(args.input)

    if input_path.is_file():
        logger.info(f"Mode fichier unique: {input_path}")

        # OCR
        try:
            ocr_result = ocr_processor.process_file(str(input_path))
            logger.info(f"✅ OCR terminé - {len(ocr_result['full_text'])} caractères extraits")
        except Exception as e:
            logger.error(f"Erreur OCR: {e}")
            return

        # Sauvegarder localement
        output_file = Path(args.output) / f"{input_path.stem}_ocr.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ocr_result, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Résultats sauvegardés: {output_file}")

        # Upload vers Supabase si demandé
        if args.upload:
            logger.info("Upload vers Supabase...")

            # Préparer les données sans embeddings
            data = {
                "content": ocr_result['full_text'],
                "embedding": None,  # Pas d'embeddings
                "metadata": {
                    "file_path": str(input_path),
                    "page_count": ocr_result.get('page_count', 0),
                    "extraction_method": "azure_ocr_only"
                }
            }

            try:
                supabase_uploader.upload_document(args.table, data)
                logger.info("✅ Document uploadé dans Supabase")
            except Exception as e:
                logger.error(f"Erreur upload: {e}")

    elif input_path.is_dir():
        logger.info(f"Mode répertoire: {input_path}")

        # Trouver tous les fichiers
        supported_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        files = [
            f for f in input_path.rglob('*')
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        logger.info(f"Trouvé {len(files)} fichiers à traiter")

        all_results = []

        for file_path in tqdm(files, desc="Traitement des fichiers"):
            try:
                # OCR
                ocr_result = ocr_processor.process_file(str(file_path))

                # Sauvegarder localement
                output_file = Path(args.output) / f"{file_path.stem}_ocr.json"
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(ocr_result, f, ensure_ascii=False, indent=2)

                all_results.append(ocr_result)

                logger.info(f"✅ {file_path.name}")

            except Exception as e:
                logger.error(f"❌ Erreur avec {file_path.name}: {e}")

        # Upload vers Supabase si demandé
        if args.upload and all_results:
            logger.info(f"Upload de {len(all_results)} documents vers Supabase...")

            documents = []
            for result in all_results:
                documents.append({
                    "content": result['full_text'],
                    "embedding": None,
                    "metadata": {
                        "file_path": result.get('file_path', ''),
                        "page_count": result.get('page_count', 0),
                        "extraction_method": "azure_ocr_only"
                    }
                })

            try:
                supabase_uploader.upload_batch(args.table, documents)
                logger.info(f"✅ {len(documents)} documents uploadés")
            except Exception as e:
                logger.error(f"Erreur upload: {e}")

        logger.info(f"🎉 Traitement terminé! {len(all_results)} fichiers traités")

    else:
        logger.error(f"Chemin invalide: {args.input}")

    logger.info("\n💡 Note: Cette version N'inclut PAS les embeddings OpenAI")
    logger.info("   Pour activer les embeddings, configurez le billing sur OpenAI")
    logger.info("   puis utilisez: python main.py")


if __name__ == "__main__":
    main()
