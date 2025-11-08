# 🤖 Connecter ChatGPT à votre système de recherche documentaire

## 🎯 Quelle méthode choisir ?

ChatGPT peut maintenant se connecter à votre système de deux façons :

### Option 1 : API REST (✅ Recommandé - Simple et testé)

**Utilisez :** `api_server.py`
- ✅ Simple à configurer
- ✅ Bien testé et documenté
- ✅ Compatible avec n'importe quel client HTTP
- ✅ Documentation Swagger interactive
- ✅ Fonctionne immédiatement

**Guide :** Voir `CHATGPT_SETUP.md`

### Option 2 : MCP Natif (🔬 Expérimental)

**Utilisez :** `mcp_server_http.py`
- 🔬 Utilise le protocole MCP standard
- 🔬 Même serveur pour Claude + ChatGPT
- ⚠️ Nécessite ChatGPT Developer Mode (en déploiement progressif)
- ⚠️ Configuration plus complexe

**Guide :** Voir `CHATGPT_MCP_NATIVE.md`

---

## 🚀 Démarrage rapide (API REST - Recommandé)

### 1. Installer les dépendances

```powershell
cd C:\Users\DanielJandric\embeddingsall
pip install fastapi uvicorn pydantic
```

### 2. Démarrer le serveur

```powershell
python api_server.py
```

### 3. Tester localement

Ouvrir dans votre navigateur : http://localhost:8000

Vous devriez voir :
```json
{
  "name": "Documents Search API",
  "version": "1.0.0",
  "status": "online"
}
```

### 4. Exposer sur Internet avec ngrok

```powershell
# Télécharger ngrok: https://ngrok.com/download
ngrok http 8000
```

Copier l'URL : `https://abc123.ngrok.io`

### 5. Configurer ChatGPT

1. Aller sur https://chat.openai.com
2. Créer un **GPT Custom**
3. Onglet **Configure** → **Actions** → **Create new action**
4. Copier le contenu de `chatgpt_actions_schema.yaml`
5. Remplacer `https://abc123.ngrok.io` par votre URL ngrok
6. **Save**

### 6. Tester

Dans votre GPT custom :
```
"Quelles sont les statistiques de ma base de données ?"
```

ChatGPT devrait répondre avec vos 184 documents et 2601 chunks !

---

## 📊 Endpoints disponibles

| Endpoint | Description | Exemple |
|----------|-------------|---------|
| `GET /api/stats` | Statistiques de la base | - |
| `POST /api/search` | Recherche sémantique | `{"query": "Aigle"}` |
| `POST /api/upload` | Upload un document | `{"file_path": "C:\\doc.pdf"}` |
| `POST /api/files/read` | Lire un fichier | `{"file_path": "C:\\file.txt"}` |
| `POST /api/files/write` | Écrire un fichier | `{"file_path": "...", "content": "..."}` |
| `POST /api/files/list` | Lister des fichiers | `{"directory": "C:\\Docs"}` |

---

## 💡 Exemples d'utilisation dans ChatGPT

### Exemple 1 : Recherche
```
"Recherche dans mes documents : Combien vaut l'immeuble de Aigle ?"

→ ChatGPT appelle /api/search
→ Répond : "14'850'000 CHF (similarité 68%)"
```

### Exemple 2 : Upload
```
"Upload le fichier C:\Documents\contrat.pdf dans la base"

→ ChatGPT appelle /api/upload
→ Traite le PDF (OCR, chunking, embeddings)
→ Confirme l'upload
```

### Exemple 3 : Génération de rapport
```
"Recherche tous les documents sur Aigle et génère un rapport Markdown"

→ ChatGPT appelle /api/search
→ Analyse les résultats
→ Appelle /api/files/write pour créer le rapport
→ Confirme : "Rapport créé dans C:\Reports\aigle.md"
```

---

## 🔒 Sécurité

⚠️ **IMPORTANT :** L'API n'a actuellement **aucune authentification**. Toute personne avec l'URL ngrok peut accéder à vos données.

**Pour sécuriser rapidement :**

Voir la section "Sécurité" dans `CHATGPT_SETUP.md` pour :
- Authentification par API Key
- OAuth 2.0
- IP Whitelisting

---

## 📚 Documentation complète

- **`CHATGPT_SETUP.md`** - Guide complet API REST (recommandé)
- **`CHATGPT_MCP_NATIVE.md`** - Guide MCP natif (expérimental)
- **`chatgpt_actions_schema.yaml`** - Schéma OpenAPI pour ChatGPT

---

## 🧪 Tests

```powershell
# Terminal 1 : Démarrer l'API
python api_server.py

# Terminal 2 : Tester
python test_api.py
```

Les tests vérifient :
- ✅ Endpoint racine
- ✅ Statistiques de la base
- ✅ Recherche sémantique
- ✅ Listage de fichiers

---

## 🆚 Comparaison : Claude Desktop vs ChatGPT

| Fonctionnalité | Claude Desktop (MCP) | ChatGPT (API REST) |
|----------------|----------------------|-------------------|
| Connexion | Local (stdio) | Remote (HTTPS) |
| Configuration | `.claude/config.json` | GPT Actions |
| Sécurité | N/A (local) | API Key / OAuth |
| Documentation | Swagger auto | OpenAPI YAML |
| Outils disponibles | 7 outils | 6 endpoints |

**Vous avez maintenant les deux systèmes !** 🎉

---

## ✅ Checklist

- [ ] Dépendances installées (`pip install fastapi uvicorn`)
- [ ] Serveur démarré (`python api_server.py`)
- [ ] Tests réussis (`python test_api.py`)
- [ ] ngrok installé et configuré
- [ ] URL ngrok copiée
- [ ] GPT custom créé dans ChatGPT
- [ ] Schéma OpenAPI configuré avec URL ngrok
- [ ] Test réussi dans ChatGPT
- [ ] (Optionnel) Sécurité configurée

**Une fois terminé, vous pouvez utiliser ChatGPT pour interroger vos 184 documents ! 🚀**

---

## ❓ Besoin d'aide ?

1. **L'API ne démarre pas :** Vérifier le fichier `.env` avec les clés API
2. **ChatGPT ne peut pas accéder :** Vérifier que ngrok est actif et l'URL est correcte
3. **Erreurs de recherche :** Vérifier que Supabase contient des documents
4. **Timeout :** Augmenter le timeout dans `api_server.py`

Pour plus de détails, voir `CHATGPT_SETUP.md`.
