$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    throw "git command not found. Install Git before preparing the public repository."
}

$candidateFiles = @(
    git -c core.quotePath=false ls-files --cached --others --exclude-standard
) | ForEach-Object {
    ([string]$_).Trim('"')
} | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique

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
$placeholderUserSegments = "(?:<[^\\/]+>|your[-_ ]?(?:user|name)|user|username|example|sample|placeholder)"
$realWindowsUserHomePattern = "C:[\\/]+Users[\\/]+(?!" + $placeholderUserSegments + "(?:[\\/]|$))[^\\/`"'<>\s]+"
$realPosixUserHomePattern = "(?:^|[\s=:`"'])(?:[\\/]Users|[\\/]home)[\\/]+(?!" + $placeholderUserSegments + "(?:[\\/]|$))[^\\/`"'<>\s]+"
$providerSecretKeys = @(
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_OPENAI_API_KEY"
)
$providerSecretPattern = "\b(" + (($providerSecretKeys | ForEach-Object { [regex]::Escape($_) }) -join "|") + ")\b\s*[:=]\s*['""]?(?!(?:<|\$\{|your|example|sample|placeholder|changeme|replace_me|test_|fixture_))[^'"",\s]{12,}"
$hiddenUnicodeBidiChars = -join @(
    [char]0x202A,
    [char]0x202B,
    [char]0x202C,
    [char]0x202D,
    [char]0x202E,
    [char]0x2066,
    [char]0x2067,
    [char]0x2068,
    [char]0x2069
)
$hiddenUnicodeBidiPattern = "[" + [regex]::Escape($hiddenUnicodeBidiChars) + "]"
$contentPatterns = @(
    @{ Name = "local_windows_user_path"; Pattern = "C:[\\/]+Users[\\/]+" + [regex]::Escape($privateUser) },
    @{ Name = "local_posix_user_path"; Pattern = "[\\/]Users[\\/]+" + [regex]::Escape($privateUser) },
    @{ Name = "generic_local_windows_user_path"; Pattern = $realWindowsUserHomePattern },
    @{ Name = "generic_local_posix_user_path"; Pattern = $realPosixUserHomePattern },
    @{ Name = "openai_key_assignment"; Pattern = 'OPENAI_API_KEY\s*=\s*[''"]?[^''",\s]{8,}' },
    @{ Name = "provider_secret_assignment"; Pattern = $providerSecretPattern },
    @{ Name = "generic_openai_secret"; Pattern = "sk-[A-Za-z0-9_-]{32,}" },
    @{ Name = "github_pat"; Pattern = "gh[pousr]_[A-Za-z0-9_]{20,}" },
    @{ Name = "private_key"; Pattern = "BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY" },
    @{ Name = "refresh_token"; Pattern = "refresh_token\s*[:=]" },
    @{ Name = "auth_token"; Pattern = "auth_token\s*[:=]" },
    @{ Name = "hidden_unicode_bidi_control"; Pattern = $hiddenUnicodeBidiPattern }
)

$issues = New-Object System.Collections.Generic.List[object]

$requiredReleaseFiles = @(
    "README.md",
    "README.ko.md",
    "ROADMAP.md",
    "ROADMAP.ko.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.ko.md",
    "SECURITY.md",
    "LICENSE",
    "pyproject.toml",
    ".github/dependabot.yml",
    "docs/security_threat_model.md",
    "docs/security_threat_model.ko.md",
    "schemas/README.md",
    "schemas/first_run_doctor.v1.schema.json",
    "schemas/llm_client_result.v1.schema.json",
    "schemas/tool_execution_artifact_manifest.v1.schema.json",
    "schemas/reasoning_ledger_candidate.v1.schema.json",
    "schemas/hiring_dossier.v1.schema.json"
)

foreach ($requiredFile in $requiredReleaseFiles) {
    $requiredPath = Join-Path $Root $requiredFile
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        $issues.Add([pscustomobject]@{
            type = "missing_required_release_file"
            file = $requiredFile
            rule = "public_release_required_file"
        })
    }
}

$pyprojectPath = Join-Path $Root "pyproject.toml"
if (Test-Path -LiteralPath $pyprojectPath -PathType Leaf) {
    $pyprojectText = Get-Content -LiteralPath $pyprojectPath -Raw -Encoding UTF8
    if ($pyprojectText -notmatch 'license\s*=\s*\{\s*file\s*=\s*"LICENSE"\s*\}') {
        $issues.Add([pscustomobject]@{
            type = "missing_package_license_metadata"
            file = "pyproject.toml"
            rule = "project_license_file_must_reference_LICENSE"
        })
    }
}

foreach ($file in $candidateFiles) {
    $normalized = $file -replace '\\', '/'
    if (
        $normalized -match '/\.gitkeep$' `
        -or $normalized -eq 'runs/.gitkeep' `
        -or $normalized -eq 'runs/public_repo_hygiene_report.json'
    ) {
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
        hidden_unicode_policy = "Reject U+202A..U+202E and U+2066..U+2069 bidirectional controls in public text files"
        required_release_files = $requiredReleaseFiles
        package_license_metadata = "pyproject.toml must reference LICENSE"
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
