import os
from pathlib import Path
from typing import Optional

def _read_text_file(file_path: str, encoding: str = "utf-8") -> str:
    with open(file_path, "r", encoding=encoding, errors="ignore") as f:
        return f.read()

def _read_pdf(file_path: str) -> str:
    try:
        from PyPDF2 import PdfReader  # requirements already include PyPDF2
    except Exception:
        return ""
    try:
        reader = PdfReader(file_path)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(texts).strip()
    except Exception:
        return ""

def extract_text_from_file(file_path: str) -> str:
    """
    Extraction minimale de texte:
    - TXT / MD: lecture directe
    - PDF: PyPDF2
    - Autres: tentative de lecture texte, sinon vide
    """
    if not file_path or not os.path.exists(file_path):
        return ""
    ext = Path(file_path).suffix.lower()
    if ext in [".txt", ".md", ".csv", ".json", ".yaml", ".yml"]:
        return _read_text_file(file_path)
    if ext == ".pdf":
        return _read_pdf(file_path)
    # fallback: essayer en texte brut
    try:
        return _read_text_file(file_path)
    except Exception:
        return ""


