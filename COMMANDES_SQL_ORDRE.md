# 🚀 Commandes SQL à Exécuter (Ordre)

## ✅ OUI, tu dois exécuter ça dans Supabase !

Va sur **https://app.supabase.com** → ton projet → **SQL Editor** → **New Query**

Puis **copie-colle et exécute** chaque fichier dans cet ordre :

---

## 📝 Ordre d'Exécution

### ✅ 1. Extensions PostgreSQL
**Fichier:** `sql_migrations/01_extensions.sql`

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

### ✅ 2. Table documents_full
**Fichier:** `sql_migrations/02_table_documents_full.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 3. Index pour documents_full
**Fichier:** `sql_migrations/03_indexes_documents_full.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 4. Table document_chunks
**Fichier:** `sql_migrations/04_table_document_chunks.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 5. Index pour document_chunks
**Fichier:** `sql_migrations/05_indexes_document_chunks.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 6. Table extracted_entities
**Fichier:** `sql_migrations/06_table_extracted_entities.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 7. Tables de tags
**Fichier:** `sql_migrations/07_tables_tags.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 8. Table document_relations
**Fichier:** `sql_migrations/08_table_document_relations.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 9. Fonctions et Triggers Full-Text
**Fichier:** `sql_migrations/09_functions_triggers_fulltext.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 10. Index Full-Text
**Fichier:** `sql_migrations/10_indexes_fulltext.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 11. Fonction Recherche Sémantique Enhanced
**Fichier:** `sql_migrations/11_function_search_enhanced.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 12. Fonction Recherche Full-Text
**Fichier:** `sql_migrations/12_function_search_fulltext.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 13. Fonction Recherche Hybride
**Fichier:** `sql_migrations/13_function_search_hybrid.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 14. Vues Matérialisées
**Fichier:** `sql_migrations/14_materialized_views.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 15. Fonction Refresh Views
**Fichier:** `sql_migrations/15_function_refresh_views.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

### ✅ 16. Commentaires (Optionnel)
**Fichier:** `sql_migrations/16_comments.sql`

Copier-coller tout le contenu du fichier et exécuter.

---

## 🎯 Résumé Visuel

```
1️⃣  Extensions (vector, pg_trgm)
    ↓
2️⃣  Table documents_full
    ↓
3️⃣  Index documents_full
    ↓
4️⃣  Table document_chunks
    ↓
5️⃣  Index document_chunks
    ↓
6️⃣  Table extracted_entities
    ↓
7️⃣  Tables tags
    ↓
8️⃣  Table document_relations
    ↓
9️⃣  Fonctions/Triggers Full-Text
    ↓
🔟 Index Full-Text
    ↓
1️⃣1️⃣ Fonction Search Enhanced
    ↓
1️⃣2️⃣ Fonction Search Full-Text
    ↓
1️⃣3️⃣ Fonction Search Hybrid
    ↓
1️⃣4️⃣ Vues Matérialisées
    ↓
1️⃣5️⃣ Fonction Refresh Views
    ↓
1️⃣6️⃣ Commentaires (optionnel)
    ↓
✅ TERMINÉ !
```

---

## ⚡ Vérification Rapide Après Chaque Étape

À la fin de chaque fichier SQL, il y a une requête de vérification.

Par exemple après l'étape 2 (table documents_full) :

```sql
SELECT tablename FROM pg_tables WHERE tablename = 'documents_full';
```

Devrait retourner : `documents_full`

---

## 🚨 Si Tu as une Erreur

**Note le numéro de l'étape où ça bloque** et copie-colle l'erreur exacte.

Erreurs communes :

### "extension vector does not exist"
→ Ton Supabase n'a pas l'extension vector (rare)
→ Contacte le support Supabase

### "relation already exists"
→ Normal si tu réexécutes, passe à l'étape suivante

### "syntax error at or near"
→ Assure-toi de copier TOUT le contenu du fichier

---

## 📊 Après TOUT Avoir Exécuté

Vérifie que tout est OK :

```sql
-- Vérifier les tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Vérifier les fonctions
SELECT proname FROM pg_proc WHERE proname LIKE '%search%' OR proname LIKE '%match%';

-- Vérifier les vues matérialisées
SELECT matviewname FROM pg_matviews;
```

Tu devrais voir :
- **Tables** : documents_full, document_chunks, extracted_entities, document_tags, document_tag_relations, document_relations
- **Fonctions** : match_document_chunks_enhanced, search_documents_fulltext, search_hybrid, refresh_all_materialized_views
- **Vues** : stats_by_category, stats_by_location

---

## 🎉 Après l'Installation

Une fois que TOUT est exécuté sans erreur :

```bash
# Upload des documents
python upload_enhanced.py -i /chemin/vers/documents
```

---

**C'est parti ! Ouvre Supabase SQL Editor et copie-colle les fichiers un par un ! 🚀**
