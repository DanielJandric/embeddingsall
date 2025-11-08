#!/usr/bin/env python3
"""
Script de démonstration des niveaux de granularité de chunking.

Ce script permet de :
1. Visualiser comment différents niveaux de granularité affectent le découpage du texte
2. Comparer le nombre de chunks générés pour chaque niveau
3. Estimer l'impact sur le coût et la précision de recherche
"""

import sys
from pathlib import Path
from src.embeddings import EmbeddingGenerator
from src.chunking_config import (
    chunking_manager,
    GranularityLevel,
    GRANULARITY_CONFIGS
)


# Texte d'exemple pour la démonstration
SAMPLE_TEXT = """
L'intelligence artificielle (IA) est un domaine de l'informatique qui vise à créer des machines
capables de simuler l'intelligence humaine. Elle englobe plusieurs sous-domaines, notamment
l'apprentissage automatique (machine learning), le traitement du langage naturel, la vision
par ordinateur et la robotique.

Le machine learning est une branche de l'IA qui permet aux ordinateurs d'apprendre à partir
de données sans être explicitement programmés. Les algorithmes d'apprentissage automatique
peuvent identifier des modèles dans les données et faire des prédictions ou des décisions
basées sur ces modèles.

Le deep learning, une sous-catégorie du machine learning, utilise des réseaux de neurones
artificiels avec plusieurs couches pour traiter des données complexes. Ces réseaux sont
inspirés de la structure du cerveau humain et sont particulièrement efficaces pour des tâches
comme la reconnaissance d'images, la traduction automatique et la génération de texte.

Les applications de l'IA sont vastes et touchent de nombreux domaines : santé (diagnostic
médical, découverte de médicaments), finance (détection de fraude, trading algorithmique),
transport (véhicules autonomes), commerce (recommandations personnalisées), et bien d'autres.

Cependant, l'IA soulève également des questions éthiques importantes concernant la vie privée,
la sécurité, les biais algorithmiques et l'impact sur l'emploi. Il est crucial de développer
ces technologies de manière responsable et transparente, en tenant compte de leurs implications
sociales et économiques.

L'avenir de l'IA promet des avancées révolutionnaires dans de nombreux domaines. Les chercheurs
travaillent sur des systèmes d'IA plus généraux (AGI - Artificial General Intelligence) capables
de comprendre et d'apprendre n'importe quelle tâche intellectuelle qu'un humain peut accomplir.
Bien que nous soyons encore loin de cet objectif, les progrès récents sont remarquables.

Les embeddings textuels, comme ceux utilisés dans ce système, sont un exemple parfait de
l'application pratique de l'IA moderne. Ils permettent de représenter le sens sémantique
d'un texte sous forme de vecteurs numériques, facilitant ainsi la recherche et la comparaison
de documents basées sur leur contenu plutôt que sur de simples correspondances de mots-clés.
"""


def print_separator(char="=", length=80):
    """Affiche une ligne de séparation."""
    print(char * length)


def print_header(text):
    """Affiche un en-tête formaté."""
    print_separator()
    print(f"  {text}")
    print_separator()


def analyze_chunks(chunks, chunk_size, overlap, level_name):
    """Analyse et affiche les statistiques des chunks."""
    print(f"\n📊 {level_name}")
    print(f"   Paramètres : chunk_size={chunk_size}, overlap={overlap}")
    print(f"   Nombre de chunks : {len(chunks)}")

    if chunks:
        avg_size = sum(len(c) for c in chunks) / len(chunks)
        min_size = min(len(c) for c in chunks)
        max_size = max(len(c) for c in chunks)

        print(f"   Taille moyenne des chunks : {avg_size:.0f} caractères")
        print(f"   Taille min/max : {min_size}/{max_size} caractères")


def estimate_costs(num_chunks):
    """Estime les coûts approximatifs pour les embeddings."""
    # Prix approximatifs pour text-embedding-3-small (janvier 2025)
    # $0.020 par 1M tokens (~750k mots)
    # Estimation : ~1.3 caractères = 1 token

    tokens_per_chunk = 300  # Estimation moyenne
    total_tokens = num_chunks * tokens_per_chunk
    cost_per_1m_tokens = 0.020

    estimated_cost_per_1k_docs = (total_tokens * cost_per_1m_tokens / 1_000_000) * 1000

    return {
        "total_tokens": total_tokens,
        "cost_per_doc": (total_tokens * cost_per_1m_tokens / 1_000_000),
        "cost_per_1k_docs": estimated_cost_per_1k_docs
    }


def compare_all_levels():
    """Compare tous les niveaux de granularité disponibles."""

    print_header("COMPARAISON DES NIVEAUX DE GRANULARITÉ")

    print(f"\n📝 Texte d'exemple : {len(SAMPLE_TEXT)} caractères")
    print(f"   (~{len(SAMPLE_TEXT.split())} mots)")

    # Initialiser le générateur d'embeddings
    # Note: Pas besoin de clé API réelle pour juste tester le chunking
    try:
        embedding_gen = EmbeddingGenerator(api_key="demo-key-not-used")
    except:
        # Si ça échoue, créer une instance simple sans API
        embedding_gen = EmbeddingGenerator.__new__(EmbeddingGenerator)

    print("\n")
    print_separator("-")
    print("ANALYSE PAR NIVEAU DE GRANULARITÉ")
    print_separator("-")

    results = []

    # Tester chaque niveau de granularité
    for level in GranularityLevel:
        config = GRANULARITY_CONFIGS[level]

        # Découper le texte
        chunks = embedding_gen.chunk_text(
            SAMPLE_TEXT,
            chunk_size=config.chunk_size,
            overlap=config.overlap
        )

        # Analyser
        analyze_chunks(
            chunks,
            config.chunk_size,
            config.overlap,
            level.value.upper()
        )

        # Estimer les coûts
        costs = estimate_costs(len(chunks))

        print(f"   💰 Coût estimé : ${costs['cost_per_doc']:.6f} par document")
        print(f"   💰 Coût pour 1000 docs : ${costs['cost_per_1k_docs']:.2f}")
        print(f"   ℹ️  {config.description}")

        results.append({
            "level": level.value,
            "chunks": len(chunks),
            "config": config,
            "costs": costs
        })

    # Tableau récapitulatif
    print("\n")
    print_separator("=")
    print("TABLEAU RÉCAPITULATIF")
    print_separator("=")

    print(f"\n{'Niveau':<15} {'Chunks':<10} {'Taille':<12} {'Overlap':<12} {'Coût/1k docs':<15}")
    print_separator("-")

    for result in results:
        level = result['level']
        chunks = result['chunks']
        config = result['config']
        cost = result['costs']['cost_per_1k_docs']

        print(
            f"{level.upper():<15} "
            f"{chunks:<10} "
            f"{config.chunk_size:<12} "
            f"{config.overlap:<12} "
            f"${cost:<14.2f}"
        )

    # Recommandations
    print("\n")
    print_separator("=")
    print("RECOMMANDATIONS")
    print_separator("=")

    print("""
🎯 ULTRA_FINE (200/50) :
   ✅ Meilleure précision de recherche sémantique
   ✅ Idéal pour documents techniques détaillés
   ⚠️  Coût le plus élevé
   ⚠️  Plus de chunks = plus de temps de traitement

🎯 FINE (400/100) - RECOMMANDÉ :
   ✅ Excellent équilibre précision/coût
   ✅ Très bonne granularité pour la plupart des cas
   ✅ Configuration V2 actuelle
   ✓  Bon rapport qualité/prix

🎯 MEDIUM (600/150) :
   ✅ Bon compromis pour usage général
   ✓  Coût modéré
   ⚠️  Moins de précision que FINE

🎯 STANDARD (1000/200) :
   ✅ Bonne performance pour documents longs
   ✅ Coût réduit
   ⚠️  Configuration V1 (ancienne)
   ⚠️  Moins de granularité

🎯 COARSE (1500/300) :
   ✅ Pour très gros corpus de documents
   ✅ Coût minimal
   ⚠️  Perte significative de précision
   ⚠️  Contexte très large peut diluer le sens

💡 CONSEIL : Pour maximiser la qualité de recherche sémantique, utilisez ULTRA_FINE ou FINE.
             Le surcoût est généralement négligeable par rapport aux bénéfices en précision.
""")

    print_separator("=")


def show_chunk_preview():
    """Affiche un aperçu des premiers chunks pour ULTRA_FINE vs STANDARD."""

    print_header("APERÇU VISUEL : ULTRA_FINE vs STANDARD")

    try:
        embedding_gen = EmbeddingGenerator(api_key="demo-key-not-used")
    except:
        embedding_gen = EmbeddingGenerator.__new__(EmbeddingGenerator)

    # ULTRA_FINE
    print("\n🔹 ULTRA_FINE (200 caractères, overlap 50)")
    print_separator("-", 80)

    ultra_config = GRANULARITY_CONFIGS[GranularityLevel.ULTRA_FINE]
    ultra_chunks = embedding_gen.chunk_text(
        SAMPLE_TEXT,
        chunk_size=ultra_config.chunk_size,
        overlap=ultra_config.overlap
    )

    for i, chunk in enumerate(ultra_chunks[:3]):  # Afficher 3 premiers
        print(f"\nChunk {i+1}/{len(ultra_chunks)} ({len(chunk)} chars):")
        print(f"  «{chunk[:150]}{'...' if len(chunk) > 150 else ''}»")

    print(f"\n... ({len(ultra_chunks) - 3} autres chunks)")

    # STANDARD
    print("\n")
    print("🔹 STANDARD (1000 caractères, overlap 200)")
    print_separator("-", 80)

    standard_config = GRANULARITY_CONFIGS[GranularityLevel.STANDARD]
    standard_chunks = embedding_gen.chunk_text(
        SAMPLE_TEXT,
        chunk_size=standard_config.chunk_size,
        overlap=standard_config.overlap
    )

    for i, chunk in enumerate(standard_chunks[:2]):  # Afficher 2 premiers
        print(f"\nChunk {i+1}/{len(standard_chunks)} ({len(chunk)} chars):")
        print(f"  «{chunk[:200]}{'...' if len(chunk) > 200 else ''}»")

    print(f"\n... ({len(standard_chunks) - 2} autres chunks)")

    print("\n")
    print("💡 OBSERVATION :")
    print(f"   - ULTRA_FINE : {len(ultra_chunks)} chunks très ciblés")
    print(f"   - STANDARD : {len(standard_chunks)} chunks plus généraux")
    print(f"   - Ratio : {len(ultra_chunks)/len(standard_chunks):.1f}x plus de chunks avec ULTRA_FINE")
    print()


def main():
    """Point d'entrée principal."""

    print("\n" * 2)

    # Comparaison complète
    compare_all_levels()

    # Aperçu visuel
    print("\n" * 2)
    show_chunk_preview()

    # Configuration actuelle
    print("\n" * 2)
    print_header("CONFIGURATION ACTUELLE DU SYSTÈME")

    current_config = chunking_manager.get_config()
    current_level = chunking_manager.get_granularity_level()

    print(f"\n✅ Niveau actif : {current_level.value.upper()}")
    print(f"   Chunk size : {current_config.chunk_size} caractères")
    print(f"   Overlap : {current_config.overlap} caractères")
    print(f"   Chunks/10k : ~{current_config.chunks_per_10k}")
    print(f"   Description : {current_config.description}")

    print(f"\n💡 Pour changer le niveau, modifiez GRANULARITY_LEVEL dans .env")
    print(f"   Niveaux disponibles : ULTRA_FINE, FINE, MEDIUM, STANDARD, COARSE")
    print()


if __name__ == "__main__":
    main()
