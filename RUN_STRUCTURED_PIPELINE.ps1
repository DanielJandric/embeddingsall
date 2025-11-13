<# 
    RUN_STRUCTURED_PIPELINE.ps1
    ----------------------------
    Orchestrates the post-import structuration and insight jobs in sequence.

    Usage:
        .\RUN_STRUCTURED_PIPELINE.ps1                # use default python (python)
        .\RUN_STRUCTURED_PIPELINE.ps1 -PythonExe py  # use py launcher alias

    The script:
        1. Builds structured entities/mentions from enrichments.
        2. Aggregates property & stakeholder insights (phase 2).
        3. Infers document-to-document relationships.
        4. Infers entity-to-entity relationships.

    Each step logs to its respective file and stops on error.
#>

param(
    [string]$PythonExe = "python",
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [string]$Title,
        [string]$Command,
        [string]$Arguments
    )

    Write-Host ""
    Write-Host ("=" * 80)
    Write-Host ("[STEP] {0}" -f $Title)
    Write-Host ("=" * 80)
    Write-Host ("Command: {0} {1}" -f $Command, $Arguments)

    & $Command $Arguments.Split(" ") 2>&1 | Tee-Object -Variable output

    if ($LASTEXITCODE -ne 0) {
        Write-Error ("[ERROR] Step '{0}' failed." -f $Title)
        throw "Pipeline aborted."
    }

    Write-Host ("[OK] {0}" -f $Title)
}

try {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptRoot

    $pythonPath = Get-Command $PythonExe -ErrorAction Stop | Select-Object -ExpandProperty Source
    Write-Host "[INFO] Using Python at $pythonPath"

    $dryFlag = ""
    if ($DryRun.IsPresent) {
        $dryFlag = "--dry-run"
        Write-Host "[INFO] Dry-run mode enabled (no Supabase writes)."
    }

    Invoke-Step -Title "Structured entities & mentions" `
        -Command $PythonExe `
        -Arguments ("build_structured_insights.py --batch-size 1000 {0}" -f $dryFlag).Trim()

    $phase2Args = "--batch-size 1000"
    if (-not $DryRun.IsPresent) {
        $phase2Args += " --upsert"
    } else {
        $phase2Args += " --dry-run"
    }
    Invoke-Step -Title "Property & stakeholder insights (phase 2)" `
        -Command $PythonExe `
        -Arguments ("improvement_phase2.py {0}" -f $phase2Args)

    $docRelArgs = ""
    if (-not $DryRun.IsPresent) {
        $docRelArgs = "--upsert"
    }
    Invoke-Step -Title "Document relationship builder (job #3)" `
        -Command $PythonExe `
        -Arguments ("build_document_relationships.py {0}" -f $docRelArgs).Trim()

    $entityRelArgs = ""
    if (-not $DryRun.IsPresent) {
        $entityRelArgs = "--upsert"
    }
    Invoke-Step -Title "Entity relationship builder (job #4)" `
        -Command $PythonExe `
        -Arguments ("build_entity_relationships.py {0}" -f $entityRelArgs).Trim()

    Write-Host ""
    Write-Host "[DONE] Structured pipeline completed successfully."
}
catch {
    Write-Error $_
    exit 1
}

