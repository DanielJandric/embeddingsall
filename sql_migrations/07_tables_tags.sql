-- ================================================================
-- ÉTAPE 7: Tables de Tags
-- ================================================================

-- Table des tags
CREATE TABLE IF NOT EXISTS document_tags (
    id BIGSERIAL PRIMARY KEY,
    tag_name TEXT NOT NULL UNIQUE,
    tag_category TEXT,
    tag_description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour document_tags
CREATE INDEX IF NOT EXISTS idx_tags_category ON document_tags USING btree(tag_category);
CREATE INDEX IF NOT EXISTS idx_tags_usage ON document_tags USING btree(usage_count DESC);

-- Table de relation many-to-many
CREATE TABLE IF NOT EXISTS document_tag_relations (
    document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    tag_id BIGINT NOT NULL REFERENCES document_tags(id) ON DELETE CASCADE,
    confidence NUMERIC(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (document_id, tag_id)
);

-- Index pour document_tag_relations
CREATE INDEX IF NOT EXISTS idx_tag_relations_document ON document_tag_relations USING btree(document_id);
CREATE INDEX IF NOT EXISTS idx_tag_relations_tag ON document_tag_relations USING btree(tag_id);

-- Vérification
SELECT tablename FROM pg_tables WHERE tablename IN ('document_tags', 'document_tag_relations');
