-- ============================================================================
-- NOUVELLE STRUCTURE OPTIMISÉE POUR LA RECHERCHE SÉMANTIQUE
-- ============================================================================
-- Architecture:
-- 1. documents_full : Stocke le document complet avec métadonnées
-- 2. document_chunks : Stocke les chunks avec embeddings (forte granularité)
-- ============================================================================

-- Étape 1: Activer l'extension pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- TABLE 1: DOCUMENTS COMPLETS
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents_full (
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
    processing_method TEXT, -- 'pdf_direct', 'azure_ocr', 'text_file', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index sur file_path pour recherche rapide
CREATE INDEX IF NOT EXISTS documents_full_file_path_idx ON documents_full(file_path);

-- Index sur file_name pour recherche par nom
CREATE INDEX IF NOT EXISTS documents_full_file_name_idx ON documents_full(file_name);

-- Index sur métadonnées
CREATE INDEX IF NOT EXISTS documents_full_metadata_idx ON documents_full USING GIN (metadata);

-- Index sur date de création
CREATE INDEX IF NOT EXISTS documents_full_created_at_idx ON documents_full (created_at DESC);

-- ============================================================================
-- TABLE 2: CHUNKS AVEC EMBEDDINGS (HAUTE GRANULARITÉ)
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_content TEXT NOT NULL,
    chunk_size INT NOT NULL,
    embedding VECTOR(1536),  -- text-embedding-3-small OpenAI
    chunk_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Contrainte d'unicité : un seul chunk par (document_id, chunk_index)
    UNIQUE(document_id, chunk_index)
);

-- Index pour la recherche vectorielle (HNSW est plus rapide que IVFFlat)
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
ON document_chunks
USING hnsw (embedding vector_cosine_ops);

-- Index sur document_id pour récupérer tous les chunks d'un document
CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx ON document_chunks(document_id);

-- Index composite pour trier les chunks par document
CREATE INDEX IF NOT EXISTS document_chunks_doc_chunk_idx ON document_chunks(document_id, chunk_index);

-- Index sur les métadonnées des chunks
CREATE INDEX IF NOT EXISTS document_chunks_metadata_idx ON document_chunks USING GIN (chunk_metadata);

-- ============================================================================
-- FONCTIONS UTILES
-- ============================================================================

-- Fonction pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour updated_at sur documents_full
DROP TRIGGER IF EXISTS update_documents_full_updated_at ON documents_full;
CREATE TRIGGER update_documents_full_updated_at
    BEFORE UPDATE ON documents_full
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FONCTION DE RECHERCHE VECTORIELLE (PRINCIPALE)
-- ============================================================================

CREATE OR REPLACE FUNCTION match_document_chunks(
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
LANGUAGE SQL STABLE
AS $$
    SELECT
        c.id AS chunk_id,
        c.document_id,
        d.file_name,
        d.file_path,
        c.chunk_index,
        c.chunk_content,
        d.full_content AS full_document_content,
        1 - (c.embedding <=> query_embedding) AS similarity,
        c.chunk_metadata,
        d.metadata AS document_metadata
    FROM document_chunks c
    JOIN documents_full d ON c.document_id = d.id
    WHERE 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ============================================================================
-- FONCTION : Rechercher dans un fichier spécifique
-- ============================================================================

CREATE OR REPLACE FUNCTION match_chunks_in_file(
    query_embedding VECTOR(1536),
    file_path_param TEXT,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id BIGINT,
    chunk_index INT,
    chunk_content TEXT,
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        c.id AS chunk_id,
        c.chunk_index,
        c.chunk_content,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM document_chunks c
    JOIN documents_full d ON c.document_id = d.id
    WHERE d.file_path = file_path_param
        AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ============================================================================
-- FONCTION : Récupérer un document complet par ID
-- ============================================================================

CREATE OR REPLACE FUNCTION get_full_document(document_id_param BIGINT)
RETURNS TABLE (
    id BIGINT,
    file_name TEXT,
    file_path TEXT,
    full_content TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        id,
        file_name,
        file_path,
        full_content,
        metadata,
        created_at
    FROM documents_full
    WHERE id = document_id_param;
$$;

-- ============================================================================
-- FONCTION : Récupérer tous les chunks d'un document
-- ============================================================================

CREATE OR REPLACE FUNCTION get_document_chunks(document_id_param BIGINT)
RETURNS TABLE (
    chunk_id BIGINT,
    chunk_index INT,
    chunk_content TEXT,
    chunk_size INT
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        id AS chunk_id,
        chunk_index,
        chunk_content,
        chunk_size
    FROM document_chunks
    WHERE document_id = document_id_param
    ORDER BY chunk_index;
$$;

-- ============================================================================
-- FONCTION : Statistiques globales
-- ============================================================================

CREATE OR REPLACE FUNCTION get_database_stats()
RETURNS TABLE (
    total_documents BIGINT,
    total_chunks BIGINT,
    avg_chunks_per_document NUMERIC,
    total_size_mb NUMERIC,
    avg_chunk_size INT
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        COUNT(DISTINCT d.id) AS total_documents,
        COUNT(c.id) AS total_chunks,
        ROUND(COUNT(c.id)::NUMERIC / NULLIF(COUNT(DISTINCT d.id), 0), 2) AS avg_chunks_per_document,
        ROUND(SUM(d.file_size_bytes)::NUMERIC / 1024.0 / 1024.0, 2) AS total_size_mb,
        ROUND(AVG(c.chunk_size))::INT AS avg_chunk_size
    FROM documents_full d
    LEFT JOIN document_chunks c ON d.id = c.document_id;
$$;

-- ============================================================================
-- VUE : Résumé des documents avec nombre de chunks
-- ============================================================================

CREATE OR REPLACE VIEW documents_summary AS
SELECT
    d.id,
    d.file_name,
    d.file_path,
    d.file_type,
    d.page_count,
    d.word_count,
    d.char_count,
    COUNT(c.id) AS chunk_count,
    d.processing_method,
    d.created_at
FROM documents_full d
LEFT JOIN document_chunks c ON d.id = c.document_id
GROUP BY d.id
ORDER BY d.created_at DESC;

-- ============================================================================
-- FONCTION : Supprimer un document et ses chunks
-- ============================================================================

CREATE OR REPLACE FUNCTION delete_document_by_path(file_path_param TEXT)
RETURNS TABLE (
    deleted_document_id BIGINT,
    deleted_chunks_count BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    doc_id BIGINT;
    chunks_count BIGINT;
BEGIN
    -- Trouver le document
    SELECT id INTO doc_id
    FROM documents_full
    WHERE file_path = file_path_param;

    IF doc_id IS NULL THEN
        RETURN QUERY SELECT NULL::BIGINT, 0::BIGINT;
        RETURN;
    END IF;

    -- Compter les chunks
    SELECT COUNT(*) INTO chunks_count
    FROM document_chunks
    WHERE document_id = doc_id;

    -- Supprimer le document (les chunks seront supprimés automatiquement via CASCADE)
    DELETE FROM documents_full WHERE id = doc_id;

    RETURN QUERY SELECT doc_id, chunks_count;
END;
$$;

-- ============================================================================
-- FONCTION : Nettoyer les vieux documents
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_documents(days_old INT DEFAULT 365)
RETURNS TABLE (
    deleted_documents BIGINT,
    deleted_chunks BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    docs_count BIGINT;
    chunks_count BIGINT;
BEGIN
    -- Compter d'abord
    SELECT COUNT(*) INTO docs_count
    FROM documents_full
    WHERE created_at < NOW() - (days_old || ' days')::INTERVAL;

    SELECT COUNT(*) INTO chunks_count
    FROM document_chunks c
    JOIN documents_full d ON c.document_id = d.id
    WHERE d.created_at < NOW() - (days_old || ' days')::INTERVAL;

    -- Supprimer (CASCADE supprimera les chunks)
    DELETE FROM documents_full
    WHERE created_at < NOW() - (days_old || ' days')::INTERVAL;

    RETURN QUERY SELECT docs_count, chunks_count;
END;
$$;

-- ============================================================================
-- VÉRIFICATIONS ET TESTS
-- ============================================================================

-- Vérifier que l'extension vector est activée
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Vérifier que les tables existent
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('documents_full', 'document_chunks');

-- Vérifier que les index existent
SELECT tablename, indexname FROM pg_indexes
WHERE tablename IN ('documents_full', 'document_chunks')
ORDER BY tablename, indexname;

-- Vérifier que les fonctions existent
SELECT routine_name FROM information_schema.routines
WHERE routine_name LIKE '%document%' OR routine_name LIKE '%chunk%'
ORDER BY routine_name;

-- Afficher les statistiques initiales
SELECT * FROM get_database_stats();

-- ============================================================================
-- EXEMPLES D'UTILISATION
-- ============================================================================

/*
-- 1. Voir les statistiques
SELECT * FROM get_database_stats();

-- 2. Voir tous les documents avec leur nombre de chunks
SELECT * FROM documents_summary;

-- 3. Rechercher des chunks similaires
SELECT * FROM match_document_chunks(
    ARRAY[0.1, 0.2, ...]::VECTOR(1536),  -- Embedding de la requête
    0.7,  -- Seuil de similarité
    10    -- Nombre de résultats
);

-- 4. Récupérer un document complet
SELECT * FROM get_full_document(1);

-- 5. Récupérer tous les chunks d'un document
SELECT * FROM get_document_chunks(1);

-- 6. Supprimer un document et ses chunks
SELECT * FROM delete_document_by_path('/chemin/vers/fichier.pdf');

-- 7. Nettoyer les documents de plus d'un an
SELECT * FROM cleanup_old_documents(365);
*/

-- ============================================================================
-- MESSAGE FINAL
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ Configuration Supabase terminée avec succès !';
    RAISE NOTICE '📊 Nouvelle structure avec 2 tables :';
    RAISE NOTICE '   - documents_full : Documents complets';
    RAISE NOTICE '   - document_chunks : Chunks avec embeddings (haute granularité)';
    RAISE NOTICE '';
    RAISE NOTICE '🔍 Fonctions disponibles :';
    RAISE NOTICE '   - match_document_chunks() : Recherche sémantique';
    RAISE NOTICE '   - get_full_document() : Récupérer document complet';
    RAISE NOTICE '   - get_database_stats() : Statistiques';
    RAISE NOTICE '';
    RAISE NOTICE '📝 Prochaine étape : Uploader vos documents avec process_fast.py';
    RAISE NOTICE '';
END $$;
