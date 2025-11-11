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

-- Vérification
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'documents_full'
ORDER BY indexname;
