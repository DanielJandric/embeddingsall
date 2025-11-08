"""
Module pour extraire le texte directement des PDFs (sans OCR)
Beaucoup plus rapide et fonctionne pour les gros fichiers
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extrait le texte directement d'un PDF (sans OCR).
    Fonctionne pour les PDFs qui contiennent du texte.

    Args:
        pdf_path: Chemin vers le PDF

    Returns:
        Le texte extrait ou None si échec
    """
    try:
        from PyPDF2 import PdfReader

        logger.info(f"Extraction texte direct du PDF: {Path(pdf_path).name}")

        reader = PdfReader(pdf_path)
        text_parts = []

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n".join(text_parts)

        # Nettoyer les caractères null et autres caractères problématiques
        full_text = full_text.replace('\u0000', '')  # Supprimer les caractères null
        full_text = full_text.replace('\x00', '')     # Supprimer les null bytes

        if full_text.strip():
            logger.info(f"✅ {len(full_text)} caractères extraits de {len(reader.pages)} pages")
            return full_text
        else:
            logger.warning(f"⚠️  Aucun texte trouvé dans le PDF (peut-être un scan)")
            return None

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction du texte: {e}")
        return None
