#!/usr/bin/env python3
"""
Script d'upload de documents avec métadonnées enrichies.

Ce script permet d'uploader des documents en spécifiant des métadonnées
personnalisées via un fichier CSV ou JSON.

Formats supportés :
1. CSV avec colonnes : file_path, type_document, metadata (JSON)
2. JSON avec configuration complète
3. Dossiers organisés avec métadonnées héritées
"""

import argparse
import json
import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

from src.metadata_enrichment import create_metadata_for_document, MetadataExtractor
from src.embeddings import EmbeddingGenerator
from src.supabase_client_v2 import SupabaseUploaderV2
from src.azure_ocr import AzureOCRProcessor
from src.chunking_config import get_chunking_params
from process_v2 import extract_text_from_file

# Configuration du logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_metadata_from_csv(csv_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Charge les métadonnées depuis un fichier CSV.

    Format CSV attendu :
    file_path,type_document,commune,valeur_chf,annee,tags
    C:\Docs\eval1.pdf,evaluation_immobiliere,Aigle,14850000,2023,"immobilier,vaud"

    Returns:
        Dictionnaire {file_path: metadata}
    """
    metadata_map = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            file_path = row.pop('file_path')

            # Convertir les valeurs numériques
            metadata = {}
            for key, value in row.items():
                if not value or value.strip() == '':
                    continue

                # Essayer de convertir en nombre
                try:
                    if '.' in value:
                        metadata[key] = float(value)
                    else:
                        metadata[key] = int(value)
                except ValueError:
                    # Essayer de parser JSON (pour listes, etc.)
                    if value.startswith('[') or value.startswith('{'):
                        try:
                            metadata[key] = json.loads(value)
                        except:
                            metadata[key] = value
                    else:
                        metadata[key] = value

            metadata_map[file_path] = metadata

    logger.info(f"✅ {len(metadata_map)} fichiers avec métadonnées chargés depuis CSV")
    return metadata_map


def load_metadata_from_json(json_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Charge les métadonnées depuis un fichier JSON.

    Format JSON attendu :
    {
        "C:\\Docs\\eval1.pdf": {
            "type_document": "evaluation_immobiliere",
            "commune": "Aigle",
            "valeur_chf": 14850000,
            ...
        },
        ...
    }
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        metadata_map = json.load(f)

    logger.info(f"✅ {len(metadata_map)} fichiers avec métadonnées chargés depuis JSON")
    return metadata_map


def create_metadata_csv_template(output_path: str, file_paths: List[str]):
    """
    Crée un template CSV à remplir manuellement.

    Args:
        output_path: Chemin du fichier CSV à créer
        file_paths: Liste des fichiers à traiter
    """
    # Colonnes recommandées
    fieldnames = [
        'file_path',
        'type_document',
        'commune',
        'canton',
        'annee',
        'valeur_chf',
        'surface_m2',
        'description',
        'tags'
    ]

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for file_path in file_paths:
            # Extraction automatique basique
            auto_meta = MetadataExtractor.extract_from_filename(file_path)

            row = {
                'file_path': file_path,
                'type_document': auto_meta.get('type_document', ''),
                'commune': auto_meta.get('commune', ''),
                'canton': auto_meta.get('canton', ''),
                'annee': auto_meta.get('annee', ''),
                'valeur_chf': '',
                'surface_m2': '',
                'description': '',
                'tags': ''
            }
            writer.writerow(row)

    logger.info(f"✅ Template CSV créé : {output_path}")
    logger.info(f"📝 Remplissez les colonnes manquantes puis relancez avec --metadata-csv")


def process_with_metadata(
    file_path: str,
    metadata: Dict[str, Any],
    embedding_gen: EmbeddingGenerator,
    uploader: SupabaseUploaderV2,
    ocr_processor: Optional[AzureOCRProcessor] = None
) -> Dict[str, Any]:
    """
    Traite un fichier avec des métadonnées enrichies.
    """
    file_name = Path(file_path).name

    try:
        logger.info(f"\n{'='*70}")
        logger.info(f"📄 {file_name}")
        logger.info(f"{'='*70}")

        # 1. Extraction du texte
        logger.info(f"📥 Extraction du texte...")
        full_text, method, page_count = extract_text_from_file(file_path, ocr_processor)
        logger.info(f"✅ Texte extrait: {len(full_text)} caractères ({method})")

        # 2. Extraction automatique de métadonnées depuis le contenu
        content_metadata = MetadataExtractor.extract_from_content(full_text)
        logger.info(f"📊 Métadonnées extraites du contenu: {len(content_metadata)} champs")

        # 3. Fusionner toutes les métadonnées (priorité : manuelles > contenu > fichier)
        filename_metadata = MetadataExtractor.extract_from_filename(file_path)
        final_metadata = {**filename_metadata, **content_metadata, **metadata}

        logger.info(f"✅ Métadonnées finales: {len(final_metadata)} champs")
        logger.info(f"   Principaux champs: {list(final_metadata.keys())[:8]}")

        # 4. Découpage en chunks
        chunk_size, chunk_overlap = get_chunking_params()
        logger.info(f"🔢 Découpage en chunks (taille: {chunk_size}, overlap: {chunk_overlap})...")
        chunks = embedding_gen.chunk_text(full_text)
        logger.info(f"✅ {len(chunks)} chunks créés")

        # 5. Génération des embeddings
        logger.info(f"🧠 Génération de {len(chunks)} embeddings...")
        embeddings = embedding_gen.generate_embeddings_batch(chunks, batch_size=100)
        logger.info(f"✅ {len(embeddings)} embeddings générés")

        # 6. Préparer les données avec métadonnées enrichies
        chunks_with_embeddings = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_metadata = final_metadata.copy()
            chunk_metadata.update({
                "total_chunks": len(chunks),
                "chunk_size": len(chunk)
            })

            chunks_with_embeddings.append({
                "chunk_index": idx,
                "chunk_text": chunk,
                "embedding": embedding,
                "metadata": chunk_metadata
            })

        # 7. Upload vers Supabase
        logger.info(f"📤 Upload vers Supabase avec métadonnées enrichies...")

        result = uploader.upload_document_with_chunks(
            file_path=file_path,
            full_content=full_text,
            chunks_with_embeddings=chunks_with_embeddings,
            file_type=Path(file_path).suffix.lstrip('.'),
            page_count=page_count,
            processing_method=method,
            additional_metadata=final_metadata  # Métadonnées pour le document complet
        )

        logger.info(f"✅ Upload terminé: {result['chunks_count']} chunks avec métadonnées enrichies")

        return {
            "status": "success",
            "file_name": file_name,
            "metadata_fields": len(final_metadata),
            "chunks_count": len(chunks),
            "sample_metadata": dict(list(final_metadata.items())[:5])  # Premier 5 champs
        }

    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        return {
            "status": "error",
            "file_name": file_name,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Upload de documents avec métadonnées enrichies"
    )

    parser.add_argument(
        "-i", "--input",
        help="Dossier ou fichier à traiter"
    )

    parser.add_argument(
        "--metadata-csv",
        help="Fichier CSV contenant les métadonnées"
    )

    parser.add_argument(
        "--metadata-json",
        help="Fichier JSON contenant les métadonnées"
    )

    parser.add_argument(
        "--create-template",
        action="store_true",
        help="Créer un template CSV pour remplir les métadonnées"
    )

    parser.add_argument(
        "--template-output",
        default="metadata_template.csv",
        help="Nom du fichier template CSV (défaut: metadata_template.csv)"
    )

    parser.add_argument(
        "--extensions",
        type=str,
        default="pdf,txt,md",
        help="Extensions de fichiers à traiter (séparées par des virgules)"
    )

    args = parser.parse_args()

    # Initialiser les composants
    try:
        logger.info("🔧 Initialisation...")
        embedding_gen = EmbeddingGenerator()
        uploader = SupabaseUploaderV2()
        logger.info("✅ Composants initialisés")

        try:
            ocr_processor = AzureOCRProcessor()
            logger.info("✅ Azure OCR initialisé")
        except:
            ocr_processor = None
            logger.warning("⚠️  Azure OCR non disponible")

    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        sys.exit(1)

    # Collecter les fichiers
    if not args.input:
        logger.error("❌ Argument --input requis")
        sys.exit(1)

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
    else:
        logger.error(f"❌ Chemin invalide: {input_path}")
        sys.exit(1)

    logger.info(f"📁 {len(file_paths)} fichiers trouvés")

    # Mode 1 : Créer un template CSV
    if args.create_template:
        create_metadata_csv_template(args.template_output, file_paths)
        logger.info(f"\n📝 Prochaines étapes:")
        logger.info(f"1. Ouvrir {args.template_output} dans Excel")
        logger.info(f"2. Remplir les colonnes avec les bonnes métadonnées")
        logger.info(f"3. Sauvegarder le fichier")
        logger.info(f"4. Relancer : python upload_with_metadata.py -i ... --metadata-csv {args.template_output}")
        return

    # Mode 2 : Upload avec métadonnées
    metadata_map = {}

    if args.metadata_csv:
        metadata_map = load_metadata_from_csv(args.metadata_csv)
    elif args.metadata_json:
        metadata_map = load_metadata_from_json(args.metadata_json)
    else:
        logger.warning("⚠️  Aucun fichier de métadonnées fourni. Métadonnées automatiques uniquement.")

    # Traiter les fichiers
    results = {"success": [], "errors": []}

    for idx, file_path in enumerate(file_paths, 1):
        logger.info(f"\n[{idx}/{len(file_paths)}] Traitement en cours...")

        # Récupérer les métadonnées pour ce fichier
        file_metadata = metadata_map.get(file_path, {})

        result = process_with_metadata(
            file_path=file_path,
            metadata=file_metadata,
            embedding_gen=embedding_gen,
            uploader=uploader,
            ocr_processor=ocr_processor
        )

        if result["status"] == "success":
            results["success"].append(result)
        else:
            results["errors"].append(result)

    # Résumé
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 RÉSUMÉ")
    logger.info(f"{'='*70}")
    logger.info(f"✅ Succès: {len(results['success'])}")
    logger.info(f"❌ Erreurs: {len(results['errors'])}")

    if results['success']:
        logger.info(f"\n📊 Exemples de métadonnées utilisées:")
        for res in results['success'][:3]:
            logger.info(f"\n   {res['file_name']}:")
            logger.info(f"   - {res['metadata_fields']} champs de métadonnées")
            logger.info(f"   - Échantillon: {res['sample_metadata']}")

    if results['errors']:
        logger.info(f"\n❌ Fichiers en erreur:")
        for error in results['errors']:
            logger.info(f"   - {error['file_name']}: {error['error']}")


if __name__ == "__main__":
    main()
