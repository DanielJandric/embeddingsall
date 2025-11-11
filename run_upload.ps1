# Minimal PowerShell script: upload from C:\OneDriveExport with 3 workers
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Run from this script's directory
Set-Location $PSScriptRoot

try {
  python upload_maximal.py -i "C:\OneDriveExport" --workers 3
} catch {
  py upload_maximal.py -i "C:\OneDriveExport" --workers 3
}


