# 🤖 Système de Chatbot RAG avec MCP Server

Ce projet fournit un système complet de recherche sémantique et de chatbot basé sur vos documents.

## 📋 Composants

### 1. **Recherche Sémantique** (`src/semantic_search.py`)
Module pour effectuer des recherches sémantiques dans la base de données Supabase.

### 2. **Serveur MCP** (`mcp_server.py`)
Serveur compatible avec le Model Context Protocol pour exposer les fonctionnalités de recherche.

### 3. **Chatbot RAG** (`chatbot.py`)
Interface conversationnelle qui utilise RAG (Retrieval Augmented Generation) pour répondre aux questions.

---

## 🚀 Installation

### Prérequis

1. **Python 3.8+**
2. **Variables d'environnement** dans `.env`:
   ```env
   OPENAI_API_KEY=sk-...
   SUPABASE_URL=https://...
   SUPABASE_KEY=eyJ...
   ```

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Configuration Supabase

**IMPORTANT**: Avant d'utiliser le système, vous devez exécuter le script SQL dans Supabase.

1. Ouvrez votre dashboard Supabase
2. Allez dans **SQL Editor**
3. Copiez-collez le contenu de `supabase_setup.sql`
4. Exécutez le script

Cela créera:
- La table `documents` avec l'extension pgvector
- La fonction `match_documents()` pour la recherche vectorielle
- Les index nécessaires pour de bonnes performances

---

## 📚 Utilisation

### 1. Recherche Sémantique (Python)

```python
from src.semantic_search import SemanticSearchEngine

# Initialiser le moteur
engine = SemanticSearchEngine()

# Rechercher
results = engine.search(
    query="Quelles sont les informations sur les contrats?",
    limit=5,
    threshold=0.7
)

# Afficher les résultats
for result in results:
    print(f"{result['file_name']}: {result['similarity']:.1%}")
    print(result['content'][:200])
    print()
```

### 2. Chatbot RAG (CLI)

#### Mode Interactif

```bash
python chatbot.py
```

Exemple de session:
```
🤖 CHATBOT RAG - MODE INTERACTIF
======================================================================

💬 Votre question: Quels sont les principaux contrats mentionnés?

🔍 Recherche de documents pour: Quels sont les principaux contrats...
✅ 3 documents trouvés

🤖 Réponse:

D'après les documents, les principaux contrats mentionnés sont:
1. Cashflex Sarl - CHF 25,080 (01.01.2021)
2. Centre ITS - CHF 107,091 (01.01.2020)

Ces informations proviennent des fichiers PDF de facturation.

======================================================================
📚 SOURCES UTILISÉES (3 documents):
======================================================================

1. 1_6053.01.0201_Cashflex_Sarl_CHF_25080_01.01.2021.pdf
   Pertinence: 87.3%
   Chunk: 0

2. 1_6053.01.0202_Centre_ITS_CHF_107091_01.01.2020_.pdf
   Pertinence: 82.1%
   Chunk: 0
```

#### Mode Question Unique

```bash
# Poser une seule question
python chatbot.py -q "Quel est le montant total des contrats?"

# Avec options
python chatbot.py -q "Question?" -m gpt-4 -l 10 -t 0.8
```

**Options:**
- `-q, --question`: Question à poser (mode non-interactif)
- `-m, --model`: Modèle OpenAI (défaut: gpt-4o-mini)
- `-l, --limit`: Nombre de documents à récupérer (défaut: 5)
- `-t, --threshold`: Seuil de similarité 0-1 (défaut: 0.7)
- `--no-sources`: Ne pas afficher les sources

**Commandes interactives:**
- `reset` : Réinitialiser la conversation
- `stats` : Afficher les statistiques de la base
- `quit` ou `exit` : Quitter

### 3. Serveur MCP

Le serveur MCP expose la recherche sémantique aux applications compatibles MCP (Claude Desktop, Cline, etc.).

#### Démarrage du serveur

```bash
python mcp_server.py
```

#### Configuration pour Claude Desktop

Ajoutez cette configuration à votre fichier de configuration Claude Desktop:

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/claude/claude_desktop_config.json
```

Contenu:
```json
{
  "mcpServers": {
    "documents-search": {
      "command": "python",
      "args": [
        "C:\\chemin\\vers\\embeddingsall\\mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\chemin\\vers\\embeddingsall",
        "OPENAI_API_KEY": "sk-...",
        "SUPABASE_URL": "https://...",
        "SUPABASE_KEY": "eyJ..."
      }
    }
  }
}
```

#### Outils disponibles via MCP

1. **search_documents**: Recherche sémantique
   - Paramètres: `query`, `limit`, `threshold`
   - Retourne les meilleurs résultats avec scores

2. **get_context_for_rag**: Contexte pour RAG
   - Paramètres: `query`, `limit`, `threshold`
   - Retourne le contexte formaté pour un prompt

3. **get_database_stats**: Statistiques
   - Retourne le nombre de documents, fichiers, etc.

---

## 🔧 Architecture

```
┌─────────────────┐
│   Documents     │
│  (PDF, TXT...) │
└────────┬────────┘
         │
         │ process_fast.py
         ▼
┌─────────────────┐
│ Azure OCR +     │
│ PDF Extractor   │
└────────┬────────┘
         │
         │ Extraction texte
         ▼
┌─────────────────┐
│  OpenAI API     │
│  (Embeddings)   │
└────────┬────────┘
         │
         │ Embeddings (1536 dim)
         ▼
┌─────────────────┐
│   Supabase      │
│  (PostgreSQL +  │
│    pgvector)    │
└────────┬────────┘
         │
         │ Recherche vectorielle
         ▼
┌─────────────────────────────────────┐
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │   Chatbot    │  │ MCP Server  │ │
│  │     RAG      │  │             │ │
│  └──────────────┘  └─────────────┘ │
│                                     │
│  ┌──────────────┐                  │
│  │  Semantic    │                  │
│  │   Search     │                  │
│  └──────────────┘                  │
│                                     │
└─────────────────────────────────────┘
```

---

## 📊 Exemples de Questions

Voici quelques exemples de questions que vous pouvez poser au chatbot:

```
💬 Quels sont les principaux sujets abordés dans les documents?

💬 Y a-t-il des informations sur les contrats?

💬 Quels sont les montants mentionnés dans les factures?

💬 Résume les informations sur [nom du fichier].

💬 Compare les contrats Cashflex et Centre ITS.

💬 Quand ont été créés ces documents?
```

---

## 🛠️ Personnalisation

### Modifier le seuil de similarité

```python
# Plus strict (meilleurs résultats seulement)
engine.search(query="...", threshold=0.85)

# Plus permissif (plus de résultats)
engine.search(query="...", threshold=0.6)
```

### Changer le modèle OpenAI

```bash
# Utiliser GPT-4 (plus puissant, plus cher)
python chatbot.py -m gpt-4

# Utiliser GPT-4 Turbo
python chatbot.py -m gpt-4-turbo-preview
```

### Augmenter le nombre de sources

```bash
# Récupérer plus de contexte
python chatbot.py -l 10 -t 0.65
```

---

## 🐛 Résolution de problèmes

### Erreur "No module named 'mcp'"

```bash
pip install mcp>=0.9.0
```

### Erreur "match_documents function does not exist"

Vous devez exécuter `supabase_setup.sql` dans votre dashboard Supabase.

### Erreur "No results found"

1. Vérifiez que vous avez des documents dans la base:
   ```python
   from src.supabase_client import SupabaseUploader
   uploader = SupabaseUploader()
   stats = uploader.get_table_stats("documents")
   print(stats)
   ```

2. Essayez avec un seuil plus bas:
   ```bash
   python chatbot.py -q "question" -t 0.5
   ```

### Le chatbot ne répond pas correctement

1. Vérifiez votre clé API OpenAI
2. Essayez un modèle plus puissant (`-m gpt-4`)
3. Augmentez le nombre de sources (`-l 10`)

---

## 💡 Conseils d'utilisation

1. **Démarrez avec le mode interactif** pour tester
2. **Utilisez 'stats'** pour vérifier le contenu de la base
3. **Ajustez le threshold** selon vos besoins:
   - 0.7-0.8: Bon équilibre
   - 0.8-0.9: Très pertinent seulement
   - 0.5-0.7: Plus de résultats
4. **Regardez les sources** pour comprendre d'où vient la réponse
5. **Utilisez 'reset'** si la conversation dévie

---

## 📝 Logs et Debugging

Pour voir plus de détails:

```bash
# Activer les logs détaillés
export LOG_LEVEL=DEBUG
python chatbot.py
```

Ou modifier directement dans le code:
```python
logging.basicConfig(level=logging.DEBUG)
```

---

## 🚀 Prochaines étapes

1. **Tester le système**:
   ```bash
   python chatbot.py
   ```

2. **Ajouter plus de documents**:
   ```bash
   python process_fast.py -i "dossier/" --upload --workers 5
   ```

3. **Intégrer avec Claude Desktop**:
   - Configurer le MCP server
   - Utiliser les outils de recherche directement dans Claude

4. **Optimiser les performances**:
   - Ajuster les index Supabase
   - Tuner les paramètres de recherche

---

## 📧 Support

Pour toute question ou problème:
1. Vérifiez les logs
2. Testez avec `stats` et `reset`
3. Consultez la documentation Supabase
4. Vérifiez les limites de votre API OpenAI

Bon chatbot! 🎉
