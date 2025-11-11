#!/usr/bin/env python3
"""
Script de lancement adapté à l'environnement Linux/Conteneur
Détecte automatiquement où sont les fichiers et lance le traitement
"""

import os
import sys
from pathlib import Path

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")

def check_paths():
    """Vérifie les emplacements possibles des fichiers"""

    possible_paths = [
        "/home/user/embeddingsall/data/input",
        "/mnt/c/OneDriveExport",
        "/mnt/d/OneDriveExport",
        "/c/OneDriveExport",
        "./data/input",
        "../data/input",
        "/tmp/documents",
        "/workspace/documents",
        "/workspace/data/input",
    ]

    print_header("RECHERCHE DES FICHIERS")

    found_paths = []

    for path in possible_paths:
        if os.path.exists(path):
            try:
                files = list(Path(path).rglob("*"))
                doc_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.pdf', '.txt', '.docx', '.doc', '.md', '.csv']]

                if doc_files:
                    print(f"✓ Trouvé : {path}")
                    print(f"  → {len(doc_files)} fichiers documents")
                    found_paths.append((path, len(doc_files)))
            except Exception as e:
                pass

    if not found_paths:
        print("✗ Aucun fichier document trouvé dans les emplacements standards")
        print("\n💡 Suggestions :")
        print("   1. Copiez vos fichiers dans : data/input/")
        print("   2. Ou lancez ce script depuis Windows PowerShell avec run_upload.ps1")
        print("   3. Ou spécifiez un chemin personnalisé")
        return None

    print(f"\n✓ {len(found_paths)} emplacement(s) trouvé(s) avec des fichiers")

    # Retourner le chemin avec le plus de fichiers
    best_path = max(found_paths, key=lambda x: x[1])
    return best_path[0]

def run_processing(input_path):
    """Lance le traitement avec le chemin trouvé"""

    print_header("LANCEMENT DU TRAITEMENT")

    # Configuration
    granularity = os.getenv("GRANULARITY_LEVEL", "ULTRA_FINE")
    workers = 3

    print(f"📁 Dossier source : {input_path}")
    print(f"🎯 Granularité : {granularity}")
    print(f"⚡ Workers : {workers}")

    # Construire la commande
    cmd_parts = [
        "python", "process_v2.py",
        "--input", f'"{input_path}"',
        "--workers", str(workers),
        "--upload",
        "--use-ocr"
    ]

    cmd = " ".join(cmd_parts)

    print(f"\n💻 Commande : {cmd}")
    print("\n" + "="*80)

    # Demander confirmation
    response = input("\n▶ Lancer le traitement ? (o/n) : ")
    if response.lower() != 'o':
        print("❌ Traitement annulé")
        return

    # Lancer
    print("\n🚀 Démarrage...\n")
    exit_code = os.system(cmd)

    if exit_code == 0:
        print("\n✅ Traitement terminé avec succès !")
    else:
        print(f"\n❌ Erreur (code {exit_code})")

def main():
    print_header("DÉTECTION AUTOMATIQUE DE L'ENVIRONNEMENT")

    # Afficher l'environnement
    print(f"🖥️  Système : {os.uname().sysname}")
    print(f"📂 Répertoire actuel : {os.getcwd()}")

    # Vérifier si on est sur Windows ou Linux
    is_windows = sys.platform == "win32"

    if is_windows:
        print("✓ Environnement Windows détecté")
        print("\n💡 Vous devriez utiliser : .\\run_upload.ps1")
        print("   Ce script PowerShell est optimisé pour Windows")

        response = input("\n▶ Continuer quand même avec ce script Python ? (o/n) : ")
        if response.lower() != 'o':
            print("Lancez : .\\run_upload.ps1")
            return
    else:
        print("✓ Environnement Linux/Conteneur détecté")

    # Chercher les fichiers
    input_path = check_paths()

    if not input_path:
        print("\n" + "="*80)
        print("📝 COMMENT AJOUTER VOS FICHIERS")
        print("="*80)
        print("\nDEPUIS WINDOWS :")
        print('  1. Copiez vos fichiers : Copy-Item "c:\\OneDriveExport\\*" -Destination "data\\input\\" -Recurse')
        print('  2. OU lancez directement : .\\run_upload.ps1')
        print("\nDEPUIS CE TERMINAL :")
        print('  1. Copiez vos fichiers dans : data/input/')
        print('  2. Puis relancez : python run_linux.py')
        return

    # Lancer le traitement
    run_processing(input_path)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
