#!/bin/bash

# Script d'installation et de configuration

echo "🚀 Installation du système d'embeddings..."

# Créer l'environnement virtuel
echo "📦 Création de l'environnement virtuel..."
python3 -m venv venv

# Activer l'environnement virtuel
echo "✅ Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "📥 Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

# Créer le fichier .env s'il n'existe pas
if [ ! -f .env ]; then
    echo "📝 Création du fichier .env..."
    cp .env.example .env
    echo "⚠️  N'oubliez pas de configurer vos clés API dans le fichier .env"
else
    echo "✅ Le fichier .env existe déjà"
fi

# Créer les répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p data/input data/processed logs

# Rendre le script principal exécutable
chmod +x main.py

echo ""
echo "✨ Installation terminée!"
echo ""
echo "Prochaines étapes:"
echo "1. Éditez le fichier .env avec vos clés API"
echo "2. Configurez votre base Supabase (voir README.md)"
echo "3. Placez vos documents dans data/input/"
echo "4. Exécutez: python main.py -i data/input --upload"
echo ""
