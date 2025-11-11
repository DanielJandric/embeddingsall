# ============================================================================
# Script PowerShell : Upload avec Granularité Maximale
# ============================================================================
#
# Ce script :
# - Vérifie l'environnement Python
# - Installe les dépendances si nécessaire
# - Configure la granularité maximale
# - Lance le traitement avec 3 workers
#
# Usage : .\run_upload.ps1
# ============================================================================

param(
    [string]$InputPath = "c:\OneDriveExport",
    [string]$GranularityLevel = "ULTRA_FINE",
    [int]$Workers = 3,
    [switch]$SkipDependencyCheck,
    [switch]$NoUpload,
    [switch]$NoOCR
)

# Couleurs pour les messages
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-ColorOutput Yellow ("=" * 80)
    Write-ColorOutput Yellow "  $Text"
    Write-ColorOutput Yellow ("=" * 80)
    Write-Host ""
}

function Write-Success {
    param([string]$Text)
    Write-ColorOutput Green "[✓] $Text"
}

function Write-Error-Custom {
    param([string]$Text)
    Write-ColorOutput Red "[✗] $Text"
}

function Write-Info {
    param([string]$Text)
    Write-ColorOutput Cyan "[i] $Text"
}

# ============================================================================
# ÉTAPE 1 : Vérification de l'environnement
# ============================================================================

Write-Header "VÉRIFICATION DE L'ENVIRONNEMENT"

# Vérifier Python
Write-Info "Vérification de Python..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python trouvé : $pythonVersion"
} catch {
    Write-Error-Custom "Python n'est pas installé ou n'est pas dans le PATH"
    Write-Host "Installez Python depuis https://www.python.org/downloads/"
    exit 1
}

# Vérifier que le répertoire d'entrée existe
if (-Not (Test-Path $InputPath)) {
    Write-Error-Custom "Le répertoire d'entrée n'existe pas : $InputPath"
    Write-Host "Créez le répertoire ou spécifiez un autre chemin avec -InputPath"
    exit 1
}

$fileCount = (Get-ChildItem -Path $InputPath -Recurse -File | Measure-Object).Count
Write-Success "Répertoire d'entrée trouvé : $InputPath"
Write-Info "Fichiers trouvés : $fileCount"

# Vérifier le fichier .env
if (-Not (Test-Path ".env")) {
    Write-Info "Fichier .env non trouvé, création depuis .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Success "Fichier .env créé"
    Write-ColorOutput Yellow "IMPORTANT : Éditez le fichier .env avec vos clés API !"
    Write-Host ""
    Write-Host "Vous devez configurer :"
    Write-Host "  - OPENAI_API_KEY"
    Write-Host "  - SUPABASE_URL"
    Write-Host "  - SUPABASE_KEY"
    Write-Host "  - AZURE_FORM_RECOGNIZER_KEY (optionnel pour OCR)"
    Write-Host ""
    $response = Read-Host "Avez-vous configuré le fichier .env ? (o/n)"
    if ($response -ne "o" -and $response -ne "O") {
        Write-Error-Custom "Veuillez configurer .env avant de continuer"
        exit 1
    }
}

# ============================================================================
# ÉTAPE 2 : Installation des dépendances
# ============================================================================

if (-Not $SkipDependencyCheck) {
    Write-Header "INSTALLATION DES DÉPENDANCES"

    Write-Info "Vérification des packages Python..."

    $requiredPackages = @(
        "openai",
        "supabase",
        "python-dotenv",
        "tenacity",
        "PyPDF2",
        "azure-ai-formrecognizer"
    )

    $missingPackages = @()

    foreach ($package in $requiredPackages) {
        $installed = pip list 2>&1 | Select-String -Pattern "^$package\s"
        if (-Not $installed) {
            $missingPackages += $package
        }
    }

    if ($missingPackages.Count -gt 0) {
        Write-Info "Installation des packages manquants : $($missingPackages -join ', ')"
        pip install -q $missingPackages

        if ($LASTEXITCODE -eq 0) {
            Write-Success "Dépendances installées avec succès"
        } else {
            Write-Error-Custom "Erreur lors de l'installation des dépendances"
            Write-Host "Essayez : pip install -r requirements.txt"
            exit 1
        }
    } else {
        Write-Success "Toutes les dépendances sont déjà installées"
    }
} else {
    Write-Info "Vérification des dépendances ignorée (--SkipDependencyCheck)"
}

# ============================================================================
# ÉTAPE 3 : Configuration
# ============================================================================

Write-Header "CONFIGURATION"

Write-Info "Niveau de granularité : $GranularityLevel"
Write-Info "Workers parallèles : $Workers"
Write-Info "Répertoire d'entrée : $InputPath"
Write-Info "Upload Supabase : $(if ($NoUpload) { 'NON' } else { 'OUI' })"
Write-Info "Azure OCR : $(if ($NoOCR) { 'NON' } else { 'OUI' })"

# Afficher les détails de granularité
switch ($GranularityLevel) {
    "ULTRA_FINE" {
        Write-ColorOutput Cyan "  → 200 chars/chunk, 50 overlap (~60 chunks/10k caractères)"
        Write-ColorOutput Cyan "  → Précision MAXIMALE"
    }
    "FINE" {
        Write-ColorOutput Cyan "  → 400 chars/chunk, 100 overlap (~30 chunks/10k caractères)"
        Write-ColorOutput Cyan "  → Haute granularité (recommandé)"
    }
    "MEDIUM" {
        Write-ColorOutput Cyan "  → 600 chars/chunk, 150 overlap (~20 chunks/10k caractères)"
        Write-ColorOutput Cyan "  → Équilibre précision/coût"
    }
    "STANDARD" {
        Write-ColorOutput Cyan "  → 1000 chars/chunk, 200 overlap (~12 chunks/10k caractères)"
        Write-ColorOutput Cyan "  → Configuration standard"
    }
}

# ============================================================================
# ÉTAPE 4 : Confirmation
# ============================================================================

Write-Host ""
Write-ColorOutput Yellow "Prêt à traiter $fileCount fichiers"
Write-Host ""

$confirm = Read-Host "Continuer ? (o/n)"
if ($confirm -ne "o" -and $confirm -ne "O") {
    Write-Info "Opération annulée"
    exit 0
}

# ============================================================================
# ÉTAPE 5 : Lancement du traitement
# ============================================================================

Write-Header "TRAITEMENT EN COURS"

# Configurer la variable d'environnement
$env:GRANULARITY_LEVEL = $GranularityLevel

# Construire la commande
$command = "python process_v2.py --input `"$InputPath`" --workers $Workers"

if (-Not $NoUpload) {
    $command += " --upload"
}

if (-Not $NoOCR) {
    $command += " --use-ocr"
}

# Afficher la commande
Write-Info "Commande : $command"
Write-Host ""

# Créer le nom de fichier log
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "upload_$timestamp.log"

# Lancer le traitement
Write-ColorOutput Green "Démarrage du traitement..."
Write-Info "Logs sauvegardés dans : $logFile"
Write-Host ""

try {
    # Exécuter avec redirection vers fichier ET console
    Invoke-Expression $command 2>&1 | Tee-Object -FilePath $logFile

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Header "TRAITEMENT TERMINÉ AVEC SUCCÈS"
        Write-Success "Logs disponibles dans : $logFile"
    } else {
        Write-Host ""
        Write-Header "TRAITEMENT TERMINÉ AVEC ERREURS"
        Write-Error-Custom "Code de sortie : $LASTEXITCODE"
        Write-Info "Consultez le fichier log : $logFile"
        exit $LASTEXITCODE
    }
} catch {
    Write-Host ""
    Write-Error-Custom "Erreur lors du traitement : $_"
    exit 1
}

# ============================================================================
# ÉTAPE 6 : Résumé
# ============================================================================

Write-Host ""
Write-ColorOutput Cyan "═══════════════════════════════════════════════════════════════════════════"
Write-ColorOutput Cyan "  RÉSUMÉ"
Write-ColorOutput Cyan "═══════════════════════════════════════════════════════════════════════════"
Write-Host ""
Write-Host "✓ Fichiers traités depuis : $InputPath"
Write-Host "✓ Niveau de granularité : $GranularityLevel"
Write-Host "✓ Workers utilisés : $Workers"
Write-Host "✓ Log complet : $logFile"
Write-Host ""

if (-Not $NoUpload) {
    Write-ColorOutput Green "Vos documents sont maintenant disponibles dans Supabase !"
    Write-Host "Vous pouvez effectuer des recherches sémantiques ultra-précises."
}

Write-Host ""
