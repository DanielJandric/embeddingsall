#!/usr/bin/env python3
"""
Test détaillé OpenAI pour diagnostiquer le problème
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 Diagnostic complet OpenAI\n")
print("="*70)

from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
print(f"\n1. Clé API:")
print(f"   • Chargée: {api_key[:20]}...")
print(f"   • Longueur: {len(api_key)} caractères")

client = OpenAI(api_key=api_key)
print(f"\n2. Client OpenAI: ✅ Créé\n")

# Test 1: Liste des modèles
print("3. Test: Accès à l'API (liste des modèles)")
try:
    models = client.models.list()
    model_list = list(models.data)
    print(f"   ✅ API accessible - {len(model_list)} modèles trouvés")

    # Chercher les modèles d'embeddings
    embedding_models = [m.id for m in model_list if "embedding" in m.id.lower()]
    if embedding_models:
        print(f"\n   Modèles d'embeddings disponibles:")
        for m in sorted(embedding_models)[:10]:
            print(f"   • {m}")
    else:
        print("   ⚠️  Aucun modèle d'embedding trouvé")

except Exception as e:
    print(f"   ❌ Erreur: {type(e).__name__}")
    print(f"   Message: {str(e)}")

# Test 2: Génération d'embedding avec text-embedding-3-small
print("\n4. Test: Génération d'embedding (text-embedding-3-small)")
try:
    response = client.embeddings.create(
        input="Test de connexion",
        model="text-embedding-3-small"
    )
    print(f"   🎉 SUCCÈS!")
    print(f"   • Dimensions: {len(response.data[0].embedding)}")
    print(f"   • Échantillon: {response.data[0].embedding[:3]}")
except Exception as e:
    print(f"   ❌ Erreur: {type(e).__name__}")
    print(f"   Message: {str(e)}")

    # Test 3: Essayer avec text-embedding-ada-002 (ancien modèle)
    print("\n5. Test: avec text-embedding-ada-002 (ancien modèle)")
    try:
        response = client.embeddings.create(
            input="Test",
            model="text-embedding-ada-002"
        )
        print(f"   ✅ SUCCÈS avec ada-002!")
        print(f"   • Dimensions: {len(response.data[0].embedding)}")
    except Exception as e2:
        print(f"   ❌ Aussi en échec: {type(e2).__name__}")
        print(f"   Message: {str(e2)}")

print("\n" + "="*70)
print("\n💡 Diagnostic:")
print("Si tous les tests échouent avec 'Access denied':")
print("• Le problème vient du compte/organisation OpenAI")
print("• Vérifiez sur https://platform.openai.com/settings/organization/billing")
print("• Assurez-vous que le crédit est bien visible et actif")
print("• Parfois il faut attendre 5-10 minutes après avoir ajouté du crédit")
