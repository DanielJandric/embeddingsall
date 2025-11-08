"""
Configuration de la granularité des chunks pour l'optimisation des embeddings.

Ce module fournit différents niveaux de granularité prédéfinis
ainsi qu'une configuration personnalisable.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import os


class GranularityLevel(Enum):
    """Niveaux de granularité prédéfinis pour le chunking."""

    # Très haute granularité - Maximum de chunks
    # Idéal pour : Recherche très précise, analyse fine de texte
    ULTRA_FINE = "ultra_fine"

    # Haute granularité
    # Idéal pour : Recherche sémantique précise, documents techniques
    FINE = "fine"

    # Granularité moyenne
    # Idéal pour : Usage général, bon équilibre performance/précision
    MEDIUM = "medium"

    # Granularité standard
    # Idéal pour : Documents longs, contexte plus large
    STANDARD = "standard"

    # Granularité grossière
    # Idéal pour : Très gros documents, recherche par thème
    COARSE = "coarse"


@dataclass
class ChunkingConfig:
    """Configuration des paramètres de chunking."""

    chunk_size: int
    overlap: int
    description: str
    chunks_per_10k: int  # Estimation du nombre de chunks pour 10 000 caractères

    def __str__(self):
        return (
            f"ChunkingConfig("
            f"size={self.chunk_size}, "
            f"overlap={self.overlap}, "
            f"~{self.chunks_per_10k} chunks/10k chars"
            f")"
        )


# Configurations prédéfinies pour chaque niveau de granularité
GRANULARITY_CONFIGS = {
    GranularityLevel.ULTRA_FINE: ChunkingConfig(
        chunk_size=200,
        overlap=50,
        description="Granularité ultra-fine : chunks très courts pour recherche ultra-précise",
        chunks_per_10k=60
    ),

    GranularityLevel.FINE: ChunkingConfig(
        chunk_size=400,
        overlap=100,
        description="Haute granularité : chunks courts pour recherche précise (V2 actuel)",
        chunks_per_10k=30
    ),

    GranularityLevel.MEDIUM: ChunkingConfig(
        chunk_size=600,
        overlap=150,
        description="Granularité moyenne : bon équilibre entre précision et contexte",
        chunks_per_10k=20
    ),

    GranularityLevel.STANDARD: ChunkingConfig(
        chunk_size=1000,
        overlap=200,
        description="Granularité standard : chunks de taille moyenne (V1 actuel)",
        chunks_per_10k=12
    ),

    GranularityLevel.COARSE: ChunkingConfig(
        chunk_size=1500,
        overlap=300,
        description="Granularité grossière : grands chunks pour contexte étendu",
        chunks_per_10k=8
    ),
}


class ChunkingConfigManager:
    """Gestionnaire de configuration de chunking avec support des variables d'environnement."""

    def __init__(self):
        self._config: Optional[ChunkingConfig] = None
        self._level: Optional[GranularityLevel] = None

    def get_config(self) -> ChunkingConfig:
        """
        Récupère la configuration de chunking.

        Ordre de priorité :
        1. Configuration personnalisée définie via set_custom_config()
        2. Variables d'environnement CHUNK_SIZE et CHUNK_OVERLAP
        3. Variable d'environnement GRANULARITY_LEVEL
        4. Valeur par défaut : FINE (haute granularité)

        Returns:
            ChunkingConfig: Configuration de chunking à utiliser
        """
        if self._config is not None:
            return self._config

        # Vérifier les variables d'environnement pour configuration personnalisée
        chunk_size_env = os.getenv('CHUNK_SIZE')
        chunk_overlap_env = os.getenv('CHUNK_OVERLAP')

        if chunk_size_env and chunk_overlap_env:
            try:
                chunk_size = int(chunk_size_env)
                overlap = int(chunk_overlap_env)
                # Estimation approximative des chunks
                chunks_per_10k = int(10000 / (chunk_size - overlap))
                return ChunkingConfig(
                    chunk_size=chunk_size,
                    overlap=overlap,
                    description="Configuration personnalisée depuis variables d'environnement",
                    chunks_per_10k=chunks_per_10k
                )
            except ValueError:
                pass  # Fallback vers le niveau de granularité

        # Vérifier le niveau de granularité
        level = self.get_granularity_level()
        return GRANULARITY_CONFIGS[level]

    def get_granularity_level(self) -> GranularityLevel:
        """
        Récupère le niveau de granularité.

        Returns:
            GranularityLevel: Niveau de granularité à utiliser
        """
        if self._level is not None:
            return self._level

        # Vérifier la variable d'environnement
        level_env = os.getenv('GRANULARITY_LEVEL', 'FINE').upper()

        try:
            return GranularityLevel[level_env]
        except KeyError:
            # Par défaut : FINE (haute granularité - V2)
            return GranularityLevel.FINE

    def set_granularity_level(self, level: GranularityLevel):
        """Définit le niveau de granularité."""
        self._level = level
        self._config = None  # Reset de la config personnalisée

    def set_custom_config(self, chunk_size: int, overlap: int):
        """Définit une configuration personnalisée."""
        chunks_per_10k = int(10000 / (chunk_size - overlap)) if chunk_size > overlap else 0
        self._config = ChunkingConfig(
            chunk_size=chunk_size,
            overlap=overlap,
            description="Configuration personnalisée",
            chunks_per_10k=chunks_per_10k
        )

    def reset(self):
        """Réinitialise la configuration."""
        self._config = None
        self._level = None

    def print_all_configs(self):
        """Affiche tous les niveaux de granularité disponibles."""
        print("\n" + "="*80)
        print("NIVEAUX DE GRANULARITÉ DISPONIBLES")
        print("="*80 + "\n")

        for level, config in GRANULARITY_CONFIGS.items():
            print(f"🔹 {level.value.upper()}")
            print(f"   Chunk Size: {config.chunk_size} caractères")
            print(f"   Overlap: {config.overlap} caractères")
            print(f"   Chunks/10k: ~{config.chunks_per_10k} chunks")
            print(f"   Description: {config.description}")
            print()

        print("="*80 + "\n")


# Instance globale du gestionnaire
chunking_manager = ChunkingConfigManager()


def get_chunking_params() -> tuple[int, int]:
    """
    Fonction utilitaire pour obtenir les paramètres de chunking.

    Returns:
        tuple[int, int]: (chunk_size, overlap)
    """
    config = chunking_manager.get_config()
    return config.chunk_size, config.overlap


# Exemples d'utilisation
if __name__ == "__main__":
    # Afficher tous les niveaux disponibles
    chunking_manager.print_all_configs()

    # Exemple 1 : Utiliser la configuration par défaut
    print("Configuration par défaut :")
    config = chunking_manager.get_config()
    print(config)
    print()

    # Exemple 2 : Changer le niveau de granularité
    print("Configuration ULTRA_FINE :")
    chunking_manager.set_granularity_level(GranularityLevel.ULTRA_FINE)
    config = chunking_manager.get_config()
    print(config)
    print()

    # Exemple 3 : Configuration personnalisée
    print("Configuration personnalisée :")
    chunking_manager.set_custom_config(chunk_size=300, overlap=75)
    config = chunking_manager.get_config()
    print(config)
    print()

    # Exemple 4 : Utiliser la fonction utilitaire
    chunking_manager.reset()
    chunk_size, overlap = get_chunking_params()
    print(f"Paramètres via fonction utilitaire : size={chunk_size}, overlap={overlap}")
