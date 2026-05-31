from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.channel_gateway import OPENCLAW_CHANNEL_MESSAGE_SCHEMA
from ai22b.talent_foundry.openclaw_compat import resolve_openclaw_channel


OPENCLAW_CHANNEL_ACCESS_CONFIG_SCHEMA = "ai22b-openclaw-channel-access-config/v1"
OPENCLAW_PLATFORM_EVENT_TRANSLATION_SCHEMA = "ai22b-openclaw-platform-event-translation/v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_openclaw_channel_access_config(
    *,
    channels: list[str] | None = None,
    allowed_senders: list[str] | None = None,
    allowed_conversations: list[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    selected_channels = channels or ["telegram", "discord", "slack"]
    resolved_channels = []
    for channel_id in selected_channels:
        channel = resolve_openclaw_channel(channel_id)
        resolved_channels.append(channel["channel_id"])
    config = {
        "schema": OPENCLAW_CHANNEL_ACCESS_CONFIG_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "default_policy": "deny_unlisted",
        "allowed_channel_ids": sorted(set(resolved_channels)),
        "allowed_sender_ids": sorted(set(allowed_senders or [])),
        "allowed_conversation_ids": sorted(set(allowed_conversations or [])),
        "raw_external_payload_policy": "do_not_store",
        "pairing_status": "owner_review_required_before_live_use",
        "security": {
            "secret_values_stored": False,
            "private_training_files_ingested": False,
            "unlisted_sender_policy": "block",
            "unlisted_conversation_policy": "block",
        },
    }
    if output_path is not None:
        _write_json(output_path, config)
    return config


def _message_text(message: dict[str, Any]) -> str:
    value = message.get("text") or message.get("caption") or message.get("content") or ""
    return str(value).strip()


def _telegram_chat_kind(chat: dict[str, Any]) -> str:
    chat_type = str(chat.get("type") or "").casefold()
    if chat_type in {"group", "supergroup"}:
        return "group"
    if chat_type == "channel":
        return "channel"
    return "user"


def _telegram_event(payload: dict[str, Any]) -> dict[str, Any]:
    message = (
        payload.get("message")
        or payload.get("edited_message")
        or payload.get("channel_post")
        or payload.get("edited_channel_post")
        or {}
    )
    if not isinstance(message, dict):
        message = {}
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    chat_id = str(chat.get("id") or "")
    sender_id = str(sender.get("id") or chat_id or "unknown")
    kind = _telegram_chat_kind(chat)
    conversation_id = f"agent:main:telegram:{kind}:{chat_id}" if chat_id else "agent:main:telegram:unknown"
    if message.get("message_thread_id") is not None:
        conversation_id += f":topic:{message['message_thread_id']}"
    attachments = []
    for key in ["photo", "document", "video", "voice", "audio"]:
        if key in message:
            attachments.append({"type": key, "present": True})
    return {
        "channel_id": "telegram",
        "conversation_id": conversation_id,
        "sender_id": f"telegram:{sender_id}",
        "text": _message_text(message),
        "attachments": attachments,
        "metadata": {
            "platform_event_type": next((key for key in ["message", "edited_message", "channel_post", "edited_channel_post"] if key in payload), None),
            "telegram_update_id": payload.get("update_id"),
            "telegram_message_id": message.get("message_id"),
            "chat_type": chat.get("type"),
            "display_name": sender.get("username") or sender.get("first_name") or chat.get("title"),
        },
    }


def _discord_event(payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("d") if isinstance(payload.get("d"), dict) else payload
    author = event.get("author") if isinstance(event.get("author"), dict) else {}
    channel_id = str(event.get("channel_id") or "")
    thread_id = str(event.get("thread_id") or event.get("thread") or "")
    conversation_id = f"agent:main:discord:channel:{channel_id}" if channel_id else "agent:main:discord:unknown"
    if thread_id:
        conversation_id += f":thread:{thread_id}"
    attachments = [
        {
            "id": str(item.get("id") or ""),
            "filename": item.get("filename"),
            "content_type": item.get("content_type"),
        }
        for item in event.get("attachments", [])
        if isinstance(item, dict)
    ]
    return {
        "channel_id": "discord",
        "conversation_id": conversation_id,
        "sender_id": f"discord:{author.get('id') or 'unknown'}",
        "text": _message_text(event),
        "attachments": attachments,
        "metadata": {
            "platform_event_type": payload.get("t") or "MESSAGE_CREATE",
            "discord_message_id": event.get("id"),
            "guild_id": event.get("guild_id"),
            "display_name": author.get("username") or author.get("global_name"),
            "message_content_intent_required": not bool(event.get("content")),
        },
    }


def _slack_event(payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    channel = str(event.get("channel") or "")
    thread_ts = str(event.get("thread_ts") or event.get("ts") or "")
    conversation_id = f"agent:main:slack:channel:{channel}" if channel else "agent:main:slack:unknown"
    if thread_ts:
        conversation_id += f":thread:{thread_ts}"
    sender = str(event.get("user") or event.get("bot_id") or "unknown")
    return {
        "channel_id": "slack",
        "conversation_id": conversation_id,
        "sender_id": f"slack:{sender}",
        "text": _message_text(event),
        "attachments": [],
        "metadata": {
            "platform_event_type": payload.get("type") or event.get("type"),
            "slack_team_id": payload.get("team_id"),
            "slack_event_id": payload.get("event_id"),
            "slack_ts": event.get("ts"),
            "display_name": sender,
            "url_verification_challenge_present": bool(payload.get("challenge")),
        },
    }


def _google_chat_event(payload: dict[str, Any]) -> dict[str, Any]:
    message = payload.get("message") if isinstance(payload.get("message"), dict) else payload
    space = payload.get("space") if isinstance(payload.get("space"), dict) else message.get("space", {})
    sender = payload.get("user") if isinstance(payload.get("user"), dict) else message.get("sender", {})
    space_id = str(space.get("name") or message.get("space", {}).get("name") or "unknown").replace(":", "_")
    thread = message.get("thread") if isinstance(message.get("thread"), dict) else {}
    conversation_id = f"agent:main:google-chat:space:{space_id}"
    if thread.get("name"):
        conversation_id += f":thread:{str(thread['name']).replace(':', '_')}"
    sender_id = str(sender.get("name") or sender.get("email") or "unknown")
    return {
        "channel_id": "google-chat",
        "conversation_id": conversation_id,
        "sender_id": f"google-chat:{sender_id}",
        "text": _message_text(message),
        "attachments": [],
        "metadata": {
            "platform_event_type": payload.get("type") or "MESSAGE",
            "google_chat_message_name": message.get("name"),
            "space_name": space.get("name"),
            "display_name": sender.get("displayName") or sender.get("name"),
        },
    }


def _line_event(payload: dict[str, Any]) -> dict[str, Any]:
    events = payload.get("events") if isinstance(payload.get("events"), list) else [payload]
    event = next((item for item in events if isinstance(item, dict)), {})
    source = event.get("source") if isinstance(event.get("source"), dict) else {}
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    source_type = str(source.get("type") or "user")
    target = str(source.get("groupId") or source.get("roomId") or source.get("userId") or "unknown")
    sender = str(source.get("userId") or target)
    return {
        "channel_id": "line",
        "conversation_id": f"agent:main:line:{source_type}:{target}",
        "sender_id": f"line:{sender}",
        "text": _message_text(message),
        "attachments": [{"type": message.get("type"), "present": True}] if message.get("type") != "text" else [],
        "metadata": {
            "platform_event_type": event.get("type"),
            "line_reply_token_present": bool(event.get("replyToken")),
            "display_name": sender,
        },
    }


def _matrix_event(payload: dict[str, Any]) -> dict[str, Any]:
    content = payload.get("content") if isinstance(payload.get("content"), dict) else payload
    room_id = str(payload.get("room_id") or payload.get("roomId") or "unknown")
    sender = str(payload.get("sender") or "unknown")
    return {
        "channel_id": "matrix",
        "conversation_id": f"agent:main:matrix:room:{room_id}",
        "sender_id": f"matrix:{sender}",
        "text": str(content.get("body") or content.get("text") or ""),
        "attachments": [],
        "metadata": {
            "platform_event_type": payload.get("type") or content.get("msgtype"),
            "matrix_event_id": payload.get("event_id"),
            "display_name": sender,
        },
    }


def _mattermost_event(payload: dict[str, Any]) -> dict[str, Any]:
    channel_id = str(payload.get("channel_id") or payload.get("channelId") or "unknown")
    user_id = str(payload.get("user_id") or payload.get("userId") or payload.get("user_name") or "unknown")
    return {
        "channel_id": "mattermost",
        "conversation_id": f"agent:main:mattermost:channel:{channel_id}",
        "sender_id": f"mattermost:{user_id}",
        "text": _message_text(payload),
        "attachments": [],
        "metadata": {
            "platform_event_type": payload.get("trigger_word") or "message",
            "mattermost_post_id": payload.get("post_id"),
            "display_name": payload.get("user_name") or user_id,
        },
    }


def _sms_event(payload: dict[str, Any]) -> dict[str, Any]:
    from_number = str(payload.get("From") or payload.get("from") or "unknown")
    to_number = str(payload.get("To") or payload.get("to") or "unknown")
    return {
        "channel_id": "sms",
        "conversation_id": f"agent:main:sms:phone:{from_number}",
        "sender_id": f"sms:{from_number}",
        "text": str(payload.get("Body") or payload.get("body") or ""),
        "attachments": [],
        "metadata": {
            "platform_event_type": "twilio_sms_webhook",
            "sms_to": to_number,
            "sms_message_sid": payload.get("MessageSid") or payload.get("SmsMessageSid"),
            "display_name": from_number,
        },
    }


def _synology_chat_event(payload: dict[str, Any]) -> dict[str, Any]:
    channel_id = str(payload.get("channel_id") or payload.get("channelId") or payload.get("token") or "unknown")
    sender = str(payload.get("user_id") or payload.get("username") or payload.get("user_name") or "unknown")
    return {
        "channel_id": "synology-chat",
        "conversation_id": f"agent:main:synology-chat:channel:{channel_id}",
        "sender_id": f"synology-chat:{sender}",
        "text": _message_text(payload),
        "attachments": [],
        "metadata": {
            "platform_event_type": "synology_outgoing_webhook",
            "display_name": payload.get("username") or payload.get("user_name") or sender,
        },
    }


def _envelope_from_parts(parts: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": OPENCLAW_CHANNEL_MESSAGE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "channel": {
            "channel_id": parts["channel_id"],
            "surface_id": f"openclaw-channel-{parts['channel_id']}",
        },
        "conversation_id": parts["conversation_id"],
        "sender": {
            "sender_id": parts["sender_id"],
            "display_name": parts["metadata"].get("display_name"),
        },
        "message": {
            "text": parts["text"],
            "attachments": parts["attachments"],
        },
        "policy": {
            "translated_from_external_platform": True,
            "raw_external_payload_saved": False,
            "channel_plugin_may_send_outbound": False,
        },
        "metadata": {
            **parts["metadata"],
            "external_platform_event": True,
            "raw_external_payload_saved": False,
        },
    }


def evaluate_channel_access(channel_message: dict[str, Any], access_config: dict[str, Any] | None) -> dict[str, Any]:
    if access_config is None:
        return {
            "allowed": False,
            "decision": "review_required_no_access_config",
            "reason": "No channel access config was provided.",
        }
    if access_config.get("schema") != OPENCLAW_CHANNEL_ACCESS_CONFIG_SCHEMA:
        raise ValueError("Unsupported channel access config schema")
    channel_id = str(channel_message.get("channel", {}).get("channel_id") or "")
    sender_id = str(channel_message.get("sender", {}).get("sender_id") or "")
    conversation_id = str(channel_message.get("conversation_id") or "")
    allowed_channels = set(access_config.get("allowed_channel_ids") or [])
    allowed_senders = set(access_config.get("allowed_sender_ids") or [])
    allowed_conversations = set(access_config.get("allowed_conversation_ids") or [])
    if allowed_channels and channel_id not in allowed_channels:
        return {"allowed": False, "decision": "blocked_channel_not_allowed", "reason": channel_id}
    if not allowed_senders and not allowed_conversations:
        return {
            "allowed": False,
            "decision": "review_required_empty_sender_and_conversation_allowlists",
            "reason": "Add an allowed sender or conversation before routing live channel events.",
        }
    if sender_id in allowed_senders or conversation_id in allowed_conversations:
        return {"allowed": True, "decision": "allowed", "reason": "sender_or_conversation_allowlisted"}
    return {
        "allowed": False,
        "decision": "blocked_sender_or_conversation_not_allowed",
        "reason": f"{sender_id}|{conversation_id}",
    }


def translate_openclaw_platform_event(
    *,
    channel_id: str,
    payload: dict[str, Any],
    access_config: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    channel = resolve_openclaw_channel(channel_id)
    normalized_channel_id = channel["channel_id"]
    if normalized_channel_id == "telegram":
        parts = _telegram_event(payload)
    elif normalized_channel_id == "discord":
        parts = _discord_event(payload)
    elif normalized_channel_id == "slack":
        parts = _slack_event(payload)
    elif normalized_channel_id == "google-chat":
        parts = _google_chat_event(payload)
    elif normalized_channel_id == "line":
        parts = _line_event(payload)
    elif normalized_channel_id == "matrix":
        parts = _matrix_event(payload)
    elif normalized_channel_id == "mattermost":
        parts = _mattermost_event(payload)
    elif normalized_channel_id == "sms":
        parts = _sms_event(payload)
    elif normalized_channel_id == "synology-chat":
        parts = _synology_chat_event(payload)
    else:
        raise ValueError(f"Platform ingress adapter is not implemented for channel: {normalized_channel_id}")
    channel_message = _envelope_from_parts(parts)
    access = evaluate_channel_access(channel_message, access_config)
    channel_message["policy"]["channel_plugin_may_send_outbound"] = bool(access["allowed"])
    result = {
        "schema": OPENCLAW_PLATFORM_EVENT_TRANSLATION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "translated",
        "channel_id": normalized_channel_id,
        "channel_message": channel_message,
        "access": access,
        "security": {
            "raw_external_payload_saved": False,
            "secret_values_stored": False,
            "private_training_files_ingested": False,
        },
    }
    if output_path is not None:
        _write_json(output_path, result)
    return result
