#!/usr/bin/env python3
"""
Script pour vérifier le statut de l'upload
"""
import os
from pathlib import Path
from collections import defaultdict

# Configuration (utilise l'environnement)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICEROLE_KEY") or os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY/SUPABASE_SERVICEROLE_KEY")
    print('Set in PowerShell, e.g.:')
    print('$env:SUPABASE_URL="https://YOUR.supabase.co"')
    print('$env:SUPABASE_SERVICEROLE_KEY="..."')
    raise SystemExit(1)

print("📦 Installing packages...")
os.system("pip install -q supabase")

from supabase import create_client

# Client Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Répertoire source
input_dir = Path(r"C:\OneDriveExport")

# Extensions supportées
extensions = ['.pdf', '.txt', '.doc', '.docx', '.md', 
              '.png', '.jpg', '.jpeg', '.tiff', '.bmp',
              '.xlsx', '.xls', '.csv']

print("\n" + "="*70)
print("📊 ANALYSE DU STATUT D'UPLOAD")
print("="*70)

# 1. Compter les fichiers locaux
print("\n📁 FICHIERS LOCAUX (C:\\OneDriveExport):")
print("-"*40)

local_files = []
file_types = defaultdict(int)
total_size_mb = 0

for ext in extensions:
    files = list(input_dir.rglob(f'*{ext}'))
    local_files.extend(files)
    file_types[ext] = len(files)
    for f in files:
        try:
            total_size_mb += f.stat().st_size / 1048576
        except:
            pass

print(f"📄 Total fichiers trouvés: {len(local_files)}")
print(f"💾 Taille totale: {total_size_mb:.1f} MB")
print("\nPar type:")
for ext, count in sorted(file_types.items()):
    if count > 0:
        print(f"  {ext}: {count} fichiers")

# 2. Compter dans Supabase
print("\n📤 FICHIERS DANS SUPABASE:")
print("-"*40)

# Récupérer tous les documents
try:
    # Compter les documents
    count_result = supabase.table('documents_full').select('id', count='exact').execute()
    doc_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
    
    # Récupérer les stats
    stats_result = supabase.table('documents_full').select('file_name, file_size_bytes, created_at').execute()
    
    uploaded_files = set()
    uploaded_size_mb = 0
    uploaded_types = defaultdict(int)
    
    for doc in stats_result.data:
        uploaded_files.add(doc['file_name'])
        if doc['file_size_bytes']:
            uploaded_size_mb += doc['file_size_bytes'] / 1048576
        
        # Déterminer le type
        for ext in extensions:
            if doc['file_name'].lower().endswith(ext):
                uploaded_types[ext] += 1
                break
    
    print(f"✅ Documents uploadés: {len(uploaded_files)}")
    print(f"💾 Taille uploadée: {uploaded_size_mb:.1f} MB")
    
    print("\nPar type uploadé:")
    for ext, count in sorted(uploaded_types.items()):
        if count > 0:
            print(f"  {ext}: {count} fichiers")
    
    # Compter les chunks
    chunks_result = supabase.table('document_chunks').select('id', count='exact').execute()
    chunk_count = chunks_result.count if hasattr(chunks_result.count) else 0
    print(f"\n📊 Chunks créés: {chunk_count}")
    
except Exception as e:
    print(f"❌ Erreur Supabase: {e}")
    uploaded_files = set()

# 3. Calculer ce qui reste
print("\n🔄 STATUT:")
print("-"*40)

# Fichiers restants
local_file_names = {f.name for f in local_files}
remaining_files = local_file_names - uploaded_files
already_uploaded = local_file_names & uploaded_files

print(f"✅ Déjà uploadés: {len(already_uploaded)} / {len(local_files)} ({100*len(already_uploaded)/len(local_files):.1f}%)")
print(f"⏳ Reste à uploader: {len(remaining_files)} fichiers")
print(f"📈 Progression: {'█' * int(50*len(already_uploaded)/len(local_files))}{'░' * (50-int(50*len(already_uploaded)/len(local_files)))}")

# Estimation du temps restant
if len(remaining_files) > 0:
    print(f"\n⏱️  ESTIMATION:")
    print(f"   Avec 3 workers: ~{len(remaining_files) * 10 / 60:.1f} minutes")
    print(f"   Avec 5 workers: ~{len(remaining_files) * 6 / 60:.1f} minutes")

# Afficher quelques fichiers restants
if remaining_files:
    print(f"\n📋 Exemples de fichiers à uploader:")
    for i, fname in enumerate(list(remaining_files)[:10]):
        print(f"   - {fname}")
    if len(remaining_files) > 10:
        print(f"   ... et {len(remaining_files) - 10} autres")

print("\n" + "="*70)
print("✨ Analyse terminée!")
print("="*70)
