# 🚀 GUIDE RAPIDE - CE QUE VOUS POUVEZ FAIRE MAINTENANT

## ✅ CE QUI FONCTIONNE DÉJÀ

Votre système est configuré et **FONCTIONNE** avec :
- ✅ **Azure OCR** - Extraction de texte depuis PDF et images
- ✅ **Toutes les dépendances** - Installation complète

## ⚠️ CE QUI NE FONCTIONNE PAS ENCORE

- ❌ **OpenAI Embeddings** - Besoin de configurer le billing/paiement sur OpenAI
- ⚠️ **Supabase** - Besoin d'exécuter le script SQL (voir ci-dessous)

---

## 🎯 OPTION 1 : Utiliser MAINTENANT (sans embeddings)

### Extraire du texte d'un document avec Azure OCR

```bash
# 1. Mettez votre PDF ou image dans data/input/
cp votre-document.pdf data/input/

# 2. Lancez le traitement (SANS embeddings)
python main_without_embeddings.py -i data/input/votre-document.pdf

# 3. Le résultat sera dans data/processed/votre-document_ocr.json
```

### Traiter un dossier complet

```bash
# Traiter tous les PDF/images d'un dossier
python main_without_embeddings.py -i data/input/
```

---

## 🔧 OPTION 2 : Configurer Supabase (5 minutes)

### Étape 1 : Ouvrir Supabase

1. Allez sur https://supabase.com/dashboard
2. Connectez-vous
3. Ouvrez votre projet

### Étape 2 : Exécuter le SQL

1. Cliquez sur **"SQL Editor"** dans le menu de gauche (icône 🔨)
2. Cliquez sur **"New query"**
3. Copiez-collez le contenu du fichier `supabase_simple.sql`
4. Cliquez sur **"RUN"** (bouton vert)

Vous devriez voir "Configuration terminée!"

### Étape 3 : Tester

```bash
# Traiter ET uploader vers Supabase (sans embeddings)
python main_without_embeddings.py -i data/input/doc.pdf --upload
```

---

## 💰 OPTION 3 : Configurer OpenAI (pour les embeddings)

### Pourquoi les embeddings ?

Les embeddings permettent la **recherche sémantique** :
- Rechercher par sens, pas juste par mots-clés
- Trouver des documents similaires
- Construire un moteur de recherche intelligent

### Configuration

1. Allez sur https://platform.openai.com/account/billing
2. Ajoutez une carte de crédit
3. Ajoutez au moins **$5 de crédit**
4. Votre clé API fonctionnera automatiquement

### Une fois configuré

```bash
# Traiter avec OCR + Embeddings + Upload Supabase
python main.py -i data/input/doc.pdf --upload
```

---

## 📁 Structure des Fichiers

```
embeddingsall/
├── main.py                        ← Script COMPLET (OCR + Embeddings)
├── main_without_embeddings.py     ← Script SANS Embeddings (fonctionne maintenant!)
├── test_setup.py                  ← Test de configuration
├── test_azure_only.py             ← Test Azure OCR
├── supabase_simple.sql            ← SQL à exécuter dans Supabase
├── data/
│   ├── input/                     ← Mettez vos documents ICI
│   └── processed/                 ← Résultats JSON ici
└── src/
    ├── azure_ocr.py               ← Module OCR
    ├── embeddings.py              ← Module Embeddings
    └── supabase_client.py         ← Module Supabase
```

---

## 🧪 Tests Disponibles

### Test complet de configuration
```bash
python test_setup.py
```

### Test Azure OCR uniquement
```bash
python test_azure_only.py
```

---

## 📝 Exemples d'Utilisation

### 1. Extraire le texte d'un PDF
```bash
python main_without_embeddings.py -i data/input/contrat.pdf
# Résultat: data/processed/contrat_ocr.json
```

### 2. Traiter plusieurs documents
```bash
python main_without_embeddings.py -i data/input/
# Traite tous les PDF/images du dossier
```

### 3. Upload vers Supabase (après configuration)
```bash
python main_without_embeddings.py -i data/input/ --upload
```

### 4. Avec logs détaillés
```bash
python main_without_embeddings.py -i data/input/ --log-level DEBUG
```

---

## 🆘 Dépannage

### "Azure endpoint et key doivent être fournis"
→ Vérifiez votre fichier `.env`

### "Table does not exist" (Supabase)
→ Exécutez `supabase_simple.sql` dans Supabase

### "Access denied" (OpenAI)
→ Configurez le billing sur OpenAI (voir OPTION 3)

---

## ✅ RÉSUMÉ

**CE QUE VOUS POUVEZ FAIRE MAINTENANT :**
```bash
# Mettre un document dans data/input/
cp mon-document.pdf data/input/

# Extraire le texte avec Azure OCR
python main_without_embeddings.py -i data/input/mon-document.pdf

# Voir le résultat
cat data/processed/mon-document_ocr.json
```

**PLUS TARD (après config Supabase) :**
```bash
python main_without_embeddings.py -i data/input/ --upload
```

**ENCORE PLUS TARD (après config OpenAI) :**
```bash
python main.py -i data/input/ --upload  # Avec embeddings!
```

---

## 🎉 C'est tout !

Vous avez un système fonctionnel d'extraction de texte avec Azure OCR.

Les embeddings et Supabase sont des **bonus** que vous pouvez ajouter plus tard ! 🚀
