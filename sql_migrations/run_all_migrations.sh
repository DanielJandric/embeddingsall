#!/bin/bash
# ================================================================
# Script d'Exécution Automatique des Migrations SQL
# ================================================================

set -e  # Arrêter en cas d'erreur

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonctions
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Banner
echo -e "${BLUE}"
echo "================================================================"
echo "   Exécution des Migrations SQL - Schéma Amélioré"
echo "================================================================"
echo -e "${NC}"

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "01_extensions.sql" ]; then
    error "Vous devez exécuter ce script depuis le répertoire sql_migrations/"
    exit 1
fi

# Vérifier les variables d'environnement
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    error "Variables SUPABASE_URL et SUPABASE_KEY non définies"
    echo ""
    echo "Définissez-les avec:"
    echo "  export SUPABASE_URL='https://xxx.supabase.co'"
    echo "  export SUPABASE_KEY='eyJxxx...'"
    exit 1
fi

# Méthode d'exécution
echo ""
info "Méthode d'exécution :"
echo "1) Via psql (nécessite DATABASE_URL)"
echo "2) Via Supabase SQL Editor (manuel - recommandé)"
echo "3) Via Python"
echo ""
read -p "Votre choix [1-3]: " method

case $method in
    1)
        # Via psql
        if [ -z "$DATABASE_URL" ]; then
            error "Variable DATABASE_URL non définie"
            echo "Définissez-la avec:"
            echo "  export DATABASE_URL='postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres'"
            exit 1
        fi

        if ! command -v psql &> /dev/null; then
            error "psql n'est pas installé"
            exit 1
        fi

        info "Exécution via psql..."
        echo ""

        # Liste des fichiers dans l'ordre
        FILES=(
            "01_extensions.sql"
            "02_table_documents_full.sql"
            "03_indexes_documents_full.sql"
            "04_table_document_chunks.sql"
            "05_indexes_document_chunks.sql"
            "06_table_extracted_entities.sql"
            "07_tables_tags.sql"
            "08_table_document_relations.sql"
            "09_functions_triggers_fulltext.sql"
            "10_indexes_fulltext.sql"
            "11_function_search_enhanced.sql"
            "12_function_search_fulltext.sql"
            "13_function_search_hybrid.sql"
            "14_materialized_views.sql"
            "15_function_refresh_views.sql"
            "16_comments.sql"
        )

        # Exécuter chaque fichier
        for file in "${FILES[@]}"; do
            info "Exécution de $file..."

            if psql "$DATABASE_URL" -f "$file" > /dev/null 2>&1; then
                success "$file exécuté avec succès"
            else
                error "Erreur lors de l'exécution de $file"
                echo ""
                echo "Détails de l'erreur:"
                psql "$DATABASE_URL" -f "$file"
                exit 1
            fi
        done

        echo ""
        success "Toutes les migrations ont été exécutées avec succès !"
        ;;

    2)
        # Manuel via Supabase
        info "Exécution manuelle recommandée"
        echo ""
        echo "Suivez ces étapes :"
        echo ""
        echo "1. Allez sur https://app.supabase.com"
        echo "2. Sélectionnez votre projet"
        echo "3. Allez dans SQL Editor"
        echo "4. Exécutez les fichiers dans l'ordre :"
        echo ""

        FILES=(
            "01_extensions.sql"
            "02_table_documents_full.sql"
            "03_indexes_documents_full.sql"
            "04_table_document_chunks.sql"
            "05_indexes_document_chunks.sql"
            "06_table_extracted_entities.sql"
            "07_tables_tags.sql"
            "08_table_document_relations.sql"
            "09_functions_triggers_fulltext.sql"
            "10_indexes_fulltext.sql"
            "11_function_search_enhanced.sql"
            "12_function_search_fulltext.sql"
            "13_function_search_hybrid.sql"
            "14_materialized_views.sql"
            "15_function_refresh_views.sql"
            "16_comments.sql"
        )

        for i in "${!FILES[@]}"; do
            echo "   $((i+1)). ${FILES[$i]}"
        done

        echo ""
        info "Consultez README_EXECUTION.md pour plus de détails"
        ;;

    3)
        # Via Python
        info "Exécution via Python..."

        cd ..
        if [ -f "run_migrations.py" ]; then
            python3 run_migrations.py
        else
            error "Script run_migrations.py introuvable"
            exit 1
        fi
        ;;

    *)
        error "Choix invalide"
        exit 1
        ;;
esac

echo ""
info "Consultez README_EXECUTION.md pour les vérifications post-migration"
echo ""
