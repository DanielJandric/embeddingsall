#!/usr/bin/env python3
"""
Test pour vérifier si les embeddings sont dans Supabase
"""

from dotenv import load_dotenv
from src.supabase_client import SupabaseUploader
from src.embeddings import EmbeddingGenerator

load_dotenv()

print("=" * 70)
print("🔍 VÉRIFICATION DES EMBEDDINGS DANS SUPABASE")
print("=" * 70)

supabase = SupabaseUploader()

# 1. Compter les embeddings NON NULL
print("\n1️⃣ Comptage des embeddings...")
with_emb = supabase.client.table('document_chunks').select('id', count='exact').not_.is_('embedding', 'null').limit(1).execute()
total = supabase.client.table('document_chunks').select('id', count='exact').limit(1).execute()

embeddings_count = with_emb.count if hasattr(with_emb, 'count') else 0
total_count = total.count if hasattr(total, 'count') else 0

print(f"   Total chunks: {total_count}")
print(f"   ✅ Chunks AVEC embeddings: {embeddings_count}")
print(f"   ❌ Chunks SANS embeddings: {total_count - embeddings_count}")

# 2. Test de recherche direct
if embeddings_count > 0:
    print("\n2️⃣ Test de recherche directe...")

    # Générer un embedding de test
    emb_gen = EmbeddingGenerator()
    test_embedding = emb_gen.generate_embedding('Aigle')

    print(f"   Embedding généré: {len(test_embedding)} dimensions")

    # Appeler la fonction SQL directement avec différents seuils
    for threshold in [0.3, 0.5, 0.7]:
        result = supabase.client.rpc('match_document_chunks', {
            'query_embedding': test_embedding,
            'match_threshold': threshold,
            'match_count': 5
        }).execute()

        print(f"\n   📊 Seuil {threshold}: {len(result.data)} résultats")

        if result.data:
            for i, r in enumerate(result.data[:3], 1):
                print(f"      {i}. {r.get('file_name', 'Inconnu')} - Similarité: {r.get('similarity', 0):.1%}")

    if not any(len(supabase.client.rpc('match_document_chunks', {
        'query_embedding': test_embedding,
        'match_threshold': t,
        'match_count': 5
    }).execute().data) > 0 for t in [0.3, 0.5, 0.7]):
        print("\n   ❌ PROBLÈME: Aucun résultat même avec seuil 0.3")
        print("      Les embeddings existent mais la recherche ne fonctionne pas")
else:
    print("\n❌ PROBLÈME MAJEUR: Aucun embedding dans Supabase!")
    print("   Les embeddings ont été créés localement mais PAS uploadés vers Supabase")
    print("\n💡 Solution: Re-lancer l'upload:")
    print("   python process_v2.py -i \"C:\\OneDriveExport\" --upload --workers 1")

print("\n" + "=" * 70)
print("✅ Test terminé")
print("=" * 70)
