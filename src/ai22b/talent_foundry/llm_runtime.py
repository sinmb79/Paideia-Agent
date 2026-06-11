from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.from_scratch.bigram import generate_text, load_model
from ai22b.talent_foundry.llm_clients import (
    LLMClient,
    build_llm_client,
    build_runtime_messages,
    count_private_reasoning_fields,
    is_loopback_http_endpoint,
    sanitize_llm_result_packet,
)


RUNTIME_SCHEMA = "ai-talent-llm-runtime/v1"
RUNTIME_RESULT_SCHEMA = "ai-talent-llm-runtime-result/v1"
CLIENT_RESULT_RUNTIME_SUMMARY_KEYS = (
    "schema",
    "engine",
    "status",
    "reason",
    "model",
    "endpoint",
    "error_type",
    "network_access",
    "local_files_only",
    "identity_policy",
    "raw_output_saved",
    "response_id",
    "usage",
)

TRANSFORMERS_REQUIRED_FILE_GROUPS = {
    "config": ["config.json"],
    "tokenizer": ["tokenizer.json", "tokenizer_config.json", "vocab.json", "spiece.model"],
    "weights": ["model.safetensors", "pytorch_model.bin"],
}
EXTERNAL_API_ENGINES = {
    "openai_chatgpt_codex",
    "anthropic_claude_api",
    "google_gemini_api",
    "mistral_api",
    "openrouter_api",
}
LOCAL_HTTP_ENGINES = {"ollama_local_http", "lm_studio_local_http"}
LLM_PROVIDER_DOCTOR_SCHEMA = "paideia-llm-provider-doctor/v1"
LLM_PROVIDER_PREFLIGHT_SCHEMA = "paideia-llm-provider-preflight/v1"
LLM_PROVIDER_SMOKE_CONTRACT_SCHEMA = "paideia-llm-provider-smoke-contract/v1"
LLM_APPLICATION_SMOKE_SCHEMA = "paideia-llm-application-smoke/v1"
LLM_REVIEWABLE_PLAN_SCHEMA = "paideia-llm-reviewable-plan/v1"
LLM_CLIENT_CONTRACT_SCHEMA = "paideia-llm-client-contract/v1"
MODEL_REQUIRED_ENGINES = {
    "anthropic_claude_api",
    "google_gemini_api",
    "mistral_api",
    "openrouter_api",
}
LOCAL_MODEL_PATH_REQUIRED_ENGINES = {"bigram_local", "transformers_local", "llama_cpp_local"}
PROVIDER_ENV_REQUIREMENTS = {
    "openai_chatgpt_codex": [["OPENAI_API_KEY"]],
    "anthropic_claude_api": [["ANTHROPIC_API_KEY"]],
    "google_gemini_api": [["GEMINI_API_KEY", "GOOGLE_API_KEY"]],
    "mistral_api": [["MISTRAL_API_KEY"]],
    "openrouter_api": [["OPENROUTER_API_KEY"]],
}


def build_llm_runtime_config(
    *,
    engine: str = "deterministic_local",
    model_path: str | None = None,
    model: str | None = None,
    service: str | None = None,
) -> dict[str, Any]:
    compatible_engines = [
        "deterministic_local",
        "bigram_local",
        "transformers_local",
        "llama_cpp_local",
        "openai_chatgpt_codex",
        "anthropic_claude_api",
        "google_gemini_api",
        "mistral_api",
        "openrouter_api",
        "ollama_local_http",
        "lm_studio_local_http",
    ]
    if engine not in compatible_engines:
        raise ValueError(f"Unsupported LLM runtime engine: {engine}")

    codex_bridge = engine == "openai_chatgpt_codex"
    external_api = engine in EXTERNAL_API_ENGINES
    local_http = engine in LOCAL_HTTP_ENGINES
    if codex_bridge:
        network_access = "codex_host_managed_data_minimized"
    elif external_api:
        network_access = "external_api_selected_data_minimized"
    elif local_http:
        network_access = "localhost_only"
    else:
        network_access = "blocked"
    return {
        "schema": RUNTIME_SCHEMA,
        "service": service or engine,
        "engine": engine,
        "model": model,
        "model_path": model_path,
        "local_only": not external_api,
        "network_access": network_access,
        "identity_policy": "application_engine_not_identity",
        "private_reasoning_trace": "do_not_store",
        "compatible_engines": compatible_engines,
        "execution_contract": {
            "input": "task + talent manifest + verified memory summaries",
            "output": "draft language, tool-use suggestions, and answer text",
            "cannot_change_identity": True,
            "cannot_override_guardrails": True,
        },
    }


def doctor_llm_provider(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    service: str | None = None,
    live_check: bool = False,
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """Build a public-safe readiness report for one selected LLM provider."""

    runtime_config = build_llm_runtime_config(
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
    )
    checks: list[dict[str, Any]] = []

    def add_check(
        check_id: str,
        passed: bool,
        *,
        severity: str = "error",
        status: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        checks.append(
            {
                "id": check_id,
                "status": status or ("passed" if passed else "failed"),
                "passed": passed,
                "severity": severity,
                "details": details or {},
            }
        )

    add_check(
        "supported_engine",
        True,
        details={"engine": engine, "compatible_engines": runtime_config["compatible_engines"]},
    )
    add_check(
        "identity_boundary",
        runtime_config["identity_policy"] == "application_engine_not_identity",
        details={
            "identity_policy": runtime_config["identity_policy"],
            "private_reasoning_trace": runtime_config["private_reasoning_trace"],
        },
    )

    model_required = engine in MODEL_REQUIRED_ENGINES
    add_check(
        "model_selected",
        (not model_required) or bool(model),
        details={"model_required": model_required, "model_present": bool(model)},
    )

    if engine in PROVIDER_ENV_REQUIREMENTS:
        env_groups = PROVIDER_ENV_REQUIREMENTS[engine]
        group_results = [
            {
                "one_of": group,
                "present": [key for key in group if bool(os.environ.get(key))],
            }
            for group in env_groups
        ]
        env_ready = all(bool(item["present"]) for item in group_results)
        add_check(
            "credential_environment",
            env_ready,
            details={
                "required": group_results,
                "secret_values_exported": False,
            },
        )

    if engine in LOCAL_HTTP_ENGINES:
        default_endpoint = "http://localhost:11434" if engine == "ollama_local_http" else "http://localhost:1234/v1/chat/completions"
        endpoint = model_path or default_endpoint
        loopback_endpoint = is_loopback_http_endpoint(endpoint)
        add_check(
            "local_http_endpoint",
            loopback_endpoint,
            severity="warning" if loopback_endpoint else "error",
            details={
                "endpoint": endpoint,
                "loopback_endpoint": loopback_endpoint,
                "allowed_hosts": ["localhost", "127.0.0.0/8", "::1"],
                "localhost_only_enforced": True,
                "server_reachability_requires_live_check": True,
            },
        )

    if engine in LOCAL_MODEL_PATH_REQUIRED_ENGINES:
        path = Path(model_path) if model_path else None
        add_check(
            "model_path_selected",
            path is not None,
            details={"model_path_present": path is not None},
        )
        if path is not None:
            add_check(
                "model_path_exists",
                path.exists(),
                details={"model_path": str(path), "is_dir": path.is_dir() if path.exists() else False},
            )
            if path.exists() and engine == "transformers_local":
                missing = _missing_transformers_files(path)
                add_check(
                    "transformers_local_files",
                    not missing,
                    details={"missing_files": missing, "local_files_only": True},
                )
            if path.exists() and engine == "llama_cpp_local":
                gguf_ready = (path.is_file() and path.suffix.casefold() == ".gguf") or (
                    path.is_dir() and any(child.suffix.casefold() == ".gguf" for child in path.iterdir())
                )
                add_check(
                    "llama_cpp_gguf_file",
                    gguf_ready,
                    details={"requires_gguf": True},
                )

    live_result: dict[str, Any] | None = None
    if live_check:
        live_result = invoke_llm_application_engine(
            runtime_config,
            manifest=_doctor_manifest(),
            task="Paideia LLM provider smoke test. Reply briefly with OK.",
            llm_mode="live",
            client=client,
        )
        add_check(
            "live_smoke",
            live_result.get("status") == "completed",
            details=_sanitize_runtime_result(live_result),
        )
    else:
        add_check(
            "live_smoke",
            True,
            severity="info",
            status="skipped",
            details={"reason": "live_check_not_requested", "network_call_made": False},
        )
    smoke_contract = _build_provider_smoke_contract(
        runtime_config,
        live_check_requested=live_check,
        live_result=live_result,
        client_override_used=client is not None,
    )
    add_check(
        "smoke_contract_verified",
        smoke_contract["status"] in {"passed", "skipped"},
        severity="error" if live_check else "info",
        status=smoke_contract["status"],
        details={
            "schema": smoke_contract["schema"],
            "provider_call_attempted": smoke_contract["provider_call_attempted"],
            "network_call_made_by_doctor": smoke_contract["network_call_made_by_doctor"],
            "raw_provider_payload_saved": smoke_contract["retention_policy"]["raw_provider_payload_saved"],
            "private_reasoning_trace": smoke_contract["data_policy"]["private_reasoning_trace"],
        },
    )

    blocking_failures = [
        check
        for check in checks
        if not check["passed"] and check["severity"] == "error"
    ]
    return {
        "schema": LLM_PROVIDER_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "service": service or engine,
        "model": model,
        "model_path": model_path,
        "live_check_requested": live_check,
        "passed": not blocking_failures,
        "status": "ready" if not blocking_failures else "needs_configuration",
        "network_access": runtime_config["network_access"],
        "local_only": runtime_config["local_only"],
        "secret_values_exported": False,
        "smoke_contract": smoke_contract,
        "checks": checks,
        "live_result": _sanitize_runtime_result(live_result) if live_result else None,
    }


def _provider_next_actions(doctor: dict[str, Any], *, engine: str, llm_mode: str) -> list[str]:
    checks = {check["id"]: check for check in doctor.get("checks", [])}
    actions: list[str] = []
    if llm_mode == "offline":
        actions.append("Switch to --llm-mode live or auto only when you intentionally want provider execution.")
    if not checks.get("credential_environment", {}).get("passed", True):
        required = checks["credential_environment"].get("details", {}).get("required", [])
        env_hint = " or ".join("/".join(group.get("one_of", [])) for group in required)
        actions.append(f"Set the required credential environment variable ({env_hint}) before live use.")
    if not checks.get("model_selected", {}).get("passed", True):
        actions.append("Pass --llm-model for this provider before live use.")
    if not checks.get("model_path_selected", {}).get("passed", True):
        actions.append("Pass --llm-model-path for this local model engine.")
    if not checks.get("model_path_exists", {}).get("passed", True):
        actions.append("Point --llm-model-path at an existing local model file or directory.")
    if engine in LOCAL_HTTP_ENGINES:
        actions.append("Start the selected localhost model server, then run doctor-llm-provider with --live-check.")
    elif engine in EXTERNAL_API_ENGINES:
        actions.append("Run doctor-llm-provider with --live-check only when you want a real API smoke call.")
    else:
        actions.append("Use offline mode for deterministic/local engines unless a model path is configured.")
    return list(dict.fromkeys(actions))


def build_llm_provider_preflight(
    runtime_config: dict[str, Any],
    *,
    llm_mode: str,
    llm_model: str | None = None,
) -> dict[str, Any]:
    """Build a no-network provider readiness packet to embed in runtime artifacts."""

    if runtime_config.get("schema") != RUNTIME_SCHEMA:
        raise ValueError("Unsupported LLM runtime config schema")
    if llm_mode not in {"offline", "auto", "live"}:
        raise ValueError("llm_mode must be offline, auto, or live")

    engine = runtime_config["engine"]
    effective_model = llm_model or runtime_config.get("model")
    model_path = runtime_config.get("model_path")
    doctor = doctor_llm_provider(
        engine=engine,
        model=effective_model,
        model_path=model_path,
        service=runtime_config.get("service"),
        live_check=False,
    )
    blocking_checks = [
        {
            "id": check["id"],
            "status": check["status"],
            "severity": check["severity"],
            "details": check.get("details", {}),
        }
        for check in doctor.get("checks", [])
        if not check.get("passed") and check.get("severity") == "error"
    ]
    live_path_selected = llm_mode in {"auto", "live"} and (
        engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES
    )
    if llm_mode == "offline":
        status = "skipped_offline"
    elif blocking_checks:
        status = "needs_configuration"
    elif live_path_selected:
        status = "ready_for_explicit_live_attempt"
    elif engine in LOCAL_MODEL_PATH_REQUIRED_ENGINES:
        status = "local_model_ready"
    else:
        status = "offline_or_deterministic_ready"

    return {
        "schema": LLM_PROVIDER_PREFLIGHT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "service": runtime_config.get("service", engine),
        "llm_mode": llm_mode,
        "model": effective_model,
        "model_path": model_path,
        "status": status,
        "provider_doctor_status": doctor["status"],
        "blocking_checks": blocking_checks,
        "live_path_selected": live_path_selected,
        "live_check_performed": False,
        "live_check_requires_explicit_flag": True,
        "network_call_made_by_preflight": False,
        "data_policy": {
            "send_private_training_files": False,
            "send_selected_memory_route_only": True,
            "secret_values_exported": False,
            "private_reasoning_trace": "do_not_store",
        },
        "doctor_summary": {
            "schema": doctor["schema"],
            "passed": doctor["passed"],
            "network_access": doctor["network_access"],
            "local_only": doctor["local_only"],
            "smoke_contract_status": doctor.get("smoke_contract", {}).get("status"),
            "check_statuses": [
                {
                    "id": check["id"],
                    "status": check["status"],
                    "passed": check["passed"],
                    "severity": check["severity"],
                }
                for check in doctor.get("checks", [])
            ],
        },
        "next_actions": _provider_next_actions(doctor, engine=engine, llm_mode=llm_mode),
    }


def _attach_provider_preflight(result: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    result.setdefault("llm_provider_preflight", preflight)
    return result


def invoke_llm_application_engine(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    client: LLMClient | None = None,
    policy_context: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if runtime_config.get("schema") != RUNTIME_SCHEMA:
        raise ValueError("Unsupported LLM runtime config schema")
    if llm_mode not in {"offline", "auto", "live"}:
        raise ValueError("llm_mode must be offline, auto, or live")

    effective_config = {**runtime_config}
    if llm_model:
        effective_config["model"] = llm_model

    engine = effective_config["engine"]
    model_path = effective_config.get("model_path")
    preflight = build_llm_provider_preflight(effective_config, llm_mode=llm_mode, llm_model=llm_model)
    if engine in {"bigram_local", "transformers_local", "llama_cpp_local"} and not model_path:
        return _attach_provider_preflight({
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": engine,
            "status": "unavailable",
            "reason": "model_path_required_for_local_model_engine",
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
        }, preflight)
    if llm_mode in {"auto", "live"} and (engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES):
        live_result = _invoke_live_client(
            effective_config,
            manifest=manifest,
            task=task,
            client=client,
            policy_context=policy_context,
            tools=tools,
        )
        _attach_provider_preflight(live_result, preflight)
        if live_result.get("status") == "completed" or llm_mode == "live":
            return live_result
        offline_result = _invoke_offline_or_local_engine(effective_config, manifest=manifest, task=task)
        return _attach_provider_preflight({
            **offline_result,
            "llm_mode": "auto",
            "live_attempt": live_result,
            "fallback_used": True,
        }, preflight)
    return _attach_provider_preflight(
        _invoke_offline_or_local_engine(effective_config, manifest=manifest, task=task),
        preflight,
    )


def run_llm_application_smoke(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    service: str | None = None,
    llm_mode: str = "offline",
    task: str = "Paideia application-engine smoke test. Reply with a short reviewable result.",
    client: LLMClient | None = None,
) -> dict[str, Any]:
    """Run the selected LLM through the Paideia application-engine path and return a public-safe report."""

    runtime_config = build_llm_runtime_config(
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
    )
    manifest = _doctor_manifest()
    runtime_result = invoke_llm_application_engine(
        runtime_config,
        manifest=manifest,
        task=task,
        llm_mode=llm_mode,
        llm_model=model,
        client=client,
        policy_context={
            "schema": "paideia-llm-application-smoke-policy/v1",
            "purpose": "verify_provider_as_language_engine_not_agent_identity",
            "store_raw_provider_text": False,
            "private_reasoning_trace": "do_not_store",
        },
        tools=[],
    )
    preflight = (
        runtime_result.get("llm_provider_preflight", {})
        if isinstance(runtime_result.get("llm_provider_preflight"), dict)
        else {}
    )
    llm_plan = runtime_result.get("llm_plan", {}) if isinstance(runtime_result.get("llm_plan"), dict) else {}
    client_result = (
        runtime_result.get("client_result", {})
        if isinstance(runtime_result.get("client_result"), dict)
        else {}
    )
    public_safe = (
        runtime_result.get("identity_policy") == "application_engine_not_identity"
        and llm_plan.get("raw_provider_text_stored") is not True
        and llm_plan.get("private_reasoning_trace") == "do_not_store"
        and client_result.get("private_reasoning_field_values_stored", False) is False
        and client_result.get("raw_output_saved", False) is False
    )
    llm_client_contract = (
        runtime_result.get("llm_client_contract", {})
        if isinstance(runtime_result.get("llm_client_contract"), dict)
        else {}
    )
    contract_safe = not llm_client_contract or llm_client_contract.get("status") == "passed"
    report = {
        "schema": LLM_APPLICATION_SMOKE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "service": service or engine,
        "model": model,
        "model_path_present": bool(model_path),
        "llm_mode": llm_mode,
        "status": (
            "passed"
            if runtime_result.get("status") == "completed" and public_safe and contract_safe
            else "failed"
        ),
        "passed": runtime_result.get("status") == "completed" and public_safe and contract_safe,
        "runtime_result": _sanitize_runtime_result(runtime_result),
        "runtime_contract": {
            "application_engine_only": runtime_result.get("identity_policy") == "application_engine_not_identity",
            "raw_provider_text_stored": llm_plan.get("raw_provider_text_stored") is True,
            "private_reasoning_trace": llm_plan.get("private_reasoning_trace"),
            "client_result_summary_only": bool(client_result) and "text" not in client_result,
            "client_result_private_reasoning_values_stored": client_result.get(
                "private_reasoning_field_values_stored",
                False,
            ),
            "llm_client_contract_schema": llm_client_contract.get("schema"),
            "llm_client_contract_status": llm_client_contract.get("status"),
            "llm_client_contract_summary_only": llm_client_contract.get("client_result_summary_only"),
            "llm_client_contract_raw_payload_saved": llm_client_contract.get("raw_provider_payload_saved"),
            "llm_client_contract_private_reasoning_values_stored": llm_client_contract.get(
                "private_reasoning_field_values_stored"
            ),
        },
        "llm_client_contract": llm_client_contract or None,
        "preflight": {
            "schema": preflight.get("schema"),
            "status": preflight.get("status"),
            "live_check_performed": preflight.get("live_check_performed"),
            "network_call_made_by_preflight": preflight.get("network_call_made_by_preflight"),
            "blocking_check_count": len(preflight.get("blocking_checks", [])),
        },
        "data_policy": {
            "secret_values_exported": False,
            "send_private_training_files": False,
            "send_full_session_replay": False,
            "private_reasoning_trace": "do_not_store",
            "raw_provider_payload_saved": False,
        },
    }
    return report


def _invoke_offline_or_local_engine(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
) -> dict[str, Any]:
    engine = runtime_config["engine"]
    model_path = runtime_config.get("model_path")
    if engine in {"bigram_local", "transformers_local", "llama_cpp_local"} and not model_path:
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": engine,
            "status": "unavailable",
            "reason": "model_path_required_for_local_model_engine",
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
        }
    if model_path and not Path(model_path).exists():
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": engine,
            "status": "unavailable",
            "reason": "local_model_path_not_found",
            "model_path": model_path,
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
        }
    if engine == "bigram_local":
        return _invoke_bigram_local(runtime_config, manifest=manifest, task=task)
    if engine == "transformers_local":
        return _invoke_transformers_local(runtime_config, manifest=manifest, task=task)
    if engine == "llama_cpp_local":
        return _inspect_llama_cpp_local(runtime_config)
    if engine == "openai_chatgpt_codex":
        return _invoke_openai_chatgpt_codex_bridge(runtime_config, manifest=manifest, task=task)
    if engine in (EXTERNAL_API_ENGINES - {"openai_chatgpt_codex"}) or engine in LOCAL_HTTP_ENGINES:
        return _invoke_configured_adapter_manifest(runtime_config, manifest=manifest, task=task)

    agent = manifest["agent"]
    prompt_fingerprint = _prompt_fingerprint(manifest=manifest, task=task)
    draft = (
        f"{agent['name']}은 자신의 학습 기록과 절차 원칙을 기준으로 "
        f"'{task}' 업무의 초안을 로컬 응용 엔진에서 구성한다."
    )
    llm_plan = build_reviewable_llm_plan(text=draft, task=task)
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": engine,
        "status": "completed",
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "prompt_fingerprint": prompt_fingerprint,
        "applied_as": "language_and_tool_reasoning_engine",
        "draft": llm_plan["assistant_reply"],
        "llm_plan": llm_plan,
    }


def _invoke_live_client(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
    client: LLMClient | None = None,
    policy_context: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    llm_client = client or build_llm_client(runtime_config)
    messages = build_runtime_messages(manifest=manifest, task=task, policy_context=policy_context)
    if hasattr(llm_client, "generate_result"):
        typed_result = llm_client.generate_result(messages, tools=tools or [], policy=policy_context or {})
        client_result = typed_result.to_public_artifact()
        typed_result_contract_used = True
    else:
        client_result = llm_client.generate(messages, tools=tools or [], policy=policy_context or {})
        typed_result_contract_used = False
    original_client_result_keys = set(client_result)
    private_reasoning_fields_omitted = count_private_reasoning_fields(client_result)
    client_result = sanitize_llm_result_packet(client_result)
    client_result_summary = _client_result_for_runtime_storage(
        client_result,
        original_keys=original_client_result_keys,
        private_reasoning_fields_omitted=private_reasoning_fields_omitted,
    )
    engine = runtime_config["engine"]
    llm_client_contract = _build_llm_client_contract(
        runtime_config,
        runtime_status="completed" if client_result.get("status") == "completed" else "unavailable",
        client_result_summary=client_result_summary,
        client_override_used=client is not None,
        typed_result_contract_used=typed_result_contract_used,
    )
    if client_result.get("status") != "completed":
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": engine,
            "status": "unavailable",
            "reason": client_result.get("reason", "llm_client_unavailable"),
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
            "llm_mode": "live",
            "client_result": client_result_summary,
            "llm_client_contract": llm_client_contract,
        }
    llm_plan = build_reviewable_llm_plan(
        text=str(client_result.get("text", "")),
        task=task,
        tools=tools,
    )
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": engine,
        "status": "completed",
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "applied_as": "live_language_and_tool_reasoning_engine",
        "prompt_fingerprint": _prompt_fingerprint(manifest=manifest, task=task),
        "llm_mode": "live",
        "model": client_result.get("model") or runtime_config.get("model"),
        "draft": llm_plan["assistant_reply"],
        "llm_plan": llm_plan,
        "client_result": client_result_summary,
        "llm_client_contract": llm_client_contract,
        "data_policy": {
            "send_private_training_files": False,
            "send_selected_memory_route_only": True,
            "store_hidden_chain_of_thought": False,
            "store_raw_client_result_text": False,
        },
    }


def _client_result_for_runtime_storage(
    client_result: dict[str, Any],
    *,
    original_keys: set[str] | None = None,
    private_reasoning_fields_omitted: int = 0,
) -> dict[str, Any]:
    summary = {
        key: client_result[key]
        for key in CLIENT_RESULT_RUNTIME_SUMMARY_KEYS
        if key in client_result
    }
    private_reasoning_omitted_keys = {
        key
        for key in original_keys or set()
        if count_private_reasoning_fields({key: "omitted_private_reasoning"}) > 0
    }
    omitted_keys = sorted(
        key
        for key in (original_keys or set(client_result))
        if key not in CLIENT_RESULT_RUNTIME_SUMMARY_KEYS and key not in private_reasoning_omitted_keys
    )
    if "text" in client_result:
        summary["text_omitted"] = True
    summary.setdefault("raw_output_saved", False)
    if omitted_keys:
        summary["omitted_keys"] = omitted_keys
    if private_reasoning_fields_omitted:
        summary["private_reasoning_fields_omitted"] = private_reasoning_fields_omitted
    summary["private_reasoning_field_values_stored"] = False
    summary["retention_policy"] = "summary_without_provider_text_or_debug_payload"
    return summary


def _build_llm_client_contract(
    runtime_config: dict[str, Any],
    *,
    runtime_status: str,
    client_result_summary: dict[str, Any],
    client_override_used: bool,
    typed_result_contract_used: bool = False,
) -> dict[str, Any]:
    private_values_stored = client_result_summary.get("private_reasoning_field_values_stored", False)
    raw_output_saved = client_result_summary.get("raw_output_saved", False)
    summary_only = "text" not in client_result_summary
    safe = summary_only and raw_output_saved is False and private_values_stored is False
    return {
        "schema": LLM_CLIENT_CONTRACT_SCHEMA,
        "status": "passed" if safe else "failed",
        "engine": runtime_config["engine"],
        "service": runtime_config.get("service", runtime_config["engine"]),
        "model": client_result_summary.get("model") or runtime_config.get("model"),
        "llm_mode": "live",
        "runtime_status": runtime_status,
        "client_result_status": client_result_summary.get("status"),
        "client_executor": "injected_client" if client_override_used else "built_in_client",
        "client_override_used": client_override_used,
        "typed_result_contract_used": typed_result_contract_used,
        "application_engine_only": runtime_config.get("identity_policy") == "application_engine_not_identity",
        "network_access": runtime_config.get("network_access"),
        "network_call_requires_explicit_live_check": True,
        "secret_values_exported": False,
        "send_private_training_files": False,
        "send_full_session_replay": False,
        "send_selected_memory_route_only": True,
        "client_result_summary_only": summary_only,
        "text_omitted": client_result_summary.get("text_omitted") is True,
        "omitted_keys": client_result_summary.get("omitted_keys", []),
        "raw_provider_text_saved": False,
        "raw_provider_payload_saved": False,
        "raw_output_saved": raw_output_saved,
        "private_reasoning_fields_omitted": client_result_summary.get("private_reasoning_fields_omitted", 0),
        "private_reasoning_field_values_stored": private_values_stored,
        "private_reasoning_trace": "do_not_store",
        "retention_policy": client_result_summary.get(
            "retention_policy",
            "summary_without_provider_text_or_debug_payload",
        ),
    }


def _compact_text(value: Any, *, limit: int = 1200) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _json_object_from_text(text: str) -> tuple[dict[str, Any] | None, str]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            return None, "plain_text_fallback"
        try:
            data = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return None, "plain_text_fallback"
    if isinstance(data, dict):
        return data, "json_object"
    return None, "plain_text_fallback"


def _normalize_reasoning_summary(value: Any, *, task: str, source: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if isinstance(value, list):
        for index, item in enumerate(value, start=1):
            if isinstance(item, dict):
                step = item.get("step") or item.get("id") or item.get("title") or f"step_{index}"
                summary = item.get("summary") or item.get("reason") or item.get("evidence") or item
            else:
                step = f"step_{index}"
                summary = item
            items.append({"step": _compact_text(step, limit=80), "summary": _compact_text(summary, limit=300)})
    elif value:
        items.append({"step": "summary", "summary": _compact_text(value, limit=300)})
    if items:
        return items[:6]
    return [
        {
            "step": "request_understood",
            "summary": _compact_text(f"요청 '{task}'을 실행 전 검토 가능한 업무 단위로 정리했습니다.", limit=300),
        },
        {
            "step": "policy_and_evidence_first",
            "summary": "정책 게이트, 근거 확인, 보스 검토 가능한 산출물 생성을 우선합니다.",
        },
        {
            "step": "plan_source",
            "summary": f"LLM 출력은 {source} 경로로 정규화되었고 숨은 추론 원문은 저장하지 않습니다.",
        },
    ]


def _normalize_string_list(value: Any, *, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        normalized = [_compact_text(item, limit=220) for item in value if str(item).strip()]
        if normalized:
            return normalized[:6]
    if isinstance(value, str) and value.strip():
        return [_compact_text(value, limit=220)]
    return fallback


def _normalize_tool_plan(value: Any, *, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    available = {
        str(item.get("id") or item.get("name"))
        for item in tools or []
        if item.get("id") or item.get("name")
    }
    raw_items = value if isinstance(value, list) else []
    if not raw_items:
        raw_items = [
            {
                "tool": item.get("id") or item.get("name"),
                "purpose": item.get("description", "candidate tool for registered execution loop"),
            }
            for item in tools or []
        ]
    normalized: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, dict):
            tool = str(item.get("tool") or item.get("name") or item.get("id") or "").strip()
            purpose = item.get("purpose") or item.get("reason") or item.get("description") or "candidate tool"
            requires_approval = bool(item.get("requires_boss_approval", False))
        else:
            tool = str(item).strip()
            purpose = "candidate tool"
            requires_approval = False
        if not tool:
            continue
        normalized.append(
            {
                "tool": _compact_text(tool, limit=80),
                "purpose": _compact_text(purpose, limit=220),
                "registration_status": "registered" if tool in available else "not_in_selected_tool_set",
                "execution_policy": "suggestion_only_registered_executor_decides",
                "requires_boss_approval": requires_approval,
            }
        )
    return normalized[:8]


def build_reviewable_llm_plan(
    *,
    text: str,
    task: str,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    parsed, source = _json_object_from_text(text)
    assistant_reply = text
    reasoning_value: Any = None
    next_actions_value: Any = None
    tool_plan_value: Any = None
    if parsed is not None:
        assistant_reply = str(
            parsed.get("assistant_reply")
            or parsed.get("answer")
            or parsed.get("draft")
            or parsed.get("summary")
            or text
        )
        reasoning_value = parsed.get("reviewable_reasoning_summary") or parsed.get("reasoning_summary")
        next_actions_value = parsed.get("suggested_next_actions") or parsed.get("next_actions")
        tool_plan_value = parsed.get("tool_plan") or parsed.get("tool_use_suggestions")
    return {
        "schema": LLM_REVIEWABLE_PLAN_SCHEMA,
        "source": source,
        "assistant_reply": _compact_text(assistant_reply, limit=1800),
        "reviewable_reasoning_summary": _normalize_reasoning_summary(
            reasoning_value,
            task=task,
            source=source,
        ),
        "suggested_next_actions": _normalize_string_list(
            next_actions_value,
            fallback=[
                "근거와 정책 경계를 먼저 검토합니다.",
                "필요한 산출물은 등록된 로컬 도구와 workspace artifact로만 남깁니다.",
                "학습 승격은 보스 또는 감독위원회 검토 뒤에만 진행합니다.",
            ],
        ),
        "tool_plan": _normalize_tool_plan(tool_plan_value, tools=tools),
        "tool_plan_policy": "suggestions_only_registered_executor_decides",
        "private_reasoning_trace": "do_not_store",
        "raw_provider_text_stored": False,
    }


def _build_provider_smoke_contract(
    runtime_config: dict[str, Any],
    *,
    live_check_requested: bool,
    live_result: dict[str, Any] | None,
    client_override_used: bool = False,
) -> dict[str, Any]:
    live_check_performed = live_result is not None
    engine = runtime_config["engine"]
    provider_call_attempted = live_check_performed and engine in EXTERNAL_API_ENGINES.union(LOCAL_HTTP_ENGINES)
    client_summary = {}
    if isinstance(live_result, dict) and isinstance(live_result.get("client_result"), dict):
        client = live_result["client_result"]
        client_summary = {
            "schema": client.get("schema"),
            "engine": client.get("engine"),
            "status": client.get("status"),
            "reason": client.get("reason"),
            "model": client.get("model"),
            "text_omitted": client.get("text_omitted") is True,
            "omitted_keys": client.get("omitted_keys", []),
            "raw_output_saved": client.get("raw_output_saved"),
            "private_reasoning_fields_omitted": client.get("private_reasoning_fields_omitted", 0),
            "private_reasoning_field_values_stored": client.get("private_reasoning_field_values_stored", False),
            "retention_policy": client.get("retention_policy"),
        }
    live_status = live_result.get("status") if isinstance(live_result, dict) else None
    runtime_reason = live_result.get("reason") if isinstance(live_result, dict) else None
    client_reason = client_summary.get("reason")
    no_transport_reason = _no_transport_reason(runtime_reason or client_reason)
    network_call_made_by_doctor = bool(
        provider_call_attempted
        and not client_override_used
        and no_transport_reason is None
    )
    if not live_check_requested:
        status = "skipped"
    elif live_status == "completed":
        status = "passed"
    else:
        status = "failed"
    return {
        "schema": LLM_PROVIDER_SMOKE_CONTRACT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "service": runtime_config.get("service", engine),
        "model": runtime_config.get("model"),
        "live_check_requested": live_check_requested,
        "live_check_performed": live_check_performed,
        "provider_call_attempted": provider_call_attempted,
        "provider_call_executor": "injected_client" if client_override_used else "built_in_client",
        "client_override_used": client_override_used,
        "network_call_made_by_doctor": network_call_made_by_doctor,
        "network_call_blocked_before_transport": bool(
            provider_call_attempted
            and not client_override_used
            and no_transport_reason is not None
        ),
        "network_call_block_reason": no_transport_reason,
        "network_call_delegated_to_client_override": provider_call_attempted and client_override_used,
        "network_policy": "no_network_without_explicit_live_check",
        "data_policy": {
            "send_private_training_files": False,
            "send_full_session_replay": False,
            "send_selected_memory_route_only": True,
            "secret_values_exported": False,
            "private_reasoning_trace": "do_not_store",
        },
        "retention_policy": {
            "raw_provider_text_saved": False,
            "raw_provider_payload_saved": False,
            "client_result_summary_only": True,
            "hidden_reasoning_saved": False,
        },
        "result_summary": {
            "runtime_status": live_status,
            "runtime_reason": runtime_reason,
            "runtime_identity_policy": live_result.get("identity_policy") if isinstance(live_result, dict) else None,
            "client_result": client_summary,
        },
        "failure_mode": (
            "not_requested"
            if not live_check_requested
            else "none"
            if status == "passed"
            else "fail_closed_unavailable"
        ),
        "status": status,
    }


def _no_transport_reason(reason: Any) -> str | None:
    """Return why a built-in provider client stopped before network transport."""

    text = str(reason or "")
    if not text:
        return None
    if text.endswith("_not_set") or "_KEY_not_set" in text or "API_KEY" in text and text.endswith("_not_set"):
        return "credential_not_set"
    if text in {"model_required_for_live_provider", "local_model_path_not_found"}:
        return text
    if text.endswith("_import_failed"):
        return "client_sdk_import_failed"
    return None


def _invoke_bigram_local(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
) -> dict[str, Any]:
    model_path = Path(runtime_config["model_path"])
    try:
        model = load_model(model_path)
    except Exception as exc:
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": "bigram_local",
            "status": "unavailable",
            "reason": "bigram_checkpoint_load_failed",
            "model_path": str(model_path),
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
            "local_files_only": True,
        }

    if model.get("model_type") != "character_bigram" or "counts" not in model or "vocab" not in model:
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": "bigram_local",
            "status": "unavailable",
            "reason": "invalid_bigram_checkpoint",
            "model_path": str(model_path),
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
            "local_files_only": True,
        }

    seed = manifest["agent"]["name"]
    draft = generate_text(model, seed=seed, length=160, random_seed=22)
    llm_plan = build_reviewable_llm_plan(text=draft, task=task)
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": "bigram_local",
        "status": "completed",
        "model_path": str(model_path),
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "local_files_only": True,
        "applied_as": "from_scratch_language_draft_engine",
        "draft": llm_plan["assistant_reply"],
        "llm_plan": llm_plan,
        "prompt_fingerprint": _prompt_fingerprint(manifest=manifest, task=task),
    }


def _missing_transformers_files(model_path: Path) -> list[str]:
    missing: list[str] = []
    for group_files in TRANSFORMERS_REQUIRED_FILE_GROUPS.values():
        if not any((model_path / name).exists() for name in group_files):
            missing.append(group_files[0])
    return missing


def _invoke_transformers_local(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
) -> dict[str, Any]:
    model_path = Path(runtime_config["model_path"])
    missing_files = _missing_transformers_files(model_path)
    if missing_files:
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": "transformers_local",
            "status": "unavailable",
            "reason": "local_model_files_missing",
            "model_path": str(model_path),
            "missing_files": missing_files,
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
            "local_files_only": True,
        }

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(str(model_path), local_files_only=True)
        prompt = _build_runtime_prompt(manifest=manifest, task=task)
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=64, do_sample=False)
        text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as exc:  # Transformers error types vary by version and model files.
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": "transformers_local",
            "status": "unavailable",
            "reason": "transformers_local_load_failed",
            "model_path": str(model_path),
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
            "local_files_only": True,
        }

    llm_plan = build_reviewable_llm_plan(text=text, task=task)
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": "transformers_local",
        "status": "completed",
        "model_path": str(model_path),
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "local_files_only": True,
        "applied_as": "language_and_tool_reasoning_engine",
        "draft": llm_plan["assistant_reply"],
        "llm_plan": llm_plan,
        "prompt_fingerprint": _prompt_fingerprint(manifest=manifest, task=task),
    }


def _inspect_llama_cpp_local(runtime_config: dict[str, Any]) -> dict[str, Any]:
    model_path = Path(runtime_config["model_path"])
    if model_path.is_dir():
        gguf_files = sorted(path.name for path in model_path.glob("*.gguf"))
        if not gguf_files:
            return {
                "schema": RUNTIME_RESULT_SCHEMA,
                "engine": "llama_cpp_local",
                "status": "unavailable",
                "reason": "gguf_model_file_missing",
                "model_path": str(model_path),
                "identity_policy": runtime_config["identity_policy"],
                "network_access": runtime_config["network_access"],
            }
        model_file = model_path / gguf_files[0]
    else:
        model_file = model_path
        if model_file.suffix.casefold() != ".gguf":
            return {
                "schema": RUNTIME_RESULT_SCHEMA,
                "engine": "llama_cpp_local",
                "status": "unavailable",
                "reason": "gguf_model_file_required",
                "model_path": str(model_path),
                "identity_policy": runtime_config["identity_policy"],
                "network_access": runtime_config["network_access"],
            }

    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": "llama_cpp_local",
        "status": "ready_to_load",
        "model_path": str(model_file),
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "local_files_only": True,
    }


def _invoke_openai_chatgpt_codex_bridge(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
) -> dict[str, Any]:
    agent = manifest["agent"]
    draft = (
        f"{agent['name']} uses the local manifest, learning ledger, and memory substrate as identity "
        f"and reasoning context. OpenAI ChatGPT Codex supplies language generation only for: {task}"
    )
    llm_plan = build_reviewable_llm_plan(text=draft, task=task)
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": "openai_chatgpt_codex",
        "status": "bridge_context_prepared",
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "applied_as": "language_and_tool_reasoning_engine_only",
        "prompt_fingerprint": _prompt_fingerprint(manifest=manifest, task=task),
        "data_policy": {
            "send_private_training_files": False,
            "send_selected_memory_route_only": True,
            "api_key_storage": "not_required_by_this_bridge",
        },
        "model": runtime_config.get("model"),
        "draft": llm_plan["assistant_reply"],
        "llm_plan": llm_plan,
    }


def _invoke_configured_adapter_manifest(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
) -> dict[str, Any]:
    agent = manifest["agent"]
    engine = runtime_config["engine"]
    is_local_http = engine in LOCAL_HTTP_ENGINES
    draft = (
        f"{agent['name']} is ready to use {engine} as the selected LLM adapter. "
        f"Paideia keeps identity and learned routes in local records; the adapter supplies language generation for: {task}"
    )
    llm_plan = build_reviewable_llm_plan(text=draft, task=task)
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": engine,
        "status": "adapter_manifest_ready",
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "applied_as": "language_and_tool_reasoning_engine_only_when_configured",
        "prompt_fingerprint": _prompt_fingerprint(manifest=manifest, task=task),
        "data_policy": {
            "send_private_training_files": False,
            "send_selected_memory_route_only": True,
            "requires_user_configured_key_or_local_server": True,
            "local_http_only": is_local_http,
        },
        "model": runtime_config.get("model"),
        "draft": llm_plan["assistant_reply"],
        "llm_plan": llm_plan,
    }


def _doctor_manifest() -> dict[str, Any]:
    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "paideia-provider-doctor",
            "role": "LLM provider readiness checker",
            "major_goal": "Verify the selected application engine without becoming the agent identity.",
        },
        "memory_profile": {
            "procedural_principles": ["identity stays in local records", "do not store hidden chain-of-thought"],
            "semantic_themes": ["provider readiness", "public-safe diagnostic"],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
    }


def _sanitize_runtime_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if result is None:
        return None
    safe_keys = {
        "schema",
        "engine",
        "status",
        "reason",
        "model",
        "model_path",
        "network_access",
        "identity_policy",
        "llm_mode",
        "fallback_used",
        "local_files_only",
    }
    sanitized = {key: result[key] for key in safe_keys if key in result}
    client_result = result.get("client_result")
    if isinstance(client_result, dict):
        sanitized["client_result"] = {
            key: client_result[key]
            for key in [
                "schema",
                "engine",
                "status",
                "reason",
                "model",
                "endpoint",
                "error_type",
                "network_access",
                "local_files_only",
                "text_omitted",
                "omitted_keys",
                "raw_output_saved",
                "private_reasoning_fields_omitted",
                "private_reasoning_field_values_stored",
                "retention_policy",
            ]
            if key in client_result
        }
    client_contract = result.get("llm_client_contract")
    if isinstance(client_contract, dict):
        sanitized["llm_client_contract"] = {
            key: client_contract[key]
            for key in [
                "schema",
                "status",
                "engine",
                "service",
                "model",
                "llm_mode",
                "runtime_status",
                "client_result_status",
                "client_executor",
                "client_override_used",
                "typed_result_contract_used",
                "application_engine_only",
                "network_access",
                "client_result_summary_only",
                "text_omitted",
                "raw_provider_text_saved",
                "raw_provider_payload_saved",
                "raw_output_saved",
                "private_reasoning_fields_omitted",
                "private_reasoning_field_values_stored",
                "private_reasoning_trace",
                "retention_policy",
            ]
            if key in client_contract
        }
    return sanitized


def _build_runtime_prompt(*, manifest: dict[str, Any], task: str) -> str:
    agent = manifest["agent"]
    principles = ", ".join(manifest.get("memory_profile", {}).get("procedural_principles", []))
    return (
        f"이름: {agent['name']}\n"
        f"전공 목표: {agent.get('major_goal')}\n"
        f"절차 원칙: {principles}\n"
        f"업무: {task}\n"
        "정체성은 학적, 고용 계약, 기억 프로필에서 오며 LLM은 응용 엔진이다.\n"
        "답변:"
    )


def _prompt_fingerprint(*, manifest: dict[str, Any], task: str) -> str:
    agent = manifest["agent"]
    return hashlib.sha256(f"{agent['name']}|{agent.get('major_goal')}|{task}".encode("utf-8")).hexdigest()[:16]
