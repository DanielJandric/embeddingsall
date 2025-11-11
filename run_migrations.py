#!/usr/bin/env python3
"""
Script Python pour exécuter les migrations SQL dans Supabase
"""

import os
import sys
from pathlib import Path
from supabase import create_client

# Couleurs pour terminal
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.NC}")

def success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.NC}")

def error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.NC}")

def warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.NC}")


def main():
    print(f"{Colors.BLUE}")
    print("=" * 70)
    print("   Exécution des Migrations SQL - Schéma Amélioré")
    print("=" * 70)
    print(f"{Colors.NC}\n")

    # Vérifier les variables d'environnement
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        error("Variables d'environnement SUPABASE_URL et SUPABASE_KEY non définies")
        print("\nDéfinissez-les avec:")
        print("  export SUPABASE_URL='https://xxx.supabase.co'")
        print("  export SUPABASE_KEY='eyJxxx...'")
        sys.exit(1)

    # Créer le client Supabase
    try:
        client = create_client(url, key)
        success("Connexion à Supabase établie")
    except Exception as e:
        error(f"Impossible de se connecter à Supabase: {e}")
        sys.exit(1)

    # Liste des fichiers de migration dans l'ordre
    migration_files = [
        "01_extensions.sql",
        "02_table_documents_full.sql",
        "03_indexes_documents_full.sql",
        "04_table_document_chunks.sql",
        "05_indexes_document_chunks.sql",
        "06_table_extracted_entities.sql",
        "07_tables_tags.sql",
        "08_table_document_relations.sql",
        "09_functions_triggers_fulltext.sql",
        "10_indexes_fulltext.sql",
        "11_function_search_enhanced.sql",
        "12_function_search_fulltext.sql",
        "13_function_search_hybrid.sql",
        "14_materialized_views.sql",
        "15_function_refresh_views.sql",
        "16_comments.sql"
    ]

    migrations_dir = Path(__file__).parent / "sql_migrations"

    if not migrations_dir.exists():
        error(f"Répertoire sql_migrations/ introuvable: {migrations_dir}")
        sys.exit(1)

    print()
    warning("ATTENTION: Cette opération va créer/modifier les tables dans Supabase")
    response = input("Continuer ? [y/N]: ")

    if response.lower() != 'y':
        info("Opération annulée")
        sys.exit(0)

    print()

    # Exécuter chaque migration
    for i, filename in enumerate(migration_files, 1):
        filepath = migrations_dir / filename

        if not filepath.exists():
            error(f"Fichier introuvable: {filepath}")
            continue

        info(f"[{i}/{len(migration_files)}] Exécution de {filename}...")

        try:
            # Lire le fichier SQL
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read()

            # Exécuter via RPC (méthode alternative car supabase-py ne supporte pas SQL direct)
            # Note: Supabase ne permet pas d'exécuter du SQL arbitraire via l'API REST
            # Il faut utiliser psql ou l'interface web

            warning(f"⚠️  Impossible d'exécuter {filename} via l'API Python")
            print(f"   Veuillez exécuter manuellement dans Supabase SQL Editor")
            print(f"   Ou utilisez psql avec le script run_all_migrations.sh")

        except Exception as e:
            error(f"Erreur lors de la lecture de {filename}: {e}")
            sys.exit(1)

    print()
    warning("L'API Supabase Python ne permet pas d'exécuter du SQL arbitraire")
    print()
    info("Utilisez plutôt l'une de ces méthodes :")
    print()
    print("1. Supabase SQL Editor (RECOMMANDÉ)")
    print("   - Allez sur https://app.supabase.com")
    print("   - SQL Editor > New Query")
    print("   - Copiez-collez chaque fichier et exécutez")
    print()
    print("2. Via psql")
    print("   cd sql_migrations")
    print("   ./run_all_migrations.sh")
    print()
    info("Consultez sql_migrations/README_EXECUTION.md pour plus de détails")


if __name__ == '__main__':
    main()
