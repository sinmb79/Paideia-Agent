from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.llm_runtime import (
    build_llm_provider_preflight,
    build_llm_runtime_config,
    doctor_llm_provider,
)
from ai22b.talent_foundry.onboarding_choices import (
    DEFAULT_CHAT_SURFACE_ID,
    DEFAULT_LLM_SERVICE_ID,
    EXTERNAL_API_ENGINES,
    LLM_SERVICE_CATALOG,
    LOCAL_HTTP_ENGINES,
    LOCAL_MODEL_ENGINES,
    resolve_chat_surface,
    resolve_llm_service,
)


LLM_ONBOARDING_CHECKLIST_SCHEMA = "paideia-llm-onboarding-checklist/v1"
LLM_PROVIDER_MATRIX_SCHEMA = "paideia-llm-provider-matrix/v1"
LLM_CONNECTION_PROFILE_SCHEMA = "paideia-llm-connection-profile/v1"
LLM_LIVE_SETUP_GUIDE_SCHEMA = "paideia-llm-live-setup-guide/v1"

ENV_REQUIREMENTS: dict[str, list[list[str]]] = {
    "openai_chatgpt_codex": [["OPENAI_API_KEY"]],
    "anthropic_claude_api": [["ANTHROPIC_API_KEY"]],
    "google_gemini_api": [["GEMINI_API_KEY", "GOOGLE_API_KEY"]],
    "mistral_api": [["MISTRAL_API_KEY"]],
    "openrouter_api": [["OPENROUTER_API_KEY"]],
}

DEFAULT_LOCAL_ENDPOINTS = {
    "ollama_local_http": "http://localhost:11434",
    "lm_studio_local_http": "http://localhost:1234/v1/chat/completions",
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _arg(flag: str, value: str | None, placeholder: str | None = None) -> str:
    selected = value if value else placeholder
    return f" {flag} {selected}" if selected else ""


def _command(
    command: str,
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    live: bool = False,
    strict: bool = False,
    output: str,
) -> str:
    needs_model = engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES
    needs_path = engine in LOCAL_HTTP_ENGINES or engine in LOCAL_MODEL_ENGINES
    parts = [
        f"ai22b-talent-foundry {command}",
        f"--llm-engine {engine}",
        _arg("--llm-model", model, "<model>" if needs_model else None).strip(),
        _arg("--llm-model-path", model_path, "<localhost-url-or-local-model-path>" if needs_path else None).strip(),
        "--live-check" if live else "",
        "--strict" if strict else "",
        f"--output {output}",
    ]
    return " ".join(part for part in parts if part)


def _readiness_suite_command(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    live: bool = False,
    strict: bool = False,
    output_dir: str,
) -> str:
    needs_model = engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES
    needs_path = engine in LOCAL_HTTP_ENGINES or engine in LOCAL_MODEL_ENGINES
    parts = [
        "ai22b-talent-foundry doctor-llm-live-readiness",
        f"--llm-engine {engine}",
        _arg("--llm-model", model, "<model>" if needs_model else None).strip(),
        _arg("--llm-model-path", model_path, "<localhost-url-or-local-model-path>" if needs_path else None).strip(),
        "--live-check" if live else "",
        "--strict" if strict else "",
        f"--output-dir {output_dir}",
    ]
    return " ".join(part for part in parts if part)


def _chat_command(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    mode: str,
) -> str:
    needs_model = engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES
    needs_path = engine in LOCAL_HTTP_ENGINES or engine in LOCAL_MODEL_ENGINES
    parts = [
        "ai22b-talent-foundry chat-hired-agent",
        "--employment-record <employment_record.json>",
        "--message \"안녕, 오늘 맡길 업무를 같이 정리해보자.\"",
        f"--llm-engine {engine}",
        f"--llm-mode {mode}",
        _arg("--llm-model", model, "<model>" if needs_model else None).strip(),
        _arg("--llm-model-path", model_path, "<localhost-url-or-local-model-path>" if needs_path else None).strip(),
        "--output <chat_turn.json>",
    ]
    return " ".join(part for part in parts if part)


def _chat_runtime_smoke_command(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    chat_surface: str,
    live: bool = False,
    strict: bool = False,
    output: str,
) -> str:
    needs_model = engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES
    needs_path = engine in LOCAL_HTTP_ENGINES or engine in LOCAL_MODEL_ENGINES
    parts = [
        "ai22b-talent-foundry run-chat-runtime-smoke",
        f"--llm-engine {engine}",
        f"--chat-surface {chat_surface}",
        _arg("--llm-model", model, "<model>" if needs_model else None).strip(),
        _arg("--llm-model-path", model_path, "<localhost-url-or-local-model-path>" if needs_path else None).strip(),
        "--live-check" if live else "",
        "--strict" if strict else "",
        f"--output {output}",
    ]
    return " ".join(part for part in parts if part)


def _command_by_id(checklist: dict[str, Any], command_id: str) -> dict[str, Any]:
    command_plan = checklist.get("command_plan", [])
    if not isinstance(command_plan, list):
        return {}
    for item in command_plan:
        if isinstance(item, dict) and item.get("id") == command_id:
            return item
    return {}


def _profile_env_setup(engine: str) -> list[dict[str, Any]]:
    setup: list[dict[str, Any]] = []
    for group in ENV_REQUIREMENTS.get(engine, []):
        preferred = group[0]
        setup.append(
            {
                "one_of": group,
                "preferred": preferred,
                "powershell": f"$env:{preferred} = '<paste-your-{preferred.lower()}>'",
                "stores_secret_in_profile": False,
            }
        )
    return setup


def _profile_readiness(
    *,
    engine: str,
    model: str | None,
    model_path: str | None,
    doctor: dict[str, Any],
    live_preflight: dict[str, Any],
) -> str:
    if engine == "deterministic_local":
        return "offline_ready_no_setup"
    if engine in LOCAL_MODEL_ENGINES and not model_path:
        return "needs_local_model_path"
    if engine in LOCAL_MODEL_ENGINES and live_preflight.get("status") == "needs_configuration":
        return "needs_local_model_files"
    if engine in LOCAL_HTTP_ENGINES and not model:
        return "needs_local_model_name"
    if engine in LOCAL_HTTP_ENGINES:
        return "ready_for_localhost_live_check" if doctor.get("passed") else "needs_local_server_live_check"
    if engine in EXTERNAL_API_ENGINES and engine != "openai_chatgpt_codex" and not model:
        return "needs_model_and_credentials"
    if engine in EXTERNAL_API_ENGINES:
        return "ready_for_explicit_live_check" if doctor.get("passed") else "needs_credentials_before_live"
    return "ready_for_offline_check"


def build_llm_connection_profile(
    *,
    llm_service: str | None = DEFAULT_LLM_SERVICE_ID,
    llm_engine: str | None = None,
    llm_model: str | None = None,
    llm_model_path: str | None = None,
    chat_surface: str | None = DEFAULT_CHAT_SURFACE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a one-page, no-network connection profile for the selected LLM provider."""

    checklist = build_llm_onboarding_checklist(
        llm_service=llm_service,
        llm_engine=llm_engine,
        llm_model=llm_model,
        llm_model_path=llm_model_path,
        chat_surface=chat_surface,
    )
    selected_llm = checklist["selected_llm_service"]
    selected_chat = checklist["selected_chat_surface"]
    engine = selected_llm["engine"]
    model = selected_llm.get("selected_model")
    model_path = selected_llm.get("selected_model_path")
    runtime_config = build_llm_runtime_config(
        engine=engine,
        service=selected_llm.get("service_id"),
        model=model,
        model_path=model_path,
    )
    doctor = doctor_llm_provider(
        engine=engine,
        service=selected_llm.get("service_id"),
        model=model,
        model_path=model_path,
        live_check=False,
    )
    live_preflight = build_llm_provider_preflight(runtime_config, llm_mode="live", llm_model=model)
    command_by_id = {item["id"]: item for item in checklist["command_plan"]}
    local_endpoint = model_path if engine in LOCAL_HTTP_ENGINES else None
    if engine in LOCAL_HTTP_ENGINES and not local_endpoint:
        local_endpoint = DEFAULT_LOCAL_ENDPOINTS.get(engine)
    needs_live = engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES
    needs_model = engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES
    needs_model_path = engine in LOCAL_MODEL_ENGINES
    readiness = _profile_readiness(
        engine=engine,
        model=model,
        model_path=model_path,
        doctor=doctor,
        live_preflight=live_preflight,
    )
    profile = {
        "schema": LLM_CONNECTION_PROFILE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": readiness,
        "selected_llm_service": selected_llm,
        "selected_chat_surface": selected_chat,
        "runtime_identity_policy": runtime_config["identity_policy"],
        "setup_requirements": {
            "requires_live_check_before_agent_work": needs_live,
            "requires_model_argument": needs_model,
            "requires_model_path": needs_model_path,
            "requires_localhost_endpoint": engine in LOCAL_HTTP_ENGINES,
            "required_env": _profile_env_setup(engine),
            "recommended_model_argument": model or ("<model>" if needs_model else None),
            "recommended_model_path_argument": (
                model_path
                or local_endpoint
                or ("<local-model-path>" if needs_model_path else None)
            ),
        },
        "readiness": {
            "doctor_status": doctor.get("status"),
            "doctor_passed": doctor.get("passed"),
            "live_preflight_status": live_preflight.get("status"),
            "blocking_checks": live_preflight.get("blocking_checks", []),
            "next_actions": live_preflight.get("next_actions", []),
        },
        "verification_sequence": [
            {
                "id": "no_network_doctor",
                "network_call": False,
                "command": command_by_id["provider_doctor_no_network"]["command"],
                "purpose": "Verify static provider configuration without contacting the provider.",
            },
            {
                "id": "explicit_live_provider_check",
                "network_call": needs_live,
                "command": command_by_id["provider_doctor_live_check"]["command"],
                "purpose": "Contact the selected API or localhost server only after the owner intentionally requests it.",
            },
            {
                "id": "live_application_engine_smoke",
                "network_call": needs_live,
                "command": command_by_id["application_engine_live_smoke"]["command"],
                "purpose": "Verify the provider can serve as a language engine without becoming the agent identity.",
            },
            {
                "id": "live_agent_runtime_smoke",
                "network_call": needs_live,
                "command": command_by_id["agent_runtime_live_smoke"]["command"],
                "purpose": "Verify policy, planning, registered tools, verification, and review-gated memory with the selected provider.",
            },
            {
                "id": "chat_runtime_smoke",
                "network_call": needs_live,
                "command": command_by_id["chat_runtime_smoke"]["command"],
                "purpose": "Verify the selected chat surface can run a hired-chat turn before daily conversation.",
            },
        ],
        "daily_use_commands": {
            "chat_runtime_smoke": command_by_id["chat_runtime_smoke"]["command"],
            "offline_first_chat": command_by_id["chat_surface_first_turn"]["command"],
            "live_chat_template": _chat_command(
                engine=engine,
                model=model,
                model_path=model_path or local_endpoint,
                mode="live",
            ),
        },
        "fail_closed_expectation": {
            "missing_key_or_server_status": "needs_configuration",
            "tool_execution_before_provider_ready": False,
            "workspace_artifacts_before_provider_ready": False,
            "learning_promotion_before_review": False,
        },
        "data_policy": {
            "llm_is_identity": False,
            "identity_source": "local_training_records_memory_substrate_and_reasoning_ledger",
            "send_private_training_files": False,
            "send_selected_memory_summaries_only": True,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "secret_values_exported": False,
        },
        "public_safe": {
            "network_call_performed": False,
            "live_check_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
    }
    if output_path is not None:
        _write_json(output_path, profile)
    return profile


def _setup_guide_status(profile: dict[str, Any], *, needs_live: bool) -> str:
    if not needs_live:
        if profile.get("status") == "offline_ready_no_setup":
            return "offline_ready_no_live_setup_required"
        return "local_setup_required_before_offline_use"
    if profile.get("status") in {"ready_for_explicit_live_check", "ready_for_localhost_live_check"}:
        return "ready_for_explicit_live_check"
    return "needs_owner_configuration_before_live"


def _setup_cards(profile: dict[str, Any], *, needs_live: bool) -> list[dict[str, Any]]:
    setup = profile.get("setup_requirements", {}) if isinstance(profile.get("setup_requirements"), dict) else {}
    cards: list[dict[str, Any]] = []
    required_env = setup.get("required_env", []) if isinstance(setup.get("required_env"), list) else []
    if required_env:
        cards.append(
            {
                "id": "api_credentials",
                "title": "API credential",
                "status": "owner_action_required",
                "required_env": required_env,
                "secret_policy": (
                    "Paste secrets into your shell or local secret manager only; "
                    "Paideia does not write secret values into this guide."
                ),
            }
        )
    if setup.get("requires_model_argument"):
        cards.append(
            {
                "id": "model_argument",
                "title": "Model name",
                "status": "owner_action_required" if setup.get("recommended_model_argument") == "<model>" else "ready",
                "recommended_value": setup.get("recommended_model_argument"),
                "examples": {
                    "openai_chatgpt_codex": "gpt-4.1-mini",
                    "anthropic_claude_api": "claude-3-5-sonnet-latest",
                    "google_gemini_api": "gemini-1.5-pro",
                    "ollama_local_http": "llama3.1",
                    "lm_studio_local_http": "loaded-local-model",
                },
            }
        )
    if setup.get("requires_localhost_endpoint"):
        cards.append(
            {
                "id": "localhost_endpoint",
                "title": "Local model server",
                "status": "ready_for_owner_live_check",
                "recommended_value": setup.get("recommended_model_path_argument"),
                "network_scope": "localhost_only",
            }
        )
    if setup.get("requires_model_path"):
        cards.append(
            {
                "id": "local_model_path",
                "title": "Local model files",
                "status": "owner_action_required",
                "recommended_value": setup.get("recommended_model_path_argument"),
                "network_scope": "local_files_only",
            }
        )
    if not cards:
        cards.append(
            {
                "id": "no_live_setup_required",
                "title": "No live setup required",
                "status": "ready",
                "reason": (
                    "This selected engine can run the public-safe offline path without "
                    "credentials, localhost, or model files."
                ),
            }
        )
    if needs_live:
        cards.append(
            {
                "id": "owner_live_intent",
                "title": "Explicit live-check consent",
                "status": "required_before_provider_call",
                "policy": "Live API or localhost calls happen only when the owner runs a command with --live-check.",
            }
        )
    return cards


def build_llm_live_setup_guide(
    *,
    llm_service: str | None = DEFAULT_LLM_SERVICE_ID,
    llm_engine: str | None = None,
    llm_model: str | None = None,
    llm_model_path: str | None = None,
    chat_surface: str | None = DEFAULT_CHAT_SURFACE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a no-network owner-facing guide for live provider setup."""

    checklist = build_llm_onboarding_checklist(
        llm_service=llm_service,
        llm_engine=llm_engine,
        llm_model=llm_model,
        llm_model_path=llm_model_path,
        chat_surface=chat_surface,
    )
    profile = build_llm_connection_profile(
        llm_service=llm_service,
        llm_engine=llm_engine,
        llm_model=llm_model,
        llm_model_path=llm_model_path,
        chat_surface=chat_surface,
    )
    selected_llm = profile["selected_llm_service"]
    selected_chat = profile["selected_chat_surface"]
    needs_live = bool(profile["setup_requirements"]["requires_live_check_before_agent_work"])
    status = _setup_guide_status(profile, needs_live=needs_live)
    no_network_doctor = _command_by_id(checklist, "provider_doctor_no_network")
    live_readiness_command = _command_by_id(checklist, "llm_live_readiness_suite")
    guide = {
        "schema": LLM_LIVE_SETUP_GUIDE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "selected_llm_service": selected_llm,
        "selected_chat_surface": selected_chat,
        "setup_cards": _setup_cards(profile, needs_live=needs_live),
        "readiness_gate": {
            "connection_profile_status": profile.get("status"),
            "doctor_status": profile.get("readiness", {}).get("doctor_status"),
            "live_preflight_status": profile.get("readiness", {}).get("live_preflight_status"),
            "blocking_checks": profile.get("readiness", {}).get("blocking_checks", []),
            "requires_explicit_live_check": needs_live,
            "ready_for_daily_live_work_when": [
                "provider doctor passes with --live-check",
                "application-engine live smoke passes",
                "agent-runtime live smoke passes",
                "chat-runtime smoke passes for the selected chat surface",
            ]
            if needs_live
            else [
                "offline deterministic/provider-free checks pass",
                "chat-runtime smoke passes before daily conversation",
            ],
        },
        "safe_runbook": [
            {
                "id": "review_connection_profile",
                "network_call": False,
                "artifact": "<llm_connection_profile.json>",
                "purpose": "Review setup requirements before any provider call.",
            },
            {
                "id": "no_network_provider_doctor",
                "network_call": False,
                "command": no_network_doctor.get("command"),
                "purpose": "Check static provider configuration without contacting APIs or localhost servers.",
            },
            {
                "id": "explicit_live_readiness_suite",
                "network_call": needs_live,
                "command": live_readiness_command.get("command"),
                "purpose": "Run only after the owner intentionally wants to call the selected API or localhost provider.",
            },
            {
                "id": "first_live_chat_template",
                "network_call": needs_live,
                "command": profile.get("daily_use_commands", {}).get("live_chat_template"),
                "purpose": "Start daily chat only after the readiness suite is reviewed.",
            },
        ],
        "daily_use": {
            "offline_first_chat": profile.get("daily_use_commands", {}).get("offline_first_chat"),
            "chat_runtime_smoke": profile.get("daily_use_commands", {}).get("chat_runtime_smoke"),
            "live_chat_template": profile.get("daily_use_commands", {}).get("live_chat_template"),
        },
        "owner_visible_summary": {
            "ko": (
                "선택한 LLM은 오프라인 경로로 바로 점검할 수 있으며, 별도 live 설정은 필요하지 않습니다."
                if status == "offline_ready_no_live_setup_required"
                else "선택한 LLM은 live 사용 전에 보스가 모델, 키, localhost, 또는 로컬 모델 경로를 설정하고 --live-check를 직접 실행해야 합니다."
                if status == "needs_owner_configuration_before_live"
                else "선택한 LLM은 설정값이 채워져 있어 명시적 --live-check로 실제 연결을 확인할 수 있습니다."
            ),
            "en": (
                "The selected LLM can be checked through the offline path without separate live setup."
                if status == "offline_ready_no_live_setup_required"
                else "Before live use, the owner must configure the model, key, localhost server, or local model path and intentionally run --live-check."
                if status == "needs_owner_configuration_before_live"
                else "The selected LLM has enough setup metadata for an explicit --live-check."
            ),
        },
        "data_policy": {
            "llm_is_identity": False,
            "send_private_training_files": False,
            "send_selected_memory_summaries_only": True,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "secret_values_exported": False,
        },
        "public_safe": {
            "network_call_performed": False,
            "live_check_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
    }
    if output_path is not None:
        _write_json(output_path, guide)
    return guide


def _readiness_status(doctor: dict[str, Any], live_preflight: dict[str, Any], *, engine: str) -> str:
    if engine == "deterministic_local":
        return "offline_ready"
    if engine in LOCAL_MODEL_ENGINES and live_preflight.get("status") == "needs_configuration":
        return "local_model_path_required"
    if doctor.get("passed"):
        return "ready_for_explicit_live_smoke"
    return "needs_configuration_before_live"


def build_llm_onboarding_checklist(
    *,
    llm_service: str | None = DEFAULT_LLM_SERVICE_ID,
    llm_engine: str | None = None,
    llm_model: str | None = None,
    llm_model_path: str | None = None,
    chat_surface: str | None = DEFAULT_CHAT_SURFACE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a public-safe first-run checklist for the selected LLM and chat surface.

    The checklist intentionally performs no live provider call. It records the
    exact doctor, smoke, runtime, and chat commands an owner can run next.
    """

    selected_llm = resolve_llm_service(
        llm_service=llm_service,
        llm_engine=llm_engine,
        llm_model=llm_model,
        llm_model_path=llm_model_path,
    )
    selected_chat = resolve_chat_surface(chat_surface)
    engine = selected_llm["engine"]
    model = selected_llm.get("selected_model")
    model_path = selected_llm.get("selected_model_path")
    runtime_config = build_llm_runtime_config(
        engine=engine,
        service=selected_llm.get("service_id"),
        model=model,
        model_path=model_path,
    )
    doctor = doctor_llm_provider(
        engine=engine,
        service=selected_llm.get("service_id"),
        model=model,
        model_path=model_path,
        live_check=False,
    )
    offline_preflight = build_llm_provider_preflight(runtime_config, llm_mode="offline", llm_model=model)
    live_preflight = build_llm_provider_preflight(runtime_config, llm_mode="live", llm_model=model)
    readiness = _readiness_status(doctor, live_preflight, engine=engine)
    live_provider = engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES
    command_plan = [
        {
            "id": "provider_doctor_no_network",
            "required_before_live": True,
            "network_call": False,
            "command": _command(
                "doctor-llm-provider",
                engine=engine,
                model=model,
                model_path=model_path,
                output="llm_provider_doctor.json",
            ),
            "expected": "ready for deterministic/local configured providers, or needs_configuration with exact missing model/key/path checks.",
        },
        {
            "id": "provider_doctor_live_check",
            "required_before_live": engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES,
            "network_call": engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES,
            "command": _command(
                "doctor-llm-provider",
                engine=engine,
                model=model,
                model_path=model_path,
                live=True,
                strict=True,
                output="llm_provider_doctor.live.json",
            ),
            "expected": "provider smoke passes, or strict mode returns code 2 without saving raw provider payloads.",
        },
        {
            "id": "application_engine_no_network_smoke",
            "required_before_agent_work": not live_provider,
            "network_call": False,
            "command": _command(
                "run-llm-application-smoke",
                engine=engine,
                model=model,
                model_path=model_path,
                output="llm_application_smoke.json",
            ),
            "expected": (
                "deterministic/local configured engines produce a completed public-safe summary; "
                "external adapters may only prove manifest/preflight shape until live-check is explicit."
            ),
        },
        {
            "id": "application_engine_live_smoke",
            "required_before_agent_work": live_provider,
            "network_call": live_provider,
            "command": _command(
                "run-llm-application-smoke",
                engine=engine,
                model=model,
                model_path=model_path,
                live=True,
                strict=True,
                output="llm_application_smoke.live.json",
            ),
            "expected": "after provider credentials/server are ready, this proves the live application-engine path or fails closed.",
        },
        {
            "id": "agent_runtime_no_network_smoke",
            "required_before_agent_work": not live_provider,
            "network_call": False,
            "command": _command(
                "run-agent-runtime-smoke",
                engine=engine,
                model=model,
                model_path=model_path,
                strict=True,
                output="agent_runtime_smoke.json",
            ),
            "expected": "no-network runtime contract for deterministic/local configured engines; external live work still requires live smoke.",
        },
        {
            "id": "agent_runtime_live_smoke",
            "required_before_agent_work": live_provider,
            "network_call": live_provider,
            "command": _command(
                "run-agent-runtime-smoke",
                engine=engine,
                model=model,
                model_path=model_path,
                live=True,
                strict=True,
                output="agent_runtime_smoke.live.json",
            ),
            "expected": "after provider credentials/server are ready, this proves policy, LLM planning, tools, verification, and memory gating with the selected provider.",
        },
        {
            "id": "llm_live_readiness_suite",
            "required_before_agent_work": live_provider,
            "network_call": live_provider,
            "command": _readiness_suite_command(
                engine=engine,
                model=model,
                model_path=model_path,
                live=live_provider,
                strict=True,
                output_dir="llm_live_readiness",
            ),
            "expected": (
                "one command writes provider doctor, application smoke, and full agent runtime smoke artifacts; "
                "without provider readiness it fails closed before daily live work."
            ),
        },
        {
            "id": "chat_runtime_smoke",
            "required_before_daily_use": True,
            "network_call": live_provider,
            "command": _chat_runtime_smoke_command(
                engine=engine,
                model=model,
                model_path=model_path,
                chat_surface=selected_chat["id"],
                live=live_provider,
                strict=True,
                output="chat_runtime_smoke.json",
            ),
            "expected": "proves the selected chat surface can run a hired-chat turn with provider preflight and review-gated learning.",
        },
        {
            "id": "chat_surface_first_turn",
            "required_before_daily_use": False,
            "network_call": False,
            "command": _chat_command(engine=engine, model=model, model_path=model_path, mode="offline"),
            "expected": "first chat turn uses local education and memory records; live mode can be selected only after provider readiness.",
        },
    ]
    checklist = {
        "schema": LLM_ONBOARDING_CHECKLIST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": readiness,
        "selected_llm_service": selected_llm,
        "selected_chat_surface": selected_chat,
        "runtime_identity_policy": runtime_config["identity_policy"],
        "readiness": {
            "status": readiness,
            "doctor_status": doctor.get("status"),
            "doctor_passed": doctor.get("passed"),
            "offline_preflight_status": offline_preflight.get("status"),
            "live_preflight_status": live_preflight.get("status"),
            "blocking_checks": live_preflight.get("blocking_checks", []),
            "next_actions": live_preflight.get("next_actions", []),
        },
        "command_plan": command_plan,
        "acceptance_checks": [
            "doctor report exists and exports no secret values",
            "application smoke stores no raw provider payload or hidden reasoning trace",
            "agent runtime smoke proves policy before LLM and tools",
            "live readiness suite ties provider doctor, application smoke, and full runtime smoke together",
            "chat runtime smoke proves the selected chat surface before daily conversation",
            "chat turn records provider preflight and selected memory route",
            "learning promotion remains review-gated after provider fallback or failure",
        ],
        "public_safe": {
            "network_call_performed": False,
            "live_check_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
    }
    if output_path is not None:
        _write_json(output_path, checklist)
    return checklist


def build_llm_provider_matrix(
    *,
    chat_surface: str | None = DEFAULT_CHAT_SURFACE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a public-safe matrix of all selectable LLM providers.

    This is the OpenClaw-style first screen in JSON form: it lets an owner see
    every selectable language engine, its readiness posture, and the exact next
    commands before choosing one. It intentionally performs no live checks.
    """

    services: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    live_required_count = 0
    for item in LLM_SERVICE_CATALOG:
        checklist = build_llm_onboarding_checklist(
            llm_service=item["id"],
            chat_surface=chat_surface,
        )
        command_by_id = {command["id"]: command for command in checklist["command_plan"]}
        service = checklist["selected_llm_service"]
        live_required = bool(
            command_by_id.get("provider_doctor_live_check", {}).get("required_before_live")
            or command_by_id.get("agent_runtime_live_smoke", {}).get("required_before_agent_work")
        )
        if live_required:
            live_required_count += 1
        status = checklist["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        services.append(
            {
                "service_id": service["service_id"],
                "label": service["label"],
                "engine": service["engine"],
                "status": status,
                "researcher_fit": service.get("researcher_fit"),
                "default_chat_mode": service.get("default_chat_mode"),
                "network_access": service.get("network_access"),
                "runtime_readiness": service.get("runtime_readiness"),
                "model_policy": service.get("model_policy"),
                "requires": service.get("requires", []),
                "privacy_note": service.get("privacy_note"),
                "cost_warning": service.get("cost_warning"),
                "doctor_command": command_by_id["provider_doctor_no_network"]["command"],
                "live_check_command": command_by_id["provider_doctor_live_check"]["command"],
                "application_smoke_command": command_by_id["application_engine_no_network_smoke"]["command"],
                "application_live_smoke_command": command_by_id["application_engine_live_smoke"]["command"],
                "agent_runtime_smoke_command": command_by_id["agent_runtime_no_network_smoke"]["command"],
                "agent_runtime_live_smoke_command": command_by_id["agent_runtime_live_smoke"]["command"],
                "chat_command": command_by_id["chat_surface_first_turn"]["command"],
                "live_required_before_agent_work": live_required,
                "blocking_checks": checklist["readiness"].get("blocking_checks", []),
                "next_actions": checklist["readiness"].get("next_actions", []),
                "data_transfer_policy": service.get("data_transfer_policy", {}),
                "failure_policy": service.get("failure_policy", {}),
            }
        )

    selected_chat = resolve_chat_surface(chat_surface)
    matrix = {
        "schema": LLM_PROVIDER_MATRIX_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_chat_surface": selected_chat,
        "summary": {
            "service_count": len(services),
            "status_counts": status_counts,
            "live_required_count": live_required_count,
            "no_network_service_ids": [
                item["service_id"]
                for item in services
                if item["network_access"] == "blocked"
            ],
            "localhost_service_ids": [
                item["service_id"]
                for item in services
                if item["network_access"] == "localhost_only"
            ],
            "external_api_service_ids": [
                item["service_id"]
                for item in services
                if str(item["network_access"]).startswith("external_api")
                or item["service_id"] == "openai_chatgpt_codex"
            ],
        },
        "selection_policy": {
            "llm_is_identity": False,
            "identity_source": "local_training_records_memory_substrate_and_reasoning_ledger",
            "live_checks_require_explicit_command": True,
            "default_network_call_performed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
        "services": services,
        "public_safe": {
            "network_call_performed": False,
            "live_check_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
    }
    if output_path is not None:
        _write_json(output_path, matrix)
    return matrix
