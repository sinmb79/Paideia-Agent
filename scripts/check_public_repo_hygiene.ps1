$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    throw "git command not found. Install Git before preparing the public repository."
}

$candidateFiles = @(
    git ls-files --cached --others --exclude-standard
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique

$pathBlocklist = @(
    '^AGENTS\.md$',
    '^docs/log\.md$',
    '^data/private/',
    '^data/processed/',
    '^models/',
    '^runs/',
    '^apps/[^/]+/runs/',
    '(^|/)node_modules/',
    '(^|/)dist/',
    '(^|/)target/'
)

$privateUser = "sin" + "mb"
$contentPatterns = @(
    @{ Name = "local_username"; Pattern = [regex]::Escape($privateUser) },
    @{ Name = "local_windows_user_path"; Pattern = "C:[\\/]+Users[\\/]+" + [regex]::Escape($privateUser) },
    @{ Name = "openai_key_assignment"; Pattern = 'OPENAI_API_KEY\s*=\s*[''"]?[^''",\s]{8,}' },
    @{ Name = "generic_openai_secret"; Pattern = "sk-[A-Za-z0-9_-]{32,}" },
    @{ Name = "github_pat"; Pattern = "gh[pousr]_[A-Za-z0-9_]{20,}" },
    @{ Name = "private_key"; Pattern = "BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY" },
    @{ Name = "refresh_token"; Pattern = "refresh_token\s*[:=]" },
    @{ Name = "auth_token"; Pattern = "auth_token\s*[:=]" }
)

$issues = New-Object System.Collections.Generic.List[object]

foreach ($file in $candidateFiles) {
    $normalized = $file -replace '\\', '/'
    if ($normalized -match '/\.gitkeep$' -or $normalized -eq 'runs/.gitkeep') {
        continue
    }
    foreach ($pattern in $pathBlocklist) {
        if ($normalized -match $pattern) {
            $issues.Add([pscustomobject]@{
                type = "blocked_path"
                file = $file
                rule = $pattern
            })
        }
    }

    $fullPath = Join-Path $Root $file
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        continue
    }

    try {
        $text = Get-Content -LiteralPath $fullPath -Raw -Encoding UTF8
    } catch {
        continue
    }

    foreach ($item in $contentPatterns) {
        if ($text -match $item.Pattern) {
            $issues.Add([pscustomobject]@{
                type = "blocked_content"
                file = $file
                rule = $item.Name
            })
        }
    }
}

$issueArray = @($issues.ToArray())

$report = [ordered]@{
    schema = "ai22b-public-repo-hygiene/v1"
    checked_at = (Get-Date).ToUniversalTime().ToString("o")
    candidate_file_count = $candidateFiles.Count
    passed = ($issueArray.Count -eq 0)
    issues = $issueArray
    policy = [ordered]@{
        publish_mode = "selective_files_only"
        excluded_by_default = @(
            "AGENTS.md",
            "docs/log.md",
            "data/private",
            "data/processed",
            "models",
            "runs",
            "apps/*/runs",
            "local voice assets",
            "session logs",
            "environment files"
        )
    }
}

$outputDir = Join-Path $Root "runs"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$outputPath = Join-Path $outputDir "public_repo_hygiene_report.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding UTF8

if ($report["passed"]) {
    Write-Host "[OK] Public repository hygiene passed."
    Write-Host $outputPath
    exit 0
}

Write-Host "[FAIL] Public repository hygiene found blocked files or content."
$report.issues | Format-Table -AutoSize
Write-Host $outputPath
exit 1
