-- ================================================================
-- ÉTAPE 1: Extensions PostgreSQL
-- ================================================================

-- Extension pour vecteurs (embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- Extension pour recherche trigram (fuzzy search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Vérification
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');
