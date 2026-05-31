from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENCLAW_GATEWAY_LLM_DOCTOR_SCHEMA = "ai22b-openclaw-gateway-llm-doctor/v1"
OPENCLAW_GATEWAY_HTTP_PROTOCOL = "openclaw_gateway_openai_chat_completions"
OPENCLAW_GATEWAY_REFERENCE_URLS = [
    "https://docs.openclaw.ai/gateway/openai-http-api",
    "https://docs.openclaw.ai/cli/gateway",
    "https://docs.openclaw.ai/gateway/config-agents",
    "https://docs.openclaw.ai/providers",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_base_url(value: str | None) -> str:
    base_url = str(value or "http://127.0.0.1:18789/v1").strip().rstrip("/")
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _first_env_value(env_vars: list[str]) -> tuple[str | None, str | None]:
    for env_var in env_vars:
        value = os.environ.get(env_var)
        if value:
            return env_var, value
    return None, None


def _auth_headers(env_vars: list[str]) -> tuple[dict[str, str], str | None]:
    env_var, secret = _first_env_value(env_vars)
    if not secret:
        return {}, None
    return {"Authorization": f"Bearer {secret}"}, env_var


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        redacted[key] = "<redacted>" if key.casefold() == "authorization" and value else value
    return redacted


def _http_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8", errors="replace")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {"raw": parsed}


def _extract_model_ids(response: dict[str, Any]) -> list[str]:
    data = response.get("data")
    if isinstance(data, list):
        return [str(item.get("id")) for item in data if isinstance(item, dict) and item.get("id")]
    models = response.get("models")
    if isinstance(models, list):
        return [str(item.get("id") if isinstance(item, dict) else item) for item in models]
    return []


def _load_config_patch_from_bundle(
    runtime_bundle_path: Path | None,
    config_patch_path: Path | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if config_patch_path is not None:
        path = config_patch_path.expanduser().resolve()
        return _read_json(path), str(path)
    if runtime_bundle_path is None:
        return None, None
    bundle_path = runtime_bundle_path.expanduser().resolve()
    bundle = _read_json(bundle_path)
    patch_ref = bundle.get("artifacts", {}).get("openclaw_config_patch")
    if not patch_ref:
        return None, None
    patch_path = Path(str(patch_ref)).expanduser()
    if not patch_path.is_absolute():
        patch_path = bundle_path.parent / patch_path
    patch_path = patch_path.resolve()
    return _read_json(patch_path), str(patch_path)


def doctor_openclaw_gateway_llm(
    employment_record_path: Path,
    *,
    output_path: Path | None = None,
    runtime_bundle_path: Path | None = None,
    config_patch_path: Path | None = None,
    probe_gateway: bool = False,
    probe_chat: bool = False,
    model_override: str | None = None,
    probe_message: str = "Paideia OpenClaw Gateway smoke test.",
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    employment_record_path = employment_record_path.expanduser().resolve()
    employment = _read_json(employment_record_path)
    runtime = employment.get("llm_runtime", {})
    llm_service = employment.get("llm_service", {})
    agent = employment.get("agent", {})
    base_url = _normalize_base_url(runtime.get("base_url") or runtime.get("model_path") or llm_service.get("base_url"))
    local_endpoint = base_url.startswith(("http://localhost", "http://127.0.0.1"))
    secret_env_vars = list(runtime.get("secret_env_vars") or llm_service.get("secret_env_vars") or [])
    auth_header, auth_env_var = _auth_headers(secret_env_vars)
    agent_target = str(runtime.get("openclaw_agent_target") or llm_service.get("openclaw_agent_target") or "openclaw/default")
    backend_model = (
        model_override
        or runtime.get("openclaw_model")
        or llm_service.get("openclaw_model")
        or runtime.get("model")
    )

    config_patch: dict[str, Any] | None = None
    config_patch_ref: str | None = None
    config_patch_error: str | None = None
    try:
        config_patch, config_patch_ref = _load_config_patch_from_bundle(runtime_bundle_path, config_patch_path)
    except Exception as exc:
        config_patch_error = f"{type(exc).__name__}: {str(exc)[:500]}"
    patch_enabled = (
        _get_path(config_patch or {}, "openclaw_json_patch.gateway.http.endpoints.chatCompletions.enabled")
        is True
    )

    checks = [
        {
            "id": "employment_record_active",
            "passed": employment.get("schema") == "ai-talent-local-employment/v1" and employment.get("status") == "active",
            "path": str(employment_record_path),
        },
        {
            "id": "llm_runtime_is_openclaw_gateway_http",
            "passed": runtime.get("engine") == "openclaw_gateway_http",
            "engine": runtime.get("engine"),
        },
        {
            "id": "api_protocol_matches_openclaw_gateway",
            "passed": runtime.get("api_protocol") == OPENCLAW_GATEWAY_HTTP_PROTOCOL,
            "api_protocol": runtime.get("api_protocol"),
        },
        {
            "id": "base_url_targets_v1",
            "passed": base_url.endswith("/v1"),
            "base_url": base_url,
            "loopback": local_endpoint,
        },
        {
            "id": "agent_target_configured",
            "passed": agent_target in {"openclaw", "openclaw/default"} or agent_target.startswith("openclaw/"),
            "agent_target": agent_target,
        },
        {
            "id": "backend_model_header_available",
            "passed": bool(backend_model),
            "x_openclaw_model": backend_model,
            "severity": "warning" if not backend_model else "info",
            "message": "If omitted, OpenClaw uses the selected agent's configured default backend model.",
        },
        {
            "id": "auth_env_or_private_ingress",
            "passed": bool(auth_env_var) or local_endpoint,
            "auth_env_var": auth_env_var,
            "loopback_without_auth_allowed_only_if_gateway_auth_none": local_endpoint and not auth_env_var,
        },
    ]
    if runtime_bundle_path is not None or config_patch_path is not None:
        checks.append(
            {
                "id": "config_patch_enables_chat_completions",
                "passed": patch_enabled,
                "config_patch": config_patch_ref,
                "error": config_patch_error,
            }
        )

    probes: list[dict[str, Any]] = []
    headers = {
        **auth_header,
    }
    if backend_model:
        headers["x-openclaw-model"] = str(backend_model)
    headers["x-openclaw-session-key"] = f"paideia-doctor:{employment.get('employment_id', 'unknown')}"
    headers["x-openclaw-message-channel"] = "paideia-gateway-doctor"

    if probe_gateway:
        try:
            response = _http_json(
                method="GET",
                url=f"{base_url}/models",
                headers=auth_header,
                timeout_seconds=timeout_seconds,
            )
            model_ids = _extract_model_ids(response)
            probes.append(
                {
                    "id": "get_v1_models",
                    "passed": "openclaw/default" in model_ids or "openclaw" in model_ids,
                    "url": f"{base_url}/models",
                    "model_ids": model_ids[:20],
                    "headers": _redact_headers(auth_header),
                }
            )
        except Exception as exc:
            probes.append(
                {
                    "id": "get_v1_models",
                    "passed": False,
                    "url": f"{base_url}/models",
                    "headers": _redact_headers(auth_header),
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:800],
                }
            )

    if probe_chat:
        payload = {
            "model": agent_target,
            "user": f"paideia-doctor:{employment.get('employment_id', 'unknown')}",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are verifying that Paideia can reach OpenClaw Gateway. "
                        "Return a short plain text acknowledgement."
                    ),
                },
                {
                    "role": "user",
                    "content": probe_message,
                },
            ],
            "temperature": 0.0,
            "max_tokens": 96,
        }
        try:
            response = _http_json(
                method="POST",
                url=f"{base_url}/chat/completions",
                headers=headers,
                payload=payload,
                timeout_seconds=timeout_seconds,
            )
            choices = response.get("choices") or []
            probes.append(
                {
                    "id": "post_v1_chat_completions",
                    "passed": bool(choices),
                    "url": f"{base_url}/chat/completions",
                    "request": {
                        "model": agent_target,
                        "x_openclaw_model": backend_model,
                        "headers": _redact_headers(headers),
                    },
                    "usage": response.get("usage"),
                    "choice_count": len(choices) if isinstance(choices, list) else 0,
                }
            )
        except Exception as exc:
            probes.append(
                {
                    "id": "post_v1_chat_completions",
                    "passed": False,
                    "url": f"{base_url}/chat/completions",
                    "request": {
                        "model": agent_target,
                        "x_openclaw_model": backend_model,
                        "headers": _redact_headers(headers),
                    },
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:800],
                }
            )

    blocking_failed_checks = [
        check
        for check in checks
        if not check.get("passed") and check.get("id") != "backend_model_header_available"
    ]
    failed_probes = [probe for probe in probes if not probe.get("passed")]
    if failed_probes:
        status = "needs_attention"
    elif probes:
        status = "pass" if not blocking_failed_checks else "needs_attention"
    else:
        status = "ready_for_gateway_start" if not blocking_failed_checks else "needs_attention"

    report = {
        "schema": OPENCLAW_GATEWAY_LLM_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "employment_record": str(employment_record_path),
        "agent": {
            "name": agent.get("name"),
            "role": agent.get("role"),
        },
        "gateway_contract": {
            "base_url": base_url,
            "models_endpoint": f"{base_url}/models",
            "chat_completions_endpoint": f"{base_url}/chat/completions",
            "openai_model_field_is_agent_target": True,
            "agent_target": agent_target,
            "backend_model_header": backend_model,
            "session_header": "x-openclaw-session-key",
            "message_channel_header": "x-openclaw-message-channel",
        },
        "checks": checks,
        "probes": probes,
        "security": {
            "secret_values_stored": False,
            "private_training_files_exported": False,
            "gateway_token_is_operator_credential": True,
            "recommended_network_boundary": "loopback_tailnet_or_private_ingress_only",
        },
        "next_commands": {
            "start_openclaw_gateway": "openclaw gateway run",
            "probe_models": (
                f"ai22b-talent-foundry doctor-openclaw-gateway-llm --employment-record {employment_record_path} "
                "--probe-gateway --output openclaw_gateway_llm_doctor.json"
            ),
            "probe_chat": (
                f"ai22b-talent-foundry doctor-openclaw-gateway-llm --employment-record {employment_record_path} "
                "--probe-gateway --probe-chat --output openclaw_gateway_llm_doctor.json"
            ),
        },
        "source_docs_checked": OPENCLAW_GATEWAY_REFERENCE_URLS,
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
