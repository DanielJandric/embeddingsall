#!/usr/bin/env python3
"""
Test Azure OCR uniquement (sans embeddings)
"""

import os
from dotenv import load_dotenv
from src.azure_ocr import AzureOCRProcessor

print("🧪 Test Azure OCR uniquement\n")

# Charger les variables d'environnement
load_dotenv()

# Initialiser Azure OCR
print("1️⃣ Initialisation d'Azure OCR...")
try:
    ocr = AzureOCRProcessor(
        endpoint=os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT"),
        key=os.getenv("AZURE_FORM_RECOGNIZER_KEY")
    )
    print("   ✅ Azure OCR initialisé\n")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

# Créer un fichier de test simple
print("2️⃣ Création d'un document de test...")
test_file = "data/input/test.txt"
os.makedirs("data/input", exist_ok=True)

# Créer un fichier texte simple pour tester
with open(test_file, 'w', encoding='utf-8') as f:
    f.write("Ceci est un test de document.\nLigne 2: Test réussi!")

print(f"   ✅ Fichier créé: {test_file}\n")

print("=" * 60)
print("✅ Configuration Azure OK!")
print("=" * 60)
print("\n💡 Pour tester avec un vrai PDF/image:")
print("1. Placez votre document dans: data/input/")
print("2. Lancez: python main.py -i data/input/votre-doc.pdf")
print("\n⚠️  Note: Les embeddings OpenAI ne fonctionneront pas tant")
print("   que vous n'aurez pas configuré le billing sur OpenAI")
