#!/usr/bin/env python3
"""
Script de test pour vérifier que tout fonctionne
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

print("="*70)
print("TEST DU SYSTÈME DE RECHERCHE ET CHATBOT")
print("="*70)

# Vérifier les variables d'environnement
print("\n1. Vérification des variables d'environnement...")

required_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
missing = []

for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"   ✅ {var}: {'*' * 10} (défini)")
    else:
        print(f"   ❌ {var}: Non défini")
        missing.append(var)

if missing:
    print(f"\n❌ Variables manquantes: {', '.join(missing)}")
    print("   Vérifiez votre fichier .env")
    sys.exit(1)

print("\n✅ Toutes les variables d'environnement sont définies\n")

# Test 1: Importer les modules
print("2. Test des imports...")

try:
    from src.embeddings import EmbeddingGenerator
    print("   ✅ EmbeddingGenerator importé")
except Exception as e:
    print(f"   ❌ Erreur import EmbeddingGenerator: {e}")
    sys.exit(1)

try:
    from src.supabase_client import SupabaseUploader
    print("   ✅ SupabaseUploader importé")
except Exception as e:
    print(f"   ❌ Erreur import SupabaseUploader: {e}")
    sys.exit(1)

try:
    from src.semantic_search import SemanticSearchEngine
    print("   ✅ SemanticSearchEngine importé")
except Exception as e:
    print(f"   ❌ Erreur import SemanticSearchEngine: {e}")
    sys.exit(1)

print("\n✅ Tous les modules importés\n")

# Test 2: Connexion Supabase
print("3. Test de la connexion Supabase...")

try:
    uploader = SupabaseUploader()
    stats = uploader.get_table_stats("documents")

    total_docs = stats.get('total_documents', 0)
    print(f"   ✅ Connexion Supabase réussie")
    print(f"   📊 Documents dans la base: {total_docs}")

    if total_docs == 0:
        print("\n   ⚠️  ATTENTION: La base de données est vide")
        print("   Exécutez d'abord: python process_fast.py -i 'dossier' --upload")
        sys.exit(0)

except Exception as e:
    print(f"   ❌ Erreur Supabase: {e}")
    print("\n   Vérifiez que:")
    print("   1. Vous avez exécuté supabase_setup.sql dans votre dashboard")
    print("   2. SUPABASE_URL et SUPABASE_KEY sont corrects")
    sys.exit(1)

print()

# Test 3: Génération d'embeddings
print("4. Test de génération d'embeddings...")

try:
    emb_gen = EmbeddingGenerator()
    test_text = "Ceci est un test"
    embedding = emb_gen.generate_embedding(test_text)

    print(f"   ✅ Embedding généré")
    print(f"   📐 Dimensions: {len(embedding)}")

    if len(embedding) != 1536:
        print(f"   ⚠️  Attention: dimension attendue 1536, obtenu {len(embedding)}")

except Exception as e:
    print(f"   ❌ Erreur génération embedding: {e}")
    print("\n   Vérifiez OPENAI_API_KEY")
    sys.exit(1)

print()

# Test 4: Recherche sémantique
print("5. Test de recherche sémantique...")

try:
    search_engine = SemanticSearchEngine()

    # Recherche de test
    results = search_engine.search(
        query="information",
        limit=3,
        threshold=0.5  # Seuil bas pour avoir des résultats
    )

    print(f"   ✅ Recherche exécutée")
    print(f"   📊 Résultats trouvés: {len(results)}")

    if results:
        print(f"\n   Premier résultat:")
        print(f"   - Fichier: {results[0]['file_name']}")
        print(f"   - Similarité: {results[0]['similarity']:.1%}")
        print(f"   - Contenu (100 premiers caractères):")
        content = results[0]['content'][:100]
        print(f"     {content}...")
    else:
        print("\n   ⚠️  Aucun résultat trouvé")
        print("   Essayez avec un seuil plus bas ou une autre requête")

except Exception as e:
    print(f"   ❌ Erreur recherche: {e}")
    import traceback
    traceback.print_exc()

    print("\n   Vérifiez que:")
    print("   1. La fonction match_documents existe dans Supabase")
    print("   2. Vous avez exécuté supabase_setup.sql")
    sys.exit(1)

print()

# Test 5: Test chatbot (optionnel)
print("6. Test du chatbot...")

try:
    from chatbot import DocumentChatbot

    chatbot = DocumentChatbot(
        model="gpt-4o-mini",
        search_limit=3,
        search_threshold=0.5
    )

    print(f"   ✅ Chatbot initialisé")
    print(f"   🤖 Modèle: gpt-4o-mini")

    # Test d'une question simple (sans affichage complet)
    print("\n   Test d'une question simple...")
    sources, context = chatbot.search_documents("information")

    if sources:
        print(f"   ✅ Contexte récupéré: {len(sources)} sources")
    else:
        print(f"   ⚠️  Aucune source trouvée")

except Exception as e:
    print(f"   ⚠️  Erreur chatbot: {e}")
    print("   (Non bloquant, le reste fonctionne)")

print()

# Résumé
print("="*70)
print("✅ TESTS TERMINÉS AVEC SUCCÈS")
print("="*70)
print()
print("Vous pouvez maintenant utiliser:")
print()
print("1. Recherche sémantique:")
print("   python -c \"from src.semantic_search import SemanticSearchEngine; \\")
print("              engine = SemanticSearchEngine(); \\")
print("              print(engine.search_and_format('votre question'))\"")
print()
print("2. Chatbot interactif:")
print("   python chatbot.py")
print()
print("3. Chatbot question unique:")
print("   python chatbot.py -q 'Votre question?'")
print()
print("4. Serveur MCP:")
print("   python mcp_server.py")
print()
print("="*70)
