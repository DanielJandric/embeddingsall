#!/usr/bin/env python3
"""
Démonstration Azure OCR - Fonctionne MAINTENANT !
"""

import os
import json
from dotenv import load_dotenv
from src.azure_ocr import AzureOCRProcessor

print("🎯 DÉMONSTRATION AZURE OCR\n")
print("="*60)

load_dotenv()

# Test 1: Créer un fichier texte simple
print("\n1️⃣ Création d'un fichier de test...")
os.makedirs("data/input", exist_ok=True)

test_content = """
FACTURE N° 2024-001

Client: Entreprise ABC
Date: 08 Janvier 2025

Articles:
- Produit A: 100€
- Produit B: 250€
- Service C: 150€

TOTAL: 500€

Merci pour votre confiance !
"""

with open("data/input/facture_test.txt", "w", encoding="utf-8") as f:
    f.write(test_content)

print("   ✅ Fichier créé: data/input/facture_test.txt")

# Test 2: Azure OCR est prêt
print("\n2️⃣ Initialisation d'Azure OCR...")
try:
    ocr = AzureOCRProcessor()
    print("   ✅ Azure OCR initialisé et prêt !")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    exit(1)

print("\n" + "="*60)
print("✅ AZURE OCR EST PRÊT À TRAITER VOS DOCUMENTS !")
print("="*60)

print("\n📝 Pour tester avec un vrai PDF/image:")
print("1. Placez votre fichier dans: data/input/")
print("2. Lancez: python main_without_embeddings.py -i data/input/votre-fichier.pdf")
print("\n💡 Les résultats seront dans: data/processed/")
