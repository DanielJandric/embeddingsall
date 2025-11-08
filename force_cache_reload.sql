-- ============================================================================
-- FORCE LE RELOAD DU CACHE POSTGREST
-- ============================================================================
-- Exécutez ce script pour forcer Supabase à rafraîchir le cache API
-- ============================================================================

-- Méthode 1: GRANT trivial (force le reload immédiat)
GRANT SELECT ON public.documents_full TO anon;
GRANT SELECT ON public.document_chunks TO anon;
GRANT SELECT ON public.documents_summary TO anon;
GRANT EXECUTE ON FUNCTION public.get_database_stats() TO anon;
GRANT EXECUTE ON FUNCTION public.match_document_chunks(vector(1536), float, int) TO anon;
GRANT EXECUTE ON FUNCTION public.get_full_document(bigint) TO anon;
GRANT EXECUTE ON FUNCTION public.delete_document_by_path(text) TO anon;

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Cache PostgREST forcé au reload !';
    RAISE NOTICE 'Attendez 10-30 secondes puis testez avec Python.';
END $$;

-- Vérification finale
SELECT 'VALIDATION' AS section, 'Tables' AS type, COUNT(*) AS count
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('documents_full', 'document_chunks')

UNION ALL

SELECT 'VALIDATION', 'Fonctions', COUNT(*)
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name IN ('get_database_stats', 'match_document_chunks', 'get_full_document', 'delete_document_by_path')

UNION ALL

SELECT 'VALIDATION', 'Vue', COUNT(*)
FROM information_schema.views
WHERE table_schema = 'public'
AND table_name = 'documents_summary';

-- Test fonctionnel
SELECT * FROM public.get_database_stats();
