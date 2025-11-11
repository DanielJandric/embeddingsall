#!/usr/bin/env python3
"""
Script direct pour uploader depuis C:\OneDriveExport
"""
import os
import sys
from pathlib import Path
import hashlib
from datetime import datetime

# Valider la présence des variables d'environnement requises
required_env = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
missing = [k for k in required_env if not os.getenv(k)]
if missing:
    print(f"❌ Missing environment variables: {', '.join(missing)}")
    print("Set them in PowerShell before running, e.g.:")
    print('$env:OPENAI_API_KEY="sk-..."')
    print('$env:SUPABASE_URL="https://....supabase.co"')
    print('$env:SUPABASE_KEY="..."  # or SUPABASE_SERVICEROLE_KEY')
    sys.exit(1)

# Chunks longs avec beaucoup de contexte
CHUNK_SIZE = 2500
CHUNK_OVERLAP = 500

print("📦 Installing packages...")
os.system("pip install -q supabase openai PyPDF2 azure-ai-formrecognizer python-docx")

from supabase import create_client
from openai import OpenAI

# Clients
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def extract_text(file_path):
    """Extrait le texte d'un fichier"""
    try:
        if file_path.suffix.lower() == '.pdf':
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        elif file_path.suffix.lower() in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif file_path.suffix.lower() in ['.doc', '.docx']:
            import docx
            doc = docx.Document(str(file_path))
            return '\n'.join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"❌ Error extracting {file_path}: {e}")
    return None

def chunk_text(text):
    """Découpe en chunks longs avec overlap"""
    if len(text) <= CHUNK_SIZE:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - CHUNK_OVERLAP if end < len(text) else end
    return chunks

def process_file(file_path):
    """Traite un fichier"""
    print(f"📄 {file_path.name}")
    
    # Checksum
    with open(file_path, 'rb') as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    
    # Vérifier si déjà uploadé
    existing = supabase.table('documents_full').select('id').eq('checksum', checksum).execute()
    if existing.data:
        print(f"  ⏭️ Already uploaded")
        return
    
    # Extraire texte
    text = extract_text(file_path)
    if not text or len(text.strip()) < 10:
        print(f"  ⚠️ No text")
        return
    
    # Document principal
    doc_data = {
        'file_name': file_path.name,
        'file_path': str(file_path),
        'full_content': text,
        'file_size_bytes': file_path.stat().st_size,
        'checksum': checksum,
        'metadata': {
            'upload_date': datetime.now().isoformat(),
            'chunk_config': f'{CHUNK_SIZE}/{CHUNK_OVERLAP}'
        }
    }
    
    doc_result = supabase.table('documents_full').insert(doc_data).execute()
    if not doc_result.data:
        print(f"  ❌ Insert failed")
        return
    
    doc_id = doc_result.data[0]['id']
    
    # Chunks
    chunks = chunk_text(text)
    for idx, chunk in enumerate(chunks):
        # Embedding
        try:
            response = openai_client.embeddings.create(
                input=chunk[:8000],
                model="text-embedding-3-small"
            )
            embedding = response.data[0].embedding
        except:
            embedding = []
        
        # Contexte
        chunk_data = {
            'document_id': doc_id,
            'chunk_index': idx,
            'chunk_content': chunk,
            'chunk_size': len(chunk),  # Colonne directe requise par Supabase
            'embedding': embedding,
            'chunk_metadata': {'total': len(chunks), 'size': len(chunk)}
        }
        
        if idx > 0:
            chunk_data['context_before'] = chunks[idx-1][-200:]
        if idx < len(chunks)-1:
            chunk_data['context_after'] = chunks[idx+1][:200]
        
        supabase.table('document_chunks').insert(chunk_data).execute()
    
    print(f"  ✅ {len(chunks)} chunks")

# Main
input_dir = Path(r"C:\OneDriveExport")
files = list(input_dir.rglob('*.pdf')) + list(input_dir.rglob('*.txt')) + \
        list(input_dir.rglob('*.doc')) + list(input_dir.rglob('*.docx'))

print(f"\n📁 Processing {len(files)} files from {input_dir}\n")

for file in files:
    try:
        process_file(file)
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n✅ DONE!")
