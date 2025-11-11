-- =============================================================================
-- Supabase Real Estate Enrichment Migration
-- Adds comprehensive real-estate metadata, search vectors, GIN/TRGM indexes,
-- auxiliary tables (entities/tags/relations), and search functions.
-- Safe to re-run (IF NOT EXISTS guards).
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- documents_full: add real-estate and business fields
-- -----------------------------------------------------------------------------
ALTER TABLE public.documents_full
    ADD COLUMN IF NOT EXISTS type_document TEXT,
    ADD COLUMN IF NOT EXISTS categorie TEXT,
    ADD COLUMN IF NOT EXISTS sous_categorie TEXT,
    ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}'::text[],
    ADD COLUMN IF NOT EXISTS commune TEXT,
    ADD COLUMN IF NOT EXISTS canton TEXT,
    ADD COLUMN IF NOT EXISTS pays TEXT DEFAULT 'Suisse',
    ADD COLUMN IF NOT EXISTS code_postal TEXT,
    ADD COLUMN IF NOT EXISTS adresse_principale TEXT,
    ADD COLUMN IF NOT EXISTS montant_principal NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS devise TEXT DEFAULT 'CHF',
    ADD COLUMN IF NOT EXISTS montant_min NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS montant_max NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS date_document DATE,
    ADD COLUMN IF NOT EXISTS annee_document INTEGER,
    ADD COLUMN IF NOT EXISTS date_debut DATE,
    ADD COLUMN IF NOT EXISTS date_fin DATE,
    ADD COLUMN IF NOT EXISTS periode TEXT,
    ADD COLUMN IF NOT EXISTS entite_principale TEXT,
    ADD COLUMN IF NOT EXISTS parties_secondaires TEXT[],
    ADD COLUMN IF NOT EXISTS bailleur TEXT,
    ADD COLUMN IF NOT EXISTS locataire TEXT,
    ADD COLUMN IF NOT EXISTS type_bien TEXT,
    ADD COLUMN IF NOT EXISTS surface_m2 NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS nombre_pieces NUMERIC(3,1),
    ADD COLUMN IF NOT EXISTS annee_construction INTEGER,
    ADD COLUMN IF NOT EXISTS metadata_completeness_score NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS information_richness_score NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS confidence_level TEXT,
    ADD COLUMN IF NOT EXISTS langue TEXT DEFAULT 'fr',
    ADD COLUMN IF NOT EXISTS niveau_formalite TEXT,
    ADD COLUMN IF NOT EXISTS extraction_version TEXT DEFAULT '2.0',
    ADD COLUMN IF NOT EXISTS last_indexed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS checksum TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS documents_full_checksum_unique_idx
ON public.documents_full (checksum) WHERE checksum IS NOT NULL;

-- TRGM fuzzy search and arrays
CREATE INDEX IF NOT EXISTS idx_documents_file_name_trgm
ON public.documents_full USING GIN (file_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_documents_tags ON public.documents_full USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_type_categorie ON public.documents_full (type_document, categorie);
CREATE INDEX IF NOT EXISTS idx_documents_commune ON public.documents_full (commune);
CREATE INDEX IF NOT EXISTS idx_documents_canton ON public.documents_full (canton);
CREATE INDEX IF NOT EXISTS idx_documents_date ON public.documents_full (date_document);
CREATE INDEX IF NOT EXISTS idx_documents_annee ON public.documents_full (annee_document);

-- Full text search vector (French, with unaccent)
ALTER TABLE public.documents_full
    ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE OR REPLACE FUNCTION public.documents_search_vector_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french', unaccent(coalesce(NEW.file_name, ''))), 'A') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.type_document, ''))), 'A') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.categorie, ''))), 'B') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.commune, ''))), 'B') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.entite_principale, ''))), 'B') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.full_content, ''))), 'C');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS documents_search_vector_trigger ON public.documents_full;
CREATE TRIGGER documents_search_vector_trigger
BEFORE INSERT OR UPDATE OF file_name, type_document, categorie, commune, entite_principale, full_content
ON public.documents_full
FOR EACH ROW
EXECUTE FUNCTION public.documents_search_vector_update();

CREATE INDEX IF NOT EXISTS idx_documents_search_vector
ON public.documents_full USING GIN (search_vector);

-- -----------------------------------------------------------------------------
-- document_chunks: contextual and semantic fields
-- -----------------------------------------------------------------------------
ALTER TABLE public.document_chunks
    ADD COLUMN IF NOT EXISTS context_before TEXT,
    ADD COLUMN IF NOT EXISTS context_after TEXT,
    ADD COLUMN IF NOT EXISTS start_position INTEGER,
    ADD COLUMN IF NOT EXISTS end_position INTEGER,
    ADD COLUMN IF NOT EXISTS page_number INTEGER,
    ADD COLUMN IF NOT EXISTS section_title TEXT,
    ADD COLUMN IF NOT EXISTS section_level INTEGER,
    ADD COLUMN IF NOT EXISTS paragraph_index INTEGER,
    ADD COLUMN IF NOT EXISTS chunk_type TEXT,
    ADD COLUMN IF NOT EXISTS has_tables BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS has_numbers BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS has_dates BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS has_amounts BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS entities_mentioned TEXT[],
    ADD COLUMN IF NOT EXISTS locations_mentioned TEXT[],
    ADD COLUMN IF NOT EXISTS importance_score NUMERIC(3,2),
    ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE INDEX IF NOT EXISTS idx_chunks_page_number ON public.document_chunks (page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_type ON public.document_chunks (chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_importance ON public.document_chunks (importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_content_flags
ON public.document_chunks (has_tables, has_numbers, has_dates, has_amounts);

CREATE OR REPLACE FUNCTION public.chunks_search_vector_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french', unaccent(coalesce(NEW.section_title, ''))), 'A') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.chunk_content, ''))), 'B') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.context_before, ''))), 'C') ||
        setweight(to_tsvector('french', unaccent(coalesce(NEW.context_after, ''))), 'C');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS chunks_search_vector_trigger ON public.document_chunks;
CREATE TRIGGER chunks_search_vector_trigger
BEFORE INSERT OR UPDATE OF chunk_content, section_title, context_before, context_after
ON public.document_chunks
FOR EACH ROW
EXECUTE FUNCTION public.chunks_search_vector_update();

CREATE INDEX IF NOT EXISTS idx_chunks_search_vector
ON public.document_chunks USING GIN (search_vector);

-- -----------------------------------------------------------------------------
-- Auxiliary tables for entities and tags
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.extracted_entities (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES public.documents_full(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    entity_normalized TEXT,
    context TEXT,
    chunk_ids BIGINT[],
    mention_count INTEGER DEFAULT 1,
    entity_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_document_id ON public.extracted_entities (document_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON public.extracted_entities (entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_value ON public.extracted_entities (entity_value);
CREATE INDEX IF NOT EXISTS idx_entities_normalized ON public.extracted_entities (entity_normalized);
CREATE INDEX IF NOT EXISTS idx_entities_value_trgm ON public.extracted_entities USING GIN (entity_value gin_trgm_ops);

CREATE TABLE IF NOT EXISTS public.document_tags (
    id BIGSERIAL PRIMARY KEY,
    tag_name TEXT NOT NULL UNIQUE,
    tag_category TEXT,
    tag_description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tags_category ON public.document_tags (tag_category);
CREATE INDEX IF NOT EXISTS idx_tags_usage ON public.document_tags (usage_count DESC);

CREATE TABLE IF NOT EXISTS public.document_tag_relations (
    document_id BIGINT NOT NULL REFERENCES public.documents_full(id) ON DELETE CASCADE,
    tag_id BIGINT NOT NULL REFERENCES public.document_tags(id) ON DELETE CASCADE,
    confidence NUMERIC(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (document_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_tag_relations_document ON public.document_tag_relations (document_id);
CREATE INDEX IF NOT EXISTS idx_tag_relations_tag ON public.document_tag_relations (tag_id);

-- Document-to-document relations
CREATE TABLE IF NOT EXISTS public.document_relations (
    id BIGSERIAL PRIMARY KEY,
    source_document_id BIGINT NOT NULL REFERENCES public.documents_full(id) ON DELETE CASCADE,
    target_document_id BIGINT NOT NULL REFERENCES public.documents_full(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    similarity_score NUMERIC(5,4),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_document_id, target_document_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_relations_source ON public.document_relations (source_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON public.document_relations (target_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON public.document_relations (relation_type);
CREATE INDEX IF NOT EXISTS idx_relations_similarity ON public.document_relations (similarity_score DESC);

-- -----------------------------------------------------------------------------
-- Full-text and hybrid search functions
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.search_documents_fulltext(
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
    FROM public.documents_full d
    WHERE
        d.search_vector @@ websearch_to_tsquery('french', search_query)
        AND (filter_type_document IS NULL OR d.type_document = filter_type_document)
        AND (filter_categorie IS NULL OR d.categorie = filter_categorie)
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.match_document_chunks_enhanced(
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
        (1 - (c.embedding <=> query_embedding))::float AS similarity,
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
    FROM public.document_chunks c
    INNER JOIN public.documents_full d ON c.document_id = d.id
    WHERE
        c.embedding IS NOT NULL
        AND (1 - (c.embedding <=> query_embedding)) > match_threshold
        AND (filter_type_document IS NULL OR d.type_document = filter_type_document)
        AND (filter_categorie IS NULL OR d.categorie = filter_categorie)
        AND (filter_commune IS NULL OR d.commune = filter_commune)
        AND (filter_canton IS NULL OR d.canton = filter_canton)
        AND (filter_tags IS NULL OR d.tags && filter_tags)
        AND (min_date IS NULL OR d.date_document >= min_date)
        AND (max_date IS NULL OR d.date_document <= max_date)
    ORDER BY similarity DESC, c.importance_score DESC NULLS LAST
    LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.search_hybrid(
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
        SELECT c.id AS chunk_id, c.document_id, (1 - (c.embedding <=> query_embedding)) AS score
        FROM public.document_chunks c
        WHERE c.embedding IS NOT NULL
        ORDER BY score DESC
        LIMIT match_count * 2
    ),
    fulltext_results AS (
        SELECT c.id AS chunk_id, c.document_id,
               ts_rank(c.search_vector, websearch_to_tsquery('french', search_text)) AS score
        FROM public.document_chunks c
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
    FROM semantic_results s
    FULL OUTER JOIN fulltext_results f ON s.chunk_id = f.chunk_id
    INNER JOIN public.document_chunks c ON COALESCE(s.chunk_id, f.chunk_id) = c.id
    INNER JOIN public.documents_full d ON c.document_id = d.id
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- -----------------------------------------------------------------------------
-- Materialized views (optional analytics)
-- -----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS public.stats_by_category CASCADE;
CREATE MATERIALIZED VIEW public.stats_by_category AS
SELECT
    categorie,
    type_document,
    COUNT(*) as document_count,
    AVG(metadata_completeness_score) as avg_completeness,
    AVG(information_richness_score) as avg_richness,
    MIN(date_document) as earliest_date,
    MAX(date_document) as latest_date,
    SUM(file_size_bytes) as total_size_bytes
FROM public.documents_full
WHERE categorie IS NOT NULL
GROUP BY categorie, type_document;

CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_category_type
ON public.stats_by_category(categorie, type_document);

DROP MATERIALIZED VIEW IF EXISTS public.stats_by_location CASCADE;
CREATE MATERIALIZED VIEW public.stats_by_location AS
SELECT
    canton,
    commune,
    COUNT(*) as document_count,
    COUNT(DISTINCT type_document) as document_types,
    AVG(montant_principal) as avg_montant,
    SUM(montant_principal) as total_montant
FROM public.documents_full
WHERE commune IS NOT NULL
GROUP BY canton, commune;

CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_location
ON public.stats_by_location(canton, commune);

-- Refresh helper
CREATE OR REPLACE FUNCTION public.refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.stats_by_category;
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.stats_by_location;
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- =============================================================================
-- After running:
--   SELECT * FROM public.get_database_stats();
--   SELECT * FROM public.stats_by_category LIMIT 10;
--   SELECT * FROM public.stats_by_location LIMIT 10;
-- =============================================================================


