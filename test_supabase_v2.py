#!/usr/bin/env python3
"""
Test de diagnostic complet pour Supabase V2
"""

from dotenv import load_dotenv
from src.supabase_client_v2 import SupabaseUploaderV2

load_dotenv()

print("="*70)
print("DIAGNOSTIC SUPABASE V2")
print("="*70)

uploader = SupabaseUploaderV2()

# Test 1: Vérifier les tables
print("\n1. Test des tables...")
try:
    # Test documents_full
    response = uploader.client.table("documents_full").select("*").limit(1).execute()
    print("   ✅ Table 'documents_full' existe")
    print(f"      Documents: {len(response.data)}")
except Exception as e:
    print(f"   ❌ Table 'documents_full': {e}")

try:
    # Test document_chunks
    response = uploader.client.table("document_chunks").select("*").limit(1).execute()
    print("   ✅ Table 'document_chunks' existe")
    print(f"      Chunks: {len(response.data)}")
except Exception as e:
    print(f"   ❌ Table 'document_chunks': {e}")

# Test 2: Lister les fonctions disponibles
print("\n2. Test des fonctions RPC disponibles...")

# Liste des fonctions qu'on devrait avoir
expected_functions = [
    "get_database_stats",
    "match_document_chunks",
    "get_full_document",
    "get_document_chunks",
    "delete_document_by_path"
]

for func_name in expected_functions:
    try:
        # Essayer d'appeler chaque fonction
        if func_name == "get_database_stats":
            response = uploader.client.rpc(func_name).execute()
            print(f"   ✅ Fonction '{func_name}' fonctionne")
            if response.data:
                print(f"      Résultat: {response.data[0]}")

        elif func_name == "match_document_chunks":
            # Test avec un embedding factice
            test_embedding = [0.0] * 1536
            response = uploader.client.rpc(
                func_name,
                {
                    "query_embedding": test_embedding,
                    "match_threshold": 0.7,
                    "match_count": 1
                }
            ).execute()
            print(f"   ✅ Fonction '{func_name}' fonctionne")
            print(f"      Résultats: {len(response.data)}")

        else:
            print(f"   ⏭️  Fonction '{func_name}' (non testée)")

    except Exception as e:
        error_msg = str(e)
        if "PGRST202" in error_msg or "Could not find the function" in error_msg:
            print(f"   ❌ Fonction '{func_name}' INTROUVABLE")
            print(f"      Erreur: {error_msg[:100]}...")
        else:
            print(f"   ⚠️  Fonction '{func_name}': {error_msg[:100]}...")

# Test 3: Vérifier directement avec SQL
print("\n3. Vérification SQL directe...")

try:
    # Requête pour lister les fonctions
    sql_query = """
    SELECT routine_name, routine_type
    FROM information_schema.routines
    WHERE routine_schema = 'public'
    AND routine_name LIKE '%document%'
    ORDER BY routine_name;
    """

    # Note: Supabase ne permet pas toujours les requêtes directes
    # On va essayer via une requête RPC si possible
    print("   ℹ️  Vérification SQL non disponible via API REST")
    print("   → Allez dans SQL Editor et exécutez:")
    print(f"      {sql_query}")

except Exception as e:
    print(f"   ⚠️  {e}")

# Test 4: Test d'insertion simple
print("\n4. Test d'insertion dans documents_full...")

try:
    test_doc = {
        "file_name": "test.txt",
        "file_path": "/tmp/test_diagnostic.txt",
        "file_type": "txt",
        "full_content": "Ceci est un test de diagnostic",
        "file_size_bytes": 100,
        "page_count": 1,
        "word_count": 5,
        "char_count": 30,
        "processing_method": "test",
        "metadata": {"test": True}
    }

    # Supprimer d'abord si existe
    try:
        uploader.client.table("documents_full")\
            .delete()\
            .eq("file_path", test_doc["file_path"])\
            .execute()
    except:
        pass

    # Insérer
    response = uploader.client.table("documents_full")\
        .insert(test_doc)\
        .execute()

    if response.data:
        doc_id = response.data[0]["id"]
        print(f"   ✅ Insertion réussie (ID: {doc_id})")

        # Nettoyer
        uploader.client.table("documents_full").delete().eq("id", doc_id).execute()
        print(f"   ✅ Nettoyage réussi")
    else:
        print(f"   ⚠️  Insertion sans erreur mais pas de données retournées")

except Exception as e:
    print(f"   ❌ Erreur insertion: {e}")

# Résumé
print("\n" + "="*70)
print("RÉSUMÉ")
print("="*70)

print("""
Si les fonctions sont INTROUVABLES (PGRST202) :
1. Allez dans votre Supabase Dashboard
2. SQL Editor → Nouvelle requête
3. Exécutez cette requête pour voir les fonctions :

   SELECT routine_name FROM information_schema.routines
   WHERE routine_schema = 'public' ORDER BY routine_name;

4. Si la liste est vide ou incomplète :
   → Réexécutez TOUT le fichier supabase_setup_v2.sql
   → Attendez 1-2 minutes pour le cache
   → Relancez ce diagnostic

5. Si les fonctions apparaissent dans SQL mais pas en Python :
   → Problème de cache Supabase
   → Essayez de redémarrer votre projet Supabase
   → Ou attendez quelques minutes
""")

print("="*70)
