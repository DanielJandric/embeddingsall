-- ================================================================
-- MIGRATION : AJOUTER LES COLONNES MANQUANTES
-- ================================================================
-- Ce script ajoute les nouvelles colonnes aux tables existantes
-- Sans supprimer les données
-- ================================================================

-- ================================================================
-- PARTIE 1 : AJOUTER COLONNES MANQUANTES À documents_full
-- ================================================================

-- Classification du document
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS type_document TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS categorie TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS sous_categorie TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS tags TEXT[];

-- Localisation
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS commune TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS canton TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS pays TEXT DEFAULT 'Suisse';
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS code_postal TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS adresse_principale TEXT;

-- Informations financières
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS montant_principal NUMERIC(15,2);
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS devise TEXT DEFAULT 'CHF';
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS montant_min NUMERIC(15,2);
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS montant_max NUMERIC(15,2);

-- Informations temporelles
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS date_document DATE;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS annee_document INTEGER;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS date_debut DATE;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS date_fin DATE;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS periode TEXT;

-- Parties impliquées
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS entite_principale TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS parties_secondaires TEXT[];
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS bailleur TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS locataire TEXT;

-- Informations immobilières
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS type_bien TEXT;
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS surface_m2 NUMERIC(10,2);
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS nombre_pieces NUMERIC(3,1);
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS annee_construction INTEGER;

-- Informations de qualité
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS metadata_completeness_score NUMERIC(5,2);
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS information_richness_score NUMERIC(5,2);
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS confidence_level TEXT;

-- Langue et style
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS langue TEXT DEFAULT 'fr';
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS niveau_formalite TEXT;

-- Full-text search vector
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Informations de traitement
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS extraction_version TEXT DEFAULT '2.0';
ALTER TABLE documents_full ADD COLUMN IF NOT EXISTS last_indexed_at TIMESTAMPTZ;

-- Message de confirmation
DO $$ BEGIN RAISE NOTICE '✅ Colonnes ajoutées à documents_full'; END $$;

-- ================================================================
-- PARTIE 2 : AJOUTER COLONNES MANQUANTES À document_chunks
-- ================================================================

-- Contexte enrichi
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS context_before TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS context_after TEXT;

-- Position dans le document
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS start_position INTEGER;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS end_position INTEGER;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS page_number INTEGER;

-- Structure du document
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS section_title TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS section_level INTEGER;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS paragraph_index INTEGER;

-- Informations sémantiques
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chunk_type TEXT;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS has_tables BOOLEAN DEFAULT FALSE;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS has_numbers BOOLEAN DEFAULT FALSE;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS has_dates BOOLEAN DEFAULT FALSE;
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS has_amounts BOOLEAN DEFAULT FALSE;

-- Entités mentionnées
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS entities_mentioned TEXT[];
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS locations_mentioned TEXT[];

-- Importance
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS importance_score NUMERIC(3,2);

-- Full-text search vector
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Message de confirmation
DO $$ BEGIN RAISE NOTICE '✅ Colonnes ajoutées à document_chunks'; END $$;

-- ================================================================
-- PARTIE 3 : CRÉER INDEX MANQUANTS
-- ================================================================

-- Index pour documents_full
CREATE INDEX IF NOT EXISTS idx_documents_type_document ON documents_full USING btree(type_document);
CREATE INDEX IF NOT EXISTS idx_documents_categorie ON documents_full USING btree(categorie);
CREATE INDEX IF NOT EXISTS idx_documents_commune ON documents_full USING btree(commune);
CREATE INDEX IF NOT EXISTS idx_documents_canton ON documents_full USING btree(canton);
CREATE INDEX IF NOT EXISTS idx_documents_date ON documents_full USING btree(date_document);
CREATE INDEX IF NOT EXISTS idx_documents_annee ON documents_full USING btree(annee_document);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents_full USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_file_name_trgm ON documents_full USING GIN(file_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_documents_type_categorie ON documents_full USING btree(type_document, categorie);
CREATE INDEX IF NOT EXISTS idx_documents_commune_canton ON documents_full USING btree(commune, canton);

-- Index pour document_chunks
CREATE INDEX IF NOT EXISTS idx_chunks_page_number ON document_chunks USING btree(page_number);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_type ON document_chunks USING btree(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_importance ON document_chunks USING btree(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_content_flags ON document_chunks(has_tables, has_numbers, has_dates, has_amounts);

-- Index full-text search (CRUCIAL)
CREATE INDEX IF NOT EXISTS idx_documents_search_vector ON documents_full USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON document_chunks USING GIN(search_vector);

-- Message de confirmation
DO $$ BEGIN RAISE NOTICE '✅ Index créés'; END $$;

-- ================================================================
-- PARTIE 4 : CRÉER NOUVELLES TABLES SI N'EXISTENT PAS
-- ================================================================

-- Table extracted_entities
CREATE TABLE IF NOT EXISTS extracted_entities (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    entity_normalized TEXT,
    context TEXT,
    chunk_ids BIGINT[],
    mention_count INTEGER DEFAULT 1,
    entity_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_document_id ON extracted_entities USING btree(document_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON extracted_entities USING btree(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_value ON extracted_entities USING btree(entity_value);
CREATE INDEX IF NOT EXISTS idx_entities_normalized ON extracted_entities USING btree(entity_normalized);
CREATE INDEX IF NOT EXISTS idx_entities_type_value ON extracted_entities USING btree(entity_type, entity_value);
CREATE INDEX IF NOT EXISTS idx_entities_value_trgm ON extracted_entities USING GIN(entity_value gin_trgm_ops);

-- Table document_tags
CREATE TABLE IF NOT EXISTS document_tags (
    id BIGSERIAL PRIMARY KEY,
    tag_name TEXT NOT NULL UNIQUE,
    tag_category TEXT,
    tag_description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tags_category ON document_tags USING btree(tag_category);
CREATE INDEX IF NOT EXISTS idx_tags_usage ON document_tags USING btree(usage_count DESC);

-- Table document_tag_relations
CREATE TABLE IF NOT EXISTS document_tag_relations (
    document_id BIGINT NOT NULL REFERENCES documents_full(id) ON DELETE CASCADE,
    tag_id BIGINT NOT NULL REFERENCES document_tags(id) ON DELETE CASCADE,
    confidence NUMERIC(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (document_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_tag_relations_document ON document_tag_relations USING btree(document_id);
CREATE INDEX IF NOT EXISTS idx_tag_relations_tag ON document_tag_relations USING btree(tag_id);

-- Table document_relations
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

CREATE INDEX IF NOT EXISTS idx_relations_source ON document_relations USING btree(source_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON document_relations USING btree(target_document_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON document_relations USING btree(relation_type);
CREATE INDEX IF NOT EXISTS idx_relations_similarity ON document_relations USING btree(similarity_score DESC);

-- Message de confirmation
DO $$ BEGIN RAISE NOTICE '✅ Nouvelles tables créées'; END $$;

-- ================================================================
-- PARTIE 5 : FONCTIONS ET TRIGGERS
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

DROP TRIGGER IF EXISTS documents_updated_at_trigger ON documents_full;
CREATE TRIGGER documents_updated_at_trigger
BEFORE UPDATE ON documents_full
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Message de confirmation
DO $$ BEGIN RAISE NOTICE '✅ Fonctions et triggers créés'; END $$;

-- ================================================================
-- PARTIE 6 : FONCTIONS DE RECHERCHE
-- ================================================================

-- Fonction de recherche sémantique améliorée
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

-- Fonction de recherche full-text
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

-- Fonction de recherche hybride
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

-- Message de confirmation
DO $$ BEGIN RAISE NOTICE '✅ Fonctions de recherche créées'; END $$;

-- ================================================================
-- PARTIE 7 : VUES MATÉRIALISÉES
-- ================================================================

-- Vue pour statistiques par catégorie
DROP MATERIALIZED VIEW IF EXISTS stats_by_category CASCADE;
CREATE MATERIALIZED VIEW stats_by_category AS
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

CREATE UNIQUE INDEX idx_stats_category_type ON stats_by_category(categorie, type_document);

-- Vue pour documents par commune
DROP MATERIALIZED VIEW IF EXISTS stats_by_location CASCADE;
CREATE MATERIALIZED VIEW stats_by_location AS
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

CREATE UNIQUE INDEX idx_stats_location ON stats_by_location(canton, commune);

-- Fonction pour rafraîchir les vues
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY stats_by_category;
    REFRESH MATERIALIZED VIEW CONCURRENTLY stats_by_location;
END;
$$ LANGUAGE plpgsql;

-- Message de confirmation
DO $$ BEGIN RAISE NOTICE '✅ Vues matérialisées créées'; END $$;

-- ================================================================
-- VÉRIFICATIONS FINALES
-- ================================================================

-- Vérifier les colonnes de documents_full
SELECT COUNT(*) as nb_colonnes_documents_full
FROM information_schema.columns
WHERE table_name = 'documents_full';

-- Vérifier les colonnes de document_chunks
SELECT COUNT(*) as nb_colonnes_document_chunks
FROM information_schema.columns
WHERE table_name = 'document_chunks';

-- Vérifier les tables créées
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- ================================================================
-- MESSAGE FINAL
-- ================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
    RAISE NOTICE '✅ MIGRATION TERMINÉE AVEC SUCCÈS !';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Nouvelles colonnes ajoutées à documents_full';
    RAISE NOTICE '📊 Nouvelles colonnes ajoutées à document_chunks';
    RAISE NOTICE '🆕 Nouvelles tables créées (extracted_entities, document_tags, etc.)';
    RAISE NOTICE '📇 Index créés pour performances optimales';
    RAISE NOTICE '🔍 Fonctions de recherche installées';
    RAISE NOTICE '📈 Vues matérialisées créées';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 PROCHAINE ÉTAPE : Réuploader les documents avec upload_maximal.py';
    RAISE NOTICE '   pour remplir toutes les nouvelles colonnes !';
    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;
