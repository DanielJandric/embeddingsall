# 🚀 COMMANDES POUR UPLOAD MAXIMAL

## 📍 Tes Documents
**Chemin:** `C:\OneDriveExport`

---

## ⚡ COMMANDES À EXÉCUTER

### 1️⃣ Vider les Anciennes Tables (Dans Supabase SQL Editor)

**Va sur Supabase → SQL Editor → Exécute :**

```sql
-- Vider toutes les tables
TRUNCATE TABLE document_chunks CASCADE;
TRUNCATE TABLE documents_full CASCADE;
TRUNCATE TABLE extracted_entities CASCADE;
TRUNCATE TABLE document_tag_relations CASCADE;
TRUNCATE TABLE document_tags CASCADE;
TRUNCATE TABLE document_relations CASCADE;

-- Vérification (doit retourner 0 pour chaque)
SELECT 'documents_full' as table_name, COUNT(*) as count FROM documents_full
UNION ALL
SELECT 'document_chunks', COUNT(*) FROM document_chunks
UNION ALL
SELECT 'extracted_entities', COUNT(*) FROM extracted_entities
UNION ALL
SELECT 'document_tags', COUNT(*) FROM document_tags;
```

✅ **Tu dois voir 0 partout**

---

### 2️⃣ Upload MAXIMAL

**Dans ton terminal (WSL/Linux) :**

```bash
cd /home/user/embeddingsall

# Test d'abord (DRY RUN) - SANS upload réel
python upload_maximal.py -i /mnt/c/OneDriveExport --dry-run
```

**OU si tu es sur Windows (cmd/PowerShell) :**

```bash
cd C:\path\to\embeddingsall

# Test d'abord
python upload_maximal.py -i "C:\OneDriveExport" --dry-run
```

---

### 3️⃣ Si le Test est OK → Upload RÉEL

**WSL/Linux :**

```bash
python upload_maximal.py -i /mnt/c/OneDriveExport
```

**Windows :**

```bash
python upload_maximal.py -i "C:\OneDriveExport"
```

---

## 📊 Configuration MAXIMALE Appliquée

```
✅ Chunk Size: 800 caractères (plus petit = meilleure précision)
✅ Overlap: 250 caractères (plus grand = meilleur contexte)
✅ Contexte: 300 caractères avant/après (au lieu de 200)
✅ Extraction: TOUTES les métadonnées (100+ champs)
✅ Entités: Entreprises, lieux, personnes, montants, dates
✅ Tags: Génération automatique intelligente
✅ Scores: Importance, qualité, complétude
✅ Structure: Titres, sections, paragraphes
✅ Analyse: Langue, formalité, type de document
✅ Full-text: Vecteurs de recherche pondérés
✅ Logging: Mode DEBUG complet (fichier upload_maximal.log)
```

---

## 📝 Pendant l'Upload

Tu verras des logs détaillés comme :

```
================================================================================
UPLOAD MAXIMAL: /mnt/c/OneDriveExport/contrat_lausanne.pdf
================================================================================
📄 Extraction du texte...
✅ Texte extrait: 15234 caractères, 2456 mots
🔍 Extraction MAXIMALE des métadonnées...
✅ 87 champs de métadonnées extraits
🗂️  Mapping vers schéma de base de données...
   Type: contrat de location
   Catégorie: immobilier
   Commune: Lausanne
   Canton: VD
   Tags: 12 tags
   Score complétude: 89.3%
   Score richesse: 92.1%
📤 Upload du document vers Supabase...
✅ Document uploadé: ID=42
✂️  Création des chunks enrichis...
✅ 19 chunks créés
   🌟 7 chunks avec importance > 0.7
   💰 5 chunks contiennent des montants
📤 Upload des chunks vers Supabase...
✅ 19 chunks uploadés
🏢 23 entités uniques extraites
🏷️  12 tags créés
⏱️  Temps de traitement: 8.34 secondes
================================================================================
✅ UPLOAD TERMINÉ AVEC SUCCÈS
================================================================================
```

---

## ⏱️ Estimation du Temps

**Calcul :**
- ~5-10 secondes par document (dépend de la taille)
- Si tu as 100 documents → ~10-15 minutes
- Si tu as 1000 documents → ~2-3 heures
- Si tu as 10000 documents → ~20-30 heures

**L'upload se fait automatiquement**, tu peux lancer et laisser tourner !

---

## 📊 À la Fin - Statistiques

```
================================================================================
📊 STATISTIQUES DÉTAILLÉES D'UPLOAD MAXIMAL
================================================================================
Documents traités:        1234
Documents uploadés:       1230
Chunks créés:             24680
Entités extraites:        5432
Tags créés:               14760
Champs métadonnées:       107310
Taille totale:            456.78 MB
Temps total:              183.45 minutes

Moyennes par document:
  - Temps:                8.95 secondes
  - Chunks:               20.1
  - Métadonnées:          87.2

Erreurs:                  4
================================================================================
```

---

## 🔍 Vérifier dans Supabase

**Après l'upload, va dans Supabase → Table Editor :**

### Table `documents_full`

Tu devrais voir pour chaque document :
- ✅ `file_name` : nom du fichier
- ✅ `type_document` : détecté automatiquement
- ✅ `categorie` : catégorie principale
- ✅ `commune`, `canton` : localisation
- ✅ `montant_principal` : montant détecté
- ✅ `date_document` : date du document
- ✅ `tags` : array de tags
- ✅ `metadata_completeness_score` : score de complétude
- ✅ Etc. (40+ champs remplis)

### Table `document_chunks`

Tu devrais voir pour chaque chunk :
- ✅ `chunk_content` : contenu du chunk
- ✅ `context_before` : 300 chars avant
- ✅ `context_after` : 300 chars après
- ✅ `importance_score` : score d'importance
- ✅ `has_tables`, `has_amounts`, `has_dates` : flags
- ✅ `entities_mentioned` : entités extraites
- ✅ `embedding` : vecteur d'embedding

---

## 🧪 Tester la Recherche

**Dans un script Python ou notebook :**

```python
from src.supabase_client_enhanced import SupabaseClientEnhanced
from src.embeddings import generate_embedding

client = SupabaseClientEnhanced()

# Test 1: Recherche full-text
print("🔍 Test 1: Recherche full-text")
results = client.search_fulltext('contrat location lausanne', limit=5)
print(f"Trouvé {len(results)} documents")
for r in results:
    print(f"  📄 {r['file_name']}")
    print(f"     Type: {r['type_document']}, Commune: {r['commune']}")
    print(f"     Score: {r['rank']:.3f}")
    print()

# Test 2: Recherche sémantique
print("🔍 Test 2: Recherche sémantique")
query = "Trouver les évaluations immobilières de plus de 10 millions"
embedding = generate_embedding(query)
results = client.search_similar(embedding, limit=5)
print(f"Trouvé {len(results)} chunks")
for r in results:
    print(f"  📄 {r['file_name']}")
    print(f"     Type: {r['type_document']}, Montant: {r.get('montant_principal', 'N/A')} CHF")
    print(f"     Similarité: {r['similarity']:.2%}")
    print(f"     Extrait: {r['chunk_content'][:100]}...")
    print()

# Test 3: Recherche hybride (meilleure précision)
print("🔍 Test 3: Recherche hybride")
results = client.search_hybrid(
    search_text='évaluation immobilière aigle',
    query_embedding=embedding,
    limit=5
)
print(f"Trouvé {len(results)} résultats")
for r in results:
    print(f"  📄 {r['file_name']}")
    print(f"     Score combiné: {r['combined_score']:.3f}")
    print(f"     (Sémantique: {r['semantic_score']:.3f}, Full-text: {r['fulltext_score']:.3f})")
    print()

# Test 4: Statistiques
print("📊 Statistiques")
stats_cat = client.get_stats_by_category()
print(f"Catégories: {len(stats_cat)}")
for s in stats_cat[:5]:
    print(f"  {s['categorie']} / {s['type_document']}: {s['document_count']} docs")

stats_loc = client.get_stats_by_location()
print(f"\nLocalisations: {len(stats_loc)}")
for s in stats_loc[:5]:
    print(f"  {s['canton']} - {s['commune']}: {s['document_count']} docs")

# Rafraîchir les vues matérialisées
print("\n🔄 Rafraîchissement des vues matérialisées...")
client.refresh_materialized_views()
print("✅ Fait")
```

---

## 💰 Coût Estimé OpenAI

**Estimation :**
- Modèle: `text-embedding-3-small`
- Prix: ~$0.00002 par 1000 tokens
- 1 chunk ≈ 200 tokens en moyenne
- 1000 documents × 20 chunks = 20000 chunks
- 20000 chunks × 200 tokens = 4M tokens
- Coût: ~$0.08 pour 1000 documents

**Pour 10000 documents ≈ $0.80**

---

## 🗂️ Fichier de Log

Tous les détails sont sauvegardés dans :

```bash
upload_maximal.log
```

Tu peux le consulter pour voir exactement ce qui s'est passé.

---

## 🆘 En Cas d'Erreur

### Erreur: "No module named 'src'"

```bash
# Assure-toi d'être dans le bon répertoire
cd /home/user/embeddingsall

# Vérifie que le dossier src/ existe
ls -la src/
```

### Erreur: "OPENAI_API_KEY not found"

```bash
# Vérifie ton fichier .env
cat .env | grep OPENAI_API_KEY

# Si vide, ajoute-le
echo "OPENAI_API_KEY=sk-xxx..." >> .env
```

### Erreur: "SUPABASE_URL not found"

```bash
# Vérifie ton fichier .env
cat .env | grep SUPABASE

# Ajoute si nécessaire
echo "SUPABASE_URL=https://xxx.supabase.co" >> .env
echo "SUPABASE_KEY=eyJxxx..." >> .env
```

### Upload bloqué / Très lent

C'est normal si tu as beaucoup de fichiers. L'upload prend du temps car :
1. Extraction de texte (PDF, DOCX, etc.)
2. Analyse de 100+ métadonnées
3. Génération des embeddings (API OpenAI)
4. Upload vers Supabase

**Laisse tourner**, ça continue même si ça semble lent.

---

## 🎯 COMMANDE FINALE

**Si tu es sur WSL/Linux :**

```bash
cd /home/user/embeddingsall
python upload_maximal.py -i /mnt/c/OneDriveExport
```

**Si tu es sur Windows :**

```bash
cd C:\...\embeddingsall
python upload_maximal.py -i "C:\OneDriveExport"
```

---

**C'est parti ! Lance la commande et laisse tourner ! 🚀**

**N'oublie pas** :
1. ✅ Vider les tables dans Supabase d'abord
2. ✅ Vérifier que .env contient OPENAI_API_KEY et SUPABASE_URL/KEY
3. ✅ Lancer l'upload
4. ✅ Attendre (peut prendre plusieurs heures si beaucoup de fichiers)
5. ✅ Vérifier dans Supabase Table Editor
6. ✅ Tester la recherche
