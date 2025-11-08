#!/usr/bin/env python3
"""
Script pour vérifier directement les données dans Supabase
"""

import json
from dotenv import load_dotenv
from src.supabase_client import SupabaseUploader

load_dotenv()

print("=" * 70)
print("🔍 VÉRIFICATION DES DONNÉES SUPABASE")
print("=" * 70)

supabase = SupabaseUploader()

# 1. Vérifier la table document_chunks
print("\n1️⃣ Vérification de la table 'document_chunks'...")
try:
    response = supabase.client.table("document_chunks").select("*").limit(3).execute()

    print(f"✅ Nombre de résultats: {len(response.data)}")

    if response.data:
        print("\n📊 STRUCTURE D'UN CHUNK:")
        chunk = response.data[0]

        for key, value in chunk.items():
            if key == "embedding":
                print(f"  - {key}: [vector de {len(value) if value else 0} dimensions]")
            elif isinstance(value, str):
                preview = value[:100] + "..." if len(value) > 100 else value
                print(f"  - {key}: '{preview}'")
            else:
                print(f"  - {key}: {value}")

        # Vérifier spécifiquement le contenu
        print("\n🔍 VÉRIFICATION DU CONTENU:")
        if "chunk_content" in chunk:
            content = chunk["chunk_content"]
            if content:
                print(f"  ✅ chunk_content: {len(content)} caractères")
                print(f"  Aperçu: {content[:200]}")
            else:
                print("  ❌ chunk_content est vide ou NULL")
        else:
            print("  ❌ Champ 'chunk_content' n'existe pas")

        if "text" in chunk:
            text = chunk["text"]
            if text:
                print(f"  ✅ text: {len(text)} caractères")
            else:
                print("  ❌ text est vide ou NULL")

        if "content" in chunk:
            content = chunk["content"]
            if content:
                print(f"  ✅ content: {len(content)} caractères")
            else:
                print("  ❌ content est vide ou NULL")

    else:
        print("❌ Aucune donnée dans document_chunks")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

# 2. Vérifier la table documents_full
print("\n2️⃣ Vérification de la table 'documents_full'...")
try:
    response = supabase.client.table("documents_full").select("*").limit(3).execute()

    print(f"✅ Nombre de documents: {len(response.data)}")

    if response.data:
        doc = response.data[0]
        print("\n📄 CHAMPS DISPONIBLES:")
        for key in doc.keys():
            print(f"  - {key}")

except Exception as e:
    print(f"❌ Table documents_full n'existe peut-être pas: {e}")

# 3. Liste des tables disponibles
print("\n3️⃣ Liste des tables...")
try:
    # Essayer de lister les tables via une requête système PostgreSQL
    response = supabase.client.rpc("pg_catalog.pg_tables").execute()
    print("Tables disponibles:")
    for table in response.data:
        print(f"  - {table}")
except:
    print("❌ Impossible de lister les tables automatiquement")
    print("Vérifiez manuellement dans le dashboard Supabase:")
    print("  - document_chunks")
    print("  - documents_full")
    print("  - documents (ancienne?)")

print("\n" + "=" * 70)
print("✅ Vérification terminée")
print("=" * 70)
