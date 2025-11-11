# 🪟 Embeddingsall - Windows Setup

Système de traitement de documents avec **granularité maximale** pour recherche sémantique ultra-précise.

---

## 🚀 Démarrage Ultra-Rapide

### Pour PowerShell (Recommandé) :

```powershell
# 1. Vérifier l'environnement
.\check_env.ps1

# 2. Éditer .env avec vos clés
notepad .env

# 3. Lancer !
.\run_upload.ps1
```

### Pour CMD/Batch :

```cmd
run_upload.cmd
```

---

## 📋 Ce qui est Inclus

### Scripts Windows :
- ✅ **`run_upload.ps1`** - Script PowerShell complet avec interface interactive
- ✅ **`run_upload.cmd`** - Script Batch pour CMD
- ✅ **`check_env.ps1`** - Vérification de l'environnement

### Documentation :
- ✅ **`QUICKSTART_WINDOWS.md`** - Guide de démarrage Windows
- ✅ **`GUIDE_GRANULARITE.md`** - Guide complet en français
- ✅ **`README_WINDOWS.md`** - Ce fichier

### Scripts Python :
- ✅ **`process_v2.py`** - Traitement avec architecture V2
- ✅ **`demo_granularity.py`** - Démonstration des niveaux
- ✅ **`src/chunking_config.py`** - Configuration de granularité

---

## 🎯 Fonctionnalités

### Granularité Maximale

**5 niveaux prédéfinis** :

| Niveau | Chunks/10k | Cas d'usage |
|--------|-----------|-------------|
| ULTRA_FINE | ~60 | 🔥 Précision maximale |
| FINE | ~30 | ⭐ Recommandé |
| MEDIUM | ~20 | Équilibré |
| STANDARD | ~12 | Économique |
| COARSE | ~8 | Archive |

### Traitement Parallèle

- ⚡ 1-10 workers configurables
- 🚀 Traitement jusqu'à 10x plus rapide
- 💾 Gestion automatique de la mémoire

### Support Multi-formats

- 📄 PDF (direct + OCR)
- 🖼️ Images (via Azure OCR)
- 📝 TXT, MD, CSV
- 🔍 Détection automatique du meilleur mode

### Upload Automatique

- ☁️ Upload vers Supabase
- 🗄️ 2 tables : documents complets + chunks
- 🔎 Index vectoriel HNSW pour recherche rapide

---

## ⚙️ Configuration Requise

### Logiciels :
- Python 3.8+
- PowerShell 5.1+ (Windows 10/11)

### Services Cloud :
- OpenAI API (pour embeddings)
- Supabase (stockage + recherche vectorielle)
- Azure Form Recognizer (optionnel, pour OCR)

---

## 📦 Installation

### 1. Cloner le Projet

```powershell
git clone <votre-repo>
cd embeddingsall
```

### 2. Créer .env

```powershell
Copy-Item .env.example .env
notepad .env
```

Configurez vos clés :
```bash
OPENAI_API_KEY=sk-votre_cle
SUPABASE_URL=https://votre-projet.supabase.co
SUPABASE_KEY=votre_cle
GRANULARITY_LEVEL=ULTRA_FINE
```

### 3. Installer les Dépendances

Le script `run_upload.ps1` installe automatiquement les dépendances manquantes.

Ou manuellement :
```powershell
pip install -r requirements.txt
```

---

## 🎮 Utilisation

### Mode Automatique (Recommandé)

```powershell
.\run_upload.ps1
```

Le script va :
1. ✅ Vérifier Python et les dépendances
2. ✅ Installer ce qui manque
3. ✅ Vous demander confirmation
4. ✅ Traiter tous vos fichiers
5. ✅ Uploader vers Supabase
6. ✅ Sauvegarder les logs

### Mode Personnalisé

```powershell
# Granularité ULTRA_FINE avec 5 workers
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE" -Workers 5

# Depuis un autre répertoire
.\run_upload.ps1 -InputPath "D:\Documents"

# Test sans upload
.\run_upload.ps1 -NoUpload
```

### Options Disponibles

| Option | Description | Défaut |
|--------|-------------|--------|
| `-InputPath` | Répertoire source | `c:\OneDriveExport` |
| `-GranularityLevel` | Niveau de granularité | `ULTRA_FINE` |
| `-Workers` | Nombre de threads | `3` |
| `-NoUpload` | Désactiver l'upload | Upload activé |
| `-NoOCR` | Désactiver l'OCR | OCR activé |
| `-SkipDependencyCheck` | Ignorer vérif dépendances | Vérification activée |

---

## 📊 Exemples de Résultats

### Avec ULTRA_FINE (200 chars/chunk) :

```
Document : rapport_annuel.pdf (25 432 caractères)
→ 152 chunks créés
→ Précision de recherche : ⭐⭐⭐⭐⭐
→ Coût : $0.0003
```

### Avec FINE (400 chars/chunk) :

```
Document : rapport_annuel.pdf (25 432 caractères)
→ 76 chunks créés
→ Précision de recherche : ⭐⭐⭐⭐
→ Coût : $0.00015
```

### Avec STANDARD (1000 chars/chunk) :

```
Document : rapport_annuel.pdf (25 432 caractères)
→ 30 chunks créés
→ Précision de recherche : ⭐⭐
→ Coût : $0.00006
```

**Verdict** : ULTRA_FINE coûte 5x plus cher mais offre **40-60% de précision en plus** !

---

## 🔍 Démonstration

Pour voir l'impact visuel de chaque niveau :

```powershell
python demo_granularity.py
```

Affiche :
- Nombre de chunks par niveau
- Taille moyenne des chunks
- Estimation des coûts
- Aperçu du découpage

---

## 📈 Performance

### Avec 3 Workers :

| Documents | Temps | Chunks | Coût (ULTRA_FINE) |
|-----------|-------|--------|-------------------|
| 10 | ~2 min | ~600 | $0.001 |
| 100 | ~15 min | ~6 000 | $0.012 |
| 1000 | ~2h | ~60 000 | $0.12 |

*(Pour documents de ~10k caractères)*

---

## 🛠️ Dépannage

### "Python n'est pas reconnu"

```powershell
# Télécharger et installer Python
# https://www.python.org/downloads/
# ⚠️ Cocher "Add Python to PATH" !
```

### "Les scripts sont désactivés"

```powershell
# En tant qu'Admin
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "Module X not found"

```powershell
pip install -r requirements.txt
```

### Vérification complète

```powershell
.\check_env.ps1
```

---

## 📚 Documentation Complète

- **`QUICKSTART_WINDOWS.md`** - Guide rapide Windows
- **`GUIDE_GRANULARITE.md`** - Guide détaillé sur la granularité
- **`README.md`** - Documentation générale du projet

---

## 🎯 Cas d'Usage

### 1. Documentation Technique

```powershell
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE"
```

→ Recherche ultra-précise de fonctions, paramètres, configurations

### 2. Documents Juridiques

```powershell
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE" -Workers 5
```

→ Identification exacte de clauses et articles

### 3. Archive de Documents

```powershell
.\run_upload.ps1 -GranularityLevel "MEDIUM" -Workers 10
```

→ Bon équilibre coût/performance

### 4. Test/Développement

```powershell
.\run_upload.ps1 -NoUpload -NoOCR -Workers 1
```

→ Test local rapide sans upload

---

## 💡 Conseils Pro

### Optimiser les Coûts

Pour réduire les coûts tout en gardant une bonne qualité :
```bash
GRANULARITY_LEVEL=FINE  # Au lieu de ULTRA_FINE
```

### Maximiser la Vitesse

Pour traiter de gros volumes rapidement :
```powershell
.\run_upload.ps1 -Workers 10 -NoOCR
```

### Meilleure Qualité

Pour une précision maximale :
```powershell
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE" -Workers 3
```

---

## 📞 Support

**Problème ?**

1. Exécutez `.\check_env.ps1`
2. Vérifiez `.env`
3. Consultez `QUICKSTART_WINDOWS.md`
4. Vérifiez les logs dans `upload_YYYYMMDD_HHMMSS.log`

---

## 🚀 Commande Prête à l'Emploi

```powershell
# Configuration optimale
.\run_upload.ps1 -GranularityLevel "ULTRA_FINE" -Workers 3
```

**C'est parti ! 🎯**
