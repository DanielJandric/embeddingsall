# 🚀 Guide de Démarrage Rapide - Windows

Guide pour lancer le traitement avec **granularité maximale** sur Windows.

---

## ⚡ Démarrage Rapide (3 étapes)

### 1️⃣ Vérifier l'environnement

```powershell
.\check_env.ps1
```

Si tout est ✓ vert, passez à l'étape 2.
Sinon, suivez les instructions affichées.

---

### 2️⃣ Configurer vos clés API

Éditez le fichier `.env` avec vos clés :

```powershell
notepad .env
```

**Configurations obligatoires** :
```bash
OPENAI_API_KEY=sk-votre_cle_openai_ici
SUPABASE_URL=https://votre-projet.supabase.co
SUPABASE_KEY=votre_cle_supabase_ici
```

**Configuration de granularité** (optionnel, défaut = FINE) :
```bash
GRANULARITY_LEVEL=ULTRA_FINE
```

Sauvegardez et fermez.

---

### 3️⃣ Lancer le traitement

```powershell
.\run_upload.ps1
```

**C'est tout !** Le script va :
- ✅ Vérifier l'environnement
- ✅ Installer les dépendances manquantes
- ✅ Traiter tous vos fichiers
- ✅ Uploader vers Supabase

---

## 🎯 Options Avancées

### Changer le répertoire d'entrée

```powershell
.\run_upload.ps1 -InputPath "D:\MesFichiers"
```

### Changer le niveau de granularité

```powershell
# Granularité MAXIMALE (60 chunks/10k)
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE"

# Haute granularité (30 chunks/10k) - Recommandé
.\run_upload.ps1 -GranularityLevel "FINE"

# Granularité moyenne (20 chunks/10k)
.\run_upload.ps1 -GranularityLevel "MEDIUM"
```

### Ajuster le nombre de workers

```powershell
# 5 workers (plus rapide si vous avez un bon CPU)
.\run_upload.ps1 -Workers 5

# 1 worker (mode séquentiel)
.\run_upload.ps1 -Workers 1
```

### Tester SANS uploader

```powershell
.\run_upload.ps1 -NoUpload
```

### Désactiver l'OCR (plus rapide)

```powershell
.\run_upload.ps1 -NoOCR
```

### Combiner les options

```powershell
.\run_upload.ps1 `
  -InputPath "c:\OneDriveExport" `
  -GranularityLevel "ULTRA_FINE" `
  -Workers 3 `
  -NoOCR
```

---

## 📊 Niveaux de Granularité

| Niveau | Chunks/10k | Précision | Coût/1k docs | Recommandation |
|--------|-----------|-----------|--------------|----------------|
| **ULTRA_FINE** | ~60 | ⭐⭐⭐⭐⭐ | $100 | Maximum |
| **FINE** | ~30 | ⭐⭐⭐⭐ | $50 | Optimal ✓ |
| **MEDIUM** | ~20 | ⭐⭐⭐ | $30 | Équilibré |
| **STANDARD** | ~12 | ⭐⭐ | $20 | Économique |
| **COARSE** | ~8 | ⭐ | $10 | Archive |

---

## 🛠️ Résolution de Problèmes

### Python n'est pas reconnu

```powershell
# Vérifier l'installation
python --version

# Si erreur, installez Python depuis :
# https://www.python.org/downloads/
# ⚠️ Cochez "Add Python to PATH" pendant l'installation !
```

### Erreur "script désactivé" PowerShell

```powershell
# Exécuter une seule fois (en tant qu'admin)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Dépendances manquantes

```powershell
# Installer toutes les dépendances
pip install -r requirements.txt
```

### Fichier .env manquant

```powershell
# Créer depuis l'exemple
Copy-Item .env.example .env

# Puis éditer
notepad .env
```

### Erreur OpenAI API

Vérifiez que votre clé commence par `sk-` et est valide :
```bash
OPENAI_API_KEY=sk-proj-...
```

### Erreur Supabase

Vérifiez vos identifiants Supabase :
```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📁 Structure des Fichiers

```
embeddingsall/
├── .env                          ← Vos clés API (à créer)
├── .env.example                  ← Template
├── run_upload.ps1                ← Script principal ⭐
├── check_env.ps1                 ← Vérification environnement
├── process_v2.py                 ← Script Python (appelé par run_upload.ps1)
├── demo_granularity.py           ← Démo des niveaux
├── GUIDE_GRANULARITE.md          ← Guide complet FR
├── QUICKSTART_WINDOWS.md         ← Ce fichier
├── requirements.txt              ← Dépendances Python
├── src/
│   ├── chunking_config.py        ← Configuration granularité
│   ├── embeddings.py             ← Génération embeddings
│   ├── supabase_client_v2.py     ← Client Supabase
│   └── ...
└── data/
    ├── input/                    ← Vos fichiers source
    └── processed/                ← Résultats
```

---

## 💡 Exemples d'Utilisation

### Cas 1 : Traitement Standard

```powershell
# Vérifier
.\check_env.ps1

# Lancer
.\run_upload.ps1
```

### Cas 2 : Maximum de Précision

```powershell
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE" -Workers 5
```

### Cas 3 : Test Rapide

```powershell
.\run_upload.ps1 -NoUpload -NoOCR -Workers 1
```

### Cas 4 : Production avec Logs

```powershell
# Le script sauvegarde automatiquement dans upload_YYYYMMDD_HHMMSS.log
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE"

# Consulter les logs après
notepad upload_20241111_143022.log
```

---

## 🎓 Aller Plus Loin

### Comparer les niveaux de granularité

```powershell
python demo_granularity.py
```

### Consulter le guide complet

```powershell
notepad GUIDE_GRANULARITE.md
```

### Traiter un seul fichier

```powershell
python process_v2.py --input "c:\OneDriveExport\document.pdf" --upload
```

---

## ✅ Checklist Avant Premier Lancement

- [ ] Python 3.8+ installé
- [ ] Fichier `.env` créé et configuré
- [ ] Clés API OpenAI et Supabase valides
- [ ] Dépendances Python installées
- [ ] Fichiers placés dans le répertoire source
- [ ] `.\check_env.ps1` affiche tout en ✓ vert

---

## 🆘 Support

**Problème ?** Vérifiez d'abord :

1. `.\check_env.ps1` → Tout doit être ✓
2. `.env` → Clés API correctes
3. `pip list` → Dépendances installées

**Documentation complète** :
- `GUIDE_GRANULARITE.md` - Guide FR détaillé
- `demo_granularity.py` - Comparaison des niveaux

---

## 🚀 Commande Finale (Copier-Coller)

```powershell
# Granularité MAXIMALE avec 3 workers
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE" -Workers 3
```

**Bonne chance ! 🎯**
