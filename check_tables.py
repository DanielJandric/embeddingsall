#!/usr/bin/env python3
"""
Script pour vérifier quelles tables ont des données
"""

from dotenv import load_dotenv
from src.supabase_client import SupabaseUploader

load_dotenv()

print("=" * 70)
print("🔍 VÉRIFICATION DES TABLES SUPABASE")
print("=" * 70)

supabase = SupabaseUploader()

# Liste des tables à vérifier
tables = ["documents", "document_chunks", "documents_full"]

for table_name in tables:
    print(f"\n📊 Table: {table_name}")
    print("-" * 70)

    try:
        # Compter les lignes
        response = supabase.client.table(table_name).select("*", count="exact").limit(1).execute()
        count = response.count if hasattr(response, 'count') else 0

        print(f"✅ Nombre de lignes: {count}")

        if count > 0 and response.data:
            print(f"📄 Premier enregistrement:")
            first = response.data[0]
            for key in list(first.keys())[:10]:  # Afficher les 10 premières colonnes
                value = first[key]
                if isinstance(value, str) and len(value) > 50:
                    print(f"   - {key}: {value[:50]}...")
                elif isinstance(value, list) and len(value) > 0:
                    print(f"   - {key}: [liste de {len(value)} éléments]")
                else:
                    print(f"   - {key}: {value}")

    except Exception as e:
        print(f"❌ Erreur: {e}")

print("\n" + "=" * 70)
print("✅ Vérification terminée")
print("=" * 70)
