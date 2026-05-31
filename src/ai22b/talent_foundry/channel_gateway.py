from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
from ai22b.talent_foundry.openclaw_compat import (
    find_openclaw_channel,
    openclaw_channel_manifest,
)


OPENCLAW_GATEWAY_CONFIG_SCHEMA = "ai22b-openclaw-channel-gateway-config/v1"
OPENCLAW_CHANNEL_MESSAGE_SCHEMA = "ai22b-openclaw-channel-message/v1"
OPENCLAW_CHANNEL_RUN_SCHEMA = "ai22b-openclaw-channel-run/v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(data, ensure_ascii=False) + "\n")


def _load_employment(employment_record_path: Path) -> dict[str, Any]:
    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")
    if employment.get("status") != "active":
        raise ValueError("Local employment record is not active")
    return employment


def _channel_or_error(channel_id: str) -> dict[str, Any]:
    channel = find_openclaw_channel(channel_id)
    if channel is None:
        raise ValueError(f"Unsupported OpenClaw channel: {channel_id}")
    return channel


def _message_id(
    *,
    employment_id: str,
    channel_id: str,
    conversation_id: str,
    sender_id: str,
    message: str,
) -> str:
    raw = f"{employment_id}|{channel_id}|{conversation_id}|{sender_id}|{message}".encode("utf-8")
    return "openclaw_msg_" + hashlib.sha256(raw).hexdigest()[:16]


def build_openclaw_gateway_config(
    employment_record_path: Path,
    *,
    channels: list[str] | None = None,
    bind_host: str = "127.0.0.1",
    port: int = 8722,
    output_path: Path | None = None,
) -> dict[str, Any]:
    employment = _load_employment(employment_record_path)
    selected_channels = channels or ["webchat"]
    resolved_channels = [_channel_or_error(channel_id) for channel_id in selected_channels]
    config = {
        "schema": OPENCLAW_GATEWAY_CONFIG_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "employment": {
            "employment_id": employment["employment_id"],
            "agent": employment["agent"],
            "employment_record": str(employment_record_path),
        },
        "gateway": {
            "mode": "local_loopback_openclaw_channel_gateway",
            "bind_host": bind_host,
            "port": port,
            "server_command": "ai22b-talent-foundry run-openclaw-channel-gateway-server",
            "http_paths": {
                "health": "/health",
                "config": "/openclaw/gateway-config",
                "message": "/openclaw/channel-message",
                "platform_event": "/openclaw/platform-event/{channel}",
            },
        },
        "allowed_channels": [
            {
                "channel_id": channel["channel_id"],
                "surface_id": f"openclaw-channel-{channel['channel_id']}",
                "label": channel["label"],
                "transport": channel["transport"],
            }
            for channel in resolved_channels
        ],
        "openclaw_channel_catalog": openclaw_channel_manifest(),
        "security": {
            "external_network_exposure": "disabled_by_default",
            "allowed_bind_hosts": ["127.0.0.1", "localhost"],
            "pairing_or_bot_token_storage": "not_stored_by_paideia_core",
            "channel_plugins": "must_translate_platform_events_to_openclaw_channel_message_schema",
            "private_training_files_sent_to_channel": False,
            "outbound_delivery": "return_envelope_by_default; platform plugins must explicitly send",
        },
        "message_contract": {
            "inbound_schema": OPENCLAW_CHANNEL_MESSAGE_SCHEMA,
            "outbound_schema": OPENCLAW_CHANNEL_RUN_SCHEMA,
            "core_behavior": "route channel message to Paideia memory-substrate chat and return a sendable reply envelope",
            "routing_policy": "reply_to_origin_channel; model_does_not_choose_channel",
        },
    }
    if output_path is not None:
        _write_json(output_path, config)
    return config


def _build_inbound_message(
    employment: dict[str, Any],
    *,
    channel: dict[str, Any],
    message: str,
    sender_id: str,
    conversation_id: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    message_id = _message_id(
        employment_id=employment["employment_id"],
        channel_id=channel["channel_id"],
        conversation_id=conversation_id,
        sender_id=sender_id,
        message=message,
    )
    return {
        "schema": OPENCLAW_CHANNEL_MESSAGE_SCHEMA,
        "message_id": message_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "channel": {
            "channel_id": channel["channel_id"],
            "surface_id": f"openclaw-channel-{channel['channel_id']}",
            "label": channel["label"],
            "transport": channel["transport"],
        },
        "conversation_id": conversation_id,
        "sender": {
            "sender_id": sender_id,
            "display_name": metadata.get("display_name") if metadata else None,
        },
        "message": {
            "text": message,
            "attachments": metadata.get("attachments", []) if metadata else [],
        },
        "policy": {
            "translated_from_external_platform": bool(metadata and metadata.get("external_platform_event")),
            "raw_external_payload_saved": False,
            "channel_plugin_may_send_outbound": True,
        },
        "metadata": metadata or {},
    }


def run_openclaw_channel_message(
    employment_record_path: Path,
    *,
    channel_id: str,
    message: str,
    sender_id: str = "local-user",
    conversation_id: str = "local-conversation",
    output_path: Path | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    learn_from_chat: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    employment = _load_employment(employment_record_path)
    channel = _channel_or_error(channel_id)
    inbound = _build_inbound_message(
        employment,
        channel=channel,
        message=message,
        sender_id=sender_id,
        conversation_id=conversation_id,
        metadata=metadata,
    )
    target_root = employment_record_path.parent
    output_path = output_path or target_root / "last_openclaw_channel_run.json"
    chat_turn_path = output_path.parent / f"{inbound['message_id']}_paideia_chat_turn.json"
    chat_turn = run_chat_turn_from_employment(
        employment_record_path,
        message=message,
        output_path=chat_turn_path,
        llm_mode=llm_mode,
        llm_model=llm_model,
        learn_from_chat=learn_from_chat,
    )
    answer = str(chat_turn.get("assistant_answer") or chat_turn.get("assistant_reply") or chat_turn.get("reply") or "")
    run = {
        "schema": OPENCLAW_CHANNEL_RUN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "reply_ready",
        "employment": {
            "employment_id": employment["employment_id"],
            "agent": employment["agent"],
        },
        "inbound": inbound,
        "paideia_chat_turn": {
            "path": str(chat_turn_path),
            "schema": chat_turn.get("schema"),
            "reply_generation_mode": chat_turn.get("reply_generation_mode"),
            "conversation_intent": chat_turn.get("conversation_intent"),
            "learning_decision": chat_turn.get("chat_learning_update", {}).get("decision"),
        },
        "outbound": {
            "schema": "ai22b-openclaw-channel-outbound-message/v1",
            "channel_id": channel["channel_id"],
            "conversation_id": conversation_id,
            "reply_to_message_id": inbound["message_id"],
            "text": answer,
            "format": "plain_text",
            "attachments": [],
            "send_policy": "return_to_gateway_plugin_not_sent_by_paideia_core",
        },
        "security": {
            "external_send_performed_by_core": False,
            "private_training_files_sent_to_channel": False,
            "raw_external_payload_saved": False,
        },
    }
    _write_json(output_path, run)
    _append_jsonl(target_root / "openclaw_channel_gateway_log.jsonl", run)
    return run
