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

-- Vérification
SELECT proname FROM pg_proc WHERE proname = 'refresh_all_materialized_views';
