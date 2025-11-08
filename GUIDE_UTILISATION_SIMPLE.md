# 🚀 GUIDE D'UTILISATION ULTRA-SIMPLE

## ✅ LE PLUS SIMPLE : Traiter UN Dossier Complet

**Vous avez un dossier avec plein de fichiers ? Utilisez ceci :**

```bash
python process_all.py -i "C:\chemin\vers\votre\dossier" --upload
```

C'est **TOUT** ! Le système va :
- ✅ Détecter automatiquement tous les fichiers
- ✅ Choisir le bon traitement (OCR pour PDF/images, lecture directe pour TXT)
- ✅ Gérer les fichiers trop grands
- ✅ Continuer même si un fichier plante
- ✅ Tout uploader dans Supabase

---

## 📁 Types de Fichiers Supportés

| Type | Extensions | Traitement |
|------|-----------|------------|
| **Texte** | `.txt`, `.md`, `.csv`, `.json`, `.xml` | Lecture directe |
| **PDF** | `.pdf` | Azure OCR |
| **Images** | `.jpg`, `.png`, `.tiff`, `.bmp` | Azure OCR |
| **Autres** | Tout autre fichier | Tentative de lecture texte |

---

## 💡 Exemples Concrets

### Exemple 1 : Dossier de Factures

```bash
# Vous avez un dossier C:\Mes_Factures avec des PDF
python process_all.py -i "C:\Mes_Factures" --upload
```

**Résultat :**
- Toutes les factures sont extraites
- Embeddings générés
- Tout dans Supabase, searchable !

### Exemple 2 : Mélange de Fichiers

```bash
# Un dossier avec PDF, TXT, images, etc.
python process_all.py -i "C:\Mes_Documents" --upload
```

**Résultat :**
- Le script détecte automatiquement chaque type
- PDF/images → OCR
- TXT → Lecture directe
- Tout traité et uploadé !

### Exemple 3 : Test Local (sans Supabase)

```bash
# Juste pour tester, sans uploader
python process_all.py -i "C:\Test"
```

### Exemple 4 : Avec Logs Détaillés

```bash
# Pour voir exactement ce qui se passe
python process_all.py -i "C:\Mes_Documents" --upload --log-level DEBUG
```

---

## 🔧 Options Disponibles

```bash
python process_all.py --help
```

**Options principales :**
- `-i` ou `--input` : Dossier à traiter (REQUIS)
- `--upload` : Upload vers Supabase (sans ça = juste extraction)
- `--log-level` : DEBUG, INFO, WARNING, ERROR

---

## 📊 Que Fait le Script ?

Pour **CHAQUE fichier** dans votre dossier :

1. **Détection** : Quel type de fichier ?
   - PDF/Image → OCR Azure
   - TXT/CSV/JSON → Lecture directe
   - Autre → Essai lecture texte

2. **Extraction** : Récupère le texte

3. **Découpage** : Coupe en chunks intelligents (1000 caractères avec overlap)

4. **Embeddings** : Génère les vecteurs OpenAI

5. **Upload** : Envoie vers Supabase (si --upload)

6. **Continue** : Même si un fichier plante, ça continue avec les autres !

---

## 🎯 Gestion des Erreurs

Le script est **ROBUSTE** :

- ❌ Fichier trop grand ? → Avertissement, on skip
- ❌ Format bizarre ? → On essaie de lire en texte
- ❌ Erreur OCR ? → On log et on continue
- ❌ Un fichier plante ? → Les autres continuent

À la fin, vous avez un **rapport** :
```
✅ Succès: 45
❌ Erreurs: 3
📁 Total: 48
```

---

## 🔍 Vérifier les Résultats

### Dans Supabase

1. Allez sur https://supabase.com/dashboard
2. Ouvrez votre projet
3. "Table Editor" → Table "documents"
4. Vous voyez TOUS vos fichiers !

### Rechercher

Créez `recherche.py` :

```python
from dotenv import load_dotenv
from src.embeddings import EmbeddingGenerator
from src.supabase_client import SupabaseUploader

load_dotenv()

question = "montant total des factures"

embedder = EmbeddingGenerator()
query_embedding = embedder.generate_embedding(question)

uploader = SupabaseUploader()
results = uploader.search_similar(
    table_name="documents",
    query_embedding=query_embedding,
    limit=10
)

for i, r in enumerate(results, 1):
    print(f"{i}. {r['metadata']['file_name']}: {r['content'][:100]}...")
```

Puis : `python recherche.py`

---

## 💰 Coûts

Avec vos **$200 OpenAI** :

- 1 fichier moyen (10 pages) ≈ $0.01
- 100 fichiers ≈ $1
- 1000 fichiers ≈ $10
- **20,000 fichiers** avec $200 !

Azure OCR est déjà payé (dans votre abonnement).

---

## ❓ Problèmes Courants

### "Fichier trop grand"

Le script vous le dit et skip automatiquement. Pas de problème !

### "Erreur OCR"

Fichier corrompu ou format pas supporté par Azure. Le script continue.

### "Pas de texte extrait"

Le fichier est vide ou illisible. Check manuellement.

---

## 🎉 RÉSUMÉ

**Une seule commande pour TOUT traiter :**

```bash
python process_all.py -i "C:\Votre\Dossier" --upload
```

C'est TOUT ce que vous avez besoin ! 🚀

---

## 📞 Besoin d'Aide ?

Regardez les logs :
```bash
python process_all.py -i "C:\Dossier" --upload --log-level DEBUG
```

Le script vous dira exactement ce qui se passe !
