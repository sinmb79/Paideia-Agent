$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"

if (-not (Test-Path $Venv)) {
    python -m venv $Venv
}

& (Join-Path $Venv "Scripts\python.exe") -m pip install --upgrade pip
& (Join-Path $Venv "Scripts\python.exe") -m pip install -e $Root

Write-Host "Virtual environment ready: $Venv"
Write-Host "For optional AI lab packages, review requirements-lab.txt first."
