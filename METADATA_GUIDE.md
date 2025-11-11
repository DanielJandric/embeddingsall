# 📊 Guide des Métadonnées Enrichies

Ce guide explique comment ajouter des **métadonnées pertinentes** à vos documents pour améliorer la recherche et l'organisation.

---

## 🎯 Pourquoi des métadonnées ?

Les métadonnées permettent de :

1. ✅ **Filtrer** les recherches (ex: "documents de 2023 uniquement")
2. ✅ **Contextualiser** les résultats (ex: "commune: Aigle")
3. ✅ **Organiser** votre base documentaire
4. ✅ **Enrichir** les réponses de l'IA
5. ✅ **Analyser** vos données (ex: "valeur totale du portefeuille")

---

## 📁 Structure des métadonnées

### **Métadonnées automatiques** (extraites automatiquement)

```python
{
    # Depuis le nom de fichier :
    "source_filename": "evaluation_aigle_2023.pdf",
    "source_directory": "C:\\OneDriveExport\\evaluations",
    "extraction_date": "2024-11-08T10:30:00",
    "type_document": "évaluation",  # Si détecté dans le nom
    "annee": 2023,                  # Si détecté dans le nom
    "commune": "Aigle",             # Si détecté dans le nom

    # Depuis le contenu :
    "montants_chf": [14850000, 13500000],
    "montant_max_chf": 14850000,
    "surfaces_m2": [2500, 2200],
    "surface_principale_m2": 2500,
    "dates_mentionnees": ["15.06.2023", "01.01.2023"],
    "langue": "français"
}
```

### **Métadonnées manuelles** (vous les ajoutez)

```python
{
    # Identification :
    "type_document": "évaluation immobilière",
    "categorie": "immobilier",
    "sous_categorie": "évaluation",

    # Localisation :
    "commune": "Aigle",
    "canton": "Vaud",
    "adresse": "Rue du Centre 15",

    # Informations métier :
    "valeur_venale": 14850000,
    "type_bien": "immeuble locatif",
    "nombre_logements": 24,
    "evaluateur": "Expert Immobilier SA",

    # Organisation :
    "tags": ["immobilier", "vaud", "aigle"]
}
```

---

## 🚀 Méthode 1 : Upload avec fichier CSV (Recommandé)

### **Étape 1 : Créer un template CSV**

```powershell
python upload_with_metadata.py -i "C:\OneDriveExport" --create-template
```

Ceci crée `metadata_template.csv` avec extraction automatique de base.

### **Étape 2 : Remplir le CSV dans Excel**

Ouvrir `metadata_template.csv` dans Excel :

| file_path | type_document | commune | canton | annee | valeur_chf | surface_m2 | description | tags |
|-----------|---------------|---------|--------|-------|------------|------------|-------------|------|
| C:\Docs\eval1.pdf | évaluation immobilière | Aigle | Vaud | 2023 | 14850000 | 2500 | Immeuble locatif centre-ville | immobilier,vaud,aigle |
| C:\Docs\contrat1.pdf | contrat de location | Lausanne | Vaud | 2024 | 2500 | 95 | Bail 4.5 pièces | bail,lausanne |

### **Étape 3 : Uploader avec les métadonnées**

```powershell
python upload_with_metadata.py -i "C:\OneDriveExport" --metadata-csv metadata_template.csv
```

---

## 🚀 Méthode 2 : Upload avec fichier JSON (Pour métadonnées complexes)

### **Créer un fichier JSON**

Créer `mes_metadonnees.json` :

```json
{
  "C:\\OneDriveExport\\evaluation_aigle_2023.pdf": {
    "type_document": "évaluation immobilière",
    "commune": "Aigle",
    "valeur_venale": 14850000,
    "type_bien": "immeuble locatif",
    "nombre_logements": 24,
    "evaluateur": "Expert Immobilier SA",
    "date_evaluation": "2023-06-15",
    "rendement_brut_pct": 4.5,
    "tags": ["immobilier", "vaud", "aigle", "locatif"]
  },

  "C:\\OneDriveExport\\contrat_lausanne_2024.pdf": {
    "type_document": "contrat de location",
    "commune": "Lausanne",
    "loyer_mensuel_chf": 2500,
    "surface_m2": 95,
    "nombre_pieces": 4.5,
    "date_debut": "2024-01-01",
    "tags": ["bail", "lausanne", "résidentiel"]
  }
}
```

### **Uploader**

```powershell
python upload_with_metadata.py -i "C:\OneDriveExport" --metadata-json mes_metadonnees.json
```

---

## 📋 Templates de métadonnées par type de document

### **1. Évaluation immobilière**

```json
{
  "type_document": "évaluation immobilière",
  "categorie": "immobilier",
  "commune": "Aigle",
  "canton": "Vaud",
  "adresse": "Rue du Centre 15",
  "type_bien": "immeuble locatif",
  "valeur_venale": 14850000,
  "valeur_rendement": 13500000,
  "surface_totale_m2": 2500,
  "nombre_logements": 24,
  "annee_construction": 1985,
  "annee_renovation": 2015,
  "evaluateur": "Expert Immobilier SA",
  "date_evaluation": "2023-06-15",
  "rendement_brut_pct": 4.5,
  "tags": ["immobilier", "vaud", "évaluation"]
}
```

### **2. Contrat de location**

```json
{
  "type_document": "contrat de location",
  "categorie": "juridique",
  "commune": "Lausanne",
  "adresse": "Avenue de la Gare 42",
  "bailleur": "Immobilière Vaudoise SA",
  "locataire": "Martin Dupont",
  "loyer_mensuel_chf": 2500,
  "charges_mensuelles_chf": 300,
  "surface_m2": 95,
  "nombre_pieces": 4.5,
  "date_debut": "2024-01-01",
  "date_fin": "2026-12-31",
  "depot_garantie_chf": 7500,
  "tags": ["bail", "location", "lausanne"]
}
```

### **3. Rapport financier**

```json
{
  "type_document": "rapport financier",
  "categorie": "finance",
  "societe": "Immobilière Vaudoise SA",
  "exercice": 2023,
  "periode_debut": "2023-01-01",
  "periode_fin": "2023-12-31",
  "chiffre_affaires_chf": 12500000,
  "resultat_net_chf": 1850000,
  "actif_total_chf": 85000000,
  "fonds_propres_chf": 35000000,
  "auditeur": "Cabinet Audit",
  "tags": ["finance", "comptabilité", "2023"]
}
```

### **4. Contrat de vente**

```json
{
  "type_document": "contrat de vente",
  "categorie": "transaction",
  "commune": "Lausanne",
  "vendeur": "Immobilière Vaudoise SA",
  "acheteur": "Fonds Pension XYZ",
  "prix_vente_chf": 5000000,
  "date_signature": "2024-03-15",
  "date_transfert": "2024-06-01",
  "notaire": "Notaire Martin",
  "tags": ["vente", "transaction", "lausanne"]
}
```

### **5. Expertise technique**

```json
{
  "type_document": "expertise technique",
  "categorie": "immobilier",
  "commune": "Montreux",
  "type_bien": "villa",
  "expert": "Bureau Technique Romand",
  "date_expertise": "2024-02-20",
  "etat_general": "moyen",
  "travaux_urgents_chf": 45000,
  "travaux_moyen_terme_chf": 120000,
  "classe_energetique": "E",
  "tags": ["expertise", "diagnostic", "montreux"]
}
```

---

## 🔍 Utiliser les métadonnées dans les recherches

Une fois uploadés avec métadonnées, vous pouvez faire des recherches plus précises :

### **Dans Claude Desktop :**

```
"Recherche tous les contrats de location à Lausanne"
→ Utilise les métadonnées : commune="Lausanne", type_document="contrat de location"

"Trouve les évaluations de 2023 avec une valeur supérieure à 10 millions"
→ Utilise : annee=2023, valeur_venale>10000000

"Liste tous les documents concernant Aigle"
→ Utilise : commune="Aigle"
```

### **Dans votre code Python :**

```python
from src.semantic_search import SemanticSearchEngine

search_engine = SemanticSearchEngine()

# Recherche avec filtre sur métadonnées
results = search_engine.search(
    query="valeur immobilière",
    filters={
        "commune": "Aigle",
        "annee": 2023,
        "type_document": "évaluation immobilière"
    }
)
```

---

## 📊 Métadonnées recommandées par secteur

### **Immobilier**

| Champ | Type | Exemple | Importance |
|-------|------|---------|------------|
| commune | string | "Aigle" | ⭐⭐⭐⭐⭐ |
| canton | string | "Vaud" | ⭐⭐⭐⭐ |
| type_bien | string | "immeuble locatif" | ⭐⭐⭐⭐⭐ |
| valeur_chf | number | 14850000 | ⭐⭐⭐⭐⭐ |
| surface_m2 | number | 2500 | ⭐⭐⭐⭐ |
| annee | number | 2023 | ⭐⭐⭐⭐ |

### **Juridique (Contrats)**

| Champ | Type | Exemple | Importance |
|-------|------|---------|------------|
| type_contrat | string | "location" | ⭐⭐⭐⭐⭐ |
| parties | array | ["A", "B"] | ⭐⭐⭐⭐ |
| date_signature | string | "2024-01-15" | ⭐⭐⭐⭐⭐ |
| date_expiration | string | "2026-12-31" | ⭐⭐⭐⭐ |
| montant_chf | number | 2500 | ⭐⭐⭐⭐ |

### **Finance**

| Champ | Type | Exemple | Importance |
|-------|------|---------|------------|
| exercice | number | 2023 | ⭐⭐⭐⭐⭐ |
| societe | string | "Entreprise SA" | ⭐⭐⭐⭐⭐ |
| resultat_net_chf | number | 1850000 | ⭐⭐⭐⭐ |
| chiffre_affaires_chf | number | 12500000 | ⭐⭐⭐⭐ |
| auditeur | string | "Cabinet X" | ⭐⭐⭐ |

---

## 💡 Conseils pratiques

### **1. Conventions de nommage des fichiers**

Utilisez des noms de fichiers structurés pour extraction automatique :

```
[TYPE]_[LOCALITE]_[DATE]_[DESCRIPTION].pdf

✅ Bon : evaluation_aigle_2023-06_immeuble_locatif.pdf
✅ Bon : contrat_lausanne_2024-01_bail_dupont.pdf
❌ Mauvais : doc1.pdf
❌ Mauvais : scan_20240315.pdf
```

### **2. Organisation des dossiers**

```
OneDriveExport/
├── evaluations/
│   ├── 2023/
│   │   ├── evaluation_aigle_2023-06.pdf
│   │   └── evaluation_vevey_2023-09.pdf
│   └── 2024/
├── contrats/
│   ├── locations/
│   └── ventes/
└── rapports/
    ├── financiers/
    └── techniques/
```

### **3. Tags cohérents**

Utilisez des tags standardisés :

```json
{
  "tags": [
    "immobilier",      // Catégorie principale
    "vaud",            // Localisation
    "aigle",           // Commune
    "locatif",         // Type
    "évaluation"       // Document type
  ]
}
```

### **4. Formats de dates**

Utilisez toujours le format ISO : `YYYY-MM-DD`

```json
{
  "date_evaluation": "2023-06-15",
  "date_debut": "2024-01-01",
  "date_expiration": "2026-12-31"
}
```

### **5. Unités**

Soyez explicite sur les unités :

```json
{
  "valeur_chf": 14850000,        // ✅ Clair
  "surface_m2": 2500,            // ✅ Clair
  "rendement_pct": 4.5,          // ✅ Clair

  "valeur": 14850000,            // ❌ Quelle devise ?
  "surface": 2500,               // ❌ m2 ou pieds carrés ?
  "rendement": 4.5               // ❌ Pourcentage ou ratio ?
}
```

---

## 🔄 Workflow complet

### **Scénario : Vous avez 50 nouveaux documents à uploader**

```powershell
# 1. Créer le template CSV
python upload_with_metadata.py -i "C:\NouveauxDocs" --create-template

# 2. Remplir metadata_template.csv dans Excel
#    (Ajouter : commune, valeur_chf, type_bien, etc.)

# 3. Sauvegarder le CSV

# 4. Uploader avec métadonnées
python upload_with_metadata.py -i "C:\NouveauxDocs" --metadata-csv metadata_template.csv

# 5. Vérifier
python check_supabase_data.py
```

---

## 📈 Analyse de vos données avec métadonnées

Une fois vos documents uploadés avec métadonnées riches, vous pouvez faire des analyses :

```python
# Exemple d'analyse
from src.supabase_client_v2 import SupabaseUploaderV2

uploader = SupabaseUploaderV2()

# Récupérer tous les documents
response = uploader.client.table("documents_full").select("*").execute()

import pandas as pd
df = pd.DataFrame(response.data)

# Analyses possibles :
# - Valeur totale du portefeuille immobilier
total_valeur = df[df['metadata']['type_document'] == 'évaluation']['metadata']['valeur_chf'].sum()

# - Documents par commune
docs_par_commune = df.groupby(df['metadata']['commune']).size()

# - Évolution temporelle
docs_par_annee = df.groupby(df['metadata']['annee']).size()
```

---

## ✅ Checklist métadonnées de qualité

Pour chaque type de document, assurez-vous d'avoir :

**Immobilier :**
- [ ] Commune et canton
- [ ] Type de bien
- [ ] Valeur en CHF
- [ ] Surface en m²
- [ ] Année

**Contrats :**
- [ ] Parties (vendeur, acheteur, bailleur, locataire)
- [ ] Dates (signature, début, fin)
- [ ] Montants
- [ ] Type de contrat

**Finance :**
- [ ] Société
- [ ] Exercice comptable
- [ ] Résultats financiers
- [ ] Dates de période

**Général (tous documents) :**
- [ ] Type de document
- [ ] Catégorie
- [ ] Date
- [ ] Tags pertinents

---

## 🎯 Prochaines étapes

1. ✅ Choisissez votre méthode (CSV ou JSON)
2. ✅ Identifiez les métadonnées pertinentes pour vos documents
3. ✅ Créez un template ou un fichier JSON
4. ✅ Remplissez les métadonnées
5. ✅ Uploadez avec `upload_with_metadata.py`
6. ✅ Testez les recherches enrichies

**Vos documents seront beaucoup plus faciles à retrouver et analyser ! 🚀**
