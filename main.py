#!/usr/bin/env python3
"""
Script principal pour le traitement de documents avec OCR, embeddings et Supabase.

Ce script orchestre:
1. L'extraction de texte via Azure OCR
2. La génération d'embeddings via OpenAI
3. Le transfert des données vers Supabase
"""

import os
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm

from src.logger import setup_logger
from src.azure_ocr import AzureOCRProcessor
from src.embeddings import EmbeddingGenerator
from src.supabase_client import SupabaseUploader


def load_config():
    """Charge la configuration depuis le fichier .env"""
    load_dotenv()

    config = {
        # Azure
        "azure_endpoint": os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT"),
        "azure_key": os.getenv("AZURE_FORM_RECOGNIZER_KEY"),

        # OpenAI
        "openai_key": os.getenv("OPENAI_API_KEY"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),

        # Supabase
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_key": os.getenv("SUPABASE_KEY"),

        # Configuration de traitement
        "batch_size": int(os.getenv("BATCH_SIZE", "100")),
        "chunk_size": int(os.getenv("CHUNK_SIZE", "1000")),
        "max_workers": int(os.getenv("MAX_WORKERS", "4"))
    }

    return config


def process_single_file(
    file_path: str,
    ocr_processor: AzureOCRProcessor,
    embedding_generator: EmbeddingGenerator,
    logger
) -> List[Dict[str, Any]]:
    """
    Traite un fichier unique: OCR -> Embeddings.

    Args:
        file_path: Chemin du fichier
        ocr_processor: Processeur OCR
        embedding_generator: Générateur d'embeddings
        logger: Logger

    Returns:
        Liste de dicts avec texte et embeddings
    """
    logger.info(f"Traitement de {file_path}")

    # Étape 1: OCR
    try:
        ocr_result = ocr_processor.process_file(file_path)
    except Exception as e:
        logger.error(f"Erreur OCR pour {file_path}: {e}")
        return []

    # Étape 2: Embeddings
    try:
        embeddings_data = embedding_generator.process_ocr_result(ocr_result)
    except Exception as e:
        logger.error(f"Erreur embeddings pour {file_path}: {e}")
        return []

    return embeddings_data


def process_directory(
    input_dir: str,
    output_dir: str,
    table_name: str,
    upload_to_supabase: bool,
    config: Dict[str, Any],
    logger
):
    """
    Traite tous les fichiers d'un répertoire.

    Args:
        input_dir: Répertoire d'entrée
        output_dir: Répertoire de sortie
        table_name: Nom de la table Supabase
        upload_to_supabase: Si True, upload vers Supabase
        config: Configuration
        logger: Logger
    """
    # Initialiser les processeurs
    logger.info("Initialisation des processeurs...")

    ocr_processor = AzureOCRProcessor(
        endpoint=config["azure_endpoint"],
        key=config["azure_key"]
    )

    embedding_generator = EmbeddingGenerator(
        api_key=config["openai_key"],
        model=config["embedding_model"]
    )

    if upload_to_supabase:
        supabase_uploader = SupabaseUploader(
            url=config["supabase_url"],
            key=config["supabase_key"]
        )

    # Trouver tous les fichiers
    input_path = Path(input_dir)
    supported_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    files = [
        f for f in input_path.rglob('*')
        if f.is_file() and f.suffix.lower() in supported_extensions
    ]

    logger.info(f"Trouvé {len(files)} fichiers à traiter")

    # Traiter chaque fichier
    all_embeddings = []

    for file_path in tqdm(files, desc="Traitement des fichiers"):
        embeddings_data = process_single_file(
            str(file_path),
            ocr_processor,
            embedding_generator,
            logger
        )

        if embeddings_data:
            all_embeddings.extend(embeddings_data)

            # Sauvegarder le résultat localement
            output_file = Path(output_dir) / f"{file_path.stem}_embeddings.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(embeddings_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Résultats sauvegardés dans {output_file}")

    # Upload vers Supabase si demandé
    if upload_to_supabase and all_embeddings:
        logger.info(f"Upload de {len(all_embeddings)} embeddings vers Supabase...")

        try:
            results = supabase_uploader.upload_embeddings(
                table_name=table_name,
                embeddings_data=all_embeddings,
                batch_size=config["batch_size"]
            )

            logger.info(f"Upload terminé: {len(results)} entrées dans Supabase")

            # Afficher les statistiques
            stats = supabase_uploader.get_table_stats(table_name)
            logger.info(f"Statistiques de la table: {stats}")

        except Exception as e:
            logger.error(f"Erreur lors de l'upload vers Supabase: {e}")

    logger.info("Traitement terminé!")
    logger.info(f"Total d'embeddings générés: {len(all_embeddings)}")


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Traitement de documents avec OCR, embeddings et Supabase"
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

    parser.add_argument(
        "--log-file",
        help="Fichier de log optionnel"
    )

    args = parser.parse_args()

    # Setup logger
    logger = setup_logger(
        level=getattr(__import__('logging'), args.log_level),
        log_file=args.log_file
    )

    # Charger la configuration
    config = load_config()

    # Vérifier les paramètres requis
    if not config["azure_endpoint"] or not config["azure_key"]:
        logger.error("Configuration Azure manquante! Vérifiez votre fichier .env")
        return

    if not config["openai_key"]:
        logger.error("Configuration OpenAI manquante! Vérifiez votre fichier .env")
        return

    if args.upload and (not config["supabase_url"] or not config["supabase_key"]):
        logger.error("Configuration Supabase manquante! Vérifiez votre fichier .env")
        return

    # Traiter le fichier ou répertoire
    input_path = Path(args.input)

    if input_path.is_file():
        logger.info("Mode fichier unique")

        ocr_processor = AzureOCRProcessor(
            endpoint=config["azure_endpoint"],
            key=config["azure_key"]
        )

        embedding_generator = EmbeddingGenerator(
            api_key=config["openai_key"],
            model=config["embedding_model"]
        )

        embeddings_data = process_single_file(
            str(input_path),
            ocr_processor,
            embedding_generator,
            logger
        )

        # Sauvegarder
        output_file = Path(args.output) / f"{input_path.stem}_embeddings.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Résultats sauvegardés dans {output_file}")

        # Upload si demandé
        if args.upload and embeddings_data:
            supabase_uploader = SupabaseUploader(
                url=config["supabase_url"],
                key=config["supabase_key"]
            )

            results = supabase_uploader.upload_embeddings(
                table_name=args.table,
                embeddings_data=embeddings_data,
                batch_size=config["batch_size"]
            )

            logger.info(f"Upload terminé: {len(results)} entrées")

    elif input_path.is_dir():
        logger.info("Mode répertoire")

        process_directory(
            input_dir=str(input_path),
            output_dir=args.output,
            table_name=args.table,
            upload_to_supabase=args.upload,
            config=config,
            logger=logger
        )

    else:
        logger.error(f"Chemin invalide: {args.input}")


if __name__ == "__main__":
    main()
