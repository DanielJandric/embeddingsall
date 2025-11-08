"""
Configuration du logging pour l'application
"""

import logging
import sys
from pathlib import Path

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


def setup_logger(
    name: str = "embeddings",
    level: int = logging.INFO,
    log_file: str = None
) -> logging.Logger:
    """
    Configure et retourne un logger.

    Args:
        name: Nom du logger
        level: Niveau de logging
        log_file: Fichier de log optionnel

    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Éviter les doublons
    if logger.handlers:
        return logger

    # Format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Console handler avec couleurs si disponible
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if COLORLOG_AVAILABLE:
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt=date_format,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    else:
        formatter = logging.Formatter(log_format, datefmt=date_format)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler si demandé
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
