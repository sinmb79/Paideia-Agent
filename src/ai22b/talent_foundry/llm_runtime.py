from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.from_scratch.bigram import generate_text, load_model
from ai22b.talent_foundry.llm_clients import (
    LLMClient,
    build_llm_client,
    build_runtime_messages,
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
        add_check(
            "local_http_endpoint",
            True,
            severity="warning",
            details={
                "endpoint": model_path or default_endpoint,
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
        "checks": checks,
        "live_result": _sanitize_runtime_result(live_result) if live_result else None,
    }


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
    model_path = runtime_config.get("model_path")
    model = effective_config.get("model")
    if engine in {"bigram_local", "transformers_local", "llama_cpp_local"} and not model_path:
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": engine,
            "status": "unavailable",
            "reason": "model_path_required_for_local_model_engine",
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
        }
    if llm_mode in {"auto", "live"} and (engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES):
        live_result = _invoke_live_client(
            effective_config,
            manifest=manifest,
            task=task,
            client=client,
            policy_context=policy_context,
            tools=tools,
        )
        if live_result.get("status") == "completed" or llm_mode == "live":
            return live_result
        offline_result = _invoke_offline_or_local_engine(effective_config, manifest=manifest, task=task)
        return {
            **offline_result,
            "llm_mode": "auto",
            "live_attempt": live_result,
            "fallback_used": True,
        }
    return _invoke_offline_or_local_engine(effective_config, manifest=manifest, task=task)


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
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": engine,
        "status": "completed",
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "prompt_fingerprint": prompt_fingerprint,
        "applied_as": "language_and_tool_reasoning_engine",
        "draft": (
            f"{agent['name']}은 자신의 학습 기록과 절차 원칙을 기준으로 "
            f"'{task}' 업무의 초안을 로컬 응용 엔진에서 구성한다."
        ),
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
    client_result = llm_client.generate(messages, tools=tools or [], policy=policy_context or {})
    client_result = sanitize_llm_result_packet(client_result)
    client_result_summary = _client_result_for_runtime_storage(client_result)
    engine = runtime_config["engine"]
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
        }
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
        "draft": client_result.get("text", ""),
        "client_result": client_result_summary,
        "data_policy": {
            "send_private_training_files": False,
            "send_selected_memory_route_only": True,
            "store_hidden_chain_of_thought": False,
            "store_raw_client_result_text": False,
        },
    }


def _client_result_for_runtime_storage(client_result: dict[str, Any]) -> dict[str, Any]:
    summary = {
        key: client_result[key]
        for key in CLIENT_RESULT_RUNTIME_SUMMARY_KEYS
        if key in client_result
    }
    omitted_keys = sorted(
        key
        for key in client_result
        if key not in CLIENT_RESULT_RUNTIME_SUMMARY_KEYS
    )
    if "text" in client_result:
        summary["text_omitted"] = True
    if omitted_keys:
        summary["omitted_keys"] = omitted_keys
    summary["retention_policy"] = "summary_without_provider_text_or_debug_payload"
    return summary


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
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": "bigram_local",
        "status": "completed",
        "model_path": str(model_path),
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "local_files_only": True,
        "applied_as": "from_scratch_language_draft_engine",
        "draft": draft,
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

    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": "transformers_local",
        "status": "completed",
        "model_path": str(model_path),
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "local_files_only": True,
        "applied_as": "language_and_tool_reasoning_engine",
        "draft": text,
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
        "draft": (
            f"{agent['name']} uses the local manifest, learning ledger, and memory substrate as identity "
            f"and reasoning context. OpenAI ChatGPT Codex supplies language generation only for: {task}"
        ),
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
        "draft": (
            f"{agent['name']} is ready to use {engine} as the selected LLM adapter. "
            f"Paideia keeps identity and learned routes in local records; the adapter supplies language generation for: {task}"
        ),
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
                "error_type",
                "network_access",
                "local_files_only",
            ]
            if key in client_result
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
