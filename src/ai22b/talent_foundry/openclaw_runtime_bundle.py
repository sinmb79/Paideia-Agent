from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.channel_connectors import (
    build_openclaw_channel_connector_catalog,
    doctor_openclaw_channel_connectors,
)
from ai22b.talent_foundry.channel_delivery import (
    SUPPORTED_DELIVERY_CHANNELS,
    build_openclaw_channel_delivery_config,
)
from ai22b.talent_foundry.channel_gateway import build_openclaw_gateway_config
from ai22b.talent_foundry.channel_ingress import build_openclaw_channel_access_config
from ai22b.talent_foundry.onboarding_choices import build_llm_service_health
from ai22b.talent_foundry.openclaw_compat import (
    find_openclaw_channel,
    find_openclaw_provider,
    openclaw_channel_manifest,
    openclaw_provider_manifest,
)
from ai22b.talent_foundry.provider_connectors import doctor_openclaw_provider_connectors


OPENCLAW_RUNTIME_BUNDLE_SCHEMA = "ai22b-openclaw-runtime-bundle/v1"
OPENCLAW_CONFIG_PATCH_SCHEMA = "ai22b-openclaw-config-patch/v1"

OPENCLAW_REFERENCE_URLS = [
    "https://docs.openclaw.ai/reference/wizard",
    "https://docs.openclaw.ai/providers",
    "https://docs.openclaw.ai/concepts/model-providers",
    "https://docs.openclaw.ai/channels",
    "https://docs.openclaw.ai/channels/channel-routing",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_employment(employment_record_path: Path) -> dict[str, Any]:
    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")
    if employment.get("status") != "active":
        raise ValueError("Local employment record is not active")
    return employment


def _safe_agent_key(employment: dict[str, Any]) -> str:
    raw = f"paideia-{employment.get('employment_id', 'agent')}"
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-").casefold()
    return value or "paideia-agent"


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item).strip()
        if not value:
            continue
        key = value.casefold()
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result


def _env_alternatives(env_var: str) -> list[str]:
    return [part.strip() for part in str(env_var).split(" or ") if part.strip()]


def _infer_provider_id(employment: dict[str, Any]) -> str:
    llm_service = employment.get("llm_service", {})
    llm_runtime = employment.get("llm_runtime", {})
    provider_id = llm_service.get("openclaw_provider_id") or llm_runtime.get("openclaw_provider_id")
    if provider_id:
        return str(provider_id)
    model_selector = str(llm_service.get("openclaw_model") or llm_runtime.get("openclaw_model") or "")
    if "/" in model_selector:
        return model_selector.split("/", 1)[0]
    service_id = str(llm_service.get("service_id") or llm_runtime.get("service") or "")
    provider = find_openclaw_provider(service_id)
    if provider is not None:
        return str(provider["provider_id"])
    return "openai"


def _model_selector(employment: dict[str, Any], provider_id: str) -> str:
    llm_service = employment.get("llm_service", {})
    llm_runtime = employment.get("llm_runtime", {})
    openclaw_model = llm_service.get("openclaw_model") or llm_runtime.get("openclaw_model")
    if openclaw_model:
        return str(openclaw_model)
    provider = find_openclaw_provider(provider_id)
    selected_model = llm_service.get("selected_model") or llm_runtime.get("model") or (
        provider.get("default_model") if provider else None
    )
    if selected_model:
        selected = str(selected_model)
        return selected if "/" in selected else f"{provider_id}/{selected}"
    return f"{provider_id}/<select-model>"


def _normalize_channels(employment: dict[str, Any], channels: list[str] | None) -> list[str]:
    requested = list(channels or [])
    if not requested:
        chat_surface = employment.get("chat_surface", {})
        if chat_surface.get("openclaw_channel_id"):
            requested.append(str(chat_surface["openclaw_channel_id"]))
        elif str(chat_surface.get("id", "")).startswith("openclaw-channel-"):
            requested.append(str(chat_surface["id"]))
    if not requested:
        requested = ["webchat"]
    normalized: list[str] = []
    for channel_id in requested:
        channel = find_openclaw_channel(channel_id)
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel: {channel_id}")
        normalized.append(str(channel["channel_id"]))
    return _dedupe(normalized)


def _channel_env_vars(channel_doctor: dict[str, Any]) -> list[str]:
    env_vars: list[str] = []
    for result in channel_doctor.get("results", []):
        for check in result.get("checks", []):
            check_id = str(check.get("id") or "")
            if check_id.startswith("env:"):
                env_vars.extend(_env_alternatives(check_id.removeprefix("env:")))
    return _dedupe(env_vars)


def _provider_env_vars(provider_doctor: dict[str, Any]) -> list[str]:
    env_vars: list[str] = []
    for result in provider_doctor.get("results", []):
        for check in result.get("checks", []):
            check_id = str(check.get("id") or "")
            if check_id.startswith("env:"):
                env_vars.extend(_env_alternatives(check_id.removeprefix("env:")))
    return _dedupe(env_vars)


def _build_env_template(
    *,
    provider_id: str,
    channels: list[str],
    provider_env_vars: list[str],
    channel_env_vars: list[str],
    bind_host: str,
    port: int,
) -> str:
    lines = [
        "# Paideia Agent OpenClaw runtime environment template",
        "# Set these values only in your local shell. Do not commit real secrets.",
        f"# Provider: {provider_id}",
    ]
    if provider_env_vars:
        lines.append("# Choose one compatible provider secret unless your provider requires more.")
        for env_var in provider_env_vars:
            lines.append(f'# $env:{env_var} = "<set-locally>"')
    else:
        lines.append("# No provider secret is required by the selected local/offline adapter.")
    lines.extend(
        [
            "",
            "# Channel bridge secrets and paths",
            f"# Channels: {', '.join(channels)}",
        ]
    )
    if channel_env_vars:
        for env_var in channel_env_vars:
            lines.append(f'# $env:{env_var} = "<set-locally>"')
    else:
        lines.append("# No channel secret is required for the selected local channel.")
    lines.extend(
        [
            "",
            "# Local Paideia OpenClaw-compatible gateway",
            f'$env:PAIDEIA_OPENCLAW_GATEWAY_URL = "http://{bind_host}:{port}/openclaw/channel-message"',
            "",
        ]
    )
    return "\n".join(lines)


def _build_config_patch(
    *,
    employment_record_path: Path,
    employment: dict[str, Any],
    provider_id: str,
    model_selector: str,
    provider: dict[str, Any] | None,
    channels: list[str],
    bind_host: str,
    port: int,
    provider_env_vars: list[str],
    channel_doctor: dict[str, Any],
) -> dict[str, Any]:
    agent_key = _safe_agent_key(employment)
    gateway_url = f"http://{bind_host}:{port}/openclaw/channel-message"
    channel_connectors = {item["channel_id"]: item for item in channel_doctor.get("results", [])}
    return {
        "schema": OPENCLAW_CONFIG_PATCH_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_runtime": "OpenClaw-compatible local gateway",
        "source_docs_checked": OPENCLAW_REFERENCE_URLS,
        "employment": {
            "employment_id": employment["employment_id"],
            "agent": employment["agent"],
            "employment_record": str(employment_record_path),
            "identity_boundary": "Paideia local training records remain identity; the selected LLM is an application engine.",
        },
        "openclaw_json_patch": {
            "agents": {
                "defaults": {
                    "model": {"primary": model_selector},
                },
                agent_key: {
                    "name": employment["agent"]["name"],
                    "role": employment["agent"].get("role"),
                    "model": {"primary": model_selector},
                    "channels": channels,
                    "gateway": {
                        "type": "paideia-local-openclaw-channel-gateway",
                        "url": gateway_url,
                        "health": f"http://{bind_host}:{port}/health",
                    },
                    "memory": {
                        "source": "Paideia memory_substrate, learning ledger, curriculum, and Reasoning Ledger artifacts",
                        "private_reasoning_trace": "do_not_store",
                    },
                },
            },
            "models": {
                provider_id: {
                    "provider": provider_id,
                    "model": model_selector,
                    "apiProtocol": (provider or {}).get("api_protocol"),
                    "baseURL": (provider or {}).get("base_url"),
                    "auth": {
                        "envCandidates": provider_env_vars,
                        "secretValuesStored": False,
                    },
                },
            },
            "channels": {
                channel_id: {
                    "enabled": True,
                    "gatewayURL": gateway_url,
                    "connectorStatus": channel_connectors.get(channel_id, {}).get("connector_status"),
                    "nextStep": channel_connectors.get(channel_id, {}).get("next_step"),
                }
                for channel_id in channels
            },
        },
        "operator_policy": {
            "existing_openclaw_config": "merge_or_review; do_not_reset_without_user_choice",
            "secret_values_stored": False,
            "private_training_files_exported": False,
            "recommended_bind_host": "127.0.0.1",
            "live_channel_send": "explicit_plugin_or_send_command_required",
        },
    }


def build_openclaw_runtime_bundle(
    employment_record_path: Path,
    *,
    channels: list[str] | None = None,
    output_dir: Path | None = None,
    bind_host: str = "127.0.0.1",
    port: int = 8722,
) -> dict[str, Any]:
    employment_record_path = employment_record_path.resolve()
    employment = _load_employment(employment_record_path)
    selected_channels = _normalize_channels(employment, channels)
    provider_id = _infer_provider_id(employment)
    provider = find_openclaw_provider(provider_id)
    if provider is None:
        raise ValueError(f"Unsupported OpenClaw provider: {provider_id}")
    model = _model_selector(employment, provider_id)

    output_dir = (output_dir or employment_record_path.parent / "openclaw_runtime_bundle").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    gateway_config_path = output_dir / "openclaw_gateway_config.json"
    access_config_path = output_dir / "openclaw_channel_access_config.json"
    provider_doctor_path = output_dir / "openclaw_provider_doctor.json"
    channel_connector_catalog_path = output_dir / "openclaw_channel_connectors.json"
    channel_doctor_path = output_dir / "openclaw_channel_doctor.json"
    llm_health_path = output_dir / "llm_service_health.json"
    config_patch_path = output_dir / "openclaw_config_patch.json"
    env_template_path = output_dir / "openclaw.env.example.ps1"
    manifest_path = output_dir / "openclaw_runtime_bundle.json"

    gateway_config = build_openclaw_gateway_config(
        employment_record_path,
        channels=selected_channels,
        bind_host=bind_host,
        port=port,
        output_path=gateway_config_path,
    )
    build_openclaw_channel_access_config(
        channels=selected_channels,
        output_path=access_config_path,
    )
    provider_doctor = doctor_openclaw_provider_connectors(
        providers=[provider_id],
        output_path=provider_doctor_path,
    )
    channel_connector_catalog = build_openclaw_channel_connector_catalog(
        channels=selected_channels,
        output_path=channel_connector_catalog_path,
    )
    channel_doctor = doctor_openclaw_channel_connectors(
        channels=selected_channels,
        output_path=channel_doctor_path,
    )
    llm_health = build_llm_service_health(employment.get("llm_service", {}))
    _write_json(llm_health_path, llm_health)

    delivery_channels = [channel for channel in selected_channels if channel in SUPPORTED_DELIVERY_CHANNELS]
    delivery_config_path: Path | None = None
    if delivery_channels:
        delivery_config_path = output_dir / "openclaw_channel_delivery_config.json"
        build_openclaw_channel_delivery_config(
            channels=delivery_channels,
            output_path=delivery_config_path,
        )

    provider_envs = _provider_env_vars(provider_doctor)
    channel_envs = _channel_env_vars(channel_doctor)
    config_patch = _build_config_patch(
        employment_record_path=employment_record_path,
        employment=employment,
        provider_id=provider_id,
        model_selector=model,
        provider=provider,
        channels=selected_channels,
        bind_host=bind_host,
        port=port,
        provider_env_vars=provider_envs,
        channel_doctor=channel_doctor,
    )
    _write_json(config_patch_path, config_patch)
    _write_text(
        env_template_path,
        _build_env_template(
            provider_id=provider_id,
            channels=selected_channels,
            provider_env_vars=provider_envs,
            channel_env_vars=channel_envs,
            bind_host=bind_host,
            port=port,
        ),
    )

    artifacts = {
        "manifest": str(manifest_path),
        "openclaw_config_patch": str(config_patch_path),
        "openclaw_env_template": str(env_template_path),
        "gateway_config": str(gateway_config_path),
        "channel_access_config": str(access_config_path),
        "provider_doctor": str(provider_doctor_path),
        "channel_connector_catalog": str(channel_connector_catalog_path),
        "channel_doctor": str(channel_doctor_path),
        "llm_service_health": str(llm_health_path),
    }
    if delivery_config_path is not None:
        artifacts["channel_delivery_config"] = str(delivery_config_path)

    bundle = {
        "schema": OPENCLAW_RUNTIME_BUNDLE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_owner_review",
        "employment": {
            "employment_id": employment["employment_id"],
            "agent": employment["agent"],
            "employment_record": str(employment_record_path),
        },
        "selection": {
            "provider_id": provider_id,
            "model": model,
            "channels": selected_channels,
            "chat_surface": employment.get("chat_surface", {}),
            "bind_host": bind_host,
            "port": port,
        },
        "readiness": {
            "llm_service_health": llm_health,
            "provider_doctor_summary": provider_doctor["summary"],
            "channel_connector_summary": channel_connector_catalog["summary"],
            "channel_doctor_summary": channel_doctor["summary"],
            "secret_values_stored": False,
        },
        "artifacts": artifacts,
        "next_commands": {
            "doctor_provider": (
                "ai22b-talent-foundry doctor-openclaw-provider-connectors "
                f"--provider {provider_id} --output {provider_doctor_path}"
            ),
            "doctor_channels": (
                "ai22b-talent-foundry doctor-openclaw-channel-connectors "
                + " ".join(f"--channel {channel}" for channel in selected_channels)
                + f" --output {channel_doctor_path}"
            ),
            "run_channel_gateway": (
                "ai22b-talent-foundry run-openclaw-channel-gateway-server "
                f"--employment-record {employment_record_path} "
                + " ".join(f"--channel {channel}" for channel in selected_channels)
                + f" --access-config {access_config_path} --bind-host {bind_host} --port {port}"
            ),
            "run_webchat": (
                "ai22b-talent-foundry run-openclaw-webchat-server "
                f"--employment-record {employment_record_path} --bind-host {bind_host} --port {port}"
            ),
            "check_llm_service": (
                "ai22b-talent-foundry check-llm-service "
                f"--llm-service {employment.get('llm_service', {}).get('service_id', '')} "
                f"--llm-model {employment.get('llm_service', {}).get('selected_model') or ''} "
                f"--output {llm_health_path}"
            ),
        },
        "openclaw_reference": {
            "provider_catalog": openclaw_provider_manifest(),
            "channel_catalog": openclaw_channel_manifest(),
            "docs": OPENCLAW_REFERENCE_URLS,
        },
        "notes": [
            "Review openclaw_config_patch.json before merging into an existing OpenClaw config.",
            "Set secrets in the local shell using openclaw.env.example.ps1; real values are never written.",
            "Channel access config starts deny-by-default and needs allowlisted senders or conversations before raw platform events are routed.",
        ],
        "generated_gateway_config": gateway_config,
    }
    _write_json(manifest_path, bundle)
    return bundle
