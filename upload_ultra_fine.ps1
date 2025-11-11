# Script PowerShell pour upload ultra-fin avec contexte enrichi
# Chunks longs (2500 chars) avec grand overlap (500 chars) pour contexte maximal

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Configuration pour extraction ultra-fine
Write-Host "🔧 Configuration ULTRA-FINE avec chunks longs et contexte enrichi..." -ForegroundColor Cyan

# Variables d'environnement - AZURE OCR pour extraction maximale
$env:AZURE_FORM_RECOGNIZER_ENDPOINT = "https://mcpdj.cognitiveservices.azure.com/"
$env:AZURE_FORM_RECOGNIZER_KEY = "AZURE_KEY_REDACTED"

# OpenAI pour embeddings
$env:OPENAI_API_KEY = "OPENAI_KEY_REDACTED"
$env:EMBEDDING_MODEL = "text-embedding-3-small"

# Supabase
$env:SUPABASE_URL = "https://kpfitkmaaztrjwqvockf.supabase.co"
$env:SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtwZml0a21hYXp0cmp3cXZvY2tmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI1OTA5MjgsImV4cCI6MjA3ODE2NjkyOH0.bX83QyPdlTBz0wc4qqyjKsY7jAFNkGFdG-Affo8AhEQ"
$env:SUPABASE_SERVICEROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtwZml0a21hYXp0cmp3cXZvY2tmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjU5MDkyOCwiZXhwIjoyMDc4MTY2OTI4fQ.NYrNsMHTy-GVgyUAsiC0l1-mU-mdQUXZLs2CW-O5yAQ"

# CONFIGURATION ULTRA-FINE: Chunks longs avec beaucoup de contexte
$env:CHUNK_SIZE = "2500"        # Chunks plus longs pour plus de contexte
$env:CHUNK_OVERLAP = "500"      # Grand overlap pour continuité
$env:GRANULARITY_LEVEL = "ULTRA_FINE"
$env:BATCH_SIZE = "50"          # Batch plus petit pour précision
$env:MAX_WORKERS = "3"

Write-Host "📊 Configuration:" -ForegroundColor Green
Write-Host "   - Chunk Size: 2500 chars (longs chunks)" -ForegroundColor Yellow
Write-Host "   - Overlap: 500 chars (20% overlap pour contexte)" -ForegroundColor Yellow
Write-Host "   - Granularity: ULTRA_FINE" -ForegroundColor Yellow
Write-Host "   - Workers: 3 parallel processes" -ForegroundColor Yellow
Write-Host ""

# Aller dans le répertoire du projet
Set-Location "C:\Users\DanielJandric\embeddingsall"

# Vérifier que le répertoire source existe
$sourceDir = "C:\OneDriveExport"
if (-not (Test-Path $sourceDir)) {
    Write-Host "❌ ERROR: Directory not found: $sourceDir" -ForegroundColor Red
    exit 1
}

# Compter les fichiers
$fileCount = (Get-ChildItem -Path $sourceDir -Recurse -Include *.pdf,*.txt,*.doc,*.docx,*.md | Measure-Object).Count
Write-Host "📁 Found $fileCount documents in $sourceDir" -ForegroundColor Cyan
Write-Host ""

# Lancer l'upload avec configuration ultra-fine
Write-Host "🚀 Starting ULTRA-FINE upload with enriched context..." -ForegroundColor Green
Write-Host "   This will create longer chunks with more context for better LLM understanding" -ForegroundColor Gray
Write-Host ""

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "upload_ultra_fine_$timestamp.log"

try {
    # Essayer avec python d'abord
    python upload_complete.py -i $sourceDir --workers 3 2>&1 | Tee-Object -FilePath $logFile
} catch {
    # Sinon essayer avec py
    py upload_complete.py -i $sourceDir --workers 3 2>&1 | Tee-Object -FilePath $logFile
}

Write-Host ""
Write-Host "✅ Upload completed! Log saved to: $logFile" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Note: Ultra-fine configuration creates:" -ForegroundColor Cyan
Write-Host "   - Longer chunks (2500 chars) for more context" -ForegroundColor Gray
Write-Host "   - 500 char overlap between chunks for continuity" -ForegroundColor Gray
Write-Host "   - Better context preservation for LLM understanding" -ForegroundColor Gray
Write-Host "   - Ideal for complex documents with poor formatting" -ForegroundColor Gray
