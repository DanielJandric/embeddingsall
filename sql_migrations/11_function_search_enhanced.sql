-- ================================================================
-- ÉTAPE 11: Fonction de Recherche Sémantique Améliorée
-- ================================================================

CREATE OR REPLACE FUNCTION match_document_chunks_enhanced(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    filter_type_document text DEFAULT NULL,
    filter_categorie text DEFAULT NULL,
    filter_commune text DEFAULT NULL,
    filter_canton text DEFAULT NULL,
    filter_tags text[] DEFAULT NULL,
    min_date date DEFAULT NULL,
    max_date date DEFAULT NULL
)
RETURNS TABLE (
    chunk_id bigint,
    document_id bigint,
    file_name text,
    file_path text,
    chunk_index integer,
    chunk_content text,
    context_before text,
    context_after text,
    section_title text,
    page_number integer,
    full_document_content text,
    similarity float,
    chunk_metadata jsonb,
    document_metadata jsonb,
    type_document text,
    categorie text,
    commune text,
    canton text,
    date_document date,
    montant_principal numeric,
    tags text[],
    importance_score numeric
)
LANGUAGE plpgsql
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
        c.context_before,
        c.context_after,
        c.section_title,
        c.page_number,
        d.full_content AS full_document_content,
        1 - (c.embedding <=> query_embedding) AS similarity,
        c.chunk_metadata,
        d.metadata AS document_metadata,
        d.type_document,
        d.categorie,
        d.commune,
        d.canton,
        d.date_document,
        d.montant_principal,
        d.tags,
        c.importance_score
    FROM
        document_chunks c
    INNER JOIN
        documents_full d ON c.document_id = d.id
    WHERE
        1 - (c.embedding <=> query_embedding) > match_threshold
        AND (filter_type_document IS NULL OR d.type_document = filter_type_document)
        AND (filter_categorie IS NULL OR d.categorie = filter_categorie)
        AND (filter_commune IS NULL OR d.commune = filter_commune)
        AND (filter_canton IS NULL OR d.canton = filter_canton)
        AND (filter_tags IS NULL OR d.tags && filter_tags)
        AND (min_date IS NULL OR d.date_document >= min_date)
        AND (max_date IS NULL OR d.date_document <= max_date)
    ORDER BY
        similarity DESC,
        c.importance_score DESC NULLS LAST
    LIMIT match_count;
END;
$$;

-- Vérification
SELECT proname, pronargs FROM pg_proc WHERE proname = 'match_document_chunks_enhanced';
