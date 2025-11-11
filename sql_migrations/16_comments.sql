-- ================================================================
-- ÉTAPE 16: Commentaires sur les Tables (Optionnel)
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

-- Vérification
SELECT
    tablename,
    obj_description((schemaname||'.'||tablename)::regclass, 'pg_class') as table_comment
FROM pg_tables
WHERE tablename IN ('documents_full', 'document_chunks', 'extracted_entities', 'document_tags', 'document_relations');
