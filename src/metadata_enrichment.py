"""
Système de métadonnées enrichies pour les documents.

Métadonnées recommandées selon le type de document :
- Immobilier : localité, type_bien, valeur, surface, année
- Contrats : parties, date_signature, date_expiration, montant
- Rapports : auteur, date_rapport, période_couverte, type_rapport
- Financier : exercice, société, montant_transaction, devise
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import re


class MetadataExtractor:
    """Extrait et enrichit les métadonnées des documents."""

    # Patterns pour extraction automatique
    PATTERNS = {
        'montant_chf': r'CHF\s*([\d\']+(?:\.\d{2})?)',
        'montant_eur': r'EUR\s*([\d\']+(?:\.\d{2})?)',
        'date': r'\d{1,2}[./]\d{1,2}[./]\d{2,4}',
        'surface': r'(\d+(?:\.\d+)?)\s*m[²2]',
        'commune_vd': [
            'Aigle', 'Lausanne', 'Vevey', 'Montreux', 'Yverdon',
            'Morges', 'Nyon', 'Renens', 'Pully', 'Prilly'
        ]
    }

    @staticmethod
    def extract_from_filename(file_path: str) -> Dict[str, Any]:
        """
        Extrait des métadonnées à partir du nom de fichier.

        Conventions de nommage recommandées :
        - [TYPE]_[LOCALITE]_[DATE]_[DESCRIPTION].pdf
        - evaluation_aigle_2023-01_immeuble.pdf
        - contrat_lausanne_2024-03_location.pdf
        """
        file_name = Path(file_path).stem
        metadata = {
            "source_filename": Path(file_path).name,
            "source_directory": str(Path(file_path).parent),
            "extraction_date": datetime.now().isoformat()
        }

        # Extraire le type de document du nom
        types_docs = {
            'evaluation': 'évaluation immobilière',
            'contrat': 'contrat',
            'rapport': 'rapport',
            'facture': 'facture',
            'offre': 'offre',
            'estimation': 'estimation',
            'expertise': 'expertise'
        }

        for key, value in types_docs.items():
            if key in file_name.lower():
                metadata['type_document'] = value
                break

        # Extraire l'année
        year_match = re.search(r'(20\d{2})', file_name)
        if year_match:
            metadata['annee'] = int(year_match.group(1))

        # Extraire les communes
        for commune in MetadataExtractor.PATTERNS['commune_vd']:
            if commune.lower() in file_name.lower():
                metadata['commune'] = commune
                metadata['canton'] = 'Vaud'
                break

        return metadata

    @staticmethod
    def extract_from_content(text: str, file_type: str = None) -> Dict[str, Any]:
        """
        Extrait des métadonnées à partir du contenu du document.
        """
        metadata = {}

        # Extraire les montants en CHF
        montants_chf = re.findall(MetadataExtractor.PATTERNS['montant_chf'], text)
        if montants_chf:
            # Nettoyer et convertir
            montants = [float(m.replace("'", "")) for m in montants_chf]
            metadata['montants_chf'] = montants
            metadata['montant_max_chf'] = max(montants)
            metadata['montant_min_chf'] = min(montants)

        # Extraire les surfaces
        surfaces = re.findall(MetadataExtractor.PATTERNS['surface'], text)
        if surfaces:
            surfaces_float = [float(s) for s in surfaces]
            metadata['surfaces_m2'] = surfaces_float
            metadata['surface_principale_m2'] = max(surfaces_float)

        # Extraire les dates
        dates = re.findall(MetadataExtractor.PATTERNS['date'], text[:2000])  # Chercher dans les 2000 premiers caractères
        if dates:
            metadata['dates_mentionnees'] = dates[:5]  # Max 5 dates

        # Détecter la langue (simple)
        if any(word in text.lower() for word in ['et', 'le', 'la', 'de', 'du']):
            metadata['langue'] = 'français'
        elif any(word in text.lower() for word in ['the', 'and', 'of', 'in']):
            metadata['langue'] = 'anglais'
        elif any(word in text.lower() for word in ['der', 'die', 'das', 'und']):
            metadata['langue'] = 'allemand'

        return metadata

    @staticmethod
    def enrich_metadata(
        base_metadata: Dict[str, Any],
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enrichit les métadonnées de base avec des métadonnées personnalisées.

        Args:
            base_metadata: Métadonnées extraites automatiquement
            custom_metadata: Métadonnées fournies manuellement

        Returns:
            Métadonnées enrichies
        """
        enriched = base_metadata.copy()

        if custom_metadata:
            # Fusionner avec priorité aux métadonnées manuelles
            enriched.update(custom_metadata)

        # Ajouter des tags automatiques
        tags = []

        if enriched.get('type_document'):
            tags.append(enriched['type_document'])

        if enriched.get('commune'):
            tags.append(f"commune:{enriched['commune']}")

        if enriched.get('annee'):
            tags.append(f"annee:{enriched['annee']}")

        if enriched.get('montant_max_chf') and enriched['montant_max_chf'] > 1_000_000:
            tags.append('montant_élevé')

        enriched['tags'] = tags

        return enriched


# Exemples de métadonnées personnalisées par type de document

METADATA_TEMPLATES = {
    'evaluation_immobiliere': {
        'type_document': 'évaluation immobilière',
        'categorie': 'immobilier',
        'sous_categorie': 'évaluation',
        # À remplir manuellement :
        # 'commune': 'Aigle',
        # 'adresse': 'Rue de...',
        # 'type_bien': 'immeuble locatif',
        # 'valeur_venale': 14850000,
        # 'surface_totale_m2': 2500,
        # 'annee_construction': 1985,
        # 'evaluateur': 'Expert SA',
        # 'date_evaluation': '2023-06-15'
    },

    'contrat_location': {
        'type_document': 'contrat de location',
        'categorie': 'juridique',
        'sous_categorie': 'bail',
        # À remplir manuellement :
        # 'bailleur': 'Société X',
        # 'locataire': 'Personne Y',
        # 'loyer_mensuel_chf': 2500,
        # 'charges_mensuelles_chf': 300,
        # 'date_debut': '2024-01-01',
        # 'date_fin': '2026-12-31',
        # 'depot_garantie_chf': 7500
    },

    'contrat_vente': {
        'type_document': 'contrat de vente',
        'categorie': 'juridique',
        'sous_categorie': 'transaction',
        # À remplir manuellement :
        # 'vendeur': 'Vendeur SA',
        # 'acheteur': 'Acheteur SA',
        # 'prix_vente_chf': 5000000,
        # 'commune': 'Lausanne',
        # 'date_signature': '2024-03-15',
        # 'notaire': 'Notaire Y'
    },

    'rapport_financier': {
        'type_document': 'rapport financier',
        'categorie': 'finance',
        'sous_categorie': 'comptabilité',
        # À remplir manuellement :
        # 'societe': 'Entreprise X SA',
        # 'exercice': '2023',
        # 'periode_debut': '2023-01-01',
        # 'periode_fin': '2023-12-31',
        # 'auditeur': 'Cabinet Audit',
        # 'resultat_net_chf': 150000
    },

    'facture': {
        'type_document': 'facture',
        'categorie': 'comptabilité',
        'sous_categorie': 'facturation',
        # À remplir manuellement :
        # 'numero_facture': 'FAC-2024-001',
        # 'fournisseur': 'Fournisseur SA',
        # 'client': 'Client SA',
        # 'montant_ht_chf': 10000,
        # 'tva_pct': 7.7,
        # 'montant_ttc_chf': 10770,
        # 'date_emission': '2024-01-15',
        # 'date_echeance': '2024-02-15'
    }
}


def create_metadata_for_document(
    file_path: str,
    document_type: str,
    custom_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Crée un ensemble complet de métadonnées pour un document.

    Args:
        file_path: Chemin du fichier
        document_type: Type de document (clé de METADATA_TEMPLATES)
        custom_fields: Champs personnalisés spécifiques au document

    Returns:
        Métadonnées complètes

    Example:
        >>> metadata = create_metadata_for_document(
        ...     "evaluation_aigle_2023.pdf",
        ...     "evaluation_immobiliere",
        ...     {
        ...         'commune': 'Aigle',
        ...         'valeur_venale': 14850000,
        ...         'type_bien': 'immeuble locatif',
        ...         'date_evaluation': '2023-06-15'
        ...     }
        ... )
    """
    # Métadonnées du template
    template = METADATA_TEMPLATES.get(document_type, {}).copy()

    # Métadonnées extraites du nom de fichier
    filename_meta = MetadataExtractor.extract_from_filename(file_path)

    # Fusionner tout
    metadata = {**template, **filename_meta}

    if custom_fields:
        metadata.update(custom_fields)

    # Ajouter un identifiant unique
    metadata['document_id_custom'] = f"{document_type}_{Path(file_path).stem}"

    return metadata


# Exemple d'utilisation
if __name__ == "__main__":
    # Exemple 1 : Évaluation immobilière
    metadata1 = create_metadata_for_document(
        "evaluation_aigle_2023-06_immeuble_locatif.pdf",
        "evaluation_immobiliere",
        {
            'commune': 'Aigle',
            'canton': 'Vaud',
            'adresse': 'Rue du Centre 15',
            'type_bien': 'immeuble locatif',
            'valeur_venale': 14850000,
            'valeur_rendement': 13500000,
            'surface_totale_m2': 2500,
            'nombre_logements': 24,
            'annee_construction': 1985,
            'annee_renovation': 2015,
            'evaluateur': 'Expert Immobilier SA',
            'date_evaluation': '2023-06-15',
            'rendement_brut_pct': 4.5
        }
    )

    print("Exemple de métadonnées enrichies :")
    print(metadata1)

    # Exemple 2 : Contrat de vente
    metadata2 = create_metadata_for_document(
        "contrat_vente_lausanne_2024-03.pdf",
        "contrat_vente",
        {
            'vendeur': 'Immobilière Vaudoise SA',
            'acheteur': 'Fonds Pension XYZ',
            'prix_vente_chf': 5000000,
            'commune': 'Lausanne',
            'adresse': 'Avenue de la Gare 42',
            'date_signature': '2024-03-15',
            'date_transfert': '2024-06-01',
            'notaire': 'Notaire Martin & Associés',
            'conditions_suspensives': ['financement', 'autorisation_commune']
        }
    )

    print("\n" + "="*70)
    print("Deuxième exemple :")
    print(metadata2)
