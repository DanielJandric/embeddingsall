-- ================================================================
-- ÉTAPE 4: Table document_chunks
-- ================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    -- Identifiants
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,

    -- Contenu du chunk
    chunk_content TEXT NOT NULL,
    chunk_size INTEGER NOT NULL,

    -- Contexte enrichi
    context_before TEXT,
    context_after TEXT,

    -- Position dans le document
    start_position INTEGER,
    end_position INTEGER,
    page_number INTEGER,

    -- Structure du document
    section_title TEXT,
    section_level INTEGER,
    paragraph_index INTEGER,

    -- Informations sémantiques
    chunk_type TEXT,
    has_tables BOOLEAN DEFAULT FALSE,
    has_numbers BOOLEAN DEFAULT FALSE,
    has_dates BOOLEAN DEFAULT FALSE,
    has_amounts BOOLEAN DEFAULT FALSE,

    -- Entités mentionnées
    entities_mentioned TEXT[],
    locations_mentioned TEXT[],

    -- Importance
    importance_score NUMERIC(3,2),

    -- Embedding vectoriel
    embedding vector(1536),

    -- Full-text search vector
    search_vector tsvector,

    -- Métadonnées du chunk
    chunk_metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(document_id, chunk_index)
);

-- Vérification
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE tablename = 'document_chunks';
