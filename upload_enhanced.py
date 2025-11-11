#!/usr/bin/env python3
"""
Upload Enhanced - Script d'upload avec nouveau schéma amélioré
=================================================================
Upload des documents avec métadonnées enrichies vers Supabase
en utilisant le nouveau schéma optimisé pour recherche LLM.

Fonctionnalités:
- Extraction complète des métadonnées (100+ champs)
- Mapping vers champs dédiés de la base de données
- Chunks avec contexte avant/après
- Calcul de scores d'importance
- Extraction d'entités (entreprises, lieux, personnes)
- Full-text search vectors
- Tags automatiques

Usage:
    python upload_enhanced.py -i /chemin/vers/documents
    python upload_enhanced.py -i /chemin/vers/documents --dry-run
    python upload_enhanced.py -i /chemin/vers/documents --metadata-csv metadata.csv
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# Import des modules existants
from src.file_processor import extract_text_from_file
from src.metadata_extractor_advanced import MetadataExtractorAdvanced
from src.embeddings import generate_embedding, chunk_text
from src.supabase_client_v2 import SupabaseClient

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedDocumentUploader:
    """Uploader de documents avec métadonnées enrichies"""

    def __init__(self, supabase_client: SupabaseClient, dry_run: bool = False):
        self.client = supabase_client
        self.dry_run = dry_run
        self.extractor = MetadataExtractorAdvanced()

        # Statistiques
        self.stats = {
            'documents_processed': 0,
            'documents_uploaded': 0,
            'chunks_created': 0,
            'entities_extracted': 0,
            'errors': 0
        }

    def map_metadata_to_schema(self, metadata: Dict[str, Any], file_path: str, content: str) -> Dict[str, Any]:
        """
        Mappe les métadonnées extraites vers les champs dédiés du schéma

        Args:
            metadata: Métadonnées extraites par MetadataExtractorAdvanced
            file_path: Chemin du fichier
            content: Contenu du document

        Returns:
            Dict avec les champs mappés pour la table documents_full
        """

        # Extraction du type de document
        type_doc = metadata.get('type_document_detecte', 'inconnu')
        categorie = metadata.get('categorie_principale', 'autre')
        sous_categorie = metadata.get('categories_secondaires', [])
        sous_categorie = sous_categorie[0] if sous_categorie else None

        # Extraction de la localisation
        commune = metadata.get('commune_principale')
        canton = metadata.get('canton_principal')
        codes_postaux = metadata.get('codes_postaux', [])
        code_postal = codes_postaux[0] if codes_postaux else None

        adresses = metadata.get('adresses_mentionnees', [])
        adresse_principale = adresses[0] if adresses else None

        # Extraction des montants
        montants_chf = metadata.get('montants_chf', [])
        montant_principal = max(montants_chf) if montants_chf else None
        montant_min = min(montants_chf) if montants_chf else None
        montant_max = max(montants_chf) if montants_chf else None

        # Extraction des dates
        dates = metadata.get('dates_mentionnees', [])
        date_document = dates[0] if dates else None
        annees = metadata.get('annees_mentionnees', [])
        annee_document = max(annees) if annees else None

        # Extraction des parties
        bailleur = metadata.get('bailleur')
        locataire = metadata.get('locataire')
        entreprises = metadata.get('entreprises_mentionnees', [])
        entite_principale = entreprises[0] if entreprises else None

        # Informations immobilières
        type_bien = metadata.get('type_bien_detecte')
        surfaces = metadata.get('surfaces_m2', [])
        surface_m2 = max(surfaces) if surfaces else None
        nombre_pieces = metadata.get('nombre_pieces')

        # Génération de tags automatiques
        tags = self._generate_tags(metadata, type_doc, categorie)

        # Calcul de la confiance
        confidence = metadata.get('type_document_confiance', 0.0)
        if confidence > 0.8:
            confidence_level = 'haute'
        elif confidence > 0.5:
            confidence_level = 'moyenne'
        else:
            confidence_level = 'basse'

        # Construction du document pour insertion
        document_data = {
            # Informations de base
            'file_name': Path(file_path).name,
            'file_path': str(file_path),
            'file_type': Path(file_path).suffix.lower().lstrip('.'),
            'full_content': content,

            # Statistiques
            'file_size_bytes': metadata.get('file_size_bytes', 0),
            'page_count': metadata.get('page_count', 0),
            'word_count': metadata.get('longueur_mots', 0),
            'char_count': metadata.get('longueur_caracteres', 0),

            # Classification
            'type_document': type_doc,
            'categorie': categorie,
            'sous_categorie': sous_categorie,
            'tags': tags,

            # Localisation
            'commune': commune,
            'canton': canton,
            'pays': 'Suisse',
            'code_postal': code_postal,
            'adresse_principale': adresse_principale,

            # Informations financières
            'montant_principal': montant_principal,
            'devise': 'CHF',
            'montant_min': montant_min,
            'montant_max': montant_max,

            # Informations temporelles
            'date_document': date_document,
            'annee_document': annee_document,

            # Parties impliquées
            'entite_principale': entite_principale,
            'parties_secondaires': entreprises[1:] if len(entreprises) > 1 else None,
            'bailleur': bailleur,
            'locataire': locataire,

            # Informations immobilières
            'type_bien': type_bien,
            'surface_m2': surface_m2,
            'nombre_pieces': nombre_pieces,

            # Qualité et confiance
            'metadata_completeness_score': metadata.get('metadata_completeness_score', 0),
            'information_richness_score': metadata.get('information_richness_score', 0),
            'confidence_level': confidence_level,

            # Langue et style
            'langue': metadata.get('langue_detectee', 'fr'),
            'niveau_formalite': metadata.get('niveau_formalite'),

            # Métadonnées complètes en JSONB
            'metadata': metadata,

            # Informations de traitement
            'processing_method': 'upload_enhanced',
            'extraction_version': '2.0'
        }

        return document_data

    def _generate_tags(self, metadata: Dict[str, Any], type_doc: str, categorie: str) -> List[str]:
        """Génère des tags automatiques basés sur les métadonnées"""
        tags = []

        # Tags de base
        if type_doc and type_doc != 'inconnu':
            tags.append(type_doc)
        if categorie and categorie != 'autre':
            tags.append(categorie)

        # Tags géographiques
        if metadata.get('canton_principal'):
            tags.append(f"canton_{metadata['canton_principal']}")

        # Tags temporels
        annee = metadata.get('annee_la_plus_recente')
        if annee:
            tags.append(f"annee_{annee}")

            # Tag par décennie
            decennie = (annee // 10) * 10
            tags.append(f"annees_{decennie}s")

        # Tags de contenu
        if metadata.get('montants_chf'):
            tags.append('contient_montants')
        if metadata.get('adresses_mentionnees'):
            tags.append('contient_adresses')
        if metadata.get('entreprises_mentionnees'):
            tags.append('contient_entreprises')

        # Tags de qualité
        completeness = metadata.get('metadata_completeness_score', 0)
        if completeness > 70:
            tags.append('metadata_complete')

        richness = metadata.get('information_richness_score', 0)
        if richness > 70:
            tags.append('information_riche')

        return tags

    def create_enhanced_chunks(
        self,
        content: str,
        document_id: int,
        chunk_size: int = 1000,
        overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Crée des chunks enrichis avec contexte avant/après

        Args:
            content: Contenu du document
            document_id: ID du document parent
            chunk_size: Taille des chunks
            overlap: Chevauchement entre chunks

        Returns:
            Liste de chunks enrichis
        """

        # Chunking du texte
        basic_chunks = chunk_text(content, chunk_size=chunk_size, overlap=overlap)

        enhanced_chunks = []

        for idx, chunk in enumerate(basic_chunks):
            # Calcul des positions
            start_pos = content.find(chunk)
            end_pos = start_pos + len(chunk) if start_pos != -1 else len(chunk)

            # Extraction du contexte avant/après
            context_before = None
            context_after = None

            if start_pos > 0:
                context_start = max(0, start_pos - 200)
                context_before = content[context_start:start_pos].strip()

            if end_pos < len(content):
                context_end = min(len(content), end_pos + 200)
                context_after = content[end_pos:context_end].strip()

            # Détection du type de chunk
            chunk_type = self._detect_chunk_type(chunk)

            # Détection de contenu spécifique
            has_tables = self._contains_tables(chunk)
            has_numbers = any(char.isdigit() for char in chunk)
            has_dates = self._contains_dates(chunk)
            has_amounts = self._contains_amounts(chunk)

            # Extraction d'entités dans le chunk
            entities = self._extract_entities_from_chunk(chunk)
            locations = self._extract_locations_from_chunk(chunk)

            # Calcul du score d'importance
            importance_score = self._calculate_importance_score(
                chunk, has_tables, has_numbers, has_dates, has_amounts, entities
            )

            # Détection de section (basique)
            section_title, section_level = self._detect_section(chunk, idx)

            # Génération de l'embedding
            try:
                embedding = generate_embedding(chunk)
            except Exception as e:
                logger.error(f"Erreur génération embedding chunk {idx}: {e}")
                embedding = None

            chunk_data = {
                'document_id': document_id,
                'chunk_index': idx,
                'chunk_content': chunk,
                'chunk_size': len(chunk),
                'context_before': context_before,
                'context_after': context_after,
                'start_position': start_pos if start_pos != -1 else None,
                'end_position': end_pos if start_pos != -1 else None,
                'section_title': section_title,
                'section_level': section_level,
                'paragraph_index': idx,  # Simplification
                'chunk_type': chunk_type,
                'has_tables': has_tables,
                'has_numbers': has_numbers,
                'has_dates': has_dates,
                'has_amounts': has_amounts,
                'entities_mentioned': entities,
                'locations_mentioned': locations,
                'importance_score': importance_score,
                'embedding': embedding,
                'chunk_metadata': {
                    'chunk_length': len(chunk),
                    'word_count': len(chunk.split()),
                    'has_context_before': context_before is not None,
                    'has_context_after': context_after is not None
                }
            }

            enhanced_chunks.append(chunk_data)

        return enhanced_chunks

    def _detect_chunk_type(self, chunk: str) -> str:
        """Détecte le type de chunk (header, body, table, list, footer)"""
        lines = chunk.strip().split('\n')

        # Header: court et au début
        if len(lines) <= 2 and len(chunk) < 100:
            return 'header'

        # Table: contient beaucoup de pipes ou tabs
        if '|' in chunk or '\t' in chunk:
            pipe_count = chunk.count('|')
            if pipe_count > 5:
                return 'table'

        # List: commence par des puces ou numéros
        if any(line.strip().startswith(('-', '*', '•', '1.', '2.', '3.')) for line in lines):
            return 'list'

        # Footer: contient des infos de page/copyright
        if any(keyword in chunk.lower() for keyword in ['page', 'copyright', '©', 'tous droits']):
            return 'footer'

        return 'body'

    def _contains_tables(self, text: str) -> bool:
        """Détecte si le texte contient des tables"""
        return '|' in text and text.count('|') > 5

    def _contains_dates(self, text: str) -> bool:
        """Détecte si le texte contient des dates"""
        import re
        date_patterns = [
            r'\d{1,2}[./]\d{1,2}[./]\d{2,4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}'
        ]
        return any(re.search(pattern, text.lower()) for pattern in date_patterns)

    def _contains_amounts(self, text: str) -> bool:
        """Détecte si le texte contient des montants"""
        import re
        amount_patterns = [
            r'CHF\s*[\d\'\s]+',
            r'[\d\'\s]+\s*CHF',
            r'Fr\.\s*[\d\'\s]+',
            r'€\s*[\d\'\s]+',
            r'\$\s*[\d\'\s]+'
        ]
        return any(re.search(pattern, text) for pattern in amount_patterns)

    def _extract_entities_from_chunk(self, chunk: str) -> List[str]:
        """Extrait les entités du chunk (simplifié)"""
        entities = []

        # Recherche de noms d'entreprises (SA, Sàrl, etc.)
        import re
        company_pattern = r'\b([A-Z][a-zé]+(?:\s+[A-Z][a-zé]+)*\s+(?:SA|Sàrl|SARL|AG|GmbH))\b'
        companies = re.findall(company_pattern, chunk)
        entities.extend(companies)

        return list(set(entities))[:10]  # Max 10 entités

    def _extract_locations_from_chunk(self, chunk: str) -> List[str]:
        """Extrait les lieux du chunk (simplifié)"""
        locations = []

        # Liste des cantons suisses
        cantons = ['VD', 'GE', 'VS', 'FR', 'NE', 'JU', 'BE', 'LU', 'ZH', 'AG', 'SG', 'TI', 'GR', 'SO', 'BS', 'BL', 'SH', 'AR', 'AI', 'TG', 'UR', 'SZ', 'OW', 'NW', 'GL', 'ZG']

        for canton in cantons:
            if canton in chunk:
                locations.append(canton)

        return list(set(locations))

    def _calculate_importance_score(
        self,
        chunk: str,
        has_tables: bool,
        has_numbers: bool,
        has_dates: bool,
        has_amounts: bool,
        entities: List[str]
    ) -> float:
        """Calcule un score d'importance pour le chunk (0-1)"""

        score = 0.5  # Score de base

        # Bonus pour contenu structuré
        if has_tables:
            score += 0.1

        # Bonus pour informations factuelles
        if has_numbers:
            score += 0.05
        if has_dates:
            score += 0.1
        if has_amounts:
            score += 0.15

        # Bonus pour entités
        if entities:
            score += min(0.1, len(entities) * 0.02)

        # Pénalité si chunk trop court ou trop long
        chunk_length = len(chunk)
        if chunk_length < 100:
            score -= 0.1
        elif chunk_length > 2000:
            score -= 0.05

        # Limiter entre 0 et 1
        return max(0.0, min(1.0, score))

    def _detect_section(self, chunk: str, index: int) -> Tuple[Optional[str], Optional[int]]:
        """Détecte si le chunk est un titre de section (basique)"""

        lines = chunk.strip().split('\n')
        first_line = lines[0].strip() if lines else ""

        # Si première ligne courte et pas de point à la fin = probablement un titre
        if len(first_line) < 100 and not first_line.endswith('.'):
            # Détection du niveau basé sur la longueur/formatage
            if first_line.isupper():
                return (first_line, 1)
            elif len(first_line) < 50:
                return (first_line, 2)
            else:
                return (first_line, 3)

        return (None, None)

    def upload_document(
        self,
        file_path: str,
        manual_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Upload un document avec métadonnées enrichies

        Args:
            file_path: Chemin vers le fichier
            manual_metadata: Métadonnées manuelles optionnelles

        Returns:
            ID du document uploadé ou None si erreur
        """

        try:
            logger.info(f"Traitement: {file_path}")

            # 1. Extraction du texte
            content = extract_text_from_file(file_path)
            if not content:
                logger.warning(f"Impossible d'extraire le texte de {file_path}")
                return None

            # 2. Extraction des métadonnées
            metadata = self.extractor.extract_metadata(content, file_path)

            # 3. Fusion avec métadonnées manuelles si fournies
            if manual_metadata:
                metadata.update(manual_metadata)

            # 4. Mapping vers le schéma
            document_data = self.map_metadata_to_schema(metadata, file_path, content)

            if self.dry_run:
                logger.info(f"[DRY RUN] Document préparé: {document_data['file_name']}")
                logger.info(f"[DRY RUN] Tags: {document_data['tags']}")
                logger.info(f"[DRY RUN] Type: {document_data['type_document']}, Catégorie: {document_data['categorie']}")
                return 999999  # ID fictif pour dry-run

            # 5. Upload du document
            doc_id = self.client.upload_document(document_data)
            logger.info(f"✓ Document uploadé: ID={doc_id}, {document_data['file_name']}")

            self.stats['documents_uploaded'] += 1

            # 6. Création des chunks enrichis
            chunks = self.create_enhanced_chunks(content, doc_id)

            # 7. Upload des chunks
            chunk_count = self.client.upload_chunks_batch(chunks)
            logger.info(f"✓ {chunk_count} chunks uploadés pour document {doc_id}")

            self.stats['chunks_created'] += chunk_count

            # 8. Extraction et upload des entités (TODO: implémenter table entities)
            # entities = self._extract_all_entities(content, doc_id)
            # self.stats['entities_extracted'] += len(entities)

            return doc_id

        except Exception as e:
            logger.error(f"Erreur upload {file_path}: {e}", exc_info=True)
            self.stats['errors'] += 1
            return None
        finally:
            self.stats['documents_processed'] += 1

    def upload_directory(
        self,
        directory: str,
        metadata_csv: Optional[str] = None,
        metadata_json: Optional[str] = None
    ):
        """
        Upload tous les documents d'un répertoire

        Args:
            directory: Chemin vers le répertoire
            metadata_csv: Chemin optionnel vers CSV de métadonnées
            metadata_json: Chemin optionnel vers JSON de métadonnées
        """

        # Chargement des métadonnées manuelles si fournies
        manual_metadata_map = {}

        if metadata_csv:
            manual_metadata_map = self._load_metadata_csv(metadata_csv)
        elif metadata_json:
            manual_metadata_map = self._load_metadata_json(metadata_json)

        # Parcours des fichiers
        supported_extensions = ['.pdf', '.txt', '.md', '.doc', '.docx']
        files = []

        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if any(filename.lower().endswith(ext) for ext in supported_extensions):
                    files.append(os.path.join(root, filename))

        logger.info(f"Trouvé {len(files)} fichiers à traiter")

        # Upload de chaque fichier
        for file_path in files:
            manual_meta = manual_metadata_map.get(Path(file_path).name, {})
            self.upload_document(file_path, manual_meta)

        # Affichage des statistiques
        self._print_stats()

    def _load_metadata_csv(self, csv_path: str) -> Dict[str, Dict[str, Any]]:
        """Charge les métadonnées depuis un CSV"""
        import csv

        metadata_map = {}

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    filename = row.pop('file_name', None)
                    if filename:
                        # Conversion des types
                        for key, value in row.items():
                            if value.replace('.', '').isdigit():
                                row[key] = float(value) if '.' in value else int(value)
                        metadata_map[filename] = row
        except Exception as e:
            logger.error(f"Erreur chargement CSV: {e}")

        return metadata_map

    def _load_metadata_json(self, json_path: str) -> Dict[str, Dict[str, Any]]:
        """Charge les métadonnées depuis un JSON"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Si c'est une liste, indexer par file_name
            if isinstance(data, list):
                return {item['file_name']: item for item in data if 'file_name' in item}

            return data
        except Exception as e:
            logger.error(f"Erreur chargement JSON: {e}")
            return {}

    def _print_stats(self):
        """Affiche les statistiques d'upload"""
        logger.info("\n" + "="*60)
        logger.info("STATISTIQUES D'UPLOAD")
        logger.info("="*60)
        logger.info(f"Documents traités:  {self.stats['documents_processed']}")
        logger.info(f"Documents uploadés: {self.stats['documents_uploaded']}")
        logger.info(f"Chunks créés:       {self.stats['chunks_created']}")
        logger.info(f"Entités extraites:  {self.stats['entities_extracted']}")
        logger.info(f"Erreurs:            {self.stats['errors']}")
        logger.info("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Upload de documents avec métadonnées enrichies"
    )
    parser.add_argument(
        '-i', '--input',
        required=True,
        help="Chemin vers le fichier ou répertoire à uploader"
    )
    parser.add_argument(
        '--metadata-csv',
        help="Chemin vers CSV de métadonnées manuelles"
    )
    parser.add_argument(
        '--metadata-json',
        help="Chemin vers JSON de métadonnées manuelles"
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1000,
        help="Taille des chunks (défaut: 1000)"
    )
    parser.add_argument(
        '--overlap',
        type=int,
        default=200,
        help="Chevauchement entre chunks (défaut: 200)"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Mode test sans upload réel"
    )

    args = parser.parse_args()

    # Initialisation du client Supabase
    client = SupabaseClient()

    # Initialisation de l'uploader
    uploader = EnhancedDocumentUploader(client, dry_run=args.dry_run)

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
        logger.error(f"Chemin invalide: {input_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
