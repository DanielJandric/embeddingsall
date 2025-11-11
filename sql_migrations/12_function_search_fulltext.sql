-- ================================================================
-- ÉTAPE 12: Fonction de Recherche Full-Text
-- ================================================================

CREATE OR REPLACE FUNCTION search_documents_fulltext(
    search_query text,
    match_count int DEFAULT 20,
    filter_type_document text DEFAULT NULL,
    filter_categorie text DEFAULT NULL
)
RETURNS TABLE (
    document_id bigint,
    file_name text,
    file_path text,
    type_document text,
    categorie text,
    commune text,
    date_document date,
    rank real,
    headline text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id AS document_id,
        d.file_name,
        d.file_path,
        d.type_document,
        d.categorie,
        d.commune,
        d.date_document,
        ts_rank(d.search_vector, websearch_to_tsquery('french', search_query)) AS rank,
        ts_headline('french', d.full_content, websearch_to_tsquery('french', search_query),
            'MaxWords=50, MinWords=25, MaxFragments=3') AS headline
    FROM
        documents_full d
    WHERE
        d.search_vector @@ websearch_to_tsquery('french', search_query)
        AND (filter_type_document IS NULL OR d.type_document = filter_type_document)
        AND (filter_categorie IS NULL OR d.categorie = filter_categorie)
    ORDER BY
        rank DESC
    LIMIT match_count;
END;
$$;

-- Vérification
SELECT proname, pronargs FROM pg_proc WHERE proname = 'search_documents_fulltext';
