from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENCLAW_INSTALLED_RUNTIME_DOCTOR_SCHEMA = "ai22b-openclaw-installed-runtime-doctor/v1"

SECRET_KEY_PATTERNS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "bot_token",
    "client_secret",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "session_token",
    "token",
    "webhook",
)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _secret_like_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.casefold())
    return any(pattern in normalized for pattern in SECRET_KEY_PATTERNS)


def _redact_text(text: str) -> str:
    if not text:
        return text
    home = str(Path.home())
    profile = os.environ.get("USERPROFILE", "")
    for path in {home, profile}:
        if path:
            text = text.replace(path, "~")
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email-redacted>", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "sk-<redacted>", text)
    text = re.sub(r"\bsk-proj-[A-Za-z0-9_-]{8,}\b", "sk-proj-<redacted>", text)
    text = re.sub(r"\b[A-Za-z0-9_-]{32,}\b", "<secret-like-redacted>", text)
    return text


def _redact(value: Any, *, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _secret_like_key(str(key)):
                redacted[str(key)] = "<redacted>"
            else:
                redacted[str(key)] = _redact(item, parent_key=str(key))
        return redacted
    if isinstance(value, list):
        return [_redact(item, parent_key=parent_key) for item in value]
    if isinstance(value, str):
        if parent_key and _secret_like_key(parent_key):
            return "<redacted>"
        return _redact_text(value)
    return value


def _parse_json(stdout: str) -> tuple[dict[str, Any] | None, str | None]:
    if not stdout.strip():
        return None, "empty_stdout"
    try:
        parsed = json.loads(stdout)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {str(exc)[:300]}"
    if not isinstance(parsed, dict):
        return None, "json_output_was_not_an_object"
    return parsed, None


def _run_openclaw(
    openclaw_binary: str,
    args: list[str],
    *,
    timeout_seconds: int,
    expect_json: bool = False,
) -> dict[str, Any]:
    command = [openclaw_binary, *args]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return {
            "command": ["openclaw", *args],
            "ran": False,
            "passed": False,
            "error_type": type(exc).__name__,
            "error": _redact_text(str(exc)[:500]),
            "secret_values_stored": False,
        }

    parsed_json = None
    json_error = None
    if expect_json:
        parsed_json, json_error = _parse_json(completed.stdout)
    return {
        "command": ["openclaw", *args],
        "ran": True,
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout_preview": _redact_text(completed.stdout[:1200]),
        "stderr_preview": _redact_text(completed.stderr[:1200]),
        "json": _redact(parsed_json) if parsed_json is not None else None,
        "json_error": json_error,
        "secret_values_stored": False,
    }


def _probe_map(commands: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in commands}


def _json_for(probes: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    data = probes.get(key, {}).get("json")
    return data if isinstance(data, dict) else {}


def _summary(probes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    config_validate = _json_for(probes, "config_validate")
    models_status = _json_for(probes, "models_status")
    channels_status = _json_for(probes, "channels_status")
    gateway_status = _json_for(probes, "gateway_status")
    auth = models_status.get("auth", {}) if isinstance(models_status.get("auth"), dict) else {}
    gateway = gateway_status.get("gateway", {}) if isinstance(gateway_status.get("gateway"), dict) else {}
    service = gateway_status.get("service", {}) if isinstance(gateway_status.get("service"), dict) else {}
    runtime = service.get("runtime", {}) if isinstance(service.get("runtime"), dict) else {}
    return {
        "config_valid": bool(config_validate.get("valid")),
        "default_model": models_status.get("defaultModel"),
        "resolved_default_model": models_status.get("resolvedDefault"),
        "allowed_model_count": len(models_status.get("allowed", []) or []),
        "missing_providers_in_use": auth.get("missingProvidersInUse", []),
        "runtime_auth_routes": [
            {
                "provider": item.get("provider"),
                "runtime": item.get("runtime"),
                "auth_provider": item.get("authProvider"),
                "status": item.get("status"),
            }
            for item in auth.get("runtimeAuthRoutes", []) or []
            if isinstance(item, dict)
        ],
        "configured_channels": channels_status.get("configuredChannels", []),
        "gateway_reachable": channels_status.get("gatewayReachable"),
        "gateway_bind_host": gateway.get("bindHost"),
        "gateway_port": gateway.get("port"),
        "gateway_service_runtime_status": runtime.get("status"),
    }


def _status(cli_detected: bool, summary: dict[str, Any], probes: dict[str, dict[str, Any]]) -> str:
    if not cli_detected:
        return "openclaw_cli_not_found"
    if not summary.get("config_valid"):
        return "needs_openclaw_config_repair"
    if summary.get("missing_providers_in_use"):
        return "needs_model_provider_auth"
    if summary.get("gateway_service_runtime_status") in {"running", "started"} or summary.get("gateway_reachable") is True:
        return "ready_with_openclaw_gateway"
    if probes.get("gateway_status", {}).get("ran"):
        return "ready_for_gateway_start"
    return "ready_for_openclaw_probe"


def doctor_openclaw_installed_runtime(
    *,
    output_path: Path | None = None,
    timeout_seconds: int = 20,
    probe_gateway: bool = False,
) -> dict[str, Any]:
    openclaw_binary = shutil.which("openclaw")
    commands: list[dict[str, Any]] = []
    if openclaw_binary:
        command_specs = [
            ("version", ["--version"], False),
            ("config_file", ["config", "file"], False),
            ("config_validate", ["config", "validate", "--json"], True),
            ("models_status", ["models", "status", "--json"], True),
            ("channels_status", ["channels", "status", "--json"], True),
            (
                "gateway_status",
                ["gateway", "status", "--json"] if probe_gateway else ["gateway", "status", "--json", "--no-probe"],
                True,
            ),
        ]
        for command_id, args, expect_json in command_specs:
            result = _run_openclaw(
                openclaw_binary,
                args,
                timeout_seconds=timeout_seconds,
                expect_json=expect_json,
            )
            result["id"] = command_id
            commands.append(result)
    probes = _probe_map(commands)
    summary = _summary(probes)
    doctor = {
        "schema": OPENCLAW_INSTALLED_RUNTIME_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": _status(bool(openclaw_binary), summary, probes),
        "openclaw_cli": {
            "detected_on_path": bool(openclaw_binary),
            "binary": _redact_text(openclaw_binary or "openclaw"),
            "version": _redact_text(probes.get("version", {}).get("stdout_preview", "")).strip() or None,
        },
        "summary": summary,
        "commands": commands,
        "next_commands": {
            "run_guided_onboarding": "openclaw onboard",
            "repair_or_review": "openclaw doctor",
            "start_gateway_foreground": "openclaw gateway run --force",
            "probe_gateway_after_start": (
                "ai22b-talent-foundry doctor-openclaw-installed-runtime "
                "--probe-gateway --output openclaw_installed_runtime_doctor.live.json"
            ),
            "probe_model_auth_live": "openclaw models status --json --probe",
            "probe_channels_live": "openclaw channels status --json --probe",
        },
        "policy": {
            "read_only": True,
            "external_network_call_performed": bool(probe_gateway),
            "provider_probe_performed": False,
            "channel_probe_performed": False,
            "secret_values_stored": False,
            "redaction": "home paths, emails, secret-like strings, and secret-keyed values are redacted",
        },
        "source_docs_checked": [
            "https://docs.openclaw.ai/cli",
            "https://docs.openclaw.ai/cli/gateway",
            "https://docs.openclaw.ai/cli/models",
            "https://docs.openclaw.ai/cli/channels",
            "https://docs.openclaw.ai/cli/agents",
        ],
    }
    if output_path is not None:
        _write_json(output_path, doctor)
    return doctor
