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

-- Vérification
SELECT matviewname FROM pg_matviews WHERE matviewname IN ('stats_by_category', 'stats_by_location');
