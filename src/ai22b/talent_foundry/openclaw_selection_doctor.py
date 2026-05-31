from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.onboarding_choices import (
    build_llm_service_health,
    resolve_chat_surface,
    resolve_llm_service,
)
from ai22b.talent_foundry.openclaw_compat import find_openclaw_channel, find_openclaw_provider
from ai22b.talent_foundry.openclaw_support_matrix import build_openclaw_support_matrix


OPENCLAW_SELECTION_DOCTOR_SCHEMA = "ai22b-openclaw-selection-doctor/v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _provider_id_from_selection(selected_llm_service: dict[str, Any]) -> str | None:
    openclaw_model = selected_llm_service.get("openclaw_model")
    if isinstance(openclaw_model, str) and "/" in openclaw_model:
        provider_id = openclaw_model.split("/", 1)[0]
        provider = find_openclaw_provider(provider_id)
        if provider:
            return str(provider["provider_id"])
    provider_id = selected_llm_service.get("openclaw_provider_id")
    if provider_id:
        provider = find_openclaw_provider(str(provider_id))
        if provider:
            return str(provider["provider_id"])
    return None


def _channel_ids_from_selection(chat_surface: dict[str, Any], channels: list[str] | None) -> list[str]:
    selected: list[str] = []
    for raw_channel in channels or []:
        channel = find_openclaw_channel(raw_channel)
        if channel is not None:
            selected.append(str(channel["channel_id"]))
    surface_channel = chat_surface.get("openclaw_channel_id")
    if surface_channel:
        channel = find_openclaw_channel(str(surface_channel))
        if channel is not None:
            selected.append(str(channel["channel_id"]))
    deduped: list[str] = []
    seen: set[str] = set()
    for channel_id in selected:
        if channel_id not in seen:
            seen.add(channel_id)
            deduped.append(channel_id)
    return deduped


def _selection_status(
    *,
    matrix_status: str,
    provider_support: dict[str, Any] | None,
    channel_support: list[dict[str, Any]],
    llm_health: dict[str, Any],
) -> str:
    if matrix_status != "pass":
        return "needs_catalog_update"
    if provider_support is None:
        return "needs_supported_openclaw_provider"
    health_status = str(llm_health.get("status") or "")
    if health_status.startswith("needs_"):
        return "needs_llm_configuration"
    if provider_support.get("support_level") == "openclaw_plugin_or_oauth_required":
        return "needs_openclaw_provider_plugin"
    if any(item.get("support", {}).get("openclaw_plugin_or_bridge_required") for item in channel_support):
        return "needs_channel_plugin_or_bridge"
    return "ready_for_onboarding"


def doctor_openclaw_selection(
    *,
    llm_service: str | None = None,
    llm_engine: str | None = None,
    llm_model: str | None = None,
    llm_model_path: str | None = None,
    chat_surface: str | None = None,
    channels: list[str] | None = None,
    output_path: Path | None = None,
    refresh_docs: bool = False,
    docs_timeout: int = 15,
) -> dict[str, Any]:
    selected_llm_service = resolve_llm_service(
        llm_service=llm_service,
        llm_engine=llm_engine,
        llm_model=llm_model,
        llm_model_path=llm_model_path,
    )
    selected_chat_surface = resolve_chat_surface(chat_surface)
    llm_health = build_llm_service_health(selected_llm_service)
    support_matrix = build_openclaw_support_matrix(refresh_docs=refresh_docs, docs_timeout=docs_timeout)
    provider_by_id = {item["provider_id"]: item for item in support_matrix.get("provider_support", [])}
    channel_by_id = {item["channel_id"]: item for item in support_matrix.get("channel_support", [])}

    provider_id = _provider_id_from_selection(selected_llm_service)
    selected_channel_ids = _channel_ids_from_selection(selected_chat_surface, channels)
    provider_support = provider_by_id.get(provider_id) if provider_id else None
    channel_support = [
        {
            "channel_id": channel_id,
            "support": channel_by_id.get(channel_id),
        }
        for channel_id in selected_channel_ids
    ]
    status = _selection_status(
        matrix_status=str(support_matrix.get("status")),
        provider_support=provider_support,
        channel_support=channel_support,
        llm_health=llm_health,
    )
    doctor = {
        "schema": OPENCLAW_SELECTION_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "selected_llm_service": selected_llm_service,
        "selected_chat_surface": selected_chat_surface,
        "llm_service_health": llm_health,
        "openclaw_selection": {
            "provider_id": provider_id,
            "provider_support": provider_support,
            "channels": channel_support,
        },
        "support_matrix_summary": {
            "schema": support_matrix.get("schema"),
            "status": support_matrix.get("status"),
            "source_mode": support_matrix.get("source_mode"),
            "coverage": support_matrix.get("coverage"),
            "parity_summary": support_matrix.get("parity_summary"),
        },
        "next_commands": _next_commands(
            provider_id=provider_id,
            selected_llm_service=selected_llm_service,
            selected_chat_surface=selected_chat_surface,
            selected_channel_ids=selected_channel_ids,
        ),
        "claim_boundary": {
            "secret_values_stored": False,
            "external_network_call_performed": False,
            "what_this_checks": "Provider/model and channel ids resolve to OpenClaw-compatible Paideia catalogs and readiness paths.",
            "what_this_does_not_check": "It does not authenticate provider APIs, complete OAuth, pair QR sessions, or live-send platform messages.",
        },
    }
    if output_path is not None:
        _write_json(output_path, doctor)
    return doctor


def render_openclaw_selection_summary(
    doctor: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> str:
    selected_llm = doctor.get("selected_llm_service", {})
    selected_chat = doctor.get("selected_chat_surface", {})
    selection = doctor.get("openclaw_selection", {})
    provider_support = selection.get("provider_support") or {}
    channels = selection.get("channels") or []
    llm_health = doctor.get("llm_service_health", {})
    claim_boundary = doctor.get("claim_boundary", {})
    next_commands = doctor.get("next_commands", {})

    lines = [
        "# OpenClaw Selection Summary",
        "",
        f"- Status: `{doctor.get('status')}`",
        f"- LLM service: `{selected_llm.get('service_id') or selected_llm.get('id')}`",
        f"- LLM engine: `{selected_llm.get('engine')}`",
        f"- OpenClaw model: `{selected_llm.get('openclaw_model') or selected_llm.get('selected_model') or 'not specified'}`",
        f"- LLM health: `{llm_health.get('status')}`",
        f"- Chat surface: `{selected_chat.get('id')}`",
        "",
        "## Provider",
        "",
        f"- Provider id: `{selection.get('provider_id') or 'not resolved'}`",
        f"- Support level: `{provider_support.get('support_level') or 'not available'}`",
        f"- Recommended path: {provider_support.get('recommended_path') or 'Review provider configuration.'}",
        f"- Required env vars: `{', '.join(provider_support.get('secret_env_vars') or []) or 'none'}`",
        "",
        "## Channels",
        "",
    ]
    if channels:
        for item in channels:
            support = item.get("support") or {}
            lines.extend(
                [
                    f"- `{item.get('channel_id')}`",
                    f"  - Support level: `{support.get('support_level') or 'not available'}`",
                    f"  - Recommended path: {support.get('recommended_path') or 'Review channel configuration.'}",
                    f"  - Required env vars: `{', '.join(support.get('required_env_vars') or []) or 'none'}`",
                ]
            )
    else:
        lines.append("- No OpenClaw chat channel was selected. Local console/chat surfaces can still run.")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            f"- Secret values stored: `{claim_boundary.get('secret_values_stored')}`",
            f"- External network call performed: `{claim_boundary.get('external_network_call_performed')}`",
            f"- Scope: {claim_boundary.get('what_this_checks')}",
            f"- Not checked: {claim_boundary.get('what_this_does_not_check')}",
            "",
            "## Next Commands",
            "",
        ]
    )
    for key, command in next_commands.items():
        lines.extend(
            [
                f"### {key}",
                "",
                "```powershell",
                str(command),
                "```",
                "",
            ]
        )
    summary = "\n".join(lines).rstrip() + "\n"
    if output_path is not None:
        _write_text(output_path, summary)
    return summary


def _next_commands(
    *,
    provider_id: str | None,
    selected_llm_service: dict[str, Any],
    selected_chat_surface: dict[str, Any],
    selected_channel_ids: list[str],
) -> dict[str, str]:
    channel_args = " ".join(f"--channel {channel_id}" for channel_id in selected_channel_ids)
    llm_model = selected_llm_service.get("openclaw_model") or selected_llm_service.get("selected_model") or "<provider/model>"
    commands = {
        "provider_doctor": (
            "ai22b-talent-foundry doctor-openclaw-provider-connectors "
            f"--provider {provider_id or '<provider>'} --output provider_connector_doctor.json"
        ),
        "channel_doctor": (
            "ai22b-talent-foundry doctor-openclaw-channel-connectors "
            f"{channel_args} --output channel_connector_doctor.json"
        ).replace("  ", " ").strip(),
        "support_matrix": "ai22b-talent-foundry build-openclaw-support-matrix --output openclaw_support_matrix.json",
        "onboard": (
            "ai22b-talent-foundry start-console "
            f"--output-dir runs\\console_onboarding"
        ),
    }
    if selected_llm_service.get("engine") == "openclaw_gateway_http":
        commands["gateway_llm_after_hire"] = (
            "ai22b-talent-foundry doctor-openclaw-gateway-llm "
            "--employment-record <employment_record.json> "
            f"--model {llm_model} --output openclaw_gateway_llm_doctor.json"
        )
    if selected_channel_ids:
        commands["channel_flow_after_hire"] = (
            "ai22b-talent-foundry doctor-openclaw-channel-flow "
            "--employment-record <employment_record.json> "
            f"{channel_args} --output openclaw_channel_flow_doctor.json"
        ).replace("  ", " ").strip()
    if str(selected_chat_surface.get("id", "")).startswith("openclaw-channel-"):
        commands["web_or_channel_gateway_after_hire"] = (
            "ai22b-talent-foundry run-openclaw-channel-gateway-server "
            "--employment-record <employment_record.json> "
            f"{channel_args} --port 8722 --output-dir channel_gateway_runs"
        ).replace("  ", " ").strip()
    return commands
