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

# 1. Test Extraction du texte
print("=" * 70)
print("ÉTAPE 1 : Extraction du texte du PDF")
print("=" * 70)

try:
    # Méthode 1: Extraction directe (RAPIDE)
    print("📖 Tentative d'extraction directe du texte (sans OCR)...")
    from src.pdf_extractor import extract_text_from_pdf

    text = extract_text_from_pdf(pdf_path)

    if text and len(text.strip()) > 100:
        print(f"✅ Extraction directe réussie !")
        print(f"   📝 Caractères extraits: {len(text)}")
        print(f"\n   Aperçu du texte (100 premiers caractères):")
        print(f"   {text[:100]}...")
    else:
        # Méthode 2: Azure OCR (fallback pour scans)
        print("⚠️  Peu ou pas de texte trouvé")
        print("\n🔍 Tentative avec Azure OCR (pour PDFs scannés)...")

        from src.azure_ocr import AzureOCRProcessor
        ocr = AzureOCRProcessor()

        size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        if size_mb > 50:
            print(f"❌ PDF trop grand pour Azure OCR: {size_mb:.1f} MB (max 50 MB)")
            print("   → Impossible de traiter ce PDF")
            sys.exit(1)

        print("   ⏳ Envoi à Azure OCR (30-120 secondes)...")
        result = ocr.process_file(pdf_path)
        text = result.get('full_text', '')

        if text:
            print(f"✅ OCR terminé !")
            print(f"   📝 Caractères extraits: {len(text)}")
        else:
            print("❌ Aucun texte extrait même avec OCR")
            sys.exit(1)

except Exception as e:
    print(f"\n❌ Erreur d'extraction: {e}")
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
