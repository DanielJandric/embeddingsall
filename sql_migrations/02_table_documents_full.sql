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

-- Vérification
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE tablename = 'documents_full';
