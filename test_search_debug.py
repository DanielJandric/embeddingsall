#!/usr/bin/env python3
"""
Script de diagnostic pour tester la recherche et voir exactement ce que Supabase retourne
"""

import json
from dotenv import load_dotenv
from src.semantic_search import SemanticSearchEngine
from src.supabase_client import SupabaseUploader
from src.embeddings import EmbeddingGenerator

# Charger .env
load_dotenv()

print("=" * 70)
print("🔍 DIAGNOSTIC DE RECHERCHE SUPABASE")
print("=" * 70)

# Test 1: Générer un embedding
print("\n1️⃣ Test génération d'embedding...")
embedding_gen = EmbeddingGenerator()
test_query = "immeuble aigle"
embedding = embedding_gen.generate_embedding(test_query)
print(f"✅ Embedding généré: {len(embedding)} dimensions")

# Test 2: Appel direct à Supabase
print("\n2️⃣ Test appel direct Supabase RPC...")
supabase = SupabaseUploader()

try:
    raw_response = supabase.client.rpc(
        "match_document_chunks",
        {
            "query_embedding": embedding,
            "match_threshold": 0.5,
            "match_count": 3
        }
    ).execute()

    print(f"✅ Réponse reçue: {len(raw_response.data)} résultats")

    # Afficher la structure complète du premier résultat
    if raw_response.data:
        print("\n📊 STRUCTURE DU PREMIER RÉSULTAT:")
        print(json.dumps(raw_response.data[0], indent=2, default=str))

        print("\n📋 CLÉS DISPONIBLES:")
        for key in raw_response.data[0].keys():
            value = raw_response.data[0][key]
            if isinstance(value, str):
                preview = value[:100] + "..." if len(value) > 100 else value
                print(f"  - {key}: '{preview}'")
            else:
                print(f"  - {key}: {type(value).__name__}")
    else:
        print("❌ Aucun résultat retourné")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Via SemanticSearchEngine
print("\n3️⃣ Test via SemanticSearchEngine...")
engine = SemanticSearchEngine()
results = engine.search(test_query, limit=3, threshold=0.5)

if results:
    print(f"✅ {len(results)} résultats trouvés")
    print("\n📄 PREMIER RÉSULTAT TRAITÉ:")
    print(json.dumps(results[0], indent=2, default=str))
else:
    print("❌ Aucun résultat")

print("\n" + "=" * 70)
print("✅ Diagnostic terminé")
print("=" * 70)
