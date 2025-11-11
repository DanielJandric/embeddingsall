-- ================================================================
-- ÉTAPE 10: Index Full-Text Search
-- ================================================================

-- Index full-text search pour documents (CRUCIAL pour LLM)
CREATE INDEX IF NOT EXISTS idx_documents_search_vector ON documents_full USING GIN(search_vector);

-- Index full-text search pour chunks
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON document_chunks USING GIN(search_vector);

-- Vérification
SELECT
    indexname,
    tablename
FROM pg_indexes
WHERE indexname IN ('idx_documents_search_vector', 'idx_chunks_search_vector');
