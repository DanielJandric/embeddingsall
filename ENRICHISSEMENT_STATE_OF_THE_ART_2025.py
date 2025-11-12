#!/usr/bin/env python3
"""
ENRICHISSEMENT STATE OF THE ART 2025
Architecture complète pour RAG immobilier Suisse
Multi-workers, Multi-models, Multi-strategies
"""

import os
import sys
import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import asyncio
import aiohttp
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from collections import defaultdict
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import LatentDirichletAllocation
import spacy
from transformers import pipeline
import pandas as pd
import argparse
import math

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s'
)
logger = logging.getLogger("enrichment_2025")

LOG_FILE = os.getenv("ENRICH_LOG_FILE", "enrichissement_progress.log")
try:
    log_path = os.path.abspath(LOG_FILE)
    already_has_handler = any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == log_path
        for h in logger.handlers
    )
    if not already_has_handler:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] %(message)s'))
        logger.addHandler(file_handler)
except Exception as log_exc:
    logger.warning(f"Impossible d'initialiser le fichier de logs '{LOG_FILE}': {log_exc}")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv non installé ; les variables seront lues directement depuis l'environnement.")

# ================== CONFIGURATION ==================

# Helper pour parser les réponses Anthropic
def parse_claude_json(response) -> Tuple[str, Optional[Dict]]:
    texts: List[str] = []
    try:
        content = getattr(response, "content", None)
        if content:
            for block in content:
                block_text = ""
                if isinstance(block, dict):
                    block_text = block.get("text", "")
                else:
                    block_text = getattr(block, "text", "")
                if block_text:
                    texts.append(block_text)
        raw_text = "\n".join(texts).strip()
        if not raw_text:
            return "", None

        candidates: List[str] = []
        if "```" in raw_text:
            for segment in raw_text.split("```"):
                seg = segment.strip()
                if not seg:
                    continue
                if seg.lower().startswith("json"):
                    seg = seg[4:].strip()
                candidates.append(seg)
        else:
            candidates.append(raw_text)

        for candidate in candidates:
            try:
                return raw_text, json.loads(candidate)
            except Exception:
                continue

        return raw_text, None
    except Exception as parse_error:
        logger.error(f"Erreur parsing Claude: {parse_error}")
        return "", None

# API Keys (always load from environment to avoid leaking secrets)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")

if not OPENAI_API_KEY or not ANTHROPIC_API_KEY:
    logger.warning("⚠️ OPENAI_API_KEY ou ANTHROPIC_API_KEY manquant dans l'environnement.")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("⚠️ Variables Supabase manquantes dans l'environnement.")

# Workers Configuration
WORKERS_CONFIG = {
    'metadata_extraction': 10,      # Extraction parallèle des métadonnées
    'semantic_enrichment': 6,       # GPT-4/Claude enrichissement
    'knowledge_graph': 4,           # Construction du graphe
    'cross_reference': 3,           # Analyse croisée
    'quality_control': 2            # Validation finale
}

# Models Configuration - DERNIÈRES VERSIONS NOVEMBRE 2025
MODELS = {
    'gpt4': 'gpt-4.1',  # Chat GPT-4.1 exactement
    'embedding': 'text-embedding-3-large',
    'embedding_small': 'text-embedding-3-small'
}

# Distribution du travail entre modèles
MODEL_TASKS = {
    'gpt4': ['summary', 'classification', 'risk_analysis'],  # GPT-4.1 pour analyse
    'claude': ['qa_generation', 'entity_extraction', 'relationships']  # Claude pour extraction
}

# ================== STRATÉGIES D'ENRICHISSEMENT ==================

class EnrichmentStrategy(Enum):
    """Stratégies d'enrichissement disponibles"""
    METADATA_EXTRACTION = "metadata_extraction"
    SEMANTIC_ANALYSIS = "semantic_analysis"
    ENTITY_RECOGNITION = "entity_recognition"
    RELATIONSHIP_MAPPING = "relationship_mapping"
    TEMPORAL_ANALYSIS = "temporal_analysis"
    FINANCIAL_ANALYSIS = "financial_analysis"
    LEGAL_ANALYSIS = "legal_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    QUALITY_SCORING = "quality_scoring"
    CROSS_REFERENCE = "cross_reference"

@dataclass
class DocumentEnrichment:
    """Structure pour stocker l'enrichissement d'un document"""
    document_id: int
    file_name: str
    
    # Métadonnées extraites
    metadata_swiss: Dict = field(default_factory=dict)
    entities: List[Dict] = field(default_factory=list)
    dates: List[Dict] = field(default_factory=list)
    amounts: List[Dict] = field(default_factory=list)
    locations: List[Dict] = field(default_factory=list)
    
    # Analyse sémantique
    summary_short: str = ""
    summary_detailed: str = ""
    key_points: List[str] = field(default_factory=list)
    questions_answers: List[Dict] = field(default_factory=list)
    
    # Classification et scoring
    document_type: str = ""
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    importance_score: float = 0.0
    confidence_score: float = 0.0
    quality_score: float = 0.0
    
    # Relations et graphe
    related_documents: List[int] = field(default_factory=list)
    entity_relationships: List[Dict] = field(default_factory=list)
    temporal_sequence: Dict = field(default_factory=dict)
    
    # Analyse avancée
    risk_factors: List[Dict] = field(default_factory=list)
    compliance_checks: List[Dict] = field(default_factory=list)
    anomalies: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

# ================== 1. EXTRACTION MÉTADONNÉES SUISSE ==================

class SwissMetadataExtractor:
    """Extraction spécifique pour VOS immeubles - Focus Vaud, Fribourg, Valais"""
    
    # FOCUS SUR VOS 3 CANTONS UNIQUEMENT
    CANTONS = {
        'VD': 'Vaud',
        'FR': 'Fribourg', 
        'VS': 'Valais'
    }
    
    # VOS VILLES SPÉCIFIQUES
    TARGET_CITIES = {
        'chippis': {'canton': 'VS', 'code_postal': '3965'},
        'sion': {'canton': 'VS', 'code_postal': '1950'},
        'martigny': {'canton': 'VS', 'code_postal': '1920'},
        'aigle': {'canton': 'VD', 'code_postal': '1860'},
        'fribourg': {'canton': 'FR', 'code_postal': '1700'}
    }
    
    # Codes postaux de vos régions
    POSTAL_CODES = {
        '3965': 'Chippis',
        '1950': 'Sion',
        '1951': 'Sion',
        '1920': 'Martigny',
        '1860': 'Aigle',
        '1700': 'Fribourg',
        '1701': 'Fribourg'
    }
    
    def extract_all(self, text: str) -> Dict:
        """Extraction complète des métadonnées suisses"""
        metadata = {}
        
        # Canton et localisation
        metadata.update(self._extract_location(text))
        
        # Montants et finances
        metadata.update(self._extract_financial(text))
        
        # Dates et périodes
        metadata.update(self._extract_temporal(text))
        
        # Entités et personnes
        metadata.update(self._extract_entities(text))
        
        # Propriétés immobilières
        metadata.update(self._extract_property_details(text))
        
        # Informations légales
        metadata.update(self._extract_legal_info(text))
        
        return metadata
    
    def _extract_location(self, text: str) -> Dict:
        """Extraction des informations de localisation"""
        location = {}
        
        # Canton
        for code, name in self.CANTONS.items():
            if code in text or name in text:
                location['canton'] = name
                location['canton_code'] = code
                break
        
        # Code postal et ville
        postal_pattern = r'\b(1[0-9]{3}|[2-9][0-9]{3})\s+([A-Za-zÀ-ÿ\s\-]+)'
        postal_matches = re.findall(postal_pattern, text)
        if postal_matches:
            location['code_postal'] = postal_matches[0][0]
            location['commune'] = postal_matches[0][1].strip()
        
        # Adresse complète
        address_pattern = r'(?:rue|avenue|chemin|route|place|quai)\s+[^,\n]+(?:,\s*\d+)?'
        address_match = re.search(address_pattern, text, re.IGNORECASE)
        if address_match:
            location['adresse'] = address_match.group(0)
        
        # Coordonnées GPS si présentes
        gps_pattern = r'(\d+\.\d+)[,\s]+(\d+\.\d+)'
        gps_match = re.search(gps_pattern, text)
        if gps_match:
            location['latitude'] = float(gps_match.group(1))
            location['longitude'] = float(gps_match.group(2))
        
        return location
    
    def _extract_financial(self, text: str) -> Dict:
        """Extraction des montants et informations financières"""
        financial = {}
        
        # Montants CHF
        chf_pattern = r'CHF\s*([0-9\'\s]+(?:\.\d{2})?)'
        chf_amounts = re.findall(chf_pattern, text)
        if chf_amounts:
            amounts = [float(amt.replace("'", "").replace(" ", "")) for amt in chf_amounts]
            financial['montants_chf'] = amounts
            financial['montant_principal'] = max(amounts)
            financial['montant_total'] = sum(amounts)
        
        # Loyer mensuel
        loyer_pattern = r'loyer(?:\s+mensuel)?\s*:?\s*CHF?\s*([0-9\'\s]+)'
        loyer_match = re.search(loyer_pattern, text, re.IGNORECASE)
        if loyer_match:
            financial['loyer_mensuel'] = float(loyer_match.group(1).replace("'", "").replace(" ", ""))
        
        # Charges
        charges_pattern = r'charges?\s*:?\s*CHF?\s*([0-9\'\s]+)'
        charges_match = re.search(charges_pattern, text, re.IGNORECASE)
        if charges_match:
            financial['charges'] = float(charges_match.group(1).replace("'", "").replace(" ", ""))
        
        # Prix de vente
        vente_pattern = r'prix(?:\s+de\s+vente)?\s*:?\s*CHF?\s*([0-9\'\s]+)'
        vente_match = re.search(vente_pattern, text, re.IGNORECASE)
        if vente_match:
            financial['prix_vente'] = float(vente_match.group(1).replace("'", "").replace(" ", ""))
        
        return financial
    
    def _extract_temporal(self, text: str) -> Dict:
        """Extraction des dates et périodes"""
        temporal = {}
        
        # Dates formats européens
        date_patterns = [
            r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b',  # DD.MM.YYYY ou DD/MM/YYYY
            r'\b(\d{4})-(\d{2})-(\d{2})\b',            # YYYY-MM-DD
            r'\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b'
        ]
        
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates_found.extend(matches)
        
        if dates_found:
            temporal['dates'] = dates_found
            # Identifier la date principale (première ou plus récente)
            temporal['date_principale'] = dates_found[0] if dates_found else None
        
        # Durée de contrat
        duree_pattern = r'durée\s*:?\s*(\d+)\s*(an|mois|jour)'
        duree_match = re.search(duree_pattern, text, re.IGNORECASE)
        if duree_match:
            temporal['duree_valeur'] = int(duree_match.group(1))
            temporal['duree_unite'] = duree_match.group(2)
        
        # Année de construction
        construction_pattern = r'(?:construit|construction|bâti)\s+(?:en\s+)?(\d{4})'
        construction_match = re.search(construction_pattern, text, re.IGNORECASE)
        if construction_match:
            temporal['annee_construction'] = int(construction_match.group(1))
        
        return temporal
    
    def _extract_entities(self, text: str) -> Dict:
        """Extraction des entités et personnes"""
        entities = {}
        
        # Patterns pour différents rôles
        patterns = {
            'bailleur': r'bailleur\s*:?\s*([A-Z][A-Za-zÀ-ÿ\s\-]+)',
            'locataire': r'locataire\s*:?\s*([A-Z][A-Za-zÀ-ÿ\s\-]+)',
            'propriétaire': r'propriétaire\s*:?\s*([A-Z][A-Za-zÀ-ÿ\s\-]+)',
            'notaire': r'notaire\s*:?\s*(?:Me\s+)?([A-Z][A-Za-zÀ-ÿ\s\-]+)',
            'régie': r'régie\s*:?\s*([A-Z][A-Za-zÀ-ÿ\s\-]+)',
            'architecte': r'architecte\s*:?\s*([A-Z][A-Za-zÀ-ÿ\s\-]+)'
        }
        
        for role, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                entities[role] = match.group(1).strip()
        
        # Extraction des entreprises (SA, Sàrl, etc.)
        company_pattern = r'([A-Z][A-Za-zÀ-ÿ\s\-]+)\s+(?:SA|S\.A\.|Sàrl|SARL|AG)'
        companies = re.findall(company_pattern, text)
        if companies:
            entities['entreprises'] = list(set(companies))
        
        # Numéros IDE/CHE (identifiants d'entreprise suisse)
        ide_pattern = r'(?:IDE|CHE)[:\s\-]*(\d{3}\.\d{3}\.\d{3})'
        ide_matches = re.findall(ide_pattern, text)
        if ide_matches:
            entities['ide_numbers'] = ide_matches
        
        return entities
    
    def _extract_property_details(self, text: str) -> Dict:
        """Extraction des détails immobiliers"""
        property_info = {}
        
        # Surface
        surface_patterns = [
            (r'(\d+(?:\.\d+)?)\s*m[²2]', 'surface_m2'),
            (r'surface\s*:?\s*(\d+(?:\.\d+)?)', 'surface_m2'),
            (r'(\d+(?:\.\d+)?)\s*(?:mètres?\s+carrés?|m2)', 'surface_m2')
        ]
        
        for pattern, key in surface_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                property_info[key] = float(match.group(1))
                break
        
        # Nombre de pièces
        pieces_pattern = r'(\d+(?:\.\d+)?)\s*pièces?'
        pieces_match = re.search(pieces_pattern, text, re.IGNORECASE)
        if pieces_match:
            property_info['nombre_pieces'] = float(pieces_match.group(1))
        
        # Étage
        etage_pattern = r'(\d+)(?:er?|ème|e)?\s*étage'
        etage_match = re.search(etage_pattern, text, re.IGNORECASE)
        if etage_match:
            property_info['etage'] = int(etage_match.group(1))
        
        # Type de bien
        types_bien = {
            'appartement': ['appartement', 'appart', 'app'],
            'maison': ['maison', 'villa', 'chalet'],
            'bureau': ['bureau', 'bureaux', 'commercial'],
            'local': ['local', 'arcade', 'dépôt'],
            'parking': ['parking', 'garage', 'place de parc'],
            'terrain': ['terrain', 'parcelle']
        }
        
        for type_name, keywords in types_bien.items():
            if any(keyword in text.lower() for keyword in keywords):
                property_info['type_bien'] = type_name
                break
        
        # Équipements
        equipements = {
            'balcon': r'\bbalcon\b',
            'terrasse': r'\bterrasse\b',
            'jardin': r'\bjardin\b',
            'cave': r'\bcave\b',
            'parking': r'\bparking\b|\bgarage\b',
            'ascenseur': r'\bascenseur\b',
            'piscine': r'\bpiscine\b'
        }
        
        property_info['equipements'] = []
        for equip, pattern in equipements.items():
            if re.search(pattern, text, re.IGNORECASE):
                property_info['equipements'].append(equip)
        
        return property_info
    
    def _extract_legal_info(self, text: str) -> Dict:
        """Extraction des informations légales"""
        legal = {}
        
        # Numéro de parcelle
        parcelle_pattern = r'parcelle\s*(?:n[°o]?\s*)?(\d+)'
        parcelle_match = re.search(parcelle_pattern, text, re.IGNORECASE)
        if parcelle_match:
            legal['numero_parcelle'] = parcelle_match.group(1)
        
        # Référence RF (registre foncier)
        rf_pattern = r'RF\s*(\d+)'
        rf_match = re.search(rf_pattern, text)
        if rf_match:
            legal['reference_rf'] = rf_match.group(1)
        
        # Numéro de contrat
        contrat_pattern = r'contrat\s*(?:n[°o]?\s*)?([A-Z0-9\-]+)'
        contrat_match = re.search(contrat_pattern, text, re.IGNORECASE)
        if contrat_match:
            legal['numero_contrat'] = contrat_match.group(1)
        
        # Type de contrat
        if 'bail' in text.lower() or 'location' in text.lower():
            legal['type_contrat'] = 'bail'
        elif 'vente' in text.lower() or 'achat' in text.lower():
            legal['type_contrat'] = 'vente'
        elif 'hypothèque' in text.lower() or 'hypothécaire' in text.lower():
            legal['type_contrat'] = 'hypothèque'
        
        return legal

# ================== 2. ENRICHISSEMENT SÉMANTIQUE ==================

class SemanticEnricher:
    """Enrichissement sémantique avec LLMs"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialiser les clients API"""
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except:
            logger.warning("OpenAI client non disponible")
        
        try:
            import anthropic
            self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        except:
            logger.warning("Anthropic client non disponible")
    
    async def enrich_document(self, text: str, metadata: Dict) -> Dict:
        """Enrichissement complet d'un document"""
        enrichment = {}
        
        # Utiliser différents modèles pour différentes tâches
        tasks = [
            self._generate_summary(text, metadata),
            self._generate_qa_pairs(text, metadata),
            self._extract_key_points(text),
            self._classify_document(text, metadata),
            self._assess_quality(text, metadata)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                enrichment.update(result)
            else:
                logger.error(f"Erreur enrichissement: {result}")
        
        return enrichment
    
    async def _generate_summary(self, text: str, metadata: Dict) -> Dict:
        """Générer des résumés avec GPT-4.1 - Focus VALEUR AJOUTÉE"""
        prompt = f"""
        Document immobilier dans {metadata.get('canton', 'Suisse')} - {metadata.get('commune', '')}.
        
        FOCUS: Extraire la VALEUR AJOUTÉE pour un propriétaire immobilier.
        - Opportunités financières
        - Risques à mitiger
        - Actions recommandées
        - Dates critiques
        
        Texte: {text[:3000]}
        
        Fournir:
        1. Valeur clé (1 phrase - ce qui compte vraiment)
        2. Analyse détaillée (focus rentabilité/risques)
        3. Actions concrètes à prendre
        
        Format JSON:
        {{
            "value_proposition": "...",
            "detailed_analysis": "...",
            "action_items": ["...", "..."],
            "critical_dates": ["...", "..."],
            "financial_impact": "estimation en CHF si applicable"
        }}
        """
        
        try:
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model=MODELS['gpt4'],  # GPT-4.1
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Erreur génération résumé: {e}")
            return {}
    
    async def _generate_qa_pairs(self, text: str, metadata: Dict) -> Dict:
        """Générer Q&A avec Claude 3.5 Sonnet - Questions PRATIQUES"""
        
        city = metadata.get('commune', 'inconnue')
        canton = metadata.get('canton', 'VS/VD/FR')
        
        prompt = f"""
        Document immobilier à {city}, {canton}.
        
        Générer 5 Q&A PRATIQUES pour un propriétaire/gestionnaire:
        1. Question sur les obligations légales
        2. Question sur la rentabilité/finances
        3. Question sur les travaux/maintenance
        4. Question sur les locataires/baux
        5. Question sur les échéances/dates importantes
        
        Contexte: {text[:2000]}
        
        Format JSON:
        {{
            "qa_pairs": [
                {{"question": "...", "answer": "...", "category": "legal|financial|maintenance|tenant|deadline"}},
                ...
            ]
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=MODELS['gpt4'],
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1500,
            )
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError as exc:
                logger.error(f"Erreur Q&A: JSON invalide ({exc}). Réponse brute: {response.choices[0].message.content[:500]}")
        except Exception as e:
            logger.error(f"Erreur Q&A: {e}")
        return {"qa_pairs": []}
    
    async def _extract_key_points(self, text: str) -> Dict:
        """Extraire les points clés"""
        # Utilisation de TF-IDF pour extraction rapide
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            vectorizer = TfidfVectorizer(max_features=10, stop_words='french')
            tfidf = vectorizer.fit_transform([text])
            
            key_terms = vectorizer.get_feature_names_out()
            
            return {"key_terms": list(key_terms)}
        except:
            return {"key_terms": []}
    
    async def _classify_document(self, text: str, metadata: Dict) -> Dict:
        """Classifier le document"""
        categories = {
            'contrat_location': ['bail', 'location', 'loyer', 'locataire'],
            'acte_vente': ['vente', 'achat', 'propriétaire', 'notaire'],
            'document_technique': ['plan', 'architecte', 'construction', 'travaux'],
            'document_financier': ['hypothèque', 'prêt', 'garantie', 'caution'],
            'document_administratif': ['permis', 'autorisation', 'commune', 'canton'],
            'correspondance': ['lettre', 'courrier', 'demande', 'réponse'],
            'expertise': ['expertise', 'évaluation', 'estimation', 'rapport']
        }
        
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            best_category = max(scores, key=scores.get)
            confidence = scores[best_category] / len(categories[best_category])
            
            return {
                "document_type": best_category,
                "classification_confidence": confidence
            }
        
        return {"document_type": "autre", "classification_confidence": 0.0}
    
    async def _assess_quality(self, text: str, metadata: Dict) -> Dict:
        """Évaluer la qualité du document"""
        quality_score = 0.0
        factors = []
        
        # Longueur du texte
        if len(text) > 1000:
            quality_score += 0.2
            factors.append("Contenu substantiel")
        
        # Présence de métadonnées
        if metadata:
            if 'canton' in metadata:
                quality_score += 0.1
                factors.append("Localisation identifiée")
            if 'montant_principal' in metadata:
                quality_score += 0.1
                factors.append("Montants présents")
            if 'dates' in metadata:
                quality_score += 0.1
                factors.append("Dates identifiées")
        
        # Structure du document
        if re.search(r'\b(article|clause|section)\s+\d+', text, re.IGNORECASE):
            quality_score += 0.2
            factors.append("Document structuré")
        
        # Signatures
        if re.search(r'signature|signé', text, re.IGNORECASE):
            quality_score += 0.1
            factors.append("Document signé")
        
        # Références légales
        if re.search(r'\b(CO|CC|CPC|LP|OBLF)\b', text):
            quality_score += 0.2
            factors.append("Références légales")
        
        return {
            "quality_score": min(quality_score, 1.0),
            "quality_factors": factors
        }

# ================== 3. CONSTRUCTION DU GRAPHE DE CONNAISSANCES ==================

class KnowledgeGraphBuilder:
    """Construction du graphe de connaissances"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entity_index = defaultdict(list)
        
    def build_from_documents(self, documents: List[DocumentEnrichment]) -> nx.DiGraph:
        """Construire le graphe à partir des documents enrichis"""
        
        # Ajouter les nœuds documents
        for doc in documents:
            self.graph.add_node(
                f"doc_{doc.document_id}",
                type="document",
                name=doc.file_name,
                metadata=doc.metadata_swiss
            )
            
            # Ajouter les entités
            for entity in doc.entities:
                entity_id = f"entity_{entity['name']}_{entity['type']}"
                
                if not self.graph.has_node(entity_id):
                    self.graph.add_node(
                        entity_id,
                        type="entity",
                        entity_type=entity['type'],
                        name=entity['name']
                    )
                
                # Lier document et entité
                self.graph.add_edge(
                    f"doc_{doc.document_id}",
                    entity_id,
                    relation="mentions"
                )
                
                self.entity_index[entity['name']].append(doc.document_id)
            
            # Ajouter les locations
            if doc.locations:
                for loc in doc.locations:
                    loc_id = f"location_{loc.get('canton', 'unknown')}_{loc.get('commune', 'unknown')}"
                    
                    if not self.graph.has_node(loc_id):
                        self.graph.add_node(
                            loc_id,
                            type="location",
                            **loc
                        )
                    
                    self.graph.add_edge(
                        f"doc_{doc.document_id}",
                        loc_id,
                        relation="located_in"
                    )
            
            # Ajouter les relations temporelles
            if doc.dates:
                for date_info in doc.dates:
                    date_id = f"date_{date_info['date']}"
                    
                    if not self.graph.has_node(date_id):
                        self.graph.add_node(
                            date_id,
                            type="date",
                            **date_info
                        )
                    
                    self.graph.add_edge(
                        f"doc_{doc.document_id}",
                        date_id,
                        relation="dated"
                    )
        
        # Détecter les communautés
        self._detect_communities()
        
        # Calculer les centralités
        self._calculate_centralities()
        
        return self.graph
    
    def _detect_communities(self):
        """Détecter les communautés dans le graphe"""
        try:
            from networkx.algorithms import community
            
            # Convertir en graphe non dirigé pour la détection
            undirected = self.graph.to_undirected()
            
            # Détection de communautés
            communities = community.greedy_modularity_communities(undirected)
            
            # Assigner les communautés aux nœuds
            for i, comm in enumerate(communities):
                for node in comm:
                    self.graph.nodes[node]['community'] = i
                    
        except Exception as e:
            logger.error(f"Erreur détection communautés: {e}")
    
    def _calculate_centralities(self):
        """Calculer les mesures de centralité"""
        try:
            # PageRank
            pagerank = nx.pagerank(self.graph)
            for node, score in pagerank.items():
                self.graph.nodes[node]['pagerank'] = score
            
            # Centralité de degré
            degree_centrality = nx.degree_centrality(self.graph)
            for node, score in degree_centrality.items():
                self.graph.nodes[node]['degree_centrality'] = score
            
            # Centralité d'intermédiarité
            betweenness = nx.betweenness_centrality(self.graph)
            for node, score in betweenness.items():
                self.graph.nodes[node]['betweenness'] = score
                
        except Exception as e:
            logger.error(f"Erreur calcul centralités: {e}")
    
    def find_related_documents(self, document_id: int, max_distance: int = 2) -> List[int]:
        """Trouver les documents liés"""
        related = []
        doc_node = f"doc_{document_id}"
        
        if doc_node in self.graph:
            # BFS pour trouver les documents proches
            for node in nx.single_source_shortest_path_length(
                self.graph, doc_node, cutoff=max_distance
            ):
                if node.startswith("doc_") and node != doc_node:
                    related.append(int(node.replace("doc_", "")))
        
        return related
    
    def export_graph(self, format: str = "json") -> Any:
        """Exporter le graphe"""
        if format == "json":
            from networkx.readwrite import json_graph
            return json_graph.node_link_data(self.graph)
        elif format == "gexf":
            return nx.generate_gexf(self.graph)
        elif format == "graphml":
            return nx.generate_graphml(self.graph)
        else:
            return self.graph

# ================== 4. ANALYSE TEMPORELLE ==================

class TemporalAnalyzer:
    """Analyse temporelle des documents"""
    
    def analyze_timeline(self, documents: List[DocumentEnrichment]) -> Dict:
        """Créer une timeline des événements"""
        timeline = defaultdict(list)
        
        for doc in documents:
            if doc.dates:
                for date_info in doc.dates:
                    timeline[date_info['date']].append({
                        'document_id': doc.document_id,
                        'file_name': doc.file_name,
                        'event': date_info.get('event', 'Document daté'),
                        'type': doc.document_type
                    })
        
        # Trier par date
        sorted_timeline = dict(sorted(timeline.items()))
        
        # Détecter les périodes importantes
        periods = self._detect_important_periods(sorted_timeline)
        
        # Analyser les tendances
        trends = self._analyze_trends(sorted_timeline)
        
        return {
            'timeline': sorted_timeline,
            'important_periods': periods,
            'trends': trends
        }
    
    def _detect_important_periods(self, timeline: Dict) -> List[Dict]:
        """Détecter les périodes avec beaucoup d'activité"""
        periods = []
        
        # Grouper par mois/année
        monthly_activity = defaultdict(int)
        for date_str, events in timeline.items():
            # Extraire année-mois
            if len(date_str) >= 7:
                month_key = date_str[:7]
                monthly_activity[month_key] += len(events)
        
        # Identifier les pics
        if monthly_activity:
            mean_activity = sum(monthly_activity.values()) / len(monthly_activity)
            std_activity = np.std(list(monthly_activity.values()))
            
            for month, count in monthly_activity.items():
                if count > mean_activity + 2 * std_activity:
                    periods.append({
                        'period': month,
                        'activity_count': count,
                        'type': 'high_activity'
                    })
        
        return periods
    
    def _analyze_trends(self, timeline: Dict) -> Dict:
        """Analyser les tendances temporelles"""
        trends = {
            'document_frequency': {},
            'seasonal_patterns': {},
            'growth_rate': 0.0
        }
        
        # Fréquence par type de document dans le temps
        doc_types_over_time = defaultdict(lambda: defaultdict(int))
        
        for date_str, events in timeline.items():
            for event in events:
                doc_type = event.get('type', 'unknown')
                year = date_str[:4] if len(date_str) >= 4 else 'unknown'
                doc_types_over_time[doc_type][year] += 1
        
        trends['document_frequency'] = dict(doc_types_over_time)
        
        # Patterns saisonniers
        monthly_counts = defaultdict(int)
        for date_str in timeline.keys():
            if len(date_str) >= 7:
                month = int(date_str[5:7])
                monthly_counts[month] += 1
        
        if monthly_counts:
            max_month = max(monthly_counts, key=monthly_counts.get)
            min_month = min(monthly_counts, key=monthly_counts.get)
            trends['seasonal_patterns'] = {
                'peak_month': max_month,
                'low_month': min_month,
                'monthly_distribution': dict(monthly_counts)
            }
        
        return trends

# ================== 5. ANALYSE IMMOBILIÈRE VALEUR AJOUTÉE ==================

class RealEstateValueAnalyzer:
    """Analyse VALEUR AJOUTÉE pour vos immeubles VD/FR/VS"""
    
    def analyze_property_value(self, doc: DocumentEnrichment) -> Dict:
        """Analyser la valeur d'un bien immobilier"""
        
        analysis = {
            'rental_yield': self._calculate_rental_yield(doc),
            'market_position': self._analyze_market_position(doc),
            'optimization_opportunities': self._find_optimization(doc),
            'regulatory_compliance': self._check_local_regulations(doc),
            'investment_recommendation': self._generate_recommendation(doc)
        }
        
        return analysis
    
    def _calculate_rental_yield(self, doc: DocumentEnrichment) -> Dict:
        """Calculer le rendement locatif"""
        loyer_mensuel_raw = doc.metadata_swiss.get('loyer_mensuel', 0)
        prix_vente_raw = doc.metadata_swiss.get('prix_vente', 0)

        try:
            loyer_mensuel = float(loyer_mensuel_raw)
        except (TypeError, ValueError):
            loyer_mensuel = 0.0

        try:
            prix_vente = float(prix_vente_raw)
        except (TypeError, ValueError):
            prix_vente = 0.0
        
        if loyer_mensuel > 0 and prix_vente > 0:
            rendement_brut = (loyer_mensuel * 12 / prix_vente) * 100
            rendement_net = rendement_brut * 0.7  # Estimation avec charges
            
            return {
                'rendement_brut': f"{rendement_brut:.2f}%",
                'rendement_net_estime': f"{rendement_net:.2f}%",
                'evaluation': 'Excellent' if rendement_brut > 5 else 'Bon' if rendement_brut > 4 else 'À optimiser'
            }
        return {}
    
    def _analyze_market_position(self, doc: DocumentEnrichment) -> Dict:
        """Analyser la position sur le marché local"""
        city = doc.metadata_swiss.get('commune', '').lower()
        
        # Prix moyens par ville (données 2025)
        market_data = {
            'sion': {'loyer_m2': 22, 'prix_m2': 5500},
            'martigny': {'loyer_m2': 20, 'prix_m2': 5000},
            'aigle': {'loyer_m2': 24, 'prix_m2': 6000},
            'fribourg': {'loyer_m2': 25, 'prix_m2': 6500},
            'chippis': {'loyer_m2': 18, 'prix_m2': 4500}
        }
        
        if city in market_data:
            surface_raw = doc.metadata_swiss.get('surface_m2', 0)
            loyer_raw = doc.metadata_swiss.get('loyer_mensuel', 0)

            try:
                surface = float(surface_raw)
            except (TypeError, ValueError):
                surface = 0.0

            try:
                loyer = float(loyer_raw)
            except (TypeError, ValueError):
                loyer = 0.0
            
            if surface > 0 and loyer > 0:
                loyer_m2_actuel = loyer / surface
                loyer_m2_marche = market_data[city]['loyer_m2']
                
                return {
                    'loyer_actuel_m2': f"{loyer_m2_actuel:.2f} CHF",
                    'loyer_marche_m2': f"{loyer_m2_marche} CHF",
                    'potentiel': f"+{(loyer_m2_marche - loyer_m2_actuel) * surface:.0f} CHF/mois" if loyer_m2_marche > loyer_m2_actuel else "Optimal",
                    'position': 'Sous-évalué' if loyer_m2_actuel < loyer_m2_marche * 0.9 else 'Marché' if loyer_m2_actuel < loyer_m2_marche * 1.1 else 'Sur-évalué'
                }
        return {}
    
    def _find_optimization(self, doc: DocumentEnrichment) -> List[str]:
        """Trouver les opportunités d'optimisation"""
        opportunities = []
        
        # Optimisation des loyers
        if doc.metadata_swiss.get('loyer_mensuel'):
            opportunities.append("Révision annuelle du loyer selon l'indice suisse des prix")
        
        # Optimisation énergétique
        if doc.metadata_swiss.get('annee_construction', 2000) < 2010:
            opportunities.append("Audit énergétique pour subventions cantonales (Programme Bâtiments)")
        
        # Optimisation fiscale
        if doc.metadata_swiss.get('canton') == 'Vaud':
            opportunities.append("Déduction des travaux d'entretien jusqu'à 20% de la valeur locative")
        elif doc.metadata_swiss.get('canton') == 'Fribourg':
            opportunities.append("Avantages fiscaux pour rénovation énergétique (jusqu'à 50% déductible)")
        elif doc.metadata_swiss.get('canton') == 'Valais':
            opportunities.append("Subventions cantonales pour panneaux solaires (jusqu'à 30%)")
        
        return opportunities
    
    def _check_local_regulations(self, doc: DocumentEnrichment) -> Dict:
        """Vérifier la conformité aux règlements locaux"""
        canton = doc.metadata_swiss.get('canton')
        
        regulations = {
            'Vaud': {
                'loi': 'LDTR (Loi sur la démolition, transformation et rénovation)',
                'points_clés': ['Autorisation pour travaux > 30% valeur ECA', 'Protection des locataires', 'Contrôle des loyers après travaux']
            },
            'Fribourg': {
                'loi': 'LATeC (Loi sur l amenagement du territoire)',
                'points_clés': ['Densification encouragée', 'Normes Minergie subventionnées', 'Protection patrimoine en vieille ville']
            },
            'Valais': {
                'loi': 'LC (Loi sur les constructions)',
                'points_clés': ['Lex Weber applicable', 'Restrictions résidences secondaires', 'Zones à bâtir limitées']
            }
        }
        
        return regulations.get(canton, {})
    
    def _generate_recommendation(self, doc: DocumentEnrichment) -> str:
        """Générer une recommandation d'investissement"""
        score = 0
        
        # Critères d'évaluation
        if doc.metadata_swiss.get('canton') in ['VD', 'FR', 'VS']:
            score += 2
        
        if doc.metadata_swiss.get('commune', '').lower() in ['sion', 'martigny', 'aigle', 'fribourg', 'chippis']:
            score += 3
        
        rendement = self._calculate_rental_yield(doc)
        if rendement and float(rendement.get('rendement_brut', '0').replace('%', '')) > 4.5:
            score += 3
        
        if doc.quality_score > 0.7:
            score += 2
        
        # Recommandation basée sur le score
        if score >= 8:
            return "FORTE OPPORTUNITÉ - Bien stratégique à conserver/développer"
        elif score >= 5:
            return "OPPORTUNITÉ - Potentiel d'optimisation intéressant"
        elif score >= 3:
            return "NEUTRE - Analyser options d'amélioration"
        else:
            return "RÉVISION - Envisager repositionnement ou cession"

# Remplacer l'ancien RiskAnalyzer
class RiskAnalyzer(RealEstateValueAnalyzer):
    """Analyse des risques ET de la valeur ajoutée"""
    
    def analyze_risks(self, doc: DocumentEnrichment) -> List[Dict]:
        """Analyser les risques d'un document"""
        risks = []
        
        # Analyse valeur ajoutée en premier
        value_analysis = self.analyze_property_value(doc)
        
        # Convertir en risques/opportunités
        if value_analysis.get('rental_yield', {}).get('evaluation') == 'À optimiser':
            risks.append({
                'type': 'opportunity',
                'level': 'high',
                'description': 'Potentiel d\'augmentation du rendement locatif',
                'action': 'Réviser les loyers au marché'
            })
        
        # Risques spécifiques VD/FR/VS
        risks.extend(self._analyze_cantonal_risks(doc))
        
        return risks
    
    def _analyze_cantonal_risks(self, doc: DocumentEnrichment) -> List[Dict]:
        """Risques spécifiques par canton"""
        risks = []
        canton = doc.metadata_swiss.get('canton')
        
        if canton == 'VD':
            risks.append({
                'type': 'regulatory',
                'level': 'medium',
                'description': 'LDTR - Vérifier conformité pour travaux',
                'action': 'Consulter avocat spécialisé avant travaux importants'
            })
        elif canton == 'VS':
            risks.append({
                'type': 'regulatory',
                'level': 'high',
                'description': 'Lex Weber - Restrictions résidences secondaires',
                'action': 'Vérifier statut résidence principale/secondaire'
            })
        elif canton == 'FR':
            risks.append({
                'type': 'opportunity',
                'level': 'medium',
                'description': 'Subventions énergétiques disponibles',
                'action': 'Demander audit énergétique CECB+'
            })
        
        return risks
    
    def _analyze_financial_risks(self, doc: DocumentEnrichment) -> List[Dict]:
        """Analyser les risques financiers"""
        risks = []
        
        # Montants anormalement élevés
        if doc.metadata_swiss.get('montant_principal', 0) > 1000000:
            risks.append({
                'type': 'financial',
                'level': 'high',
                'description': 'Montant très élevé détecté',
                'value': doc.metadata_swiss['montant_principal']
            })
        
        # Incohérences de montants
        if doc.amounts:
            amounts = [a['value'] for a in doc.amounts]
            if len(set(amounts)) > 5:
                risks.append({
                    'type': 'financial',
                    'level': 'medium',
                    'description': 'Multiples montants différents',
                    'value': len(set(amounts))
                })
        
        return risks
    
    def _analyze_legal_risks(self, doc: DocumentEnrichment) -> List[Dict]:
        """Analyser les risques légaux"""
        risks = []
        
        # Documents expirés
        if doc.dates:
            current_date = datetime.now()
            for date_info in doc.dates:
                if date_info.get('type') == 'expiration':
                    exp_date = datetime.strptime(date_info['date'], '%Y-%m-%d')
                    if exp_date < current_date:
                        risks.append({
                            'type': 'legal',
                            'level': 'high',
                            'description': 'Document expiré',
                            'date': date_info['date']
                        })
        
        # Signatures manquantes
        if doc.document_type in ['contrat_location', 'acte_vente']:
            if 'signé' not in doc.metadata_swiss.get('status', ''):
                risks.append({
                    'type': 'legal',
                    'level': 'high',
                    'description': 'Signature potentiellement manquante'
                })
        
        return risks
    
    def _analyze_compliance_risks(self, doc: DocumentEnrichment) -> List[Dict]:
        """Analyser les risques de conformité"""
        risks = []
        
        # RGPD - données personnelles
        if doc.entities:
            person_count = len([e for e in doc.entities if e['type'] == 'person'])
            if person_count > 10:
                risks.append({
                    'type': 'compliance',
                    'level': 'medium',
                    'description': 'Nombreuses données personnelles',
                    'count': person_count
                })
        
        # Conformité fiscale
        if doc.metadata_swiss.get('montant_principal', 0) > 100000:
            if 'tva' not in str(doc.metadata_swiss):
                risks.append({
                    'type': 'compliance',
                    'level': 'medium',
                    'description': 'TVA non mentionnée pour montant important'
                })
        
        return risks
    
    def _detect_anomalies(self, doc: DocumentEnrichment) -> List[Dict]:
        """Détecter les anomalies"""
        anomalies = []
        
        # Dates incohérentes
        if doc.dates:
            dates = [d['date'] for d in doc.dates]
            if len(dates) > 2:
                # Vérifier l'ordre chronologique
                sorted_dates = sorted(dates)
                if dates != sorted_dates:
                    anomalies.append({
                        'type': 'anomaly',
                        'level': 'low',
                        'description': 'Dates non chronologiques'
                    })
        
        # Doublons potentiels
        if doc.related_documents and len(doc.related_documents) > 5:
            anomalies.append({
                'type': 'anomaly',
                'level': 'medium',
                'description': 'Nombreux documents similaires détectés',
                'count': len(doc.related_documents)
            })
        
        return anomalies

# ================== 6. GÉNÉRATEUR DE SUBSTANCE ACTIONNABLE ==================

class SubstanceGenerator:
    """Génère de la VRAIE SUBSTANCE - pas du blabla"""
    
    async def generate_actionable_insights(self, doc: DocumentEnrichment, text: str) -> Dict:
        """Générer des insights CONCRETS et ACTIONNABLES"""
        
        # Utiliser Claude 3.5 Sonnet pour extraction profonde
        prompt = f"""
        Analyse ce document immobilier de {doc.metadata_swiss.get('commune', 'Suisse')}, {doc.metadata_swiss.get('canton', 'VD/FR/VS')}.
        
        GÉNÈRE DE LA SUBSTANCE CONCRÈTE:
        
        1. ARGENT À RÉCUPÉRER IMMÉDIATEMENT:
        - Loyers sous-évalués (montant exact)
        - Charges récupérables non facturées
        - Subventions disponibles non réclamées
        - Optimisations fiscales manquées
        
        2. RISQUES FINANCIERS CACHÉS:
        - Travaux obligatoires à venir (montant)
        - Contentieux potentiels
        - Non-conformités coûteuses
        - Échéances critiques ratées
        
        3. OPPORTUNITÉS DE VALORISATION:
        - Potentiel de densification (m² constructibles)
        - Changement d'affectation possible
        - Division en lots rentable
        - Amélioration énergétique subventionnée
        
        4. ACTIONS IMMÉDIATES (avec deadline):
        - Quoi faire cette semaine
        - Qui contacter
        - Documents à préparer
        - Décisions urgentes
        
        5. CHIFFRAGE PRÉCIS:
        - ROI de chaque action
        - Coûts vs bénéfices
        - Timeline de récupération
        
        Contexte: {text[:4000]}
        
        SOIS ULTRA PRÉCIS. Pas de généralités. Des CHIFFRES, des DATES, des NOMS.
        
        Format JSON avec exemples concrets.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=MODELS['gpt4'],
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=3000,
            )
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError as exc:
                logger.error(
                    f"Erreur génération substance: JSON invalide ({exc}). Réponse brute: {response.choices[0].message.content[:500]}"
                )
                return self._generate_fallback_insights(doc)
        except Exception as e:
            logger.error(f"Erreur génération substance: {e}")
            return self._generate_fallback_insights(doc)
    
    def _generate_fallback_insights(self, doc: DocumentEnrichment) -> Dict:
        """Insights de base si Claude échoue"""
        insights = {
            'argent_recuperable': [],
            'risques_caches': [],
            'opportunites': [],
            'actions_immediates': [],
            'chiffrage': {}
        }
        
        # Calculs basiques mais concrets
        if doc.metadata_swiss.get('loyer_mensuel'):
            loyer = doc.metadata_swiss['loyer_mensuel']
            
            # Potentiel d'augmentation standard
            insights['argent_recuperable'].append({
                'type': 'Augmentation loyer',
                'montant': f"{loyer * 0.05:.0f} CHF/mois",
                'action': 'Notification augmentation selon art. 269d CO',
                'deadline': '3 mois avant échéance bail'
            })
        
        if doc.metadata_swiss.get('surface_m2'):
            surface = doc.metadata_swiss['surface_m2']
            
            # Potentiel solaire
            insights['opportunites'].append({
                'type': 'Installation photovoltaïque',
                'potentiel': f"{surface * 0.15 * 200:.0f} kWh/an",
                'subvention': f"{surface * 0.15 * 400:.0f} CHF (Pronovo)",
                'roi': '7-9 ans'
            })
        
        return insights

class ActionPlanGenerator:
    """Génère un plan d'action CONCRET sur 12 mois"""
    
    def generate_12_month_plan(self, enrichments: List[DocumentEnrichment]) -> Dict:
        """Plan d'action sur 12 mois pour maximiser la valeur"""
        
        plan = {
            'immediate': [],  # 0-1 mois
            'court_terme': [],  # 1-3 mois
            'moyen_terme': [],  # 3-6 mois
            'long_terme': []  # 6-12 mois
        }
        
        # Analyser tous les documents pour identifier les priorités
        for doc in enrichments:
            # Actions immédiates
            if doc.risk_factors:
                for risk in doc.risk_factors:
                    if risk['level'] == 'high':
                        plan['immediate'].append({
                            'action': risk['action'],
                            'document': doc.file_name,
                            'impact_financier': risk.get('value', 'À évaluer'),
                            'responsable': 'Gérant',
                            'deadline': 'Sous 7 jours'
                        })
            
            # Optimisations court terme
            if doc.metadata_swiss.get('loyer_mensuel'):
                plan['court_terme'].append({
                    'action': f"Réviser loyer {doc.metadata_swiss.get('commune', '')}",
                    'potentiel': f"+{doc.metadata_swiss['loyer_mensuel'] * 0.05:.0f} CHF/mois",
                    'document': doc.file_name,
                    'process': 'Notification formelle locataire'
                })
            
            # Projets moyen terme
            if doc.metadata_swiss.get('annee_construction', 2000) < 2010:
                plan['moyen_terme'].append({
                    'action': 'Audit énergétique CECB+',
                    'cout': '3000-5000 CHF',
                    'subvention': '50% canton',
                    'economie': '20-30% charges chauffage',
                    'document': doc.file_name
                })
        
        return plan

# ================== 7. PIPELINE D'ENRICHISSEMENT AMÉLIORÉ ==================

class EnrichmentPipeline:
    """Pipeline complet avec génération de substance"""
    
    def __init__(self):
        self.metadata_extractor = SwissMetadataExtractor()
        self.semantic_enricher = SemanticEnricher()
        self.graph_builder = KnowledgeGraphBuilder()
        self.temporal_analyzer = TemporalAnalyzer()
        self.risk_analyzer = RiskAnalyzer()
        self.substance_generator = SubstanceGenerator()
        self.action_plan_generator = ActionPlanGenerator()
        
        # Statistiques
        self.stats = {
            'total_processed': 0,
            'success': 0,
            'errors': 0,
            'processing_time': 0
        }
    
    async def process_document(self, doc_id: int, text: str, file_name: str) -> DocumentEnrichment:
        """Traiter un document complet"""
        start_time = datetime.now()
        
        try:
            # Créer l'objet enrichissement
            enrichment = DocumentEnrichment(
                document_id=doc_id,
                file_name=file_name
            )
            
            # Phase 1: Extraction métadonnées
            logger.info(f"[{doc_id}] Extraction métadonnées...")
            metadata = self.metadata_extractor.extract_all(text)
            enrichment.metadata_swiss = metadata
            
            # Phase 2: Enrichissement sémantique
            logger.info(f"[{doc_id}] Enrichissement sémantique...")
            semantic = await self.semantic_enricher.enrich_document(text, metadata)
            
            enrichment.summary_short = semantic.get('summary_short', '')
            enrichment.summary_detailed = semantic.get('summary_detailed', '')
            enrichment.key_points = semantic.get('key_points', [])
            enrichment.questions_answers = semantic.get('qa_pairs', [])
            enrichment.document_type = semantic.get('document_type', '')
            enrichment.quality_score = semantic.get('quality_score', 0.0)
            
            # Phase 3: Analyse des risques ET valeur ajoutée
            logger.info(f"[{doc_id}] Analyse des risques et valeur...")
            risks = self.risk_analyzer.analyze_risks(enrichment)
            enrichment.risk_factors = risks
            
            # Phase 4: Génération de SUBSTANCE
            logger.info(f"[{doc_id}] Génération insights actionnables...")
            substance = await self.substance_generator.generate_actionable_insights(enrichment, text)
            enrichment.recommendations = substance.get('actions_immediates', [])
            
            # Calculer les scores
            enrichment.importance_score = self._calculate_importance(enrichment)
            enrichment.confidence_score = self._calculate_confidence(enrichment)
            
            # Stats
            self.stats['success'] += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats['processing_time'] += processing_time
            
            logger.info(f"[{doc_id}] Enrichissement terminé en {processing_time:.2f}s")
            
            return enrichment
            
        except Exception as e:
            logger.error(f"[{doc_id}] Erreur enrichissement: {e}")
            self.stats['errors'] += 1
            raise
        finally:
            self.stats['total_processed'] += 1
    
    def _calculate_importance(self, enrichment: DocumentEnrichment) -> float:
        """Calculer le score d'importance"""
        score = 0.0
        
        # Basé sur le type de document
        important_types = ['acte_vente', 'contrat_location', 'hypothèque']
        if enrichment.document_type in important_types:
            score += 0.3
        
        # Basé sur les montants
        if enrichment.metadata_swiss.get('montant_principal', 0) > 100000:
            score += 0.2
        
        # Basé sur les risques
        high_risks = [r for r in enrichment.risk_factors if r['level'] == 'high']
        if high_risks:
            score += 0.2
        
        # Basé sur les relations
        if len(enrichment.related_documents) > 3:
            score += 0.1
        
        # Basé sur la qualité
        score += enrichment.quality_score * 0.2
        
        return min(score, 1.0)
    
    def _calculate_confidence(self, enrichment: DocumentEnrichment) -> float:
        """Calculer le score de confiance"""
        confidence = 0.0
        factors = 0
        
        # Confiance dans les métadonnées
        if enrichment.metadata_swiss:
            confidence += 0.8
            factors += 1
        
        # Confiance dans la classification
        if enrichment.document_type and enrichment.document_type != 'autre':
            confidence += 0.9
            factors += 1
        
        # Confiance dans les Q&A
        if enrichment.questions_answers:
            avg_qa_confidence = sum(
                qa.get('confidence', 0) for qa in enrichment.questions_answers
            ) / len(enrichment.questions_answers)
            confidence += avg_qa_confidence
            factors += 1
        
        return confidence / factors if factors > 0 else 0.0
    
    async def process_batch(self, documents: List[Tuple[int, str, str]], 
                           max_workers: int = 6) -> List[DocumentEnrichment]:
        """Traiter un batch de documents"""
        logger.info(f"Traitement batch de {len(documents)} documents avec {max_workers} workers")
        
        results = []
        
        # Créer les tâches
        tasks = []
        for doc_id, text, file_name in documents:
            task = self.process_document(doc_id, text, file_name)
            tasks.append(task)
        
        # Exécuter en parallèle avec limitation
        for i in range(0, len(tasks), max_workers):
            batch_tasks = tasks[i:i+max_workers]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, DocumentEnrichment):
                    results.append(result)
                else:
                    logger.error(f"Erreur batch: {result}")
        
        # Construire le graphe de connaissances
        if results:
            logger.info("Construction du graphe de connaissances...")
            self.graph_builder.build_from_documents(results)
            
            # Ajouter les relations au enrichissement
            for enrichment in results:
                related = self.graph_builder.find_related_documents(
                    enrichment.document_id
                )
                enrichment.related_documents = related
        
        # Analyse temporelle globale
        if results:
            logger.info("Analyse temporelle...")
            timeline = self.temporal_analyzer.analyze_timeline(results)
            # Stocker pour référence future
            self.timeline = timeline
        
        return results
    
    def get_statistics(self) -> Dict:
        """Obtenir les statistiques du pipeline"""
        stats = self.stats.copy()
        
        if stats['total_processed'] > 0:
            stats['success_rate'] = stats['success'] / stats['total_processed']
            stats['avg_processing_time'] = stats['processing_time'] / stats['total_processed']
        
        # Statistiques du graphe
        if self.graph_builder.graph:
            stats['graph_nodes'] = self.graph_builder.graph.number_of_nodes()
            stats['graph_edges'] = self.graph_builder.graph.number_of_edges()
        
        return stats

# ================== 7. SAUVEGARDE VERS SUPABASE ==================

class EnrichmentSaver:
    """Sauvegarde des enrichissements vers Supabase"""
    
    def __init__(self):
        from supabase import create_client
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def save_enrichment(self, enrichment: DocumentEnrichment) -> bool:
        """Sauvegarder un enrichissement"""
        try:
            # Préparer les données pour Supabase
            data = {
                'document_id': enrichment.document_id,
                
                # Métadonnées Suisse
                'canton': enrichment.metadata_swiss.get('canton'),
                'commune': enrichment.metadata_swiss.get('commune'),
                'code_postal': enrichment.metadata_swiss.get('code_postal'),
                'adresse_principale': enrichment.metadata_swiss.get('adresse'),
                
                # Montants
                'montant_principal': enrichment.metadata_swiss.get('montant_principal'),
                'devise': 'CHF' if enrichment.metadata_swiss.get('montant_principal') else None,
                
                # Entités
                'bailleur': enrichment.metadata_swiss.get('bailleur'),
                'locataire': enrichment.metadata_swiss.get('locataire'),
                'proprietaire': enrichment.metadata_swiss.get('proprietaire'),
                
                # Propriété
                'type_bien': enrichment.metadata_swiss.get('type_bien'),
                'surface_m2': enrichment.metadata_swiss.get('surface_m2'),
                'nombre_pieces': enrichment.metadata_swiss.get('nombre_pieces'),
                'etage': enrichment.metadata_swiss.get('etage'),
                
                # Classification
                'type_document': enrichment.document_type,
                'categorie': enrichment.document_type,
                'tags': enrichment.tags,
                
                # Scores
                'importance_score': enrichment.importance_score,
                'confidence_level': enrichment.confidence_score,
                'data_quality_score': enrichment.quality_score,
                
                # Enrichissement complet en JSON
                'metadata': {
                    'enrichment_version': '2025.1',
                    'summary_short': enrichment.summary_short,
                    'summary_detailed': enrichment.summary_detailed,
                    'key_points': enrichment.key_points,
                    'qa_pairs': enrichment.questions_answers,
                    'risk_factors': enrichment.risk_factors,
                    'related_documents': enrichment.related_documents,
                    'all_metadata': enrichment.metadata_swiss
                }
            }
            
            # Mettre à jour le document
            response = self.client.table('documents_full').update(data).eq(
                'id', enrichment.document_id
            ).execute()
            
            # Sauvegarder aussi dans la table d'enrichissement dédiée
            enrichment_data = {
                'document_id': enrichment.document_id,
                'enrichment_type': 'state_of_the_art_2025',
                'enrichment_data': {
                    'summary': enrichment.summary_detailed,
                    'qa_pairs': enrichment.questions_answers,
                    'key_points': enrichment.key_points,
                    'risk_analysis': enrichment.risk_factors,
                    'relationships': enrichment.related_documents
                },
                'created_at': datetime.now().isoformat()
            }
            
            self.client.table('document_enrichments').upsert(enrichment_data).execute()
            
            logger.info(f"[{enrichment.document_id}] Enrichissement sauvegardé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde: {e}")
            return False
    
    def save_knowledge_graph(self, graph: nx.DiGraph) -> bool:
        """Sauvegarder le graphe de connaissances"""
        try:
            from networkx.readwrite import json_graph
            
            graph_data = {
                'graph_type': 'knowledge_graph',
                'graph_data': json_graph.node_link_data(graph),
                'statistics': {
                    'nodes': graph.number_of_nodes(),
                    'edges': graph.number_of_edges(),
                    'components': nx.number_weakly_connected_components(graph)
                },
                'created_at': datetime.now().isoformat()
            }
            
            self.client.table('knowledge_graph').upsert(graph_data).execute()
            
            logger.info("Graphe de connaissances sauvegardé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde graphe: {e}")
            return False

# ================== MAIN EXECUTION ==================

async def main(
    *,
    auto_confirm: bool = False,
    limit: Optional[int] = None,
    batch_size: int = 50,
    include_existing: bool = False,
    semantic_workers: Optional[int] = None,
) -> None:
    """Fonction principale d'enrichissement."""
    
    print("\n" + "=" * 80)
    print("ENRICHISSEMENT STATE OF THE ART 2025")
    print("=" * 80)
    logger.info("Démarrage du pipeline d'enrichissement (auto_confirm=%s, limit=%s, batch_size=%s, include_existing=%s)",
                auto_confirm, limit, batch_size, include_existing)
    
    pipeline = EnrichmentPipeline()
    saver = EnrichmentSaver()
    
    print("\n[1] Récupération des documents...")
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    response = client.table('documents_full').select('id, file_name, full_content').execute()
    documents = response.data or []
    logger.info("Documents récupérés: %s", len(documents))
    print(f"  -> {len(documents)} documents trouvés")
    
    enriched_ids: set[int] = set()
    if not include_existing:
        enriched_response = client.table('document_enrichments').select('document_id').execute()
        enriched_ids = {r['document_id'] for r in (enriched_response.data or [])}
        logger.info("Documents déjà enrichis: %s", len(enriched_ids))
    
    documents_to_process: List[Tuple[int, str, str]] = []
    for doc in documents:
        doc_id = doc.get('id')
        if doc_id is None:
            continue
        if not include_existing and doc_id in enriched_ids:
            continue
        documents_to_process.append((doc_id, doc.get('full_content', ''), doc.get('file_name', f"doc_{doc_id}")))
    
    if limit:
        documents_to_process = documents_to_process[:max(limit, 0)]
    
    total_documents = len(documents_to_process)
    print(f"  -> {total_documents} documents à enrichir")
    logger.info("Documents à traiter après filtrage: %s", total_documents)
    
    if total_documents == 0:
        print("\n[INFO] Tous les documents sont déjà enrichis!")
        logger.info("Aucun document à traiter, arrêt.")
        return
    
    if not auto_confirm:
        try:
            response = input(f"\nEnrichir {total_documents} documents? (o/n): ")
            if response.strip().lower() != 'o':
                print("Annulé.")
                logger.info("Enrichissement annulé par l'utilisateur.")
                return
        except EOFError:
            print("Entrée utilisateur indisponible. Relancez avec --yes pour confirmer automatiquement.")
            logger.warning("Entrée utilisateur indisponible (EOF). Annulation.")
            return
    else:
        print("  -> Confirmation automatique activée (--yes)")
    
    semantic_workers = max(1, int(semantic_workers or WORKERS_CONFIG['semantic_enrichment']))
    current_workers = WORKERS_CONFIG.copy()
    current_workers['semantic_enrichment'] = semantic_workers
    total_workers = sum(current_workers.values())
    print(f"\n[2] Enrichissement avec {total_workers} workers total (semantic={semantic_workers})...")
    logger.info(
        "Workers configurés: %s (semantic=%s) | configuration complète: %s",
        total_workers,
        semantic_workers,
        current_workers,
    )
    
    batch_size = max(1, int(batch_size))
    total_batches = math.ceil(total_documents / batch_size)
    all_enrichments: List[DocumentEnrichment] = []
    global_start = datetime.now()
    
    for batch_index in range(total_batches):
        start_idx = batch_index * batch_size
        batch = documents_to_process[start_idx:start_idx + batch_size]
        batch_number = batch_index + 1
        print(f"\n  Batch {batch_number}/{total_batches}")
        logger.info("Traitement du batch %s/%s (%s documents)", batch_number, total_batches, len(batch))
        
        batch_start = datetime.now()
        enrichments = await pipeline.process_batch(
            batch,
            max_workers=semantic_workers,
        )
        batch_duration = (datetime.now() - batch_start).total_seconds()
        all_enrichments.extend(enrichments)
        
        print(f"  Sauvegarde de {len(enrichments)} enrichissements...")
        logger.info("Sauvegarde de %s enrichissements (durée batch: %.2fs)", len(enrichments), batch_duration)
        for enrichment in enrichments:
            saver.save_enrichment(enrichment)
        
        processed = len(all_enrichments)
        elapsed = (datetime.now() - global_start).total_seconds()
        progress = processed / total_documents if total_documents else 0
        rate = processed / elapsed if elapsed > 0 else 0
        remaining_docs = total_documents - processed
        eta_seconds = remaining_docs / rate if rate > 0 else None
        
        print(f"  Progression: {progress*100:.1f}% ({processed}/{total_documents})")
        if rate > 0:
            print(f"  Cadence moyenne: {rate:.2f} doc/s | ETA: {str(timedelta(seconds=int(eta_seconds))) if eta_seconds else 'calcul...'}")
        logger.info("Progression: %.1f%% (%s/%s) | Cadence %.2f doc/s | ETA %s",
                    progress * 100, processed, total_documents, rate,
                    str(timedelta(seconds=int(eta_seconds))) if eta_seconds else "N/A")
    
    if pipeline.graph_builder.graph:
        print("\n[3] Sauvegarde du graphe de connaissances...")
        logger.info("Sauvegarde du graphe de connaissances.")
        saver.save_knowledge_graph(pipeline.graph_builder.graph)
    
    print("\n" + "=" * 80)
    print("STATISTIQUES FINALES")
    print("=" * 80)
    
    stats = pipeline.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    logger.info("Statistiques finales: %s", stats)
    
    total_duration = (datetime.now() - global_start).total_seconds()
    print(f"\n[TERMINÉ] Enrichissement State of the Art 2025 complété en {timedelta(seconds=int(total_duration))} !")
    logger.info("Pipeline terminé en %ss", total_duration)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrichissement State of the Art 2025")
    parser.add_argument("--yes", "-y", action="store_true", help="Confirmer automatiquement la procédure")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de documents à traiter")
    parser.add_argument("--batch-size", type=int, default=50, help="Taille des batches (défaut: 50)")
    parser.add_argument("--include-existing", action="store_true", help="Inclure les documents déjà enrichis")
    parser.add_argument("--workers", type=int, default=None, help="Nombre de workers pour l'enrichissement sémantique (défaut configuration)")
    args = parser.parse_args()

    try:
        import spacy
        import networkx
        import sklearn
        from transformers import pipeline
    except ImportError:
        print("Installation des dépendances avancées...")
        os.system("pip install spacy networkx scikit-learn transformers")
        os.system("python -m spacy download fr_core_news_sm")
    
    asyncio.run(
        main(
            auto_confirm=args.yes,
            limit=args.limit,
            batch_size=args.batch_size,
            include_existing=args.include_existing,
            semantic_workers=args.workers,
        )
    )
