#!/usr/bin/env python3
"""
Applique les métadonnées avancées à tous les documents existants dans Supabase.

Ce script :
1. Récupère tous les documents de la base
2. Extrait les métadonnées avancées (100+ champs)
3. Met à jour les documents avec les nouvelles métadonnées
4. Génère un rapport d'enrichissement
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm
import logging

load_dotenv()

from src.metadata_extractor_advanced import AdvancedMetadataExtractor
from src.supabase_client_v2 import SupabaseUploaderV2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def apply_metadata_to_documents(
    limit: int = None,
    dry_run: bool = False,
    output_report: str = None
):
    """
    Applique les métadonnées avancées à tous les documents.

    Args:
        limit: Nombre maximum de documents à traiter (None = tous)
        dry_run: Si True, n'applique pas les changements
        output_report: Chemin du fichier JSON de rapport
    """

    uploader = SupabaseUploaderV2()

    # 1. Récupérer tous les documents
    logger.info("📥 Récupération des documents depuis Supabase...")

    query = uploader.client.table("documents_full").select("id, file_path, full_content, metadata")

    if limit:
        query = query.limit(limit)

    response = query.execute()
    documents = response.data

    logger.info(f"✅ {len(documents)} documents récupérés")

    # 2. Traiter chaque document
    results = {
        "total": len(documents),
        "success": [],
        "errors": [],
        "metadata_stats": {}
    }

    logger.info(f"\n🔄 Traitement de {len(documents)} documents...")

    for doc in tqdm(documents, desc="Enrichissement"):
        doc_id = doc['id']
        file_path = doc['file_path']
        full_content = doc['full_content']
        existing_metadata = doc.get('metadata', {})

        try:
            # Extraire les métadonnées avancées
            advanced_metadata = AdvancedMetadataExtractor.extract_all_metadata(
                text=full_content,
                file_path=file_path
            )

            # Fusionner avec les métadonnées existantes (priorité aux nouvelles)
            merged_metadata = {**existing_metadata, **advanced_metadata}

            # Compter les champs ajoutés
            new_fields_count = len(advanced_metadata)

            if not dry_run:
                # Mettre à jour dans Supabase
                uploader.client.table("documents_full")\
                    .update({"metadata": merged_metadata})\
                    .eq("id", doc_id)\
                    .execute()

            results["success"].append({
                "id": doc_id,
                "file_path": file_path,
                "new_fields_count": new_fields_count,
                "sample_fields": list(advanced_metadata.keys())[:10]
            })

            # Collecter des statistiques
            for key in advanced_metadata.keys():
                results["metadata_stats"][key] = results["metadata_stats"].get(key, 0) + 1

        except Exception as e:
            logger.error(f"❌ Erreur pour {file_path}: {e}")
            results["errors"].append({
                "id": doc_id,
                "file_path": file_path,
                "error": str(e)
            })

    # 3. Rapport final
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 RAPPORT D'ENRICHISSEMENT")
    logger.info(f"{'='*70}")
    logger.info(f"✅ Succès: {len(results['success'])}")
    logger.info(f"❌ Erreurs: {len(results['errors'])}")

    if results['success']:
        avg_fields = sum(r['new_fields_count'] for r in results['success']) / len(results['success'])
        logger.info(f"📊 Moyenne de nouveaux champs par document: {avg_fields:.1f}")

    # Top 10 des métadonnées les plus fréquentes
    if results['metadata_stats']:
        logger.info(f"\n📈 Top 10 des métadonnées extraites:")
        sorted_stats = sorted(results['metadata_stats'].items(), key=lambda x: x[1], reverse=True)[:10]
        for field, count in sorted_stats:
            percentage = (count / len(documents)) * 100
            logger.info(f"   {field}: {count} documents ({percentage:.1f}%)")

    # Exemples de métadonnées
    if results['success']:
        logger.info(f"\n🔍 Exemple de métadonnées extraites (premier document):")
        example = results['success'][0]
        logger.info(f"   Fichier: {Path(example['file_path']).name}")
        logger.info(f"   Nouveaux champs: {example['new_fields_count']}")
        logger.info(f"   Échantillon: {', '.join(example['sample_fields'][:5])}...")

    if dry_run:
        logger.info(f"\n⚠️  MODE DRY-RUN : Aucun changement appliqué")
    else:
        logger.info(f"\n✅ Métadonnées appliquées avec succès")

    # Sauvegarder le rapport
    if output_report:
        with open(output_report, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"\n📄 Rapport sauvegardé: {output_report}")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Applique les métadonnées avancées aux documents existants"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Nombre maximum de documents à traiter"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (n'applique pas les changements)"
    )

    parser.add_argument(
        "--output-report",
        default="metadata_enrichment_report.json",
        help="Fichier de rapport JSON"
    )

    args = parser.parse_args()

    apply_metadata_to_documents(
        limit=args.limit,
        dry_run=args.dry_run,
        output_report=args.output_report
    )


if __name__ == "__main__":
    main()
