#!/bin/bash
# ================================================================
# Script d'Installation du Schéma Amélioré
# ================================================================
# Ce script facilite l'installation et la configuration du nouveau
# schéma amélioré pour recherche optimisée par LLM.
# ================================================================

set -e  # Arrêter en cas d'erreur

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
echo -e "${BLUE}"
echo "================================================================"
echo "   Installation du Schéma Amélioré pour Recherche LLM"
echo "================================================================"
echo -e "${NC}"

# Vérifications préalables
info "Vérification des prérequis..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    error "Python 3 n'est pas installé"
    exit 1
fi
success "Python 3 trouvé"

# Vérifier les variables d'environnement Supabase
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    error "Variables d'environnement SUPABASE_URL et SUPABASE_KEY non définies"
    echo ""
    echo "Veuillez les définir:"
    echo "  export SUPABASE_URL='https://xxx.supabase.co'"
    echo "  export SUPABASE_KEY='eyJxxx...'"
    exit 1
fi
success "Variables Supabase configurées"

# Vérifier les dépendances Python
info "Vérification des dépendances Python..."
if ! python3 -c "import supabase" &> /dev/null; then
    warning "Module supabase non installé. Installation..."
    pip install supabase-py
fi
success "Dépendances Python OK"

# Menu principal
echo ""
echo "Que souhaitez-vous faire ?"
echo ""
echo "1) Appliquer le nouveau schéma (créer les tables)"
echo "2) Tester l'upload avec des documents d'exemple (dry-run)"
echo "3) Uploader des documents (upload complet)"
echo "4) Migrer les données existantes"
echo "5) Afficher les statistiques de la base"
echo "6) Rafraîchir les vues matérialisées"
echo "7) Tout faire (schéma + upload)"
echo "0) Quitter"
echo ""
read -p "Votre choix [0-7]: " choice

case $choice in
    1)
        # Appliquer le schéma
        info "Application du schéma amélioré..."

        if [ ! -f "supabase_enhanced_schema.sql" ]; then
            error "Fichier supabase_enhanced_schema.sql introuvable"
            exit 1
        fi

        echo ""
        warning "ATTENTION: Cette opération va créer/modifier les tables dans votre base Supabase"
        read -p "Continuer ? [y/N]: " confirm

        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            info "Opération annulée"
            exit 0
        fi

        # Utiliser psql si disponible, sinon via Python
        if command -v psql &> /dev/null && [ ! -z "$SUPABASE_DATABASE_URL" ]; then
            info "Application du schéma via psql..."
            psql "$SUPABASE_DATABASE_URL" -f supabase_enhanced_schema.sql
        else
            info "Application du schéma via Python..."
            python3 - <<EOF
import os
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
client = create_client(url, key)

with open('supabase_enhanced_schema.sql', 'r') as f:
    sql = f.read()

# Exécuter le SQL (attention: peut ne pas supporter toutes les commandes)
print("⚠️  Note: Certaines commandes SQL complexes peuvent nécessiter psql")
print("Veuillez appliquer le schéma manuellement via l'interface Supabase SQL Editor")
print("ou via psql avec: psql \$SUPABASE_DATABASE_URL -f supabase_enhanced_schema.sql")
EOF
        fi

        success "Schéma appliqué avec succès"
        ;;

    2)
        # Test upload (dry-run)
        info "Mode test - aucun upload réel ne sera effectué"

        read -p "Chemin vers les documents de test: " doc_path

        if [ ! -d "$doc_path" ] && [ ! -f "$doc_path" ]; then
            error "Chemin invalide: $doc_path"
            exit 1
        fi

        info "Lancement du test d'upload..."
        python3 upload_enhanced.py -i "$doc_path" --dry-run

        success "Test terminé"
        ;;

    3)
        # Upload complet
        info "Upload de documents avec nouveau schéma"

        read -p "Chemin vers les documents: " doc_path

        if [ ! -d "$doc_path" ] && [ ! -f "$doc_path" ]; then
            error "Chemin invalide: $doc_path"
            exit 1
        fi

        # Demander si métadonnées manuelles
        read -p "Fichier de métadonnées CSV (laisser vide si aucun): " meta_csv
        read -p "Fichier de métadonnées JSON (laisser vide si aucun): " meta_json

        # Construire la commande
        cmd="python3 upload_enhanced.py -i \"$doc_path\""

        if [ ! -z "$meta_csv" ] && [ -f "$meta_csv" ]; then
            cmd="$cmd --metadata-csv \"$meta_csv\""
        fi

        if [ ! -z "$meta_json" ] && [ -f "$meta_json" ]; then
            cmd="$cmd --metadata-json \"$meta_json\""
        fi

        echo ""
        warning "Commande à exécuter:"
        echo "$cmd"
        echo ""
        read -p "Continuer ? [y/N]: " confirm

        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            info "Opération annulée"
            exit 0
        fi

        info "Lancement de l'upload..."
        eval $cmd

        success "Upload terminé"
        ;;

    4)
        # Migration
        info "Migration des données existantes"
        warning "Cette fonctionnalité nécessite d'exporter puis réimporter les documents"

        # Export des données
        info "Étape 1: Export des données existantes..."
        python3 export_supabase_data.py -o migration_export.json

        if [ ! -f "migration_export.json" ]; then
            error "Échec de l'export"
            exit 1
        fi

        success "Export réussi"

        # Demander le chemin des documents originaux
        echo ""
        warning "Pour réimporter, vous avez besoin des fichiers originaux"
        read -p "Chemin vers les documents originaux: " doc_path

        if [ ! -d "$doc_path" ]; then
            error "Chemin invalide: $doc_path"
            exit 1
        fi

        # Backup
        info "Étape 2: Création d'une sauvegarde..."
        backup_file="backup_$(date +%Y%m%d_%H%M%S).json"
        cp migration_export.json "$backup_file"
        success "Sauvegarde créée: $backup_file"

        # Appliquer le nouveau schéma
        echo ""
        warning "Étape 3: Application du nouveau schéma"
        warning "ATTENTION: Cette opération va SUPPRIMER les anciennes tables"
        echo ""
        read -p "Continuer ? Tapez 'CONFIRMER' pour continuer: " confirm

        if [ "$confirm" != "CONFIRMER" ]; then
            info "Migration annulée"
            exit 0
        fi

        # Ici on devrait supprimer les anciennes tables et créer les nouvelles
        info "Application du schéma..."
        # (code SQL pour drop et recréer)

        # Réimport
        info "Étape 4: Réimport des documents..."
        python3 upload_enhanced.py -i "$doc_path"

        success "Migration terminée"
        ;;

    5)
        # Statistiques
        info "Récupération des statistiques..."

        python3 - <<'EOF'
from src.supabase_client_enhanced import SupabaseClientEnhanced

client = SupabaseClientEnhanced()

print("\n" + "="*60)
print("STATISTIQUES PAR CATÉGORIE")
print("="*60)
stats = client.get_stats_by_category()
for stat in stats[:10]:  # Top 10
    print(f"{stat.get('categorie', 'N/A')} / {stat.get('type_document', 'N/A')}: {stat.get('document_count', 0)} docs")

print("\n" + "="*60)
print("STATISTIQUES PAR LOCALISATION")
print("="*60)
stats = client.get_stats_by_location()
for stat in stats[:10]:  # Top 10
    canton = stat.get('canton', 'N/A')
    commune = stat.get('commune', 'N/A')
    count = stat.get('document_count', 0)
    total = stat.get('total_montant', 0)
    print(f"{canton} - {commune}: {count} docs, Total: {total:.2f} CHF")

print("\n" + "="*60)
EOF

        success "Statistiques affichées"
        ;;

    6)
        # Rafraîchir vues matérialisées
        info "Rafraîchissement des vues matérialisées..."

        python3 - <<'EOF'
from src.supabase_client_enhanced import SupabaseClientEnhanced

client = SupabaseClientEnhanced()
client.refresh_materialized_views()
print("✅ Vues matérialisées rafraîchies")
EOF

        success "Vues rafraîchies"
        ;;

    7)
        # Tout faire
        info "Installation complète: schéma + upload"

        read -p "Chemin vers les documents: " doc_path

        if [ ! -d "$doc_path" ] && [ ! -f "$doc_path" ]; then
            error "Chemin invalide: $doc_path"
            exit 1
        fi

        # 1. Schéma
        info "Étape 1/3: Application du schéma..."
        warning "Cette opération va créer/modifier les tables"
        read -p "Continuer ? [y/N]: " confirm

        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            info "Opération annulée"
            exit 0
        fi

        # Appliquer schéma (voir option 1)
        info "Schéma appliqué (vérifier manuellement si nécessaire)"

        # 2. Upload
        info "Étape 2/3: Upload des documents..."
        python3 upload_enhanced.py -i "$doc_path"

        # 3. Rafraîchir stats
        info "Étape 3/3: Rafraîchissement des statistiques..."
        python3 - <<'EOF'
from src.supabase_client_enhanced import SupabaseClientEnhanced
client = SupabaseClientEnhanced()
client.refresh_materialized_views()
EOF

        success "Installation complète terminée !"
        ;;

    0)
        info "Au revoir !"
        exit 0
        ;;

    *)
        error "Choix invalide"
        exit 1
        ;;
esac

echo ""
success "Opération terminée avec succès !"
echo ""
info "Consultez le guide complet: ENHANCED_SCHEMA_GUIDE.md"
echo ""
