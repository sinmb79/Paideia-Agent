from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.provider_connectors import build_openclaw_provider_connector_catalog
from ai22b.talent_foundry.openclaw_compat import resolve_openclaw_provider


OPENCLAW_PROVIDER_AUTH_DOCTOR_SCHEMA = "ai22b-openclaw-provider-auth-doctor/v1"

SECRET_KEY_PATTERNS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "cookie",
    "credential",
    "key",
    "password",
    "private",
    "secret",
    "session",
    "token",
)

OAUTH_OR_ACCOUNT_PROVIDERS = {
    "claude-max-api-proxy",
    "github-copilot",
    "google-gemini-cli",
    "opencode",
    "opencode-go",
    "qwen-oauth",
}

CLOUD_PROFILE_PROVIDERS = {
    "amazon-bedrock",
    "amazon-bedrock-mantle",
    "anthropic-vertex",
    "google-vertex",
    "tencent-tokenhub",
}

MEDIA_OR_TOOL_PROVIDERS = {
    "azure-speech",
    "comfyui",
    "deepgram",
    "elevenlabs",
    "fal",
    "gradium",
    "inworld",
    "pixverse",
    "runway",
    "senseaudio",
    "vydra",
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_openclaw_config_path() -> Path:
    return Path.home() / ".openclaw" / "openclaw.json"


def _env_alternatives(env_var: str) -> list[str]:
    return [part.strip() for part in str(env_var).split(" or ") if part.strip()]


def _env_check(env_var: str) -> dict[str, Any]:
    alternatives = _env_alternatives(env_var)
    present = any(os.environ.get(item) for item in alternatives)
    return {
        "id": f"env:{env_var}",
        "kind": "environment_secret",
        "passed": present,
        "secret_value_stored": False,
        "message": "configured" if present else f"{env_var} is not set in this shell.",
    }


def _secret_like_key(key: str) -> bool:
    normalized = "".join(char if char.isalnum() else "_" for char in key.casefold())
    return any(pattern in normalized for pattern in SECRET_KEY_PATTERNS)


def _redact_config(value: Any, *, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if _secret_like_key(str(key)) else _redact_config(item, parent_key=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_config(item, parent_key=parent_key) for item in value]
    if parent_key and _secret_like_key(parent_key):
        return "<redacted>"
    return value


def _load_redacted_openclaw_config(path: Path | None) -> dict[str, Any]:
    config_path = (path or _default_openclaw_config_path()).expanduser()
    report: dict[str, Any] = {
        "path": str(config_path),
        "exists": config_path.exists(),
        "readable_json": False,
        "secret_values_stored": False,
        "provider_hints": [],
    }
    if not config_path.exists():
        return report
    try:
        parsed = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:300]
        return report
    redacted = _redact_config(parsed)
    report["readable_json"] = True
    report["top_level_keys"] = sorted(str(key) for key in parsed.keys()) if isinstance(parsed, dict) else []
    report["provider_hints"] = sorted(_provider_hints_from_config(redacted))
    return report


def _provider_hints_from_config(config: Any) -> set[str]:
    hints: set[str] = set()

    def visit(value: Any, key_hint: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                if key_text in {"provider", "providerId", "provider_id"} and isinstance(item, str):
                    hints.add(item)
                if key_text == "providers" and isinstance(item, dict):
                    hints.update(str(provider_id) for provider_id in item.keys())
                if key_text in {"primary", "model", "default"} and isinstance(item, str) and "/" in item:
                    hints.add(item.split("/", 1)[0])
                visit(item, key_text)
        elif isinstance(value, list):
            for item in value:
                visit(item, key_hint)
        elif key_hint in {"primary", "model", "default"} and isinstance(value, str) and "/" in value:
            hints.add(value.split("/", 1)[0])

    visit(config)
    return {hint for hint in hints if hint and hint != "<redacted>"}


def _auth_kind(provider: dict[str, Any]) -> str:
    provider_id = str(provider["provider_id"])
    if provider.get("external_openclaw_provider"):
        return "openclaw_gateway_owned_provider_or_plugin"
    if provider_id == "openai":
        return "api_key_or_codex_host_bridge"
    if provider.get("manifest_only"):
        if provider_id in OAUTH_OR_ACCOUNT_PROVIDERS or "oauth" in provider_id:
            return "openclaw_oauth_or_account_session"
        if provider_id in CLOUD_PROFILE_PROVIDERS:
            return "cloud_provider_profile"
        if provider_id in MEDIA_OR_TOOL_PROVIDERS:
            return "capability_plugin_or_media_provider"
        return "openclaw_provider_plugin_or_custom_runner"
    if provider.get("local_endpoint"):
        return "local_server_endpoint"
    if provider.get("secret_env_vars"):
        return "api_key_environment"
    return "no_secret_required"


def _auth_status(
    *,
    provider: dict[str, Any],
    auth_kind: str,
    checks: list[dict[str, Any]],
    config_report: dict[str, Any],
) -> str:
    provider_id = str(provider["provider_id"])
    provider_hints = set(str(item) for item in config_report.get("provider_hints", []))
    has_provider_hint = provider_id in provider_hints
    if provider.get("external_openclaw_provider"):
        return "ready_for_openclaw_gateway_review" if has_provider_hint else "needs_openclaw_provider_auth"
    if provider.get("manifest_only"):
        return "ready_for_openclaw_gateway_review" if has_provider_hint else "needs_openclaw_provider_auth"
    if auth_kind == "local_server_endpoint":
        return "ready_for_local_server_probe"
    if auth_kind == "api_key_or_codex_host_bridge" and not any(check.get("passed") for check in checks):
        return "ready_for_codex_host_or_api_key"
    if checks and any(check.get("passed") for check in checks):
        return "ready_for_paideia_live_llm"
    if checks:
        return "needs_provider_api_key"
    return "ready_for_paideia_live_llm"


def _next_actions(provider: dict[str, Any], auth_kind: str) -> list[str]:
    provider_id = str(provider["provider_id"])
    actions = [
        f"ai22b-talent-foundry doctor-openclaw-provider-connectors --provider {provider_id} --output provider_connector_doctor.json",
    ]
    if provider.get("external_openclaw_provider"):
        actions.extend(
            [
                "openclaw onboard",
                "openclaw models auth list",
                "openclaw config --section model",
                "openclaw gateway run",
                (
                    "ai22b-talent-foundry doctor-openclaw-gateway-llm "
                    "--employment-record <employment_record.json> --probe-gateway --probe-chat "
                    "--output openclaw_gateway_llm_doctor.live.json"
                ),
            ]
        )
    elif provider.get("manifest_only"):
        actions.extend(
            [
                "openclaw onboard",
                "openclaw models auth list",
                "openclaw config --section model",
                "openclaw gateway run",
                (
                    "ai22b-talent-foundry doctor-openclaw-gateway-llm "
                    "--employment-record <employment_record.json> --probe-gateway --probe-chat "
                    "--output openclaw_gateway_llm_doctor.live.json"
                ),
            ]
        )
    elif auth_kind == "local_server_endpoint":
        actions.extend(
            [
                "Start the local model server before live use.",
                "ai22b-talent-foundry run-hired-agent --employment-record <employment_record.json> --llm-mode live",
            ]
        )
    elif auth_kind == "api_key_or_codex_host_bridge":
        actions.extend(
            [
                "Use the Codex host bridge for context-prepared chat, or set OPENAI_API_KEY for live Responses API calls.",
                "ai22b-talent-foundry run-hired-agent --employment-record <employment_record.json> --llm-mode live",
            ]
        )
    else:
        actions.extend(
            [
                "Set one of the listed provider environment variables in the local shell.",
                "ai22b-talent-foundry run-hired-agent --employment-record <employment_record.json> --llm-mode live",
            ]
        )
    return actions


def doctor_openclaw_provider_auth(
    *,
    providers: list[str] | None = None,
    openclaw_config_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    selected: list[str] = []
    for raw_provider in providers or []:
        provider = resolve_openclaw_provider(raw_provider)
        selected.append(str(provider["provider_id"]))
    catalog = build_openclaw_provider_connector_catalog(providers=selected or None)
    config_report = _load_redacted_openclaw_config(openclaw_config_path)
    openclaw_bin = shutil.which("openclaw")
    results: list[dict[str, Any]] = []
    for provider in catalog["providers"]:
        checks = [_env_check(env_var) for env_var in provider.get("secret_env_vars", [])]
        auth_kind = _auth_kind(provider)
        provider_hints = set(str(item) for item in config_report.get("provider_hints", []))
        config_has_provider_hint = str(provider["provider_id"]) in provider_hints
        if provider.get("manifest_only"):
            checks.append(
                {
                    "id": "tool:openclaw",
                    "kind": "local_cli",
                    "passed": bool(openclaw_bin),
                    "binary_on_path": bool(openclaw_bin),
                    "path_value_stored": False,
                    "message": "openclaw CLI is available." if openclaw_bin else "openclaw CLI was not found on PATH.",
                }
            )
            checks.append(
                {
                    "id": "openclaw_config:provider_hint",
                    "kind": "redacted_config_hint",
                    "passed": config_has_provider_hint,
                    "secret_value_stored": False,
                    "message": (
                        f"{provider['provider_id']} appears in the selected OpenClaw config."
                        if config_has_provider_hint
                        else f"{provider['provider_id']} was not detected in the selected OpenClaw config."
                    ),
                }
            )
        results.append(
            {
                "provider_id": provider["provider_id"],
                "service_id": provider["service_id"],
                "label": provider["label"],
                "engine": provider["engine"],
                "api_protocol": provider["api_protocol"],
                "connector_status": provider["connector_status"],
                "auth_kind": auth_kind,
                "auth_status": _auth_status(
                    provider=provider,
                    auth_kind=auth_kind,
                    checks=checks,
                    config_report=config_report,
                ),
                "paideia_live_adapter_ready": provider["live_adapter_ready"],
                "openclaw_gateway_recommended": bool(
                    provider.get("manifest_only") or provider.get("external_openclaw_provider")
                ),
                "local_endpoint": provider["local_endpoint"],
                "base_url_recorded": provider["base_url_recorded"],
                "checks": checks,
                "next_actions": _next_actions(provider, auth_kind),
            }
        )
    doctor = {
        "schema": OPENCLAW_PROVIDER_AUTH_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_owner_review",
        "results": results,
        "summary": {
            "provider_count": len(results),
            "paideia_live_adapter_ready_count": sum(1 for item in results if item["paideia_live_adapter_ready"]),
            "ready_for_paideia_live_llm_count": sum(
                1
                for item in results
                if item["auth_status"] in {"ready_for_paideia_live_llm", "ready_for_codex_host_or_api_key"}
            ),
            "manifest_or_plugin_provider_count": sum(1 for item in results if item["openclaw_gateway_recommended"]),
            "ready_for_openclaw_gateway_review_count": sum(
                1 for item in results if item["auth_status"] == "ready_for_openclaw_gateway_review"
            ),
            "needs_openclaw_provider_auth_count": sum(
                1 for item in results if item["auth_status"] == "needs_openclaw_provider_auth"
            ),
            "local_server_endpoint_count": sum(1 for item in results if item["auth_kind"] == "local_server_endpoint"),
        },
        "openclaw_config": {
            **config_report,
            "path": "<redacted-local-path>" if config_report.get("path") else None,
        },
        "policy": {
            "secret_values_stored": False,
            "absolute_local_paths_stored": False,
            "external_network_call_performed": False,
            "llm_identity_policy": "application_engine_not_identity",
            "plugin_auth_boundary": "OpenClaw owns OAuth, account sessions, cloud profiles, and custom provider plugins when Paideia cannot call the provider directly.",
        },
        "source_docs_checked": [
            "https://docs.openclaw.ai/providers",
            "https://docs.openclaw.ai/concepts/model-providers",
            "https://docs.openclaw.ai/gateway/openai-http-api",
        ],
    }
    if output_path is not None:
        _write_json(output_path, doctor)
    return doctor
