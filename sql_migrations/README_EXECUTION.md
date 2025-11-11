# 🚀 Guide d'Exécution des Migrations SQL

## 📋 Ordre d'Exécution

Les fichiers SQL doivent être exécutés **dans cet ordre précis** :

### Étape par Étape

1. **01_extensions.sql** - Extensions PostgreSQL (vector, pg_trgm)
2. **02_table_documents_full.sql** - Table principale des documents
3. **03_indexes_documents_full.sql** - Index pour documents_full
4. **04_table_document_chunks.sql** - Table des chunks
5. **05_indexes_document_chunks.sql** - Index pour document_chunks
6. **06_table_extracted_entities.sql** - Table des entités extraites
7. **07_tables_tags.sql** - Tables de tags (document_tags + relations)
8. **08_table_document_relations.sql** - Table des relations entre documents
9. **09_functions_triggers_fulltext.sql** - Fonctions et triggers pour full-text search
10. **10_indexes_fulltext.sql** - Index full-text search
11. **11_function_search_enhanced.sql** - Fonction de recherche sémantique enrichie
12. **12_function_search_fulltext.sql** - Fonction de recherche full-text
13. **13_function_search_hybrid.sql** - Fonction de recherche hybride
14. **14_materialized_views.sql** - Vues matérialisées pour statistiques
15. **15_function_refresh_views.sql** - Fonction pour rafraîchir les vues
16. **16_comments.sql** - Commentaires (optionnel)

---

## 🎯 Méthodes d'Exécution

### Méthode 1 : Via Supabase SQL Editor (RECOMMANDÉ)

**Plus simple et directement dans l'interface Supabase**

1. Aller sur https://app.supabase.com
2. Sélectionner votre projet
3. Aller dans **SQL Editor** (menu de gauche)
4. Cliquer sur **New Query**
5. Pour chaque fichier (dans l'ordre) :
   - Copier le contenu du fichier
   - Coller dans l'éditeur SQL
   - Cliquer sur **Run** (ou Ctrl+Enter)
   - Vérifier qu'il n'y a pas d'erreurs
   - Passer au fichier suivant

**Astuce** : Vous pouvez voir les résultats de vérification à la fin de chaque fichier pour confirmer que tout s'est bien passé.

---

### Méthode 2 : Via Script Automatique (bash)

**Pour exécuter tout d'un coup**

```bash
cd /home/user/embeddingsall
./run_all_migrations.sh
```

Le script exécutera tous les fichiers dans l'ordre et s'arrêtera en cas d'erreur.

---

### Méthode 3 : Via psql (ligne de commande)

**Si vous avez accès direct à PostgreSQL**

```bash
# Définir la variable de connexion (remplacer par votre URL)
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres"

# Exécuter tous les fichiers dans l'ordre
cd /home/user/embeddingsall/sql_migrations

psql $DATABASE_URL -f 01_extensions.sql
psql $DATABASE_URL -f 02_table_documents_full.sql
psql $DATABASE_URL -f 03_indexes_documents_full.sql
psql $DATABASE_URL -f 04_table_document_chunks.sql
psql $DATABASE_URL -f 05_indexes_document_chunks.sql
psql $DATABASE_URL -f 06_table_extracted_entities.sql
psql $DATABASE_URL -f 07_tables_tags.sql
psql $DATABASE_URL -f 08_table_document_relations.sql
psql $DATABASE_URL -f 09_functions_triggers_fulltext.sql
psql $DATABASE_URL -f 10_indexes_fulltext.sql
psql $DATABASE_URL -f 11_function_search_enhanced.sql
psql $DATABASE_URL -f 12_function_search_fulltext.sql
psql $DATABASE_URL -f 13_function_search_hybrid.sql
psql $DATABASE_URL -f 14_materialized_views.sql
psql $DATABASE_URL -f 15_function_refresh_views.sql
psql $DATABASE_URL -f 16_comments.sql
```

---

### Méthode 4 : Via Python

**Utiliser le script Python fourni**

```bash
python run_migrations.py
```

---

## ✅ Vérifications Après Exécution

### Vérifier les Tables

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

Vous devriez voir :
- `documents_full`
- `document_chunks`
- `extracted_entities`
- `document_tags`
- `document_tag_relations`
- `document_relations`

### Vérifier les Index

```sql
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

Vous devriez avoir 15+ index.

### Vérifier les Fonctions

```sql
SELECT proname, pronargs
FROM pg_proc
WHERE proname IN (
    'match_document_chunks_enhanced',
    'search_documents_fulltext',
    'search_hybrid',
    'refresh_all_materialized_views'
);
```

### Vérifier les Vues Matérialisées

```sql
SELECT matviewname
FROM pg_matviews
WHERE schemaname = 'public';
```

Vous devriez voir :
- `stats_by_category`
- `stats_by_location`

### Vérifier les Triggers

```sql
SELECT tgname, tgrelid::regclass
FROM pg_trigger
WHERE tgname LIKE '%search_vector%' OR tgname LIKE '%updated_at%';
```

---

## 🚨 En Cas d'Erreur

### Erreur : "extension does not exist"

**Problème** : Extensions non installées

**Solution** :
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Si ça ne marche pas, vérifier que les extensions sont disponibles dans Supabase (elles devraient l'être).

---

### Erreur : "relation already exists"

**Problème** : Table/Index déjà créé

**Solution** : C'est normal si vous réexécutez. Les scripts utilisent `IF NOT EXISTS` donc ça ne devrait pas bloquer.

---

### Erreur : "syntax error near..."

**Problème** : Erreur de syntaxe SQL

**Solution** :
1. Vérifier la version de PostgreSQL (doit être 13+)
2. Copier-coller exactement le contenu du fichier (sans modifications)
3. Vérifier qu'il n'y a pas de caractères cachés

---

### Erreur : "function already exists"

**Problème** : Fonction déjà créée

**Solution** : Normal, les scripts utilisent `CREATE OR REPLACE` donc ça devrait remplacer automatiquement.

---

## 📊 Après l'Installation

### 1. Tester la Recherche Full-Text

```sql
-- Doit retourner une fonction vide (normal car pas encore de données)
SELECT * FROM search_documents_fulltext('test');
```

### 2. Tester la Recherche Sémantique

```sql
-- Doit retourner une fonction vide (normal car pas encore de données)
SELECT * FROM match_document_chunks_enhanced(
    ARRAY[0.1, 0.2, ...]::vector(1536),  -- Embedding de test
    0.7,
    10
);
```

### 3. Uploader des Documents de Test

```bash
cd /home/user/embeddingsall
python upload_enhanced.py -i /path/to/test/documents --dry-run
```

### 4. Uploader pour de Vrai

```bash
python upload_enhanced.py -i /path/to/documents
```

---

## 💡 Conseils

1. **Exécuter étape par étape** : Si une erreur survient, vous saurez exactement où
2. **Vérifier après chaque étape** : Utilisez les requêtes de vérification à la fin de chaque fichier
3. **Sauvegarder** : Si vous avez déjà des données, faites une sauvegarde avant
4. **Utiliser Supabase SQL Editor** : C'est la méthode la plus simple et visuelle

---

## 🔄 Rollback (Annulation)

Si vous voulez tout annuler :

```sql
-- ATTENTION: Cela supprime TOUTES les données !

DROP MATERIALIZED VIEW IF EXISTS stats_by_location CASCADE;
DROP MATERIALIZED VIEW IF EXISTS stats_by_category CASCADE;

DROP TABLE IF EXISTS document_relations CASCADE;
DROP TABLE IF EXISTS document_tag_relations CASCADE;
DROP TABLE IF EXISTS document_tags CASCADE;
DROP TABLE IF EXISTS extracted_entities CASCADE;
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents_full CASCADE;

DROP FUNCTION IF EXISTS refresh_all_materialized_views();
DROP FUNCTION IF EXISTS search_hybrid(text, vector, int, float, float);
DROP FUNCTION IF EXISTS search_documents_fulltext(text, int, text, text);
DROP FUNCTION IF EXISTS match_document_chunks_enhanced(vector, float, int, text, text, text, text, text[], date, date);
DROP FUNCTION IF EXISTS chunks_search_vector_update();
DROP FUNCTION IF EXISTS documents_search_vector_update();
DROP FUNCTION IF EXISTS update_updated_at_column();
```

---

## 📞 Support

Si vous rencontrez des problèmes :

1. Vérifier les logs dans Supabase (Database > Logs)
2. Consulter la documentation PostgreSQL
3. Vérifier que la version de PostgreSQL est compatible (13+)
4. Vérifier que les extensions vector et pg_trgm sont disponibles

---

**Prêt à commencer ? Utilisez la Méthode 1 (Supabase SQL Editor) pour la simplicité !** 🚀
