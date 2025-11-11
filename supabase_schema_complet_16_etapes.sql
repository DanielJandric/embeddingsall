-- ================================================================
-- SCHÉMA COMPLET - 16 ÉTAPES EN UN SEUL FICHIER
-- ================================================================
-- À exécuter dans Supabase SQL Editor
-- Copier-coller TOUT ce fichier et exécuter
-- ================================================================

-- ================================================================
-- ÉTAPE 1: Extensions PostgreSQL
-- ================================================================

-- Extension pour vecteurs (embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- Extension pour recherche trigram (fuzzy search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Vérification
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');

-- ================================================================
-- ÉTAPE 2: Table documents_full
-- ================================================================

CREATE TABLE IF NOT EXISTS documents_full (
    -- Identifiants
    id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_type TEXT,

    -- Contenu
    full_content TEXT NOT NULL,

    -- Statistiques de base
    file_size_bytes BIGINT DEFAULT 0,
    page_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    char_count INTEGER DEFAULT 0,

    -- Classification du document
    type_document TEXT,
    categorie TEXT,
    sous_categorie TEXT,
    tags TEXT[],

    -- Localisation
    commune TEXT,
    canton TEXT,
    pays TEXT DEFAULT 'Suisse',
    code_postal TEXT,
    adresse_principale TEXT,

    -- Informations financières
    montant_principal NUMERIC(15,2),
    devise TEXT DEFAULT 'CHF',
    montant_min NUMERIC(15,2),
    montant_max NUMERIC(15,2),

    -- Informations temporelles
    date_document DATE,
    annee_document INTEGER,
    date_debut DATE,
    date_fin DATE,
    periode TEXT,

    -- Parties impliquées
    entite_principale TEXT,
    parties_secondaires TEXT[],
    bailleur TEXT,
    locataire TEXT,

    -- Informations immobilières
    type_bien TEXT,
    surface_m2 NUMERIC(10,2),
    nombre_pieces NUMERIC(3,1),
    annee_construction INTEGER,

    -- Informations de qualité
    metadata_completeness_score NUMERIC(5,2),
    information_richness_score NUMERIC(5,2),
    confidence_level TEXT,

    -- Langue et style
    langue TEXT DEFAULT 'fr',
    niveau_formalite TEXT,

    -- Full-text search vector
    search_vector tsvector,

    -- Métadonnées complètes (JSONB)
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Informations de traitement
    processing_method TEXT,
    extraction_version TEXT DEFAULT '2.0',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_indexed_at TIMESTAMPTZ
);

-- ================================================================
-- ÉTAPE 3: Index pour documents_full
-- ================================================================

-- Index btree standards
CREATE INDEX IF NOT EXISTS idx_documents_file_name ON documents_full USING btree(file_name);
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents_full USING btree(file_type);
CREATE INDEX IF NOT EXISTS idx_documents_type_document ON documents_full USING btree(type_document);
CREATE INDEX IF NOT EXISTS idx_documents_categorie ON documents_full USING btree(categorie);
CREATE INDEX IF NOT EXISTS idx_documents_commune ON documents_full USING btree(commune);
CREATE INDEX IF NOT EXISTS idx_documents_canton ON documents_full USING btree(canton);
CREATE INDEX IF NOT EXISTS idx_documents_date ON documents_full USING btree(date_document);
CREATE INDEX IF NOT EXISTS idx_documents_annee ON documents_full USING btree(annee_document);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents_full USING btree(created_at DESC);

-- Index GIN pour arrays et JSONB
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents_full USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents_full USING GIN(metadata);

-- Index trigram pour recherche fuzzy
CREATE INDEX IF NOT EXISTS idx_documents_file_name_trgm ON documents_full USING GIN(file_name gin_trgm_ops);

-- Index composites pour requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_documents_type_categorie ON documents_full USING btree(type_document, categorie);
CREATE INDEX IF NOT EXISTS idx_documents_commune_canton ON documents_full USING btree(commune, canton);

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

-- ================================================================
-- ÉTAPE 5: Index pour document_chunks
-- ================================================================

-- Index btree standards
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks USING btree(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON document_chunks USING btree(chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_page_number ON document_chunks USING btree(page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_type ON document_chunks USING btree(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_importance ON document_chunks USING btree(importance_score DESC);

-- Index pour filtrage avec flags booléens
CREATE INDEX IF NOT EXISTS idx_chunks_content_flags ON document_chunks(has_tables, has_numbers, has_dates, has_amounts);

-- Index vectoriel HNSW pour recherche sémantique rapide
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

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

-- ================================================================
-- ÉTAPE 7: Tables de Tags
-- ================================================================

-- Table des tags
CREATE TABLE IF NOT EXISTS document_tags (
    id BIGSERIAL PRIMARY KEY,
    tag_name TEXT NOT NULL UNIQUE,
    tag_category TEXT,
    tag_description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour document_tags
CREATE INDEX IF NOT EXISTS idx_tags_category ON document_tags USING btree(tag_category);
CREATE INDEX IF NOT EXISTS idx_tags_usage ON document_tags USING btree(usage_count DESC);

-- Table de relation many-to-many
CREATE TABLE IF NOT EXISTS document_tag_relations (
    document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    tag_id BIGINT NOT NULL REFERENCES document_tags(id) ON DELETE CASCADE,
    confidence NUMERIC(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (document_id, tag_id)
);

-- Index pour document_tag_relations
CREATE INDEX IF NOT EXISTS idx_tag_relations_document ON document_tag_relations USING btree(document_id);
CREATE INDEX IF NOT EXISTS idx_tag_relations_tag ON document_tag_relations USING btree(tag_id);

-- ================================================================
-- ÉTAPE 8: Table document_relations
-- ================================================================

CREATE TABLE IF NOT EXISTS document_relations (
    id BIGSERIAL PRIMARY KEY,
    source_document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    target_document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,

    relation_type TEXT NOT NULL,
    similarity_score NUMERIC(5,4),

    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(source_document_id, target_document_id, relation_type)
);

-- Index pour document_relations
CREATE INDEX IF NOT EXISTS idx_relations_source ON document_relations USING btree(source_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON document_relations USING btree(target_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON document_relations USING btree(relation_type);
CREATE INDEX IF NOT EXISTS idx_relations_similarity ON document_relations USING btree(similarity_score DESC);

-- ================================================================
-- ÉTAPE 9: Fonctions et Triggers pour Full-Text Search
-- ================================================================

-- Fonction pour mettre à jour le search_vector des documents
CREATE OR REPLACE FUNCTION documents_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french', COALESCE(NEW.file_name, '')), 'A') ||
        setweight(to_tsvector('french', COALESCE(NEW.type_document, '')), 'A') ||
        setweight(to_tsvector('french', COALESCE(NEW.categorie, '')), 'B') ||
        setweight(to_tsvector('french', COALESCE(NEW.commune, '')), 'B') ||
        setweight(to_tsvector('french', COALESCE(NEW.entite_principale, '')), 'B') ||
        setweight(to_tsvector('french', COALESCE(NEW.full_content, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour mise à jour automatique du search_vector (documents)
DROP TRIGGER IF EXISTS documents_search_vector_trigger ON documents_full;
CREATE TRIGGER documents_search_vector_trigger
BEFORE INSERT OR UPDATE OF file_name, type_document, categorie, commune, entite_principale, full_content
ON documents_full
FOR EACH ROW
EXECUTE FUNCTION documents_search_vector_update();

-- Fonction pour mettre à jour le search_vector des chunks
CREATE OR REPLACE FUNCTION chunks_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('french', COALESCE(NEW.section_title, '')), 'A') ||
        setweight(to_tsvector('french', COALESCE(NEW.chunk_content, '')), 'B') ||
        setweight(to_tsvector('french', COALESCE(NEW.context_before, '')), 'C') ||
        setweight(to_tsvector('french', COALESCE(NEW.context_after, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour chunks
DROP TRIGGER IF EXISTS chunks_search_vector_trigger ON document_chunks;
CREATE TRIGGER chunks_search_vector_trigger
BEFORE INSERT OR UPDATE OF chunk_content, section_title, context_before, context_after
ON document_chunks
FOR EACH ROW
EXECUTE FUNCTION chunks_search_vector_update();

-- Fonction pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour updated_at
DROP TRIGGER IF EXISTS documents_updated_at_trigger ON documents_full;
CREATE TRIGGER documents_updated_at_trigger
BEFORE UPDATE ON documents_full
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- ÉTAPE 10: Index Full-Text Search
-- ================================================================

-- Index full-text search pour documents (CRUCIAL pour LLM)
CREATE INDEX IF NOT EXISTS idx_documents_search_vector ON documents_full USING GIN(search_vector);

-- Index full-text search pour chunks
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON document_chunks USING GIN(search_vector);

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

-- ================================================================
-- ÉTAPE 14: Vues Matérialisées pour Statistiques
-- ================================================================

-- Vue pour statistiques par catégorie
CREATE MATERIALIZED VIEW IF NOT EXISTS stats_by_category AS
SELECT
    categorie,
    type_document,
    COUNT(*) as document_count,
    AVG(metadata_completeness_score) as avg_completeness,
    AVG(information_richness_score) as avg_richness,
    MIN(date_document) as earliest_date,
    MAX(date_document) as latest_date,
    SUM(file_size_bytes) as total_size_bytes
FROM documents_full
WHERE categorie IS NOT NULL
GROUP BY categorie, type_document;

-- Index unique pour vue matérialisée
CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_category_type ON stats_by_category(categorie, type_document);

-- Vue pour documents par commune
CREATE MATERIALIZED VIEW IF NOT EXISTS stats_by_location AS
SELECT
    canton,
    commune,
    COUNT(*) as document_count,
    COUNT(DISTINCT type_document) as document_types,
    AVG(montant_principal) as avg_montant,
    SUM(montant_principal) as total_montant
FROM documents_full
WHERE commune IS NOT NULL
GROUP BY canton, commune;

-- Index unique pour vue matérialisée
CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_location ON stats_by_location(canton, commune);

-- ================================================================
-- ÉTAPE 15: Fonction pour Rafraîchir les Vues Matérialisées
-- ================================================================

CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY stats_by_category;
    REFRESH MATERIALIZED VIEW CONCURRENTLY stats_by_location;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- ÉTAPE 16: Commentaires (Optionnel)
-- ================================================================

COMMENT ON TABLE documents_full IS 'Documents complets avec métadonnées enrichies pour recherche optimisée par LLM';
COMMENT ON TABLE document_chunks IS 'Chunks de documents avec contexte, embeddings et métadonnées sémantiques';
COMMENT ON TABLE extracted_entities IS 'Entités extraites des documents (entreprises, personnes, lieux)';
COMMENT ON TABLE document_tags IS 'Tags et catégories disponibles pour classification';
COMMENT ON TABLE document_relations IS 'Relations entre documents (similarité, références)';

COMMENT ON COLUMN documents_full.search_vector IS 'Vecteur de recherche full-text pondéré par importance';
COMMENT ON COLUMN documents_full.metadata_completeness_score IS 'Score de complétude des métadonnées (0-100)';
COMMENT ON COLUMN document_chunks.importance_score IS 'Score d''importance du chunk basé sur son contenu';
COMMENT ON COLUMN document_chunks.context_before IS 'Contexte précédant le chunk pour meilleure compréhension';
COMMENT ON COLUMN document_chunks.context_after IS 'Contexte suivant le chunk pour meilleure compréhension';

-- ================================================================
-- VÉRIFICATIONS FINALES
-- ================================================================

-- Vérifier les tables créées
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Vérifier les fonctions créées
SELECT proname FROM pg_proc WHERE proname IN (
    'match_document_chunks_enhanced',
    'search_documents_fulltext',
    'search_hybrid',
    'refresh_all_materialized_views',
    'documents_search_vector_update',
    'chunks_search_vector_update',
    'update_updated_at_column'
);

-- Vérifier les vues matérialisées
SELECT matviewname FROM pg_matviews WHERE schemaname = 'public';

-- Vérifier les triggers
SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE tgname LIKE '%search_vector%' OR tgname LIKE '%updated_at%';

-- ================================================================
-- FIN DU SCHÉMA COMPLET
-- ================================================================

-- Message de succès
DO $$
BEGIN
    RAISE NOTICE '✅ SCHÉMA COMPLET INSTALLÉ AVEC SUCCÈS !';
    RAISE NOTICE '📊 Tables créées: documents_full, document_chunks, extracted_entities, document_tags, document_tag_relations, document_relations';
    RAISE NOTICE '🔍 Fonctions créées: match_document_chunks_enhanced, search_documents_fulltext, search_hybrid, refresh_all_materialized_views';
    RAISE NOTICE '📈 Vues matérialisées: stats_by_category, stats_by_location';
    RAISE NOTICE '🚀 Prêt pour upload des documents avec upload_maximal.py !';
END $$;
