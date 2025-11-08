#!/usr/bin/env python3
"""
Script de test pour vérifier que tout est bien configuré
"""

import os
from dotenv import load_dotenv

print("🧪 Test de configuration...\n")

# Charger les variables d'environnement
load_dotenv()

# Test 1 : Vérifier les variables d'environnement
print("1️⃣ Vérification des variables d'environnement:")
checks = {
    "Azure Endpoint": os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT"),
    "Azure Key": os.getenv("AZURE_FORM_RECOGNIZER_KEY"),
    "OpenAI Key": os.getenv("OPENAI_API_KEY"),
    "Supabase URL": os.getenv("SUPABASE_URL"),
    "Supabase Key": os.getenv("SUPABASE_KEY"),
}

all_ok = True
for name, value in checks.items():
    if value and value not in ["votre_cle_azure", "sk-votre_cle_openai", "votre_cle_supabase", "https://votre-projet.supabase.co", "https://votre-resource.cognitiveservices.azure.com/"]:
        print(f"   ✅ {name}: Configuré")
    else:
        print(f"   ❌ {name}: MANQUANT")
        all_ok = False

print()

if not all_ok:
    print("❌ Configuration incomplète ! Vérifiez votre fichier .env")
    exit(1)

# Test 2 : Vérifier les imports
print("2️⃣ Vérification des dépendances Python:")
try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    print("   ✅ Azure Form Recognizer")
except ImportError as e:
    print(f"   ❌ Azure Form Recognizer: {e}")
    all_ok = False

try:
    from openai import OpenAI
    print("   ✅ OpenAI")
except ImportError as e:
    print(f"   ❌ OpenAI: {e}")
    all_ok = False

try:
    from supabase import create_client
    print("   ✅ Supabase")
except ImportError as e:
    print(f"   ❌ Supabase: {e}")
    all_ok = False

print()

if not all_ok:
    print("❌ Certaines dépendances manquent ! Exécutez: pip install -r requirements.txt")
    exit(1)

# Test 3 : Tester la connexion OpenAI
print("3️⃣ Test de connexion OpenAI:")
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Test simple
    response = client.embeddings.create(
        input="Test de connexion",
        model="text-embedding-3-small"
    )

    print(f"   ✅ Connexion OK - Embedding généré ({len(response.data[0].embedding)} dimensions)")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    all_ok = False

print()

# Test 4 : Tester la connexion Supabase
print("4️⃣ Test de connexion Supabase:")
try:
    from supabase import create_client

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    # Vérifier si la table existe
    response = supabase.table("documents").select("id", count="exact").limit(1).execute()
    print(f"   ✅ Connexion OK - Table 'documents' existe ({response.count if hasattr(response, 'count') else 0} entrées)")
except Exception as e:
    print(f"   ⚠️  Attention: {e}")
    print("   💡 Assurez-vous d'avoir exécuté le script supabase_setup.sql dans Supabase")

print()

# Test 5 : Tester la connexion Azure
print("5️⃣ Test de connexion Azure:")
try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential

    client = DocumentAnalysisClient(
        endpoint=os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("AZURE_FORM_RECOGNIZER_KEY"))
    )

    print("   ✅ Client Azure initialisé (test complet nécessite un document)")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    all_ok = False

print()

# Résultat final
if all_ok:
    print("=" * 60)
    print("🎉 TOUT EST BON ! Vous êtes prêt à utiliser le système !")
    print("=" * 60)
    print("\nProchaines étapes :")
    print("1. Placez vos documents dans le dossier: data/input/")
    print("2. Exécutez: python main.py -i data/input --upload")
    print("\nPour plus d'aide: python main.py --help")
else:
    print("=" * 60)
    print("⚠️  Il y a des problèmes à corriger")
    print("=" * 60)
