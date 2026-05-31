from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.channel_connectors import doctor_openclaw_channel_connectors
from ai22b.talent_foundry.channel_ingress import build_openclaw_channel_access_config
from ai22b.talent_foundry.openclaw_compat import find_openclaw_channel, find_openclaw_provider
from ai22b.talent_foundry.openclaw_channel_pairing import doctor_openclaw_channel_pairing
from ai22b.talent_foundry.openclaw_provider_auth import doctor_openclaw_provider_auth
from ai22b.talent_foundry.openclaw_runtime_bundle import OPENCLAW_REFERENCE_URLS
from ai22b.talent_foundry.provider_connectors import doctor_openclaw_provider_connectors


OPENCLAW_BRIDGE_SETUP_KIT_SCHEMA = "ai22b-openclaw-bridge-setup-kit/v1"
OPENCLAW_PROVIDER_PLUGIN_PLAN_SCHEMA = "ai22b-openclaw-provider-plugin-plan/v1"
OPENCLAW_CHANNEL_PLUGIN_PLAN_SCHEMA = "ai22b-openclaw-channel-plugin-plan/v1"
OPENCLAW_BRIDGE_SMOKE_TEST_SCHEMA = "ai22b-openclaw-bridge-smoke-tests/v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
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


def _env_vars_from_doctor(doctor: dict[str, Any]) -> list[str]:
    envs: list[str] = []
    for result in doctor.get("results", []):
        for check in result.get("checks", []):
            check_id = str(check.get("id") or "")
            if check_id.startswith("env:"):
                envs.extend(_env_alternatives(check_id.removeprefix("env:")))
    return _dedupe(envs)


def _providers_from_manifest(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    data = _read_json(path)
    if data.get("schema") == "ai22b-openclaw-config-import/v1":
        detected = data.get("detected", {})
        return _dedupe(
            [
                str(detected.get("primary_provider_id") or ""),
                *[str(item) for item in detected.get("supported_provider_ids", [])],
            ]
        )
    if data.get("schema") == "ai22b-openclaw-runtime-bundle/v1":
        return _dedupe([str(data.get("selection", {}).get("provider_id") or "")])
    return []


def _channels_from_manifest(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    data = _read_json(path)
    if data.get("schema") == "ai22b-openclaw-config-import/v1":
        return _dedupe([str(item) for item in data.get("detected", {}).get("channel_ids", [])])
    if data.get("schema") == "ai22b-openclaw-runtime-bundle/v1":
        return _dedupe([str(item) for item in data.get("selection", {}).get("channels", [])])
    return []


def _normalize_providers(providers: list[str] | None, manifest_path: Path | None) -> list[str]:
    selected = _dedupe([*(providers or []), *_providers_from_manifest(manifest_path)])
    if not selected:
        selected = ["openai"]
    normalized: list[str] = []
    for provider_id in selected:
        provider = find_openclaw_provider(provider_id)
        if provider is None:
            raise ValueError(f"Unsupported OpenClaw provider: {provider_id}")
        normalized.append(provider["provider_id"])
    return _dedupe(normalized)


def _normalize_channels(channels: list[str] | None, manifest_path: Path | None) -> list[str]:
    selected = _dedupe([*(channels or []), *_channels_from_manifest(manifest_path)])
    if not selected:
        selected = ["webchat"]
    normalized: list[str] = []
    for channel_id in selected:
        channel = find_openclaw_channel(channel_id)
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel: {channel_id}")
        normalized.append(channel["channel_id"])
    return _dedupe(normalized)


def _build_provider_plan(provider_doctor: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": OPENCLAW_PROVIDER_PLUGIN_PLAN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "providers": [
            {
                "provider_id": item["provider_id"],
                "runtime_status": item["runtime_status"],
                "api_protocol": item["api_protocol"],
                "live_adapter_ready": item["live_adapter_ready"],
                "ready_for_live_llm": item["ready_for_live_llm"],
                "adapter_path": (
                    "paideia_live_adapter"
                    if item["live_adapter_ready"]
                    else "openclaw_provider_plugin_or_oauth_required"
                ),
                "checks": item["checks"],
                "next_step": item["next_step"],
            }
            for item in provider_doctor["results"]
        ],
        "policy": {
            "llm_identity": "application_engine_only",
            "secret_values_stored": False,
            "provider_model_style": "provider/model",
        },
        "source_docs_checked": OPENCLAW_REFERENCE_URLS,
    }


def _provider_auth_map(provider_auth: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["provider_id"]): item for item in provider_auth.get("results", [])}


def _build_channel_plan(channel_doctor: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": OPENCLAW_CHANNEL_PLUGIN_PLAN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "channels": [
            {
                "channel_id": item["channel_id"],
                "connector_status": item["connector_status"],
                "generic_normalized_gateway_ready": item["generic_normalized_gateway_ready"],
                "direct_raw_ingress_ready": item["direct_raw_ingress_ready"],
                "direct_delivery_ready": item["direct_delivery_ready"],
                "ready_for_live_delivery": item["ready_for_live_delivery"],
                "checks": item["checks"],
                "next_step": item["next_step"],
                "openclaw_policy_notes": {
                    "dm_policy": "pairing_or_allowlist_recommended",
                    "group_policy": "allowlist_or_mention_gating_recommended",
                    "bot_loop_protection": "external_plugin_responsibility",
                },
            }
            for item in channel_doctor["results"]
        ],
        "policy": {
            "inbound_default": "deny_until_allowlisted",
            "live_delivery": "dry_run_first_then_explicit_live",
            "secret_values_stored": False,
        },
        "source_docs_checked": OPENCLAW_REFERENCE_URLS,
    }


def _generic_channel_message(channel_id: str) -> dict[str, Any]:
    return {
        "schema": "ai22b-openclaw-channel-message/v1",
        "channel": {"channel_id": channel_id},
        "conversation_id": f"agent:main:{channel_id}:conversation:<allowlisted-id>",
        "sender": {"sender_id": f"{channel_id}:<allowlisted-sender>", "display_name": "Owner"},
        "message": {"text": "Paideia bridge smoke test", "attachments": []},
        "metadata": {"external_platform_event": False, "smoke_test": True},
    }


def _platform_event_example(channel_id: str) -> dict[str, Any] | None:
    if channel_id == "telegram":
        return {
            "update_id": 100000001,
            "message": {
                "message_id": 1,
                "from": {"id": 12345, "is_bot": False, "first_name": "Owner"},
                "chat": {"id": 12345, "type": "private"},
                "text": "Paideia Telegram bridge smoke test",
            },
        }
    if channel_id == "discord":
        return {
            "t": "MESSAGE_CREATE",
            "d": {
                "id": "111111111111111111",
                "channel_id": "222222222222222222",
                "guild_id": "333333333333333333",
                "author": {"id": "444444444444444444", "username": "owner"},
                "content": "Paideia Discord bridge smoke test",
                "attachments": [],
            },
        }
    if channel_id == "slack":
        return {
            "type": "event_callback",
            "team_id": "T123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "Paideia Slack bridge smoke test",
                "ts": "1710000000.000100",
            },
        }
    return None


def _build_smoke_tests(
    *,
    channels: list[str],
    output_dir: Path,
    bind_host: str,
    port: int,
) -> dict[str, Any]:
    examples_dir = output_dir / "smoke_test_payloads"
    payloads: dict[str, str] = {}
    platform_events: dict[str, str] = {}
    for channel_id in channels:
        payload_path = examples_dir / f"{channel_id}_channel_message.json"
        _write_json(payload_path, _generic_channel_message(channel_id))
        payloads[channel_id] = str(payload_path)
        platform_event = _platform_event_example(channel_id)
        if platform_event is not None:
            event_path = examples_dir / f"{channel_id}_platform_event.json"
            _write_json(event_path, platform_event)
            platform_events[channel_id] = str(event_path)
    return {
        "schema": OPENCLAW_BRIDGE_SMOKE_TEST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "gateway": {
            "url": f"http://{bind_host}:{port}/openclaw/channel-message",
            "health": f"http://{bind_host}:{port}/health",
        },
        "payloads": payloads,
        "platform_events": platform_events,
        "commands": {
            "start_gateway": (
                "ai22b-talent-foundry run-openclaw-channel-gateway-server "
                "--employment-record <employment_record.json> "
                + " ".join(f"--channel {channel_id}" for channel_id in channels)
                + f" --bind-host {bind_host} --port {port} --access-config <channel_access_config.json>"
            ),
            "send_normalized_payload": (
                "Invoke-RestMethod -Method Post "
                f"-Uri http://{bind_host}:{port}/openclaw/channel-message "
                "-ContentType 'application/json' -InFile <payload.json>"
            ),
            "translate_supported_platform_event": (
                "ai22b-talent-foundry translate-openclaw-platform-event "
                "--channel <telegram|discord|slack> --event <platform_event.json> "
                "--access-config <channel_access_config.json> --output <translation.json>"
            ),
        },
        "secret_values_stored": False,
    }


def _build_env_template(
    *,
    providers: list[str],
    channels: list[str],
    provider_envs: list[str],
    channel_envs: list[str],
    bind_host: str,
    port: int,
) -> str:
    lines = [
        "# Paideia OpenClaw bridge setup environment template",
        "# Fill values only in your local shell. Do not commit this file with real values.",
        f"# Providers: {', '.join(providers)}",
    ]
    if provider_envs:
        for env_var in provider_envs:
            lines.append(f'# $env:{env_var} = "<set-locally>"')
    else:
        lines.append("# No provider secret env var was required by the selected provider plan.")
    lines.extend(["", f"# Channels: {', '.join(channels)}"])
    if channel_envs:
        for env_var in channel_envs:
            lines.append(f'# $env:{env_var} = "<set-locally>"')
    else:
        lines.append("# No channel secret env var was required by the selected channel plan.")
    lines.extend(
        [
            "",
            f'$env:PAIDEIA_OPENCLAW_GATEWAY_URL = "http://{bind_host}:{port}/openclaw/channel-message"',
            "",
        ]
    )
    return "\n".join(lines)


def build_openclaw_bridge_setup_kit(
    *,
    output_dir: Path,
    providers: list[str] | None = None,
    channels: list[str] | None = None,
    import_manifest_path: Path | None = None,
    runtime_bundle_path: Path | None = None,
    bind_host: str = "127.0.0.1",
    port: int = 8722,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_source = import_manifest_path or runtime_bundle_path
    selected_providers = _normalize_providers(providers, manifest_source)
    selected_channels = _normalize_channels(channels, manifest_source)

    provider_doctor = doctor_openclaw_provider_connectors(providers=selected_providers)
    provider_auth_doctor = doctor_openclaw_provider_auth(providers=selected_providers)
    channel_doctor = doctor_openclaw_channel_connectors(channels=selected_channels)
    channel_pairing_doctor = doctor_openclaw_channel_pairing(channels=selected_channels)
    provider_plan = _build_provider_plan(provider_doctor)
    provider_auth_by_id = _provider_auth_map(provider_auth_doctor)
    for provider in provider_plan["providers"]:
        auth = provider_auth_by_id.get(str(provider["provider_id"]), {})
        provider["auth_kind"] = auth.get("auth_kind")
        provider["auth_status"] = auth.get("auth_status")
        provider["openclaw_gateway_recommended"] = auth.get("openclaw_gateway_recommended")
    channel_plan = _build_channel_plan(channel_doctor)
    smoke_tests = _build_smoke_tests(
        channels=selected_channels,
        output_dir=output_dir,
        bind_host=bind_host,
        port=port,
    )

    provider_envs = _env_vars_from_doctor(provider_doctor)
    channel_envs = _env_vars_from_doctor(channel_doctor)
    env_template_path = output_dir / "openclaw_bridge.env.example.ps1"
    provider_plan_path = output_dir / "openclaw_provider_plugin_plan.json"
    provider_auth_doctor_path = output_dir / "openclaw_provider_auth_doctor.json"
    channel_plan_path = output_dir / "openclaw_channel_plugin_plan.json"
    channel_pairing_doctor_path = output_dir / "openclaw_channel_pairing_doctor.json"
    access_config_path = output_dir / "openclaw_bridge_channel_access_config.json"
    smoke_tests_path = output_dir / "openclaw_bridge_smoke_tests.json"
    manifest_path = output_dir / "openclaw_bridge_setup_kit.json"

    _write_text(
        env_template_path,
        _build_env_template(
            providers=selected_providers,
            channels=selected_channels,
            provider_envs=provider_envs,
            channel_envs=channel_envs,
            bind_host=bind_host,
            port=port,
        ),
    )
    _write_json(provider_plan_path, provider_plan)
    _write_json(provider_auth_doctor_path, provider_auth_doctor)
    _write_json(channel_plan_path, channel_plan)
    _write_json(channel_pairing_doctor_path, channel_pairing_doctor)
    _write_json(smoke_tests_path, smoke_tests)
    access_config = build_openclaw_channel_access_config(
        channels=selected_channels,
        allowed_senders=[],
        allowed_conversations=[],
        output_path=access_config_path,
    )

    kit = {
        "schema": OPENCLAW_BRIDGE_SETUP_KIT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_owner_review",
        "source": {
            "import_manifest": str(import_manifest_path) if import_manifest_path else None,
            "runtime_bundle": str(runtime_bundle_path) if runtime_bundle_path else None,
        },
        "selection": {
            "providers": selected_providers,
            "channels": selected_channels,
            "bind_host": bind_host,
            "port": port,
        },
        "readiness": {
            "provider_summary": provider_doctor["summary"],
            "provider_auth_summary": provider_auth_doctor["summary"],
            "channel_summary": channel_doctor["summary"],
            "channel_pairing_summary": channel_pairing_doctor["summary"],
            "access_policy": access_config["default_policy"],
            "secret_values_stored": False,
        },
        "artifacts": {
            "manifest": str(manifest_path),
            "env_template": str(env_template_path),
            "provider_plugin_plan": str(provider_plan_path),
            "provider_auth_doctor": str(provider_auth_doctor_path),
            "channel_plugin_plan": str(channel_plan_path),
            "channel_pairing_doctor": str(channel_pairing_doctor_path),
            "channel_access_config": str(access_config_path),
            "smoke_tests": str(smoke_tests_path),
            "smoke_test_payloads_dir": str(output_dir / "smoke_test_payloads"),
        },
        "next_commands": {
            "doctor_providers": (
                "ai22b-talent-foundry doctor-openclaw-provider-connectors "
                + " ".join(f"--provider {provider}" for provider in selected_providers)
                + f" --output {output_dir / 'provider_doctor.json'}"
            ),
            "doctor_provider_auth": (
                "ai22b-talent-foundry doctor-openclaw-provider-auth "
                + " ".join(f"--provider {provider}" for provider in selected_providers)
                + f" --output {provider_auth_doctor_path}"
            ),
            "doctor_channels": (
                "ai22b-talent-foundry doctor-openclaw-channel-connectors "
                + " ".join(f"--channel {channel}" for channel in selected_channels)
                + f" --output {output_dir / 'channel_doctor.json'}"
            ),
            "doctor_channel_pairing": (
                "ai22b-talent-foundry doctor-openclaw-channel-pairing "
                + " ".join(f"--channel {channel}" for channel in selected_channels)
                + f" --output {channel_pairing_doctor_path}"
            ),
            "start_gateway": smoke_tests["commands"]["start_gateway"],
            "send_normalized_payload": smoke_tests["commands"]["send_normalized_payload"],
        },
        "operator_notes": [
            "OpenClaw channels can run simultaneously; Paideia keeps all external channel access deny-by-default until allowlists are reviewed.",
            "Provider plugins, OAuth accounts, QR sessions, and bot tokens remain user-managed outside public artifacts.",
            "Use smoke_test_payloads before enabling live channel delivery.",
        ],
        "source_docs_checked": OPENCLAW_REFERENCE_URLS,
    }
    _write_json(manifest_path, kit)
    return kit
