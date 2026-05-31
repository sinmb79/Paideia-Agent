$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $Root "src"

python -m unittest discover -s (Join-Path $Root "tests") -p "test_*.py"
