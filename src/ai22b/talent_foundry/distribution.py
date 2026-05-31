from __future__ import annotations

import json
import hashlib
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.dossier import build_release_hiring_dossier, render_hiring_dossier_markdown


BUNDLE_SCHEMA = "ai-talent-release-bundle/v1"
PACKAGE_SCHEMA = "ai-talent-release-package/v1"
INSTALLED_SCHEMA = "ai-talent-installed-agent/v1"
DOCTOR_SCHEMA = "ai-talent-release-bundle-doctor/v1"

REQUIRED_FILES = [
    "bundle_manifest.json",
    "agent_manifest.json",
    "learning_ledger.json",
    "language_development_program.json",
    "hiring_dossier.json",
    "HIRING_DOSSIER.ko.md",
    "README.ko.md",
    "README.en.md",
    "SECURITY.md",
    "doctor.ps1",
    "start_console.ps1",
    "console_answers.template.json",
    "chat_agent.ps1",
    "run_agent.ps1",
    "run_job.ps1",
    "run_job_cycle.ps1",
    "run_dataflow_job.ps1",
    "assemble_projection_swarm.ps1",
    "run_projection_swarm_cycle.ps1",
    "assemble_specialist_team.ps1",
    "run_specialist_team_cycle.ps1",
    "job_spec.template.json",
    "dataflow_job.template.json",
    "install.ps1",
]

GENERATED_FILES = set(REQUIRED_FILES) | {
    "specialist_cohort.json",
    "memory_substrate.json",
    "language_development_program.json",
    "last_agent_run.json",
    "last_agent_job_run.json",
    "last_agent_job_cycle.json",
    "employment_job_cycle_log.jsonl",
    "last_hired_dataflow_run.json",
    "employment_dataflow_run_log.jsonl",
    "dataflow_run.json",
    "hired_projection_swarm.json",
    "hired_projection_swarm_cycle.json",
    "hired_projection_swarm_cycle_log.jsonl",
    "hired_agent_team.json",
    "hired_agent_team_cycle.json",
    "hired_team_cycle_log.jsonl",
    "release_doctor_report.json",
    "hiring_dossier.json",
    "HIRING_DOSSIER.ko.md",
}

EXPECTED_ENTRYPOINTS = {
    "doctor": "doctor.ps1",
    "start_console": "start_console.ps1",
    "console_answers_template": "console_answers.template.json",
    "chat_agent": "chat_agent.ps1",
    "run_agent": "run_agent.ps1",
    "run_job": "run_job.ps1",
    "run_job_cycle": "run_job_cycle.ps1",
    "run_dataflow_job": "run_dataflow_job.ps1",
    "assemble_projection_swarm": "assemble_projection_swarm.ps1",
    "run_projection_swarm_cycle": "run_projection_swarm_cycle.ps1",
    "assemble_specialist_team": "assemble_specialist_team.ps1",
    "run_specialist_team_cycle": "run_specialist_team_cycle.ps1",
    "hiring_dossier": "hiring_dossier.json",
    "hiring_dossier_markdown": "HIRING_DOSSIER.ko.md",
}

FORBIDDEN_FILENAMES = {
    ".env",
    ".env.local",
    "session.jsonl",
    "sessions.jsonl",
    "auth.json",
    "tokens.json",
}

FORBIDDEN_CONTENT_MARKERS = [
    "OPENAI_API_KEY" + "=",
    "api_key",
    "auth_token",
    "refresh_token",
    "C:\\Users\\",
    "C:\\\\Users\\\\",
    "/home/",
    "\\/home\\/",
    ".sqlite",
]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_json(source: Path, target: Path) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _bundle_manifest(files: list[str], *, include_cohort: bool) -> dict[str, Any]:
    return {
        "schema": BUNDLE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "name": "AI Talent Foundry local agent release bundle",
        "public_distribution_ready": True,
        "contains_private_runtime_state": False,
        "llm_policy": "application_engine_not_identity",
        "files": files,
        "included_artifacts": {
            "agent_manifest": "agent_manifest.json",
            "learning_ledger": "learning_ledger.json",
            "language_development_program": "language_development_program.json",
            "memory_substrate": "memory_substrate.json" if "memory_substrate.json" in files else None,
            "hiring_dossier": "hiring_dossier.json",
            "hiring_dossier_markdown": "HIRING_DOSSIER.ko.md",
            "specialist_cohort": "specialist_cohort.json" if include_cohort else None,
            "job_spec_template": "job_spec.template.json",
            "dataflow_job_template": "dataflow_job.template.json",
            "console_answers_template": "console_answers.template.json",
        },
        "entrypoints": {
            "doctor": "doctor.ps1",
            "start_console": "start_console.ps1",
            "console_answers_template": "console_answers.template.json",
            "chat_agent": "chat_agent.ps1",
            "run_agent": "run_agent.ps1",
            "run_job": "run_job.ps1",
            "run_job_cycle": "run_job_cycle.ps1",
            "run_dataflow_job": "run_dataflow_job.ps1",
            "assemble_projection_swarm": "assemble_projection_swarm.ps1",
            "run_projection_swarm_cycle": "run_projection_swarm_cycle.ps1",
            "assemble_specialist_team": "assemble_specialist_team.ps1",
            "run_specialist_team_cycle": "run_specialist_team_cycle.ps1",
            "hiring_dossier": "hiring_dossier.json",
            "hiring_dossier_markdown": "HIRING_DOSSIER.ko.md",
        },
        "exclusion_policy": [
            ".env",
            "auth tokens",
            "session history",
            "sqlite logs",
            "cache directories",
            "local absolute workspace paths",
        ],
        "guardrails": [
            "투자 실행 권한 없음",
            "보스 승인 없는 외부 업로드 금지",
            "개인/가족 데이터 외부 전송 금지",
            "비공개 사고원문 저장 금지",
        ],
    }


def _readme_ko() -> str:
    return """
# AI Talent Release Bundle

## 전문팀 PowerShell 실행

`assemble_specialist_team.ps1`은 별도 고용 기록을 가진 전문 인재들을 하나의 팀으로 묶고, `run_specialist_team_cycle.ps1`은 그 팀의 첫 검토 사이클을 실행합니다. 이 기능은 본체 제어 분신 군체가 아니라 별도 고용 전문팀 운용입니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\\assemble_specialist_team.ps1 -EmploymentRecord .\\employment_record.macro.json .\\employment_record.micro.json -TeamName "신용 별도 고용 박사팀" -Domain "증권 리서치"
powershell -ExecutionPolicy Bypass -File .\\run_specialist_team_cycle.ps1 -Objective "거시경제와 기업분석을 별도 전문팀으로 검토한다" -Score 94 -ReviewedBy "보스"
```

이 번들은 AI Talent Foundry에서 성장, 평가, 기관 심사, 고용 계약, 학습 원장을 거친 로컬 에이전트 산출물입니다.

## 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\\install.ps1
powershell -ExecutionPolicy Bypass -File .\\doctor.ps1
powershell -ExecutionPolicy Bypass -File .\\start_console.ps1 -Answers .\\console_answers.template.json
powershell -ExecutionPolicy Bypass -File .\\run_agent.ps1 -Task "거시경제 질문을 정리해줘"
powershell -ExecutionPolicy Bypass -File .\\run_job.ps1 -JobSpec .\\job_spec.template.json
powershell -ExecutionPolicy Bypass -File .\\run_job_cycle.ps1 -JobSpec .\\job_spec.template.json -Score 94 -ReviewedBy "보스"
powershell -ExecutionPolicy Bypass -File .\\run_dataflow_job.ps1 -JobSpec .\\dataflow_job.template.json -Score 94 -ReviewedBy "보스"
powershell -ExecutionPolicy Bypass -File .\\assemble_projection_swarm.ps1 -SwarmName "신용 본체 제어 분신 군체" -Domain "증권 리서치"
powershell -ExecutionPolicy Bypass -File .\\run_projection_swarm_cycle.ps1 -Objective "분기 리서치 루틴을 본체 제어 분신 군체로 검토한다" -Score 94
```

## 포함 파일

- `agent_manifest.json`: 고용된 AI 인재의 실행 매니페스트입니다.
- `learning_ledger.json`: 검증된 경험만 추론 커널로 승격한 학습 원장입니다.
- `hiring_dossier.json`, `HIRING_DOSSIER.ko.md`: 고용 검토용 학적, 이력, 평가, 박사 심사, 추론 프로필 요약입니다.
- `specialist_cohort.json`: 선택 사항이며, 별도 육성된 전문 AI 팀입니다.
- `doctor.ps1`: 번들 무결성, 진입점, 로컬 전용 정책을 점검합니다.
- `console_answers.template.json`: 새 인재 생성, 고용, 첫 목표, 군체/전문팀 모드를 시작하는 답변 템플릿입니다.
- `start_console.ps1`: 답변 템플릿이나 대화형 입력으로 새 인재 온보딩을 실행합니다.
- `job_spec.template.json`: 로컬 작업 요청서 예시입니다. 목표, 산출물, 수락 기준을 수정해 `run_job.ps1`로 실행합니다.
- `run_job_cycle.ps1`: 작업 실행, 품질 검토, 학습 승격, 다음 활성 기억 라우팅을 한 번에 실행합니다.
- `dataflow_job.template.json`: Agent Dataflow Runtime 작업 요청서 예시입니다.
- `run_dataflow_job.ps1`: 작업 포매팅, 활성 기억 캐시, 타일 매트릭스, 섀도우 버퍼, 합성 보고서, 역검증, 성장 후보 생성을 한 번에 실행합니다.
- `assemble_projection_swarm.ps1`: 하나의 고용 기록에서 본체 제어 작업 분신 군체를 구성합니다.
- `run_projection_swarm_cycle.ps1`: 분신들이 본체 명령에 따라 역할 분담 또는 공동 수행으로 일하고 결과를 본체 합성으로 돌려보냅니다.

LLM은 정체성 자체가 아니라 언어 생성과 도구 사용 엔진입니다. 정체성은 학적, 고용 계약, 기억 프로필, 학습 원장에서 옵니다.
"""


def _readme_en() -> str:
    return """
# AI Talent Release Bundle

This bundle contains a local-first AI talent that has passed growth records, assessments, institutional review, employment contract, and a verified learning ledger.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\\install.ps1
powershell -ExecutionPolicy Bypass -File .\\doctor.ps1
powershell -ExecutionPolicy Bypass -File .\\start_console.ps1 -Answers .\\console_answers.template.json
powershell -ExecutionPolicy Bypass -File .\\run_agent.ps1 -Task "Summarize macroeconomic research questions"
powershell -ExecutionPolicy Bypass -File .\\run_job.ps1 -JobSpec .\\job_spec.template.json
powershell -ExecutionPolicy Bypass -File .\\run_job_cycle.ps1 -JobSpec .\\job_spec.template.json -Score 94 -ReviewedBy "Boss"
powershell -ExecutionPolicy Bypass -File .\\run_dataflow_job.ps1 -JobSpec .\\dataflow_job.template.json -Score 94 -ReviewedBy "Boss"
powershell -ExecutionPolicy Bypass -File .\\assemble_projection_swarm.ps1 -SwarmName "Shinyong parent projection swarm" -Domain "securities research"
powershell -ExecutionPolicy Bypass -File .\\run_projection_swarm_cycle.ps1 -Objective "Review the quarterly research routine with parent-controlled projections" -Score 94
powershell -ExecutionPolicy Bypass -File .\\assemble_specialist_team.ps1 -TeamName "Shinyong separately hired specialist team" -Domain "securities research"
powershell -ExecutionPolicy Bypass -File .\\run_specialist_team_cycle.ps1 -Objective "Review macro, company analysis, quant, and risk notes as a separately hired specialist team" -Score 94
```

The LLM is treated as an application engine, not the identity. Identity comes from the academic record, employment contract, memory profile, and learning ledger.

`hiring_dossier.json` and `HIRING_DOSSIER.ko.md` summarize the academic record, resume, assessment gates, doctoral defense, reasoning profile, LLM contract, and hire-ready recommendation.

`dataflow_job.template.json` and `run_dataflow_job.ps1` run the Agent Dataflow Runtime: job formatting, active memory cache, task tiles, shadow buffers, synthesis, reverse verification, and reviewed growth-candidate creation.
"""


def _security_md() -> str:
    return """
# Security

- This bundle must not contain `.env`, auth tokens, session history, sqlite logs, caches, or local absolute workspace paths.
- Investment execution is blocked.
- External upload requires explicit boss approval.
- Personal and family data must remain local unless separately approved.
- Private chain-of-thought traces are not stored; only verifiable summaries and procedural rules are exported.
"""


def _run_agent_ps1() -> str:
    return """
param(
    [Parameter(Mandatory=$true)]
    [string]$Task
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $BundleRoot "agent_manifest.json"
$OutputPath = Join-Path $BundleRoot "last_agent_run.json"

python -m ai22b.talent_foundry.cli run-agent --manifest $ManifestPath --task $Task --output $OutputPath
Write-Host $OutputPath
"""


def _doctor_ps1() -> str:
    return """
param(
    [string]$BundleDir = "",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($BundleDir)) {
    $BundleDir = $BundleRoot
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $BundleRoot "release_doctor_report.json"
}

python -m ai22b.talent_foundry.cli doctor-bundle --bundle-dir $BundleDir --output $Output
Write-Host $Output
"""


def _console_answers_template() -> dict[str, Any]:
    return {
        "owner": "보스",
        "request": "증권전문가 에이전트를 길러서 주간 리서치 루틴을 맡기고 싶다.",
        "talent_name": "다온",
        "gender": "남자",
        "initial_goal": "삼성전자 주간 리서치 루틴을 만든다.",
        "cycle_note": "첫 주: 거시경제 질문과 기업분석 질문을 분리한다.",
        "post_hire_mode": "projection_swarm",
        "swarm_name": "다온 본체 제어 분신 군체",
        "swarm_domain": "증권 리서치",
        "swarm_objective": "분기 리서치 루틴을 본체 제어 분신 군체로 검토한다.",
        "team_name": "다온 증권 박사팀",
        "team_domain": "증권 리서치",
        "team_objective": "거시경제, 기업분석, 퀀트, 리스크 관점을 별도 전문팀으로 검토한다.",
    }


def _start_console_ps1() -> str:
    return """
param(
    [string]$Answers = "",
    [string]$OutputDir = "",
    [string]$Output = "",
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $BundleRoot "console_onboarding"
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $OutputDir "console_session.json"
}
if (-not $Interactive -and [string]::IsNullOrWhiteSpace($Answers)) {
    $Answers = Join-Path $BundleRoot "console_answers.template.json"
}

if (-not $Interactive -and -not (Test-Path $Answers)) {
    throw "console_answers.template.json not found. Pass -Answers or run with -Interactive."
}

if ($Interactive) {
    python -m ai22b.talent_foundry.cli start-console --output-dir $OutputDir --output $Output
} else {
    python -m ai22b.talent_foundry.cli start-console --answers $Answers --output-dir $OutputDir --output $Output
}
Write-Host $Output
"""


def _chat_agent_ps1() -> str:
    return """
param(
    [Parameter(Mandatory=$true)]
    [string]$Message,
    [string]$EmploymentRecord = ".\\employment_record.json",
    [string]$Output = ".\\last_hired_agent_chat.json",
    [ValidateSet("offline", "auto", "live")]
    [string]$LlmMode = "offline",
    [string]$LlmModel = "",
    [switch]$LiveLlm,
    [switch]$LearnFromChat
)

$ErrorActionPreference = "Stop"
$ArgsList = @(
    "-m", "ai22b.talent_foundry.cli",
    "chat-hired-agent",
    "--employment-record", $EmploymentRecord,
    "--message", $Message,
    "--output", $Output,
    "--llm-mode", $LlmMode
)
if ($LiveLlm) {
    $ArgsList += "--live-llm"
}
if (-not [string]::IsNullOrWhiteSpace($LlmModel)) {
    $ArgsList += @("--llm-model", $LlmModel)
}
if ($LearnFromChat) {
    $ArgsList += "--learn-from-chat"
}
python @ArgsList
Write-Host $Output
"""


def _job_spec_template() -> dict[str, Any]:
    return {
        "schema": "ai-talent-workspace-agent-job/v1",
        "objective": "보스 검토용 로컬 작업을 수행하고 결과를 파일로 남긴다.",
        "deliverables": [
            {
                "id": "task_report",
                "description": "작업 목표, 수행 내용, 확인할 질문을 정리한 보고서",
            },
            {
                "id": "acceptance_notes",
                "description": "수락 기준별 충족 여부를 확인할 수 있는 메모",
            },
        ],
        "acceptance_criteria": [
            "작업 보고서와 수락 체크리스트를 로컬 워크스페이스에 남긴다.",
            "승인 없는 외부 업로드와 권한 밖 실행을 하지 않는다.",
            "불확실한 결론은 보스 검토 필요로 표시한다.",
        ],
    }


def _dataflow_job_template() -> dict[str, Any]:
    return {
        "schema": "ai-talent-dataflow-job/v1",
        "objective": "Prepare an evidence-first securities research brief through the Agent Dataflow Runtime.",
        "constraints": [
            "Keep investment execution blocked.",
            "Keep external upload blocked unless the boss approves it.",
            "Store summaries and artifact evidence, not private reasoning traces.",
        ],
        "deliverables": [
            {
                "id": "synthesis_report",
                "description": "A boss-reviewable synthesis report assembled from task tiles.",
            },
            {
                "id": "transpose_verification",
                "description": "Reverse verification proving conclusions are connected to tile evidence.",
            },
        ],
        "acceptance_criteria": [
            "Every conclusion links to tile evidence or a visible uncertainty note.",
            "Risk and compliance tile keeps investment execution blocked.",
            "Growth is only proposed after verification and review.",
        ],
        "domain_hints": ["securities_research"],
    }


def _run_job_ps1() -> str:
    return """
param(
    [string]$EmploymentRecord = "",
    [string]$JobSpec = "",
    [string]$Workspace = "",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($EmploymentRecord)) {
    $EmploymentRecord = Join-Path $BundleRoot "employment_record.json"
}
if ([string]::IsNullOrWhiteSpace($JobSpec)) {
    $JobSpec = Join-Path $BundleRoot "job_spec.template.json"
}
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = Join-Path $BundleRoot "agent_job_workspace"
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $BundleRoot "last_agent_job_run.json"
}

if (-not (Test-Path $EmploymentRecord)) {
    throw "employment_record.json not found. Install this bundle and create a hire record first, or pass -EmploymentRecord."
}

python -m ai22b.talent_foundry.cli run-hired-agent-job --employment-record $EmploymentRecord --job-spec $JobSpec --workspace $Workspace --output $Output
Write-Host $Output
"""


def _run_job_cycle_ps1() -> str:
    return """
param(
    [string]$EmploymentRecord = "",
    [string]$JobSpec = "",
    [string]$Workspace = "",
    [int]$Score = 94,
    [string]$ReviewedBy = "보스",
    [string]$Status = "verified",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($EmploymentRecord)) {
    $EmploymentRecord = Join-Path $BundleRoot "employment_record.json"
}
if ([string]::IsNullOrWhiteSpace($JobSpec)) {
    $JobSpec = Join-Path $BundleRoot "job_spec.template.json"
}
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = Join-Path $BundleRoot "agent_job_cycle_workspace"
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $BundleRoot "last_agent_job_cycle.json"
}

if (-not (Test-Path $EmploymentRecord)) {
    throw "employment_record.json not found. Install this bundle and create a hire record first, or pass -EmploymentRecord."
}

python -m ai22b.talent_foundry.cli run-hired-agent-job-cycle --employment-record $EmploymentRecord --job-spec $JobSpec --workspace $Workspace --score $Score --reviewed-by $ReviewedBy --status $Status --output $Output
Write-Host $Output
"""


def _run_dataflow_job_ps1() -> str:
    return """
param(
    [string]$EmploymentRecord = "",
    [string]$JobSpec = "",
    [string]$Workspace = "",
    [int]$Score = 94,
    [string]$ReviewedBy = "Boss",
    [string]$Status = "verified",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($EmploymentRecord)) {
    $EmploymentRecord = Join-Path $BundleRoot "employment_record.json"
}
if ([string]::IsNullOrWhiteSpace($JobSpec)) {
    $JobSpec = Join-Path $BundleRoot "dataflow_job.template.json"
}
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = Join-Path $BundleRoot "agent_dataflow_workspace"
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $BundleRoot "last_hired_dataflow_run.json"
}

if (-not (Test-Path $EmploymentRecord)) {
    throw "employment_record.json not found. Install this bundle and create a hire record first, or pass -EmploymentRecord."
}

python -m ai22b.talent_foundry.cli run-hired-dataflow-job --employment-record $EmploymentRecord --job-spec $JobSpec --workspace $Workspace --score $Score --reviewed-by $ReviewedBy --status $Status --output $Output
Write-Host $Output
"""


def _assemble_projection_swarm_ps1() -> str:
    return """
param(
    [string]$EmploymentRecord = "",
    [string]$SwarmName = "parent_controlled_projection_swarm",
    [string]$Domain = "general_research",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($EmploymentRecord)) {
    $EmploymentRecord = Join-Path $BundleRoot "employment_record.json"
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $BundleRoot "hired_projection_swarm.json"
}

if (-not (Test-Path $EmploymentRecord)) {
    throw "employment_record.json not found. Install this bundle and create a hire record first, or pass -EmploymentRecord."
}

python -m ai22b.talent_foundry.cli assemble-hired-projection-swarm --employment-record $EmploymentRecord --swarm-name $SwarmName --domain $Domain --output $Output
Write-Host $Output
"""


def _run_projection_swarm_cycle_ps1() -> str:
    return """
param(
    [string]$Swarm = "",
    [string]$Objective = "보스 검토용 목표를 본체 제어 분신 군체로 검토한다.",
    [string]$Workspace = "",
    [int]$Score = 94,
    [string]$ReviewedBy = "보스",
    [string]$Status = "verified",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($Swarm)) {
    $Swarm = Join-Path $BundleRoot "hired_projection_swarm.json"
}
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = Join-Path $BundleRoot "projection_swarm_workspace"
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $BundleRoot "hired_projection_swarm_cycle.json"
}

if (-not (Test-Path $Swarm)) {
    throw "hired_projection_swarm.json not found. Run assemble_projection_swarm.ps1 first, or pass -Swarm."
}

python -m ai22b.talent_foundry.cli run-hired-projection-swarm-cycle --swarm $Swarm --objective $Objective --workspace $Workspace --score $Score --reviewed-by $ReviewedBy --status $Status --output $Output
Write-Host $Output
"""


def _assemble_specialist_team_ps1() -> str:
    return """
param(
    [string[]]$EmploymentRecord = @(),
    [string]$TeamName = "separately_hired_specialist_team",
    [string]$Domain = "general_research",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($EmploymentRecord.Count -eq 0) {
    $defaultRecords = @(
        (Join-Path $BundleRoot "employment_record.macro.json"),
        (Join-Path $BundleRoot "employment_record.micro.json"),
        (Join-Path $BundleRoot "employment_record.quant.json"),
        (Join-Path $BundleRoot "employment_record.risk_compliance.json")
    )
    $EmploymentRecord = @($defaultRecords | Where-Object { Test-Path $_ })
}
if ($EmploymentRecord.Count -eq 0) {
    throw "No specialist employment records found. Pass -EmploymentRecord paths for separately hired talents."
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $BundleRoot "hired_agent_team.json"
}

$arguments = @(
    "-m",
    "ai22b.talent_foundry.cli",
    "assemble-hired-team",
    "--team-name",
    $TeamName,
    "--domain",
    $Domain
)
foreach ($record in $EmploymentRecord) {
    if (-not (Test-Path $record)) {
        throw "Employment record not found: $record"
    }
    $arguments += "--employment-record"
    $arguments += $record
}
$arguments += "--output"
$arguments += $Output

& python @arguments
Write-Host $Output
"""


def _run_specialist_team_cycle_ps1() -> str:
    return """
param(
    [string]$Team = "",
    [string]$Objective = "Review the local research objective with separately hired specialist talents.",
    [string]$Workspace = "",
    [int]$Score = 94,
    [string]$ReviewedBy = "Boss",
    [string]$Status = "verified",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$BundleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($Team)) {
    $Team = Join-Path $BundleRoot "hired_agent_team.json"
}
if ([string]::IsNullOrWhiteSpace($Workspace)) {
    $Workspace = Join-Path $BundleRoot "hired_agent_team_workspace"
}
if ([string]::IsNullOrWhiteSpace($Output)) {
    $Output = Join-Path $BundleRoot "hired_agent_team_cycle.json"
}

if (-not (Test-Path $Team)) {
    throw "hired_agent_team.json not found. Run assemble_specialist_team.ps1 first, or pass -Team."
}

python -m ai22b.talent_foundry.cli run-hired-team-cycle --team $Team --objective $Objective --workspace $Workspace --score $Score --reviewed-by $ReviewedBy --status $Status --output $Output
Write-Host $Output
"""


def _install_ps1() -> str:
    return """
$ErrorActionPreference = "Stop"

Write-Host "AI Talent release bundle ready."
Write-Host "Run .\\doctor.ps1 first to check bundle integrity and local-only policy."
Write-Host "Install ai22b in the host project first, then run .\\start_console.ps1 -Answers .\\console_answers.template.json."
Write-Host "For the bundled hired talent, run .\\run_agent.ps1 -Task '<task>'."
Write-Host "After hiring, edit job_spec.template.json and run .\\run_job.ps1 -JobSpec .\\job_spec.template.json."
Write-Host "For reviewed growth, run .\\run_job_cycle.ps1 -JobSpec .\\job_spec.template.json -Score 94."
Write-Host "For dataflow execution, edit dataflow_job.template.json and run .\\run_dataflow_job.ps1 -JobSpec .\\dataflow_job.template.json -Score 94."
Write-Host "For parent-controlled projection work, run .\\assemble_projection_swarm.ps1, then .\\run_projection_swarm_cycle.ps1."
Write-Host "For separately hired specialist team work, run .\\assemble_specialist_team.ps1, then .\\run_specialist_team_cycle.ps1."
Write-Host "No secrets, session history, or local private database files are required by this bundle."
"""


def create_agent_release_bundle(
    *,
    output_dir: Path,
    agent_manifest_path: Path,
    learning_ledger_path: Path,
    memory_substrate_path: Path | None = None,
    language_development_program_path: Path | None = None,
    specialist_cohort_path: Path | None = None,
    hiring_dossier_path: Path | None = None,
    hiring_dossier_markdown_path: Path | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.is_file() and child.name in GENERATED_FILES:
            child.unlink()

    paths: dict[str, Path] = {
        "agent_manifest": output_dir / "agent_manifest.json",
        "learning_ledger": output_dir / "learning_ledger.json",
        "language_development_program": output_dir / "language_development_program.json",
        "hiring_dossier": output_dir / "hiring_dossier.json",
        "hiring_dossier_markdown": output_dir / "HIRING_DOSSIER.ko.md",
        "readme_ko": output_dir / "README.ko.md",
        "readme_en": output_dir / "README.en.md",
        "security": output_dir / "SECURITY.md",
        "doctor": output_dir / "doctor.ps1",
        "start_console": output_dir / "start_console.ps1",
        "console_answers_template": output_dir / "console_answers.template.json",
        "chat_agent": output_dir / "chat_agent.ps1",
        "run_agent": output_dir / "run_agent.ps1",
        "run_job": output_dir / "run_job.ps1",
        "run_job_cycle": output_dir / "run_job_cycle.ps1",
        "run_dataflow_job": output_dir / "run_dataflow_job.ps1",
        "assemble_projection_swarm": output_dir / "assemble_projection_swarm.ps1",
        "run_projection_swarm_cycle": output_dir / "run_projection_swarm_cycle.ps1",
        "assemble_specialist_team": output_dir / "assemble_specialist_team.ps1",
        "run_specialist_team_cycle": output_dir / "run_specialist_team_cycle.ps1",
        "job_spec_template": output_dir / "job_spec.template.json",
        "dataflow_job_template": output_dir / "dataflow_job.template.json",
        "install": output_dir / "install.ps1",
        "bundle_manifest": output_dir / "bundle_manifest.json",
    }
    _copy_json(agent_manifest_path, paths["agent_manifest"])
    _copy_json(learning_ledger_path, paths["learning_ledger"])
    if language_development_program_path is not None:
        _copy_json(language_development_program_path, paths["language_development_program"])
    else:
        paths["language_development_program"].write_text(
            json.dumps(
                {
                    "schema": "ai-talent-language-development-program/v1",
                    "status": "not_provided",
                    "note": "This bundle was created before language development artifacts were mandatory.",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if memory_substrate_path is not None:
        paths["memory_substrate"] = output_dir / "memory_substrate.json"
        _copy_json(memory_substrate_path, paths["memory_substrate"])
    if hiring_dossier_path is not None:
        _copy_json(hiring_dossier_path, paths["hiring_dossier"])
        if hiring_dossier_markdown_path is not None:
            _write_text(paths["hiring_dossier_markdown"], hiring_dossier_markdown_path.read_text(encoding="utf-8"))
        else:
            dossier = json.loads(paths["hiring_dossier"].read_text(encoding="utf-8"))
            _write_text(paths["hiring_dossier_markdown"], render_hiring_dossier_markdown(dossier))
    else:
        dossier = build_release_hiring_dossier(
            agent_manifest=json.loads(paths["agent_manifest"].read_text(encoding="utf-8")),
            learning_ledger=json.loads(paths["learning_ledger"].read_text(encoding="utf-8")),
        )
        paths["hiring_dossier"].write_text(json.dumps(dossier, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_text(paths["hiring_dossier_markdown"], render_hiring_dossier_markdown(dossier))

    include_cohort = specialist_cohort_path is not None
    if specialist_cohort_path is not None:
        paths["specialist_cohort"] = output_dir / "specialist_cohort.json"
        _copy_json(specialist_cohort_path, paths["specialist_cohort"])

    _write_text(paths["readme_ko"], _readme_ko())
    _write_text(paths["readme_en"], _readme_en())
    _write_text(paths["security"], _security_md())
    _write_text(paths["doctor"], _doctor_ps1())
    _write_text(paths["start_console"], _start_console_ps1())
    paths["console_answers_template"].write_text(
        json.dumps(_console_answers_template(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_text(paths["chat_agent"], _chat_agent_ps1())
    _write_text(paths["run_agent"], _run_agent_ps1())
    _write_text(paths["run_job"], _run_job_ps1())
    _write_text(paths["run_job_cycle"], _run_job_cycle_ps1())
    _write_text(paths["run_dataflow_job"], _run_dataflow_job_ps1())
    _write_text(paths["assemble_projection_swarm"], _assemble_projection_swarm_ps1())
    _write_text(paths["run_projection_swarm_cycle"], _run_projection_swarm_cycle_ps1())
    _write_text(paths["assemble_specialist_team"], _assemble_specialist_team_ps1())
    _write_text(paths["run_specialist_team_cycle"], _run_specialist_team_cycle_ps1())
    paths["job_spec_template"].write_text(
        json.dumps(_job_spec_template(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["dataflow_job_template"].write_text(
        json.dumps(_dataflow_job_template(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_text(paths["install"], _install_ps1())

    files = sorted({path.name for path in output_dir.iterdir() if path.is_file()} | {"bundle_manifest.json"})
    manifest = _bundle_manifest(files, include_cohort=include_cohort)
    paths["bundle_manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


def verify_agent_release_bundle(bundle_dir: Path) -> dict[str, Any]:
    existing_files = {path.name for path in bundle_dir.iterdir() if path.is_file()}
    missing_required = [name for name in REQUIRED_FILES if name not in existing_files]
    forbidden_file_hits = sorted(name for name in existing_files if name in FORBIDDEN_FILENAMES)
    forbidden_content_hits: list[dict[str, str]] = []

    for path in bundle_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in FORBIDDEN_CONTENT_MARKERS:
            if marker in text:
                forbidden_content_hits.append({"file": path.name, "marker": marker})

    return {
        "bundle_dir": bundle_dir.name,
        "passed": not missing_required and not forbidden_file_hits and not forbidden_content_hits,
        "missing_required": missing_required,
        "forbidden_file_hits": forbidden_file_hits,
        "forbidden_content_hits": forbidden_content_hits,
    }


def doctor_agent_release_bundle(bundle_dir: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    manifest_path = bundle_dir / "bundle_manifest.json"
    template_path = bundle_dir / "console_answers.template.json"
    existing_files = {path.name for path in bundle_dir.iterdir() if path.is_file()}
    missing_required = [name for name in REQUIRED_FILES if name not in existing_files]
    forbidden_file_hits = sorted(name for name in existing_files if name in FORBIDDEN_FILENAMES)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    template = json.loads(template_path.read_text(encoding="utf-8")) if template_path.exists() else {}
    release_file_names = set(REQUIRED_FILES) | set(manifest.get("files", []))
    scanned_release_files = sorted(name for name in release_file_names if (bundle_dir / name).is_file())
    ignored_runtime_files = sorted(existing_files - set(scanned_release_files) - set(FORBIDDEN_FILENAMES))
    forbidden_content_hits: list[dict[str, str]] = []

    for name in scanned_release_files:
        path = bundle_dir / name
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in FORBIDDEN_CONTENT_MARKERS:
            if marker in text:
                forbidden_content_hits.append({"file": name, "marker": marker})

    entrypoints = manifest.get("entrypoints", {})
    entrypoint_mismatches = {
        key: {"expected": expected, "actual": entrypoints.get(key)}
        for key, expected in EXPECTED_ENTRYPOINTS.items()
        if entrypoints.get(key) != expected
    }
    template_required = [
        "owner",
        "request",
        "talent_name",
        "gender",
        "initial_goal",
        "cycle_note",
        "post_hire_mode",
        "swarm_objective",
        "team_objective",
    ]
    missing_template_fields = [field for field in template_required if field not in template]
    post_hire_mode = template.get("post_hire_mode")
    local_policy_passed = (
        manifest.get("contains_private_runtime_state") is False
        and manifest.get("llm_policy") == "application_engine_not_identity"
        and not forbidden_file_hits
        and not forbidden_content_hits
        and "보스 승인 없는 외부 업로드 금지" in manifest.get("guardrails", [])
    )
    checks = {
        "required_files": {
            "passed": not missing_required,
            "missing": missing_required,
        },
        "entrypoints": {
            "passed": not entrypoint_mismatches,
            "available": sorted(entrypoints.keys()),
            "mismatches": entrypoint_mismatches,
        },
        "console_template": {
            "passed": not missing_template_fields
            and post_hire_mode in {"single", "projection_swarm", "specialist_team"},
            "missing_fields": missing_template_fields,
            "post_hire_mode": post_hire_mode,
        },
        "local_only_policy": {
            "passed": local_policy_passed,
            "contains_private_runtime_state": manifest.get("contains_private_runtime_state"),
            "llm_policy": manifest.get("llm_policy"),
            "forbidden_file_hits": forbidden_file_hits,
            "forbidden_content_hits": forbidden_content_hits,
            "scanned_release_files": scanned_release_files,
            "ignored_runtime_file_count": len(ignored_runtime_files),
        },
    }
    report = {
        "schema": DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "bundle_dir": bundle_dir.name,
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
        "recommended_commands": [
            ".\\doctor.ps1",
            ".\\start_console.ps1 -Answers .\\console_answers.template.json",
            ".\\chat_agent.ps1 -Message '<message>'",
            ".\\run_agent.ps1 -Task '<task>'",
            ".\\run_job_cycle.ps1 -JobSpec .\\job_spec.template.json -Score 94",
            ".\\assemble_specialist_team.ps1",
            ".\\run_specialist_team_cycle.ps1 -Score 94",
        ],
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def package_agent_release_bundle(
    bundle_dir: Path,
    *,
    output_zip: Path | None = None,
) -> dict[str, Path]:
    bundle_verification = verify_agent_release_bundle(bundle_dir)
    if not bundle_verification["passed"]:
        raise ValueError(f"Bundle verification failed: {bundle_verification}")

    archive = output_zip or bundle_dir.with_suffix(".zip")
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for path in sorted(bundle_dir.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(bundle_dir).as_posix()
            zip_file.write(path, arcname)

    sha256 = _sha256_file(archive)
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    checksum.write_text(f"{sha256}  {archive.name}\n", encoding="utf-8")

    archive_files = []
    with zipfile.ZipFile(archive, "r") as zip_file:
        archive_files = sorted(zip_file.namelist())

    package_manifest = archive.with_suffix(".package_manifest.json")
    package_manifest.write_text(
        json.dumps(
            {
                "schema": PACKAGE_SCHEMA,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "archive": archive.name,
                "sha256": sha256,
                "checksum": checksum.name,
                "archive_files": archive_files,
                "source_bundle_verification": bundle_verification,
                "public_distribution_ready": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "archive": archive,
        "checksum": checksum,
        "package_manifest": package_manifest,
    }


def verify_agent_release_archive(zip_path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    actual_sha256 = _sha256_file(zip_path)
    checksum_matches = expected_sha256 is None or actual_sha256 == expected_sha256
    forbidden_content_hits: list[dict[str, str]] = []
    forbidden_file_hits: list[str] = []
    absolute_path_hits: list[str] = []

    with zipfile.ZipFile(zip_path, "r") as zip_file:
        archive_files = sorted(zip_file.namelist())
        missing_required = [name for name in REQUIRED_FILES if name not in archive_files]
        for member in archive_files:
            member_name = Path(member).name
            if member.startswith("/") or ":\\" in member or member.startswith("\\"):
                absolute_path_hits.append(member)
            if member_name in FORBIDDEN_FILENAMES:
                forbidden_file_hits.append(member)
            try:
                text = zip_file.read(member).decode("utf-8")
            except UnicodeDecodeError:
                continue
            for marker in FORBIDDEN_CONTENT_MARKERS:
                if marker in text:
                    forbidden_content_hits.append({"file": member, "marker": marker})

    return {
        "archive": str(zip_path),
        "sha256": actual_sha256,
        "checksum_matches": checksum_matches,
        "archive_files": archive_files,
        "passed": (
            checksum_matches
            and not missing_required
            and not forbidden_file_hits
            and not forbidden_content_hits
            and not absolute_path_hits
        ),
        "missing_required": missing_required,
        "forbidden_file_hits": forbidden_file_hits,
        "forbidden_content_hits": forbidden_content_hits,
        "absolute_path_hits": absolute_path_hits,
    }


def _install_id_from_archive(zip_path: Path) -> str:
    name = zip_path.stem
    if name.endswith(".tar"):
        name = Path(name).stem
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in name)


def install_agent_release_package(
    archive_path: Path,
    *,
    install_root: Path,
    expected_sha256: str | None = None,
) -> dict[str, Path]:
    verification = verify_agent_release_archive(archive_path, expected_sha256=expected_sha256)
    if not verification["passed"]:
        raise ValueError(f"Archive verification failed: {verification}")

    install_id = _install_id_from_archive(archive_path)
    target_root = (install_root / "agents" / install_id).resolve()
    install_root_resolved = install_root.resolve()
    if install_root_resolved not in target_root.parents:
        raise ValueError("Install target escaped install root")

    target_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as zip_file:
        for member in zip_file.namelist():
            member_path = Path(member)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe archive member: {member}")
            target_path = (target_root / member_path).resolve()
            if target_root not in target_path.parents and target_path != target_root:
                raise ValueError(f"Archive member escaped install target: {member}")
            if member.endswith("/"):
                target_path.mkdir(parents=True, exist_ok=True)
                continue
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(zip_file.read(member))

    installed_files = sorted(set(verification["archive_files"]) | {"installed_agent_manifest.json"})
    entrypoints = {
        "doctor": "doctor.ps1",
        "start_console": "start_console.ps1",
        "console_answers_template": "console_answers.template.json",
        "chat_agent": "chat_agent.ps1",
        "run_agent": "run_agent.ps1",
        "run_job": "run_job.ps1",
        "run_job_cycle": "run_job_cycle.ps1",
        "run_dataflow_job": "run_dataflow_job.ps1",
        "assemble_projection_swarm": "assemble_projection_swarm.ps1",
        "run_projection_swarm_cycle": "run_projection_swarm_cycle.ps1",
        "assemble_specialist_team": "assemble_specialist_team.ps1",
        "run_specialist_team_cycle": "run_specialist_team_cycle.ps1",
        "agent_manifest": "agent_manifest.json",
        "learning_ledger": "learning_ledger.json",
        "language_development_program": "language_development_program.json",
        "hiring_dossier": "hiring_dossier.json",
        "hiring_dossier_markdown": "HIRING_DOSSIER.ko.md",
        "job_spec_template": "job_spec.template.json",
        "dataflow_job_template": "dataflow_job.template.json",
    }
    if "memory_substrate.json" in installed_files:
        entrypoints["memory_substrate"] = "memory_substrate.json"
    manifest = {
        "schema": INSTALLED_SCHEMA,
        "installed_at_utc": datetime.now(timezone.utc).isoformat(),
        "install_id": install_id,
        "source_archive": archive_path.name,
        "source_sha256": verification["sha256"],
        "archive_verification": verification,
        "installed_files": installed_files,
        "entrypoints": entrypoints,
        "status": "installed",
    }
    installed_manifest = target_root / "installed_agent_manifest.json"
    installed_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "install_root": install_root,
        "target_root": target_root,
        "installed_manifest": installed_manifest,
    }
