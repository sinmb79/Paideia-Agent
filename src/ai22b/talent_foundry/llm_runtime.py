from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ai22b.from_scratch.bigram import generate_text, load_model


RUNTIME_SCHEMA = "ai-talent-llm-runtime/v1"
RUNTIME_RESULT_SCHEMA = "ai-talent-llm-runtime-result/v1"

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
    "openclaw_openai_compatible",
    "openclaw_anthropic_compatible",
    "ollama_cloud_http",
    "openclaw_manifest_only",
}
LOCAL_HTTP_ENGINES = {"ollama_local_http", "lm_studio_local_http"}
LOCAL_FILE_ENGINES = {"bigram_local", "transformers_local", "llama_cpp_local"}


def build_llm_runtime_config(
    *,
    engine: str = "deterministic_local",
    model_path: str | None = None,
    model: str | None = None,
    service: str | None = None,
    provider_config: dict[str, Any] | None = None,
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
        "openclaw_openai_compatible",
        "openclaw_anthropic_compatible",
        "openclaw_manifest_only",
        "ollama_cloud_http",
        "ollama_local_http",
        "lm_studio_local_http",
    ]
    if engine not in compatible_engines:
        raise ValueError(f"Unsupported LLM runtime engine: {engine}")

    manifest_only = engine == "openclaw_manifest_only"
    configured_base_url = model_path or (provider_config or {}).get("base_url")
    openclaw_local_http = engine == "openclaw_openai_compatible" and str(configured_base_url or "").startswith(
        ("http://localhost", "http://127.0.0.1")
    )
    codex_bridge = engine == "openai_chatgpt_codex"
    local_http = engine in LOCAL_HTTP_ENGINES or openclaw_local_http
    external_api = engine in EXTERNAL_API_ENGINES and not local_http and not manifest_only
    if codex_bridge:
        network_access = "codex_host_managed_data_minimized"
    elif manifest_only:
        network_access = "disabled_until_provider_plugin_configured"
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
        "local_only": not external_api or local_http,
        "network_access": network_access,
        "openclaw_provider_id": (provider_config or {}).get("openclaw_provider_id"),
        "openclaw_model": (provider_config or {}).get("openclaw_model"),
        "api_protocol": (provider_config or {}).get("api_protocol"),
        "base_url": configured_base_url,
        "secret_env_vars": (provider_config or {}).get("secret_env_vars", []),
        "provider_status": (provider_config or {}).get("status"),
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


def invoke_llm_application_engine(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
) -> dict[str, Any]:
    if runtime_config.get("schema") != RUNTIME_SCHEMA:
        raise ValueError("Unsupported LLM runtime config schema")

    engine = runtime_config["engine"]
    model_path = runtime_config.get("model_path")
    model = runtime_config.get("model")
    if engine in LOCAL_FILE_ENGINES and not model_path:
        return {
            "schema": RUNTIME_RESULT_SCHEMA,
            "engine": engine,
            "status": "unavailable",
            "reason": "model_path_required_for_local_model_engine",
            "identity_policy": runtime_config["identity_policy"],
            "network_access": runtime_config["network_access"],
        }
    if engine in LOCAL_FILE_ENGINES and model_path and not Path(model_path).exists():
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
        "openclaw_provider_id": runtime_config.get("openclaw_provider_id"),
        "openclaw_model": runtime_config.get("openclaw_model"),
        "api_protocol": runtime_config.get("api_protocol"),
        "base_url_recorded": bool(runtime_config.get("base_url")),
        "draft": (
            f"{agent['name']} is ready to use {engine} as the selected LLM adapter. "
            f"Paideia keeps identity and learned routes in local records; the adapter supplies language generation for: {task}"
        ),
    }


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
