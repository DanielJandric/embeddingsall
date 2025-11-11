#!/usr/bin/env python3
"""
Upload MAXIMAL - Extraction ultra-complète de toutes les métadonnées
Configuration optimisée pour qualité maximale, peu importe la taille/temps
"""

import os
import sys
from pathlib import Path
from upload_enhanced import EnhancedDocumentUploader
from src.supabase_client_enhanced import SupabaseClientEnhanced
from config_upload_maximal import CHUNK_CONFIG, METADATA_CONFIG, UPLOAD_CONFIG
import logging

# Configuration du logging détaillé
logging.basicConfig(
    level=logging.DEBUG,  # Mode DEBUG pour tout voir
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_maximal.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MaximalDocumentUploader(EnhancedDocumentUploader):
    """Uploader avec configuration maximale"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Statistiques détaillées
        self.detailed_stats = {
            'documents_processed': 0,
            'documents_uploaded': 0,
            'chunks_created': 0,
            'entities_extracted': 0,
            'tags_created': 0,
            'errors': 0,
            'processing_time': 0,
            'total_size_bytes': 0,
            'metadata_fields_extracted': 0
        }

    def create_enhanced_chunks(self, content, document_id, chunk_size=None, overlap=None):
        """Override avec configuration maximale"""

        # Utiliser config maximale
        chunk_size = chunk_size or CHUNK_CONFIG['chunk_size']
        overlap = overlap or CHUNK_CONFIG['overlap']

        logger.info(f"Chunking avec taille={chunk_size}, overlap={overlap}")

        # Appeler la méthode parent avec nos params
        chunks = super().create_enhanced_chunks(
            content=content,
            document_id=document_id,
            chunk_size=chunk_size,
            overlap=overlap
        )

        # Contexte étendu
        context_size = CHUNK_CONFIG['context_size']
        for chunk in chunks:
            if chunk.get('start_position'):
                # Contexte avant étendu
                start_pos = chunk['start_position']
                context_start = max(0, start_pos - context_size)
                chunk['context_before'] = content[context_start:start_pos].strip()

                # Contexte après étendu
                end_pos = chunk.get('end_position', start_pos + len(chunk['chunk_content']))
                context_end = min(len(content), end_pos + context_size)
                chunk['context_after'] = content[end_pos:context_end].strip()

        self.detailed_stats['chunks_created'] += len(chunks)

        return chunks

    def upload_document(self, file_path, manual_metadata=None):
        """Override avec extraction maximale"""

        logger.info(f"\n{'='*80}")
        logger.info(f"UPLOAD MAXIMAL: {file_path}")
        logger.info(f"{'='*80}")

        import time
        start_time = time.time()

        try:
            # 1. Extraction du texte
            from src.file_processor import extract_text_from_file
            logger.info("📄 Extraction du texte...")
            content = extract_text_from_file(file_path)

            if not content:
                logger.warning(f"❌ Impossible d'extraire le texte de {file_path}")
                return None

            logger.info(f"✅ Texte extrait: {len(content)} caractères, {len(content.split())} mots")

            # 2. Extraction MAXIMALE des métadonnées
            logger.info("🔍 Extraction MAXIMALE des métadonnées...")
            metadata = self.extractor.extract_metadata(content, file_path)

            # Compter les champs non-vides
            metadata_count = sum(1 for v in metadata.values() if v not in [None, '', [], {}, 0])
            logger.info(f"✅ {metadata_count} champs de métadonnées extraits")
            self.detailed_stats['metadata_fields_extracted'] += metadata_count

            # 3. Fusion avec métadonnées manuelles
            if manual_metadata:
                logger.info(f"📝 Ajout de {len(manual_metadata)} métadonnées manuelles")
                metadata.update(manual_metadata)

            # 4. Mapping vers le schéma
            logger.info("🗂️  Mapping vers schéma de base de données...")
            document_data = self.map_metadata_to_schema(metadata, file_path, content)

            # Log des métadonnées principales
            logger.info(f"   Type: {document_data.get('type_document', 'N/A')}")
            logger.info(f"   Catégorie: {document_data.get('categorie', 'N/A')}")
            logger.info(f"   Commune: {document_data.get('commune', 'N/A')}")
            logger.info(f"   Canton: {document_data.get('canton', 'N/A')}")
            logger.info(f"   Tags: {len(document_data.get('tags', []))} tags")
            logger.info(f"   Score complétude: {document_data.get('metadata_completeness_score', 0):.1f}%")
            logger.info(f"   Score richesse: {document_data.get('information_richness_score', 0):.1f}%")

            if self.dry_run:
                logger.info(f"[DRY RUN] Document préparé: {document_data['file_name']}")
                return 999999

            # 5. Upload du document
            logger.info("📤 Upload du document vers Supabase...")
            doc_id = self.client.upload_document(document_data)
            logger.info(f"✅ Document uploadé: ID={doc_id}")

            self.detailed_stats['documents_uploaded'] += 1
            self.detailed_stats['total_size_bytes'] += document_data.get('file_size_bytes', 0)

            # 6. Création des chunks enrichis avec config maximale
            logger.info("✂️  Création des chunks enrichis...")
            chunks = self.create_enhanced_chunks(content, doc_id)
            logger.info(f"✅ {len(chunks)} chunks créés")

            # Log des chunks importants
            important_chunks = [c for c in chunks if c.get('importance_score', 0) > 0.7]
            logger.info(f"   🌟 {len(important_chunks)} chunks avec importance > 0.7")

            chunks_with_tables = [c for c in chunks if c.get('has_tables')]
            if chunks_with_tables:
                logger.info(f"   📊 {len(chunks_with_tables)} chunks contiennent des tables")

            chunks_with_amounts = [c for c in chunks if c.get('has_amounts')]
            if chunks_with_amounts:
                logger.info(f"   💰 {len(chunks_with_amounts)} chunks contiennent des montants")

            # 7. Upload des chunks
            logger.info("📤 Upload des chunks vers Supabase...")
            chunk_count = self.client.upload_chunks_batch(chunks)
            logger.info(f"✅ {chunk_count} chunks uploadés")

            # 8. Extraction et comptage des entités
            all_entities = []
            for chunk in chunks:
                if chunk.get('entities_mentioned'):
                    all_entities.extend(chunk['entities_mentioned'])

            unique_entities = list(set(all_entities))
            if unique_entities:
                logger.info(f"🏢 {len(unique_entities)} entités uniques extraites")
                self.detailed_stats['entities_extracted'] += len(unique_entities)

            # 9. Comptage des tags
            tags_count = len(document_data.get('tags', []))
            if tags_count:
                logger.info(f"🏷️  {tags_count} tags créés")
                self.detailed_stats['tags_created'] += tags_count

            # 10. Temps de traitement
            elapsed = time.time() - start_time
            logger.info(f"⏱️  Temps de traitement: {elapsed:.2f} secondes")
            self.detailed_stats['processing_time'] += elapsed

            logger.info(f"{'='*80}")
            logger.info(f"✅ UPLOAD TERMINÉ AVEC SUCCÈS")
            logger.info(f"{'='*80}\n")

            return doc_id

        except Exception as e:
            logger.error(f"❌ ERREUR lors de l'upload de {file_path}: {e}", exc_info=True)
            self.detailed_stats['errors'] += 1
            return None

        finally:
            self.detailed_stats['documents_processed'] += 1

    def _print_stats(self):
        """Affichage des statistiques détaillées"""

        logger.info("\n" + "="*80)
        logger.info("📊 STATISTIQUES DÉTAILLÉES D'UPLOAD MAXIMAL")
        logger.info("="*80)
        logger.info(f"Documents traités:        {self.detailed_stats['documents_processed']}")
        logger.info(f"Documents uploadés:       {self.detailed_stats['documents_uploaded']}")
        logger.info(f"Chunks créés:             {self.detailed_stats['chunks_created']}")
        logger.info(f"Entités extraites:        {self.detailed_stats['entities_extracted']}")
        logger.info(f"Tags créés:               {self.detailed_stats['tags_created']}")
        logger.info(f"Champs métadonnées:       {self.detailed_stats['metadata_fields_extracted']}")
        logger.info(f"Taille totale:            {self.detailed_stats['total_size_bytes'] / 1024 / 1024:.2f} MB")
        logger.info(f"Temps total:              {self.detailed_stats['processing_time'] / 60:.2f} minutes")

        if self.detailed_stats['documents_uploaded'] > 0:
            avg_time = self.detailed_stats['processing_time'] / self.detailed_stats['documents_uploaded']
            avg_chunks = self.detailed_stats['chunks_created'] / self.detailed_stats['documents_uploaded']
            avg_metadata = self.detailed_stats['metadata_fields_extracted'] / self.detailed_stats['documents_uploaded']

            logger.info(f"\nMoyennes par document:")
            logger.info(f"  - Temps:                {avg_time:.2f} secondes")
            logger.info(f"  - Chunks:               {avg_chunks:.1f}")
            logger.info(f"  - Métadonnées:          {avg_metadata:.1f}")

        logger.info(f"\nErreurs:                  {self.detailed_stats['errors']}")
        logger.info("="*80)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload MAXIMAL avec extraction ultra-complète de métadonnées"
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help="Chemin vers le fichier ou répertoire à uploader"
    )
    parser.add_argument(
        '--metadata-csv',
        help="CSV de métadonnées manuelles (optionnel)"
    )
    parser.add_argument(
        '--metadata-json',
        help="JSON de métadonnées manuelles (optionnel)"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Mode test sans upload réel"
    )

    args = parser.parse_args()

    # Banner
    print("\n" + "="*80)
    print("🚀 UPLOAD MAXIMAL - Configuration Ultra-Complète")
    print("="*80)
    print(f"📂 Source: {args.input}")
    print(f"✂️  Chunk size: {CHUNK_CONFIG['chunk_size']} chars")
    print(f"🔄 Overlap: {CHUNK_CONFIG['overlap']} chars")
    print(f"📝 Contexte: {CHUNK_CONFIG['context_size']} chars")
    print(f"🔍 Extraction: MAXIMALE")
    print(f"⚙️  Mode: {'DRY RUN (test)' if args.dry_run else 'PRODUCTION'}")
    print("="*80 + "\n")

    # Initialisation
    client = SupabaseClientEnhanced()
    uploader = MaximalDocumentUploader(client, dry_run=args.dry_run)

    # Upload
    input_path = Path(args.input)

    if input_path.is_file():
        uploader.upload_document(str(input_path))
    elif input_path.is_dir():
        uploader.upload_directory(
            str(input_path),
            metadata_csv=args.metadata_csv,
            metadata_json=args.metadata_json
        )
    else:
        logger.error(f"❌ Chemin invalide: {input_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
