-- ============================================================================
-- SCRIPT DE NETTOYAGE COMPLET ET RECRÉATION
-- ============================================================================
-- Ce script supprime TOUT et recommence de zéro
-- ============================================================================

-- PARTIE 1: TOUT SUPPRIMER
-- ============================================================================

-- Supprimer la vue
DROP VIEW IF EXISTS documents_summary CASCADE;

-- Supprimer toutes les fonctions
DROP FUNCTION IF EXISTS get_database_stats() CASCADE;
DROP FUNCTION IF EXISTS match_document_chunks(VECTOR(1536), FLOAT, INT) CASCADE;
DROP FUNCTION IF EXISTS match_document_chunks(VECTOR, FLOAT, INT) CASCADE;
DROP FUNCTION IF EXISTS get_full_document(BIGINT) CASCADE;
DROP FUNCTION IF EXISTS get_document_chunks(BIGINT) CASCADE;
DROP FUNCTION IF EXISTS delete_document_by_path(TEXT) CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Supprimer les tables (CASCADE supprime aussi les index et contraintes)
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents_full CASCADE;

-- PARTIE 2: TOUT RECRÉER
-- ============================================================================

-- Extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Table documents complets
CREATE TABLE documents_full (
    id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_type TEXT,
    full_content TEXT NOT NULL,
    file_size_bytes BIGINT,
    page_count INT,
    word_count INT,
    char_count INT,
    metadata JSONB DEFAULT '{}'::jsonb,
    processing_method TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index
CREATE INDEX documents_full_file_path_idx ON documents_full(file_path);
CREATE INDEX documents_full_file_name_idx ON documents_full(file_name);
CREATE INDEX documents_full_metadata_idx ON documents_full USING GIN (metadata);
CREATE INDEX documents_full_created_at_idx ON documents_full(created_at DESC);

-- Table chunks
CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_content TEXT NOT NULL,
    chunk_size INT NOT NULL,
    embedding VECTOR(1536),
    chunk_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

-- Index
CREATE INDEX document_chunks_embedding_idx ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX document_chunks_document_id_idx ON document_chunks(document_id);
CREATE INDEX document_chunks_doc_chunk_idx ON document_chunks(document_id, chunk_index);

-- Trigger updated_at
CREATE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_full_updated_at
    BEFORE UPDATE ON documents_full
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Fonction recherche vectorielle
CREATE FUNCTION match_document_chunks(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id BIGINT,
    document_id BIGINT,
    file_name TEXT,
    file_path TEXT,
    chunk_index INT,
    chunk_content TEXT,
    full_document_content TEXT,
    similarity FLOAT,
    chunk_metadata JSONB,
    document_metadata JSONB
)
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.document_id,
        d.file_name,
        d.file_path,
        c.chunk_index,
        c.chunk_content,
        d.full_content,
        1 - (c.embedding <=> query_embedding) AS similarity,
        c.chunk_metadata,
        d.metadata
    FROM document_chunks c
    JOIN documents_full d ON c.document_id = d.id
    WHERE c.embedding IS NOT NULL
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;

-- Fonction statistiques (retourne JSON)
CREATE FUNCTION get_database_stats()
RETURNS JSON
AS $$
BEGIN
    RETURN json_build_object(
        'total_documents', (SELECT COUNT(*) FROM documents_full),
        'total_chunks', (SELECT COUNT(*) FROM document_chunks),
        'avg_chunks_per_document', COALESCE(
            ROUND((SELECT COUNT(*)::NUMERIC FROM document_chunks) / NULLIF((SELECT COUNT(*) FROM documents_full), 0), 2),
            0
        ),
        'total_size_mb', COALESCE(
            ROUND((SELECT SUM(file_size_bytes) FROM documents_full)::NUMERIC / 1048576.0, 2),
            0
        ),
        'avg_chunk_size', COALESCE(
            ROUND((SELECT AVG(chunk_size) FROM document_chunks)),
            0
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Fonction récupérer document
CREATE FUNCTION get_full_document(document_id_param BIGINT)
RETURNS JSON
AS $$
BEGIN
    RETURN (
        SELECT json_build_object(
            'id', id,
            'file_name', file_name,
            'file_path', file_path,
            'full_content', full_content,
            'metadata', metadata,
            'created_at', created_at
        )
        FROM documents_full
        WHERE id = document_id_param
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Fonction supprimer document
CREATE FUNCTION delete_document_by_path(file_path_param TEXT)
RETURNS JSON
AS $$
DECLARE
    doc_id BIGINT;
    chunks_count BIGINT;
BEGIN
    SELECT id INTO doc_id FROM documents_full WHERE file_path = file_path_param;

    IF doc_id IS NULL THEN
        RETURN json_build_object('deleted_document_id', NULL, 'deleted_chunks_count', 0);
    END IF;

    SELECT COUNT(*) INTO chunks_count FROM document_chunks WHERE document_id = doc_id;

    DELETE FROM documents_full WHERE id = doc_id;

    RETURN json_build_object('deleted_document_id', doc_id, 'deleted_chunks_count', chunks_count);
END;
$$ LANGUAGE plpgsql;

-- Vue résumé
CREATE VIEW documents_summary AS
SELECT
    d.id,
    d.file_name,
    d.file_path,
    d.file_type,
    d.page_count,
    d.word_count,
    COUNT(c.id) AS chunk_count,
    d.processing_method,
    d.created_at
FROM documents_full d
LEFT JOIN document_chunks c ON d.id = c.document_id
GROUP BY d.id
ORDER BY d.created_at DESC;

-- ============================================================================
-- VÉRIFICATION
-- ============================================================================

SELECT 'Configuration terminée !' AS message;
SELECT get_database_stats() AS stats;
