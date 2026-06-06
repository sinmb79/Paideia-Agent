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
