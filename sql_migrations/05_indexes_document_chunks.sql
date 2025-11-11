-- ================================================================
-- ÉTAPE 5: Index pour document_chunks
-- ================================================================

-- Index btree standards
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks USING btree(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON document_chunks USING btree(chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_page_number ON document_chunks USING btree(page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_type ON document_chunks USING btree(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_importance ON document_chunks USING btree(importance_score DESC);

-- Index pour filtrage avec flags booléens
CREATE INDEX IF NOT EXISTS idx_chunks_content_flags ON document_chunks(has_tables, has_numbers, has_dates, has_amounts);

-- Index vectoriel HNSW pour recherche sémantique rapide
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Vérification
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'document_chunks'
ORDER BY indexname;
