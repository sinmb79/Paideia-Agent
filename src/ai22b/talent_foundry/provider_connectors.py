from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.openclaw_compat import (
    OPENCLAW_MANIFEST_ONLY_PROVIDERS,
    OPENCLAW_MODEL_PROVIDERS,
    find_openclaw_provider,
    openclaw_provider_manifest,
)


OPENCLAW_PROVIDER_CONNECTOR_CATALOG_SCHEMA = "ai22b-openclaw-provider-connector-catalog/v1"
OPENCLAW_PROVIDER_CONNECTOR_DOCTOR_SCHEMA = "ai22b-openclaw-provider-connector-doctor/v1"

LIVE_ADAPTER_PROTOCOLS = {
    "openai_responses",
    "openai_chat_completions",
    "anthropic_messages",
    "gemini_generate_content",
    "ollama_chat",
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _env_alternatives(env_var: str) -> list[str]:
    return [part.strip() for part in env_var.split(" or ") if part.strip()]


def _env_present(env_var: str) -> bool:
    for candidate in _env_alternatives(env_var):
        value = os.environ.get(candidate)
        if value:
            return True
    return False


def _provider_entry(provider: dict[str, Any]) -> dict[str, Any]:
    api_protocol = provider.get("api_protocol")
    engine = provider.get("engine")
    base_url = provider.get("base_url")
    live_adapter_ready = api_protocol in LIVE_ADAPTER_PROTOCOLS and engine != "openclaw_manifest_only"
    local_endpoint = str(base_url or "").startswith(("http://localhost", "http://127.0.0.1"))
    if engine == "openclaw_manifest_only":
        connector_status = "provider_plugin_required"
    elif live_adapter_ready:
        connector_status = "paideia_live_adapter_ready"
    else:
        connector_status = "adapter_manifest_only"
    return {
        "provider_id": provider["provider_id"],
        "service_id": provider["service_id"],
        "label": provider["label"],
        "connector_status": connector_status,
        "selection_model": "provider/model",
        "engine": engine,
        "api_protocol": api_protocol,
        "live_adapter_ready": live_adapter_ready,
        "manifest_only": engine == "openclaw_manifest_only",
        "local_endpoint": local_endpoint,
        "base_url_recorded": bool(base_url),
        "base_url": base_url,
        "secret_env_vars": provider.get("secret_env_vars", []),
        "aliases": provider.get("aliases", []),
        "status": provider.get("status"),
        "policy": {
            "secret_values_stored": False,
            "identity_boundary": "provider supplies language generation only; Paideia talent identity stays in local artifacts",
        },
    }


def build_openclaw_provider_connector_catalog(
    *,
    providers: list[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    selected = providers or [
        *[provider["provider_id"] for provider in OPENCLAW_MODEL_PROVIDERS],
        *OPENCLAW_MANIFEST_ONLY_PROVIDERS,
    ]
    entries = []
    seen: set[str] = set()
    for provider_id in selected:
        provider = find_openclaw_provider(provider_id)
        if provider is None:
            raise ValueError(f"Unsupported OpenClaw provider: {provider_id}")
        key = provider["provider_id"]
        if key in seen:
            continue
        seen.add(key)
        entries.append(_provider_entry(provider))
    catalog = {
        "schema": OPENCLAW_PROVIDER_CONNECTOR_CATALOG_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_provider_manifest": openclaw_provider_manifest(),
        "providers": entries,
        "summary": {
            "provider_count": len(entries),
            "live_adapter_ready_count": sum(1 for item in entries if item["live_adapter_ready"]),
            "manifest_only_count": sum(1 for item in entries if item["manifest_only"]),
            "openai_compatible_count": sum(1 for item in entries if item["api_protocol"] == "openai_chat_completions"),
            "anthropic_compatible_count": sum(1 for item in entries if item["api_protocol"] == "anthropic_messages"),
            "local_endpoint_count": sum(1 for item in entries if item["local_endpoint"]),
        },
        "policy": {
            "provider_model_selection": "OpenClaw-compatible provider/model strings are accepted during onboarding and hiring.",
            "secret_handling": "Only environment variable names are written; secret values are never serialized.",
            "manifest_only": "Provider pages that require provider-owned plugins, OAuth, media-only tools, or custom runners remain selectable but disabled for live LLM calls until configured.",
        },
    }
    if output_path is not None:
        _write_json(output_path, catalog)
    return catalog


def doctor_openclaw_provider_connectors(
    *,
    providers: list[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    catalog = build_openclaw_provider_connector_catalog(providers=providers)
    results = []
    for provider in catalog["providers"]:
        checks = []
        for env_var in provider["secret_env_vars"]:
            passed = _env_present(env_var)
            checks.append(
                {
                    "id": f"env:{env_var}",
                    "kind": "environment_secret",
                    "passed": passed,
                    "secret_value_stored": False,
                    "message": "configured" if passed else f"{env_var} is not set in this shell.",
                }
            )
        needs_secret = bool(provider["secret_env_vars"]) and not provider["local_endpoint"]
        secret_group_ready = not needs_secret or any(check["passed"] for check in checks)
        ready_for_live = bool(provider["live_adapter_ready"]) and bool(provider["base_url_recorded"]) and secret_group_ready
        if provider["provider_id"] == "openai" and not ready_for_live:
            bridge_status = "ready_for_codex_bridge_without_api_key"
        elif provider["manifest_only"]:
            bridge_status = "provider_plugin_required"
        else:
            bridge_status = "ready_for_live_llm" if ready_for_live else "needs_secret_or_local_server"
        results.append(
            {
                "provider_id": provider["provider_id"],
                "service_id": provider["service_id"],
                "connector_status": provider["connector_status"],
                "api_protocol": provider["api_protocol"],
                "base_url_recorded": provider["base_url_recorded"],
                "live_adapter_ready": provider["live_adapter_ready"],
                "ready_for_live_llm": ready_for_live,
                "runtime_status": bridge_status,
                "checks": checks,
                "next_step": _next_step(provider, checks),
            }
        )
    doctor = {
        "schema": OPENCLAW_PROVIDER_CONNECTOR_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": {
            "provider_count": len(results),
            "live_adapter_ready_count": sum(1 for item in results if item["live_adapter_ready"]),
            "ready_for_live_llm_count": sum(1 for item in results if item["ready_for_live_llm"]),
            "needs_secret_or_local_server_count": sum(
                1
                for item in results
                if item["live_adapter_ready"] and not item["ready_for_live_llm"] and item["provider_id"] != "openai"
            ),
            "provider_plugin_required_count": sum(1 for item in results if item["connector_status"] == "provider_plugin_required"),
        },
        "secret_values_stored": False,
    }
    if output_path is not None:
        _write_json(output_path, doctor)
    return doctor


def _next_step(provider: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    if provider["manifest_only"]:
        return "Configure the OpenClaw provider plugin, OAuth profile, media tool, or custom runner before live use."
    if provider["local_endpoint"]:
        return "Start the local provider server, select a model with provider/model, then run a live chat smoke test."
    if checks and not any(check["passed"] for check in checks):
        return "Set one of the listed environment variables in the shell that runs Paideia, then rerun doctor."
    return "Select a concrete provider/model and run Paideia live chat with the trained talent context."
