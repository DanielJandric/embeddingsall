#!/usr/bin/env python3
"""
Upload seulement les nouveaux documents (delta)
Ignore les fichiers déjà présents dans Supabase
"""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from src.supabase_client import SupabaseUploader

load_dotenv()

def get_existing_files():
    """Récupère la liste des fichiers déjà en base"""
    supabase = SupabaseUploader()

    print("📥 Récupération des fichiers existants dans Supabase...")

    existing_paths = set()
    offset = 0
    batch_size = 1000

    while True:
        response = supabase.client.table("documents_full")\
            .select("file_path")\
            .range(offset, offset + batch_size - 1)\
            .execute()

        if not response.data:
            break

        for doc in response.data:
            existing_paths.add(doc['file_path'])

        offset += batch_size

        if len(response.data) < batch_size:
            break

    print(f"✅ {len(existing_paths)} fichiers existants trouvés")
    return existing_paths

def find_new_files(input_dir, existing_paths):
    """Trouve les fichiers qui ne sont pas encore en base"""
    print(f"\n📂 Scan du dossier {input_dir}...")

    all_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(('.pdf', '.txt', '.docx', '.jpg', '.jpeg', '.png')):
                full_path = os.path.abspath(os.path.join(root, file))
                all_files.append(full_path)

    print(f"✅ {len(all_files)} fichiers trouvés dans le dossier")

    # Filtrer les nouveaux
    new_files = [f for f in all_files if f not in existing_paths]

    print(f"🆕 {len(new_files)} nouveaux fichiers à uploader")
    print(f"⏭️  {len(all_files) - len(new_files)} fichiers ignorés (déjà en base)")

    return new_files

def main():
    parser = argparse.ArgumentParser(
        description="Upload seulement les nouveaux documents (delta)"
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Dossier contenant les documents"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Nombre de workers (défaut: 2)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher les nouveaux fichiers sans uploader"
    )

    args = parser.parse_args()

    # 1. Récupérer les fichiers existants
    existing = get_existing_files()

    # 2. Trouver les nouveaux
    new_files = find_new_files(args.input, existing)

    if not new_files:
        print("\n✅ Aucun nouveau fichier à uploader !")
        return

    # 3. Afficher la liste
    print("\n📋 Nouveaux fichiers détectés:")
    for i, f in enumerate(new_files[:10], 1):
        print(f"   {i}. {Path(f).name}")
    if len(new_files) > 10:
        print(f"   ... et {len(new_files) - 10} autres")

    if args.dry_run:
        print("\n🔍 Mode dry-run - aucun upload effectué")
        return

    # 4. Créer un fichier temporaire avec la liste
    temp_file = Path("temp_new_files.txt")
    with open(temp_file, 'w', encoding='utf-8') as f:
        for file_path in new_files:
            f.write(file_path + '\n')

    print(f"\n📝 Liste sauvegardée dans {temp_file}")
    print(f"\n🚀 Pour uploader ces fichiers, exécutez:")
    print(f"   python process_v2.py -i \"{args.input}\" --upload --workers {args.workers}")
    print(f"\n💡 Ou utilisez le mode interactif pour confirmation")

    # Option: Upload automatique si confirmé
    response = input("\n❓ Voulez-vous uploader ces fichiers maintenant ? (o/n): ")

    if response.lower() == 'o':
        print("\n🚀 Lancement de l'upload...")

        import subprocess
        cmd = [
            "python", "process_v2.py",
            "-i", args.input,
            "--upload",
            "--workers", str(args.workers)
        ]

        # Note: process_v2.py va quand même re-scanner tous les fichiers
        # mais mettra à jour seulement les nouveaux car ils n'existent pas en base
        subprocess.run(cmd)
    else:
        print("❌ Upload annulé")

    # Cleanup
    if temp_file.exists():
        temp_file.unlink()

if __name__ == "__main__":
    main()
