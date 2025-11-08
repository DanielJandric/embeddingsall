-- Script de configuration de Supabase pour le système d'embeddings
-- Exécutez ce script dans l'éditeur SQL de Supabase

-- 1. Activer l'extension vector pour la recherche vectorielle
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Créer la table documents
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- Dimension pour text-embedding-3-small
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Créer un index pour la recherche vectorielle (IVFFlat)
-- Lists = 100 est un bon début, ajustez selon la taille de vos données
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Créer un index sur les métadonnées pour des requêtes rapides
CREATE INDEX IF NOT EXISTS documents_metadata_idx
ON documents
USING GIN (metadata);

-- 5. Créer un index sur la date de création
CREATE INDEX IF NOT EXISTS documents_created_at_idx
ON documents (created_at DESC);

-- 6. Fonction pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. Créer un trigger pour updated_at
DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 8. Fonction pour la recherche de similarité
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding VECTOR(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE SQL STABLE
AS $$
  SELECT
    id,
    content,
    metadata,
    1 - (embedding <=> query_embedding) AS similarity,
    created_at
  FROM documents
  WHERE 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;

-- 9. Fonction pour rechercher par fichier
CREATE OR REPLACE FUNCTION get_documents_by_file (
  file_path TEXT
)
RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE SQL STABLE
AS $$
  SELECT
    id,
    content,
    metadata,
    created_at
  FROM documents
  WHERE metadata->>'file_path' = file_path
  ORDER BY (metadata->>'chunk_index')::INT;
$$;

-- 10. Vue pour les statistiques
CREATE OR REPLACE VIEW documents_stats AS
SELECT
  COUNT(*) AS total_documents,
  COUNT(DISTINCT metadata->>'file_path') AS unique_files,
  AVG(length(content)) AS avg_content_length,
  MIN(created_at) AS first_created,
  MAX(created_at) AS last_created
FROM documents;

-- 11. Politique de sécurité Row Level Security (RLS)
-- Décommentez si vous voulez activer RLS

-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- -- Permettre la lecture à tous les utilisateurs authentifiés
-- CREATE POLICY "Permettre lecture aux utilisateurs authentifiés"
-- ON documents FOR SELECT
-- TO authenticated
-- USING (true);

-- -- Permettre l'insertion aux utilisateurs authentifiés
-- CREATE POLICY "Permettre insertion aux utilisateurs authentifiés"
-- ON documents FOR INSERT
-- TO authenticated
-- WITH CHECK (true);

-- -- Permettre la suppression aux utilisateurs authentifiés
-- CREATE POLICY "Permettre suppression aux utilisateurs authentifiés"
-- ON documents FOR DELETE
-- TO authenticated
-- USING (true);

-- 12. Fonction pour nettoyer les anciens documents
CREATE OR REPLACE FUNCTION cleanup_old_documents (
  days_old INT DEFAULT 365
)
RETURNS TABLE (
  deleted_count BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
  count BIGINT;
BEGIN
  DELETE FROM documents
  WHERE created_at < NOW() - (days_old || ' days')::INTERVAL;

  GET DIAGNOSTICS count = ROW_COUNT;

  RETURN QUERY SELECT count;
END;
$$;

-- 13. Afficher les informations de configuration
SELECT
  'Configuration terminée!' AS message,
  (SELECT COUNT(*) FROM documents) AS documents_count,
  (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'documents') AS indexes_count;

-- NOTES IMPORTANTES:
--
-- 1. DIMENSION DE L'EMBEDDING:
--    - text-embedding-3-small: 1536 dimensions
--    - text-embedding-3-large: 3072 dimensions
--    - text-embedding-ada-002: 1536 dimensions
--    Modifiez VECTOR(1536) selon votre modèle
--
-- 2. INDEX IVFFLAT:
--    - lists = 100 pour ~1M de vecteurs
--    - lists = 1000 pour ~10M de vecteurs
--    - Ajustez selon vos besoins
--
-- 3. PERFORMANCE:
--    - L'index IVFFlat nécessite au moins 'lists' lignes pour être efficace
--    - Ajoutez d'abord vos données, puis créez l'index si nécessaire
--
-- 4. RECHERCHE:
--    Utilisez la fonction match_documents:
--    SELECT * FROM match_documents('[0.1, 0.2, ...]'::vector, 0.7, 10);
--
-- 5. NETTOYAGE:
--    Pour nettoyer les documents de plus d'un an:
--    SELECT * FROM cleanup_old_documents(365);
