param(
    [string]$Seed = "22B AI",
    [int]$Length = 300
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $Root "src"

$ModelPath = Join-Path $Root "models\checkpoints\tiny_bigram_seed.json"
if (-not (Test-Path $ModelPath)) {
    & (Join-Path $PSScriptRoot "train_tiny_bigram.ps1")
}

python -m ai22b.from_scratch.bigram generate --model $ModelPath --seed $Seed --length $Length
