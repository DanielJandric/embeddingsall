-- ================================================================
-- ÉTAPE 13: Fonction de Recherche Hybride
-- ================================================================

CREATE OR REPLACE FUNCTION search_hybrid(
    search_text text,
    query_embedding vector(1536),
    match_count int DEFAULT 10,
    semantic_weight float DEFAULT 0.6,
    fulltext_weight float DEFAULT 0.4
)
RETURNS TABLE (
    chunk_id bigint,
    document_id bigint,
    file_name text,
    chunk_content text,
    combined_score float,
    semantic_score float,
    fulltext_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH semantic_results AS (
        SELECT
            c.id AS chunk_id,
            c.document_id,
            1 - (c.embedding <=> query_embedding) AS score
        FROM document_chunks c
        ORDER BY score DESC
        LIMIT match_count * 2
    ),
    fulltext_results AS (
        SELECT
            c.id AS chunk_id,
            c.document_id,
            ts_rank(c.search_vector, websearch_to_tsquery('french', search_text)) AS score
        FROM document_chunks c
        WHERE c.search_vector @@ websearch_to_tsquery('french', search_text)
        ORDER BY score DESC
        LIMIT match_count * 2
    )
    SELECT
        COALESCE(s.chunk_id, f.chunk_id) AS chunk_id,
        COALESCE(s.document_id, f.document_id) AS document_id,
        d.file_name,
        c.chunk_content,
        (COALESCE(s.score, 0) * semantic_weight + COALESCE(f.score, 0) * fulltext_weight) AS combined_score,
        COALESCE(s.score, 0) AS semantic_score,
        COALESCE(f.score, 0) AS fulltext_score
    FROM
        semantic_results s
    FULL OUTER JOIN
        fulltext_results f ON s.chunk_id = f.chunk_id
    INNER JOIN
        document_chunks c ON COALESCE(s.chunk_id, f.chunk_id) = c.id
    INNER JOIN
        documents_full d ON c.document_id = d.id
    ORDER BY
        combined_score DESC
    LIMIT match_count;
END;
$$;

-- Vérification
SELECT proname, pronargs FROM pg_proc WHERE proname = 'search_hybrid';
