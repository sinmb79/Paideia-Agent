from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.memory_substrate import build_memory_substrate, run_chat_turn_from_employment, write_memory_substrate


AGENT_PROGRAM_SCHEMA = "ai22b-paideia-agent-program/v1"
INSTALL_KIT_SCHEMA = "ai22b-paideia-agent-install-kit/v1"
PROGRAM_DOCTOR_SCHEMA = "ai22b-paideia-agent-program-doctor/v1"
DEFAULT_AGENT_PROGRAM_NAME = "Paideia Agent"
DEFAULT_AGENT_PROGRAM_NAME_KO = "Paideia Agent"
DEFAULT_AGENT_PROGRAM_FILE = "22b_paideia_agent_program.json"
DEFAULT_CHAT_SCRIPT = "start_paideia_chat.ps1"
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

Write-Host "Paideia Agent - Codex bridge chat"
Write-Host "종료하려면 exit 또는 quit 를 입력하세요."
Write-Host "Codex가 로컬 교육기록, 추론기보, 대화기록을 읽고, 연결된 LLM은 언어/추론 엔진으로만 사용됩니다."
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

    python @ArgsList | Out-Null
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


def _doctor_script() -> str:
    return """param(
    [string]$Program = ".\\22b_paideia_agent_program.json",
    [string]$Output = ".\\paideia_doctor_report.json"
)

$ErrorActionPreference = "Stop"
python -m ai22b.talent_foundry.cli doctor-agent-program --program $Program --output $Output
Write-Host $Output
"""


def _onboarding_template(program_name: str, agent_name: str) -> dict[str, Any]:
    return {
        "schema": "ai22b-paideia-onboarding-template/v1",
        "program": program_name,
        "agent_name": agent_name,
        "first_run": {
            "run_doctor_first": True,
            "open_chat_script": DEFAULT_CHAT_SCRIPT,
            "default_llm_mode": "offline",
            "live_llm_requires_api_quota": True,
            "learn_from_chat_default": False,
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
            "이 프로그램은 추론만 배우는거야, 아니면 다른 것도 육성하는거야?",
            "최근 대화에서 배운 점을 어떻게 기록해?",
        ],
    }


def _install_readme(program_name: str, agent_name: str) -> str:
    return f"""# {program_name} Install Kit

This folder is a self-contained local install kit for the hired AI talent `{agent_name}`.

## What This Is

Paideia Agent is not just a chatbot profile. It is a local AI education/runtime package:

- local education records
- learning ledger
- reasoning kibo / Ariadne Thread
- memory substrate
- Codex bridge chat script
- adapter manifests for Hermes-style and OpenClaw-style runtimes

The connected LLM is only the language and reasoning engine. Identity and learned behavior come from the local files in this kit.

## First Run

```powershell
powershell -ExecutionPolicy Bypass -File .\\doctor_paideia.ps1
powershell -ExecutionPolicy Bypass -File .\\start_paideia_chat.ps1
```

Use live LLM mode only after API quota and privacy expectations are clear:

```powershell
powershell -ExecutionPolicy Bypass -File .\\start_paideia_chat.ps1 -LiveLlm -LearnFromChat
```

## Design Notes

Paideia benchmarks useful ideas from Hermes/OpenClaw-style agents: installable local runtime, profiles, skills, persistent memory, and channel adapters. It keeps risky parts disabled by default: external gateway channels, unreviewed community skills, full session replay, and unbounded memory injection.
"""


def _adapter_manifests(agent_name: str) -> dict[str, Any]:
    shared_contract = {
        "identity_source": "local_agent_program_manifest",
        "memory_source": "learning_ledger + reasoning_kibo + memory_substrate",
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
        "추론기보는 Paideia가 길러낸 여러 결과 중 하나입니다.\n\n"
        "이 교육센터가 프로그래밍해서 육성해야 하는 축은 이렇습니다.\n"
        + "\n".join(axis_lines)
        + "\n\n"
        "즉, grham-쥬니어 같은 개별 AI 인재는 지식만 주입받는 것이 아니라 언어, 사회성, 직업 전문성, "
        "도구 사용, 안전 경계, 시뮬레이션 경험을 단계별로 통과하면서 성장해야 합니다. "
        "추론기보는 그 전체 성장 과정에서 형성된 문제 해결의 길입니다."
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
    script_path = output_path.parent / DEFAULT_CHAT_SCRIPT
    script_path.write_text(_chat_script(), encoding="utf-8")

    program = {
        "schema": AGENT_PROGRAM_SCHEMA,
        "created_at_utc": _now(),
        "name": program_name,
        "name_ko": program_name_ko,
        "tagline": "A local AI education center that raises agent talents through staged growth, simulation, and verified memory.",
        "tagline_ko": "단계별 성장, 시뮬레이션, 검증된 기억으로 AI 인재를 육성하는 로컬 AI 교육센터.",
        "name_rationale": {
            "paideia": "holistic education and formation, broader than a reasoning module",
            "ariadne_thread": "the reasoning-kibo path that helps an agent find a route through memory and tasks",
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
            "agent_identity_role": "local_learning_data_reasoning_kibo_and_employment_record",
            "answer_flow": [
                "Codex reads local identity, learning ledger, reasoning kibo, memory substrate, and recent chat logs.",
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
        "entrypoints": {
            "employment_record": _rel(employment_record_path, output_path.parent),
            "agent_manifest": _rel(agent_manifest_path, output_path.parent),
            "chat_script": DEFAULT_CHAT_SCRIPT,
            "chat_command": (
                "ai22b-talent-foundry run-agent-program-chat "
                f"--program {output_path.name} --message <message> --learn-from-chat"
            ),
            "offline_chat": "run-agent-program-chat --llm-mode offline",
            "live_llm_chat": "run-agent-program-chat --llm-mode live --learn-from-chat",
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
            "onboarding_template": DEFAULT_ONBOARDING_TEMPLATE,
            "start_chat_script": DEFAULT_CHAT_SCRIPT,
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

    onboarding = _onboarding_template(program_name, str(program.get("agent", {}).get("name") or "unknown"))
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
            "start_chat": DEFAULT_CHAT_SCRIPT,
            "program": program_path.name,
            "onboarding_template": DEFAULT_ONBOARDING_TEMPLATE,
            "adapter_manifests": "adapter_manifests",
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
    required_entrypoints = ["employment_record", "agent_manifest", "chat_script"]
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
    }
    _write_json(output_path, chat)
    return chat
