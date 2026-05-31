from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.onboarding_choices import build_llm_service_health
from ai22b.talent_foundry.openclaw_employment_runtime import build_runtime_selection_snapshot
from ai22b.talent_foundry.openclaw_support_matrix import build_openclaw_support_matrix


OPENCLAW_LIVE_SMOKE_PLAN_SCHEMA = "ai22b-openclaw-live-smoke-plan/v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _quote(value: str | Path) -> str:
    text = str(value)
    if not text:
        return '""'
    escaped = text.replace("`", "``").replace('"', '`"')
    return f'"{escaped}"'


def _command(command: str, *, requires: list[str] | None = None, network_probe: bool = False) -> dict[str, Any]:
    return {
        "command": command,
        "requires": requires or [],
        "network_probe_performed_by_plan": False,
        "network_probe_when_operator_runs": network_probe,
    }


def _support_by_id(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item.get(key)): item for item in items if item.get(key)}


def _status(
    *,
    matrix_status: str,
    provider_support: dict[str, Any] | None,
    channel_support: list[dict[str, Any]],
    llm_health_status: str,
    external_provider: bool,
    external_channels: bool,
) -> str:
    if matrix_status != "pass":
        return "needs_openclaw_catalog_update"
    if external_provider or external_channels:
        return "ready_for_openclaw_gateway_unverified_external_selection"
    if not provider_support:
        return "non_openclaw_or_unresolved_provider"
    if provider_support.get("provider_plugin_or_oauth_required"):
        return "ready_after_openclaw_provider_plugin_or_oauth"
    if any(item.get("openclaw_plugin_or_bridge_required") for item in channel_support):
        return "ready_after_channel_plugin_or_bridge"
    if str(llm_health_status).startswith("needs_"):
        return "ready_after_provider_secret_or_local_server"
    return "ready_for_live_smoke_sequence"


def _gates(
    *,
    provider_id: str | None,
    provider_support: dict[str, Any] | None,
    channel_ids: list[str],
    channel_support: list[dict[str, Any]],
    llm_health: dict[str, Any],
    external_provider: bool,
    external_channels: list[str],
) -> list[dict[str, Any]]:
    missing_secret_envs = [
        str(check["id"]).removeprefix("env:")
        for check in llm_health.get("checks", [])
        if str(check.get("id", "")).startswith("env:") and not check.get("passed")
    ]
    return [
        {
            "id": "provider_route",
            "passed": bool(provider_support or external_provider or not provider_id),
            "provider_id": provider_id,
            "support_level": provider_support.get("support_level") if provider_support else None,
            "external_openclaw_provider": external_provider,
            "requires_provider_secret": bool(missing_secret_envs),
            "missing_secret_env_vars": missing_secret_envs,
            "requires_openclaw_provider_plugin_or_oauth": bool(
                provider_support and provider_support.get("provider_plugin_or_oauth_required")
            ),
        },
        {
            "id": "chat_channel_routes",
            "passed": len(external_channels) == 0 or bool(channel_ids),
            "channel_ids": channel_ids,
            "external_openclaw_channels": external_channels,
            "requires_channel_pairing_or_bridge": [
                item["channel_id"]
                for item in channel_support
                if item.get("openclaw_plugin_or_bridge_required")
            ],
        },
        {
            "id": "secret_policy",
            "passed": True,
            "secret_values_stored": False,
            "allowed_to_store": ["env var names", "redacted readiness categories", "artifact filenames"],
            "not_allowed_to_store": ["provider keys", "bot tokens", "OAuth refresh tokens", "QR session material"],
        },
        {
            "id": "plan_network_policy",
            "passed": True,
            "external_network_call_performed_by_plan": False,
            "live_network_calls_require_operator_flags": True,
        },
    ]


def build_openclaw_live_smoke_plan(
    employment_record_path: Path,
    *,
    runtime_bundle_path: Path | None = None,
    channels: list[str] | None = None,
    output_path: Path | None = None,
    markdown_output_path: Path | None = None,
    refresh_docs: bool = False,
    docs_timeout: int = 15,
) -> dict[str, Any]:
    employment_record_path = employment_record_path.expanduser().resolve()
    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")
    if employment.get("status") != "active":
        raise ValueError("Local employment record is not active")

    selection = build_runtime_selection_snapshot(employment, channels=channels)
    llm = selection.get("llm", {})
    chat = selection.get("chat", {})
    channel_ids = [str(item["channel_id"]) for item in chat.get("openclaw_channels", [])]
    llm_health = build_llm_service_health(employment.get("llm_service", {}) or {})
    support_matrix = build_openclaw_support_matrix(refresh_docs=refresh_docs, docs_timeout=docs_timeout)
    providers = _support_by_id(support_matrix.get("provider_support", []), "provider_id")
    channels_by_id = _support_by_id(support_matrix.get("channel_support", []), "channel_id")

    provider_id = llm.get("openclaw_provider_id")
    provider_support = providers.get(str(provider_id)) if provider_id else None
    external_provider = bool(provider_id and not provider_support)
    channel_support = [channels_by_id[channel_id] for channel_id in channel_ids if channel_id in channels_by_id]
    external_channels = [channel_id for channel_id in channel_ids if channel_id not in channels_by_id]
    runtime_bundle_ref = runtime_bundle_path.expanduser().resolve() if runtime_bundle_path else employment_record_path.parent / "openclaw_runtime_bundle" / "openclaw_runtime_bundle.json"
    output_dir = output_path.expanduser().resolve().parent if output_path else employment_record_path.parent / "openclaw_live_smoke_plan"

    first_channel = channel_ids[0] if channel_ids else "webchat"
    openclaw_model = llm.get("openclaw_model") or llm.get("selected_model") or "<provider/model>"
    api_protocol = llm.get("api_protocol")
    llm_engine = llm.get("engine")
    if api_protocol == "openclaw_cli_agent_local" or llm_engine == "openclaw_cli_local":
        live_runtime_path = "openclaw_cli_local"
    elif api_protocol == "openclaw_gateway_openai_chat_completions" or llm_engine == "openclaw_gateway_http":
        live_runtime_path = "openclaw_gateway_http"
    else:
        live_runtime_path = str(llm_engine or llm.get("service_id") or "selected_llm_adapter")
    commands = {
        "offline_context_smoke": _command(
            "ai22b-talent-foundry chat-hired-agent "
            f"--employment-record {_quote(employment_record_path)} "
            "--message \"OpenClaw offline context smoke test\" "
            "--llm-mode offline "
            f"--output {_quote(output_dir / 'chat_offline_smoke.json')}"
        ),
        "build_runtime_bundle_if_missing": _command(
            "ai22b-talent-foundry build-openclaw-runtime-bundle "
            f"--employment-record {_quote(employment_record_path)} "
            + " ".join(f"--channel {channel_id}" for channel_id in (channel_ids or ["webchat"]))
            + f" --output-dir {_quote(runtime_bundle_ref.parent)}"
        ),
        "static_preflight": _command(
            "ai22b-talent-foundry doctor-openclaw-runtime-preflight "
            f"--runtime-bundle {_quote(runtime_bundle_ref)} "
            "--run-channel-flow "
            f"--output {_quote(output_dir / 'openclaw_runtime_preflight.static.json')}"
        ),
        "gateway_live_probe": _command(
            "ai22b-talent-foundry doctor-openclaw-gateway-llm "
            f"--employment-record {_quote(employment_record_path)} "
            f"--runtime-bundle {_quote(runtime_bundle_ref)} "
            "--probe-gateway --probe-chat "
            f"--output {_quote(output_dir / 'openclaw_gateway_llm.live.json')}",
            requires=["OpenClaw Gateway running", "Gateway auth env vars when enabled"],
            network_probe=True,
        ),
        "openclaw_cli_live_probe": _command(
            "ai22b-talent-foundry chat-hired-agent "
            f"--employment-record {_quote(employment_record_path)} "
            "--message \"OpenClaw CLI local agent live smoke test\" "
            "--llm-mode live "
            f"--output {_quote(output_dir / 'openclaw_cli_agent.live.json')}",
            requires=["installed OpenClaw CLI on PATH", "`openclaw agent --local` provider auth configured"],
            network_probe=True,
        ),
        "live_llm_chat_smoke": _command(
            "ai22b-talent-foundry chat-hired-agent "
            f"--employment-record {_quote(employment_record_path)} "
            "--message \"OpenClaw live LLM smoke test\" "
            "--llm-mode live "
            f"--output {_quote(output_dir / 'chat_live_smoke.json')}",
            requires=["provider auth or OpenClaw Gateway configured"],
            network_probe=True,
        ),
        "offline_channel_message_smoke": _command(
            "ai22b-talent-foundry run-openclaw-channel-message "
            f"--employment-record {_quote(employment_record_path)} "
            f"--channel {first_channel} "
            "--message \"OpenClaw channel offline smoke test\" "
            "--llm-mode offline "
            f"--output {_quote(output_dir / 'channel_offline_smoke.json')}"
        ),
        "live_channel_message_smoke": _command(
            "ai22b-talent-foundry run-openclaw-channel-message "
            f"--employment-record {_quote(employment_record_path)} "
            f"--channel {first_channel} "
            "--message \"OpenClaw channel live smoke test\" "
            "--llm-mode live "
            f"--output {_quote(output_dir / 'channel_live_smoke.json')}",
            requires=["provider auth or OpenClaw Gateway configured", "channel plugin/pairing for external delivery"],
            network_probe=True,
        ),
    }

    plan = {
        "schema": OPENCLAW_LIVE_SMOKE_PLAN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": _status(
            matrix_status=str(support_matrix.get("status")),
            provider_support=provider_support,
            channel_support=channel_support,
            llm_health_status=str(llm_health.get("status")),
            external_provider=external_provider,
            external_channels=bool(external_channels),
        ),
        "employment_record": str(employment_record_path),
        "runtime_bundle": {
            "path": str(runtime_bundle_ref),
            "exists": runtime_bundle_ref.exists(),
        },
        "selection": {
            "agent": selection.get("agent", {}),
            "llm_service_id": llm.get("service_id"),
            "llm_engine": llm.get("engine"),
            "api_protocol": api_protocol,
            "live_runtime_path": live_runtime_path,
            "openclaw_provider_id": provider_id,
            "openclaw_model": openclaw_model,
            "openclaw_gateway_auto_routed": bool(llm.get("openclaw_gateway_auto_routed")),
            "chat_surface": chat.get("surface_id"),
            "channel_ids": channel_ids,
        },
        "openclaw_support": {
            "provider": provider_support
            or {
                "provider_id": provider_id,
                "support_level": "openclaw_gateway_unverified_external_provider",
                "recommended_path": "Let OpenClaw Gateway own this provider/model selector, then run OpenClaw's provider doctor.",
            },
            "channels": channel_support
            + [
                {
                    "channel_id": channel_id,
                    "support_level": "openclaw_gateway_unverified_external_channel",
                    "recommended_path": "Let the installed OpenClaw channel plugin own pairing and delivery, while Paideia preserves normalized envelopes.",
                }
                for channel_id in external_channels
            ],
        },
        "llm_service_health": llm_health,
        "gates": _gates(
            provider_id=str(provider_id) if provider_id else None,
            provider_support=provider_support,
            channel_ids=channel_ids,
            channel_support=channel_support,
            llm_health=llm_health,
            external_provider=external_provider,
            external_channels=external_channels,
        ),
        "commands": commands,
        "operator_sequence": [
            "offline_context_smoke",
            "build_runtime_bundle_if_missing",
            "static_preflight",
            "openclaw_cli_live_probe",
            "gateway_live_probe",
            "live_llm_chat_smoke",
            "offline_channel_message_smoke",
            "live_channel_message_smoke",
        ],
        "policy": {
            "llm_identity_policy": "application_engine_not_identity",
            "local_growth_records_are_identity": True,
            "private_training_files_sent_to_provider": False,
            "private_training_files_sent_to_channel": False,
            "secret_values_stored": False,
            "external_network_call_performed_by_plan": False,
        },
        "source_docs_checked": support_matrix.get("parity_summary", {}).get("source_urls", []),
    }
    if output_path:
        _write_json(output_path, plan)
    if markdown_output_path:
        render_openclaw_live_smoke_plan_markdown(plan, output_path=markdown_output_path)
    return plan


def render_openclaw_live_smoke_plan_markdown(
    plan: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> str:
    selection = plan.get("selection", {})
    lines = [
        "# OpenClaw Live Smoke Plan",
        "",
        f"- Status: `{plan.get('status')}`",
        f"- Agent: `{selection.get('agent', {}).get('name')}`",
        f"- Provider: `{selection.get('openclaw_provider_id')}`",
        f"- Model: `{selection.get('openclaw_model')}`",
        f"- Live runtime path: `{selection.get('live_runtime_path')}`",
        f"- Chat surface: `{selection.get('chat_surface')}`",
        f"- Channels: `{', '.join(selection.get('channel_ids') or []) or 'webchat'}`",
        "",
        "## Gates",
        "",
    ]
    for gate in plan.get("gates", []):
        lines.append(f"- `{gate.get('id')}`: `{gate.get('passed')}`")
    lines.extend(["", "## Operator Sequence", ""])
    commands = plan.get("commands", {})
    for step_id in plan.get("operator_sequence", []):
        command = commands.get(step_id, {})
        lines.extend([f"### {step_id}", "", "```powershell", str(command.get("command") or ""), "```", ""])
        if command.get("requires"):
            lines.append(f"Requires: {', '.join(command['requires'])}")
            lines.append("")
    lines.extend(
        [
            "## Safety Boundary",
            "",
            "- The plan itself performs no network call.",
            "- No provider key, bot token, QR session, OAuth refresh token, or private training file is stored.",
            "- Run live probe commands only after the owner has configured the selected provider and channel in OpenClaw.",
            "",
        ]
    )
    markdown = "\n".join(lines).rstrip() + "\n"
    if output_path:
        _write_text(output_path, markdown)
    return markdown
