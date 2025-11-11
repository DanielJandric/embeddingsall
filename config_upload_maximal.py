"""
Configuration pour upload ULTRA-COMPLET avec extraction maximale de métadonnées
"""

# Configuration du chunking
CHUNK_CONFIG = {
    # Chunks plus petits = meilleure précision LLM
    'chunk_size': 800,  # 800 caractères par chunk (au lieu de 1000)
    'overlap': 250,      # Overlap de 250 chars (au lieu de 200) pour meilleur contexte
    'context_size': 300  # Contexte avant/après de 300 chars (au lieu de 200)
}

# Configuration des métadonnées
METADATA_CONFIG = {
    # Extraction maximale de toutes les métadonnées
    'extract_all': True,
    'deep_analysis': True,

    # Extraction d'entités
    'extract_entities': True,
    'extract_companies': True,
    'extract_locations': True,
    'extract_persons': True,
    'extract_amounts': True,
    'extract_dates': True,
    'extract_references': True,

    # Classification automatique
    'auto_classify': True,
    'detect_document_type': True,
    'detect_category': True,
    'generate_tags': True,

    # Scores de qualité
    'calculate_quality_scores': True,
    'calculate_importance_scores': True,
    'calculate_completeness_scores': True,

    # Analyse linguistique
    'detect_language': True,
    'analyze_formality': True,
    'extract_keywords': True,

    # Structure du document
    'detect_sections': True,
    'extract_titles': True,
    'analyze_document_structure': True,
}

# Configuration de l'upload
UPLOAD_CONFIG = {
    'batch_size': 50,  # Upload par batches de 50 chunks
    'retry_on_error': True,
    'max_retries': 3,
    'verbose': True,  # Afficher tous les détails
    'save_errors_log': True
}

# Configuration OpenAI
OPENAI_CONFIG = {
    'model': 'text-embedding-3-small',  # Modèle d'embedding
    'dimensions': 1536,
    'batch_size': 100,  # Batches de 100 pour API OpenAI
    'max_tokens': 8191
}
