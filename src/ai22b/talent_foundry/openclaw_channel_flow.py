from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.channel_delivery import SUPPORTED_DELIVERY_CHANNELS, send_openclaw_channel_outbound
from ai22b.talent_foundry.channel_gateway import run_openclaw_channel_message
from ai22b.talent_foundry.openclaw_compat import find_openclaw_channel


OPENCLAW_CHANNEL_FLOW_DOCTOR_SCHEMA = "ai22b-openclaw-channel-flow-doctor/v1"
OPENCLAW_CHANNEL_FLOW_REFERENCE_URLS = [
    "https://docs.openclaw.ai/channels",
    "https://docs.openclaw.ai/channels/channel-routing",
    "https://docs.openclaw.ai/cli/channels",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_employment(employment_record_path: Path) -> dict[str, Any]:
    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")
    if employment.get("status") != "active":
        raise ValueError("Local employment record is not active")
    return employment


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
    seen: set[str] = set()
    for raw_channel in requested:
        channel = find_openclaw_channel(raw_channel)
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel: {raw_channel}")
        channel_id = str(channel["channel_id"])
        if channel_id not in seen:
            normalized.append(channel_id)
            seen.add(channel_id)
    return normalized


def _default_conversation_id(channel_id: str) -> str:
    defaults = {
        "telegram": "telegram:group:123456:topic:1",
        "discord": "discord:channel:1234567890:thread:987654321",
        "slack": "slack:channel:C123456:thread:1700000000.000000",
        "webchat": "webchat:session:local-doctor",
    }
    return defaults.get(channel_id, f"{channel_id}:conversation:local-doctor")


def _delivery_not_applicable(channel_run: dict[str, Any], reason: str) -> dict[str, Any]:
    outbound = channel_run.get("outbound", {})
    return {
        "schema": "ai22b-openclaw-channel-delivery-run/v1",
        "mode": "dry-run",
        "status": "not_applicable",
        "channel_id": outbound.get("channel_id"),
        "adapter": reason,
        "target_valid": False,
        "network_call_performed": False,
        "security": {
            "secret_values_stored": False,
            "private_training_files_sent_to_channel": False,
            "mode_live_required_for_external_send": True,
        },
        "source_outbound": {
            "reply_to_message_id": outbound.get("reply_to_message_id"),
            "conversation_id": outbound.get("conversation_id"),
            "text_length": len(str(outbound.get("text") or "")),
        },
    }


def doctor_openclaw_channel_flow(
    employment_record_path: Path,
    *,
    channels: list[str] | None = None,
    message: str = "Paideia OpenClaw channel dry-run smoke test.",
    sender_id: str = "paideia-channel-doctor",
    conversation_id: str | None = None,
    output_path: Path | None = None,
    output_dir: Path | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    learn_from_chat: bool = False,
) -> dict[str, Any]:
    employment_record_path = employment_record_path.expanduser().resolve()
    employment = _load_employment(employment_record_path)
    selected_channels = _normalize_channels(employment, channels)
    output_path = output_path.expanduser().resolve() if output_path else employment_record_path.parent / "openclaw_channel_flow_doctor.json"
    output_dir = (
        output_dir.expanduser().resolve()
        if output_dir
        else output_path.parent / f"{output_path.stem}_artifacts"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    channel_results: list[dict[str, Any]] = []
    for channel_id in selected_channels:
        channel_run_path = output_dir / f"{channel_id}_channel_run.json"
        delivery_path = output_dir / f"{channel_id}_delivery_dry_run.json"
        try:
            channel_run = run_openclaw_channel_message(
                employment_record_path,
                channel_id=channel_id,
                message=message,
                sender_id=sender_id,
                conversation_id=conversation_id or _default_conversation_id(channel_id),
                output_path=channel_run_path,
                llm_mode=llm_mode,
                llm_model=llm_model,
                learn_from_chat=learn_from_chat,
                metadata={"doctor": "openclaw_channel_flow"},
            )
            if channel_id in SUPPORTED_DELIVERY_CHANNELS:
                delivery = send_openclaw_channel_outbound(
                    channel_run,
                    mode="dry-run",
                    output_path=delivery_path,
                )
            else:
                delivery = _delivery_not_applicable(channel_run, "external_or_loopback_channel_plugin_required")
                _write_json(delivery_path, delivery)
            channel_results.append(
                {
                    "channel_id": channel_id,
                    "status": "pass" if channel_run.get("status") == "reply_ready" else "needs_attention",
                    "channel_run": str(channel_run_path),
                    "delivery_dry_run": str(delivery_path),
                    "reply_ready": channel_run.get("status") == "reply_ready",
                    "outbound_text_length": len(str(channel_run.get("outbound", {}).get("text") or "")),
                    "delivery": {
                        "status": delivery.get("status"),
                        "adapter": delivery.get("adapter"),
                        "target_valid": delivery.get("target_valid"),
                        "network_call_performed": delivery.get("network_call_performed"),
                    },
                }
            )
        except Exception as exc:
            channel_results.append(
                {
                    "channel_id": channel_id,
                    "status": "needs_attention",
                    "channel_run": str(channel_run_path),
                    "delivery_dry_run": str(delivery_path),
                    "reply_ready": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:800],
                }
            )

    failed = [item for item in channel_results if item.get("status") != "pass"]
    report = {
        "schema": OPENCLAW_CHANNEL_FLOW_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not failed else "needs_attention",
        "employment": {
            "employment_id": employment["employment_id"],
            "agent": employment["agent"],
            "employment_record": str(employment_record_path),
        },
        "mode": {
            "llm_mode": llm_mode,
            "learn_from_chat": learn_from_chat,
            "external_delivery_mode": "dry-run",
            "external_network_call_performed": False,
        },
        "summary": {
            "channel_count": len(channel_results),
            "reply_ready_count": sum(1 for item in channel_results if item.get("reply_ready")),
            "delivery_dry_run_count": sum(1 for item in channel_results if item.get("delivery_dry_run")),
            "failed_count": len(failed),
        },
        "channels": channel_results,
        "security": {
            "secret_values_stored": False,
            "private_training_files_sent_to_channel": False,
            "raw_external_payload_saved": False,
            "live_delivery_requires_explicit_send_openclaw_channel_outbound": True,
        },
        "next_commands": {
            "run_live_delivery_after_review": (
                "ai22b-talent-foundry send-openclaw-channel-outbound "
                "--channel-run <channel_run.json> --mode live --target-id <platform_target>"
            ),
            "run_channel_gateway_server": (
                "ai22b-talent-foundry run-openclaw-channel-gateway-server "
                f"--employment-record {employment_record_path} "
                + " ".join(f"--channel {channel}" for channel in selected_channels)
            ),
        },
        "source_docs_checked": OPENCLAW_CHANNEL_FLOW_REFERENCE_URLS,
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
