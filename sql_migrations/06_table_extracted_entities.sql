-- ================================================================
-- ÉTAPE 6: Table extracted_entities
-- ================================================================

CREATE TABLE IF NOT EXISTS extracted_entities (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,

    -- Type et valeur de l'entité
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    entity_normalized TEXT,

    -- Contexte
    context TEXT,
    chunk_ids BIGINT[],

    -- Comptage
    mention_count INTEGER DEFAULT 1,

    -- Métadonnées supplémentaires
    entity_metadata JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour extracted_entities
CREATE INDEX IF NOT EXISTS idx_entities_document_id ON extracted_entities USING btree(document_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON extracted_entities USING btree(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_value ON extracted_entities USING btree(entity_value);
CREATE INDEX IF NOT EXISTS idx_entities_normalized ON extracted_entities USING btree(entity_normalized);
CREATE INDEX IF NOT EXISTS idx_entities_type_value ON extracted_entities USING btree(entity_type, entity_value);

-- Index trigram pour recherche fuzzy
CREATE INDEX IF NOT EXISTS idx_entities_value_trgm ON extracted_entities USING GIN(entity_value gin_trgm_ops);

-- Vérification
SELECT tablename FROM pg_tables WHERE tablename = 'extracted_entities';
