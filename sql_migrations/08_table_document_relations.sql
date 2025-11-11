-- ================================================================
-- ÉTAPE 8: Table document_relations
-- ================================================================

CREATE TABLE IF NOT EXISTS document_relations (
    id BIGSERIAL PRIMARY KEY,
    source_document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    target_document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,

    relation_type TEXT NOT NULL,
    similarity_score NUMERIC(5,4),

    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source_document_id, target_document_id, relation_type)
);

-- Index pour document_relations
CREATE INDEX IF NOT EXISTS idx_relations_source ON document_relations USING btree(source_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON document_relations USING btree(target_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON document_relations USING btree(relation_type);
CREATE INDEX IF NOT EXISTS idx_relations_similarity ON document_relations USING btree(similarity_score DESC);

-- Vérification
SELECT tablename FROM pg_tables WHERE tablename = 'document_relations';
