from pathlib import Path
from typing import Dict, Any, List

class MetadataExtractorAdvanced:
    """
    Extracteur minimal de métadonnées pour déblocage de pipeline.
    Remplit les clés attendues par upload_enhanced.py avec des valeurs par défaut.
    """
    def extract_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        words = content.split() if content else []
        # Valeurs minimales/défaut
        meta: Dict[str, Any] = {
            # Dimensions / stats
            "file_size_bytes": Path(file_path).stat().st_size if file_path else 0,
            "longueur_mots": len(words),
            "longueur_caracteres": len(content) if content else 0,

            # Classification
            "type_document_detecte": "inconnu",
            "categorie_principale": "autre",
            "categories_secondaires": [],

            # Localisation
            "commune_principale": None,
            "canton_principal": None,
            "codes_postaux": [],
            "adresses_mentionnees": [],

            # Montants / dates
            "montants_chf": [],
            "dates_mentionnees": [],
            "annees_mentionnees": [],

            # Parties
            "bailleur": None,
            "locataire": None,
            "entreprises_mentionnees": [],

            # Immo
            "type_bien_detecte": None,
            "surfaces_m2": [],
            "nombre_pieces": None,
            "annee_construction": None,

            # Qualité
            "metadata_completeness_score": 50,
            "information_richness_score": 50,
            "type_document_confiance": 0.5,

            # Langue / style
            "langue_detectee": "fr",
            "niveau_formalite": None,
        }
        return meta

"""
Extracteur de métadonnées ultra-complet.

Extrait un maximum de métadonnées pour faciliter la navigation et le filtrage.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json


class AdvancedMetadataExtractor:
    """Extracteur avancé de métadonnées avec règles complètes."""

    # Listes de référence pour extraction
    CANTONS_SUISSE = {
        'VD': 'Vaud', 'GE': 'Genève', 'VS': 'Valais', 'FR': 'Fribourg',
        'NE': 'Neuchâtel', 'BE': 'Berne', 'ZH': 'Zurich', 'LU': 'Lucerne',
        'TI': 'Tessin', 'GR': 'Grisons', 'SG': 'Saint-Gall', 'AG': 'Argovie',
        'TG': 'Thurgovie', 'JU': 'Jura', 'SO': 'Soleure', 'BS': 'Bâle-Ville',
        'BL': 'Bâle-Campagne', 'SH': 'Schaffhouse', 'AR': 'Appenzell Rhodes-Extérieures',
        'AI': 'Appenzell Rhodes-Intérieures', 'SZ': 'Schwytz', 'UR': 'Uri',
        'OW': 'Obwald', 'NW': 'Nidwald', 'GL': 'Glaris', 'ZG': 'Zoug'
    }

    COMMUNES_VAUD = [
        'Aigle', 'Lausanne', 'Vevey', 'Montreux', 'Yverdon-les-Bains',
        'Morges', 'Nyon', 'Renens', 'Pully', 'Prilly', 'La Tour-de-Peilz',
        'Gland', 'Ecublens', 'Crissier', 'Bussigny', 'Lutry', 'Epalinges',
        'Le Mont-sur-Lausanne', 'Chavannes-près-Renens', 'Villeneuve',
        'Clarens', 'Blonay', 'Saint-Légier-La Chiésaz', 'Corsier-sur-Vevey',
        'Bex', 'Ollon', 'Leysin', 'Villars-sur-Ollon', 'Gryon'
    ]

    TYPES_BIENS = [
        # Résidentiel
        'appartement', 'villa', 'chalet', 'maison', 'studio', 'loft',
        'attique', 'penthouse', 'duplex', 'triplex', 'maison mitoyenne',
        # Locatif
        'immeuble locatif', 'immeuble résidentiel', 'immeuble de rapport',
        'résidence', 'copropriété',
        # Commercial
        'local commercial', 'bureau', 'surface commerciale', 'boutique',
        'restaurant', 'hôtel', 'commerce',
        # Industriel
        'entrepôt', 'hangar', 'atelier', 'usine', 'local industriel',
        # Parking / Annexes
        'parking', 'place de parc', 'garage', 'box', 'cave', 'grenier',
        # Terrains
        'terrain', 'parcelle', 'terrain à bâtir', 'terrain agricole',
        # Spéciaux
        'PPE', 'locaux mixtes', 'immeuble commercial'
    ]

    TYPES_DOCUMENTS = {
        'evaluation': ['évaluation', 'expertise', 'estimation'],
        'contrat': ['contrat', 'bail', 'convention', 'acte'],
        'rapport': ['rapport', 'bilan', 'compte rendu'],
        'facture': ['facture', 'note', 'décompte'],
        'offre': ['offre', 'proposition', 'soumission'],
        'plan': ['plan', 'schéma', 'dessin'],
        'permis': ['permis', 'autorisation', 'décision'],
        'procès-verbal': ['PV', 'procès-verbal', 'assemblée'],
        'correspondance': ['lettre', 'courrier', 'courriel', 'email']
    }

    MONNAIES = ['CHF', 'EUR', 'USD', 'GBP']

    @classmethod
    def extract_all_metadata(cls, text: str, file_path: str) -> Dict[str, Any]:
        """
        Extrait TOUTES les métadonnées possibles d'un document.

        Args:
            text: Contenu du document
            file_path: Chemin du fichier

        Returns:
            Dictionnaire complet de métadonnées
        """
        metadata = {}

        # === INFORMATIONS DE BASE ===
        metadata.update(cls._extract_file_info(file_path))

        # === EXTRACTION DU CONTENU ===
        metadata.update(cls._extract_financial_data(text))
        metadata.update(cls._extract_dates(text))
        metadata.update(cls._extract_locations(text))
        metadata.update(cls._extract_dimensions(text))
        metadata.update(cls._extract_parties(text))
        metadata.update(cls._extract_references(text))
        metadata.update(cls._extract_contacts(text))
        metadata.update(cls._extract_document_structure(text))

        # === CLASSIFICATION ===
        metadata.update(cls._classify_document(text, file_path))

        # === ANALYSE LINGUISTIQUE ===
        metadata.update(cls._analyze_language(text))

        # === SCORING ET QUALITÉ ===
        metadata.update(cls._calculate_quality_scores(text, metadata))

        return metadata

    @classmethod
    def _extract_file_info(cls, file_path: str) -> Dict[str, Any]:
        """Extrait les informations du fichier."""
        path = Path(file_path)

        return {
            'file_name': path.name,
            'file_stem': path.stem,
            'file_extension': path.suffix.lstrip('.').lower(),
            'file_directory': str(path.parent),
            'file_size_bytes': path.stat().st_size if path.exists() else 0,
            'file_size_kb': round(path.stat().st_size / 1024, 2) if path.exists() else 0,
            'file_modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else None,
            'extraction_timestamp': datetime.now().isoformat()
        }

    @classmethod
    def _extract_financial_data(cls, text: str) -> Dict[str, Any]:
        """Extrait toutes les données financières."""
        metadata = {}

        # Montants par monnaie
        for currency in cls.MONNAIES:
            pattern = rf'{currency}\s*([0-9\'\s]+(?:\.[0-9]{{2}})?)'
            matches = re.findall(pattern, text, re.IGNORECASE)

            if matches:
                # Nettoyer et convertir
                amounts = []
                for match in matches:
                    cleaned = match.replace("'", "").replace(" ", "")
                    try:
                        amounts.append(float(cleaned))
                    except:
                        pass

                if amounts:
                    metadata[f'montants_{currency.lower()}'] = amounts
                    metadata[f'montant_min_{currency.lower()}'] = min(amounts)
                    metadata[f'montant_max_{currency.lower()}'] = max(amounts)
                    metadata[f'montant_total_{currency.lower()}'] = sum(amounts)
                    metadata[f'montant_moyen_{currency.lower()}'] = round(sum(amounts) / len(amounts), 2)

        # Pourcentages (rendements, taux, etc.)
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        if percentages:
            percentages_float = [float(p) for p in percentages]
            metadata['pourcentages'] = percentages_float
            metadata['pourcentage_max'] = max(percentages_float)

        # TVA
        tva_patterns = [
            r'TVA\s*:?\s*(\d+(?:\.\d+)?)\s*%',
            r'Taxe sur la valeur ajoutée.*?(\d+(?:\.\d+)?)\s*%'
        ]
        for pattern in tva_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['tva_pct'] = float(match.group(1))
                break

        return metadata

    @classmethod
    def _extract_dates(cls, text: str) -> Dict[str, Any]:
        """Extrait toutes les dates du document."""
        metadata = {}

        # Différents formats de dates
        date_patterns = [
            r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b',  # DD/MM/YYYY ou DD.MM.YYYY
            r'\b(\d{1,2})[./](\d{1,2})[./](\d{2})\b',  # DD/MM/YY
            r'\b(\d{4})-(\d{2})-(\d{2})\b',            # YYYY-MM-DD (ISO)
            r'\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b'
        ]

        all_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            all_dates.extend([' '.join(match) for match in matches])

        if all_dates:
            metadata['dates_mentionnees'] = list(set(all_dates))[:20]  # Max 20 dates
            metadata['nombre_dates'] = len(all_dates)

        # Années
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if years:
            years_int = [int(y) for y in set(years)]
            metadata['annees_mentionnees'] = sorted(years_int, reverse=True)[:10]
            metadata['annee_la_plus_recente'] = max(years_int)
            metadata['annee_la_plus_ancienne'] = min(years_int)

        # Mois/Année (ex: "juin 2023")
        month_year = re.findall(
            r'\b(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(20\d{2})\b',
            text,
            re.IGNORECASE
        )
        if month_year:
            metadata['periodes_mentionnees'] = [f"{m} {y}" for m, y in month_year[:10]]

        return metadata

    @classmethod
    def _extract_locations(cls, text: str) -> Dict[str, Any]:
        """Extrait toutes les localisations."""
        metadata = {}

        # Cantons
        cantons_trouves = []
        for abbr, nom in cls.CANTONS_SUISSE.items():
            if nom.lower() in text.lower() or f' {abbr} ' in text or f'({abbr})' in text:
                cantons_trouves.append(nom)

        if cantons_trouves:
            metadata['cantons'] = list(set(cantons_trouves))
            if len(cantons_trouves) == 1:
                metadata['canton_principal'] = cantons_trouves[0]

        # Communes Vaud
        communes_trouvees = []
        for commune in cls.COMMUNES_VAUD:
            if commune.lower() in text.lower():
                communes_trouvees.append(commune)

        if communes_trouvees:
            metadata['communes'] = list(set(communes_trouvees))
            if len(communes_trouvees) == 1:
                metadata['commune_principale'] = communes_trouvees[0]

        # Codes postaux suisses
        npa = re.findall(r'\b(1\d{3})\b', text)
        if npa:
            metadata['codes_postaux'] = list(set(npa))[:10]

        # Adresses (patterns simples)
        addresses = re.findall(
            r'(?:rue|avenue|chemin|route|place|quai)\s+(?:de\s+)?(?:la\s+|le\s+|les\s+)?[\w\-\']+(?:\s+\d+)?',
            text,
            re.IGNORECASE
        )
        if addresses:
            metadata['adresses_mentionnees'] = list(set(addresses))[:10]

        return metadata

    @classmethod
    def _extract_dimensions(cls, text: str) -> Dict[str, Any]:
        """Extrait les dimensions, surfaces, volumes."""
        metadata = {}

        # Surfaces en m²
        surfaces = re.findall(r'(\d+(?:[\'.,]\d+)?)\s*m[²2]', text, re.IGNORECASE)
        if surfaces:
            surfaces_clean = []
            for s in surfaces:
                s_clean = s.replace("'", "").replace(",", ".")
                try:
                    surfaces_clean.append(float(s_clean))
                except:
                    pass

            if surfaces_clean:
                metadata['surfaces_m2'] = surfaces_clean
                metadata['surface_min_m2'] = min(surfaces_clean)
                metadata['surface_max_m2'] = max(surfaces_clean)
                metadata['surface_totale_m2'] = sum(surfaces_clean)

        # Volumes en m³
        volumes = re.findall(r'(\d+(?:[\'.,]\d+)?)\s*m[³3]', text, re.IGNORECASE)
        if volumes:
            volumes_float = [float(v.replace("'", "").replace(",", ".")) for v in volumes if v]
            if volumes_float:
                metadata['volumes_m3'] = volumes_float
                metadata['volume_total_m3'] = sum(volumes_float)

        # Nombre de pièces
        pieces_patterns = [
            r'(\d+(?:\.\d+)?)\s*pièces?',
            r'(\d+(?:\.\d+)?)\s*p\.',
            r'(\d+)\s*chambres?'
        ]
        for pattern in pieces_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    metadata['nombre_pieces'] = float(matches[0])
                    break
                except:
                    pass

        # Étages
        etages = re.findall(r'(\d+)(?:er?|ème?)\s+étage', text, re.IGNORECASE)
        if etages:
            metadata['etages_mentionnes'] = [int(e) for e in etages]

        return metadata

    @classmethod
    def _extract_parties(cls, text: str) -> Dict[str, Any]:
        """Extrait les parties (personnes, entreprises)."""
        metadata = {}

        # Formes juridiques suisses
        formes_juridiques = ['SA', 'Sàrl', 'SARL', 'SI', 'SNC', 'SCS', 'Fondation', 'Association']
        entreprises = []

        for forme in formes_juridiques:
            pattern = rf'([\w\s\-\']+\s+{forme})'
            matches = re.findall(pattern, text)
            entreprises.extend(matches)

        if entreprises:
            metadata['entreprises_mentionnees'] = list(set(entreprises))[:10]

        # Rôles contractuels
        roles = {
            'bailleur': r'bailleur\s*:?\s*([\w\s\-\',]+)',
            'locataire': r'locataire\s*:?\s*([\w\s\-\',]+)',
            'vendeur': r'vendeur\s*:?\s*([\w\s\-\',]+)',
            'acheteur': r'acheteur\s*:?\s*([\w\s\-\',]+)',
            'mandant': r'mandant\s*:?\s*([\w\s\-\',]+)',
            'mandataire': r'mandataire\s*:?\s*([\w\s\-\',]+)'
        }

        for role, pattern in roles.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata[role] = match.group(1).strip()

        return metadata

    @classmethod
    def _extract_references(cls, text: str) -> Dict[str, Any]:
        """Extrait les numéros de référence, IDs, etc."""
        metadata = {}

        # Numéros IDE (entreprises suisses)
        ide = re.findall(r'CHE-\d{3}\.\d{3}\.\d{3}', text)
        if ide:
            metadata['numero_ide'] = ide[0]
            metadata['numeros_ide'] = list(set(ide))

        # Références de document
        ref_patterns = [
            r'(?:réf(?:érence)?|ref|n°)\s*:?\s*([\w\-/]+)',
            r'(?:dossier|affaire)\s+(?:n°|numéro)\s*:?\s*([\w\-/]+)'
        ]

        for pattern in ref_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                metadata['references'] = list(set(matches))[:5]
                break

        # Numéros de parcelle
        parcelles = re.findall(r'(?:parcelle|art\.?)\s+(?:n°|numéro)?\s*(\d+)', text, re.IGNORECASE)
        if parcelles:
            metadata['numeros_parcelle'] = list(set(parcelles))

        return metadata

    @classmethod
    def _extract_contacts(cls, text: str) -> Dict[str, Any]:
        """Extrait les informations de contact."""
        metadata = {}

        # Emails
        emails = re.findall(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', text)
        if emails:
            metadata['emails'] = list(set(emails))[:5]

        # Téléphones suisses
        phones = re.findall(r'(?:\+41|0041|0)\s*(?:\d{2})\s*\d{3}\s*\d{2}\s*\d{2}', text)
        if phones:
            metadata['telephones'] = list(set(phones))[:5]

        # Sites web
        urls = re.findall(r'https?://[\w\.-]+(?:\.ch|\.com|\.net|\.org)[\w\./]*', text, re.IGNORECASE)
        if urls:
            metadata['sites_web'] = list(set(urls))[:5]

        return metadata

    @classmethod
    def _extract_document_structure(cls, text: str) -> Dict[str, Any]:
        """Analyse la structure du document."""
        metadata = {}

        # Statistiques de base
        metadata['longueur_caracteres'] = len(text)
        metadata['longueur_mots'] = len(text.split())
        metadata['nombre_paragraphes'] = len([p for p in text.split('\n\n') if p.strip()])
        metadata['nombre_lignes'] = len(text.split('\n'))

        # Sections / Titres (détection basique)
        sections = re.findall(r'^[A-ZÀ-Ö][A-ZÀ-Ö\s]{5,50}$', text, re.MULTILINE)
        if sections:
            metadata['sections'] = sections[:10]
            metadata['nombre_sections'] = len(sections)

        # Numérotation (1., 2., etc.)
        numerotations = re.findall(r'^\s*\d+\.\s+[A-ZÀ-Ö]', text, re.MULTILINE)
        if numerotations:
            metadata['document_numerote'] = True
            metadata['nombre_items_numerotes'] = len(numerotations)

        return metadata

    @classmethod
    def _classify_document(cls, text: str, file_path: str) -> Dict[str, Any]:
        """Classifie le type de document."""
        metadata = {}
        text_lower = text.lower()
        filename_lower = Path(file_path).name.lower()

        # Type de document
        for doc_type, keywords in cls.TYPES_DOCUMENTS.items():
            for keyword in keywords:
                if keyword in filename_lower or keyword in text_lower[:2000]:
                    metadata['type_document_detecte'] = doc_type
                    metadata['type_document_confiance'] = 'élevée' if keyword in filename_lower else 'moyenne'
                    break
            if 'type_document_detecte' in metadata:
                break

        # Type de bien immobilier
        for bien in cls.TYPES_BIENS:
            if bien.lower() in text_lower[:3000]:
                metadata['type_bien_detecte'] = bien
                break

        # Catégorie générale
        categories = {
            'immobilier': ['immobilier', 'immeuble', 'appartement', 'villa', 'terrain', 'propriété'],
            'juridique': ['contrat', 'convention', 'bail', 'acte', 'procès-verbal', 'jugement'],
            'financier': ['bilan', 'compte', 'résultat', 'actif', 'passif', 'exercice'],
            'technique': ['plan', 'expertise', 'diagnostic', 'étude', 'analyse technique'],
            'administratif': ['autorisation', 'permis', 'décision', 'demande', 'certificat']
        }

        scores = {}
        for cat, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in text_lower[:3000])
            if score > 0:
                scores[cat] = score

        if scores:
            metadata['categorie_principale'] = max(scores, key=scores.get)
            metadata['categories_secondaires'] = sorted(
                [cat for cat, score in scores.items() if score > 1 and cat != metadata.get('categorie_principale')],
                key=lambda x: scores[x],
                reverse=True
            )

        return metadata

    @classmethod
    def _analyze_language(cls, text: str) -> Dict[str, Any]:
        """Analyse la langue et le style."""
        metadata = {}

        # Détection de langue
        lang_indicators = {
            'français': ['et', 'le', 'la', 'de', 'du', 'des', 'une', 'les', 'dans', 'sur'],
            'anglais': ['the', 'and', 'of', 'in', 'to', 'is', 'for', 'with', 'that', 'this'],
            'allemand': ['der', 'die', 'das', 'und', 'den', 'dem', 'des', 'ein', 'eine', 'ist']
        }

        scores = {}
        text_sample = text[:5000].lower()
        for lang, indicators in lang_indicators.items():
            score = sum(text_sample.count(f' {word} ') for word in indicators)
            scores[lang] = score

        if scores:
            metadata['langue_detectee'] = max(scores, key=scores.get)
            metadata['langue_confiance'] = 'élevée' if scores[max(scores, key=scores.get)] > 50 else 'moyenne'

        # Formalité (présence de termes juridiques/formels)
        formal_terms = [
            'soussigné', 'demeurant', 'ci-après', 'ci-dessus', 'conformément',
            'ledit', 'ladite', 'audit', 'susmentionné', 'susdit', 'attendu que'
        ]
        formal_count = sum(1 for term in formal_terms if term in text.lower())

        if formal_count > 0:
            metadata['niveau_formalite'] = 'élevé' if formal_count > 5 else 'moyen'
            metadata['termes_formels_count'] = formal_count

        return metadata

    @classmethod
    def _calculate_quality_scores(cls, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule des scores de qualité et de complétude."""
        quality = {}

        # Score de complétude des métadonnées (0-100)
        total_fields = len(metadata)
        quality['metadata_completeness_score'] = min(100, total_fields * 2)

        # Score de richesse informationnelle
        has_amounts = any(k.startswith('montant') for k in metadata.keys())
        has_dates = 'dates_mentionnees' in metadata
        has_locations = 'communes' in metadata or 'cantons' in metadata
        has_dimensions = 'surfaces_m2' in metadata
        has_parties = any(k in metadata for k in ['bailleur', 'locataire', 'vendeur', 'acheteur'])

        richness_score = sum([
            has_amounts * 20,
            has_dates * 20,
            has_locations * 20,
            has_dimensions * 20,
            has_parties * 20
        ])

        quality['information_richness_score'] = richness_score

        # Taille du document (catégorisation)
        length = metadata.get('longueur_caracteres', 0)
        if length < 1000:
            quality['document_size_category'] = 'très court'
        elif length < 5000:
            quality['document_size_category'] = 'court'
        elif length < 20000:
            quality['document_size_category'] = 'moyen'
        elif length < 50000:
            quality['document_size_category'] = 'long'
        else:
            quality['document_size_category'] = 'très long'

        # Score global de qualité (0-100)
        quality['overall_quality_score'] = round(
            (quality['metadata_completeness_score'] + richness_score) / 2,
            1
        )

        return quality
