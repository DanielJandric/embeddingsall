"""
Module pour l'extraction de texte via Azure OCR
"""

import os
import logging
from typing import List, Dict, Optional
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from PIL import Image
import pdf2image

logger = logging.getLogger(__name__)


class AzureOCRProcessor:
    """
    Processeur OCR utilisant Azure Form Recognizer pour extraire du texte
    à partir d'images et de PDFs.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        key: Optional[str] = None
    ):
        """
        Initialise le client Azure Form Recognizer.

        Args:
            endpoint: URL du endpoint Azure
            key: Clé d'API Azure
        """
        self.endpoint = endpoint or os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
        self.key = key or os.getenv("AZURE_FORM_RECOGNIZER_KEY")

        if not self.endpoint or not self.key:
            raise ValueError(
                "Azure endpoint et key doivent être fournis via les paramètres "
                "ou les variables d'environnement AZURE_FORM_RECOGNIZER_ENDPOINT "
                "et AZURE_FORM_RECOGNIZER_KEY"
            )

        self.client = DocumentAnalysisClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def extract_text_from_image(
        self,
        image_path: str,
        model_id: str = "prebuilt-read"
    ) -> Dict[str, any]:
        """
        Extrait le texte d'une image via Azure OCR.

        Args:
            image_path: Chemin vers l'image
            model_id: Modèle Azure à utiliser (prebuilt-read, prebuilt-document, etc.)

        Returns:
            Dict contenant le texte extrait et les métadonnées
        """
        logger.info(f"Extraction OCR de: {image_path}")

        logger.info("Envoi de l'image à Azure OCR...")
        with open(image_path, "rb") as f:
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                document=f
            )

        logger.info("En attente de la réponse Azure OCR...")
        result = poller.result()
        logger.info("Réponse Azure reçue !")

        # Extraire le texte complet et nettoyer les caractères null
        full_text = result.content
        if full_text:
            full_text = full_text.replace('\u0000', '').replace('\x00', '')

        # Extraire les pages et leurs contenus
        pages = []
        for page in result.pages:
            page_data = {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "unit": page.unit,
                "lines": []
            }

            # Extraire les lignes de texte
            if hasattr(page, 'lines'):
                for line in page.lines:
                    page_data["lines"].append({
                        "content": line.content,
                        "polygon": line.polygon if hasattr(line, 'polygon') else None
                    })

            pages.append(page_data)

        return {
            "file_path": image_path,
            "full_text": full_text,
            "pages": pages,
            "page_count": len(pages)
        }

    def extract_text_from_pdf(
        self,
        pdf_path: str,
        dpi: int = 300,
        model_id: str = "prebuilt-read"
    ) -> Dict[str, any]:
        """
        Extrait le texte d'un PDF en le convertissant d'abord en images.

        Args:
            pdf_path: Chemin vers le PDF
            dpi: Résolution pour la conversion
            model_id: Modèle Azure à utiliser

        Returns:
            Dict contenant le texte extrait et les métadonnées
        """
        logger.info(f"Extraction OCR du PDF: {pdf_path}")

        # Analyser directement le PDF avec Azure
        logger.info("Envoi du PDF à Azure OCR...")
        with open(pdf_path, "rb") as f:
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                document=f
            )

        logger.info("En attente de la réponse Azure OCR (cela peut prendre du temps)...")
        result = poller.result()
        logger.info("Réponse Azure reçue !")

        # Extraire le texte complet et nettoyer les caractères null
        full_text = result.content
        if full_text:
            full_text = full_text.replace('\u0000', '').replace('\x00', '')

        # Extraire les pages
        pages = []
        for page in result.pages:
            page_data = {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "lines": []
            }

            if hasattr(page, 'lines'):
                for line in page.lines:
                    page_data["lines"].append({
                        "content": line.content,
                        "polygon": line.polygon if hasattr(line, 'polygon') else None
                    })

            pages.append(page_data)

        return {
            "file_path": pdf_path,
            "full_text": full_text,
            "pages": pages,
            "page_count": len(pages)
        }

    def process_file(
        self,
        file_path: str,
        model_id: str = "prebuilt-read"
    ) -> Dict[str, any]:
        """
        Traite un fichier (image ou PDF) et extrait le texte.

        Args:
            file_path: Chemin vers le fichier
            model_id: Modèle Azure à utiliser

        Returns:
            Dict contenant le texte extrait et les métadonnées
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")

        # Déterminer le type de fichier
        ext = path.suffix.lower()

        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path, model_id=model_id)
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
            return self.extract_text_from_image(file_path, model_id=model_id)
        else:
            raise ValueError(f"Type de fichier non supporté: {ext}")

    def process_directory(
        self,
        directory_path: str,
        model_id: str = "prebuilt-read"
    ) -> List[Dict[str, any]]:
        """
        Traite tous les fichiers supportés dans un répertoire.

        Args:
            directory_path: Chemin vers le répertoire
            model_id: Modèle Azure à utiliser

        Returns:
            Liste de dicts contenant les résultats OCR
        """
        directory = Path(directory_path)

        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Répertoire invalide: {directory_path}")

        supported_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        files = [
            f for f in directory.rglob('*')
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        results = []
        for file_path in files:
            try:
                result = self.process_file(str(file_path), model_id=model_id)
                results.append(result)
                logger.info(f"Traité avec succès: {file_path}")
            except Exception as e:
                logger.error(f"Erreur lors du traitement de {file_path}: {e}")

        return results
