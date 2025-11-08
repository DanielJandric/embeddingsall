# Système de Traitement de Documents avec OCR, Embeddings et Supabase

Un pipeline complet pour traiter des documents (images et PDFs), extraire le texte via Azure OCR, générer des embeddings avec OpenAI, et stocker les résultats dans Supabase pour la recherche sémantique.

## 🚀 Fonctionnalités

- **OCR Azure** : Extraction de texte depuis images et PDFs avec Azure Form Recognizer
- **Embeddings OpenAI** : Génération d'embeddings vectoriels pour la recherche sémantique
- **Supabase** : Stockage et recherche vectorielle dans une base de données cloud
- **Traitement par lots** : Support pour le traitement de grandes quantités de documents
- **Chunking intelligent** : Découpage automatique des longs textes avec chevauchement
- **Retry automatique** : Gestion robuste des erreurs avec retry exponentiel

## 📋 Prérequis

- Python 3.8+
- Un compte Azure avec Cognitive Services (Form Recognizer)
- Une clé API OpenAI
- Un projet Supabase

## 🔧 Installation

1. **Cloner le dépôt**
```bash
git clone <votre-repo>
cd embeddingsall
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
```bash
cp .env.example .env
```

Éditez le fichier `.env` avec vos clés API :

```env
# Azure Cognitive Services
AZURE_FORM_RECOGNIZER_ENDPOINT=https://votre-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=votre_cle_azure

# OpenAI
OPENAI_API_KEY=sk-votre_cle_openai
EMBEDDING_MODEL=text-embedding-3-small

# Supabase
SUPABASE_URL=https://votre-projet.supabase.co
SUPABASE_KEY=votre_cle_supabase

# Configuration
BATCH_SIZE=100
CHUNK_SIZE=1000
MAX_WORKERS=4
```

## 🗄️ Configuration Supabase

Avant d'utiliser le script, créez la table dans Supabase avec cette requête SQL :

```sql
-- Activer l'extension pour les vecteurs
CREATE EXTENSION IF NOT EXISTS vector;

-- Créer la table documents
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- Pour text-embedding-3-small
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Créer un index pour la recherche vectorielle
CREATE INDEX documents_embedding_idx
ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Créer un index sur les métadonnées
CREATE INDEX documents_metadata_idx
ON documents
USING GIN (metadata);

-- Fonction pour la recherche de similarité
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding VECTOR(1536),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
  SELECT
    id,
    content,
    metadata,
    1 - (embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
```

## 📝 Utilisation

### Traiter un fichier unique

```bash
python main.py -i data/input/document.pdf -o data/processed
```

### Traiter un répertoire complet

```bash
python main.py -i data/input -o data/processed
```

### Traiter et uploader vers Supabase

```bash
python main.py -i data/input -o data/processed --upload --table documents
```

### Options disponibles

```
usage: main.py [-h] -i INPUT [-o OUTPUT] [-t TABLE] [--upload]
               [--log-level {DEBUG,INFO,WARNING,ERROR}] [--log-file LOG_FILE]

Arguments:
  -i, --input      Répertoire ou fichier d'entrée (requis)
  -o, --output     Répertoire de sortie pour les JSON (défaut: data/processed)
  -t, --table      Nom de la table Supabase (défaut: documents)
  --upload         Upload les résultats vers Supabase
  --log-level      Niveau de logging (défaut: INFO)
  --log-file       Fichier de log optionnel
```

## 📁 Structure du projet

```
embeddingsall/
├── main.py                 # Script principal
├── requirements.txt        # Dépendances Python
├── .env.example           # Exemple de configuration
├── .gitignore
├── README.md
├── src/
│   ├── __init__.py
│   ├── azure_ocr.py       # Module OCR Azure
│   ├── embeddings.py      # Module génération d'embeddings
│   ├── supabase_client.py # Module client Supabase
│   └── logger.py          # Configuration du logging
└── data/
    ├── input/             # Documents à traiter
    └── processed/         # Résultats JSON
```

## 🔄 Workflow

1. **Extraction OCR** : Le texte est extrait des documents (images/PDFs) via Azure Form Recognizer
2. **Chunking** : Les longs textes sont découpés en chunks avec chevauchement
3. **Embeddings** : Chaque chunk est transformé en vecteur d'embedding via OpenAI
4. **Sauvegarde locale** : Les résultats sont sauvegardés en JSON
5. **Upload Supabase** : Les embeddings sont uploadés dans Supabase (optionnel)

## 💡 Exemples d'utilisation

### Utilisation programmatique

```python
from src.azure_ocr import AzureOCRProcessor
from src.embeddings import EmbeddingGenerator
from src.supabase_client import SupabaseUploader

# Initialiser les processeurs
ocr = AzureOCRProcessor()
embedder = EmbeddingGenerator()
uploader = SupabaseUploader()

# Traiter un document
ocr_result = ocr.process_file("document.pdf")
embeddings = embedder.process_ocr_result(ocr_result)

# Upload vers Supabase
uploader.upload_embeddings("documents", embeddings)
```

### Recherche sémantique

```python
from src.embeddings import EmbeddingGenerator
from src.supabase_client import SupabaseUploader

# Générer l'embedding de la requête
embedder = EmbeddingGenerator()
query_embedding = embedder.generate_embedding("Qu'est-ce que l'IA?")

# Rechercher dans Supabase
uploader = SupabaseUploader()
results = uploader.search_similar(
    table_name="documents",
    query_embedding=query_embedding,
    limit=5,
    threshold=0.7
)

for result in results:
    print(f"Similarité: {result['similarity']:.2f}")
    print(f"Contenu: {result['content'][:200]}...")
    print("---")
```

## 🎯 Formats supportés

- **Images** : JPG, JPEG, PNG, BMP, TIFF, TIF
- **Documents** : PDF

## ⚡ Performance

- Traitement par lots pour optimiser les appels API
- Retry automatique avec backoff exponentiel
- Chunking intelligent pour gérer les longs documents
- Support du traitement parallèle (configurable)

## 🔒 Sécurité

- Les clés API sont stockées dans des variables d'environnement
- Le fichier `.env` est dans `.gitignore`
- Utilisation de HTTPS pour toutes les communications API

## 🐛 Dépannage

### Erreur "Azure endpoint et key doivent être fournis"
- Vérifiez que votre fichier `.env` contient les bonnes clés
- Assurez-vous que le fichier `.env` est à la racine du projet

### Erreur "Table does not exist"
- Exécutez les requêtes SQL de configuration dans Supabase
- Vérifiez que l'extension `vector` est activée

### Erreur de rate limit OpenAI
- Réduisez `BATCH_SIZE` dans `.env`
- Le système retry automatiquement avec backoff

## 📊 Monitoring

Le script génère des logs détaillés :

```bash
# Avec logs dans un fichier
python main.py -i data/input --upload --log-file logs/processing.log

# Avec niveau DEBUG
python main.py -i data/input --log-level DEBUG
```

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Ouvrir des issues pour les bugs
- Proposer des améliorations
- Soumettre des pull requests

## 📄 Licence

Ce projet est sous licence MIT.

## 🙏 Remerciements

- Azure Cognitive Services pour l'OCR
- OpenAI pour les embeddings
- Supabase pour la base de données vectorielle

## 📞 Support

Pour toute question ou problème, ouvrez une issue sur GitHub.
