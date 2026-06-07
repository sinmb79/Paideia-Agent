from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.llm_clients import (
    LLMResult,
    SECRET_ENV_KEYS,
    build_llm_client,
    build_runtime_messages,
    count_private_reasoning_fields,
    sanitize_llm_result_packet,
)
from ai22b.talent_foundry.llm_runtime import (
    EXTERNAL_API_ENGINES,
    LOCAL_HTTP_ENGINES,
    LLM_PROVIDER_PREFLIGHT_SCHEMA,
    build_llm_provider_preflight,
    build_llm_runtime_config,
    run_llm_application_smoke,
)


LLM_ADAPTER_CONTRACTS_SCHEMA = "paideia-llm-adapter-contracts/v1"
CLIENT_RESULT_SCHEMA = "paideia-llm-client-result/v1"

EXPECTED_DIRECT_CLIENTS = {
    "deterministic_local": "DeterministicClient",
    "openai_chatgpt_codex": "OpenAIResponsesClient",
    "anthropic_claude_api": "AnthropicMessagesClient",
    "google_gemini_api": "GeminiGenerateContentClient",
    "mistral_api": "OpenAICompatibleChatClient",
    "openrouter_api": "OpenAICompatibleChatClient",
    "ollama_local_http": "OllamaClient",
    "lm_studio_local_http": "LMStudioClient",
    "transformers_local": "TransformersLocalClient",
}
RUNTIME_ONLY_LOCAL_ENGINES = {
    "bigram_local",
    "llama_cpp_local",
}
EXTERNAL_SAMPLE_MODELS = {
    "openai_chatgpt_codex": "gpt-4.1-mini",
    "anthropic_claude_api": "claude-3-5-sonnet-latest",
    "google_gemini_api": "gemini-1.5-flash",
    "mistral_api": "mistral-small-latest",
    "openrouter_api": "openai/gpt-4.1-mini",
}
LOCAL_HTTP_SAMPLE_MODELS = {
    "ollama_local_http": "llama3.1",
    "lm_studio_local_http": "local-model",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _doctor_manifest() -> dict[str, Any]:
    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "paideia-llm-adapter-contract-agent",
            "role": "public-safe LLM adapter contract doctor fixture",
            "major_goal": "Verify LLM adapters before user-facing agent work.",
        },
        "memory_profile": {
            "procedural_principles": [
                "LLM providers are language engines, not the agent identity.",
                "Do not store raw provider text or hidden reasoning traces.",
            ],
            "semantic_themes": ["LLM adapter contracts", "fail closed", "local-first readiness"],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
        "llm_policy": {
            "role": "application_engine_not_identity",
            "private_reasoning_trace": "do_not_store",
        },
        "tool_policy": {
            "allowed_tools": ["work_session", "evidence_packet", "assessment"],
            "blocked_tools": ["external_upload", "financial_action", "personal_data_transfer"],
        },
    }


@contextmanager
def _temporarily_cleared_env(keys: list[str] | tuple[str, ...]) -> Iterator[None]:
    old_values = {key: os.environ.get(key) for key in keys}
    try:
        for key in keys:
            os.environ.pop(key, None)
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _json_clean(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _client_class_for(engine: str, *, model: str | None = None, model_path: str | None = None) -> str:
    runtime_config = build_llm_runtime_config(engine=engine, model=model, model_path=model_path)
    return type(build_llm_client(runtime_config)).__name__


def _client_factory_contract() -> dict[str, Any]:
    cases = []
    failures = []
    for engine, expected_class in EXPECTED_DIRECT_CLIENTS.items():
        model = EXTERNAL_SAMPLE_MODELS.get(engine) or LOCAL_HTTP_SAMPLE_MODELS.get(engine)
        model_path = "__missing_transformers_contract_model__" if engine == "transformers_local" else None
        actual_class = _client_class_for(engine, model=model, model_path=model_path)
        passed = actual_class == expected_class
        cases.append(
            {
                "engine": engine,
                "expected_class": expected_class,
                "actual_class": actual_class,
                "passed": passed,
            }
        )
        if not passed:
            failures.append(engine)

    runtime_only = []
    for engine in sorted(RUNTIME_ONLY_LOCAL_ENGINES):
        runtime_config = build_llm_runtime_config(
            engine=engine,
            model_path=str(PROJECT_ROOT / "models" / f"__missing_{engine}_contract_model__"),
        )
        preflight = build_llm_provider_preflight(runtime_config, llm_mode="offline")
        runtime_only.append(
            {
                "engine": engine,
                "runtime_config_schema": runtime_config.get("schema"),
                "preflight_schema": preflight.get("schema"),
                "preflight_network_call_made": preflight.get("network_call_made_by_preflight"),
                "contract": "runtime_path_only_until_direct_client_is_added",
            }
        )
    return {
        "id": "client_factory_contract",
        "status": "passed" if not failures else "failed",
        "passed": not failures,
        "cases": cases,
        "runtime_only_engines": runtime_only,
        "failure_count": len(failures),
        "failures": failures,
    }


def _deterministic_contract() -> dict[str, Any]:
    manifest = _doctor_manifest()
    runtime_config = build_llm_runtime_config(engine="deterministic_local")
    client = build_llm_client(runtime_config)
    typed_result = client.generate_result(
        build_runtime_messages(
            manifest=manifest,
            task="Verify deterministic adapter contract.",
        ),
        tools=[{"name": "evidence_packet"}],
        policy={"mode": "public_safe_contract"},
    )
    result = typed_result.to_public_artifact()
    private_fields = count_private_reasoning_fields(result)
    serialized = _json_clean(result)
    passed = (
        isinstance(typed_result, LLMResult)
        and result.get("schema") == CLIENT_RESULT_SCHEMA
        and result.get("status") == "completed"
        and result.get("identity_policy") == "application_engine_not_identity"
        and result.get("network_access") == "blocked"
        and result.get("raw_output_saved") is False
        and private_fields == 0
    )
    return {
        "id": "deterministic_generate_contract",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "engine": "deterministic_local",
        "result_status": result.get("status"),
        "network_access": result.get("network_access"),
        "raw_output_saved": result.get("raw_output_saved"),
        "typed_result_contract_used": isinstance(typed_result, LLMResult),
        "private_reasoning_field_count": private_fields,
        "serialized_result_chars": len(serialized),
    }


def _external_fail_closed_contract() -> dict[str, Any]:
    manifest = _doctor_manifest()
    cases = []
    with _temporarily_cleared_env(SECRET_ENV_KEYS):
        for engine in sorted(EXTERNAL_API_ENGINES):
            runtime_config = build_llm_runtime_config(engine=engine, model=EXTERNAL_SAMPLE_MODELS[engine])
            client = build_llm_client(runtime_config)
            typed_result = client.generate_result(
                build_runtime_messages(
                    manifest=manifest,
                    task=f"Verify {engine} missing-credential contract.",
                ),
                tools=[],
                policy={"mode": "public_safe_contract"},
            )
            result = typed_result.to_public_artifact()
            sanitized = sanitize_llm_result_packet(result)
            serialized = _json_clean(sanitized)
            reason = str(sanitized.get("reason", ""))
            passed = (
                isinstance(typed_result, LLMResult)
                and sanitized.get("schema") == CLIENT_RESULT_SCHEMA
                and sanitized.get("status") == "unavailable"
                and (
                    "not_set" in reason
                    or reason == "openai_sdk_import_failed"
                    or reason == "openai_responses_call_failed"
                )
                and count_private_reasoning_fields(sanitized) == 0
                and "[REDACTED_SECRET]" not in serialized
            )
            cases.append(
                {
                    "engine": engine,
                    "client_class": type(client).__name__,
                    "status": sanitized.get("status"),
                    "reason": reason,
                    "model": sanitized.get("model"),
                    "network_call_attempted": False,
                    "raw_provider_payload_saved": False,
                    "typed_result_contract_used": isinstance(typed_result, LLMResult),
                    "private_reasoning_field_count": count_private_reasoning_fields(sanitized),
                    "passed": passed,
                }
            )
    failures = [case["engine"] for case in cases if not case["passed"]]
    return {
        "id": "external_api_missing_credentials_fail_closed",
        "status": "passed" if not failures else "failed",
        "passed": not failures,
        "credential_env_temporarily_cleared": True,
        "network_call_performed": False,
        "case_count": len(cases),
        "cases": cases,
        "failures": failures,
    }


def _localhost_contract() -> dict[str, Any]:
    cases = []
    for engine in sorted(LOCAL_HTTP_ENGINES):
        runtime_config = build_llm_runtime_config(
            engine=engine,
            model=LOCAL_HTTP_SAMPLE_MODELS[engine],
        )
        client_class = type(build_llm_client(runtime_config)).__name__
        preflight = build_llm_provider_preflight(runtime_config, llm_mode="live")
        passed = (
            preflight.get("schema") == LLM_PROVIDER_PREFLIGHT_SCHEMA
            and preflight.get("network_call_made_by_preflight") is False
            and preflight.get("live_check_performed") is False
            and preflight.get("live_check_requires_explicit_flag") is True
            and runtime_config.get("network_access") == "localhost_only"
        )
        cases.append(
            {
                "engine": engine,
                "client_class": client_class,
                "preflight_status": preflight.get("status"),
                "network_access": runtime_config.get("network_access"),
                "network_call_performed": False,
                "live_check_performed": preflight.get("live_check_performed"),
                "live_check_requires_explicit_flag": preflight.get("live_check_requires_explicit_flag"),
                "passed": passed,
            }
        )
    failures = [case["engine"] for case in cases if not case["passed"]]
    return {
        "id": "localhost_adapters_explicit_live_contract",
        "status": "passed" if not failures else "failed",
        "passed": not failures,
        "case_count": len(cases),
        "cases": cases,
        "failures": failures,
    }


def _local_model_contract() -> dict[str, Any]:
    missing_path = PROJECT_ROOT / "models" / "__paideia_missing_transformers_contract_model__"
    runtime_config = build_llm_runtime_config(engine="transformers_local", model_path=str(missing_path))
    client = build_llm_client(runtime_config)
    typed_result = client.generate_result(
        build_runtime_messages(
            manifest=_doctor_manifest(),
            task="Verify local Transformers missing-model contract.",
        ),
        tools=[],
        policy={"mode": "public_safe_contract"},
    )
    result = typed_result.to_public_artifact()
    smoke_without_path = run_llm_application_smoke(
        engine="bigram_local",
        llm_mode="offline",
        task="Verify local model engines fail closed when a model path is missing.",
    )
    passed = (
        isinstance(typed_result, LLMResult)
        and result.get("schema") == CLIENT_RESULT_SCHEMA
        and result.get("status") == "unavailable"
        and result.get("reason") == "local_model_path_not_found"
        and result.get("local_files_only") is True
        and result.get("network_access") == "blocked"
        and smoke_without_path.get("passed") is False
        and smoke_without_path.get("runtime_result", {}).get("status") == "unavailable"
    )
    return {
        "id": "local_model_missing_path_fail_closed",
        "status": "passed" if passed else "failed",
        "passed": passed,
        "transformers_client_status": result.get("status"),
        "transformers_reason": result.get("reason"),
        "transformers_local_files_only": result.get("local_files_only"),
        "transformers_network_access": result.get("network_access"),
        "typed_result_contract_used": isinstance(typed_result, LLMResult),
        "runtime_local_model_without_path_passed": smoke_without_path.get("passed"),
        "runtime_local_model_without_path_status": smoke_without_path.get("runtime_result", {}).get("status")
        if isinstance(smoke_without_path.get("runtime_result"), dict)
        else None,
        "network_call_performed": False,
    }


def run_llm_adapter_contracts() -> dict[str, Any]:
    """Run public-safe LLM adapter contract checks without live provider calls."""

    checks = [
        _client_factory_contract(),
        _deterministic_contract(),
        _external_fail_closed_contract(),
        _localhost_contract(),
        _local_model_contract(),
    ]
    failed = [check for check in checks if not check.get("passed")]
    direct_engines = sorted(EXPECTED_DIRECT_CLIENTS)
    report = {
        "schema": LLM_ADAPTER_CONTRACTS_SCHEMA,
        "created_at_utc": _now(),
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "summary": {
            "direct_adapter_count": len(direct_engines),
            "direct_adapter_engines": direct_engines,
            "runtime_only_local_engines": sorted(RUNTIME_ONLY_LOCAL_ENGINES),
            "failed_count": len(failed),
            "network_call_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
        "checks": checks,
        "public_safe": {
            "network_call_performed": False,
            "localhost_call_performed": False,
            "external_provider_called": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "private_training_files_sent": False,
            "full_session_replay_sent": False,
        },
        "data_policy": {
            "llm_is_identity": False,
            "identity_policy": "application_engine_not_identity",
            "live_provider_calls_require_explicit_live_check": True,
            "missing_credentials_fail_closed": True,
            "localhost_servers_not_contacted_by_doctor": True,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
    }
    return report


def write_llm_adapter_contracts(path: Path) -> dict[str, Any]:
    report = run_llm_adapter_contracts()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
