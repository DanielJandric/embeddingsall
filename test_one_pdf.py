#!/usr/bin/env python3
"""
Test simple pour traiter UN SEUL PDF et voir où ça bloque
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

print("="*70)
print("TEST D'UN SEUL PDF")
print("="*70)

# Récupérer le premier PDF
if len(sys.argv) < 2:
    print("❌ Usage: python test_one_pdf.py <chemin_vers_pdf>")
    sys.exit(1)

pdf_path = sys.argv[1]
print(f"🔍 Chemin reçu: {pdf_path}")

if not Path(pdf_path).exists():
    print(f"❌ Le fichier n'existe pas: {pdf_path}")
    print(f"   Vérifiez que le chemin est correct")
    sys.exit(1)

print(f"\n📄 Fichier: {pdf_path}")
print(f"📏 Taille: {os.path.getsize(pdf_path) / (1024*1024):.2f} MB\n")

# 1. Test Azure OCR
print("=" * 70)
print("ÉTAPE 1 : Azure OCR")
print("=" * 70)

try:
    from src.azure_ocr import AzureOCRProcessor
    print("✅ Module Azure importé")

    ocr = AzureOCRProcessor()
    print("✅ Client Azure initialisé")

    print("\n⏳ Envoi du PDF à Azure OCR...")
    print("   (Cela peut prendre 30-120 secondes, soyez patient !)")

    result = ocr.process_file(pdf_path)

    text = result.get('full_text', '')
    print(f"\n✅ OCR terminé !")
    print(f"   📝 Caractères extraits: {len(text)}")
    print(f"   📄 Pages: {result.get('page_count', 0)}")

    if text:
        print(f"\n   Aperçu du texte (100 premiers caractères):")
        print(f"   {text[:100]}...")
    else:
        print("   ⚠️  AUCUN texte extrait du PDF !")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ Erreur Azure OCR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Test Embeddings
print("\n" + "=" * 70)
print("ÉTAPE 2 : Génération des embeddings")
print("=" * 70)

try:
    from src.embeddings import EmbeddingGenerator

    emb = EmbeddingGenerator()
    print("✅ Client OpenAI initialisé")

    chunks = emb.chunk_text(text, chunk_size=1000, overlap=200)
    print(f"✅ Texte découpé en {len(chunks)} chunks")

    if len(chunks) > 5:
        print(f"   ⚠️  Limitation à 5 chunks pour ce test (au lieu de {len(chunks)})")
        chunks = chunks[:5]

    print(f"\n⏳ Génération de {len(chunks)} embeddings...")
    embeddings = emb.generate_embeddings_batch(chunks, batch_size=5)

    print(f"✅ Embeddings générés : {len(embeddings)}")

except Exception as e:
    print(f"\n❌ Erreur Embeddings: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Test Supabase
print("\n" + "=" * 70)
print("ÉTAPE 3 : Upload vers Supabase")
print("=" * 70)

try:
    from src.supabase_client import SupabaseUploader

    uploader = SupabaseUploader()
    print("✅ Client Supabase initialisé")

    documents = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if embedding:
            documents.append({
                "content": chunk,
                "embedding": embedding,
                "metadata": {
                    "file_path": pdf_path,
                    "file_name": Path(pdf_path).name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "test": True
                }
            })

    print(f"⏳ Upload de {len(documents)} documents...")
    uploader.upload_batch("documents", documents, batch_size=10)

    print(f"✅ Upload réussi !")

except Exception as e:
    print(f"\n❌ Erreur Supabase: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("🎉 TEST RÉUSSI !")
print("=" * 70)
