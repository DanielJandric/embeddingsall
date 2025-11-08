-- ============================================================================
-- SCRIPT SQL FINAL - TESTÉ ET FONCTIONNEL
-- ============================================================================
-- Ce script crée une base de données optimisée pour la recherche sémantique
-- Testé avec Supabase + PostgREST + pgvector
-- ============================================================================

BEGIN;

-- ============================================================================
-- ÉTAPE 1: NETTOYAGE COMPLET
-- ============================================================================

-- Supprimer les vues
DROP VIEW IF EXISTS documents_summary CASCADE;

-- Supprimer les fonctions (toutes les variantes possibles)
DROP FUNCTION IF EXISTS get_database_stats() CASCADE;
DROP FUNCTION IF EXISTS match_document_chunks(vector, float, int) CASCADE;
DROP FUNCTION IF EXISTS match_document_chunks(vector(1536), float, int) CASCADE;
DROP FUNCTION IF EXISTS get_full_document(bigint) CASCADE;
DROP FUNCTION IF EXISTS delete_document_by_path(text) CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Supprimer les tables (l'ordre est important à cause des foreign keys)
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents_full CASCADE;

-- ============================================================================
-- ÉTAPE 2: EXTENSION PGVECTOR
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

-- ============================================================================
-- ÉTAPE 3: TABLE DOCUMENTS COMPLETS
-- ============================================================================

CREATE TABLE public.documents_full (
    id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,
    full_content TEXT NOT NULL,
    file_size_bytes BIGINT DEFAULT 0,
    page_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    char_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    processing_method TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT documents_full_file_path_unique UNIQUE (file_path)
);

-- Index pour performance
CREATE INDEX idx_documents_full_file_path ON public.documents_full USING btree (file_path);
CREATE INDEX idx_documents_full_file_name ON public.documents_full USING btree (file_name);
CREATE INDEX idx_documents_full_created_at ON public.documents_full USING btree (created_at DESC);
CREATE INDEX idx_documents_full_metadata ON public.documents_full USING gin (metadata);

COMMENT ON TABLE public.documents_full IS 'Stocke les documents complets avec leurs métadonnées';

-- ============================================================================
-- ÉTAPE 4: TABLE CHUNKS AVEC EMBEDDINGS
-- ============================================================================

CREATE TABLE public.document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_content TEXT NOT NULL,
    chunk_size INTEGER NOT NULL,
    embedding vector(1536),
    chunk_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT fk_document_chunks_document
        FOREIGN KEY (document_id)
        REFERENCES public.documents_full(id)
        ON DELETE CASCADE,
    CONSTRAINT document_chunks_doc_chunk_unique
        UNIQUE (document_id, chunk_index)
);

-- Index pour recherche vectorielle (HNSW est le plus rapide)
CREATE INDEX idx_document_chunks_embedding ON public.document_chunks
    USING hnsw (embedding vector_cosine_ops);

-- Index pour jointures
CREATE INDEX idx_document_chunks_document_id ON public.document_chunks USING btree (document_id);
CREATE INDEX idx_document_chunks_doc_chunk ON public.document_chunks USING btree (document_id, chunk_index);

COMMENT ON TABLE public.document_chunks IS 'Stocke les chunks de texte avec leurs embeddings vectoriels';

-- ============================================================================
-- ÉTAPE 5: TRIGGER POUR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_update_documents_full_updated_at
    BEFORE UPDATE ON public.documents_full
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================================
-- ÉTAPE 6: FONCTION DE RECHERCHE VECTORIELLE (PRINCIPALE)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.match_document_chunks(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    chunk_id bigint,
    document_id bigint,
    file_name text,
    file_path text,
    chunk_index int,
    chunk_content text,
    full_document_content text,
    similarity float,
    chunk_metadata jsonb,
    document_metadata jsonb
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS chunk_id,
        c.document_id,
        d.file_name,
        d.file_path,
        c.chunk_index,
        c.chunk_content,
        d.full_content AS full_document_content,
        (1 - (c.embedding <=> query_embedding))::float AS similarity,
        c.chunk_metadata,
        d.metadata AS document_metadata
    FROM public.document_chunks c
    INNER JOIN public.documents_full d ON c.document_id = d.id
    WHERE
        c.embedding IS NOT NULL
        AND (1 - (c.embedding <=> query_embedding)) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION public.match_document_chunks IS 'Recherche les chunks les plus similaires à un embedding donné';

-- ============================================================================
-- ÉTAPE 7: FONCTION STATISTIQUES
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_database_stats()
RETURNS TABLE (
    total_documents bigint,
    total_chunks bigint,
    avg_chunks_per_document numeric,
    total_size_mb numeric,
    avg_chunk_size numeric
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(DISTINCT d.id)::bigint AS total_documents,
        COUNT(c.id)::bigint AS total_chunks,
        ROUND(
            COALESCE(COUNT(c.id)::numeric / NULLIF(COUNT(DISTINCT d.id), 0), 0),
            2
        ) AS avg_chunks_per_document,
        ROUND(
            COALESCE(SUM(d.file_size_bytes)::numeric / 1048576.0, 0),
            2
        ) AS total_size_mb,
        ROUND(
            COALESCE(AVG(c.chunk_size), 0),
            0
        ) AS avg_chunk_size
    FROM public.documents_full d
    LEFT JOIN public.document_chunks c ON d.id = c.document_id;
END;
$$;

COMMENT ON FUNCTION public.get_database_stats IS 'Retourne les statistiques globales de la base de données';

-- ============================================================================
-- ÉTAPE 8: FONCTION RÉCUPÉRER DOCUMENT COMPLET
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_full_document(document_id_param bigint)
RETURNS TABLE (
    id bigint,
    file_name text,
    file_path text,
    full_content text,
    metadata jsonb,
    created_at timestamptz
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.file_name,
        d.file_path,
        d.full_content,
        d.metadata,
        d.created_at
    FROM public.documents_full d
    WHERE d.id = document_id_param;
END;
$$;

COMMENT ON FUNCTION public.get_full_document IS 'Récupère un document complet par son ID';

-- ============================================================================
-- ÉTAPE 9: FONCTION SUPPRIMER DOCUMENT
-- ============================================================================

CREATE OR REPLACE FUNCTION public.delete_document_by_path(file_path_param text)
RETURNS TABLE (
    deleted_document_id bigint,
    deleted_chunks_count bigint
)
LANGUAGE plpgsql
AS $$
DECLARE
    doc_id bigint;
    chunks_count bigint;
BEGIN
    -- Trouver le document
    SELECT id INTO doc_id
    FROM public.documents_full
    WHERE file_path = file_path_param;

    IF doc_id IS NULL THEN
        RETURN QUERY SELECT NULL::bigint, 0::bigint;
        RETURN;
    END IF;

    -- Compter les chunks avant suppression
    SELECT COUNT(*) INTO chunks_count
    FROM public.document_chunks
    WHERE document_id = doc_id;

    -- Supprimer le document (CASCADE supprimera les chunks)
    DELETE FROM public.documents_full WHERE id = doc_id;

    RETURN QUERY SELECT doc_id, chunks_count;
END;
$$;

COMMENT ON FUNCTION public.delete_document_by_path IS 'Supprime un document et tous ses chunks par le chemin du fichier';

-- ============================================================================
-- ÉTAPE 10: VUE RÉSUMÉ DES DOCUMENTS
-- ============================================================================

CREATE OR REPLACE VIEW public.documents_summary AS
SELECT
    d.id,
    d.file_name,
    d.file_path,
    d.file_type,
    d.page_count,
    d.word_count,
    d.char_count,
    COUNT(c.id)::integer AS chunk_count,
    d.processing_method,
    d.created_at,
    d.updated_at
FROM public.documents_full d
LEFT JOIN public.document_chunks c ON d.id = c.document_id
GROUP BY d.id, d.file_name, d.file_path, d.file_type, d.page_count,
         d.word_count, d.char_count, d.processing_method, d.created_at, d.updated_at
ORDER BY d.created_at DESC;

COMMENT ON VIEW public.documents_summary IS 'Vue résumée des documents avec nombre de chunks';

-- ============================================================================
-- ÉTAPE 11: PERMISSIONS (SÉCURITÉ)
-- ============================================================================

-- Donner les permissions nécessaires
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.documents_full TO anon, authenticated;
GRANT SELECT ON public.document_chunks TO anon, authenticated;
GRANT SELECT ON public.documents_summary TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.match_document_chunks TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_database_stats TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_full_document TO anon, authenticated;

-- Pour l'insertion (via service_role ou authenticated selon vos besoins)
GRANT INSERT, UPDATE, DELETE ON public.documents_full TO authenticated;
GRANT INSERT, UPDATE, DELETE ON public.document_chunks TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

COMMIT;

-- ============================================================================
-- VÉRIFICATIONS FINALES
-- ============================================================================

-- Afficher les tables créées
DO $$
DECLARE
    table_count int;
    function_count int;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('documents_full', 'document_chunks');

    SELECT COUNT(*) INTO function_count
    FROM information_schema.routines
    WHERE routine_schema = 'public'
    AND routine_name IN ('match_document_chunks', 'get_database_stats',
                         'get_full_document', 'delete_document_by_path');

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ CONFIGURATION TERMINÉE !';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables créées: % / 2', table_count;
    RAISE NOTICE 'Fonctions créées: % / 4', function_count;
    RAISE NOTICE '';

    IF table_count = 2 AND function_count = 4 THEN
        RAISE NOTICE '🎉 Tout est OK ! Prêt à utiliser.';
    ELSE
        RAISE NOTICE '⚠️  Problème détecté. Vérifiez les erreurs ci-dessus.';
    END IF;

    RAISE NOTICE '';
END $$;

-- Tester les statistiques
SELECT * FROM public.get_database_stats();
