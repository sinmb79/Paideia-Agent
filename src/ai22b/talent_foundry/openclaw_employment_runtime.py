from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.onboarding_choices import build_llm_service_health
from ai22b.talent_foundry.openclaw_compat import (
    external_openclaw_channel_descriptor,
    find_openclaw_channel,
    find_openclaw_provider,
    normalize_openclaw_channel_id,
)
from ai22b.talent_foundry.openclaw_support_matrix import build_openclaw_support_matrix


OPENCLAW_RUNTIME_SELECTION_SNAPSHOT_SCHEMA = "ai22b-openclaw-runtime-selection-snapshot/v1"
OPENCLAW_EMPLOYMENT_RUNTIME_DOCTOR_SCHEMA = "ai22b-openclaw-employment-runtime-doctor/v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _provider_id_from_runtime(employment_record: dict[str, Any]) -> str | None:
    llm_service = employment_record.get("llm_service", {}) or {}
    llm_runtime = employment_record.get("llm_runtime", {}) or {}
    openclaw_model = str(
        llm_service.get("openclaw_model")
        or llm_runtime.get("openclaw_model")
        or llm_service.get("selected_model")
        or ""
    )
    if "/" in openclaw_model:
        provider_id = openclaw_model.split("/", 1)[0]
        if find_openclaw_provider(provider_id):
            return provider_id
        if llm_service.get("openclaw_provider_unverified"):
            return provider_id
    provider_id = llm_service.get("openclaw_provider_id") or llm_runtime.get("openclaw_provider_id")
    if provider_id and (find_openclaw_provider(str(provider_id)) or llm_service.get("openclaw_provider_unverified")):
        return str(provider_id)
    service_id = str(llm_service.get("service_id") or llm_runtime.get("service") or "")
    provider = find_openclaw_provider(service_id)
    return str(provider["provider_id"]) if provider else None


def _channel_ids_from_runtime(employment_record: dict[str, Any], channels: list[str] | None = None) -> list[str]:
    selected: list[str] = []
    for channel_id in channels or []:
        channel = find_openclaw_channel(channel_id)
        if channel:
            selected.append(str(channel["channel_id"]))
        else:
            selected.append(normalize_openclaw_channel_id(channel_id))
    chat_surface = employment_record.get("chat_surface", {}) or {}
    surface_channel = chat_surface.get("openclaw_channel_id")
    if surface_channel:
        channel = find_openclaw_channel(str(surface_channel))
        if channel:
            selected.append(str(channel["channel_id"]))
        elif chat_surface.get("external_openclaw_channel"):
            selected.append(normalize_openclaw_channel_id(str(surface_channel)))
    surface_id = str(chat_surface.get("id") or "")
    if surface_id.startswith("openclaw-channel-"):
        channel = find_openclaw_channel(surface_id)
        if channel:
            selected.append(str(channel["channel_id"]))
    deduped: list[str] = []
    seen: set[str] = set()
    for channel_id in selected:
        if channel_id not in seen:
            seen.add(channel_id)
            deduped.append(channel_id)
    return deduped


def _channel_descriptor(channel_id: str) -> dict[str, Any]:
    return find_openclaw_channel(channel_id) or external_openclaw_channel_descriptor(channel_id)


def _safe_secret_env_vars(llm_service: dict[str, Any], llm_runtime: dict[str, Any]) -> list[str]:
    values = [
        *[str(item) for item in llm_service.get("secret_env_vars", []) or []],
        *[str(item) for item in llm_runtime.get("secret_env_vars", []) or []],
    ]
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def build_runtime_selection_snapshot(
    employment_record: dict[str, Any],
    *,
    channels: list[str] | None = None,
) -> dict[str, Any]:
    """Return a no-secret snapshot of the LLM and chat channel selected for a hired talent."""

    llm_service = employment_record.get("llm_service", {}) or {}
    llm_runtime = employment_record.get("llm_runtime", {}) or {}
    chat_surface = employment_record.get("chat_surface", {}) or {}
    provider_id = _provider_id_from_runtime(employment_record)
    channel_ids = _channel_ids_from_runtime(employment_record, channels)
    provider = find_openclaw_provider(provider_id) if provider_id else None
    channel_entries = [_channel_descriptor(channel_id) for channel_id in channel_ids]
    return {
        "schema": OPENCLAW_RUNTIME_SELECTION_SNAPSHOT_SCHEMA,
        "employment_id": employment_record.get("employment_id"),
        "agent": employment_record.get("agent", {}),
        "llm": {
            "service_id": llm_service.get("service_id") or llm_service.get("id") or llm_runtime.get("service"),
            "label": llm_service.get("label"),
            "engine": llm_service.get("engine") or llm_runtime.get("engine"),
            "selected_model": llm_service.get("selected_model") or llm_runtime.get("model"),
            "selected_model_path_recorded": bool(llm_service.get("selected_model_path") or llm_runtime.get("model_path")),
            "openclaw_provider_id": provider_id,
            "openclaw_provider_label": provider.get("label") if provider else None,
            "openclaw_model": llm_service.get("openclaw_model") or llm_runtime.get("openclaw_model"),
            "openclaw_agent_target": llm_service.get("openclaw_agent_target") or llm_runtime.get("openclaw_agent_target"),
            "openclaw_gateway_auto_routed": bool(llm_service.get("openclaw_gateway_auto_routed")),
            "api_protocol": llm_service.get("api_protocol") or llm_runtime.get("api_protocol"),
            "network_access": llm_service.get("network_access") or llm_runtime.get("network_access"),
            "base_url_recorded": bool(llm_service.get("base_url") or llm_runtime.get("base_url")),
            "secret_env_vars": _safe_secret_env_vars(llm_service, llm_runtime),
            "secret_values_stored": False,
        },
        "chat": {
            "surface_id": chat_surface.get("id"),
            "label": chat_surface.get("label"),
            "status": chat_surface.get("status"),
            "entrypoint": chat_surface.get("entrypoint"),
            "channel_policy": chat_surface.get("channel_policy"),
            "openclaw_channels": [
                {
                    "channel_id": channel["channel_id"],
                    "label": channel["label"],
                    "transport": channel["transport"],
                }
                for channel in channel_entries
                if channel
            ],
        },
        "policy": {
            "llm_is_identity": False,
            "local_growth_records_are_identity": True,
            "private_training_files_sent_to_provider": False,
            "private_training_files_sent_to_channel": False,
            "hidden_chain_of_thought_stored": False,
        },
    }


def _runtime_status(
    *,
    matrix_status: str,
    provider_id: str | None,
    llm_health_status: str,
    provider_support: dict[str, Any] | None,
    channel_support: list[dict[str, Any]],
) -> str:
    if matrix_status != "pass":
        return "needs_openclaw_catalog_update"
    if not provider_support:
        if not provider_id:
            return "non_openclaw_or_unresolved_provider"
        return "ready_for_openclaw_gateway_unverified_provider"
    if llm_health_status.startswith("needs_"):
        return "needs_llm_configuration"
    if provider_support.get("support_level") == "openclaw_plugin_or_oauth_required":
        return "ready_after_openclaw_provider_plugin_or_oauth"
    if any((item.get("support") or {}).get("openclaw_plugin_or_bridge_required") for item in channel_support):
        return "ready_after_channel_plugin_or_bridge"
    return "ready_for_paideia_or_openclaw_runtime"


def build_openclaw_employment_runtime_doctor(
    employment_record_path: Path,
    *,
    channels: list[str] | None = None,
    output_path: Path | None = None,
    refresh_docs: bool = False,
    docs_timeout: int = 15,
) -> dict[str, Any]:
    employment_record = _read_json(employment_record_path)
    if employment_record.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")
    if employment_record.get("status") != "active":
        raise ValueError("Local employment record is not active")

    selection = build_runtime_selection_snapshot(employment_record, channels=channels)
    llm_health = build_llm_service_health(employment_record.get("llm_service", {}) or {})
    support_matrix = build_openclaw_support_matrix(refresh_docs=refresh_docs, docs_timeout=docs_timeout)
    provider_by_id = {item["provider_id"]: item for item in support_matrix.get("provider_support", [])}
    channel_by_id = {item["channel_id"]: item for item in support_matrix.get("channel_support", [])}
    provider_id = selection.get("llm", {}).get("openclaw_provider_id")
    channel_ids = [item["channel_id"] for item in selection.get("chat", {}).get("openclaw_channels", [])]
    provider_support = provider_by_id.get(provider_id) if provider_id else None
    channel_support = [
        {
            "channel_id": channel_id,
            "support": channel_by_id.get(channel_id),
        }
        for channel_id in channel_ids
    ]
    status = _runtime_status(
        matrix_status=str(support_matrix.get("status")),
        provider_id=provider_id,
        llm_health_status=str(llm_health.get("status")),
        provider_support=provider_support,
        channel_support=channel_support,
    )
    channel_args = " ".join(f"--channel {channel_id}" for channel_id in channel_ids)
    doctor = {
        "schema": OPENCLAW_EMPLOYMENT_RUNTIME_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "employment_record": str(employment_record_path),
        "runtime_selection": selection,
        "llm_service_health": llm_health,
        "openclaw_support": {
            "provider": provider_support,
            "channels": channel_support,
        },
        "next_commands": {
            "build_runtime_bundle": (
                "ai22b-talent-foundry build-openclaw-runtime-bundle "
                f"--employment-record {employment_record_path} "
                f"{channel_args} --output-dir openclaw_runtime_bundle"
            ).replace("  ", " ").strip(),
            "doctor_runtime_preflight": (
                "ai22b-talent-foundry doctor-openclaw-runtime-preflight "
                "--runtime-bundle openclaw_runtime_bundle/openclaw_runtime_bundle.json "
                "--run-channel-flow --output openclaw_runtime_bundle/openclaw_runtime_preflight.json"
            ),
            "chat_hired_agent": (
                "ai22b-talent-foundry chat-hired-agent "
                f"--employment-record {employment_record_path} --message \"안녕\""
            ),
            "run_channel_message": (
                "ai22b-talent-foundry run-openclaw-channel-message "
                f"--employment-record {employment_record_path} "
                f"--channel {channel_ids[0] if channel_ids else 'webchat'} --message \"안녕\" "
                "--output openclaw_channel_run.json"
            ),
        },
        "claim_boundary": {
            "secret_values_stored": False,
            "external_network_call_performed": False,
            "local_absolute_paths_exported": False,
            "what_this_checks": "The hired talent's selected LLM provider/model, OpenClaw route, chat surface, and channel support path.",
            "what_this_does_not_check": "It does not authenticate paid provider keys, complete OAuth, pair QR sessions, or live-send platform messages.",
        },
    }
    if output_path:
        _write_json(output_path, doctor)
    return doctor


def render_openclaw_employment_runtime_summary(
    doctor: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> str:
    selection = doctor.get("runtime_selection", {})
    llm = selection.get("llm", {})
    chat = selection.get("chat", {})
    provider = (doctor.get("openclaw_support") or {}).get("provider") or {}
    channels = (doctor.get("openclaw_support") or {}).get("channels") or []
    lines = [
        "# OpenClaw Employment Runtime Summary",
        "",
        f"- Status: `{doctor.get('status')}`",
        f"- Agent: `{selection.get('agent', {}).get('name')}`",
        f"- LLM service: `{llm.get('service_id')}`",
        f"- LLM engine: `{llm.get('engine')}`",
        f"- OpenClaw provider: `{llm.get('openclaw_provider_id') or 'not resolved'}`",
        f"- OpenClaw model: `{llm.get('openclaw_model') or llm.get('selected_model') or 'not specified'}`",
        f"- API protocol: `{llm.get('api_protocol') or 'not specified'}`",
        f"- Network access: `{llm.get('network_access') or 'not specified'}`",
        f"- Chat surface: `{chat.get('surface_id')}`",
        "",
        "## Provider Path",
        "",
        f"- Support level: `{provider.get('support_level') or 'not available'}`",
        f"- Recommended path: {provider.get('recommended_path') or 'Review provider configuration.'}",
        f"- Required env vars: `{', '.join(provider.get('secret_env_vars') or []) or 'none'}`",
        "",
        "## Channel Path",
        "",
    ]
    if channels:
        for item in channels:
            support = item.get("support") or {}
            lines.extend(
                [
                    f"- `{item.get('channel_id')}`: `{support.get('support_level') or 'not available'}`",
                    f"  Recommended path: {support.get('recommended_path') or 'Review channel configuration.'}",
                ]
            )
    else:
        lines.append("- No OpenClaw chat channel is selected. Local CLI/Codex chat can still run.")
    lines.extend(["", "## Next Commands", ""])
    for key, command in (doctor.get("next_commands") or {}).items():
        lines.extend([f"### {key}", "", "```powershell", str(command), "```", ""])
    lines.extend(
        [
            "## Safety Boundary",
            "",
            "- No provider key, bot token, QR session, or private training file is stored in this summary.",
            "- The LLM remains an application engine; the Paideia talent identity stays in local growth records.",
            "",
        ]
    )
    summary = "\n".join(lines).rstrip() + "\n"
    if output_path:
        _write_text(output_path, summary)
    return summary
