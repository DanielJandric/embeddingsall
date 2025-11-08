#!/usr/bin/env python3
"""
Script de test pour l'API REST.
Teste tous les endpoints pour vérifier qu'ils fonctionnent.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_root():
    """Test l'endpoint racine"""
    print("=" * 70)
    print("TEST 1: Endpoint racine")
    print("-" * 70)

    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("✅ Test réussi\n")
            return True
        else:
            print("❌ Test échoué\n")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}\n")
        return False

def test_stats():
    """Test l'endpoint stats"""
    print("=" * 70)
    print("TEST 2: Statistiques de la base")
    print("-" * 70)

    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")

            if data.get("success"):
                stats = data.get("data", {})
                print(f"\n📊 Documents: {stats.get('total_documents', 0)}")
                print(f"📦 Chunks: {stats.get('total_chunks', 0)}")
                print("✅ Test réussi\n")
                return True

        print("❌ Test échoué\n")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}\n")
        return False

def test_search():
    """Test l'endpoint search"""
    print("=" * 70)
    print("TEST 3: Recherche sémantique")
    print("-" * 70)

    try:
        payload = {
            "query": "test",
            "limit": 3,
            "threshold": 0.3
        }

        print(f"Requête: {json.dumps(payload, indent=2)}")

        response = requests.post(
            f"{BASE_URL}/api/search",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n📊 Résultats trouvés: {data.get('count', 0)}")

            if data.get("count", 0) > 0:
                print("\nPremier résultat:")
                first = data["results"][0]
                print(f"  - Fichier: {first.get('file_name', 'N/A')}")
                print(f"  - Similarité: {first.get('similarity', 0):.2%}")
                print(f"  - Contenu: {first.get('content', '')[:100]}...")

            print("\n✅ Test réussi\n")
            return True

        print("❌ Test échoué\n")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}\n")
        return False

def test_files_list():
    """Test l'endpoint list_files"""
    print("=" * 70)
    print("TEST 4: Listage de fichiers")
    print("-" * 70)

    try:
        import os
        current_dir = os.getcwd()

        payload = {
            "directory": current_dir,
            "pattern": "*.py",
            "recursive": False
        }

        print(f"Requête: Lister les fichiers .py dans {current_dir}")

        response = requests.post(
            f"{BASE_URL}/api/files/list",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n📂 Fichiers trouvés: {data.get('count', 0)}")

            if data.get("count", 0) > 0:
                print("\nPremiers fichiers:")
                for file in data["files"][:5]:
                    size_kb = file.get("size_bytes", 0) / 1024
                    print(f"  - {file.get('name')}: {size_kb:.2f} KB")

            print("\n✅ Test réussi\n")
            return True

        print("❌ Test échoué\n")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}\n")
        return False

def main():
    print("\n" + "=" * 70)
    print("🧪 TESTS DE L'API REST")
    print("=" * 70)
    print(f"URL de base: {BASE_URL}")
    print("=" * 70 + "\n")

    # Vérifier que l'API est accessible
    try:
        requests.get(BASE_URL, timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ ERREUR: L'API n'est pas accessible")
        print(f"\nAssurez-vous que l'API est démarrée:")
        print("  python api_server.py")
        print(f"\nPuis relancez ce script:")
        print("  python test_api.py")
        sys.exit(1)

    # Exécuter les tests
    results = []
    results.append(("Root endpoint", test_root()))
    results.append(("Database stats", test_stats()))
    results.append(("Semantic search", test_search()))
    results.append(("List files", test_files_list()))

    # Résumé
    print("=" * 70)
    print("📋 RÉSUMÉ DES TESTS")
    print("=" * 70)

    success_count = sum(1 for _, result in results if result)
    total_count = len(results)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print("-" * 70)
    print(f"Réussis: {success_count}/{total_count}")
    print("=" * 70 + "\n")

    if success_count == total_count:
        print("🎉 Tous les tests ont réussi !")
        print("\nL'API est prête à être utilisée avec ChatGPT.")
        print("\nProchaines étapes:")
        print("1. Installer ngrok: https://ngrok.com/download")
        print("2. Exposer l'API: ngrok http 8000")
        print("3. Configurer ChatGPT avec l'URL ngrok")
        print("4. Voir CHATGPT_SETUP.md pour les détails")
    else:
        print("⚠️ Certains tests ont échoué.")
        print("\nVérifiez que:")
        print("- Le fichier .env contient les bonnes clés API")
        print("- Supabase contient des documents")
        print("- Toutes les dépendances sont installées")

    print()

if __name__ == "__main__":
    main()
