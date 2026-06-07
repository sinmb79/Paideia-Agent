from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_identity_card import (
    build_agent_id_card_payload,
    build_agent_identity_layer_envelope,
    build_agent_warrent_connector_kit,
    build_agent_warrent_registration_request,
)
from ai22b.talent_foundry.llm_onboarding import build_llm_connection_profile, build_llm_live_setup_guide
from ai22b.talent_foundry.llm_runtime import build_llm_provider_preflight, build_llm_runtime_config
from ai22b.talent_foundry.memory_substrate import build_memory_substrate, run_chat_turn_from_employment, write_memory_substrate
from ai22b.talent_foundry.onboarding_choices import (
    CHAT_SURFACE_CATALOG,
    DEFAULT_CHAT_SURFACE_ID,
    LLM_SERVICE_CATALOG,
    resolve_chat_surface,
    resolve_llm_service,
)
from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model


AGENT_PROGRAM_SCHEMA = "ai22b-paideia-agent-program/v1"
INSTALL_KIT_SCHEMA = "ai22b-paideia-agent-install-kit/v1"
PROGRAM_DOCTOR_SCHEMA = "ai22b-paideia-agent-program-doctor/v1"
KIT_FIRST_RUN_DOCTOR_SCHEMA = "ai22b-paideia-kit-first-run-doctor/v1"
PROGRAM_CHAT_STATUS_CARD_SCHEMA = "ai22b-paideia-agent-program-chat-status-card/v1"
DEFAULT_AGENT_PROGRAM_NAME = "Paideia Agent"
DEFAULT_AGENT_PROGRAM_NAME_KO = "Paideia Agent"
DEFAULT_AGENT_PROGRAM_FILE = "22b_paideia_agent_program.json"
DEFAULT_CHAT_SCRIPT = "start_paideia_chat.ps1"
DEFAULT_ONBOARDING_TEMPLATE = "paideia_onboarding.template.json"
DEFAULT_INSTALL_MANIFEST = "paideia_agent_install_manifest.json"
DEFAULT_DOCTOR_SCRIPT = "doctor_paideia.ps1"
DEFAULT_LLM_CONNECTION_PROFILE = "llm_connection_profile.json"
DEFAULT_LLM_LIVE_SETUP_GUIDE = "llm_live_setup_guide.json"
DEFAULT_RUNTIME_READINESS = "paideia_runtime_readiness.json"
DEFAULT_KIT_FIRST_RUN_DOCTOR = "paideia_kit_first_run_doctor.json"
DEFAULT_KIT_FIRST_RUN_CHAT = "paideia_first_run_chat_smoke.json"


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

```powershell
powershell -ExecutionPolicy Bypass -File .\\doctor_paideia.ps1
powershell -ExecutionPolicy Bypass -File .\\start_paideia_chat.ps1
```

The doctor checks `llm_connection_profile.json` and `paideia_runtime_readiness.json` when they are present. These files describe the selected LLM engine, no-network preflight result, first-run smoke commands, and fail-closed behavior before any live provider call is attempted.

To let the selected LLM service answer when it is available, use auto mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\\start_paideia_chat.ps1 -LlmMode auto -LearnFromChat
```

Use live LLM mode only after API quota and privacy expectations are clear:

```powershell
powershell -ExecutionPolicy Bypass -File .\\start_paideia_chat.ps1 -LiveLlm -LearnFromChat
```

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


def _build_agent_program_chat_status_card(
    *,
    program: dict[str, Any],
    chat: dict[str, Any],
    program_path: Path,
    output_path: Path,
    employment_record_path: Path,
    selected_llm_mode: str,
    selected_learn: bool,
    llm_model: str | None,
) -> dict[str, Any]:
    chat_runtime = chat.get("chat_runtime_status_card", {})
    if not isinstance(chat_runtime, dict):
        chat_runtime = {}
    memory_lifecycle = chat_runtime.get("memory_lifecycle", {})
    if not isinstance(memory_lifecycle, dict):
        memory_lifecycle = {}
    provider_preflight = chat.get("llm_provider_preflight", {})
    if not isinstance(provider_preflight, dict):
        provider_preflight = {}
    fallback = chat_runtime.get("fallback", {})
    if not isinstance(fallback, dict):
        fallback = {}
    learning = chat_runtime.get("learning", {})
    if not isinstance(learning, dict):
        learning = {}
    selected_service = program.get("onboarding_flow", {}).get("selected_llm_service", {})
    if not isinstance(selected_service, dict):
        selected_service = {}
    selected_surface = program.get("onboarding_flow", {}).get("selected_chat_surface", {})
    if not isinstance(selected_surface, dict):
        selected_surface = {}

    chat_status = chat.get("chat_status")
    chat_runtime_status = chat_runtime.get("status")
    stored_private_trace = chat.get("stored_private_reasoning_trace")
    if chat_status == "needs_configuration" or chat_runtime_status == "needs_configuration":
        status = "needs_configuration"
    elif (
        chat_status == "completed"
        and chat_runtime.get("schema") == "paideia-chat-runtime-status-card/v1"
        and stored_private_trace is False
    ):
        status = "completed_verified"
    elif chat_status == "completed":
        status = "completed_needs_runtime_review"
    else:
        status = "needs_review"

    return {
        "schema": PROGRAM_CHAT_STATUS_CARD_SCHEMA,
        "created_at_utc": _now(),
        "status": status,
        "command_surface": "run-agent-program-chat",
        "program": {
            "schema": program.get("schema"),
            "name": program.get("name"),
            "name_ko": program.get("name_ko"),
            "program_file": program_path.name,
            "output_file": output_path.name,
            "employment_record": employment_record_path.name,
            "profile_isolation": program.get("security", {}).get("profile_isolation"),
        },
        "llm_runtime": {
            "selected_mode": selected_llm_mode,
            "selected_model": llm_model,
            "selected_service_id": selected_service.get("service_id") or selected_service.get("id"),
            "selected_engine": selected_service.get("engine"),
            "reply_generation_mode": chat.get("reply_generation_mode"),
            "identity_policy": program.get("runtime_topology", {}).get("connected_llm_role"),
            "application_engine_not_identity": True,
        },
        "chat_surface": {
            "selected_chat_surface": selected_surface.get("id"),
            "active_operator": chat.get("active_operator"),
            "conversation_intent": chat.get("conversation_intent"),
            "chat_status": chat_status,
            "chat_runtime_status": chat_runtime_status,
            "chat_runtime_status_card_schema": chat_runtime.get("schema"),
        },
        "provider_gate": {
            "preflight_status": provider_preflight.get("status"),
            "live_check_performed": provider_preflight.get("live_check_performed"),
            "network_call_made_by_preflight": provider_preflight.get("network_call_made_by_preflight"),
            "fallback_used": fallback.get("used"),
            "fallback_presented_as_live": fallback.get("presented_as_live"),
        },
        "memory_route": {
            "reasoning_ledger_display_name": program.get("reasoning_kibo_contract", {}).get("display_name"),
            "bounded_selected_context": program.get("security", {}).get("memory_replay_policy"),
            "memory_lifecycle_schema": memory_lifecycle.get("schema"),
            "memory_lifecycle_status": memory_lifecycle.get("status"),
            "selected_count": memory_lifecycle.get("selected_count"),
            "quarantined_excluded": memory_lifecycle.get("quarantined_excluded"),
        },
        "learning": {
            "learn_from_chat_requested": selected_learn,
            "decision": learning.get("decision"),
            "automatic_promotion_performed": chat.get("learning_update", {}).get("automatic_promotion_performed")
            if isinstance(chat.get("learning_update"), dict)
            else False,
            "review_required": learning.get("review_required"),
        },
        "public_safe": {
            "program_wrapper_network_call_performed": False,
            "program_wrapper_subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace_stored": stored_private_trace is not False,
            "full_session_replay_saved": False,
            "absolute_paths_exported": False,
        },
        "evidence": {
            "chat_runtime_status_card_present": chat_runtime.get("schema") == "paideia-chat-runtime-status-card/v1",
            "memory_lifecycle_status_card_present": bool(memory_lifecycle.get("schema")),
            "stored_private_reasoning_trace": stored_private_trace,
            "chat_execution_trace_count": len(chat.get("chat_execution_trace", []))
            if isinstance(chat.get("chat_execution_trace"), list)
            else 0,
            "last_trace_action": chat.get("chat_execution_trace", [{}])[-1].get("action")
            if isinstance(chat.get("chat_execution_trace"), list) and chat.get("chat_execution_trace")
            else None,
        },
        "next_actions": [
            "Review this card before presenting the chat as a verified installed-agent conversation.",
            "Use live mode only after the selected provider profile and privacy posture are ready.",
            "Promote chat learning only from reviewable summaries, never hidden chain-of-thought.",
        ],
    }


def _optional_cli_arg(flag: str, value: Any) -> list[str]:
    if value is None or str(value).strip() == "":
        return []
    return [flag, str(value)]


def _command_text(parts: list[str]) -> str:
    return " ".join(parts)


def _runtime_config_from_employment(employment: dict[str, Any]) -> dict[str, Any]:
    runtime = employment.get("llm_runtime", {}) if isinstance(employment.get("llm_runtime"), dict) else {}
    llm_service = employment.get("llm_service", {}) if isinstance(employment.get("llm_service"), dict) else {}
    engine = runtime.get("engine") or llm_service.get("engine") or "deterministic_local"
    return build_llm_runtime_config(
        engine=str(engine),
        service=runtime.get("service") or llm_service.get("service_id") or str(engine),
        model=runtime.get("model") or llm_service.get("selected_model"),
        model_path=runtime.get("model_path") or llm_service.get("selected_model_path"),
    )


def _build_kit_runtime_readiness(
    *,
    employment: dict[str, Any],
    program: dict[str, Any],
    llm_connection_profile: dict[str, Any] | None,
    output_path: Path,
) -> dict[str, Any]:
    runtime_config = _runtime_config_from_employment(employment)
    engine = runtime_config["engine"]
    model = runtime_config.get("model")
    model_path = runtime_config.get("model_path")
    offline_preflight = build_llm_provider_preflight(runtime_config, llm_mode="offline", llm_model=model)
    live_preflight = build_llm_provider_preflight(runtime_config, llm_mode="live", llm_model=model)
    verification_sequence = (
        llm_connection_profile.get("verification_sequence", [])
        if isinstance(llm_connection_profile, dict)
        else []
    )
    verification_ids = [str(item.get("id")) for item in verification_sequence if isinstance(item, dict)]
    provider_args = [
        "--llm-engine",
        engine,
        *_optional_cli_arg("--llm-model", model),
        *_optional_cli_arg("--llm-model-path", model_path),
    ]
    checks = [
        {
            "id": "llm_connection_profile_present",
            "passed": isinstance(llm_connection_profile, dict)
            and llm_connection_profile.get("schema") == "paideia-llm-connection-profile/v1",
        },
        {
            "id": "connection_profile_public_safe",
            "passed": isinstance(llm_connection_profile, dict)
            and llm_connection_profile.get("public_safe", {}).get("network_call_performed") is False
            and llm_connection_profile.get("public_safe", {}).get("secret_values_exported") is False
            and llm_connection_profile.get("public_safe", {}).get("raw_provider_payload_saved") is False,
        },
        {
            "id": "identity_boundary",
            "passed": runtime_config.get("identity_policy") == "application_engine_not_identity",
        },
        {
            "id": "offline_preflight_no_network",
            "passed": offline_preflight.get("network_call_made_by_preflight") is False
            and offline_preflight.get("live_check_performed") is False,
        },
        {
            "id": "live_preflight_fail_closed_no_network",
            "passed": live_preflight.get("network_call_made_by_preflight") is False
            and live_preflight.get("live_check_performed") is False
            and live_preflight.get("live_check_requires_explicit_flag") is True,
        },
        {
            "id": "verification_sequence_covers_runtime",
            "passed": {
                "no_network_doctor",
                "explicit_live_provider_check",
                "live_agent_runtime_smoke",
                "chat_runtime_smoke",
            }
            <= set(verification_ids),
        },
    ]
    readiness = {
        "schema": "ai22b-paideia-kit-runtime-readiness/v1",
        "created_at_utc": _now(),
        "program": program.get("name"),
        "agent": program.get("agent"),
        "selected_llm_service": program.get("onboarding_flow", {}).get("selected_llm_service"),
        "selected_chat_surface": program.get("onboarding_flow", {}).get("selected_chat_surface"),
        "llm_connection_profile": {
            "entrypoint": program.get("entrypoints", {}).get("llm_connection_profile"),
            "schema": llm_connection_profile.get("schema") if isinstance(llm_connection_profile, dict) else None,
            "status": llm_connection_profile.get("status") if isinstance(llm_connection_profile, dict) else None,
            "public_safe": llm_connection_profile.get("public_safe", {}) if isinstance(llm_connection_profile, dict) else {},
        },
        "runtime_config": {
            "schema": runtime_config["schema"],
            "engine": engine,
            "service": runtime_config.get("service"),
            "model": model,
            "model_path": model_path,
            "identity_policy": runtime_config.get("identity_policy"),
            "network_access": runtime_config.get("network_access"),
            "private_reasoning_trace": runtime_config.get("private_reasoning_trace"),
        },
        "provider_preflight": {
            "offline": offline_preflight,
            "live": live_preflight,
        },
        "first_run_commands": {
            "doctor_program": _command_text(
                [
                    "ai22b-talent-foundry",
                    "doctor-agent-program",
                    "--program",
                    DEFAULT_AGENT_PROGRAM_FILE,
                    "--output",
                    "paideia_doctor_report.json",
                ]
            ),
            "provider_doctor_no_network": _command_text(
                [
                    "ai22b-talent-foundry",
                    "doctor-llm-provider",
                    *provider_args,
                    "--output",
                    "llm_provider_doctor.json",
                ]
            ),
            "runtime_readiness_suite_no_network": _command_text(
                [
                    "ai22b-talent-foundry",
                    "doctor-llm-live-readiness",
                    *provider_args,
                    "--output-dir",
                    "llm_live_readiness",
                ]
            ),
            "offline_chat": _command_text(
                [
                    "ai22b-talent-foundry",
                    "run-agent-program-chat",
                    "--program",
                    DEFAULT_AGENT_PROGRAM_FILE,
                    "--message",
                    "\"안녕, 오늘 맡길 업무를 같이 정리해보자.\"",
                    "--llm-mode",
                    "offline",
                    "--output",
                    "paideia_chat_offline.json",
                ]
            ),
            "live_chat_template": _command_text(
                [
                    "ai22b-talent-foundry",
                    "run-agent-program-chat",
                    "--program",
                    DEFAULT_AGENT_PROGRAM_FILE,
                    "--message",
                    "\"안녕, 오늘 맡길 업무를 같이 정리해보자.\"",
                    "--llm-mode",
                    "live",
                    *_optional_cli_arg("--llm-model", model),
                    "--output",
                    "paideia_chat_live.json",
                ]
            ),
        },
        "fail_closed_expectation": {
            "missing_key_or_local_server_status": "needs_configuration",
            "live_provider_requires_explicit_flag": True,
            "tool_execution_before_provider_ready": False,
            "workspace_artifacts_before_provider_ready": False,
            "learning_promotion_before_review": False,
        },
        "public_safe": {
            "network_call_performed": False,
            "live_provider_called": False,
            "localhost_called": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
        "checks": checks,
    }
    readiness["passed"] = all(check["passed"] for check in checks)
    readiness["status"] = "passed" if readiness["passed"] else "needs_review"
    _write_json(output_path, readiness)
    return readiness


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
                "developmental_ecology": entrypoints.get("developmental_ecology", "developmental_ecology.json"),
                "life_trace": entrypoints.get("life_trace", "life_trace.jsonl"),
                "growth_profile": entrypoints.get("growth_profile", "growth_profile.json"),
                "grade_learning_records": entrypoints.get(
                    "grade_learning_records",
                    "grade_learning_records.json",
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
                "onboarding_choice_manifest",
                "education_to_hiring",
                "hiring_dossier_review",
                "agent_id_card_payload_export",
                "health_check",
                "first_chat_or_dataflow_job",
            ],
            "llm_service_catalog": LLM_SERVICE_CATALOG,
            "chat_surface_catalog": CHAT_SURFACE_CATALOG,
            "role_model_catalog": [summarize_role_model(item) for item in list_role_models()],
            "choice_manifest": {
                "schema": "paideia-onboarding-choice-manifest/v1",
                "default_filename": "onboarding_choice_manifest.json",
                "purpose": "records selected LLM, chat surface, curriculum, storage, runtime, and Agent ID policy",
                "privacy": {
                    "raw_local_model_path_saved": False,
                    "raw_private_curriculum_dir_saved": False,
                    "external_registration_performed": False,
                },
            },
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
            "chat_script": DEFAULT_CHAT_SCRIPT,
            "chat_command": (
                "ai22b-talent-foundry run-agent-program-chat "
                f"--program {output_path.name} --message <message> --learn-from-chat"
            ),
            "offline_chat": "run-agent-program-chat --llm-mode offline",
            "live_llm_chat": "run-agent-program-chat --llm-mode live --learn-from-chat",
            "hiring_dossier": "hiring_dossier.json",
            "hiring_dossier_markdown": "HIRING_DOSSIER.ko.md",
            "agent_id_card_payload": "agent_id_card_payload.json",
            "agent_identity_envelope": "agent_identity_envelope.json",
        },
        "adapter_manifests": _adapter_manifests(str(agent.get("name") or "unknown")),
        "security": {
            "local_first": True,
            "private_data_upload": "forbidden_by_default",
            "external_channels_enabled": False,
            "community_skills_enabled": False,
            "gateway_binding": "disabled_until_explicit_loopback_or_private_network_configuration",
            "agent_identity_layer": "Agent_warrent ail.v1 local envelope; external registration requires explicit owner action",
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
    llm_profile_name = entrypoints.get("llm_connection_profile") or employment.get("llm_connection_profile", {}).get(
        "entrypoint"
    )
    if llm_profile_name:
        program["entrypoints"]["llm_connection_profile"] = str(llm_profile_name)
    llm_live_setup_guide_name = entrypoints.get("llm_live_setup_guide") or employment.get(
        "llm_live_setup_guide", {}
    ).get("entrypoint")
    if llm_live_setup_guide_name:
        program["entrypoints"]["llm_live_setup_guide"] = str(llm_live_setup_guide_name)
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
        employment.get("source", {}).get("installed_manifest", "installed_agent_manifest.json"),
        entrypoints.get("agent_manifest", "agent_manifest.json"),
        entrypoints.get("learning_ledger", "learning_ledger.json"),
        entrypoints.get("memory_substrate", "memory_substrate.json"),
        entrypoints.get("language_development_program", "language_development_program.json"),
        entrypoints.get("llm_connection_profile", DEFAULT_LLM_CONNECTION_PROFILE),
        entrypoints.get("llm_live_setup_guide", DEFAULT_LLM_LIVE_SETUP_GUIDE),
        entrypoints.get("agent_warrent_registration_request", "agent_warrent_registration_request.json"),
    ]
    for name in dict.fromkeys(required_names):
        copied_name = _copy_if_present(source_root / name, output_dir / name)
        if copied_name:
            copied[name] = copied_name

    employment_copy_path = output_dir / "employment_record.json"
    llm_profile_name = entrypoints.get("llm_connection_profile") or DEFAULT_LLM_CONNECTION_PROFILE
    llm_profile_path = output_dir / llm_profile_name
    if not llm_profile_path.exists():
        embedded_profile = employment.get("llm_connection_profile")
        if isinstance(embedded_profile, dict) and embedded_profile.get("schema") == "paideia-llm-connection-profile/v1":
            _write_json(llm_profile_path, embedded_profile)
            copied[llm_profile_name] = "generated_from_employment_record_embedded_profile"
        else:
            runtime = employment.get("llm_runtime", {}) if isinstance(employment.get("llm_runtime"), dict) else {}
            llm_service = employment.get("llm_service", {}) if isinstance(employment.get("llm_service"), dict) else {}
            chat_surface = employment.get("chat_surface", {}) if isinstance(employment.get("chat_surface"), dict) else {}
            profile = build_llm_connection_profile(
                llm_service=llm_service.get("service_id"),
                llm_engine=runtime.get("engine") or llm_service.get("engine") or "deterministic_local",
                llm_model=runtime.get("model") or llm_service.get("selected_model"),
                llm_model_path=runtime.get("model_path") or llm_service.get("selected_model_path"),
                chat_surface=chat_surface.get("id") or DEFAULT_CHAT_SURFACE_ID,
                output_path=llm_profile_path,
            )
            employment.setdefault("entrypoints", {})["llm_connection_profile"] = llm_profile_name
            employment["llm_connection_profile"] = {
                "schema": profile["schema"],
                "entrypoint": llm_profile_name,
                "selected_engine": profile["selected_llm_service"]["engine"],
                "status": profile["status"],
                "public_safe": profile["public_safe"],
            }
            _write_json(employment_copy_path, employment)
            copied[llm_profile_name] = "generated_no_network_from_employment_llm_runtime"
    if llm_profile_path.exists() and not employment.get("entrypoints", {}).get("llm_connection_profile"):
        employment.setdefault("entrypoints", {})["llm_connection_profile"] = llm_profile_name
        _write_json(employment_copy_path, employment)
    llm_live_setup_guide_name = entrypoints.get("llm_live_setup_guide") or DEFAULT_LLM_LIVE_SETUP_GUIDE
    llm_live_setup_guide_path = output_dir / llm_live_setup_guide_name
    if not llm_live_setup_guide_path.exists():
        runtime = employment.get("llm_runtime", {}) if isinstance(employment.get("llm_runtime"), dict) else {}
        llm_service = employment.get("llm_service", {}) if isinstance(employment.get("llm_service"), dict) else {}
        chat_surface = employment.get("chat_surface", {}) if isinstance(employment.get("chat_surface"), dict) else {}
        guide = build_llm_live_setup_guide(
            llm_service=llm_service.get("service_id"),
            llm_engine=runtime.get("engine") or llm_service.get("engine") or "deterministic_local",
            llm_model=runtime.get("model") or llm_service.get("selected_model"),
            llm_model_path=runtime.get("model_path") or llm_service.get("selected_model_path"),
            chat_surface=chat_surface.get("id") or DEFAULT_CHAT_SURFACE_ID,
            output_path=llm_live_setup_guide_path,
        )
        readiness_gate = guide.get("readiness_gate", {}) if isinstance(guide.get("readiness_gate"), dict) else {}
        employment.setdefault("entrypoints", {})["llm_live_setup_guide"] = llm_live_setup_guide_name
        employment["llm_live_setup_guide"] = {
            "schema": guide["schema"],
            "entrypoint": llm_live_setup_guide_name,
            "selected_engine": guide["selected_llm_service"]["engine"],
            "status": guide["status"],
            "requires_explicit_live_check": readiness_gate.get("requires_explicit_live_check"),
            "public_safe": guide["public_safe"],
        }
        _write_json(employment_copy_path, employment)
        copied[llm_live_setup_guide_name] = "generated_no_network_from_employment_llm_runtime"
    if llm_live_setup_guide_path.exists() and not employment.get("entrypoints", {}).get("llm_live_setup_guide"):
        employment.setdefault("entrypoints", {})["llm_live_setup_guide"] = llm_live_setup_guide_name
        _write_json(employment_copy_path, employment)

    optional_patterns = [
        "hiring_dossier.json",
        "HIRING_DOSSIER.ko.md",
        "*_reasoning_kibo.jsonl",
        "*_curriculum_manifest.json",
        "*_assessment_transcript.json",
        "*_grade_learning_records.json",
        "*_developmental_ecology.json",
        "*_life_trace.jsonl",
        "*_growth_profile.json",
        "developmental_ecology.json",
        "life_trace.jsonl",
        "growth_profile.json",
        "grade_learning_records.json",
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
        grade_learning_records_path = output_dir / entrypoints.get(
            "grade_learning_records",
            "grade_learning_records.json",
        )
        grade_learning_records = (
            _read_json(grade_learning_records_path).get("records", [])
            if grade_learning_records_path.exists()
            else []
        )
        substrate = build_memory_substrate(
            agent_manifest=agent_manifest,
            learning_ledger=learning_ledger,
            grade_learning_records=grade_learning_records,
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
    installed_manifest_name = employment.get("source", {}).get("installed_manifest", "installed_agent_manifest.json")
    installed_manifest_path = output_dir / installed_manifest_name
    if installed_manifest_path.exists():
        payload_path = output_dir / "agent_id_card_payload.json"
        envelope_path = output_dir / "agent_identity_envelope.json"
        registration_request_path = output_dir / "agent_warrent_registration_request.json"
        payload = build_agent_id_card_payload(
            installed_manifest_path=installed_manifest_path,
            employment_record_path=output_dir / "employment_record.json",
            output_path=payload_path,
        )
        envelope = build_agent_identity_layer_envelope(
            installed_manifest_path=installed_manifest_path,
            employment_record_path=output_dir / "employment_record.json",
            output_path=envelope_path,
            surface="paideia_agent_install_kit",
            task_ref="paideia-agent-kit-identity",
        )
        registration_request = build_agent_warrent_registration_request(
            installed_manifest_path=installed_manifest_path,
            employment_record_path=output_dir / "employment_record.json",
            owner_key_id="OWNER_KEY_ID_REQUIRED",
            output_path=registration_request_path,
        )
        connector = build_agent_warrent_connector_kit(
            registration_request_path=registration_request_path,
            output_dir=output_dir / "agent_warrent_connector",
        )
        copied[payload_path.name] = "generated_agent_id_card_payload"
        copied[envelope_path.name] = "generated_agent_warrent_ail_v1_envelope"
        copied[registration_request_path.name] = "generated_agent_warrent_registration_request_draft"
        copied["agent_warrent_connector"] = "generated_owner_controlled_agent_warrent_sdk_bridge"
        program["entrypoints"]["agent_id_card_payload"] = payload_path.name
        program["entrypoints"]["agent_identity_envelope"] = envelope_path.name
        program["entrypoints"]["agent_warrent_registration_request"] = registration_request_path.name
        program["entrypoints"]["agent_warrent_connector"] = "agent_warrent_connector/agent_warrent_connector_manifest.json"
        program["installable_runtime"]["agent_identity_layer"] = {
            "payload_schema": payload["schema"],
            "envelope_version": envelope["version"],
            "agent_warrent_repo": envelope["extensions"]["agent_warrent"]["repo_url"],
            "registration_state": envelope["extensions"]["agent_warrent"]["registration_state"],
            "registration_request_schema": registration_request["schema"],
            "registration_request_status": registration_request["status"],
            "registration_request_submit_ready": registration_request["submit_ready"],
            "connector_kit_schema": connector["schema"],
            "connector_kit_status": connector["status"],
            "network_action_performed": False,
        }
        _write_json(program_path, program)

    llm_connection_profile = _read_json(llm_profile_path) if llm_profile_path.exists() else None
    if llm_connection_profile:
        program["entrypoints"]["llm_connection_profile"] = _rel(llm_profile_path, output_dir)
    llm_live_setup_guide = _read_json(llm_live_setup_guide_path) if llm_live_setup_guide_path.exists() else None
    if llm_live_setup_guide:
        program["entrypoints"]["llm_live_setup_guide"] = _rel(llm_live_setup_guide_path, output_dir)
    runtime_readiness_path = output_dir / DEFAULT_RUNTIME_READINESS
    runtime_readiness = _build_kit_runtime_readiness(
        employment=employment,
        program=program,
        llm_connection_profile=llm_connection_profile,
        output_path=runtime_readiness_path,
    )
    copied[runtime_readiness_path.name] = "generated_no_network_kit_runtime_readiness"
    program["entrypoints"]["runtime_readiness"] = runtime_readiness_path.name
    program["installable_runtime"]["runtime_readiness"] = {
        "entrypoint": runtime_readiness_path.name,
        "schema": runtime_readiness["schema"],
        "status": runtime_readiness["status"],
        "selected_engine": runtime_readiness["runtime_config"]["engine"],
        "network_call_performed": False,
        "live_provider_called": False,
    }
    _write_json(program_path, program)

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
    _write_json(output_dir / DEFAULT_ONBOARDING_TEMPLATE, onboarding)
    (output_dir / "README.md").write_text(
        _install_readme(program_name, str(program.get("agent", {}).get("name") or "unknown")),
        encoding="utf-8",
    )
    (output_dir / DEFAULT_DOCTOR_SCRIPT).write_text(_doctor_script(), encoding="utf-8")

    kit_entrypoints = {
        "doctor": DEFAULT_DOCTOR_SCRIPT,
        "start_chat": DEFAULT_CHAT_SCRIPT,
        "program": program_path.name,
        "onboarding_template": DEFAULT_ONBOARDING_TEMPLATE,
        "adapter_manifests": "adapter_manifests",
        "runtime_readiness": DEFAULT_RUNTIME_READINESS,
    }
    if llm_profile_path.exists():
        kit_entrypoints["llm_connection_profile"] = llm_profile_path.name
    if llm_live_setup_guide_path.exists():
        kit_entrypoints["llm_live_setup_guide"] = llm_live_setup_guide_path.name
    if (output_dir / "agent_id_card_payload.json").exists():
        kit_entrypoints["agent_id_card_payload"] = "agent_id_card_payload.json"
    if (output_dir / "agent_identity_envelope.json").exists():
        kit_entrypoints["agent_identity_envelope"] = "agent_identity_envelope.json"
    if (output_dir / "agent_warrent_registration_request.json").exists():
        kit_entrypoints["agent_warrent_registration_request"] = "agent_warrent_registration_request.json"
    if (output_dir / "agent_warrent_connector" / "agent_warrent_connector_manifest.json").exists():
        kit_entrypoints["agent_warrent_connector"] = "agent_warrent_connector/agent_warrent_connector_manifest.json"

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
        "entrypoints": kit_entrypoints,
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
            "agent_identity_registration": "manual_owner_action_only",
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
    llm_profile_name = program.get("entrypoints", {}).get("llm_connection_profile")
    llm_profile_path = root / str(llm_profile_name) if llm_profile_name else None
    llm_profile = _read_json(llm_profile_path) if llm_profile_path and llm_profile_path.exists() else {}
    llm_public_safe = llm_profile.get("public_safe", {}) if isinstance(llm_profile, dict) else {}
    checks["llm_connection_profile"] = {
        "passed": (
            not llm_profile_name
            or (
                llm_profile_path is not None
                and llm_profile_path.exists()
                and llm_profile.get("schema") == "paideia-llm-connection-profile/v1"
                and llm_public_safe.get("network_call_performed") is False
                and llm_public_safe.get("secret_values_exported") is False
                and llm_public_safe.get("raw_provider_payload_saved") is False
            )
        ),
        "details": {
            "entrypoint": llm_profile_name,
            "exists": bool(llm_profile_path and llm_profile_path.exists()),
            "schema": llm_profile.get("schema") if isinstance(llm_profile, dict) else None,
            "status": llm_profile.get("status") if isinstance(llm_profile, dict) else None,
            "selected_engine": llm_profile.get("selected_llm_service", {}).get("engine")
            if isinstance(llm_profile.get("selected_llm_service"), dict)
            else None,
            "public_safe": llm_public_safe,
        },
    }
    llm_live_setup_guide_name = program.get("entrypoints", {}).get("llm_live_setup_guide")
    llm_live_setup_guide_path = root / str(llm_live_setup_guide_name) if llm_live_setup_guide_name else None
    llm_live_setup_guide = (
        _read_json(llm_live_setup_guide_path)
        if llm_live_setup_guide_path and llm_live_setup_guide_path.exists()
        else {}
    )
    llm_live_setup_public_safe = (
        llm_live_setup_guide.get("public_safe", {}) if isinstance(llm_live_setup_guide, dict) else {}
    )
    llm_live_readiness_gate = (
        llm_live_setup_guide.get("readiness_gate", {}) if isinstance(llm_live_setup_guide, dict) else {}
    )
    checks["llm_live_setup_guide"] = {
        "passed": (
            not llm_live_setup_guide_name
            or (
                llm_live_setup_guide_path is not None
                and llm_live_setup_guide_path.exists()
                and llm_live_setup_guide.get("schema") == "paideia-llm-live-setup-guide/v1"
                and llm_live_readiness_gate.get("requires_explicit_live_check") in {True, False}
                and llm_live_setup_public_safe.get("network_call_performed") is False
                and llm_live_setup_public_safe.get("secret_values_exported") is False
                and llm_live_setup_public_safe.get("raw_provider_payload_saved") is False
            )
        ),
        "details": {
            "entrypoint": llm_live_setup_guide_name,
            "exists": bool(llm_live_setup_guide_path and llm_live_setup_guide_path.exists()),
            "schema": llm_live_setup_guide.get("schema") if isinstance(llm_live_setup_guide, dict) else None,
            "status": llm_live_setup_guide.get("status") if isinstance(llm_live_setup_guide, dict) else None,
            "selected_engine": llm_live_setup_guide.get("selected_llm_service", {}).get("engine")
            if isinstance(llm_live_setup_guide.get("selected_llm_service"), dict)
            else None,
            "requires_explicit_live_check": llm_live_readiness_gate.get("requires_explicit_live_check"),
            "public_safe": llm_live_setup_public_safe,
        },
    }
    registration_request_name = program.get("entrypoints", {}).get("agent_warrent_registration_request")
    registration_request_path = root / str(registration_request_name) if registration_request_name else None
    registration_request = (
        _read_json(registration_request_path)
        if registration_request_path and registration_request_path.exists()
        else {}
    )
    registration_validation = (
        registration_request.get("validation", {}) if isinstance(registration_request.get("validation"), dict) else {}
    )
    registration_public_safe = (
        registration_request.get("public_safe", {}) if isinstance(registration_request.get("public_safe"), dict) else {}
    )
    checks["agent_warrent_registration_request"] = {
        "passed": (
            not registration_request_name
            or (
                registration_request_path is not None
                and registration_request_path.exists()
                and registration_request.get("schema") == "paideia-agent-warrent-registration-request/v1"
                and registration_request.get("external_registration") == "manual_owner_action_only"
                and registration_request.get("network_action_performed") is False
                and registration_request.get("submit_ready") is False
                and registration_validation.get("valid") is True
                and registration_validation.get("signature_required") is True
                and registration_public_safe.get("no_network_call") is True
                and registration_public_safe.get("raw_owner_private_key_stored") is False
            )
        ),
        "details": {
            "entrypoint": registration_request_name,
            "exists": bool(registration_request_path and registration_request_path.exists()),
            "schema": registration_request.get("schema") if isinstance(registration_request, dict) else None,
            "status": registration_request.get("status") if isinstance(registration_request, dict) else None,
            "submit_ready": registration_request.get("submit_ready") if isinstance(registration_request, dict) else None,
            "signature_required": registration_validation.get("signature_required"),
            "network_action_performed": registration_request.get("network_action_performed")
            if isinstance(registration_request, dict)
            else None,
        },
    }
    connector_name = program.get("entrypoints", {}).get("agent_warrent_connector")
    connector_path = root / str(connector_name) if connector_name else None
    connector = _read_json(connector_path) if connector_path and connector_path.exists() else {}
    connector_public_safe = connector.get("public_safe", {}) if isinstance(connector.get("public_safe"), dict) else {}
    connector_validation = connector.get("validation", {}) if isinstance(connector.get("validation"), dict) else {}
    checks["agent_warrent_connector"] = {
        "passed": (
            not connector_name
            or (
                connector_path is not None
                and connector_path.exists()
                and connector.get("schema") == "paideia-agent-warrent-connector-kit/v1"
                and connector.get("external_registration") == "manual_owner_action_only"
                and connector.get("network_action_performed") is False
                and connector_public_safe.get("no_network_call") is True
                and connector_public_safe.get("raw_owner_private_key_stored") is False
                and connector_validation.get("valid") is True
            )
        ),
        "details": {
            "entrypoint": connector_name,
            "exists": bool(connector_path and connector_path.exists()),
            "schema": connector.get("schema") if isinstance(connector, dict) else None,
            "status": connector.get("status") if isinstance(connector, dict) else None,
            "network_action_performed": connector.get("network_action_performed")
            if isinstance(connector, dict)
            else None,
        },
    }
    readiness_name = program.get("entrypoints", {}).get("runtime_readiness")
    readiness_path = root / str(readiness_name) if readiness_name else None
    readiness = _read_json(readiness_path) if readiness_path and readiness_path.exists() else {}
    readiness_public_safe = readiness.get("public_safe", {}) if isinstance(readiness, dict) else {}
    readiness_checks = readiness.get("checks", []) if isinstance(readiness.get("checks"), list) else []
    readiness_check_ids = {str(item.get("id")) for item in readiness_checks if isinstance(item, dict)}
    checks["runtime_readiness"] = {
        "passed": (
            not readiness_name
            or (
                readiness_path is not None
                and readiness_path.exists()
                and readiness.get("schema") == "ai22b-paideia-kit-runtime-readiness/v1"
                and readiness.get("passed") is True
                and readiness_public_safe.get("network_call_performed") is False
                and readiness_public_safe.get("live_provider_called") is False
                and readiness_public_safe.get("secret_values_exported") is False
                and {
                    "llm_connection_profile_present",
                    "offline_preflight_no_network",
                    "live_preflight_fail_closed_no_network",
                    "verification_sequence_covers_runtime",
                }
                <= readiness_check_ids
            )
        ),
        "details": {
            "entrypoint": readiness_name,
            "exists": bool(readiness_path and readiness_path.exists()),
            "schema": readiness.get("schema") if isinstance(readiness, dict) else None,
            "status": readiness.get("status") if isinstance(readiness, dict) else None,
            "selected_engine": readiness.get("runtime_config", {}).get("engine")
            if isinstance(readiness.get("runtime_config"), dict)
            else None,
            "check_ids": sorted(readiness_check_ids),
            "public_safe": readiness_public_safe,
        },
    }
    imported_skill_manifests = sorted((root / "skills" / "imported").glob("**/paideia_skill_manifest.json"))
    imported_skill_details = []
    unsafe_imports = []
    for manifest_path in imported_skill_manifests:
        manifest = _read_json(manifest_path)
        safety_contract = manifest.get("safety_contract", {})
        detail = {
            "path": str(manifest_path.relative_to(root)),
            "status": manifest.get("status"),
            "activation": manifest.get("activation", {}).get("status"),
            "risk_flags": manifest.get("risk_flags", []),
            "safety_contract_status": safety_contract.get("status"),
            "activation_allowed": safety_contract.get("activation_allowed"),
            "sensitive_files_copied": safety_contract.get("sensitive_files_copied"),
            "execute_imported_code": safety_contract.get("execute_imported_code"),
        }
        imported_skill_details.append(detail)
        if (
            manifest.get("activation", {}).get("status") != "disabled"
            or safety_contract.get("schema") != "paideia-imported-skill-safety-contract/v1"
            or safety_contract.get("activation_allowed") is not False
            or safety_contract.get("execute_imported_code") is not False
            or safety_contract.get("sensitive_files_copied") is not False
            or safety_contract.get("default_permissions", {}).get("network") != "blocked"
            or safety_contract.get("default_permissions", {}).get("subprocess") != "blocked"
            or safety_contract.get("default_permissions", {}).get("credential_access") != "blocked"
        ):
            unsafe_imports.append(detail)
    checks["imported_skills"] = {
        "passed": not unsafe_imports,
        "details": {
            "imported_count": len(imported_skill_manifests),
            "contract_schema": "paideia-imported-skill-safety-contract/v1",
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


def _check(check_id: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {
        "id": check_id,
        "passed": passed,
        "status": "passed" if passed else "failed",
        "details": details,
    }


def doctor_paideia_kit_first_run(
    kit_dir: Path,
    *,
    output_path: Path | None = None,
    message: str = "안녕, 오늘 맡길 업무를 같이 정리해보자.",
) -> dict[str, Any]:
    """Verify an install kit can pass doctor checks and run its first offline chat."""

    kit_dir = kit_dir.resolve()
    output_path = output_path or kit_dir / DEFAULT_KIT_FIRST_RUN_DOCTOR
    program_path = kit_dir / DEFAULT_AGENT_PROGRAM_FILE
    install_manifest_path = kit_dir / DEFAULT_INSTALL_MANIFEST
    readiness_path = kit_dir / DEFAULT_RUNTIME_READINESS
    llm_profile_path = kit_dir / DEFAULT_LLM_CONNECTION_PROFILE
    llm_live_setup_guide_path = kit_dir / DEFAULT_LLM_LIVE_SETUP_GUIDE
    agent_warrent_registration_request_path = kit_dir / "agent_warrent_registration_request.json"
    agent_warrent_connector_path = kit_dir / "agent_warrent_connector" / "agent_warrent_connector_manifest.json"
    program_doctor_path = kit_dir / "paideia_doctor_report.json"
    first_chat_path = kit_dir / DEFAULT_KIT_FIRST_RUN_CHAT
    checks: list[dict[str, Any]] = []

    checks.append(_check("kit_directory_exists", kit_dir.exists() and kit_dir.is_dir(), kit_dir=kit_dir.name))
    checks.append(_check("program_manifest_exists", program_path.exists(), program=program_path.name))
    checks.append(_check("install_manifest_exists", install_manifest_path.exists(), manifest=install_manifest_path.name))

    install_manifest: dict[str, Any] = {}
    if install_manifest_path.exists():
        install_manifest = _read_json(install_manifest_path)
    checks.append(
        _check(
            "install_manifest_schema",
            install_manifest.get("schema") == INSTALL_KIT_SCHEMA,
            schema=install_manifest.get("schema"),
            status=install_manifest.get("status"),
        )
    )

    program_doctor: dict[str, Any] = {}
    if program_path.exists():
        program_doctor = doctor_agent_program(program_path, output_path=program_doctor_path)
    checks.append(
        _check(
            "program_doctor_passed",
            program_doctor.get("passed") is True,
            schema=program_doctor.get("schema"),
            status=program_doctor.get("status", "passed" if program_doctor.get("passed") else "failed"),
            failed_checks=[
                key
                for key, value in (program_doctor.get("checks", {}) if isinstance(program_doctor.get("checks"), dict) else {}).items()
                if isinstance(value, dict) and value.get("passed") is not True
            ],
        )
    )

    readiness = _read_json(readiness_path) if readiness_path.exists() else {}
    readiness_public_safe = readiness.get("public_safe", {}) if isinstance(readiness.get("public_safe"), dict) else {}
    checks.append(
        _check(
            "runtime_readiness_passed",
            readiness.get("schema") == "ai22b-paideia-kit-runtime-readiness/v1"
            and readiness.get("passed") is True
            and readiness_public_safe.get("network_call_performed") is False
            and readiness_public_safe.get("live_provider_called") is False,
            schema=readiness.get("schema"),
            status=readiness.get("status"),
            selected_engine=readiness.get("runtime_config", {}).get("engine")
            if isinstance(readiness.get("runtime_config"), dict)
            else None,
        )
    )
    offline_preflight = readiness.get("provider_preflight", {}).get("offline", {}) if isinstance(readiness.get("provider_preflight"), dict) else {}
    live_preflight = readiness.get("provider_preflight", {}).get("live", {}) if isinstance(readiness.get("provider_preflight"), dict) else {}
    checks.append(
        _check(
            "runtime_preflight_no_network",
            offline_preflight.get("network_call_made_by_preflight") is False
            and live_preflight.get("network_call_made_by_preflight") is False
            and live_preflight.get("live_check_requires_explicit_flag") is True,
            offline_status=offline_preflight.get("status"),
            live_status=live_preflight.get("status"),
        )
    )

    llm_profile = _read_json(llm_profile_path) if llm_profile_path.exists() else {}
    llm_public_safe = llm_profile.get("public_safe", {}) if isinstance(llm_profile.get("public_safe"), dict) else {}
    checks.append(
        _check(
            "llm_connection_profile_public_safe",
            llm_profile.get("schema") == "paideia-llm-connection-profile/v1"
            and llm_public_safe.get("network_call_performed") is False
            and llm_public_safe.get("secret_values_exported") is False
            and llm_public_safe.get("raw_provider_payload_saved") is False,
            schema=llm_profile.get("schema"),
            status=llm_profile.get("status"),
        )
    )
    llm_live_setup_guide = _read_json(llm_live_setup_guide_path) if llm_live_setup_guide_path.exists() else {}
    llm_live_public_safe = (
        llm_live_setup_guide.get("public_safe", {})
        if isinstance(llm_live_setup_guide.get("public_safe"), dict)
        else {}
    )
    checks.append(
        _check(
            "llm_live_setup_guide_public_safe",
            llm_live_setup_guide.get("schema") == "paideia-llm-live-setup-guide/v1"
            and llm_live_public_safe.get("network_call_performed") is False
            and llm_live_public_safe.get("secret_values_exported") is False
            and llm_live_public_safe.get("raw_provider_payload_saved") is False,
            schema=llm_live_setup_guide.get("schema"),
            status=llm_live_setup_guide.get("status"),
        )
    )
    agent_warrent_registration_request = (
        _read_json(agent_warrent_registration_request_path)
        if agent_warrent_registration_request_path.exists()
        else {}
    )
    registration_validation = (
        agent_warrent_registration_request.get("validation", {})
        if isinstance(agent_warrent_registration_request.get("validation"), dict)
        else {}
    )
    checks.append(
        _check(
            "agent_warrent_registration_request_manual_only",
            agent_warrent_registration_request.get("schema") == "paideia-agent-warrent-registration-request/v1"
            and agent_warrent_registration_request.get("network_action_performed") is False
            and agent_warrent_registration_request.get("external_registration") == "manual_owner_action_only"
            and agent_warrent_registration_request.get("submit_ready") is False
            and registration_validation.get("valid") is True
            and registration_validation.get("signature_required") is True,
            schema=agent_warrent_registration_request.get("schema"),
            status=agent_warrent_registration_request.get("status"),
            submit_ready=agent_warrent_registration_request.get("submit_ready"),
        )
    )
    agent_warrent_connector = (
        _read_json(agent_warrent_connector_path)
        if agent_warrent_connector_path.exists()
        else {}
    )
    connector_public_safe = (
        agent_warrent_connector.get("public_safe", {})
        if isinstance(agent_warrent_connector.get("public_safe"), dict)
        else {}
    )
    connector_validation = (
        agent_warrent_connector.get("validation", {})
        if isinstance(agent_warrent_connector.get("validation"), dict)
        else {}
    )
    checks.append(
        _check(
            "agent_warrent_connector_manual_only",
            agent_warrent_connector.get("schema") == "paideia-agent-warrent-connector-kit/v1"
            and agent_warrent_connector.get("network_action_performed") is False
            and agent_warrent_connector.get("external_registration") == "manual_owner_action_only"
            and connector_public_safe.get("no_network_call") is True
            and connector_public_safe.get("raw_owner_private_key_stored") is False
            and connector_validation.get("valid") is True,
            schema=agent_warrent_connector.get("schema"),
            status=agent_warrent_connector.get("status"),
            manifest=agent_warrent_connector_path.name,
        )
    )

    chat: dict[str, Any] = {}
    if program_path.exists():
        chat = run_agent_program_chat(
            program_path,
            message=message,
            output_path=first_chat_path,
            llm_mode="offline",
            learn_from_chat=False,
        )
    chat_preflight = chat.get("llm_provider_preflight", {}) if isinstance(chat.get("llm_provider_preflight"), dict) else {}
    checks.append(
        _check(
            "offline_first_chat_completed",
            chat.get("chat_status") == "completed"
            and bool(chat.get("assistant_reply") or chat.get("assistant_answer"))
            and chat.get("stored_private_reasoning_trace") is False
            and chat_preflight.get("network_call_made_by_preflight") is False,
            chat_status=chat.get("chat_status"),
            reply_generation_mode=chat.get("reply_generation_mode"),
            active_operator=chat.get("active_operator"),
            output=first_chat_path.name,
        )
    )
    program_chat_card = (
        chat.get("agent_program_chat_status_card", {})
        if isinstance(chat.get("agent_program_chat_status_card"), dict)
        else {}
    )
    checks.append(
        _check(
            "first_chat_program_runtime_card",
            program_chat_card.get("schema") == PROGRAM_CHAT_STATUS_CARD_SCHEMA
            and program_chat_card.get("status") == "completed_verified"
            and program_chat_card.get("command_surface") == "run-agent-program-chat"
            and program_chat_card.get("public_safe", {}).get("program_wrapper_network_call_performed") is False
            and program_chat_card.get("public_safe", {}).get("private_reasoning_trace_stored") is False,
            schema=program_chat_card.get("schema"),
            status=program_chat_card.get("status"),
            command_surface=program_chat_card.get("command_surface"),
        )
    )
    checks.append(
        _check(
            "first_chat_learning_not_auto_promoted",
            chat.get("learning_update", {}).get("automatic_promotion_performed") is not True
            if isinstance(chat.get("learning_update"), dict)
            else True,
            learn_from_chat=False,
        )
    )

    passed = all(item["passed"] for item in checks)
    report = {
        "schema": KIT_FIRST_RUN_DOCTOR_SCHEMA,
        "created_at_utc": _now(),
        "kit": {
            "name": kit_dir.name,
            "program": DEFAULT_AGENT_PROGRAM_FILE,
            "install_manifest": DEFAULT_INSTALL_MANIFEST,
            "llm_connection_profile": DEFAULT_LLM_CONNECTION_PROFILE,
            "llm_live_setup_guide": DEFAULT_LLM_LIVE_SETUP_GUIDE,
            "agent_warrent_registration_request": "agent_warrent_registration_request.json",
            "agent_warrent_connector": "agent_warrent_connector/agent_warrent_connector_manifest.json",
            "runtime_readiness": DEFAULT_RUNTIME_READINESS,
            "first_chat_output": first_chat_path.name,
            "program_doctor_output": program_doctor_path.name,
        },
        "passed": passed,
        "status": "passed" if passed else "failed",
        "summary": {
            "failed_count": sum(1 for item in checks if not item["passed"]),
            "network_call_performed": False,
            "live_provider_called": False,
            "subprocess_executed": False,
            "offline_first_chat_attempted": program_path.exists(),
            "offline_first_chat_completed": chat.get("chat_status") == "completed",
        },
        "public_safe": {
            "network_call_performed": False,
            "live_provider_called": False,
            "localhost_called": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
        "checks": checks,
        "artifacts": {
            "program_doctor": {
                "schema": program_doctor.get("schema"),
                "passed": program_doctor.get("passed"),
                "output": program_doctor_path.name if program_doctor_path.exists() else None,
            },
            "runtime_readiness": {
                "schema": readiness.get("schema"),
                "status": readiness.get("status"),
                "selected_engine": readiness.get("runtime_config", {}).get("engine")
                if isinstance(readiness.get("runtime_config"), dict)
                else None,
            },
            "llm_connection_profile": {
                "schema": llm_profile.get("schema"),
                "status": llm_profile.get("status"),
            },
            "llm_live_setup_guide": {
                "schema": llm_live_setup_guide.get("schema"),
                "status": llm_live_setup_guide.get("status"),
                "requires_explicit_live_check": (
                    llm_live_setup_guide.get("readiness_gate", {}).get("requires_explicit_live_check")
                    if isinstance(llm_live_setup_guide.get("readiness_gate"), dict)
                    else None
                ),
            },
            "agent_warrent_registration_request": {
                "schema": agent_warrent_registration_request.get("schema"),
                "status": agent_warrent_registration_request.get("status"),
                "submit_ready": agent_warrent_registration_request.get("submit_ready"),
                "signature_required": registration_validation.get("signature_required"),
            },
            "agent_warrent_connector": {
                "schema": agent_warrent_connector.get("schema"),
                "status": agent_warrent_connector.get("status"),
                "network_action_performed": agent_warrent_connector.get("network_action_performed"),
                "entrypoint": "agent_warrent_connector/agent_warrent_connector_manifest.json"
                if agent_warrent_connector_path.exists()
                else None,
            },
            "first_chat": {
                "schema": chat.get("schema"),
                "chat_status": chat.get("chat_status"),
                "reply_generation_mode": chat.get("reply_generation_mode"),
                "active_operator": chat.get("active_operator"),
                "stored_private_reasoning_trace": chat.get("stored_private_reasoning_trace"),
                "program_chat_status_card": {
                    "schema": program_chat_card.get("schema"),
                    "status": program_chat_card.get("status"),
                    "command_surface": program_chat_card.get("command_surface"),
                    "chat_runtime_status": program_chat_card.get("chat_surface", {}).get("chat_runtime_status")
                    if isinstance(program_chat_card.get("chat_surface"), dict)
                    else None,
                },
                "output": first_chat_path.name if first_chat_path.exists() else None,
            },
        },
        "next_actions": [
            "Review paideia_doctor_report.json before enabling live LLM mode.",
            "Use start_paideia_chat.ps1 or run-agent-program-chat in offline mode for the first conversation.",
            "Run the provider live-check command from paideia_runtime_readiness.json only after credentials or local server setup is intentional.",
        ],
    }
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
    chat["agent_program_chat_status_card"] = _build_agent_program_chat_status_card(
        program=program,
        chat=chat,
        program_path=program_path,
        output_path=output_path,
        employment_record_path=employment_record_path,
        selected_llm_mode=selected_llm_mode,
        selected_learn=selected_learn,
        llm_model=llm_model,
    )
    _write_json(output_path, chat)
    return chat
