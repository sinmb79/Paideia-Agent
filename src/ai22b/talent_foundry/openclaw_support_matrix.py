from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.channel_connectors import build_openclaw_channel_connector_catalog
from ai22b.talent_foundry.openclaw_parity import audit_openclaw_parity
from ai22b.talent_foundry.provider_connectors import build_openclaw_provider_connector_catalog


OPENCLAW_SUPPORT_MATRIX_SCHEMA = "ai22b-openclaw-support-matrix/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _provider_support_level(provider: dict[str, Any]) -> str:
    if provider["live_adapter_ready"] and provider["local_endpoint"]:
        return "local_or_gateway_live_ready"
    if provider["live_adapter_ready"]:
        return "paideia_direct_or_openclaw_gateway_ready"
    if provider["manifest_only"]:
        return "openclaw_plugin_or_oauth_required"
    return "manifest_only_review_required"


def _channel_support_level(channel: dict[str, Any]) -> str:
    if channel["channel_id"] == "webchat":
        return "loopback_chat_ready"
    if channel["direct_raw_ingress_ready"] and channel["direct_delivery_ready"]:
        return "paideia_direct_flow_ready"
    if channel["direct_delivery_ready"]:
        return "paideia_direct_delivery_ready_ingress_plugin_required"
    if channel["generic_normalized_gateway_ready"]:
        return "normalized_gateway_ready_plugin_delivery_required"
    return "external_bridge_required"


def _provider_matrix_entry(provider: dict[str, Any]) -> dict[str, Any]:
    support_level = _provider_support_level(provider)
    return {
        "provider_id": provider["provider_id"],
        "service_id": provider["service_id"],
        "label": provider["label"],
        "support_level": support_level,
        "selection_model": provider["selection_model"],
        "paideia_direct_adapter_ready": provider["live_adapter_ready"],
        "openclaw_gateway_route_ready": True,
        "local_endpoint": provider["local_endpoint"],
        "provider_plugin_or_oauth_required": provider["manifest_only"],
        "api_protocol": provider["api_protocol"],
        "secret_env_vars": provider["secret_env_vars"],
        "recommended_path": _provider_recommended_path(provider, support_level),
    }


def _provider_recommended_path(provider: dict[str, Any], support_level: str) -> str:
    if support_level == "local_or_gateway_live_ready":
        return "Start the local model server, select provider/model, then use Paideia direct runtime or OpenClaw Gateway."
    if support_level == "paideia_direct_or_openclaw_gateway_ready":
        return "Set the provider API key environment variable or let OpenClaw Gateway own provider auth, then select provider/model."
    if support_level == "openclaw_plugin_or_oauth_required":
        return "Use OpenClaw's provider plugin, OAuth profile, media tool, or custom runner, then pass Paideia talent context through the Gateway handoff."
    return "Review provider metadata before enabling live LLM calls."


def _channel_matrix_entry(channel: dict[str, Any]) -> dict[str, Any]:
    support_level = _channel_support_level(channel)
    return {
        "channel_id": channel["channel_id"],
        "label": channel["label"],
        "transport": channel["transport"],
        "support_level": support_level,
        "generic_normalized_gateway_ready": channel["generic_normalized_gateway_ready"],
        "paideia_direct_ingress_ready": channel["direct_raw_ingress_ready"],
        "paideia_direct_delivery_ready": channel["direct_delivery_ready"],
        "openclaw_plugin_or_bridge_required": support_level == "normalized_gateway_ready_plugin_delivery_required",
        "required_env_vars": channel["required_env_vars"],
        "recommended_path": _channel_recommended_path(channel, support_level),
    }


def _channel_recommended_path(channel: dict[str, Any], support_level: str) -> str:
    if support_level == "loopback_chat_ready":
        return "Run the local WebChat or channel gateway and test without external platform secrets."
    if support_level == "paideia_direct_flow_ready":
        return "Use doctor-openclaw-channel-flow first; enable live delivery only after channel tokens and allowlists are configured."
    if support_level == "paideia_direct_delivery_ready_ingress_plugin_required":
        return "Use the normalized gateway for inbound events, then enable Paideia direct outbound delivery only after tokens, targets, and allowlists are configured."
    if support_level == "normalized_gateway_ready_plugin_delivery_required":
        return channel["setup"]
    return "Configure an external bridge, then post normalized OpenClaw-style envelopes to Paideia."


def build_openclaw_support_matrix(
    *,
    output_path: Path | None = None,
    refresh_docs: bool = False,
    docs_timeout: int = 15,
) -> dict[str, Any]:
    provider_catalog = build_openclaw_provider_connector_catalog()
    channel_catalog = build_openclaw_channel_connector_catalog()
    parity = audit_openclaw_parity(refresh_docs=refresh_docs, docs_timeout=docs_timeout)

    provider_support = [_provider_matrix_entry(provider) for provider in provider_catalog["providers"]]
    channel_support = [_channel_matrix_entry(channel) for channel in channel_catalog["channels"]]
    providers_with_direct = [item for item in provider_support if item["paideia_direct_adapter_ready"]]
    providers_with_plugins = [item for item in provider_support if item["provider_plugin_or_oauth_required"]]
    channels_direct = [item for item in channel_support if item["support_level"] in {"paideia_direct_flow_ready", "loopback_chat_ready"}]
    channels_plugin = [item for item in channel_support if item["openclaw_plugin_or_bridge_required"]]

    matrix = {
        "schema": OPENCLAW_SUPPORT_MATRIX_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if parity["status"] == "pass" else "needs_update",
        "source_mode": parity["source_mode"],
        "coverage": {
            "providers": {
                "total": len(provider_support),
                "paideia_direct_adapter_ready_count": len(providers_with_direct),
                "openclaw_gateway_route_ready_count": len(provider_support),
                "plugin_or_oauth_required_count": len(providers_with_plugins),
                "local_endpoint_count": sum(1 for item in provider_support if item["local_endpoint"]),
                "parity_missing_count": parity["coverage"]["providers"]["missing_count"],
            },
            "channels": {
                "total": len(channel_support),
                "direct_or_loopback_flow_ready_count": len(channels_direct),
                "normalized_gateway_ready_count": sum(1 for item in channel_support if item["generic_normalized_gateway_ready"]),
                "plugin_or_bridge_required_count": len(channels_plugin),
                "parity_missing_count": parity["coverage"]["channels"]["missing_count"],
            },
        },
        "operator_paths": {
            "first_sample_agent": (
                "ai22b-talent-foundry run-graham-junior-quickstart "
                "--llm-service openclaw_gateway_http --llm-model openrouter/meta-llama/llama-3.1-8b "
                "--llm-model-path http://127.0.0.1:18789/v1 --chat-surface openclaw-channel-webchat --channel webchat"
            ),
            "provider_doctor": "ai22b-talent-foundry doctor-openclaw-provider-connectors --output provider_connector_doctor.json",
            "channel_doctor": "ai22b-talent-foundry doctor-openclaw-channel-connectors --output channel_connector_doctor.json",
            "channel_flow_doctor": (
                "ai22b-talent-foundry doctor-openclaw-channel-flow "
                "--employment-record <employment_record.json> --channel webchat --output openclaw_channel_flow_doctor.json"
            ),
            "gateway_llm_doctor": (
                "ai22b-talent-foundry doctor-openclaw-gateway-llm "
                "--employment-record <employment_record.json> --output openclaw_gateway_llm_doctor.json"
            ),
            "parity_audit": "ai22b-talent-foundry audit-openclaw-parity --output openclaw_parity_audit.json --fail-on-missing",
        },
        "claim_boundary": {
            "what_this_proves": "Paideia can select and route OpenClaw-style provider/model and channel ids through local catalogs, doctors, Gateway handoff, and normalized channel envelopes.",
            "what_this_does_not_prove": "It does not prove that every external OAuth login, paid provider key, bot token, QR session, or third-party channel plugin is configured on this computer.",
            "secret_values_stored": False,
        },
        "provider_support": provider_support,
        "channel_support": channel_support,
        "parity_summary": {
            "status": parity["status"],
            "provider_missing_ids": parity["coverage"]["providers"]["missing_ids"],
            "channel_missing_ids": parity["coverage"]["channels"]["missing_ids"],
            "source_urls": sorted(
                set(parity["source_snapshots"]["providers"]["source_urls"])
                | set(parity["source_snapshots"]["channels"]["source_urls"])
            ),
        },
    }
    if output_path is not None:
        _write_json(output_path, matrix)
    return matrix
