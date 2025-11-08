"""
Script de vérification directe - bypasse le cache
"""
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"URL: {url}")
print(f"Key: {key[:20]}...")

client = create_client(url, key)

print("\n" + "="*70)
print("TEST 1: Query directe sur documents_full")
print("="*70)

try:
    # Essayer une requête directe
    response = client.table("documents_full").select("*").limit(1).execute()
    print(f"✅ SUCCÈS - Table trouvée")
    print(f"   Données: {len(response.data)} lignes")
except Exception as e:
    print(f"❌ ERREUR: {e}")

print("\n" + "="*70)
print("TEST 2: Query directe sur document_chunks")
print("="*70)

try:
    response = client.table("document_chunks").select("*").limit(1).execute()
    print(f"✅ SUCCÈS - Table trouvée")
    print(f"   Données: {len(response.data)} lignes")
except Exception as e:
    print(f"❌ ERREUR: {e}")

print("\n" + "="*70)
print("TEST 3: Fonction get_database_stats")
print("="*70)

try:
    response = client.rpc("get_database_stats").execute()
    print(f"✅ SUCCÈS - Fonction trouvée")
    print(f"   Response: {response.data}")
except Exception as e:
    print(f"❌ ERREUR: {e}")

print("\n" + "="*70)
print("TEST 4: Fonction match_document_chunks avec embedding vide")
print("="*70)

try:
    test_embedding = [0.0] * 1536
    response = client.rpc(
        "match_document_chunks",
        {
            "query_embedding": test_embedding,
            "match_threshold": 0.7,
            "match_count": 1
        }
    ).execute()
    print(f"✅ SUCCÈS - Fonction trouvée")
    print(f"   Résultats: {len(response.data)}")
except Exception as e:
    print(f"❌ ERREUR: {e}")

print("\n" + "="*70)
print("DIAGNOSTIC")
print("="*70)

print("""
Si les tables existent dans Supabase mais Python ne les trouve pas:

1. CACHE SUPABASE:
   - Allez dans Settings > API > Reload schema cache
   - Ou attendez 2-3 minutes

2. VÉRIFIER LE PROJET:
   - Vous êtes sur: """ + url + """
   - C'est bien le bon projet?

3. PERMISSIONS:
   - Dans SQL Editor, exécutez:
     SELECT * FROM documents_full LIMIT 1;
   - Si ça marche en SQL mais pas en Python = problème de permissions API

4. RÉGION/ENDPOINT:
   - Vérifiez que l'URL est correcte
   - Pas de typo dans SUPABASE_URL

5. REDÉMARRER LE PROJET:
   - Dans Supabase Dashboard > Settings > General
   - Pause project puis Resume project
""")
