# Guide de Démarrage Rapide

## Installation en 5 minutes

### 1. Cloner et installer

```bash
git clone <votre-repo>
cd embeddingsall
chmod +x setup.sh
./setup.sh
```

### 2. Configurer les clés API

Éditez le fichier `.env` :

```bash
nano .env
```

Remplissez vos clés :
```env
AZURE_FORM_RECOGNIZER_ENDPOINT=https://...
AZURE_FORM_RECOGNIZER_KEY=...
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_KEY=...
```

### 3. Configurer Supabase

1. Allez dans votre projet Supabase
2. Ouvrez l'éditeur SQL
3. Copiez-collez le contenu de `supabase_setup.sql`
4. Exécutez le script

### 4. Tester

```bash
# Placer un document de test
cp votre-document.pdf data/input/

# Traiter sans upload (test local)
python main.py -i data/input/votre-document.pdf -o data/processed

# Traiter avec upload vers Supabase
python main.py -i data/input/votre-document.pdf --upload
```

## Commandes Utiles

### Traiter un fichier unique
```bash
python main.py -i data/input/document.pdf --upload
```

### Traiter un dossier complet
```bash
python main.py -i data/input --upload
```

### Activer les logs détaillés
```bash
python main.py -i data/input --log-level DEBUG --log-file logs/debug.log
```

### Utiliser une table différente
```bash
python main.py -i data/input --upload --table mes_documents
```

## Vérification

### Vérifier l'installation
```bash
source venv/bin/activate
python -c "import azure.ai.formrecognizer; import openai; import supabase; print('✅ Toutes les dépendances sont installées')"
```

### Vérifier la configuration
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Azure:', '✅' if os.getenv('AZURE_FORM_RECOGNIZER_KEY') else '❌'); print('OpenAI:', '✅' if os.getenv('OPENAI_API_KEY') else '❌'); print('Supabase:', '✅' if os.getenv('SUPABASE_URL') else '❌')"
```

## Exemples

### Exemple Python
```bash
python examples/example_usage.py
```

Choisissez un exemple à exécuter pour voir comment utiliser les différents modules.

## Obtenir les clés API

### Azure Form Recognizer
1. Allez sur [portal.azure.com](https://portal.azure.com)
2. Créez une ressource "Form Recognizer" ou "Cognitive Services"
3. Dans "Keys and Endpoint", copiez :
   - Endpoint → `AZURE_FORM_RECOGNIZER_ENDPOINT`
   - Key 1 → `AZURE_FORM_RECOGNIZER_KEY`

### OpenAI
1. Allez sur [platform.openai.com](https://platform.openai.com)
2. Menu "API keys"
3. "Create new secret key"
4. Copiez la clé → `OPENAI_API_KEY`

### Supabase
1. Allez sur [supabase.com](https://supabase.com)
2. Créez un nouveau projet
3. Dans "Settings" → "API"
4. Copiez :
   - URL → `SUPABASE_URL`
   - anon/public key → `SUPABASE_KEY`

## Dépannage Rapide

### "ModuleNotFoundError"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Azure endpoint et key doivent être fournis"
```bash
# Vérifiez que .env existe et contient vos clés
cat .env | grep AZURE
```

### "Table does not exist"
```bash
# Exécutez supabase_setup.sql dans Supabase
```

## Structure des Résultats

Les fichiers JSON générés ont cette structure :

```json
[
  {
    "file_path": "data/input/document.pdf",
    "chunk_index": 0,
    "chunk_text": "Contenu du chunk...",
    "embedding": [0.123, -0.456, ...],
    "page_count": 5,
    "metadata": {
      "total_chunks": 10,
      "chunk_size": 856
    }
  }
]
```

## Prochaines Étapes

1. ✅ Installer et configurer
2. ✅ Tester avec un document
3. ✅ Uploader vers Supabase
4. 📚 Lire le [README complet](README.md)
5. 🔍 Implémenter la recherche sémantique
6. 🚀 Intégrer dans votre application

## Support

- 📖 Documentation complète : [README.md](README.md)
- 💡 Exemples de code : `examples/example_usage.py`
- 🐛 Problèmes : Ouvrez une issue sur GitHub
