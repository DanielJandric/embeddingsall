#!/usr/bin/env python3
"""
Script d'extraction des données Supabase en local.
Extrait toutes les données sans les modifier ou les supprimer.

Tables exportées:
- documents_full : Documents complets
- document_chunks : Chunks avec embeddings

Les données sont sauvegardées dans le dossier 'supabase_exports/'
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SupabaseExporter:
    """Exporte les données de Supabase en local."""

    def __init__(self, output_dir: str = "supabase_exports"):
        """
        Initialise l'exporteur.

        Args:
            output_dir: Dossier de sortie pour les exports
        """
        # Charger les variables d'environnement
        load_dotenv()

        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL et SUPABASE_KEY doivent être définis "
                "dans le fichier .env"
            )

        self.client: Client = create_client(self.url, self.key)
        self.output_dir = Path(output_dir)

        # Créer le dossier de sortie
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"✅ Client Supabase initialisé")
        logger.info(f"📁 Dossier d'export: {self.output_dir.absolute()}")

    def export_table(
        self,
        table_name: str,
        batch_size: int = 1000,
        select_fields: str = "*"
    ) -> Dict[str, Any]:
        """
        Exporte une table complète en JSON.

        Args:
            table_name: Nom de la table
            batch_size: Taille des batches pour la pagination
            select_fields: Champs à sélectionner

        Returns:
            Dict avec les métadonnées de l'export
        """
        logger.info(f"📥 Début de l'export de la table '{table_name}'...")

        all_data = []
        offset = 0
        total_fetched = 0

        while True:
            try:
                # Récupérer un batch
                response = self.client.table(table_name)\
                    .select(select_fields)\
                    .range(offset, offset + batch_size - 1)\
                    .execute()

                if not response.data:
                    break

                batch_count = len(response.data)
                all_data.extend(response.data)
                total_fetched += batch_count

                logger.info(
                    f"  ↳ Récupéré {batch_count} entrées "
                    f"(total: {total_fetched})"
                )

                # Si moins que batch_size, c'est le dernier batch
                if batch_count < batch_size:
                    break

                offset += batch_size

            except Exception as e:
                logger.error(f"❌ Erreur lors de l'export: {e}")
                raise

        # Sauvegarder les données
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"{table_name}_{timestamp}.json"

        export_data = {
            "table": table_name,
            "export_date": datetime.now().isoformat(),
            "total_records": len(all_data),
            "data": all_data
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(
            f"✅ Export terminé: {len(all_data)} entrées → {output_file.name}"
        )

        return {
            "table": table_name,
            "records": len(all_data),
            "file": str(output_file.absolute())
        }

    def export_all(self) -> Dict[str, Any]:
        """
        Exporte toutes les tables.

        Returns:
            Dict avec les statistiques d'export
        """
        logger.info("🚀 Début de l'export complet de Supabase...")

        results = {}

        # Exporter documents_full
        results['documents_full'] = self.export_table('documents_full')

        # Exporter document_chunks
        results['document_chunks'] = self.export_table('document_chunks')

        # Récupérer les statistiques
        try:
            stats_response = self.client.rpc("get_database_stats").execute()
            if stats_response.data:
                results['stats'] = stats_response.data
        except Exception as e:
            logger.warning(f"⚠️  Impossible de récupérer les stats: {e}")
            results['stats'] = None

        # Sauvegarder un résumé de l'export
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.output_dir / f"export_summary_{timestamp}.json"

        summary = {
            "export_date": datetime.now().isoformat(),
            "supabase_url": self.url,
            "tables": results,
            "total_files": len([k for k in results.keys() if k != 'stats'])
        }

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"📊 Résumé sauvegardé: {summary_file.name}")

        return results

    def export_documents_with_chunks(self) -> Dict[str, Any]:
        """
        Exporte les documents avec leurs chunks associés (structure hiérarchique).

        Returns:
            Dict avec les métadonnées de l'export
        """
        logger.info("📥 Export des documents avec leurs chunks...")

        # Récupérer tous les documents
        docs_response = self.client.table('documents_full')\
            .select('*')\
            .execute()

        if not docs_response.data:
            logger.warning("⚠️  Aucun document trouvé")
            return {"documents": 0, "file": None}

        documents = docs_response.data
        logger.info(f"  ↳ {len(documents)} documents récupérés")

        # Pour chaque document, récupérer ses chunks
        enriched_documents = []

        for doc in documents:
            doc_id = doc['id']

            # Récupérer les chunks du document
            chunks_response = self.client.table('document_chunks')\
                .select('*')\
                .eq('document_id', doc_id)\
                .order('chunk_index')\
                .execute()

            # Ajouter les chunks au document
            doc_with_chunks = doc.copy()
            doc_with_chunks['chunks'] = chunks_response.data or []
            doc_with_chunks['chunks_count'] = len(chunks_response.data or [])

            enriched_documents.append(doc_with_chunks)

            logger.info(
                f"  ↳ Document '{doc['file_name']}': "
                f"{len(chunks_response.data or [])} chunks"
            )

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"documents_with_chunks_{timestamp}.json"

        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_documents": len(enriched_documents),
            "documents": enriched_documents
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(
            f"✅ Export hiérarchique terminé: "
            f"{len(enriched_documents)} documents → {output_file.name}"
        )

        return {
            "documents": len(enriched_documents),
            "file": str(output_file.absolute())
        }


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Exporte les données de Supabase en local (lecture seule)"
    )
    parser.add_argument(
        '-o', '--output',
        default='supabase_exports',
        help='Dossier de sortie (défaut: supabase_exports)'
    )
    parser.add_argument(
        '--hierarchical',
        action='store_true',
        help='Export hiérarchique (documents avec leurs chunks)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Export complet (tables séparées + hiérarchique)'
    )

    args = parser.parse_args()

    try:
        exporter = SupabaseExporter(output_dir=args.output)

        if args.all:
            # Export complet
            logger.info("📦 Mode: Export complet")
            results = exporter.export_all()
            hierarchical_result = exporter.export_documents_with_chunks()

            logger.info("\n" + "="*60)
            logger.info("✅ EXPORT COMPLET TERMINÉ")
            logger.info("="*60)
            logger.info(f"Documents: {results['documents_full']['records']}")
            logger.info(f"Chunks: {results['document_chunks']['records']}")
            logger.info(f"Dossier: {exporter.output_dir.absolute()}")
            logger.info("="*60)

        elif args.hierarchical:
            # Export hiérarchique uniquement
            logger.info("📦 Mode: Export hiérarchique")
            result = exporter.export_documents_with_chunks()

            logger.info("\n" + "="*60)
            logger.info("✅ EXPORT HIÉRARCHIQUE TERMINÉ")
            logger.info("="*60)
            logger.info(f"Documents: {result['documents']}")
            logger.info(f"Fichier: {result['file']}")
            logger.info("="*60)

        else:
            # Export par défaut (tables séparées)
            logger.info("📦 Mode: Export par tables")
            results = exporter.export_all()

            logger.info("\n" + "="*60)
            logger.info("✅ EXPORT PAR TABLES TERMINÉ")
            logger.info("="*60)
            logger.info(f"Documents: {results['documents_full']['records']}")
            logger.info(f"Chunks: {results['document_chunks']['records']}")
            logger.info(f"Dossier: {exporter.output_dir.absolute()}")
            logger.info("="*60)

    except Exception as e:
        logger.error(f"\n❌ ERREUR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
