from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
import urllib.request

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
    "openclaw_gateway_http",
    "ollama_cloud_http",
    "openclaw_manifest_only",
}
LOCAL_HTTP_ENGINES = {"ollama_local_http", "lm_studio_local_http"}
LOCAL_FILE_ENGINES = {"bigram_local", "transformers_local", "llama_cpp_local"}
OPENCLAW_CLI_ENGINES = {"openclaw_cli_local"}
DEFAULT_OPENAI_APPLICATION_MODEL = "gpt-5.2"


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
        "openclaw_gateway_http",
        "openclaw_cli_local",
        "openclaw_manifest_only",
        "ollama_cloud_http",
        "ollama_local_http",
        "lm_studio_local_http",
    ]
    if engine not in compatible_engines:
        raise ValueError(f"Unsupported LLM runtime engine: {engine}")

    manifest_only = engine == "openclaw_manifest_only"
    openclaw_cli = engine in OPENCLAW_CLI_ENGINES
    configured_base_url = model_path or (provider_config or {}).get("base_url")
    openclaw_local_http = engine == "openclaw_openai_compatible" and str(configured_base_url or "").startswith(
        ("http://localhost", "http://127.0.0.1")
    )
    openclaw_gateway_local_http = engine == "openclaw_gateway_http" and str(configured_base_url or "").startswith(
        ("http://localhost", "http://127.0.0.1")
    )
    codex_bridge = engine == "openai_chatgpt_codex"
    local_http = engine in LOCAL_HTTP_ENGINES or openclaw_local_http or openclaw_gateway_local_http
    external_api = engine in EXTERNAL_API_ENGINES and not local_http and not manifest_only
    if codex_bridge:
        network_access = "codex_host_managed_data_minimized"
    elif manifest_only:
        network_access = "disabled_until_provider_plugin_configured"
    elif openclaw_cli:
        network_access = "openclaw_cli_managed_provider_network_when_live"
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
        "local_only": (not external_api and not openclaw_cli) or local_http,
        "network_access": network_access,
        "openclaw_provider_id": (provider_config or {}).get("openclaw_provider_id"),
        "openclaw_model": (provider_config or {}).get("openclaw_model"),
        "openclaw_agent_target": (provider_config or {}).get("openclaw_agent_target"),
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
    live_mode: bool = False,
    model_override: str | None = None,
    max_output_tokens: int = 900,
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
    if live_mode:
        return _invoke_live_application_engine(
            runtime_config,
            manifest=manifest,
            task=task,
            model_override=model_override,
            max_output_tokens=max_output_tokens,
        )
    if engine == "openai_chatgpt_codex":
        return _invoke_openai_chatgpt_codex_bridge(runtime_config, manifest=manifest, task=task)
    if engine in (EXTERNAL_API_ENGINES - {"openai_chatgpt_codex"}) or engine in LOCAL_HTTP_ENGINES or engine in OPENCLAW_CLI_ENGINES:
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
        "openclaw_agent_target": runtime_config.get("openclaw_agent_target"),
        "draft": (
            f"{agent['name']} is ready to use {engine} as the selected LLM adapter. "
            f"Paideia keeps identity and learned routes in local records; the adapter supplies language generation for: {task}"
        ),
    }


def _first_env_value(env_vars: list[str]) -> tuple[str | None, str | None]:
    for env_var in env_vars:
        value = os.environ.get(env_var)
        if not value:
            continue
        if env_var.endswith("_API_KEYS") and ("," in value or ";" in value):
            for candidate in value.replace(";", ",").split(","):
                if candidate.strip():
                    return env_var, candidate.strip()
        return env_var, value
    return None, None


def _request_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 60,
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {"raw": parsed}


def _selected_runtime_model(runtime_config: dict[str, Any], model_override: str | None) -> str:
    if runtime_config.get("api_protocol") == "openclaw_cli_agent_local":
        selected = (
            model_override
            or runtime_config.get("openclaw_model")
            or runtime_config.get("model")
            or os.environ.get("AI22B_OPENAI_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or DEFAULT_OPENAI_APPLICATION_MODEL
        )
    else:
        selected = (
            model_override
            or runtime_config.get("model")
            or runtime_config.get("openclaw_model")
            or os.environ.get("AI22B_OPENAI_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or DEFAULT_OPENAI_APPLICATION_MODEL
        )
    provider_id = runtime_config.get("openclaw_provider_id")
    if (
        provider_id
        and runtime_config.get("api_protocol")
        not in {"openclaw_gateway_openai_chat_completions", "openclaw_cli_agent_local"}
        and str(selected).startswith(f"{provider_id}/")
    ):
        return str(selected).split("/", 1)[1]
    return str(selected)


def _live_application_prompt(*, manifest: dict[str, Any], task: str) -> str:
    agent = manifest.get("agent", {})
    memory = manifest.get("memory_profile", {})
    return (
        "You are the language engine for a locally trained Paideia Agent talent. "
        "The LLM provides language and task drafting only; identity, learned data, and reasoning habits come from "
        "the local manifest and employment records. Answer in Korean unless the task clearly asks otherwise. "
        "Do not output hidden chain-of-thought. Provide a concise answer plus a reviewable reasoning summary.\n\n"
        f"Agent name: {agent.get('name')}\n"
        f"Role: {agent.get('role')}\n"
        f"Major goal: {agent.get('major_goal')}\n"
        f"Procedural principles: {memory.get('procedural_principles', [])}\n"
        f"Task: {task}\n"
    )


def _redact_runtime_text(text: str) -> str:
    if not text:
        return text
    home = str(Path.home())
    profile = os.environ.get("USERPROFILE", "")
    for path in {home, profile}:
        if path:
            text = text.replace(path, "~")
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email-redacted>", text)
    text = re.sub(r"\bsk-proj-[A-Za-z0-9_-]{8,}\b", "sk-proj-<redacted>", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "sk-<redacted>", text)
    return text


def _extract_openclaw_cli_text(parsed: Any, stdout: str) -> str:
    if isinstance(parsed, dict):
        for key in (
            "assistant_reply",
            "reply",
            "text",
            "content",
            "message",
            "output",
            "result",
        ):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, dict):
                nested = _extract_openclaw_cli_text(value, "")
                if nested:
                    return nested
        choices = parsed.get("choices")
        if isinstance(choices, list) and choices:
            return _extract_openclaw_cli_text(choices[0], "")
    return stdout.strip()


def _invoke_openclaw_cli_local_application_engine(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
    model: str,
) -> dict[str, Any]:
    openclaw_binary = shutil.which("openclaw")
    if not openclaw_binary:
        return _unavailable_live_result(runtime_config, reason="openclaw_cli_not_found", model=model)
    if not model:
        return _unavailable_live_result(runtime_config, reason="openclaw_provider_model_required", model=model)
    payload = {
        "task": "Generate one Paideia Agent work response using the installed OpenClaw local agent runtime.",
        "system": _live_application_prompt(manifest=manifest, task=task),
        "user_task": task,
        "response_policy": {
            "answer_language": "ko-KR",
            "hidden_chain_of_thought": "forbidden",
            "reviewable_reasoning_summary": "required",
        },
    }
    command = [
        openclaw_binary,
        "agent",
        "--local",
        "--json",
        "--model",
        model,
        "--message",
        json.dumps(payload, ensure_ascii=False),
        "--session-id",
        f"paideia-work-{_prompt_fingerprint(manifest=manifest, task=task)}",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
    except Exception as exc:
        return _unavailable_live_result(
            runtime_config,
            reason="openclaw_cli_agent_exception",
            model=model,
            error=exc,
        )
    if completed.returncode != 0:
        error = RuntimeError(_redact_runtime_text(completed.stderr or completed.stdout)[:800])
        return _unavailable_live_result(
            runtime_config,
            reason="openclaw_cli_agent_call_failed",
            model=model,
            error=error,
        )
    parsed: Any = None
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = None
    return _completed_live_result(
        runtime_config,
        model=model,
        draft=_extract_openclaw_cli_text(parsed, completed.stdout),
        provider="openclaw_cli_local",
        endpoint="openclaw agent --local",
        auth_env=None,
        usage=parsed.get("usage") if isinstance(parsed, dict) else None,
    )


def _openai_chat_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message", {}) if isinstance(first.get("message"), dict) else {}
    return str(message.get("content") or first.get("text") or "")


def _openai_responses_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response["output_text"])
    chunks: list[str] = []
    for item in response.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, dict) and content.get("text"):
                chunks.append(str(content["text"]))
    return "\n".join(chunks)


def _completed_live_result(
    runtime_config: dict[str, Any],
    *,
    model: str,
    draft: str,
    provider: str | None,
    endpoint: str,
    auth_env: str | None,
    usage: Any = None,
) -> dict[str, Any]:
    return {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": runtime_config.get("engine"),
        "status": "completed",
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "applied_as": "live_language_and_task_reasoning_engine",
        "model": model,
        "openclaw_provider_id": runtime_config.get("openclaw_provider_id"),
        "openclaw_model": runtime_config.get("openclaw_model"),
        "api_protocol": runtime_config.get("api_protocol"),
        "endpoint": endpoint,
        "auth_env_var": auth_env,
        "usage": usage,
        "draft": draft,
        "data_policy": {
            "send_private_training_files": False,
            "send_selected_manifest_summary_and_task": True,
            "store_hidden_chain_of_thought": False,
            "secret_values_stored": False,
        },
    }


def _unavailable_live_result(
    runtime_config: dict[str, Any],
    *,
    reason: str,
    model: str | None = None,
    error: Exception | None = None,
) -> dict[str, Any]:
    result = {
        "schema": RUNTIME_RESULT_SCHEMA,
        "engine": runtime_config.get("engine"),
        "status": "unavailable",
        "reason": reason,
        "identity_policy": runtime_config["identity_policy"],
        "network_access": runtime_config["network_access"],
        "model": model,
        "api_protocol": runtime_config.get("api_protocol"),
        "required_env_vars": runtime_config.get("secret_env_vars", []),
        "data_policy": {
            "secret_values_stored": False,
            "private_training_files_exported": False,
        },
    }
    if error is not None:
        result["error_type"] = type(error).__name__
        result["error"] = str(error)[:800]
    return result


def _invoke_live_application_engine(
    runtime_config: dict[str, Any],
    *,
    manifest: dict[str, Any],
    task: str,
    model_override: str | None,
    max_output_tokens: int,
) -> dict[str, Any]:
    engine = runtime_config.get("engine")
    api_protocol = runtime_config.get("api_protocol")
    model = _selected_runtime_model(runtime_config, model_override)
    prompt = _live_application_prompt(manifest=manifest, task=task)

    if engine == "openclaw_manifest_only" or api_protocol == "manifest_only":
        return _unavailable_live_result(
            runtime_config,
            reason="openclaw_provider_plugin_required",
            model=model,
        )

    if api_protocol == "openclaw_cli_agent_local" or engine == "openclaw_cli_local":
        return _invoke_openclaw_cli_local_application_engine(
            runtime_config,
            manifest=manifest,
            task=task,
            model=model,
        )

    if engine == "openai_chatgpt_codex" or api_protocol == "openai_responses":
        env_var, api_key = _first_env_value(runtime_config.get("secret_env_vars", ["OPENAI_API_KEY"]))
        if not api_key:
            return _unavailable_live_result(runtime_config, reason="provider_api_key_not_set", model=model)
        base_url = str(runtime_config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": model,
            "instructions": prompt,
            "input": task,
            "max_output_tokens": max_output_tokens,
        }
        try:
            response = _request_json(
                url=f"{base_url}/responses",
                payload=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
        except Exception as exc:
            return _unavailable_live_result(
                runtime_config,
                reason="openai_responses_call_failed",
                model=model,
                error=exc,
            )
        return _completed_live_result(
            runtime_config,
            model=model,
            draft=_openai_responses_text(response),
            provider="openai",
            endpoint=f"{base_url}/responses",
            auth_env=env_var,
            usage=response.get("usage"),
        )

    if api_protocol == "openclaw_gateway_openai_chat_completions":
        base_url = str(runtime_config.get("base_url") or runtime_config.get("model_path") or "http://127.0.0.1:18789/v1").rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        local_endpoint = base_url.startswith(("http://localhost", "http://127.0.0.1"))
        env_var, gateway_secret = _first_env_value(runtime_config.get("secret_env_vars", []))
        if not gateway_secret and not local_endpoint:
            return _unavailable_live_result(runtime_config, reason="openclaw_gateway_auth_not_configured", model=model)
        headers = {
            "x-openclaw-session-key": _prompt_fingerprint(manifest=manifest, task=task),
            "x-openclaw-message-channel": "paideia-agent-runtime",
        }
        if gateway_secret:
            headers["Authorization"] = f"Bearer {gateway_secret}"
        backend_model = model_override or runtime_config.get("openclaw_model") or runtime_config.get("model")
        if backend_model:
            headers["x-openclaw-model"] = str(backend_model)
        agent_target = str(runtime_config.get("openclaw_agent_target") or "openclaw/default")
        payload = {
            "model": agent_target,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": task},
            ],
            "temperature": 0.2,
            "max_tokens": max_output_tokens,
        }
        try:
            response = _request_json(
                url=f"{base_url}/chat/completions",
                payload=payload,
                headers=headers,
            )
        except Exception as exc:
            return _unavailable_live_result(
                runtime_config,
                reason="openclaw_gateway_chat_call_failed",
                model=str(backend_model or agent_target),
                error=exc,
            )
        return _completed_live_result(
            runtime_config,
            model=str(backend_model or agent_target),
            draft=_openai_chat_text(response),
            provider="openclaw_gateway",
            endpoint=f"{base_url}/chat/completions",
            auth_env=env_var,
            usage=response.get("usage"),
        )

    if api_protocol == "openai_chat_completions":
        base_url = str(runtime_config.get("base_url") or runtime_config.get("model_path") or "").rstrip("/")
        local_endpoint = base_url.startswith(("http://localhost", "http://127.0.0.1"))
        env_var, api_key = _first_env_value(runtime_config.get("secret_env_vars", []))
        if not base_url:
            return _unavailable_live_result(runtime_config, reason="base_url_not_configured", model=model)
        if runtime_config.get("secret_env_vars") and not api_key and not local_endpoint:
            return _unavailable_live_result(runtime_config, reason="provider_api_key_not_set", model=model)
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": task},
            ],
            "temperature": 0.2,
            "max_tokens": max_output_tokens,
        }
        try:
            response = _request_json(
                url=f"{base_url}/chat/completions",
                payload=payload,
                headers=headers,
            )
        except Exception as exc:
            return _unavailable_live_result(
                runtime_config,
                reason="openai_compatible_chat_call_failed",
                model=model,
                error=exc,
            )
        return _completed_live_result(
            runtime_config,
            model=model,
            draft=_openai_chat_text(response),
            provider=str(runtime_config.get("openclaw_provider_id") or runtime_config.get("service") or "openai_compatible"),
            endpoint=f"{base_url}/chat/completions",
            auth_env=env_var,
            usage=response.get("usage"),
        )

    if api_protocol == "anthropic_messages":
        env_var, api_key = _first_env_value(runtime_config.get("secret_env_vars", ["ANTHROPIC_API_KEY"]))
        if not api_key:
            return _unavailable_live_result(runtime_config, reason="provider_api_key_not_set", model=model)
        base_url = str(runtime_config.get("base_url") or "https://api.anthropic.com/v1").rstrip("/")
        payload = {
            "model": model,
            "max_tokens": max_output_tokens,
            "system": prompt,
            "messages": [{"role": "user", "content": task}],
        }
        try:
            response = _request_json(
                url=f"{base_url}/messages",
                payload=payload,
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            )
        except Exception as exc:
            return _unavailable_live_result(
                runtime_config,
                reason="anthropic_messages_call_failed",
                model=model,
                error=exc,
            )
        text = "\n".join(str(part.get("text", "")) for part in response.get("content", []) if isinstance(part, dict))
        return _completed_live_result(
            runtime_config,
            model=model,
            draft=text,
            provider=str(runtime_config.get("openclaw_provider_id") or "anthropic"),
            endpoint=f"{base_url}/messages",
            auth_env=env_var,
            usage=response.get("usage"),
        )

    if api_protocol == "gemini_generate_content":
        env_var, api_key = _first_env_value(runtime_config.get("secret_env_vars", ["GEMINI_API_KEY", "GOOGLE_API_KEY"]))
        if not api_key:
            return _unavailable_live_result(runtime_config, reason="provider_api_key_not_set", model=model)
        base_url = str(runtime_config.get("base_url") or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        payload = {
            "contents": [{"role": "user", "parts": [{"text": f"{prompt}\n\n{task}"}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_output_tokens},
        }
        try:
            response = _request_json(
                url=f"{base_url}/models/{model}:generateContent?key={api_key}",
                payload=payload,
                headers={},
            )
        except Exception as exc:
            return _unavailable_live_result(
                runtime_config,
                reason="gemini_generate_content_call_failed",
                model=model,
                error=exc,
            )
        candidates = response.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
        return _completed_live_result(
            runtime_config,
            model=model,
            draft=text,
            provider="google",
            endpoint=f"{base_url}/models/{model}:generateContent",
            auth_env=env_var,
            usage=response.get("usageMetadata"),
        )

    if api_protocol == "ollama_chat":
        base_url = str(runtime_config.get("base_url") or runtime_config.get("model_path") or "http://localhost:11434").rstrip("/")
        local_endpoint = base_url.startswith(("http://localhost", "http://127.0.0.1"))
        env_var, api_key = _first_env_value(runtime_config.get("secret_env_vars", []))
        if runtime_config.get("secret_env_vars") and not api_key and not local_endpoint:
            return _unavailable_live_result(runtime_config, reason="provider_api_key_not_set", model=model)
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": task},
            ],
            "options": {"temperature": 0.2, "num_predict": max_output_tokens},
        }
        try:
            response = _request_json(
                url=f"{base_url}/api/chat",
                payload=payload,
                headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            )
        except Exception as exc:
            return _unavailable_live_result(runtime_config, reason="ollama_chat_call_failed", model=model, error=exc)
        text = str(response.get("message", {}).get("content") or response.get("response") or "")
        return _completed_live_result(
            runtime_config,
            model=model,
            draft=text,
            provider=str(runtime_config.get("openclaw_provider_id") or "ollama"),
            endpoint=f"{base_url}/api/chat",
            auth_env=env_var,
            usage=response.get("usage"),
        )

    return _unavailable_live_result(
        runtime_config,
        reason="live_provider_protocol_not_supported",
        model=model,
    )


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
