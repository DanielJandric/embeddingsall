#!/usr/bin/env python3
"""
Vérifie si les documents ont des embeddings dans Supabase
"""

from dotenv import load_dotenv
from src.supabase_client import SupabaseUploader

load_dotenv()

print("="*70)
print("VÉRIFICATION DES EMBEDDINGS")
print("="*70)

uploader = SupabaseUploader()

# Requête pour compter les documents avec/sans embeddings
try:
    # Compter le total
    total_response = uploader.client.table("documents")\
        .select("id", count="exact")\
        .execute()

    total = total_response.count if hasattr(total_response, 'count') else 0

    # Compter ceux avec embedding NULL
    null_response = uploader.client.table("documents")\
        .select("id", count="exact")\
        .is_("embedding", "null")\
        .execute()

    null_count = null_response.count if hasattr(null_response, 'count') else 0

    # Compter ceux avec embedding NOT NULL
    with_embedding = total - null_count

    print(f"\n📊 Statistiques:")
    print(f"   Total documents: {total}")
    print(f"   Avec embeddings: {with_embedding}")
    print(f"   Sans embeddings (NULL): {null_count}")

    if null_count > 0:
        print(f"\n❌ PROBLÈME: {null_count} documents n'ont pas d'embeddings!")
        print(f"\n💡 SOLUTION:")
        print(f"   Vos documents ont été uploadés sans embeddings.")
        print(f"   Vous devez supprimer et réuploader avec le bon script.\n")
        print(f"   Option 1 - Supprimer tout et réuploader:")
        print(f"   1. Supprimer dans Supabase SQL Editor:")
        print(f"      DELETE FROM documents;")
        print(f"   2. Réuploader avec:")
        print(f"      python process_fast.py -i 'dossier' --upload --workers 5\n")
        print(f"   Option 2 - Garder et ajouter uniquement les embeddings manquants:")
        print(f"      (Plus complexe, nécessite un script custom)")
    else:
        print(f"\n✅ Tous les documents ont des embeddings!")
        print(f"   La recherche devrait fonctionner.")

except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
