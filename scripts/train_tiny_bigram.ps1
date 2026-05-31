$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $Root "src"

$InputPath = Join-Path $Root "corpus\seed_ko.txt"
$OutputPath = Join-Path $Root "models\checkpoints\tiny_bigram_seed.json"

python -m ai22b.from_scratch.bigram train --input $InputPath --output $OutputPath
