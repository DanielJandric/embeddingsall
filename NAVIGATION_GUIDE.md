# 🧭 Guide Complet du Système de Navigation

Ce guide explique comment utiliser le système ultra-complet de métadonnées et de navigation dans vos documents.

---

## 🎯 Vue d'ensemble

Le système extrait automatiquement **100+ champs de métadonnées** pour chaque document et fournit une **interface web de navigation** puissante.

### **Métadonnées extraites automatiquement :**

| Catégorie | Champs | Exemples |
|-----------|--------|----------|
| **📍 Localisations** | 15+ | Cantons, communes, codes postaux, adresses |
| **💰 Financier** | 20+ | Montants CHF/EUR/USD, pourcentages, TVA |
| **📅 Temporel** | 15+ | Dates, années, périodes |
| **📏 Dimensions** | 10+ | Surfaces m², volumes m³, pièces, étages |
| **👥 Parties** | 10+ | Entreprises, bailleur, locataire, vendeur, acheteur |
| **🔢 Références** | 5+ | Numéros IDE, dossiers, parcelles |
| **📞 Contacts** | 5+ | Emails, téléphones, sites web |
| **📊 Structure** | 10+ | Longueur, sections, numérotation |
| **🏷️ Classification** | 10+ | Type document, type bien, catégorie |
| **🗣️ Linguistique** | 5+ | Langue, formalité |
| **⭐ Qualité** | 5+ | Scores de complétude, richesse |

---

## 🚀 Étape 1 : Appliquer les métadonnées aux documents existants

### **A. Mode Dry-Run (Test sans modifications)**

```powershell
cd C:\Users\DanielJandric\embeddingsall
python apply_advanced_metadata.py --dry-run --limit 10
```

Ceci analyse 10 documents et affiche ce qui serait extrait, **sans modifier la base**.

**Résultat attendu :**
```
📥 Récupération des documents depuis Supabase...
✅ 10 documents récupérés

🔄 Traitement de 10 documents...
[████████████████████] 100%

📊 RAPPORT D'ENRICHISSEMENT
======================================================================
✅ Succès: 10
❌ Erreurs: 0
📊 Moyenne de nouveaux champs par document: 45.2

📈 Top 10 des métadonnées extraites:
   longueur_caracteres: 10 documents (100.0%)
   langue_detectee: 9 documents (90.0%)
   annees_mentionnees: 8 documents (80.0%)
   montants_chf: 7 documents (70.0%)
   ...

⚠️  MODE DRY-RUN : Aucun changement appliqué
```

### **B. Application réelle sur TOUS les documents**

```powershell
python apply_advanced_metadata.py
```

Ceci applique les métadonnées à **TOUS** vos 184 documents.

⏱️ **Durée estimée :** 5-10 minutes pour 184 documents

**Options avancées :**

```powershell
# Traiter seulement 50 documents
python apply_advanced_metadata.py --limit 50

# Avec rapport détaillé
python apply_advanced_metadata.py --output-report mon_rapport.json
```

---

## 🌐 Étape 2 : Lancer l'interface web de navigation

### **Démarrage du serveur**

```powershell
python navigation_web.py
```

**Résultat :**
```
🚀 Démarrage du navigateur web...
📍 Interface disponible sur: http://localhost:8080
📊 API docs: http://localhost:8080/docs
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### **Accéder à l'interface**

Ouvrir dans votre navigateur : http://localhost:8080

---

## 📊 Étape 3 : Utiliser l'interface web

### **A. Dashboard principal**

Le dashboard affiche :

**Statistiques globales :**
- 📁 Total documents : 184
- 📦 Total chunks : 2601
- 📊 Taille moyenne : 125 KB
- 🏷️ Champs métadonnées : 87

**Navigation rapide :**
- 📍 **Par commune** : Aigle (45 docs), Lausanne (32 docs), Vevey (18 docs)...
- 📁 **Par catégorie** : Immobilier (78 docs), Juridique (56 docs), Finance (32 docs)...
- 📅 **Par année** : 2023 (67 docs), 2024 (45 docs), 2022 (38 docs)...

### **B. Recherche rapide**

Dans la barre de recherche :
```
Combien vaut l'immeuble de Aigle
```

Résultats instantanés avec surlignage des passages pertinents.

### **C. Filtres avancés**

**Exemple 1 : Documents immobiliers à Aigle en 2023**
```
Commune : Aigle
Catégorie : immobilier
Année min : 2023
Année max : 2023
```
→ Cliquer "Rechercher avec filtres"

**Exemple 2 : Contrats avec loyer > 2000 CHF**
```
Catégorie : juridique
Type : contrat
Montant min CHF : 2000
```

**Exemple 3 : Évaluations avec valeur > 10 millions**
```
Type document : évaluation
Montant min CHF : 10000000
```

### **D. Export des résultats**

**Export CSV :**
```
GET http://localhost:8080/api/export/csv?commune=Aigle
```

Télécharge un CSV avec tous les documents filtrés.

---

## 🔍 Étape 4 : API REST pour intégrations

### **Endpoints disponibles**

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/stats` | GET | Statistiques globales |
| `/api/navigation` | GET | Options de navigation (communes, catégories, années) |
| `/api/search` | GET | Recherche avec filtres multiples |
| `/api/document/{id}` | GET | Détails d'un document |
| `/api/export/csv` | GET | Export CSV filtré |

### **Exemples d'utilisation**

**1. Récupérer les statistiques**
```bash
curl http://localhost:8080/api/stats
```

**2. Rechercher tous les documents de 2023 à Aigle**
```bash
curl "http://localhost:8080/api/search?commune=Aigle&annee=2023"
```

**3. Rechercher par montant**
```bash
curl "http://localhost:8080/api/search?montant_min_chf=1000000&montant_max_chf=20000000"
```

**4. Rechercher par surface**
```bash
curl "http://localhost:8080/api/search?surface_min_m2=1000&surface_max_m2=3000"
```

---

## 💡 Cas d'usage avancés

### **Cas 1 : Analyse de portefeuille immobilier**

**Question :** "Quelle est la valeur totale de mon portefeuille immobilier à Aigle ?"

**Méthode :**
1. Interface web → Filtrer : Commune=Aigle, Catégorie=immobilier
2. Export CSV
3. Excel : `=SOMME(Colonne_Montant)`

**Ou via API :**
```python
import requests

response = requests.get(
    "http://localhost:8080/api/search",
    params={"commune": "Aigle", "categorie": "immobilier"}
)

docs = response.json()["documents"]
total_value = sum(
    doc["metadata"].get("montant_max_chf", 0)
    for doc in docs
)

print(f"Valeur totale: CHF {total_value:,.0f}")
```

### **Cas 2 : Suivi des contrats de location**

**Question :** "Quels sont tous mes contrats de location actifs ?"

**Filtres :**
- Type document : contrat
- Catégorie : juridique
- Recherche textuelle : "location" ou "bail"

**Résultat :** Liste de tous les contrats avec loyer, dates, parties.

### **Cas 3 : Conformité et audit**

**Question :** "Quels documents n'ont pas de métadonnées complètes ?"

**Via API :**
```python
response = requests.get("http://localhost:8080/api/search")
docs = response.json()["documents"]

incomplete = [
    doc for doc in docs
    if doc["metadata"].get("overall_quality_score", 0) < 50
]

print(f"{len(incomplete)} documents incomplets")
```

### **Cas 4 : Analyse temporelle**

**Question :** "Évolution des valeurs immobilières par année"

**Filtres par année :**
- 2020 → Montant moyen
- 2021 → Montant moyen
- 2022 → Montant moyen
- 2023 → Montant moyen
- 2024 → Montant moyen

**Visualisation :** Graphique d'évolution

---

## 🔗 Intégration avec Claude/ChatGPT

### **Via MCP (Claude Desktop)**

Une fois les métadonnées appliquées, Claude peut faire des recherches ultra-précises :

```
"Trouve tous les documents immobiliers à Aigle avec une valeur supérieure à 10 millions"

→ Claude utilise les métadonnées pour filtrer instantanément
```

### **Via API REST (ChatGPT)**

ChatGPT peut interroger l'API de navigation :

```
"Liste tous les contrats de location à Lausanne"

→ ChatGPT appelle: GET /api/search?commune=Lausanne&type_document=contrat
```

---

## 📈 Analyse avec Python (Avancé)

### **Script d'analyse complète**

```python
import requests
import pandas as pd
import matplotlib.pyplot as plt

# 1. Récupérer tous les documents
response = requests.get("http://localhost:8080/api/search?limit=200")
docs = response.json()["documents"]

# 2. Créer un DataFrame
data = []
for doc in docs:
    meta = doc.get("metadata", {})
    data.append({
        "file": doc["file_path"],
        "commune": meta.get("commune_principale"),
        "annee": meta.get("annee_la_plus_recente"),
        "categorie": meta.get("categorie_principale"),
        "montant_chf": meta.get("montant_max_chf"),
        "surface_m2": meta.get("surface_max_m2")
    })

df = pd.DataFrame(data)

# 3. Analyses
print("=== Analyse par commune ===")
print(df.groupby("commune").size())

print("\n=== Valeur totale par commune ===")
print(df.groupby("commune")["montant_chf"].sum())

print("\n=== Documents par année ===")
print(df.groupby("annee").size())

# 4. Graphiques
df.groupby("commune").size().plot(kind="bar", title="Documents par commune")
plt.show()

df.groupby("annee").size().plot(kind="line", title="Documents par année")
plt.show()
```

---

## 🎯 Checklist de déploiement

### **Étape 1 : Enrichissement**
- [ ] Tester avec `--dry-run --limit 10`
- [ ] Vérifier les métadonnées extraites
- [ ] Appliquer sur tous les documents
- [ ] Vérifier le rapport d'enrichissement

### **Étape 2 : Interface web**
- [ ] Démarrer `python navigation_web.py`
- [ ] Accéder à http://localhost:8080
- [ ] Tester la recherche rapide
- [ ] Tester les filtres avancés
- [ ] Tester l'export CSV

### **Étape 3 : Intégrations**
- [ ] Tester l'API REST
- [ ] Configurer Claude/ChatGPT
- [ ] Créer des scripts d'analyse personnalisés

---

## 🔒 Sécurité

### **Accès local uniquement (par défaut)**

Par défaut, l'interface est accessible uniquement depuis votre machine (`localhost:8080`).

### **Exposition sur réseau local**

Pour accéder depuis d'autres machines du réseau :

```python
# Dans navigation_web.py, ligne finale :
uvicorn.run(app, host="0.0.0.0", port=8080)
```

Puis accéder via : `http://IP-DE-VOTRE-PC:8080`

### **Exposition sur Internet**

**Avec ngrok :**
```powershell
ngrok http 8080
```

⚠️ **Ajouter une authentification** si vous exposez sur Internet !

---

## 📊 Métriques de qualité

Après enrichissement, chaque document a des **scores de qualité** :

| Score | Signification |
|-------|---------------|
| **0-30** | Peu de métadonnées extraites |
| **31-50** | Métadonnées basiques |
| **51-70** | Bonnes métadonnées |
| **71-85** | Très bonnes métadonnées |
| **86-100** | Métadonnées excellentes |

**Améliorer les scores :**
- Ajouter des métadonnées manuelles via `upload_with_metadata.py`
- Utiliser des conventions de nommage cohérentes
- Structurer les documents (sections, numérotation)

---

## ❓ Dépannage

### **Problème : Peu de métadonnées extraites**

**Causes possibles :**
- Documents scannés avec OCR de mauvaise qualité
- Texte en langue non détectée
- Format de document non structuré

**Solutions :**
- Améliorer la qualité OCR
- Ajouter des métadonnées manuellement
- Utiliser des templates de métadonnées

### **Problème : Interface web lente**

**Solutions :**
- Limiter le nombre de résultats (paramètre `limit`)
- Ajouter des index PostgreSQL sur les champs JSON
- Utiliser le cache

### **Problème : Recherche ne trouve rien**

**Solutions :**
- Vérifier que les métadonnées sont appliquées
- Essayer des filtres plus larges
- Vérifier l'orthographe

---

## 🎉 Résultat final

Avec ce système, vous pouvez :

✅ **Naviguer** dans 184 documents avec 100+ critères
✅ **Filtrer** par commune, année, montant, surface, catégorie, etc.
✅ **Rechercher** instantanément avec métadonnées enrichies
✅ **Analyser** votre portefeuille documentaire
✅ **Exporter** les résultats en CSV
✅ **Intégrer** avec Claude, ChatGPT, Power BI, Excel
✅ **Visualiser** les statistiques et tendances

**Votre base documentaire est maintenant ultra-organisée et navigable ! 🚀**
