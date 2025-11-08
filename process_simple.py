#!/usr/bin/env python3
"""
Script SIMPLE de traitement SÉQUENTIEL (sans parallèle)
Plus lent mais avec logs visibles
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import des modules
from src.pdf_extractor import extract_text_from_pdf
from src.embeddings import EmbeddingGenerator
from src.supabase_client import SupabaseUploader

load_dotenv()

def detect_file_type(file_path):
    """Détecte le type de fichier"""
    ext = Path(file_path).suffix.lower()
    if ext in ['.txt', '.md', '.csv', '.json', '.xml', '.html']:
        return 'text'
    elif ext in ['.pdf']:
        return 'pdf'
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
        return 'image'
    else:
        return 'unknown'


def process_one_file(file_path, embedding_generator, supabase_uploader, upload=True):
    """Traite UN fichier et affiche les logs"""

    file_name = Path(file_path).name
    file_type = detect_file_type(file_path)

    print(f"\n{'='*70}")
    print(f"📄 {file_name}")
    print(f"{'='*70}")

    try:
        # 1. Extraction du texte
        print(f"📖 Type: {file_type}")

        if file_type == 'text':
            print("📖 Lecture du fichier texte...")
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

        elif file_type == 'pdf':
            print("📖 Extraction du texte du PDF...")
            text = extract_text_from_pdf(file_path)

            if not text or len(text.strip()) < 100:
                print("⚠️  Pas assez de texte extrait")
                return {'success': False, 'file': file_name, 'error': 'PDF scanné ou vide'}

        else:
            print(f"❌ Type de fichier non supporté: {file_type}")
            return {'success': False, 'file': file_name, 'error': f'Type non supporté: {file_type}'}

        print(f"✅ Texte extrait: {len(text)} caractères")

        # 2. Génération des embeddings
        print("🔢 Découpage en chunks...")
        chunks = embedding_generator.chunk_text(text, chunk_size=1000, overlap=200)
        print(f"✅ {len(chunks)} chunks créés")

        # Limiter à 100 chunks max
        if len(chunks) > 100:
            print(f"⚠️  Limitation à 100 chunks (au lieu de {len(chunks)})")
            chunks = chunks[:100]

        print(f"🔢 Génération de {len(chunks)} embeddings...")
        embeddings = embedding_generator.generate_embeddings_batch(chunks, batch_size=20)
        print(f"✅ {len(embeddings)} embeddings générés")

        # 3. Upload vers Supabase
        if upload and embeddings:
            print("💾 Préparation des documents...")
            documents = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding:
                    documents.append({
                        "content": chunk,
                        "embedding": embedding,
                        "metadata": {
                            "file_path": str(file_path),
                            "file_name": file_name,
                            "file_type": file_type,
                            "chunk_index": i,
                            "total_chunks": len(chunks)
                        }
                    })

            print(f"💾 Upload de {len(documents)} documents vers Supabase...")
            supabase_uploader.upload_batch("documents", documents, batch_size=100)
            print(f"✅ Upload terminé !")

        return {'success': True, 'file': file_name, 'chunks': len(chunks)}

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'file': file_name, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description="Traitement SIMPLE séquentiel")
    parser.add_argument("-i", "--input", required=True, help="Dossier à traiter")
    parser.add_argument("--upload", action="store_true", help="Upload vers Supabase")
    parser.add_argument("--max-files", type=int, default=None, help="Limiter le nombre de fichiers")

    args = parser.parse_args()

    print("="*70)
    print("📁 TRAITEMENT SIMPLE SÉQUENTIEL")
    print("="*70)

    # Lister les fichiers
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Dossier {args.input} n'existe pas")
        return

    all_files = [f for f in input_path.rglob('*') if f.is_file() and not f.name.startswith('.')]

    if args.max_files:
        all_files = all_files[:args.max_files]

    print(f"\n📂 Dossier: {input_path}")
    print(f"📊 Fichiers à traiter: {len(all_files)}")

    if len(all_files) == 0:
        print("⚠️  Aucun fichier")
        return

    # Initialiser les services
    print("\n🔧 Initialisation...")

    embedding_generator = EmbeddingGenerator()
    print("✅ Client OpenAI initialisé")

    if args.upload:
        supabase_uploader = SupabaseUploader()
        print("✅ Client Supabase initialisé")
    else:
        supabase_uploader = None

    # Traitement SÉQUENTIEL
    print("\n🚀 Début du traitement...\n")

    success_count = 0
    error_count = 0

    for i, file_path in enumerate(all_files, 1):
        print(f"\n[{i}/{len(all_files)}]")

        result = process_one_file(
            file_path,
            embedding_generator,
            supabase_uploader,
            args.upload
        )

        if result['success']:
            success_count += 1
        else:
            error_count += 1

    # Résumé
    print("\n" + "="*70)
    print("📊 RÉSUMÉ")
    print("="*70)
    print(f"✅ Succès: {success_count}")
    print(f"❌ Erreurs: {error_count}")
    print(f"📁 Total: {len(all_files)}")

    if args.upload:
        print(f"\n💾 Documents dans Supabase (table: documents)")

    print("\n🎉 Terminé !")


if __name__ == "__main__":
    main()
