# 🤖 Connecter ChatGPT à votre système de recherche documentaire

Ce guide explique comment exposer votre système de recherche via une API REST et le connecter à ChatGPT.

## 📋 Table des matières

1. [Architecture](#architecture)
2. [Installation](#installation)
3. [Démarrer l'API](#démarrer-lapi)
4. [Exposer l'API sur Internet](#exposer-lapi-sur-internet)
5. [Configurer ChatGPT](#configurer-chatgpt)
6. [Exemples d'utilisation](#exemples-dutilisation)
7. [Sécurité](#sécurité)

---

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   ChatGPT   │ ◄─────► │  API REST    │ ◄─────► │  Supabase    │
│  (OpenAI)   │  HTTPS  │  FastAPI     │         │  (Vector DB) │
└─────────────┘         └──────────────┘         └──────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │ Fichiers     │
                        │ locaux       │
                        └──────────────┘
```

**Différences avec MCP :**
- **MCP** : Claude Desktop ⟷ Serveur MCP local (stdin/stdout)
- **API REST** : ChatGPT ⟷ API HTTP publique (HTTPS)

---

## Installation

### 1. Installer les dépendances

```powershell
cd C:\Users\DanielJandric\embeddingsall
pip install fastapi uvicorn pydantic
```

### 2. Vérifier que les fichiers sont présents

```powershell
# Fichiers nécessaires
ls api_server.py                    # Serveur API FastAPI
ls chatgpt_actions_schema.yaml      # Schéma OpenAPI pour ChatGPT
ls .env                              # Variables d'environnement
```

---

## Démarrer l'API

### Option 1 : Démarrage simple (local uniquement)

```powershell
cd C:\Users\DanielJandric\embeddingsall
python api_server.py
```

Vous verrez :
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Composants de recherche et upload initialisés
✅ Azure OCR initialisé
```

### Option 2 : Démarrage avec rechargement automatique (développement)

```powershell
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
```

### Tester que l'API fonctionne

Ouvrir dans votre navigateur : http://localhost:8000

Vous devriez voir :
```json
{
  "name": "Documents Search API",
  "version": "1.0.0",
  "status": "online",
  "endpoints": { ... }
}
```

### Tester la documentation interactive

Ouvrir : http://localhost:8000/docs

Vous verrez l'interface Swagger UI avec tous les endpoints disponibles.

---

## Exposer l'API sur Internet

ChatGPT a besoin d'une URL publique HTTPS pour accéder à votre API. Voici 3 options :

### Option 1 : ngrok (Recommandé pour les tests)

**Avantages :** Gratuit, rapide, pas de configuration serveur
**Inconvénients :** URL change à chaque redémarrage (version gratuite)

#### Installation :
1. Télécharger ngrok : https://ngrok.com/download
2. Créer un compte gratuit : https://dashboard.ngrok.com/signup

#### Utilisation :
```powershell
# Terminal 1 : Démarrer l'API
python api_server.py

# Terminal 2 : Démarrer ngrok
ngrok http 8000
```

Vous verrez :
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

**URL publique :** `https://abc123.ngrok.io` (utilisez cette URL dans ChatGPT)

### Option 2 : Cloudflare Tunnel (Gratuit, URL stable)

**Avantages :** Gratuit, URL permanente, plus sécurisé
**Inconvénients :** Configuration plus complexe

```powershell
# Installer cloudflared
# Suivre : https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

cloudflared tunnel --url http://localhost:8000
```

### Option 3 : Déployer sur un serveur (Production)

Options de déploiement :
- **Heroku** : Gratuit (tier limité), facile
- **Railway** : Gratuit (tier limité), moderne
- **DigitalOcean** : 5$/mois, contrôle total
- **AWS/Azure** : Plus cher, entreprise

---

## Configurer ChatGPT

### Méthode 1 : GPT Custom (ChatGPT Plus requis)

#### Étape 1 : Créer un GPT Custom

1. Aller sur https://chat.openai.com
2. Cliquer sur votre nom → "My GPTs" → "Create a GPT"
3. Nom : "Documents Search Assistant"
4. Description : "Assistant pour rechercher dans ma base de documents"

#### Étape 2 : Configurer les Actions

1. Aller dans l'onglet **"Configure"**
2. Scroller vers **"Actions"**
3. Cliquer sur **"Create new action"**

#### Étape 3 : Importer le schéma OpenAPI

**Option A : Coller le schéma YAML**

Copier le contenu de `chatgpt_actions_schema.yaml` et le coller dans l'éditeur.

**IMPORTANT :** Modifier la ligne `servers:` avec votre URL ngrok :

```yaml
servers:
  - url: https://abc123.ngrok.io  # Remplacer par votre URL ngrok
    description: API via ngrok
```

**Option B : URL du schéma**

Si vous hébergez le fichier YAML quelque part :
```
https://votre-domaine.com/chatgpt_actions_schema.yaml
```

#### Étape 4 : Tester

Dans le GPT custom, tester :
```
"Quelles sont les statistiques de ma base de données ?"
```

ChatGPT devrait appeler l'endpoint `/api/stats` et afficher les résultats.

---

### Méthode 2 : Function Calling (API OpenAI)

Si vous utilisez l'API OpenAI directement (pas l'interface web), utilisez les functions :

```python
import openai

openai.api_key = "sk-..."

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Recherche des infos sur Aigle"}],
    functions=[
        {
            "name": "search_documents",
            "description": "Recherche sémantique dans les documents",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Question"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"]
            }
        }
    ],
    function_call="auto"
)
```

---

## Exemples d'utilisation

### Exemple 1 : Recherche sémantique

**Dans ChatGPT :**
```
"Recherche dans mes documents : Combien vaut l'immeuble de Aigle ?"
```

**ChatGPT appelle :**
```http
POST https://abc123.ngrok.io/api/search
Content-Type: application/json

{
  "query": "Combien vaut l'immeuble de Aigle ?",
  "limit": 5,
  "threshold": 0.3
}
```

**Réponse :**
```json
{
  "success": true,
  "count": 3,
  "results": [
    {
      "rank": 1,
      "content": "L'immeuble d'Aigle est évalué à 14'850'000 CHF...",
      "similarity": 0.681,
      "file_name": "evaluation_aigle_2023.pdf"
    }
  ]
}
```

**ChatGPT répond :**
> D'après le document "evaluation_aigle_2023.pdf", l'immeuble d'Aigle est évalué à **14'850'000 CHF**.

---

### Exemple 2 : Upload de document

**Dans ChatGPT :**
```
"Upload le fichier C:\Documents\nouveau_contrat.pdf dans la base de données"
```

**ChatGPT appelle :**
```http
POST https://abc123.ngrok.io/api/upload
Content-Type: application/json

{
  "file_path": "C:\\Documents\\nouveau_contrat.pdf"
}
```

---

### Exemple 3 : Génération de rapport

**Dans ChatGPT :**
```
"Recherche tous les documents sur le projet Aigle et crée un rapport Markdown"
```

**ChatGPT fait :**
1. Appelle `/api/search` avec "projet Aigle"
2. Analyse les résultats
3. Appelle `/api/files/write` pour créer le rapport
4. Confirme la création du fichier

---

## Sécurité

### ⚠️ IMPORTANT : Sécuriser votre API

L'API actuelle n'a **aucune authentification**. Toute personne avec l'URL peut accéder à vos données.

### Option 1 : Authentification par clé API (Simple)

**Modifier `api_server.py` :**

```python
from fastapi import Header, HTTPException

API_KEY = os.getenv("API_SECRET_KEY", "votre-cle-secrete-ici")

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")
    return x_api_key

# Ajouter à chaque endpoint
@app.post("/api/search", dependencies=[Depends(verify_api_key)])
async def search_documents(request: SearchRequest):
    ...
```

**Dans ChatGPT GPT Actions :**
```yaml
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

security:
  - ApiKeyAuth: []
```

Puis dans ChatGPT, aller dans "Authentication" → "API Key" → Ajouter votre clé.

### Option 2 : OAuth 2.0 (Production)

Pour une vraie sécurité, implémenter OAuth 2.0 avec Auth0 ou similaire.

### Option 3 : IP Whitelisting (ngrok Pro)

Restreindre l'accès aux IPs d'OpenAI uniquement.

---

## Tester l'API manuellement

### Avec curl :

```bash
# Stats
curl http://localhost:8000/api/stats

# Recherche
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Aigle", "limit": 3}'

# Lire un fichier
curl -X POST http://localhost:8000/api/files/read \
  -H "Content-Type: application/json" \
  -d '{"file_path": "C:\\test.txt"}'
```

### Avec Postman :

1. Télécharger Postman : https://www.postman.com/downloads/
2. Importer la collection depuis l'URL Swagger : http://localhost:8000/openapi.json
3. Tester tous les endpoints

---

## Dépannage

### Problème : "Composants non initialisés"

**Solution :** Vérifier le fichier `.env` avec les clés API

### Problème : ChatGPT ne peut pas accéder à l'API

**Solutions :**
- Vérifier que ngrok est actif
- Vérifier que l'API tourne sur le bon port
- Tester l'URL ngrok dans votre navigateur

### Problème : "CORS error"

**Solution :** Déjà configuré dans `api_server.py`, mais vérifier les headers

### Problème : Timeout lors de l'upload

**Solution :** Les gros PDFs peuvent prendre du temps. Augmenter le timeout :

```python
# Dans api_server.py
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        timeout_keep_alive=300  # 5 minutes
    )
```

---

## Ressources

- **FastAPI docs :** https://fastapi.tiangolo.com
- **ChatGPT Actions :** https://platform.openai.com/docs/actions
- **ngrok docs :** https://ngrok.com/docs
- **OpenAPI spec :** https://swagger.io/specification/

---

## Résumé des étapes

1. ✅ Installer FastAPI : `pip install fastapi uvicorn`
2. ✅ Démarrer l'API : `python api_server.py`
3. ✅ Installer ngrok : https://ngrok.com/download
4. ✅ Exposer l'API : `ngrok http 8000`
5. ✅ Créer un GPT custom dans ChatGPT
6. ✅ Coller le schéma OpenAPI avec l'URL ngrok
7. ✅ Tester dans ChatGPT

**Vous avez terminé ! ChatGPT peut maintenant accéder à votre base de documents. 🎉**
