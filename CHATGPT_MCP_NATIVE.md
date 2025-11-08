# 🤖 Connecter ChatGPT au serveur MCP (Mode Natif)

ChatGPT supporte maintenant le protocole MCP nativement en **mode développeur**. Cela vous permet d'utiliser le **même serveur** pour Claude ET ChatGPT.

## 📋 Comparaison des approches

| Caractéristique | API REST | MCP Natif (SSE) |
|----------------|----------|-----------------|
| **Protocole** | HTTP REST | MCP (SSE) |
| **Fichier serveur** | `api_server.py` | `mcp_server_http.py` |
| **Compatible avec** | Tout client HTTP | ChatGPT + Claude Desktop |
| **Standardisation** | Custom | Standard MCP |
| **Avantages** | Simple, universel | Protocol natif, meilleure intégration |
| **Recommandation** | Pour tests rapides | Pour usage production |

---

## 🔄 Architecture MCP Natif

```
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│   ChatGPT    │ ◄─────► │  MCP Server HTTP │ ◄─────► │  Supabase    │
│  Developer   │   SSE   │  (Port 3000)     │         │  (Vector DB) │
│    Mode      │  HTTPS  │                  │         └──────────────┘
└──────────────┘         └──────────────────┘
                                  │
┌──────────────┐                  │
│ Claude       │ ◄────────────────┘
│ Desktop      │   stdio
│  (Local)     │   (Port local)
└──────────────┘
```

**Le même serveur MCP** peut servir :
- ChatGPT via HTTP/SSE (remote)
- Claude Desktop via stdio (local)

---

## 🚀 Option 1 : Serveur MCP Simple (Recommandé pour débuter)

### Installation

```powershell
cd C:\Users\DanielJandric\embeddingsall
pip install starlette uvicorn
```

### Démarrage du serveur

```powershell
python mcp_server_http.py
```

Vous verrez :
```
INFO:     Uvicorn running on http://0.0.0.0:3000
🚀 Démarrage du serveur MCP HTTP/SSE
✅ Générateur d'embeddings et uploader V2 initialisés
```

### Exposer avec ngrok

```powershell
ngrok http 3000
```

Résultat :
```
Forwarding  https://abc123.ngrok.io -> http://localhost:3000
```

---

## 🔧 Configuration ChatGPT (Mode Développeur)

### Étape 1 : Activer le mode développeur

**NOTE:** Le mode développeur ChatGPT avec MCP peut être en **déploiement progressif**. Si vous ne voyez pas l'option, vous devrez attendre qu'OpenAI l'active pour votre compte.

1. Aller sur https://chatgpt.com
2. Settings → Developer Mode
3. Activer "MCP Servers"

### Étape 2 : Ajouter un MCP Connector

1. Dans Developer Mode → **MCP Connectors**
2. Cliquer sur **"Add Connector"**

3. Configurer :

```json
{
  "name": "Documents Search",
  "url": "https://abc123.ngrok.io/sse",
  "description": "Recherche sémantique dans 184 documents",
  "auth": {
    "type": "none"
  }
}
```

**IMPORTANT :** Remplacer `abc123.ngrok.io` par votre URL ngrok !

### Étape 3 : Tester

Dans ChatGPT, demander :
```
"Quelles sont les statistiques de ma base de données ?"
```

ChatGPT devrait utiliser automatiquement le MCP connector et appeler `get_database_stats`.

---

## 🔒 Sécurité : Ajouter une authentification

### Option 1 : API Key (Simple)

**Modifier `mcp_server_http.py`** :

```python
import os

API_KEY = os.getenv("MCP_API_KEY", "votre-cle-secrete")

# Dans handle_sse
async def handle_sse(request):
    # Vérifier l'authentification
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return Response("Unauthorized", status_code=401)

    token = auth_header[7:]  # Enlever "Bearer "
    if token != API_KEY:
        return Response("Invalid API Key", status_code=403)

    # Suite du code...
```

**Ajouter dans `.env`** :
```env
MCP_API_KEY=votre-cle-tres-secrete-ici
```

**Configurer dans ChatGPT** :

```json
{
  "name": "Documents Search",
  "url": "https://abc123.ngrok.io/sse",
  "auth": {
    "type": "bearer",
    "token": "votre-cle-tres-secrete-ici"
  }
}
```

### Option 2 : OAuth 2.0 (Production)

Pour une sécurité de niveau production, implémenter OAuth 2.0 avec Auth0 ou un fournisseur similaire.

---

## 🧪 Option 2 : Serveur MCP avec SDK complet

Si vous voulez utiliser toutes les fonctionnalités avancées du SDK MCP :

### Installation des dépendances

```powershell
pip install mcp[sse] starlette uvicorn
```

### Configuration avancée

Le serveur `mcp_server_http.py` utilise le transport SSE du SDK MCP officiel :

```python
from mcp.server.sse import SseServerTransport

# Le transport SSE expose automatiquement :
# - GET /sse - Endpoint pour la connexion SSE
# - POST /messages - Endpoint pour les messages
```

### Tester localement

```powershell
# Terminal 1 : Démarrer le serveur
python mcp_server_http.py

# Terminal 2 : Tester avec curl
curl http://localhost:3000/sse
```

---

## 📊 Comparaison finale : API REST vs MCP Natif

### Utilisez **API REST** (`api_server.py`) si :
- ✅ Vous voulez tester rapidement
- ✅ Vous avez besoin d'une API pour d'autres clients (mobile, web)
- ✅ Vous préférez une API simple et bien documentée
- ✅ Vous voulez utiliser Postman/curl pour tester

### Utilisez **MCP Natif** (`mcp_server_http.py`) si :
- ✅ Vous voulez le même serveur pour Claude + ChatGPT
- ✅ Vous voulez utiliser le standard MCP
- ✅ Vous prévoyez d'utiliser des fonctionnalités MCP avancées
- ✅ Vous voulez la meilleure intégration avec ChatGPT

---

## 🎯 Recommandation

**Pour commencer :**
1. Utilisez **API REST** (`api_server.py`) - Plus simple à comprendre et tester
2. Une fois familier, migrez vers **MCP Natif** (`mcp_server_http.py`)

**Pour production :**
- Utilisez **MCP Natif** avec authentification OAuth 2.0
- Déployez sur un serveur avec domaine HTTPS (pas ngrok)
- Activez le rate limiting et le logging

---

## 📝 Résumé des commandes

### API REST (Simple)
```powershell
# Démarrer
python api_server.py

# Exposer
ngrok http 8000

# URL pour ChatGPT
https://abc123.ngrok.io/api/search
```

### MCP Natif (Standard)
```powershell
# Démarrer
python mcp_server_http.py

# Exposer
ngrok http 3000

# URL pour ChatGPT
https://abc123.ngrok.io/sse
```

---

## ❓ Dépannage

### ChatGPT ne voit pas le serveur MCP

**Solutions :**
1. Vérifier que le serveur tourne : `curl http://localhost:3000/sse`
2. Vérifier l'URL ngrok est correcte
3. Vérifier que le mode développeur est activé
4. Attendre le déploiement du feature MCP sur votre compte

### Erreur "MCP Server connection failed"

**Solutions :**
1. Vérifier les logs du serveur MCP
2. Tester l'authentification (si activée)
3. Vérifier que HTTPS fonctionne (pas HTTP)
4. Redémarrer le serveur et ChatGPT

### ChatGPT n'utilise pas automatiquement le MCP

**Solution :**
Demander explicitement :
```
"Utilise le MCP connector Documents Search pour rechercher..."
```

---

## 🔗 Ressources

- **Documentation MCP :** https://modelcontextprotocol.io
- **SDK Python MCP :** https://github.com/modelcontextprotocol/python-sdk
- **OpenAI Developer Mode :** https://platform.openai.com/docs/developer-mode
- **ngrok :** https://ngrok.com/docs

---

## ✅ Checklist finale

- [ ] Serveur MCP démarré (`python mcp_server_http.py`)
- [ ] ngrok exposant le serveur (`ngrok http 3000`)
- [ ] URL ngrok copiée (`https://abc123.ngrok.io`)
- [ ] Connector ajouté dans ChatGPT Developer Mode
- [ ] Test réussi : "Quelles sont les stats de ma base ?"
- [ ] (Optionnel) Authentification configurée
- [ ] (Optionnel) Logs activés pour monitoring

**Une fois tous les éléments cochés, votre système est prêt ! 🎉**
