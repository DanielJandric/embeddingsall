#!/usr/bin/env python3
"""
Script simple pour uploader des documents vers Supabase
"""

import os
import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au path Python
sys.path.insert(0, str(Path(__file__).parent))

def process_file(file_path, uploader):
    """Traite un fichier individuel"""
    try:
        logger.info(f"📄 Processing: {file_path}")
        
        # Lire le fichier
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Calculer le hash
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Extraire le texte selon le type
        if file_path.suffix.lower() == '.txt':
            text = content.decode('utf-8', errors='ignore')
        elif file_path.suffix.lower() == '.pdf':
            try:
                import PyPDF2
                import io
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                text = ' '.join(page.extract_text() for page in pdf_reader.pages)
            except:
                logger.warning(f"Could not extract text from PDF: {file_path}")
                return None
        else:
            text = content.decode('utf-8', errors='ignore')
        
        if not text or len(text.strip()) < 10:
            logger.warning(f"⚠️ Skipping {file_path} - no text content")
            return None
            
        # Upload vers Supabase
        result = uploader.upload_document(
            file_path=str(file_path),
            text_content=text,
            metadata={
                'file_name': file_path.name,
                'file_size': len(content),
                'checksum': file_hash,
                'upload_date': datetime.now().isoformat()
            }
        )
        
        logger.info(f"✅ Uploaded: {file_path.name}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing {file_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Upload documents to Supabase')
    parser.add_argument('-i', '--input', required=True, help='Input directory')
    parser.add_argument('--workers', type=int, default=3, help='Number of workers')
    args = parser.parse_args()
    
    # Vérifier les variables d'environnement
    required_env = ['OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY']
    missing = [v for v in required_env if not os.getenv(v)]
    
    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        logger.info("Set them with:")
        for var in missing:
            logger.info(f'  $env:{var} = "your_value_here"')
        sys.exit(1)
    
    # Importer l'uploader
    try:
        from src.supabase_client_enhanced import SupabaseClientEnhanced
        uploader = SupabaseClientEnhanced()
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("Installing dependencies...")
        os.system("python -m pip install supabase openai python-dotenv PyPDF2")
        from src.supabase_client_enhanced import SupabaseClientEnhanced
        uploader = SupabaseClientEnhanced()
    
    # Trouver tous les fichiers
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"❌ Input directory not found: {input_path}")
        sys.exit(1)
    
    extensions = ['.txt', '.pdf', '.doc', '.docx', '.md']
    files = []
    for ext in extensions:
        files.extend(input_path.rglob(f'*{ext}'))
    
    logger.info(f"📁 Found {len(files)} files to process")
    
    if not files:
        logger.warning("No files found!")
        return
    
    # Traiter les fichiers en parallèle
    success_count = 0
    error_count = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_file, f, uploader): f for f in files}
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                success_count += 1
            else:
                error_count += 1
    
    # Résumé
    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Successfully uploaded: {success_count} files")
    logger.info(f"❌ Failed: {error_count} files")
    logger.info(f"{'='*50}")

if __name__ == "__main__":
    main()
