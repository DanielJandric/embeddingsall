-- =============================================================================
-- Migration: Extend metadata capacity and search capabilities
-- Target: Supabase public schema (documents_full, document_chunks)
-- Safe to re-run (IF NOT EXISTS guards)
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Extensions (optional but recommended)
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ---------------------------------------------------------------------------
-- documents_full: richer metadata fields
-- ---------------------------------------------------------------------------
ALTER TABLE public.documents_full
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS authors TEXT[] DEFAULT '{}'::text[],
    ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}'::text[],
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS source_id TEXT,
    ADD COLUMN IF NOT EXISTS language TEXT,
    ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS checksum TEXT;

-- Unique checksum when provided (skip NULLs)
CREATE UNIQUE INDEX IF NOT EXISTS documents_full_checksum_unique_idx
ON public.documents_full (checksum) WHERE checksum IS NOT NULL;

-- Array and common field indexes
CREATE INDEX IF NOT EXISTS documents_full_tags_idx
ON public.documents_full USING GIN (tags);

CREATE INDEX IF NOT EXISTS documents_full_authors_idx
ON public.documents_full USING GIN (authors);

CREATE INDEX IF NOT EXISTS documents_full_language_idx
ON public.documents_full (language);

CREATE INDEX IF NOT EXISTS documents_full_published_at_idx
ON public.documents_full (published_at DESC);

CREATE INDEX IF NOT EXISTS documents_full_source_url_idx
ON public.documents_full (source_url);

-- Fuzzy search on file_name
CREATE INDEX IF NOT EXISTS documents_full_file_name_trgm_idx
ON public.documents_full USING GIN (file_name gin_trgm_ops);

-- Full-text search vectors (generated)
ALTER TABLE public.documents_full
    ADD COLUMN IF NOT EXISTS tsv_full tsvector
    GENERATED ALWAYS AS (
        to_tsvector('simple', unaccent(coalesce(full_content, '')))
    ) STORED;

CREATE INDEX IF NOT EXISTS documents_full_tsv_full_idx
ON public.documents_full USING GIN (tsv_full);

-- ---------------------------------------------------------------------------
-- document_chunks: richer per-chunk metadata
-- ---------------------------------------------------------------------------
ALTER TABLE public.document_chunks
    ADD COLUMN IF NOT EXISTS page_number INT,
    ADD COLUMN IF NOT EXISTS section_title TEXT,
    ADD COLUMN IF NOT EXISTS bbox JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS tsv_chunk tsvector
        GENERATED ALWAYS AS (
            to_tsvector('simple', unaccent(coalesce(chunk_content, '')))
        ) STORED;

CREATE INDEX IF NOT EXISTS document_chunks_page_number_idx
ON public.document_chunks (document_id, page_number, chunk_index);

CREATE INDEX IF NOT EXISTS document_chunks_tsv_chunk_idx
ON public.document_chunks USING GIN (tsv_chunk);

-- ---------------------------------------------------------------------------
-- Advanced vector + metadata + keyword search
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.match_document_chunks_advanced(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    filter_tags text[] DEFAULT NULL,
    filter_language text DEFAULT NULL,
    filter_file_type text DEFAULT NULL,
    from_date timestamptz DEFAULT NULL,
    to_date timestamptz DEFAULT NULL,
    search_text text DEFAULT NULL
)
RETURNS TABLE (
    chunk_id bigint,
    document_id bigint,
    file_name text,
    file_path text,
    chunk_index int,
    page_number int,
    section_title text,
    chunk_content text,
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
        c.page_number,
        c.section_title,
        c.chunk_content,
        (1 - (c.embedding <=> query_embedding))::float AS similarity,
        c.chunk_metadata,
        d.metadata AS document_metadata
    FROM public.document_chunks c
    JOIN public.documents_full d ON c.document_id = d.id
    WHERE
        c.embedding IS NOT NULL
        AND (1 - (c.embedding <=> query_embedding)) > match_threshold
        AND (filter_tags IS NULL OR (d.tags && filter_tags))
        AND (filter_language IS NULL OR d.language = filter_language)
        AND (filter_file_type IS NULL OR d.file_type = filter_file_type)
        AND (from_date IS NULL OR d.created_at >= from_date)
        AND (to_date IS NULL OR d.created_at <= to_date)
        AND (
            search_text IS NULL
            OR d.tsv_full @@ plainto_tsquery('simple', unaccent(search_text))
            OR c.tsv_chunk @@ plainto_tsquery('simple', unaccent(search_text))
        )
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMIT;

-- =============================================================================
-- Notes:
-- - JSONB 'metadata' columns remain the primary catch-all for arbitrary fields.
-- - New explicit columns (tags, authors, language, etc.) are for fast filters.
-- - Use match_document_chunks_advanced() to combine vector similarity, metadata
--   filters and keyword search across both full document and chunk text.
-- =============================================================================


