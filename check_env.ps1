# ============================================================================
# Script de Vérification de l'Environnement
# ============================================================================
# Vérifie que tout est configuré correctement avant de lancer le traitement
# ============================================================================

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Test-Component {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$ErrorMessage = "",
        [string]$SuccessMessage = ""
    )

    Write-Host -NoNewline "$Name... "

    try {
        $result = & $Test
        if ($result) {
            Write-ColorOutput Green "[✓] $SuccessMessage"
            return $true
        } else {
            Write-ColorOutput Red "[✗] $ErrorMessage"
            return $false
        }
    } catch {
        Write-ColorOutput Red "[✗] $ErrorMessage : $_"
        return $false
    }
}

Write-Host ""
Write-ColorOutput Yellow ("=" * 80)
Write-ColorOutput Yellow "  VÉRIFICATION DE L'ENVIRONNEMENT"
Write-ColorOutput Yellow ("=" * 80)
Write-Host ""

$allOk = $true

# Python
$pythonOk = Test-Component `
    -Name "Python" `
    -Test { python --version 2>&1; $LASTEXITCODE -eq 0 } `
    -ErrorMessage "Python n'est pas installé" `
    -SuccessMessage ((python --version 2>&1) -replace "Python ", "Version ")

$allOk = $allOk -and $pythonOk

# pip
$pipOk = Test-Component `
    -Name "pip" `
    -Test { pip --version 2>&1; $LASTEXITCODE -eq 0 } `
    -ErrorMessage "pip n'est pas installé" `
    -SuccessMessage "Installé"

$allOk = $allOk -and $pipOk

# Fichier .env
$envOk = Test-Component `
    -Name "Fichier .env" `
    -Test { Test-Path ".env" } `
    -ErrorMessage "Fichier .env manquant" `
    -SuccessMessage "Trouvé"

$allOk = $allOk -and $envOk

if ($envOk) {
    # Vérifier les variables critiques dans .env
    $envContent = Get-Content ".env" -Raw

    $openaiOk = Test-Component `
        -Name "  OPENAI_API_KEY" `
        -Test { $envContent -match "OPENAI_API_KEY=sk-" } `
        -ErrorMessage "Non configuré" `
        -SuccessMessage "Configuré"

    $supabaseUrlOk = Test-Component `
        -Name "  SUPABASE_URL" `
        -Test { $envContent -match "SUPABASE_URL=https://" } `
        -ErrorMessage "Non configuré" `
        -SuccessMessage "Configuré"

    $supabaseKeyOk = Test-Component `
        -Name "  SUPABASE_KEY" `
        -Test { $envContent -match "SUPABASE_KEY=\w{100,}" } `
        -ErrorMessage "Non configuré" `
        -SuccessMessage "Configuré"

    $granularityOk = Test-Component `
        -Name "  GRANULARITY_LEVEL" `
        -Test { $envContent -match "GRANULARITY_LEVEL=(ULTRA_FINE|FINE|MEDIUM|STANDARD|COARSE)" } `
        -ErrorMessage "Non configuré" `
        -SuccessMessage (($envContent | Select-String "GRANULARITY_LEVEL=(\w+)").Matches.Groups[1].Value)

    $allOk = $allOk -and $openaiOk -and $supabaseUrlOk -and $supabaseKeyOk
}

# Dépendances Python
Write-Host ""
Write-ColorOutput Cyan "Dépendances Python :"

$packages = @{
    "openai" = "OpenAI API"
    "supabase" = "Supabase Client"
    "python-dotenv" = "Dotenv"
    "tenacity" = "Tenacity"
    "PyPDF2" = "PyPDF2"
    "azure-ai-formrecognizer" = "Azure Form Recognizer"
}

$installedPackages = pip list 2>&1 | Out-String

foreach ($package in $packages.Keys) {
    $description = $packages[$package]
    $packageOk = Test-Component `
        -Name "  $description" `
        -Test { $installedPackages -match "^$package\s" } `
        -ErrorMessage "Non installé" `
        -SuccessMessage "Installé"

    if (-Not $packageOk) {
        $allOk = $false
    }
}

# Scripts
Write-Host ""
Write-ColorOutput Cyan "Scripts disponibles :"

$scriptOk = Test-Component `
    -Name "  process_v2.py" `
    -Test { Test-Path "process_v2.py" } `
    -ErrorMessage "Manquant" `
    -SuccessMessage "Disponible"

$allOk = $allOk -and $scriptOk

$configOk = Test-Component `
    -Name "  src/chunking_config.py" `
    -Test { Test-Path "src/chunking_config.py" } `
    -ErrorMessage "Manquant" `
    -SuccessMessage "Disponible"

$allOk = $allOk -and $configOk

# Résumé
Write-Host ""
Write-ColorOutput Yellow ("=" * 80)

if ($allOk) {
    Write-ColorOutput Green "  ✓ ENVIRONNEMENT PRÊT !"
    Write-ColorOutput Yellow ("=" * 80)
    Write-Host ""
    Write-ColorOutput Green "Vous pouvez lancer le traitement avec :"
    Write-Host "  .\run_upload.ps1"
    Write-Host ""
} else {
    Write-ColorOutput Red "  ✗ ENVIRONNEMENT INCOMPLET"
    Write-ColorOutput Yellow ("=" * 80)
    Write-Host ""
    Write-ColorOutput Red "Veuillez corriger les erreurs ci-dessus avant de continuer."
    Write-Host ""
    Write-Host "Actions recommandées :"
    Write-Host ""

    if (-Not $pythonOk) {
        Write-Host "  1. Installez Python depuis https://www.python.org/downloads/"
    }

    if (-Not $envOk) {
        Write-Host "  2. Copiez .env.example vers .env : Copy-Item .env.example .env"
    }

    if ($envOk -and (-Not $openaiOk -or -Not $supabaseUrlOk -or -Not $supabaseKeyOk)) {
        Write-Host "  3. Éditez .env et configurez vos clés API"
    }

    $missingPackages = @()
    foreach ($package in $packages.Keys) {
        if (-Not ($installedPackages -match "^$package\s")) {
            $missingPackages += $package
        }
    }

    if ($missingPackages.Count -gt 0) {
        Write-Host "  4. Installez les dépendances : pip install -r requirements.txt"
        Write-Host "     Ou : pip install $($missingPackages -join ' ')"
    }

    Write-Host ""
    exit 1
}
