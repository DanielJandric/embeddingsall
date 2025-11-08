# 🚀 Système V2 - Architecture Optimisée avec Haute Granularité

## 📋 Nouveautés

### Architecture à 2 Tables

**Avant (V1)** :
- 1 table `documents` : chunks avec embeddings mélangés
- Granularité : 1000 caractères/chunk
- Document original perdu

**Maintenant (V2)** :
- 📄 **`documents_full`** : Document complet original avec métadonnées
- 🔢 **`document_chunks`** : Chunks avec embeddings (haute granularité)
- ✅ Document original conservé
- ✅ **2.5x plus d'embeddings** grâce à la granularité fine

### Paramètres de Granularité

```python
# V1 (ancienne version)
CHUNK_SIZE = 1000 caractères
CHUNK_OVERLAP = 200 caractères
→ Un document de 10,000 caractères = ~12 chunks

# V2 (nouvelle version)
CHUNK_SIZE = 400 caractères
CHUNK_OVERLAP = 100 caractères
→ Un document de 10,000 caractères = ~30 chunks
```

**Résultat** : **2.5x plus d'embeddings** = recherche beaucoup plus précise !

---

## 🛠️ Installation

### Étape 1 : Configurer Supabase

**IMPORTANT** : Vous devez exécuter le nouveau script SQL.

1. Ouvrez votre dashboard Supabase : https://app.supabase.com
2. Allez dans **SQL Editor**
3. Copiez-collez **tout** le contenu de `supabase_setup_v2.sql`
4. Cliquez sur **Run** (F5)

Ce script va créer :
- ✅ Table `documents_full` (documents complets)
- ✅ Table `document_chunks` (chunks avec embeddings)
- ✅ Fonction `match_document_chunks()` (recherche sémantique)
- ✅ Fonction `get_database_stats()` (statistiques)
- ✅ Index optimisés (HNSW pour vitesse)

### Étape 2 : Supprimer l'ancienne table (optionnel)

Si vous voulez nettoyer l'ancienne structure :

```sql
-- Dans Supabase SQL Editor
DROP TABLE IF EXISTS documents CASCADE;
```

### Étape 3 : Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## 📤 Upload des Documents

### Commande de Base

```bash
python process_v2.py -i "C:\OneDriveExport" --upload --workers 3
```

### Options

```bash
python process_v2.py \
  -i "C:\OneDriveExport" \      # Dossier ou fichier
  --upload \                     # Upload vers Supabase
  --workers 3 \                  # Nombre de workers parallèles
  --max-files 10 \              # Limiter à 10 fichiers (test)
  --extensions pdf,txt,md       # Types de fichiers
```

### Exemple de Sortie

```
🚀 TRAITEMENT DE 44 FICHIERS
   Workers: 3
   Granularité: 400 caractères/chunk (overlap 100)
   Upload: OUI
======================================================================

📄 document1.pdf
======================================================================
📥 Extraction du texte...
✅ Texte extrait: 15,432 caractères (pdf_direct)
📄 Pages: 12
🔢 Découpage en chunks (taille: 400, overlap: 100)...
✅ 46 chunks créés (granularité fine)
🧠 Génération de 46 embeddings...
✅ 46 embeddings générés
📤 Upload vers Supabase...
✅ Upload terminé: 46 chunks

[1/44] ✅ document1.pdf: 46 chunks

...

======================================================================
📊 RÉSUMÉ
======================================================================
✅ Succès: 42
❌ Erreurs: 2
📁 Total: 44

🔢 Total embeddings créés: 1,247
📊 Moyenne par document: 29.7

💾 Statistiques Supabase:
   Documents: 42
   Chunks: 1,247
   Moyenne chunks/doc: 29.7
   Taille moyenne chunk: 385 caractères

🎉 Terminé !
```

---

## 🔍 Recherche et Chatbot

### Le chatbot fonctionne automatiquement avec V2 !

Il suffit de mettre à jour une ligne :

```bash
python chatbot.py
```

Le chatbot utilisera automatiquement la nouvelle fonction `match_document_chunks()` qui :
- ✅ Recherche dans les chunks (haute granularité)
- ✅ Retourne le document complet en même temps
- ✅ Meilleure précision grâce aux chunks plus petits

---

## 📊 Avantages de la V2

### 1. **Meilleure Précision de Recherche**

Avec des chunks plus petits :
- ✅ Moins de "bruit" dans chaque chunk
- ✅ Embeddings plus ciblés
- ✅ Meilleurs scores de similarité
- ✅ Résultats plus pertinents

**Exemple** :
```
V1 : "...beaucoup de texte... information importante ...beaucoup de texte..."
     → Embedding dilué, score de similarité: 0.73

V2 : "...information importante..."
     → Embedding concentré, score de similarité: 0.89
```

### 2. **Document Original Conservé**

Vous pouvez toujours récupérer le document complet :
- ✅ Contexte complet disponible
- ✅ Pas besoin de reconstruire à partir des chunks
- ✅ Métadonnées riches (taille, pages, méthode, etc.)

### 3. **Statistiques Détaillées**

```bash
python -c "from src.supabase_client_v2 import SupabaseUploaderV2; \
           u = SupabaseUploaderV2(); \
           print(u.get_database_stats())"
```

Résultat :
```json
{
  "total_documents": 42,
  "total_chunks": 1247,
  "avg_chunks_per_document": 29.7,
  "total_size_mb": 15.3,
  "avg_chunk_size": 385
}
```

### 4. **Relations et Intégrité**

- ✅ Clé étrangère : chunks → documents_full
- ✅ Cascade delete : supprimer un document supprime ses chunks
- ✅ Unicité : pas de chunks dupliqués

---

## 🧪 Test du Système

### Test Complet

```bash
python test_chatbot.py
```

### Test avec 1 Fichier

```bash
# Test sans upload
python process_v2.py -i "fichier.pdf"

# Test avec upload
python process_v2.py -i "fichier.pdf" --upload
```

### Vérifier les Statistiques

```bash
python -c "
from src.supabase_client_v2 import SupabaseUploaderV2
from dotenv import load_dotenv

load_dotenv()
uploader = SupabaseUploaderV2()
stats = uploader.get_database_stats()

print('📊 Statistiques:')
print(f'   Documents: {stats[\"total_documents\"]}')
print(f'   Chunks: {stats[\"total_chunks\"]}')
print(f'   Moyenne: {stats[\"avg_chunks_per_document\"]} chunks/doc')
print(f'   Taille: {stats[\"total_size_mb\"]} MB')
"
```

---

## 🔄 Migration depuis V1

Si vous avez déjà des données en V1 :

### Option 1 : Recommencer (RECOMMANDÉ)

```sql
-- Dans Supabase SQL Editor
DROP TABLE IF EXISTS documents CASCADE;
```

Puis exécutez `supabase_setup_v2.sql` et réuploadez :

```bash
python process_v2.py -i "C:\OneDriveExport" --upload --workers 3
```

### Option 2 : Garder V1 et V2

Les deux structures peuvent coexister. V2 utilise des noms de tables différents.

---

## 📈 Comparaison V1 vs V2

| Critère | V1 | V2 |
|---------|----|----|
| **Tables** | 1 table | 2 tables |
| **Chunk size** | 1000 chars | 400 chars |
| **Chunks/10k chars** | ~12 | ~30 |
| **Document original** | ❌ Perdu | ✅ Conservé |
| **Précision recherche** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Métadonnées** | Basiques | Riches |
| **Index** | IVFFlat | HNSW (plus rapide) |
| **Relations** | Aucune | Clés étrangères |

---

## 🎯 Exemples de Recherche

Avec la haute granularité, vous pouvez poser des questions très précises :

```python
from src.semantic_search import SemanticSearchEngine

engine = SemanticSearchEngine()

# Question précise
results = engine.search(
    "Quel est le montant exact du contrat Cashflex?",
    limit=5,
    threshold=0.75
)

# Avec des chunks plus petits, le résultat contiendra
# exactement le passage avec le montant, pas un gros bloc
# avec beaucoup de texte non pertinent !
```

---

## 🔧 Personnalisation de la Granularité

Vous pouvez ajuster dans `process_v2.py` :

```python
# Pour chunks TRÈS petits (ultra précis)
CHUNK_SIZE = 250
CHUNK_OVERLAP = 50

# Pour chunks moyens (équilibre)
CHUNK_SIZE = 400  # ← Valeur actuelle
CHUNK_OVERLAP = 100

# Pour chunks plus grands (contexte)
CHUNK_SIZE = 600
CHUNK_OVERLAP = 150
```

**Recommandations** :
- **Documents techniques** : 250-400 chars
- **Documents généraux** : 400-600 chars
- **Livres/articles longs** : 600-800 chars

---

## 🐛 Résolution de Problèmes

### Erreur "function match_document_chunks does not exist"

→ Vous devez exécuter `supabase_setup_v2.sql`

### Trop de chunks / Coût élevé

→ Augmentez `CHUNK_SIZE` dans `process_v2.py`

### Pas assez de précision

→ Diminuez `CHUNK_SIZE` (minimum 200 caractères)

### Upload lent

→ Réduisez le nombre de workers ou uploadez par petits lots :
```bash
python process_v2.py -i "dossier" --upload --workers 2 --max-files 10
```

---

## 📝 Prochaines Étapes

1. **Exécuter le SQL** : `supabase_setup_v2.sql`
2. **Uploader vos documents** :
   ```bash
   python process_v2.py -i "C:\OneDriveExport" --upload --workers 3
   ```
3. **Tester le chatbot** :
   ```bash
   python chatbot.py
   ```
4. **Profiter de la haute granularité** ! 🎉

---

## 💡 Conseils

- ✅ Commencez avec `--max-files 5` pour tester
- ✅ Utilisez `--workers 3` pour un bon équilibre vitesse/stabilité
- ✅ Surveillez les stats avec `get_database_stats()`
- ✅ Ajustez `CHUNK_SIZE` selon vos besoins

---

**Bonne recherche avec V2 !** 🚀
