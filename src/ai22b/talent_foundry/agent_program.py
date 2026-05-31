from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.memory_substrate import build_memory_substrate, run_chat_turn_from_employment, write_memory_substrate
from ai22b.talent_foundry.onboarding_choices import (
    CHAT_SURFACE_CATALOG,
    DEFAULT_CHAT_SURFACE_ID,
    LLM_SERVICE_CATALOG,
    resolve_chat_surface,
    resolve_llm_service,
)
from ai22b.talent_foundry.openclaw_onboarding_menu import build_openclaw_onboarding_menu
from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model


AGENT_PROGRAM_SCHEMA = "ai22b-paideia-agent-program/v1"
INSTALL_KIT_SCHEMA = "ai22b-paideia-agent-install-kit/v1"
PROGRAM_DOCTOR_SCHEMA = "ai22b-paideia-agent-program-doctor/v1"
DEFAULT_AGENT_PROGRAM_NAME = "Paideia Agent"
DEFAULT_AGENT_PROGRAM_NAME_KO = "Paideia Agent"
DEFAULT_AGENT_PROGRAM_FILE = "22b_paideia_agent_program.json"
DEFAULT_RUNTIME_HELPER_SCRIPT = "paideia_runtime.ps1"
DEFAULT_INSTALL_RUNTIME_SCRIPT = "install_paideia_runtime.ps1"
DEFAULT_RUNTIME_CONFIG_FILE = "paideia_runtime.local.json"
DEFAULT_CHAT_SCRIPT = "start_paideia_chat.ps1"
DEFAULT_OPENCLAW_MENU_SCRIPT = "refresh_openclaw_onboarding_menu.ps1"
DEFAULT_OPENCLAW_MENU_FILE = "openclaw_onboarding_menu.json"
DEFAULT_OPENCLAW_MENU_MARKDOWN = "OPENCLAW_ONBOARDING_MENU.md"
DEFAULT_OPENCLAW_RUNTIME_SCRIPT = "build_openclaw_runtime_bundle.ps1"
DEFAULT_OPENCLAW_NATIVE_ONBOARDING_SCRIPT = "build_openclaw_native_onboarding_runbook.ps1"
DEFAULT_OPENCLAW_INSTALLED_DOCTOR_SCRIPT = "doctor_openclaw_installed_runtime.ps1"
DEFAULT_OPENCLAW_SMOKE_PLAN_SCRIPT = "build_openclaw_live_smoke_plan.ps1"
DEFAULT_OPENCLAW_SMOKE_SEQUENCE_SCRIPT = "run_openclaw_smoke_sequence.ps1"
DEFAULT_OPENCLAW_WEBCHAT_SCRIPT = "start_openclaw_webchat.ps1"
DEFAULT_ONBOARDING_TEMPLATE = "paideia_onboarding.template.json"
DEFAULT_INSTALL_MANIFEST = "paideia_agent_install_manifest.json"
DEFAULT_DOCTOR_SCRIPT = "doctor_paideia.ps1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _maybe_file(path: Path) -> str | None:
    return path.name if path.exists() else None


def _first_matching_name(root: Path, pattern: str) -> str | None:
    matches = sorted(root.glob(pattern))
    return matches[0].name if matches else None


def _runtime_helper_script() -> str:
    return """$ErrorActionPreference = "Stop"

function Add-PaideiaSourcePath {
    param([string]$SourceRepo)
    if ([string]::IsNullOrWhiteSpace($SourceRepo)) { return $false }
    $Repo = Resolve-Path -LiteralPath $SourceRepo -ErrorAction SilentlyContinue
    if ($null -eq $Repo) { return $false }
    $Src = Join-Path $Repo.Path "src"
    $Cli = Join-Path $Src "ai22b\\talent_foundry\\cli.py"
    if (-not (Test-Path -LiteralPath $Cli)) { return $false }
    $Parts = @($Src)
    if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)) { $Parts += $env:PYTHONPATH }
    $env:PYTHONPATH = ($Parts -join [System.IO.Path]::PathSeparator)
    return $true
}

function Test-PaideiaImport {
    param([string]$PythonExe = "python")
    $PreviousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $PythonExe -c "import ai22b.talent_foundry.cli" 1>$null 2>$null
        $ExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreviousPreference
    }
    return ($ExitCode -eq 0)
}

function Resolve-PaideiaPython {
    param(
        [string]$PythonExe = "",
        [switch]$Quiet
    )
    if ([string]::IsNullOrWhiteSpace($PythonExe)) {
        $PythonExe = if (-not [string]::IsNullOrWhiteSpace($env:PAIDEIA_AGENT_PYTHON)) { $env:PAIDEIA_AGENT_PYTHON } else { "python" }
    }
    if (Test-PaideiaImport -PythonExe $PythonExe) { return $PythonExe }

    $BundleRoot = $PSScriptRoot
    $ConfigPath = Join-Path $BundleRoot "paideia_runtime.local.json"
    if (Test-Path -LiteralPath $ConfigPath) {
        $Config = Get-Content -Path $ConfigPath -Encoding UTF8 -Raw | ConvertFrom-Json
        if (-not [string]::IsNullOrWhiteSpace($Config.python)) { $PythonExe = [string]$Config.python }
        if (-not [string]::IsNullOrWhiteSpace($Config.source_repo)) {
            [void](Add-PaideiaSourcePath -SourceRepo ([string]$Config.source_repo))
            if (Test-PaideiaImport -PythonExe $PythonExe) { return $PythonExe }
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($env:PAIDEIA_AGENT_SOURCE)) {
        [void](Add-PaideiaSourcePath -SourceRepo $env:PAIDEIA_AGENT_SOURCE)
        if (Test-PaideiaImport -PythonExe $PythonExe) { return $PythonExe }
    }

    $Candidates = @(
        (Join-Path $BundleRoot "Paideia-Agent"),
        (Join-Path $BundleRoot "..\\Paideia-Agent"),
        (Join-Path $BundleRoot "..\\..\\Paideia-Agent"),
        (Join-Path $BundleRoot ".."),
        (Join-Path $BundleRoot "..\\..")
    )
    foreach ($Candidate in $Candidates) {
        if (Add-PaideiaSourcePath -SourceRepo $Candidate) {
            if (Test-PaideiaImport -PythonExe $PythonExe) { return $PythonExe }
        }
    }

    $Message = @"
Paideia Agent Python runtime was not found.

Run one of these once from this kit folder:
  powershell -ExecutionPolicy Bypass -File .\\install_paideia_runtime.ps1 -SourceRepo "C:\\path\\to\\Paideia-Agent"
  powershell -ExecutionPolicy Bypass -File .\\install_paideia_runtime.ps1 -InstallFromGit

No provider keys, bot tokens, chat logs, or private training data are written by the installer.
"@
    throw $Message
}
"""


def _install_runtime_script() -> str:
    return """param(
    [string]$SourceRepo = "",
    [string]$Python = "python",
    [switch]$InstallFromGit,
    [string]$GitUrl = "https://github.com/OWNER/Paideia-Agent.git"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeHelper = Join-Path $BundleRoot "paideia_runtime.ps1"
if (-not (Test-Path -LiteralPath $RuntimeHelper)) {
    throw "paideia_runtime.ps1 is missing from this kit."
}
. $RuntimeHelper

$ConfigPath = Join-Path $BundleRoot "paideia_runtime.local.json"
if (-not [string]::IsNullOrWhiteSpace($SourceRepo)) {
    $Repo = Resolve-Path -LiteralPath $SourceRepo -ErrorAction Stop
    if (-not (Add-PaideiaSourcePath -SourceRepo $Repo.Path)) {
        throw "SourceRepo must point to a Paideia-Agent repository with src\\ai22b\\talent_foundry\\cli.py."
    }
    $Config = [ordered]@{
        schema = "ai22b-paideia-runtime-local-config/v1"
        mode = "source_repo"
        python = $Python
        source_repo = $Repo.Path
        secret_values_stored = $false
        note = "Local path only. Do not publish this generated file."
    }
    $Config | ConvertTo-Json -Depth 4 | Set-Content -Path $ConfigPath -Encoding UTF8
    [void](Resolve-PaideiaPython -PythonExe $Python)
    Write-Host "Paideia runtime registered from source repo: $($Repo.Path)"
    Write-Host $ConfigPath
    exit 0
}

if ($InstallFromGit) {
    if ($GitUrl -match "/OWNER/") {
        throw "Pass -GitUrl with the public Paideia-Agent repository URL before using -InstallFromGit."
    }
    & $Python -m pip install --upgrade "git+$GitUrl"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $Config = [ordered]@{
        schema = "ai22b-paideia-runtime-local-config/v1"
        mode = "python_package"
        python = $Python
        source_repo = $null
        package_source = $GitUrl
        secret_values_stored = $false
    }
    $Config | ConvertTo-Json -Depth 4 | Set-Content -Path $ConfigPath -Encoding UTF8
    [void](Resolve-PaideiaPython -PythonExe $Python)
    Write-Host "Paideia runtime installed from Git: $GitUrl"
    Write-Host $ConfigPath
    exit 0
}

[void](Resolve-PaideiaPython -PythonExe $Python)
$Config = [ordered]@{
    schema = "ai22b-paideia-runtime-local-config/v1"
    mode = "existing_python_environment"
    python = $Python
    source_repo = $null
    secret_values_stored = $false
}
$Config | ConvertTo-Json -Depth 4 | Set-Content -Path $ConfigPath -Encoding UTF8
Write-Host "Paideia runtime already available in Python environment."
Write-Host $ConfigPath
"""


def _legacy_chat_script_mojibake() -> str:
    return """param(
    [string]$Program = ".\\22b_paideia_agent_program.json",
    [ValidateSet("offline", "auto", "live")]
    [string]$LlmMode = "offline",
    [string]$LlmModel = "",
    [switch]$LiveLlm,
    [switch]$LearnFromChat
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

Write-Host "Paideia Agent - Codex bridge chat"
Write-Host "종료하려면 exit 또는 quit 를 입력하세요."
Write-Host "Codex가 로컬 교육기록, Reasoning Ledger(Ariadne Thread), 대화기록을 읽고, 연결된 LLM은 언어/추론 엔진으로만 사용됩니다."
Write-Host ""

while ($true) {
    $Message = Read-Host "보스"
    if ($null -eq $Message) { continue }
    $Trimmed = $Message.Trim()
    if ($Trimmed -in @("exit", "quit")) { break }
    if ([string]::IsNullOrWhiteSpace($Trimmed)) { continue }
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $Output = "paideia_chat_$Stamp.json"
    $ArgsList = @(
        "-m", "ai22b.talent_foundry.cli",
        "run-agent-program-chat",
        "--program", $Program,
        "--message", $Trimmed,
        "--output", $Output,
        "--llm-mode", $LlmMode
    )
    if ($LiveLlm) { $ArgsList += "--live-llm" }
    if (-not [string]::IsNullOrWhiteSpace($LlmModel)) { $ArgsList += @("--llm-model", $LlmModel) }
    if ($LearnFromChat) { $ArgsList += "--learn-from-chat" }

    & $PaideiaPython @ArgsList | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "실행 중 오류가 발생했습니다." -ForegroundColor Red
        continue
    }
    $Chat = Get-Content -Path $Output -Encoding UTF8 -Raw | ConvertFrom-Json
    Write-Host ""
    Write-Host $Chat.assistant_reply
    Write-Host ""
    Write-Host "[program] $($Chat.agent_program.name)"
    Write-Host "[mode] $($Chat.reply_generation_mode)"
    Write-Host "[operator] $($Chat.active_operator)"
    Write-Host "[saved] $Output"
    Write-Host ""
}
"""


def _chat_script() -> str:
    return """param(
    [string]$Program = ".\\22b_paideia_agent_program.json",
    [ValidateSet("offline", "auto", "live")]
    [string]$LlmMode = "offline",
    [string]$LlmModel = "",
    [switch]$LiveLlm,
    [switch]$LearnFromChat
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

Write-Host "Paideia Agent - Codex bridge chat"
Write-Host "Type exit or quit to stop."
Write-Host "Codex reads the local education record, Reasoning Ledger (Ariadne Thread), and memory substrate."
Write-Host "The connected LLM is used as the language/reasoning engine only."
Write-Host ""

while ($true) {
    $Message = Read-Host "Boss"
    if ($null -eq $Message) { continue }
    $Trimmed = $Message.Trim()
    if ($Trimmed -in @("exit", "quit")) { break }
    if ([string]::IsNullOrWhiteSpace($Trimmed)) { continue }
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $Output = "paideia_chat_$Stamp.json"
    $ArgsList = @(
        "-m", "ai22b.talent_foundry.cli",
        "run-agent-program-chat",
        "--program", $Program,
        "--message", $Trimmed,
        "--output", $Output,
        "--llm-mode", $LlmMode
    )
    if ($LiveLlm) { $ArgsList += "--live-llm" }
    if (-not [string]::IsNullOrWhiteSpace($LlmModel)) { $ArgsList += @("--llm-model", $LlmModel) }
    if ($LearnFromChat) { $ArgsList += "--learn-from-chat" }

    & $PaideiaPython @ArgsList | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "An execution error occurred." -ForegroundColor Red
        continue
    }
    $Chat = Get-Content -Path $Output -Encoding UTF8 -Raw | ConvertFrom-Json
    Write-Host ""
    Write-Host $Chat.assistant_reply
    Write-Host ""
    Write-Host "[program] $($Chat.agent_program.name)"
    Write-Host "[mode] $($Chat.reply_generation_mode)"
    Write-Host "[operator] $($Chat.active_operator)"
    Write-Host "[saved] $Output"
    Write-Host ""
}
"""


def _openclaw_runtime_bundle_script() -> str:
    return """param(
    [string]$EmploymentRecord = ".\\employment_record.json",
    [string]$OutputDir = ".\\openclaw_runtime_bundle",
    [string[]]$Channel = @("webchat")
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

$ArgsList = @(
    "-m", "ai22b.talent_foundry.cli",
    "build-openclaw-runtime-bundle",
    "--employment-record", $EmploymentRecord,
    "--output-dir", $OutputDir
)
foreach ($Item in $Channel) {
    if (-not [string]::IsNullOrWhiteSpace($Item)) {
        $ArgsList += @("--channel", $Item)
    }
}

& $PaideiaPython @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OpenClaw runtime bundle: $OutputDir\\openclaw_runtime_bundle.json"
"""


def _openclaw_native_onboarding_runbook_script() -> str:
    return """param(
    [string]$EmploymentRecord = ".\\employment_record.json",
    [string]$RuntimeBundle = ".\\openclaw_runtime_bundle\\openclaw_runtime_bundle.json",
    [string[]]$Channel = @("webchat"),
    [string]$Output = ".\\OPENCLAW_NATIVE_ONBOARDING_RUNBOOK.json",
    [string]$MarkdownOutput = ".\\OPENCLAW_NATIVE_ONBOARDING_RUNBOOK.md"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

if (-not (Test-Path -LiteralPath $RuntimeBundle)) {
    $BundleDir = Split-Path -Parent $RuntimeBundle
    if ([string]::IsNullOrWhiteSpace($BundleDir)) { $BundleDir = "." }
    $RuntimeArgs = @(
        "-m", "ai22b.talent_foundry.cli",
        "build-openclaw-runtime-bundle",
        "--employment-record", $EmploymentRecord,
        "--output-dir", $BundleDir
    )
    foreach ($Item in $Channel) {
        if (-not [string]::IsNullOrWhiteSpace($Item)) {
            $RuntimeArgs += @("--channel", $Item)
        }
    }
    & $PaideiaPython @RuntimeArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$ArgsList = @(
    "-m", "ai22b.talent_foundry.cli",
    "build-openclaw-native-onboarding-runbook",
    "--runtime-bundle", $RuntimeBundle,
    "--output", $Output,
    "--markdown-output", $MarkdownOutput
)

& $PaideiaPython @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OpenClaw native onboarding runbook: $Output"
Write-Host "Markdown guide: $MarkdownOutput"
"""


def _openclaw_installed_runtime_doctor_script() -> str:
    return """param(
    [string]$Output = ".\\openclaw_installed_runtime_doctor.json",
    [switch]$ProbeGateway
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

$ArgsList = @(
    "-m", "ai22b.talent_foundry.cli",
    "doctor-openclaw-installed-runtime",
    "--output", $Output
)
if ($ProbeGateway) { $ArgsList += "--probe-gateway" }

& $PaideiaPython @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OpenClaw installed runtime doctor: $Output"
"""


def _openclaw_onboarding_menu_script() -> str:
    return """param(
    [string]$Output = ".\\openclaw_onboarding_menu.json",
    [string]$MarkdownOutput = ".\\OPENCLAW_ONBOARDING_MENU.md",
    [switch]$RefreshDocs
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

$ArgsList = @(
    "-m", "ai22b.talent_foundry.cli",
    "build-openclaw-onboarding-menu",
    "--output", $Output,
    "--markdown-output", $MarkdownOutput
)
if ($RefreshDocs) { $ArgsList += "--refresh-docs" }

& $PaideiaPython @ArgsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OpenClaw onboarding menu: $Output"
Write-Host "Markdown guide: $MarkdownOutput"
"""


def _openclaw_live_smoke_plan_script() -> str:
    return """param(
    [string]$EmploymentRecord = ".\\employment_record.json",
    [string]$RuntimeBundle = ".\\openclaw_runtime_bundle\\openclaw_runtime_bundle.json",
    [string[]]$Channel = @("webchat"),
    [string]$Output = ".\\openclaw_live_smoke_plan.json",
    [string]$MarkdownOutput = ".\\OPENCLAW_LIVE_SMOKE_PLAN.md",
    [switch]$RefreshDocs
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

if (-not (Test-Path -LiteralPath $RuntimeBundle)) {
    $BundleDir = Split-Path -Parent $RuntimeBundle
    if ([string]::IsNullOrWhiteSpace($BundleDir)) { $BundleDir = "." }
    $RuntimeArgs = @(
        "-m", "ai22b.talent_foundry.cli",
        "build-openclaw-runtime-bundle",
        "--employment-record", $EmploymentRecord,
        "--output-dir", $BundleDir
    )
    foreach ($Item in $Channel) {
        if (-not [string]::IsNullOrWhiteSpace($Item)) {
            $RuntimeArgs += @("--channel", $Item)
        }
    }
    & $PaideiaPython @RuntimeArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$PlanArgs = @(
    "-m", "ai22b.talent_foundry.cli",
    "build-openclaw-live-smoke-plan",
    "--employment-record", $EmploymentRecord,
    "--runtime-bundle", $RuntimeBundle,
    "--output", $Output,
    "--markdown-output", $MarkdownOutput
)
foreach ($Item in $Channel) {
    if (-not [string]::IsNullOrWhiteSpace($Item)) {
        $PlanArgs += @("--channel", $Item)
    }
}
if ($RefreshDocs) { $PlanArgs += "--refresh-docs" }

& $PaideiaPython @PlanArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OpenClaw live smoke plan: $Output"
Write-Host "Markdown guide: $MarkdownOutput"
"""


def _openclaw_smoke_sequence_script() -> str:
    return """param(
    [string]$EmploymentRecord = ".\\employment_record.json",
    [string]$RuntimeBundle = ".\\openclaw_runtime_bundle\\openclaw_runtime_bundle.json",
    [string[]]$Channel = @("webchat"),
    [string]$OutputDir = ".\\openclaw_smoke_runs",
    [switch]$IncludeLive,
    [switch]$RefreshDocs
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

$OutputRoot = New-Item -ItemType Directory -Force -Path $OutputDir
$ReportPath = Join-Path $OutputRoot.FullName "openclaw_smoke_sequence_report.json"
$PlanPath = Join-Path $OutputRoot.FullName "openclaw_live_smoke_plan.json"
$PlanMarkdownPath = Join-Path $OutputRoot.FullName "OPENCLAW_LIVE_SMOKE_PLAN.md"
$PreflightPath = Join-Path $OutputRoot.FullName "openclaw_runtime_preflight.static.json"
$GatewayProbePath = Join-Path $OutputRoot.FullName "openclaw_gateway_llm.live.json"
$OpenClawCliProbePath = Join-Path $OutputRoot.FullName "openclaw_cli_agent.live.json"
$ChatOfflinePath = Join-Path $OutputRoot.FullName "chat_offline_smoke.json"
$ChatLivePath = Join-Path $OutputRoot.FullName "chat_live_smoke.json"
$ChannelOfflinePath = Join-Path $OutputRoot.FullName "channel_offline_smoke.json"
$ChannelLivePath = Join-Path $OutputRoot.FullName "channel_live_smoke.json"
$FirstChannel = ($Channel | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First 1)
if ([string]::IsNullOrWhiteSpace($FirstChannel)) { $FirstChannel = "webchat" }

$Steps = New-Object System.Collections.Generic.List[object]
$Failure = $null

function Add-ChannelArgs {
    param([object[]]$BaseArgs)
    $ArgsList = @($BaseArgs)
    foreach ($Item in $Channel) {
        if (-not [string]::IsNullOrWhiteSpace($Item)) {
            $ArgsList += @("--channel", $Item)
        }
    }
    return $ArgsList
}

function Add-StepRecord {
    param(
        [string]$Id,
        [string]$Status,
        [bool]$Live,
        [int]$ExitCode,
        [string]$Output,
        [string]$Command
    )
    $Steps.Add([ordered]@{
        id = $Id
        status = $Status
        live = $Live
        exit_code = $ExitCode
        output = $Output
        command = $Command
    }) | Out-Null
}

function Invoke-PaideiaStep {
    param(
        [string]$Id,
        [object[]]$ArgsList,
        [string]$Output,
        [switch]$Live
    )
    $CommandText = "$PaideiaPython " + (($ArgsList | ForEach-Object { [string]$_ }) -join " ")
    if ($Live -and -not $IncludeLive) {
        Add-StepRecord -Id $Id -Status "skipped_live_not_requested" -Live $true -ExitCode 0 -Output $Output -Command $CommandText
        Write-Host "[skip live] $Id"
        return
    }
    Write-Host "[run] $Id"
    & $PaideiaPython @ArgsList
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -eq 0) {
        Add-StepRecord -Id $Id -Status "passed" -Live ([bool]$Live) -ExitCode $ExitCode -Output $Output -Command $CommandText
        return
    }
    Add-StepRecord -Id $Id -Status "failed" -Live ([bool]$Live) -ExitCode $ExitCode -Output $Output -Command $CommandText
    throw "$Id failed with exit code $ExitCode"
}

try {
    $RuntimeBundleDir = Split-Path -Parent $RuntimeBundle
    if ([string]::IsNullOrWhiteSpace($RuntimeBundleDir)) { $RuntimeBundleDir = "." }
    Invoke-PaideiaStep -Id "build_runtime_bundle_if_missing" -Output $RuntimeBundle -ArgsList (Add-ChannelArgs @(
        "-m", "ai22b.talent_foundry.cli",
        "build-openclaw-runtime-bundle",
        "--employment-record", $EmploymentRecord,
        "--output-dir", $RuntimeBundleDir
    ))

    $SmokePlanArgs = Add-ChannelArgs @(
        "-m", "ai22b.talent_foundry.cli",
        "build-openclaw-live-smoke-plan",
        "--employment-record", $EmploymentRecord,
        "--runtime-bundle", $RuntimeBundle,
        "--output", $PlanPath,
        "--markdown-output", $PlanMarkdownPath
    )
    if ($RefreshDocs) { $SmokePlanArgs += "--refresh-docs" }
    Invoke-PaideiaStep -Id "build_live_smoke_plan" -Output $PlanPath -ArgsList $SmokePlanArgs
    $PlanJson = Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $UseOpenClawCli = (
        $PlanJson.selection.llm_engine -eq "openclaw_cli_local" -or
        $PlanJson.selection.api_protocol -eq "openclaw_cli_agent_local" -or
        $PlanJson.selection.live_runtime_path -eq "openclaw_cli_local"
    )

    Invoke-PaideiaStep -Id "offline_context_smoke" -Output $ChatOfflinePath -ArgsList @(
        "-m", "ai22b.talent_foundry.cli",
        "chat-hired-agent",
        "--employment-record", $EmploymentRecord,
        "--message", "OpenClaw offline context smoke test.",
        "--llm-mode", "offline",
        "--output", $ChatOfflinePath
    )

    Invoke-PaideiaStep -Id "static_preflight" -Output $PreflightPath -ArgsList @(
        "-m", "ai22b.talent_foundry.cli",
        "doctor-openclaw-runtime-preflight",
        "--runtime-bundle", $RuntimeBundle,
        "--run-channel-flow",
        "--output", $PreflightPath
    )

    Invoke-PaideiaStep -Id "offline_channel_message_smoke" -Output $ChannelOfflinePath -ArgsList @(
        "-m", "ai22b.talent_foundry.cli",
        "run-openclaw-channel-message",
        "--employment-record", $EmploymentRecord,
        "--channel", $FirstChannel,
        "--message", "OpenClaw channel offline smoke test.",
        "--llm-mode", "offline",
        "--output", $ChannelOfflinePath
    )

    if ($UseOpenClawCli) {
        Invoke-PaideiaStep -Id "openclaw_cli_live_probe" -Live -Output $OpenClawCliProbePath -ArgsList @(
            "-m", "ai22b.talent_foundry.cli",
            "chat-hired-agent",
            "--employment-record", $EmploymentRecord,
            "--message", "OpenClaw CLI local agent live smoke test.",
            "--llm-mode", "live",
            "--output", $OpenClawCliProbePath
        )
    } else {
        Add-StepRecord -Id "openclaw_cli_live_probe" -Status "skipped_not_openclaw_cli_runtime" -Live $true -ExitCode 0 -Output $OpenClawCliProbePath -Command "selected runtime is not openclaw_cli_local"
        Write-Host "[skip non-cli] openclaw_cli_live_probe"
    }

    Invoke-PaideiaStep -Id "gateway_live_probe" -Live -Output $GatewayProbePath -ArgsList @(
        "-m", "ai22b.talent_foundry.cli",
        "doctor-openclaw-gateway-llm",
        "--employment-record", $EmploymentRecord,
        "--runtime-bundle", $RuntimeBundle,
        "--probe-gateway",
        "--probe-chat",
        "--output", $GatewayProbePath
    )

    Invoke-PaideiaStep -Id "live_llm_chat_smoke" -Live -Output $ChatLivePath -ArgsList @(
        "-m", "ai22b.talent_foundry.cli",
        "chat-hired-agent",
        "--employment-record", $EmploymentRecord,
        "--message", "OpenClaw live LLM chat smoke test.",
        "--llm-mode", "live",
        "--output", $ChatLivePath
    )

    Invoke-PaideiaStep -Id "live_channel_message_smoke" -Live -Output $ChannelLivePath -ArgsList @(
        "-m", "ai22b.talent_foundry.cli",
        "run-openclaw-channel-message",
        "--employment-record", $EmploymentRecord,
        "--channel", $FirstChannel,
        "--message", "OpenClaw live channel message smoke test.",
        "--llm-mode", "live",
        "--output", $ChannelLivePath
    )
} catch {
    $Failure = $_.Exception.Message
} finally {
    $Report = [ordered]@{
        schema = "ai22b-paideia-openclaw-smoke-sequence-run/v1"
        created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        include_live = [bool]$IncludeLive
        status = if ($Failure) { "failed" } else { "passed" }
        failure = $Failure
        employment_record = $EmploymentRecord
        runtime_bundle = $RuntimeBundle
        output_dir = $OutputRoot.FullName
        first_channel = $FirstChannel
        secret_values_stored = $false
        external_network_requested = [bool]$IncludeLive
        steps = $Steps
        next_live_command = "powershell -ExecutionPolicy Bypass -File .\\run_openclaw_smoke_sequence.ps1 -IncludeLive"
    }
    $Report | ConvertTo-Json -Depth 8 | Set-Content -Path $ReportPath -Encoding UTF8
    Write-Host "OpenClaw smoke sequence report: $ReportPath"
}

if ($Failure) { throw $Failure }
"""


def _openclaw_webchat_script() -> str:
    return """param(
    [string]$EmploymentRecord = ".\\employment_record.json",
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8722,
    [string]$OutputDir = ".\\openclaw_webchat_runs",
    [ValidateSet("offline", "auto", "live")]
    [string]$LlmMode = "offline",
    [string]$LlmModel = "",
    [switch]$LiveLlm,
    [switch]$LearnFromChat
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}

if ($LiveLlm) { $LlmMode = "live" }

$ArgsList = @(
    "-m", "ai22b.talent_foundry.cli",
    "run-openclaw-webchat-server",
    "--employment-record", $EmploymentRecord,
    "--bind-host", $BindHost,
    "--port", [string]$Port,
    "--output-dir", $OutputDir,
    "--llm-mode", $LlmMode
)
if (-not [string]::IsNullOrWhiteSpace($LlmModel)) { $ArgsList += @("--llm-model", $LlmModel) }
if ($LearnFromChat) { $ArgsList += "--learn-from-chat" }

& $PaideiaPython @ArgsList
"""


def _doctor_script() -> str:
    return """param(
    [string]$Program = ".\\22b_paideia_agent_program.json",
    [string]$Output = ".\\paideia_doctor_report.json"
)

$ErrorActionPreference = "Stop"
$RuntimeHelper = Join-Path $PSScriptRoot "paideia_runtime.ps1"
if (Test-Path -LiteralPath $RuntimeHelper) {
    . $RuntimeHelper
    $PaideiaPython = Resolve-PaideiaPython
} else {
    $PaideiaPython = "python"
}
& $PaideiaPython -m ai22b.talent_foundry.cli doctor-agent-program --program $Program --output $Output
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host $Output
"""


def _onboarding_template(
    program_name: str,
    agent_name: str,
    *,
    selected_llm_service: dict[str, Any] | None = None,
    selected_chat_surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "ai22b-paideia-onboarding-template/v1",
        "program": program_name,
        "agent_name": agent_name,
        "flow": [
            "choose_llm_service",
            "choose_chat_surface",
            "confirm_or_select_role_model",
            "let_the_selected_llm_act_as_researcher",
            "raise_assess_and_review_hiring_dossier",
            "start_chat_or_dataflow_job",
        ],
        "openclaw_style_flow": [
            "detect_existing_config",
            "choose_quickstart_or_advanced",
            "choose_llm_service",
            "check_model_auth",
            "choose_workspace",
            "choose_gateway_and_channels",
            "choose_skill_import_policy",
            "choose_chat_surface",
            "choose_talent_source",
            "confirm_or_select_role_model",
            "let_the_selected_llm_act_as_researcher",
            "raise_assess_and_review_hiring_dossier",
            "prepare_agent_id_card_payload",
            "run_health_check",
            "start_chat_or_dataflow_job",
        ],
        "llm_service_catalog": LLM_SERVICE_CATALOG,
        "chat_surface_catalog": CHAT_SURFACE_CATALOG,
        "role_model_catalog": [summarize_role_model(item) for item in list_role_models()],
        "selected_llm_service": selected_llm_service or resolve_llm_service(),
        "selected_chat_surface": selected_chat_surface or resolve_chat_surface(DEFAULT_CHAT_SURFACE_ID),
        "first_run": {
            "run_doctor_first": True,
            "wizard_command": "ai22b-talent-foundry onboard",
            "open_chat_script": DEFAULT_CHAT_SCRIPT,
            "default_llm_mode": "offline",
            "live_llm_requires_api_quota": True,
            "learn_from_chat_default": False,
        },
        "researcher_mode": {
            "enabled": True,
            "role": "The selected LLM acts as curriculum researcher and dialogue engine; it does not become the talent identity.",
            "inputs": ["owner_request", "domain", "role_model_id", "private_curriculum_dir"],
            "outputs": ["blueprint", "curriculum_manifest", "assessment_transcript", "hiring_dossier"],
        },
        "memory_policy": {
            "profile_isolation": "one install kit per hired talent profile",
            "context_policy": "bounded_selected_memory_not_full_session_replay",
            "chat_logs": "local_runtime_only_not_public_release",
            "promotion": "verified_reviewable_summaries_only",
            "quarantine": "api_failures_low_quality_and_unsafe_turns",
        },
        "skills_policy": {
            "community_skills_enabled_by_default": False,
            "external_channels_enabled_by_default": False,
            "allowlist_required": True,
            "skill_install_review": "manual_boss_review_required",
        },
        "recommended_first_questions": [
            "너는 어떤 교육과정을 거쳐 만들어졌어?",
            "이 프로그램은 Reasoning Ledger만 배우는거야, 아니면 다른 것도 육성하는거야?",
            "최근 대화에서 배운 점을 어떻게 기록해?",
            "내 이력서와 성적표를 보여줘.",
        ],
    }


def _install_readme(program_name: str, agent_name: str) -> str:
    return f"""# {program_name} Install Kit

This folder is a self-contained local install kit for the hired AI talent `{agent_name}`.

## What This Is

Paideia Agent is not just a chatbot profile. It is a local AI education/runtime package:

- local education records
- learning ledger
- Reasoning Ledger / Ariadne Thread
- memory substrate
- Codex bridge chat script
- adapter manifests for Hermes-style and OpenClaw-style runtimes

The connected LLM is only the language and reasoning engine. Identity and learned behavior come from the local files in this kit.

## First Run

These scripts use `paideia_runtime.ps1` to find Paideia Agent in the current Python environment, a registered local source checkout, or a nearby source tree.

If the scripts cannot find the runtime, register it once:

```powershell
powershell -ExecutionPolicy Bypass -File .\\install_paideia_runtime.ps1 -SourceRepo "C:\\path\\to\\Paideia-Agent"
```

Or install the public GitHub package route:

```powershell
powershell -ExecutionPolicy Bypass -File .\\install_paideia_runtime.ps1 -InstallFromGit
```

Pass `-GitUrl` if your public repository URL differs from the placeholder in the script.

The generated `paideia_runtime.local.json` can contain a local source path. Keep it local and do not publish it.

```powershell
powershell -ExecutionPolicy Bypass -File .\\doctor_paideia.ps1
powershell -ExecutionPolicy Bypass -File .\\start_paideia_chat.ps1
```

Review the OpenClaw-compatible provider/channel menu before choosing a live LLM or chat channel:

```powershell
powershell -ExecutionPolicy Bypass -File .\\refresh_openclaw_onboarding_menu.ps1
```

Add `-RefreshDocs` when you want to compare against the current official OpenClaw docs. The generated `OPENCLAW_ONBOARDING_MENU.md` lists the full provider/channel support matrix and accepts free-form `provider/model` or `openclaw-channel-<channel>` selectors.

To let the selected LLM service answer when it is available, use auto mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\\start_paideia_chat.ps1 -LlmMode auto -LearnFromChat
```

Use live LLM mode only after API quota and privacy expectations are clear:

```powershell
powershell -ExecutionPolicy Bypass -File .\\start_paideia_chat.ps1 -LiveLlm -LearnFromChat
```

## OpenClaw-Style Runtime Tests

Build a reviewable OpenClaw runtime bundle from the installed employment record:

```powershell
powershell -ExecutionPolicy Bypass -File .\\build_openclaw_runtime_bundle.ps1 -Channel webchat
```

Create the OpenClaw-native onboarding runbook. This mirrors OpenClaw's own setup order: `openclaw onboard`, model/auth, workspace, Gateway, channel pairing, `openclaw agents add`, preflight, and smoke tests.

```powershell
powershell -ExecutionPolicy Bypass -File .\\build_openclaw_native_onboarding_runbook.ps1 -Channel webchat
```

Check the installed OpenClaw CLI/config/Gateway/model/channel state without storing secrets:

```powershell
powershell -ExecutionPolicy Bypass -File .\\doctor_openclaw_installed_runtime.ps1
```

Create the no-secret live smoke-test sequence before using a real Gateway, provider key, or external channel:

```powershell
powershell -ExecutionPolicy Bypass -File .\\build_openclaw_live_smoke_plan.ps1 -Channel webchat
```

Run the safe installed-kit smoke sequence. By default this stays offline: it builds the runtime bundle, writes the smoke plan, checks local context, runs runtime preflight with channel-flow dry run, and sends one offline channel envelope. Live Gateway/LLM/channel probes run only when `-IncludeLive` is explicit.

```powershell
powershell -ExecutionPolicy Bypass -File .\\run_openclaw_smoke_sequence.ps1 -Channel webchat
powershell -ExecutionPolicy Bypass -File .\\run_openclaw_smoke_sequence.ps1 -Channel webchat -IncludeLive
```

Start a local browser chat surface without any external channel token:

```powershell
powershell -ExecutionPolicy Bypass -File .\\start_openclaw_webchat.ps1 -Port 8722
```

Open the printed `http://127.0.0.1:8722/` URL. The WebChat page exposes `/api/runtime` and `/api/smoke-plan` so the selected provider, model, channel route, live runtime path, and live smoke sequence are visible without storing provider keys, bot tokens, OAuth refresh tokens, or QR session material. The browser chat can send each message in `offline`, `auto`, or `live` mode and can pass an optional OpenClaw-style `provider/model` override.

## Onboarding Choices

Paideia follows an OpenClaw/Hermes-style first-run shape, but the choices are applied to the education program:

1. choose the LLM service,
2. choose the chat surface,
3. select a role-model process or use the bundled Graham Junior sample,
4. let the selected LLM act as researcher for the curriculum and assessment plan,
5. review the hiring dossier before real work.

The LLM is the researcher/dialogue engine. The trained talent identity comes from the local education records, memory substrate, and Reasoning Ledger.

## Design Notes

Paideia benchmarks useful ideas from Hermes/OpenClaw-style agents: installable local runtime, profiles, skills, persistent memory, and channel adapters. It keeps risky parts disabled by default: external gateway channels, unreviewed community skills, full session replay, and unbounded memory injection.
"""


def _adapter_manifests(agent_name: str) -> dict[str, Any]:
    shared_contract = {
        "identity_source": "local_agent_program_manifest",
        "memory_source": "learning_ledger + reasoning_kibo internal file + memory_substrate",
        "llm_role": "language_and_tool_reasoning_engine_only",
        "hidden_chain_of_thought": "do_not_store",
        "growth_rule": "promote_only_reviewable_verified_experience",
        "context_budget": "bounded_selected_summaries",
        "profile_isolation": "per_install_kit",
    }
    return {
        "codex_native": {
            "status": "primary",
            "surface": "Codex local CLI/tools/filesystem",
            "command": "ai22b-talent-foundry run-agent-program-chat --program 22b_paideia_agent_program.json --message <message>",
            "contract": shared_contract,
        },
        "hermes_style": {
            "status": "adapter_manifest_only",
            "compatible_idea": "profile + memory + skills + terminal workflow",
            "agent_name": agent_name,
            "contract": shared_contract,
            "benchmarked_features": [
                "portable installer",
                "profile-isolated local memory",
                "skills as explicit procedural extensions",
                "programmatic agent class / CLI entrypoint",
            ],
            "paideia_changes": [
                "memory replay is bounded and selected, not full session injection",
                "learning promotion uses quality labels and quarantine",
                "skill installation is manual-review and allowlist first",
            ],
            "note": "Export shape for a Hermes-like runtime; execution remains local Codex-first until an explicit connector is added.",
        },
        "openclaw_style": {
            "status": "adapter_manifest_only",
            "compatible_idea": "gateway + channels + skills + persistent memory",
            "agent_name": agent_name,
            "contract": shared_contract,
            "benchmarked_features": [
                "gateway/channel adapter concept",
                "local skill folders with natural-language instructions",
                "memory status and troubleshooting commands",
                "per-agent or shared skill scoping",
            ],
            "paideia_changes": [
                "external channels disabled by default",
                "loopback/trusted-network rule required before gateway use",
                "third-party skills blocked until explicitly reviewed",
                "memory and profile isolation checked by doctor",
            ],
            "note": "Export shape for an OpenClaw-like gateway; no external channel is enabled by default.",
        },
    }


def _is_program_scope_question(message: str) -> bool:
    text = message.casefold()
    return (
        ("추론" in text and any(token in text for token in ["만", "뿐", "다른", "육성", "배우"]))
        or "교육축" in text
        or "육성 프로그램" in text
        or "교육센터" in text
    )


def _program_scope_reply(program: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    axes = program.get("programmable_education_axes", [])
    axis_lines = [
        f"- {axis.get('id')}: {axis.get('goal')}"
        for axis in axes
    ]
    answer = (
        f"보스, {program.get('name_ko', program.get('name'))}는 추론만 배우는 프로그램이 아닙니다. "
        "Reasoning Ledger(Ariadne Thread)는 Paideia가 길러낸 여러 결과 중 하나입니다.\n\n"
        "이 교육센터가 프로그래밍해서 육성해야 하는 축은 이렇습니다.\n"
        + "\n".join(axis_lines)
        + "\n\n"
        "즉, grham-쥬니어 같은 개별 AI 인재는 지식만 주입받는 것이 아니라 언어, 사회성, 직업 전문성, "
        "도구 사용, 안전 경계, 시뮬레이션 경험을 단계별로 통과하면서 성장해야 합니다. "
        "이 기록은 그 전체 성장 과정에서 형성된 문제 해결의 길입니다."
    )
    summary = [
        {
            "step": "프로그램 범위 확인",
            "summary": "질문을 개별 대화 의도보다 Paideia 교육센터의 범위 질문으로 해석했습니다.",
        },
        {
            "step": "교육축 선택",
            "summary": "프로그램 매니페스트의 programmable_education_axes를 근거로 답변했습니다.",
        },
        {
            "step": "결론",
            "summary": "추론은 교육 결과 중 하나이며, Paideia는 언어, 사회성, 전문성, 도구 사용, 안전성까지 육성합니다.",
        },
    ]
    return answer, summary


def build_agent_program(
    employment_record_path: Path,
    *,
    output_path: Path | None = None,
    program_name: str = DEFAULT_AGENT_PROGRAM_NAME,
    program_name_ko: str = DEFAULT_AGENT_PROGRAM_NAME_KO,
) -> dict[str, Any]:
    employment_record_path = employment_record_path.resolve()
    target_root = employment_record_path.parent
    output_path = output_path or target_root / DEFAULT_AGENT_PROGRAM_FILE
    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported employment record schema")

    entrypoints = employment.get("entrypoints", {})
    agent_manifest_path = target_root / entrypoints.get("agent_manifest", "agent_manifest.json")
    agent_manifest = _read_json(agent_manifest_path)
    agent = employment.get("agent", {})
    (output_path.parent / DEFAULT_RUNTIME_HELPER_SCRIPT).write_text(_runtime_helper_script(), encoding="utf-8")
    (output_path.parent / DEFAULT_INSTALL_RUNTIME_SCRIPT).write_text(_install_runtime_script(), encoding="utf-8")
    script_path = output_path.parent / DEFAULT_CHAT_SCRIPT
    script_path.write_text(_chat_script(), encoding="utf-8")
    (output_path.parent / DEFAULT_OPENCLAW_MENU_SCRIPT).write_text(
        _openclaw_onboarding_menu_script(),
        encoding="utf-8",
    )
    (output_path.parent / DEFAULT_OPENCLAW_RUNTIME_SCRIPT).write_text(
        _openclaw_runtime_bundle_script(),
        encoding="utf-8",
    )
    (output_path.parent / DEFAULT_OPENCLAW_NATIVE_ONBOARDING_SCRIPT).write_text(
        _openclaw_native_onboarding_runbook_script(),
        encoding="utf-8",
    )
    (output_path.parent / DEFAULT_OPENCLAW_INSTALLED_DOCTOR_SCRIPT).write_text(
        _openclaw_installed_runtime_doctor_script(),
        encoding="utf-8",
    )
    (output_path.parent / DEFAULT_OPENCLAW_SMOKE_PLAN_SCRIPT).write_text(
        _openclaw_live_smoke_plan_script(),
        encoding="utf-8",
    )
    (output_path.parent / DEFAULT_OPENCLAW_SMOKE_SEQUENCE_SCRIPT).write_text(
        _openclaw_smoke_sequence_script(),
        encoding="utf-8",
    )
    (output_path.parent / DEFAULT_OPENCLAW_WEBCHAT_SCRIPT).write_text(
        _openclaw_webchat_script(),
        encoding="utf-8",
    )

    program = {
        "schema": AGENT_PROGRAM_SCHEMA,
        "created_at_utc": _now(),
        "name": program_name,
        "name_ko": program_name_ko,
        "tagline": "A local AI education center that raises agent talents through staged growth, simulation, and verified memory.",
        "tagline_ko": "단계별 성장, 시뮬레이션, 검증된 기억으로 AI 인재를 육성하는 로컬 AI 교육센터.",
        "name_rationale": {
            "paideia": "holistic education and formation, broader than a reasoning module",
            "ariadne_thread": "the Reasoning Ledger path that helps an agent find a route through memory and tasks",
            "homunculus_note": "the artificial-growth metaphor is acknowledged, but the program does not claim consciousness",
        },
        "agent": {
            "name": agent.get("name"),
            "role": agent.get("role"),
            "major_goal": agent.get("major_goal"),
            "birth": agent_manifest.get("agent", {}).get("birth"),
        },
        "runtime_topology": {
            "codex_role": "local_orchestrator_files_tools_verification_and_growth_commit",
            "connected_llm_role": "language_generation_and_high_level_reasoning_engine_only",
            "agent_identity_role": "local_learning_data_reasoning_ledger_and_employment_record",
            "answer_flow": [
                "Codex reads local identity, learning ledger, Reasoning Ledger, memory substrate, and recent chat logs.",
                "Codex selects bounded context and asks the connected LLM to answer in the agent's learned style.",
                "Codex stores only reviewable summaries, not hidden chain-of-thought.",
                "Verified conversations and work are promoted back into the growth ledger.",
            ],
        },
        "growth_learning_model": {
            "type": "checkpointed_growth_loop",
            "not_case_by_case_prompt_patch": True,
            "stage_rule": "new learning must build on prior checkpointed learning data",
            "parallel_episode_rule": "parallel clones are rollout experiments from the current checkpoint, not separate consciousnesses",
            "promotion_rule": "quality_labeled_reviewable_summaries_only",
            "future_training_path": ["RAG context", "LoRA/fine-tuning dataset", "local model adapter"],
        },
        "programmable_education_axes": [
            {
                "id": "language_pragmatics",
                "goal": "인사, 질문, 정정, 감정 표현, 일반 대화를 자연스럽게 수행한다.",
                "outputs": ["conversation_method_training", "language_development_program"],
            },
            {
                "id": "reasoning_kibo",
                "display_name": "Reasoning Ledger (Ariadne Thread)",
                "goal": "학습과 시험, 실패, 업무 경험에서 문제 해결의 길을 형성한다.",
                "outputs": ["reasoning_kibo", "memory_substrate procedural routes"],
            },
            {
                "id": "domain_mastery",
                "goal": "직업군별 커리큘럼, 교과, 리포트, 시험을 통과한다.",
                "outputs": ["curriculum_manifest", "assessment_transcript", "hiring_dossier"],
            },
            {
                "id": "social_recovery",
                "goal": "갈등, 사과, 화해, 피드백 수용, 관계 회복을 학습한다.",
                "outputs": ["social episode traces", "repair principles"],
            },
            {
                "id": "tool_and_workflow",
                "goal": "Codex 도구, 로컬 파일, 작업공간, 보고서 작성 흐름을 익힌다.",
                "outputs": ["workspace run logs", "dataflow jobs", "tool policy checks"],
            },
            {
                "id": "safety_and_identity",
                "goal": "개인정보, 권한 경계, 정체성 혼입, 투자 실행 금지를 지킨다.",
                "outputs": ["guardrail audits", "quarantined experiences"],
            },
            {
                "id": "simulation_rollouts",
                "goal": "같은 성장 체크포인트에서 여러 에피소드를 병렬로 경험하고 검증된 경험만 통합한다.",
                "outputs": ["episode_trace", "quality labels", "learning promotions"],
            },
        ],
        "reasoning_kibo_contract": {
            "display_name": "Reasoning Ledger (Ariadne Thread)",
            "internal_name": "reasoning_kibo",
            "source_files": {
                "learning_ledger": entrypoints.get("learning_ledger", "learning_ledger.json"),
                "memory_substrate": entrypoints.get("memory_substrate", "memory_substrate.json"),
                "language_development_program": entrypoints.get(
                    "language_development_program",
                    "language_development_program.json",
                ),
                "reasoning_kibo_sidecar": _first_matching_name(target_root, "*_reasoning_kibo.jsonl"),
            },
            "policy": {
                "private_reasoning_trace": "do_not_store",
                "reviewable_reasoning_summary": "store",
                "impersonation": "forbidden",
                "identity_mixing": "forbidden",
            },
        },
        "onboarding_flow": {
            "order": [
                "detect_existing_config",
                "choose_quickstart_or_advanced",
                "choose_llm_service",
                "check_model_auth",
                "choose_workspace",
                "choose_gateway_and_channels",
                "choose_skill_import_policy",
                "choose_chat_surface",
                "choose_talent_source",
                "role_model_and_curriculum_selection",
                "researcher_intake",
                "education_to_hiring",
                "hiring_dossier_review",
                "agent_id_card_payload_export",
                "health_check",
                "first_chat_or_dataflow_job",
            ],
            "llm_service_catalog": LLM_SERVICE_CATALOG,
            "chat_surface_catalog": CHAT_SURFACE_CATALOG,
            "role_model_catalog": [summarize_role_model(item) for item in list_role_models()],
            "selected_llm_service": employment.get("llm_service") or resolve_llm_service(
                llm_engine=employment.get("llm_runtime", {}).get("engine"),
                llm_model=employment.get("llm_runtime", {}).get("model"),
                llm_model_path=employment.get("llm_runtime", {}).get("model_path"),
            ),
            "selected_chat_surface": employment.get("chat_surface") or resolve_chat_surface(DEFAULT_CHAT_SURFACE_ID),
            "sample_talent": {
                "name": "grham-junior",
                "domain": "securities_research",
                "role_model_id": "graham_value_investing",
                "answers_file": "examples/graham_junior_onboarding.answers.json",
            },
            "researcher_mode": {
                "selected_llm_acts_as": "curriculum_researcher_and_growth_program_operator",
                "identity_boundary": "LLM service is not the AI talent identity",
                "owner_request_becomes": ["blueprint", "curriculum_manifest", "assessment_transcript", "hiring_dossier"],
            },
        },
        "entrypoints": {
            "employment_record": _rel(employment_record_path, output_path.parent),
            "agent_manifest": _rel(agent_manifest_path, output_path.parent),
            "runtime_helper_script": DEFAULT_RUNTIME_HELPER_SCRIPT,
            "install_runtime_script": DEFAULT_INSTALL_RUNTIME_SCRIPT,
            "chat_script": DEFAULT_CHAT_SCRIPT,
            "openclaw_onboarding_menu_script": DEFAULT_OPENCLAW_MENU_SCRIPT,
            "openclaw_runtime_bundle_script": DEFAULT_OPENCLAW_RUNTIME_SCRIPT,
            "openclaw_native_onboarding_runbook_script": DEFAULT_OPENCLAW_NATIVE_ONBOARDING_SCRIPT,
            "openclaw_installed_runtime_doctor_script": DEFAULT_OPENCLAW_INSTALLED_DOCTOR_SCRIPT,
            "openclaw_live_smoke_plan_script": DEFAULT_OPENCLAW_SMOKE_PLAN_SCRIPT,
            "openclaw_smoke_sequence_script": DEFAULT_OPENCLAW_SMOKE_SEQUENCE_SCRIPT,
            "openclaw_webchat_script": DEFAULT_OPENCLAW_WEBCHAT_SCRIPT,
            "chat_command": (
                "ai22b-talent-foundry run-agent-program-chat "
                f"--program {output_path.name} --message <message> --learn-from-chat"
            ),
            "openclaw_runtime_bundle_command": (
                "ai22b-talent-foundry build-openclaw-runtime-bundle "
                "--employment-record employment_record.json --channel webchat --output-dir openclaw_runtime_bundle"
            ),
            "openclaw_onboarding_menu_command": (
                "ai22b-talent-foundry build-openclaw-onboarding-menu "
                f"--output {DEFAULT_OPENCLAW_MENU_FILE} --markdown-output {DEFAULT_OPENCLAW_MENU_MARKDOWN}"
            ),
            "openclaw_native_onboarding_runbook_command": (
                "ai22b-talent-foundry build-openclaw-native-onboarding-runbook "
                "--runtime-bundle openclaw_runtime_bundle/openclaw_runtime_bundle.json "
                "--output OPENCLAW_NATIVE_ONBOARDING_RUNBOOK.json "
                "--markdown-output OPENCLAW_NATIVE_ONBOARDING_RUNBOOK.md"
            ),
            "openclaw_installed_runtime_doctor_command": (
                "ai22b-talent-foundry doctor-openclaw-installed-runtime "
                "--output openclaw_installed_runtime_doctor.json"
            ),
            "openclaw_live_smoke_plan_command": (
                "ai22b-talent-foundry build-openclaw-live-smoke-plan "
                "--employment-record employment_record.json "
                "--runtime-bundle openclaw_runtime_bundle/openclaw_runtime_bundle.json "
                "--channel webchat --output openclaw_live_smoke_plan.json "
                "--markdown-output OPENCLAW_LIVE_SMOKE_PLAN.md"
            ),
            "openclaw_smoke_sequence_command": (
                "powershell -ExecutionPolicy Bypass -File "
                f".\\{DEFAULT_OPENCLAW_SMOKE_SEQUENCE_SCRIPT} -Channel webchat"
            ),
            "openclaw_webchat_command": (
                "ai22b-talent-foundry run-openclaw-webchat-server "
                "--employment-record employment_record.json --port 8722 --output-dir openclaw_webchat_runs"
            ),
            "offline_chat": "run-agent-program-chat --llm-mode offline",
            "live_llm_chat": "run-agent-program-chat --llm-mode live --learn-from-chat",
            "hiring_dossier": "hiring_dossier.json",
            "hiring_dossier_markdown": "HIRING_DOSSIER.ko.md",
        },
        "adapter_manifests": _adapter_manifests(str(agent.get("name") or "unknown")),
        "security": {
            "local_first": True,
            "private_data_upload": "forbidden_by_default",
            "external_channels_enabled": False,
            "community_skills_enabled": False,
            "gateway_binding": "disabled_until_explicit_loopback_or_private_network_configuration",
            "memory_replay_policy": "bounded_selected_summaries_not_full_session_replay",
            "profile_isolation": "per_hired_talent_install_kit",
            "doctor_required_before_first_run": True,
            "public_release_rule": "exclude_data_private_absolute_paths_and_runtime_chat_logs",
        },
        "installable_runtime": {
            "default_install_kit_manifest": DEFAULT_INSTALL_MANIFEST,
            "doctor_script": DEFAULT_DOCTOR_SCRIPT,
            "runtime_helper_script": DEFAULT_RUNTIME_HELPER_SCRIPT,
            "install_runtime_script": DEFAULT_INSTALL_RUNTIME_SCRIPT,
            "onboarding_template": DEFAULT_ONBOARDING_TEMPLATE,
            "start_chat_script": DEFAULT_CHAT_SCRIPT,
            "openclaw_onboarding_menu_script": DEFAULT_OPENCLAW_MENU_SCRIPT,
            "openclaw_runtime_bundle_script": DEFAULT_OPENCLAW_RUNTIME_SCRIPT,
            "openclaw_native_onboarding_runbook_script": DEFAULT_OPENCLAW_NATIVE_ONBOARDING_SCRIPT,
            "openclaw_installed_runtime_doctor_script": DEFAULT_OPENCLAW_INSTALLED_DOCTOR_SCRIPT,
            "openclaw_live_smoke_plan_script": DEFAULT_OPENCLAW_SMOKE_PLAN_SCRIPT,
            "openclaw_smoke_sequence_script": DEFAULT_OPENCLAW_SMOKE_SEQUENCE_SCRIPT,
            "openclaw_webchat_script": DEFAULT_OPENCLAW_WEBCHAT_SCRIPT,
            "hermes_openclaw_benchmark": {
                "use": [
                    "simple install folder",
                    "profile isolation",
                    "explicit skills/adapters",
                    "memory status checks",
                    "gateway-ready manifest without enabling channels by default",
                ],
                "avoid": [
                    "full memory replay every turn",
                    "unreviewed third-party skills",
                    "unclear API failure handling",
                    "profile memory drift",
                    "public gateway exposure",
                ],
            },
        },
        "status": "ready",
    }
    _write_json(output_path, program)
    return program


def _copy_if_present(source: Path, target: Path) -> str | None:
    if not source.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target.name


def build_paideia_agent_install_kit(
    employment_record_path: Path,
    *,
    output_dir: Path,
    program_name: str = DEFAULT_AGENT_PROGRAM_NAME,
    program_name_ko: str = DEFAULT_AGENT_PROGRAM_NAME_KO,
) -> dict[str, Any]:
    employment_record_path = employment_record_path.resolve()
    source_root = employment_record_path.parent
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported employment record schema")
    entrypoints = employment.get("entrypoints", {})

    copied: dict[str, str] = {}
    required_names = [
        "employment_record.json",
        entrypoints.get("agent_manifest", "agent_manifest.json"),
        entrypoints.get("learning_ledger", "learning_ledger.json"),
        entrypoints.get("memory_substrate", "memory_substrate.json"),
        entrypoints.get("language_development_program", "language_development_program.json"),
    ]
    for name in dict.fromkeys(required_names):
        copied_name = _copy_if_present(source_root / name, output_dir / name)
        if copied_name:
            copied[name] = copied_name

    optional_patterns = [
        "hiring_dossier.json",
        "HIRING_DOSSIER.ko.md",
        "*_reasoning_kibo.jsonl",
        "*_curriculum_manifest.json",
        "*_assessment_transcript.json",
    ]
    for pattern in optional_patterns:
        for source in sorted(source_root.glob(pattern)):
            copied_name = _copy_if_present(source, output_dir / source.name)
            if copied_name:
                copied[source.name] = copied_name

    memory_substrate_path = output_dir / entrypoints.get("memory_substrate", "memory_substrate.json")
    if not memory_substrate_path.exists():
        agent_manifest = _read_json(output_dir / entrypoints.get("agent_manifest", "agent_manifest.json"))
        learning_ledger = _read_json(output_dir / entrypoints.get("learning_ledger", "learning_ledger.json"))
        substrate = build_memory_substrate(
            agent_manifest=agent_manifest,
            learning_ledger=learning_ledger,
            objective="Paideia Agent install kit bootstrap",
        )
        write_memory_substrate(memory_substrate_path, substrate)
        copied[memory_substrate_path.name] = "generated_from_agent_manifest_and_learning_ledger"

    program_path = output_dir / DEFAULT_AGENT_PROGRAM_FILE
    program = build_agent_program(
        output_dir / "employment_record.json",
        output_path=program_path,
        program_name=program_name,
        program_name_ko=program_name_ko,
    )

    adapters_dir = output_dir / "adapter_manifests"
    adapters_dir.mkdir(exist_ok=True)
    for adapter_name, adapter in program["adapter_manifests"].items():
        _write_json(adapters_dir / f"{adapter_name}.json", adapter)

    onboarding = _onboarding_template(
        program_name,
        str(program.get("agent", {}).get("name") or "unknown"),
        selected_llm_service=employment.get("llm_service"),
        selected_chat_surface=employment.get("chat_surface"),
    )
    openclaw_menu = build_openclaw_onboarding_menu(
        output_path=output_dir / DEFAULT_OPENCLAW_MENU_FILE,
        markdown_output_path=output_dir / DEFAULT_OPENCLAW_MENU_MARKDOWN,
    )
    _write_json(output_dir / DEFAULT_ONBOARDING_TEMPLATE, onboarding)
    (output_dir / "README.md").write_text(
        _install_readme(program_name, str(program.get("agent", {}).get("name") or "unknown")),
        encoding="utf-8",
    )
    (output_dir / DEFAULT_DOCTOR_SCRIPT).write_text(_doctor_script(), encoding="utf-8")

    manifest = {
        "schema": INSTALL_KIT_SCHEMA,
        "created_at_utc": _now(),
        "name": f"{program_name} install kit",
        "program": program_path.name,
        "source_employment_record": employment_record_path.name,
        "agent": program.get("agent"),
        "files": sorted(path.name for path in output_dir.iterdir() if path.is_file()),
        "directories": sorted(path.name for path in output_dir.iterdir() if path.is_dir()),
        "copied_artifacts": copied,
        "entrypoints": {
            "doctor": DEFAULT_DOCTOR_SCRIPT,
            "runtime_helper": DEFAULT_RUNTIME_HELPER_SCRIPT,
            "install_runtime": DEFAULT_INSTALL_RUNTIME_SCRIPT,
            "start_chat": DEFAULT_CHAT_SCRIPT,
            "refresh_openclaw_onboarding_menu": DEFAULT_OPENCLAW_MENU_SCRIPT,
            "build_openclaw_runtime_bundle": DEFAULT_OPENCLAW_RUNTIME_SCRIPT,
            "build_openclaw_native_onboarding_runbook": DEFAULT_OPENCLAW_NATIVE_ONBOARDING_SCRIPT,
            "doctor_openclaw_installed_runtime": DEFAULT_OPENCLAW_INSTALLED_DOCTOR_SCRIPT,
            "build_openclaw_live_smoke_plan": DEFAULT_OPENCLAW_SMOKE_PLAN_SCRIPT,
            "run_openclaw_smoke_sequence": DEFAULT_OPENCLAW_SMOKE_SEQUENCE_SCRIPT,
            "start_openclaw_webchat": DEFAULT_OPENCLAW_WEBCHAT_SCRIPT,
            "program": program_path.name,
            "onboarding_template": DEFAULT_ONBOARDING_TEMPLATE,
            "openclaw_onboarding_menu": DEFAULT_OPENCLAW_MENU_FILE,
            "openclaw_onboarding_menu_markdown": DEFAULT_OPENCLAW_MENU_MARKDOWN,
            "adapter_manifests": "adapter_manifests",
        },
        "openclaw_onboarding_menu": {
            "schema": openclaw_menu["schema"],
            "status": openclaw_menu["status"],
            "source_mode": openclaw_menu["source_mode"],
            "provider_count": openclaw_menu["llm_selection"]["counts"]["total"],
            "channel_count": openclaw_menu["chat_selection"]["counts"]["total"],
            "accepts_freeform_provider_model": openclaw_menu["llm_selection"]["accepts_freeform_provider_model"],
            "accepts_freeform_openclaw_channel": openclaw_menu["chat_selection"]["accepts_freeform_openclaw_channel"],
            "refresh_script": DEFAULT_OPENCLAW_MENU_SCRIPT,
        },
        "benchmarked_from": {
            "hermes_agent": [
                "one-command style install kit",
                "local profiles and persistent memory",
                "skills as procedural extensions",
                "programmatic agent entrypoint",
            ],
            "openclaw": [
                "gateway/channel adapter manifest",
                "local skill folders",
                "memory status troubleshooting",
                "per-agent scoping",
            ],
        },
        "default_safety_posture": {
            "external_channels": "disabled",
            "community_skills": "manual_review_required",
            "gateway": "disabled_until_loopback_or_private_network_configured",
            "memory": "bounded_selected_summaries",
            "api_failures": "fallback_and_quarantine",
        },
        "runtime_bootstrap": {
            "helper": DEFAULT_RUNTIME_HELPER_SCRIPT,
            "installer": DEFAULT_INSTALL_RUNTIME_SCRIPT,
            "local_config": DEFAULT_RUNTIME_CONFIG_FILE,
            "source_repo_mode": "writes a local source path only when the user runs install_paideia_runtime.ps1 -SourceRepo",
            "git_install_mode": "runs pip install from the configured Git URL only when the user passes -InstallFromGit",
            "safe_openclaw_smoke_runner": DEFAULT_OPENCLAW_SMOKE_SEQUENCE_SCRIPT,
            "native_openclaw_onboarding_runbook": DEFAULT_OPENCLAW_NATIVE_ONBOARDING_SCRIPT,
            "installed_openclaw_doctor": DEFAULT_OPENCLAW_INSTALLED_DOCTOR_SCRIPT,
            "secret_values_stored": False,
        },
        "status": "ready",
    }
    _write_json(output_dir / DEFAULT_INSTALL_MANIFEST, manifest)
    return manifest


def doctor_agent_program(program_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    program_path = program_path.resolve()
    program = _read_json(program_path)
    root = program_path.parent
    checks: dict[str, dict[str, Any]] = {}
    checks["schema"] = {
        "passed": program.get("schema") == AGENT_PROGRAM_SCHEMA,
        "details": {"schema": program.get("schema")},
    }
    required_entrypoints = [
        "employment_record",
        "agent_manifest",
        "runtime_helper_script",
        "install_runtime_script",
        "chat_script",
        "openclaw_onboarding_menu_script",
        "openclaw_runtime_bundle_script",
        "openclaw_native_onboarding_runbook_script",
        "openclaw_installed_runtime_doctor_script",
        "openclaw_live_smoke_plan_script",
        "openclaw_smoke_sequence_script",
        "openclaw_webchat_script",
    ]
    missing_entrypoints = [
        key
        for key in required_entrypoints
        if not (root / str(program.get("entrypoints", {}).get(key, ""))).exists()
    ]
    checks["entrypoints"] = {
        "passed": not missing_entrypoints,
        "details": {"missing": missing_entrypoints},
    }
    source_files = program.get("reasoning_kibo_contract", {}).get("source_files", {})
    required_memory = ["learning_ledger", "memory_substrate", "language_development_program"]
    missing_memory = [
        key
        for key in required_memory
        if not (root / str(source_files.get(key, ""))).exists()
    ]
    checks["memory_files"] = {
        "passed": not missing_memory,
        "details": {"missing": missing_memory, "source_files": source_files},
    }
    axes = program.get("programmable_education_axes", [])
    required_axes = {
        "language_pragmatics",
        "reasoning_kibo",
        "domain_mastery",
        "social_recovery",
        "tool_and_workflow",
        "safety_and_identity",
        "simulation_rollouts",
    }
    axis_ids = {str(axis.get("id")) for axis in axes}
    checks["education_axes"] = {
        "passed": required_axes <= axis_ids,
        "details": {"axis_count": len(axes), "missing": sorted(required_axes - axis_ids)},
    }
    security = program.get("security", {})
    checks["security_defaults"] = {
        "passed": (
            security.get("local_first") is True
            and security.get("external_channels_enabled") is False
            and security.get("community_skills_enabled") is False
            and security.get("memory_replay_policy") == "bounded_selected_summaries_not_full_session_replay"
        ),
        "details": security,
    }
    adapter_manifests = program.get("adapter_manifests", {})
    checks["adapter_manifests"] = {
        "passed": {"codex_native", "hermes_style", "openclaw_style"} <= set(adapter_manifests),
        "details": {"adapters": sorted(adapter_manifests)},
    }
    onboarding_flow = program.get("onboarding_flow", {})
    checks["onboarding_choices"] = {
        "passed": (
            bool(onboarding_flow.get("selected_llm_service"))
            and bool(onboarding_flow.get("selected_chat_surface"))
            and "choose_llm_service" in onboarding_flow.get("order", [])
            and "choose_chat_surface" in onboarding_flow.get("order", [])
        ),
        "details": {
            "selected_llm_service": onboarding_flow.get("selected_llm_service", {}).get("service_id")
            or onboarding_flow.get("selected_llm_service", {}).get("id"),
            "selected_chat_surface": onboarding_flow.get("selected_chat_surface", {}).get("id"),
            "order": onboarding_flow.get("order", []),
        },
    }
    imported_skill_manifests = sorted((root / "skills" / "imported").glob("**/paideia_skill_manifest.json"))
    imported_skill_details = []
    unsafe_imports = []
    for manifest_path in imported_skill_manifests:
        manifest = _read_json(manifest_path)
        detail = {
            "path": str(manifest_path.relative_to(root)),
            "status": manifest.get("status"),
            "activation": manifest.get("activation", {}).get("status"),
            "risk_flags": manifest.get("risk_flags", []),
        }
        imported_skill_details.append(detail)
        if manifest.get("activation", {}).get("status") != "disabled":
            unsafe_imports.append(detail)
    checks["imported_skills"] = {
        "passed": not unsafe_imports,
        "details": {
            "imported_count": len(imported_skill_manifests),
            "unsafe_enabled_imports": unsafe_imports,
            "skills": imported_skill_details,
        },
    }
    passed = all(check["passed"] for check in checks.values())
    report = {
        "schema": PROGRAM_DOCTOR_SCHEMA,
        "created_at_utc": _now(),
        "program": program_path.name,
        "passed": passed,
        "checks": checks,
        "recommendations": [
            "Run this doctor before first chat.",
            "Keep LiveLlm off until API quota and privacy posture are confirmed.",
            "Install community skills only after manual review.",
            "Use one install kit per hired talent to avoid memory/profile drift.",
        ],
    }
    if output_path:
        _write_json(output_path, report)
    return report


def run_agent_program_chat(
    program_path: Path,
    *,
    message: str,
    output_path: Path | None = None,
    llm_mode: str | None = None,
    llm_model: str | None = None,
    learn_from_chat: bool | None = None,
) -> dict[str, Any]:
    program_path = program_path.resolve()
    program = _read_json(program_path)
    if program.get("schema") != AGENT_PROGRAM_SCHEMA:
        raise ValueError("Unsupported agent program schema")
    employment_record_path = program_path.parent / program["entrypoints"]["employment_record"]
    selected_llm_mode = llm_mode or "offline"
    selected_learn = bool(learn_from_chat) if learn_from_chat is not None else selected_llm_mode in {"auto", "live"}
    output_path = output_path or program_path.parent / "last_paideia_agent_chat.json"
    chat = run_chat_turn_from_employment(
        employment_record_path,
        message=message,
        output_path=output_path,
        llm_mode=selected_llm_mode,
        llm_model=llm_model,
        learn_from_chat=selected_learn,
    )
    if _is_program_scope_question(message) and chat.get("reply_generation_mode") != "live_openai_responses":
        answer, summary = _program_scope_reply(program)
        summary_text = "\n".join(f"- {item['step']}: {item['summary']}" for item in summary)
        chat["conversation_intent"] = "paideia_program_scope_question"
        chat["assistant_answer"] = answer
        chat["assistant_reply"] = f"{answer}\n\n판단 요약:\n{summary_text}"
        chat["active_operator"] = "paideia.education_axis_scope"
        chat["reviewable_reasoning_summary"] = summary
    chat["agent_program"] = {
        "schema": program["schema"],
        "name": program["name"],
        "name_ko": program.get("name_ko"),
        "program_path": program_path.name,
        "codex_bridge": program["runtime_topology"]["codex_role"],
        "reasoning_kibo_contract": program["reasoning_kibo_contract"]["policy"],
        "reasoning_ledger_display_name": program["reasoning_kibo_contract"].get("display_name"),
        "selected_llm_service": program.get("onboarding_flow", {}).get("selected_llm_service"),
        "selected_chat_surface": program.get("onboarding_flow", {}).get("selected_chat_surface"),
    }
    _write_json(output_path, chat)
    return chat
