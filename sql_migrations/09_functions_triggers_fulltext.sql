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

-- Vérification
SELECT
    tgname as trigger_name,
    tgrelid::regclass as table_name
FROM pg_trigger
WHERE tgname LIKE '%search_vector%' OR tgname LIKE '%updated_at%';
