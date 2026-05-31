from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENCLAW_CHANNEL_DELIVERY_CONFIG_SCHEMA = "ai22b-openclaw-channel-delivery-config/v1"
OPENCLAW_CHANNEL_DELIVERY_RUN_SCHEMA = "ai22b-openclaw-channel-delivery-run/v1"

SUPPORTED_DELIVERY_CHANNELS = {
    "telegram": {
        "adapter": "telegram_bot_api_send_message",
        "token_env_var": "TELEGRAM_BOT_TOKEN",
        "target_required": "chat_id",
        "official_reference": "https://core.telegram.org/bots/api#sendmessage",
    },
    "discord": {
        "adapter": "discord_webhook_or_bot_message",
        "token_env_var": "DISCORD_BOT_TOKEN",
        "webhook_url_env_var": "DISCORD_WEBHOOK_URL",
        "target_required": "channel_id_or_webhook_url",
        "official_reference": "https://discord.com/developers/docs/resources/webhook#execute-webhook",
    },
    "slack": {
        "adapter": "slack_chat_post_message",
        "token_env_var": "SLACK_BOT_TOKEN",
        "target_required": "channel",
        "official_reference": "https://api.slack.com/methods/chat.postMessage",
    },
    "google-chat": {
        "adapter": "google_chat_webhook_message",
        "webhook_url_env_var": "GOOGLE_CHAT_WEBHOOK_URL",
        "target_required": "space_webhook_url",
        "official_reference": "https://developers.google.com/workspace/chat/quickstart/webhooks",
    },
    "line": {
        "adapter": "line_messaging_api_push_message",
        "token_env_var": "LINE_CHANNEL_ACCESS_TOKEN",
        "target_required": "user_or_group_id",
        "official_reference": "https://developers.line.biz/en/reference/messaging-api/#send-push-message",
    },
    "matrix": {
        "adapter": "matrix_client_send_message",
        "token_env_var": "MATRIX_ACCESS_TOKEN",
        "base_url_env_var": "MATRIX_HOMESERVER_URL",
        "target_required": "room_id",
        "official_reference": "https://spec.matrix.org/latest/client-server-api/#put_matrixclientv3roomsroomidsendeventtypetxnid",
    },
    "mattermost": {
        "adapter": "mattermost_create_post",
        "token_env_var": "MATTERMOST_BOT_TOKEN",
        "base_url_env_var": "MATTERMOST_URL",
        "target_required": "channel_id",
        "official_reference": "https://api.mattermost.com/#tag/posts/operation/CreatePost",
    },
    "sms": {
        "adapter": "twilio_sms_message",
        "token_env_var": "TWILIO_AUTH_TOKEN",
        "account_sid_env_var": "TWILIO_ACCOUNT_SID",
        "from_number_env_var": "TWILIO_FROM_NUMBER",
        "target_required": "phone_number",
        "official_reference": "https://www.twilio.com/docs/messaging/api/message-resource#create-a-message-resource",
    },
    "synology-chat": {
        "adapter": "synology_chat_incoming_webhook",
        "webhook_url_env_var": "SYNOLOGY_CHAT_WEBHOOK_URL",
        "target_required": "incoming_webhook_url",
        "official_reference": "https://kb.synology.com/en-global/DSM/help/Chat/chat_integration",
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _request_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 60,
    method: str = "POST",
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        status_code = getattr(response, "status", None)
    if not raw:
        return {"ok": True, "http_status": status_code}
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed.setdefault("http_status", status_code)
        return parsed
    return {"ok": True, "http_status": status_code, "raw": parsed}


def _request_form(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 60,
) -> dict[str, Any]:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
        status_code = getattr(response, "status", None)
    if not raw:
        return {"ok": True, "http_status": status_code}
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed.setdefault("http_status", status_code)
        return parsed
    return {"ok": True, "http_status": status_code, "raw": parsed}


def _load_channel_run(channel_run: Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(channel_run, Path):
        return _read_json(channel_run)
    return channel_run


def _segments(conversation_id: str) -> list[str]:
    return [item for item in str(conversation_id).split(":") if item]


def _value_after(parts: list[str], key: str) -> str | None:
    try:
        index = parts.index(key)
    except ValueError:
        return None
    if index + 1 < len(parts):
        return parts[index + 1]
    return None


def _telegram_origin(conversation_id: str) -> dict[str, Any]:
    parts = _segments(conversation_id)
    return {
        "chat_id": _value_after(parts, "group")
        or _value_after(parts, "channel")
        or _value_after(parts, "user")
        or _value_after(parts, "chat"),
        "message_thread_id": _value_after(parts, "topic"),
    }


def _discord_origin(conversation_id: str) -> dict[str, Any]:
    parts = _segments(conversation_id)
    return {
        "channel_id": _value_after(parts, "channel")
        or _value_after(parts, "room")
        or _value_after(parts, "group")
        or _value_after(parts, "user"),
        "thread_id": _value_after(parts, "thread"),
    }


def _slack_origin(conversation_id: str) -> dict[str, Any]:
    parts = _segments(conversation_id)
    return {
        "channel": _value_after(parts, "channel")
        or _value_after(parts, "room")
        or _value_after(parts, "group")
        or _value_after(parts, "user"),
        "thread_ts": _value_after(parts, "thread"),
    }


def _generic_room_origin(conversation_id: str) -> dict[str, Any]:
    parts = _segments(conversation_id)
    return {
        "room_id": _value_after(parts, "room")
        or _value_after(parts, "channel")
        or _value_after(parts, "group")
        or _value_after(parts, "space")
        or _value_after(parts, "user")
        or _value_after(parts, "chat"),
        "thread_id": _value_after(parts, "thread")
        or _value_after(parts, "topic"),
    }


def _phone_origin(conversation_id: str) -> dict[str, Any]:
    parts = _segments(conversation_id)
    return {
        "phone_number": _value_after(parts, "phone")
        or _value_after(parts, "sms")
        or _value_after(parts, "user")
        or _value_after(parts, "chat"),
    }


def build_openclaw_channel_delivery_config(
    *,
    channels: list[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    selected_channels = channels or sorted(SUPPORTED_DELIVERY_CHANNELS)
    unsupported = [channel for channel in selected_channels if channel not in SUPPORTED_DELIVERY_CHANNELS]
    if unsupported:
        raise ValueError(f"Unsupported delivery channels: {', '.join(unsupported)}")
    config = {
        "schema": OPENCLAW_CHANNEL_DELIVERY_CONFIG_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "explicit_live_only",
        "default_mode": "dry-run",
        "channels": [
            {
                "channel_id": channel,
                **SUPPORTED_DELIVERY_CHANNELS[channel],
                "secret_storage": "environment_only_not_written_to_artifacts",
                "live_send_requires": "--mode live and required environment variables",
            }
            for channel in selected_channels
        ],
        "security": {
            "default_network_call_performed": False,
            "private_training_files_sent_to_channel": False,
            "secret_values_stored": False,
            "recommended_bind_host": "127.0.0.1",
        },
        "official_references": sorted(
            {SUPPORTED_DELIVERY_CHANNELS[channel]["official_reference"] for channel in selected_channels}
        ),
    }
    if output_path is not None:
        _write_json(output_path, config)
    return config


def _telegram_delivery(
    *,
    outbound: dict[str, Any],
    target_id: str | None,
    thread_id: str | None,
    token_env_var: str | None,
) -> dict[str, Any]:
    origin = _telegram_origin(str(outbound.get("conversation_id", "")))
    chat_id = target_id or origin.get("chat_id")
    message_thread_id = thread_id or origin.get("message_thread_id")
    token_env_var = token_env_var or SUPPORTED_DELIVERY_CHANNELS["telegram"]["token_env_var"]
    payload: dict[str, Any] = {"chat_id": chat_id, "text": outbound.get("text", "")}
    if message_thread_id:
        try:
            payload["message_thread_id"] = int(message_thread_id)
        except ValueError:
            payload["message_thread_id"] = message_thread_id
    token = os.environ.get(token_env_var)
    return {
        "adapter": SUPPORTED_DELIVERY_CHANNELS["telegram"]["adapter"],
        "endpoint": "https://api.telegram.org/bot<redacted>/sendMessage",
        "live_url": f"https://api.telegram.org/bot{token}/sendMessage" if token else None,
        "payload": payload,
        "headers": {},
        "auth": {"token_env_var": token_env_var, "token_present": bool(token)},
        "target_valid": bool(chat_id),
    }


def _discord_delivery(
    *,
    outbound: dict[str, Any],
    target_id: str | None,
    thread_id: str | None,
    token_env_var: str | None,
    webhook_url_env_var: str | None,
    delivery_method: str,
) -> dict[str, Any]:
    origin = _discord_origin(str(outbound.get("conversation_id", "")))
    channel_id = target_id or origin.get("channel_id")
    thread_id = thread_id or origin.get("thread_id")
    webhook_url_env_var = webhook_url_env_var or SUPPORTED_DELIVERY_CHANNELS["discord"]["webhook_url_env_var"]
    token_env_var = token_env_var or SUPPORTED_DELIVERY_CHANNELS["discord"]["token_env_var"]
    webhook_url = os.environ.get(webhook_url_env_var)
    use_webhook = delivery_method == "webhook" or (delivery_method == "auto" and bool(webhook_url))
    if use_webhook:
        url = webhook_url or ""
        query = {"wait": "true"}
        if thread_id:
            query["thread_id"] = str(thread_id)
        live_url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(query) if url else None
        return {
            "adapter": "discord_webhook_execute",
            "endpoint": "DISCORD_WEBHOOK_URL?wait=true",
            "live_url": live_url,
            "payload": {"content": outbound.get("text", "")},
            "headers": {},
            "auth": {"webhook_url_env_var": webhook_url_env_var, "webhook_url_present": bool(webhook_url)},
            "target_valid": bool(webhook_url),
        }
    send_channel_id = thread_id or channel_id
    live_url = f"https://discord.com/api/v10/channels/{send_channel_id}/messages" if send_channel_id else None
    return {
        "adapter": "discord_bot_channel_message",
        "endpoint": "https://discord.com/api/v10/channels/<channel_id>/messages",
        "live_url": live_url,
        "payload": {"content": outbound.get("text", "")},
        "headers": {"Authorization": f"Bot {os.environ.get(token_env_var)}"} if os.environ.get(token_env_var) else {},
        "auth": {"token_env_var": token_env_var, "token_present": bool(os.environ.get(token_env_var))},
        "target_valid": bool(send_channel_id),
    }


def _slack_delivery(
    *,
    outbound: dict[str, Any],
    target_id: str | None,
    thread_id: str | None,
    token_env_var: str | None,
) -> dict[str, Any]:
    origin = _slack_origin(str(outbound.get("conversation_id", "")))
    channel = target_id or origin.get("channel")
    thread_ts = thread_id or origin.get("thread_ts")
    token_env_var = token_env_var or SUPPORTED_DELIVERY_CHANNELS["slack"]["token_env_var"]
    payload: dict[str, Any] = {"channel": channel, "text": outbound.get("text", "")}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    token = os.environ.get(token_env_var)
    return {
        "adapter": SUPPORTED_DELIVERY_CHANNELS["slack"]["adapter"],
        "endpoint": "https://slack.com/api/chat.postMessage",
        "live_url": "https://slack.com/api/chat.postMessage",
        "payload": payload,
        "headers": {"Authorization": f"Bearer {token}"} if token else {},
        "auth": {"token_env_var": token_env_var, "token_present": bool(token)},
        "target_valid": bool(channel),
    }


def _google_chat_delivery(
    *,
    outbound: dict[str, Any],
    webhook_url_env_var: str | None,
) -> dict[str, Any]:
    webhook_url_env_var = webhook_url_env_var or SUPPORTED_DELIVERY_CHANNELS["google-chat"]["webhook_url_env_var"]
    webhook_url = os.environ.get(webhook_url_env_var)
    return {
        "adapter": SUPPORTED_DELIVERY_CHANNELS["google-chat"]["adapter"],
        "endpoint": "GOOGLE_CHAT_WEBHOOK_URL",
        "live_url": webhook_url,
        "payload": {"text": outbound.get("text", "")},
        "headers": {},
        "auth": {"webhook_url_env_var": webhook_url_env_var, "webhook_url_present": bool(webhook_url)},
        "target_valid": bool(webhook_url),
    }


def _synology_chat_delivery(
    *,
    outbound: dict[str, Any],
    webhook_url_env_var: str | None,
) -> dict[str, Any]:
    webhook_url_env_var = webhook_url_env_var or SUPPORTED_DELIVERY_CHANNELS["synology-chat"]["webhook_url_env_var"]
    webhook_url = os.environ.get(webhook_url_env_var)
    return {
        "adapter": SUPPORTED_DELIVERY_CHANNELS["synology-chat"]["adapter"],
        "endpoint": "SYNOLOGY_CHAT_WEBHOOK_URL",
        "live_url": webhook_url,
        "payload": {"text": outbound.get("text", "")},
        "headers": {},
        "auth": {"webhook_url_env_var": webhook_url_env_var, "webhook_url_present": bool(webhook_url)},
        "target_valid": bool(webhook_url),
    }


def _line_delivery(
    *,
    outbound: dict[str, Any],
    target_id: str | None,
    token_env_var: str | None,
) -> dict[str, Any]:
    origin = _generic_room_origin(str(outbound.get("conversation_id", "")))
    target = target_id or origin.get("room_id")
    token_env_var = token_env_var or SUPPORTED_DELIVERY_CHANNELS["line"]["token_env_var"]
    token = os.environ.get(token_env_var)
    return {
        "adapter": SUPPORTED_DELIVERY_CHANNELS["line"]["adapter"],
        "endpoint": "https://api.line.me/v2/bot/message/push",
        "live_url": "https://api.line.me/v2/bot/message/push",
        "payload": {
            "to": target,
            "messages": [{"type": "text", "text": str(outbound.get("text", ""))[:5000]}],
        },
        "headers": {"Authorization": f"Bearer {token}"} if token else {},
        "auth": {"token_env_var": token_env_var, "token_present": bool(token)},
        "target_valid": bool(target),
    }


def _matrix_delivery(
    *,
    outbound: dict[str, Any],
    target_id: str | None,
    token_env_var: str | None,
) -> dict[str, Any]:
    origin = _generic_room_origin(str(outbound.get("conversation_id", "")))
    room_id = target_id or origin.get("room_id")
    token_env_var = token_env_var or SUPPORTED_DELIVERY_CHANNELS["matrix"]["token_env_var"]
    base_url_env_var = SUPPORTED_DELIVERY_CHANNELS["matrix"]["base_url_env_var"]
    token = os.environ.get(token_env_var)
    base_url = (os.environ.get(base_url_env_var) or "").rstrip("/")
    txn_id = str(outbound.get("reply_to_message_id") or "paideia-message")
    encoded_room = urllib.parse.quote(str(room_id or ""), safe="")
    encoded_txn = urllib.parse.quote(txn_id, safe="")
    live_url = (
        f"{base_url}/_matrix/client/v3/rooms/{encoded_room}/send/m.room.message/{encoded_txn}"
        if base_url and room_id
        else None
    )
    return {
        "adapter": SUPPORTED_DELIVERY_CHANNELS["matrix"]["adapter"],
        "endpoint": f"{base_url_env_var}/_matrix/client/v3/rooms/<room_id>/send/m.room.message/<txn_id>",
        "live_url": live_url,
        "payload": {"msgtype": "m.text", "body": outbound.get("text", "")},
        "headers": {"Authorization": f"Bearer {token}"} if token else {},
        "auth": {
            "token_env_var": token_env_var,
            "token_present": bool(token),
            "base_url_env_var": base_url_env_var,
            "base_url_present": bool(base_url),
        },
        "target_valid": bool(room_id and base_url),
        "http_method": "PUT",
    }


def _mattermost_delivery(
    *,
    outbound: dict[str, Any],
    target_id: str | None,
    token_env_var: str | None,
) -> dict[str, Any]:
    origin = _generic_room_origin(str(outbound.get("conversation_id", "")))
    channel_id = target_id or origin.get("room_id")
    token_env_var = token_env_var or SUPPORTED_DELIVERY_CHANNELS["mattermost"]["token_env_var"]
    base_url_env_var = SUPPORTED_DELIVERY_CHANNELS["mattermost"]["base_url_env_var"]
    token = os.environ.get(token_env_var)
    base_url = (os.environ.get(base_url_env_var) or "").rstrip("/")
    live_url = f"{base_url}/api/v4/posts" if base_url else None
    return {
        "adapter": SUPPORTED_DELIVERY_CHANNELS["mattermost"]["adapter"],
        "endpoint": f"{base_url_env_var}/api/v4/posts",
        "live_url": live_url,
        "payload": {"channel_id": channel_id, "message": outbound.get("text", "")},
        "headers": {"Authorization": f"Bearer {token}"} if token else {},
        "auth": {
            "token_env_var": token_env_var,
            "token_present": bool(token),
            "base_url_env_var": base_url_env_var,
            "base_url_present": bool(base_url),
        },
        "target_valid": bool(channel_id and base_url),
    }


def _sms_delivery(
    *,
    outbound: dict[str, Any],
    target_id: str | None,
) -> dict[str, Any]:
    origin = _phone_origin(str(outbound.get("conversation_id", "")))
    to_number = target_id or origin.get("phone_number")
    config = SUPPORTED_DELIVERY_CHANNELS["sms"]
    sid_env_var = config["account_sid_env_var"]
    token_env_var = config["token_env_var"]
    from_env_var = config["from_number_env_var"]
    sid = os.environ.get(sid_env_var)
    token = os.environ.get(token_env_var)
    from_number = os.environ.get(from_env_var)
    auth_header = ""
    if sid and token:
        auth_header = "Basic " + base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("ascii")
    live_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json" if sid else None
    return {
        "adapter": config["adapter"],
        "endpoint": "https://api.twilio.com/2010-04-01/Accounts/<account_sid>/Messages.json",
        "live_url": live_url,
        "payload": {"To": to_number, "From": from_number, "Body": outbound.get("text", "")},
        "headers": {"Authorization": auth_header} if auth_header else {},
        "auth": {
            "account_sid_env_var": sid_env_var,
            "account_sid_present": bool(sid),
            "token_env_var": token_env_var,
            "token_present": bool(token),
            "from_number_env_var": from_env_var,
            "from_number_present": bool(from_number),
        },
        "target_valid": bool(to_number and from_number and sid),
        "request_format": "form",
    }


def _prepare_delivery(
    *,
    outbound: dict[str, Any],
    target_id: str | None,
    thread_id: str | None,
    token_env_var: str | None,
    webhook_url_env_var: str | None,
    delivery_method: str,
) -> dict[str, Any]:
    channel_id = str(outbound.get("channel_id") or "").strip()
    if channel_id == "telegram":
        return _telegram_delivery(outbound=outbound, target_id=target_id, thread_id=thread_id, token_env_var=token_env_var)
    if channel_id == "discord":
        return _discord_delivery(
            outbound=outbound,
            target_id=target_id,
            thread_id=thread_id,
            token_env_var=token_env_var,
            webhook_url_env_var=webhook_url_env_var,
            delivery_method=delivery_method,
        )
    if channel_id == "slack":
        return _slack_delivery(outbound=outbound, target_id=target_id, thread_id=thread_id, token_env_var=token_env_var)
    if channel_id == "google-chat":
        return _google_chat_delivery(outbound=outbound, webhook_url_env_var=webhook_url_env_var)
    if channel_id == "line":
        return _line_delivery(outbound=outbound, target_id=target_id, token_env_var=token_env_var)
    if channel_id == "matrix":
        return _matrix_delivery(outbound=outbound, target_id=target_id, token_env_var=token_env_var)
    if channel_id == "mattermost":
        return _mattermost_delivery(outbound=outbound, target_id=target_id, token_env_var=token_env_var)
    if channel_id == "sms":
        return _sms_delivery(outbound=outbound, target_id=target_id)
    if channel_id == "synology-chat":
        return _synology_chat_delivery(outbound=outbound, webhook_url_env_var=webhook_url_env_var)
    return {
        "adapter": "unsupported_channel_delivery_adapter",
        "endpoint": None,
        "live_url": None,
        "payload": {},
        "headers": {},
        "auth": {},
        "target_valid": False,
    }


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted = {}
    for key, value in headers.items():
        redacted[key] = "<redacted>" if value else value
    return redacted


def send_openclaw_channel_outbound(
    channel_run: Path | dict[str, Any],
    *,
    mode: str = "dry-run",
    target_id: str | None = None,
    thread_id: str | None = None,
    token_env_var: str | None = None,
    webhook_url_env_var: str | None = None,
    delivery_method: str = "auto",
    output_path: Path | None = None,
) -> dict[str, Any]:
    if mode not in {"dry-run", "live"}:
        raise ValueError("mode must be 'dry-run' or 'live'")
    if delivery_method not in {"auto", "webhook", "bot"}:
        raise ValueError("delivery_method must be auto, webhook, or bot")
    run = _load_channel_run(channel_run)
    outbound = run.get("outbound", {})
    channel_id = str(outbound.get("channel_id") or "").strip()
    prepared = _prepare_delivery(
        outbound=outbound,
        target_id=target_id,
        thread_id=thread_id,
        token_env_var=token_env_var,
        webhook_url_env_var=webhook_url_env_var,
        delivery_method=delivery_method,
    )
    required_auth_present = bool(
        prepared.get("auth", {}).get("token_present") or prepared.get("auth", {}).get("webhook_url_present")
    )
    can_send = channel_id in SUPPORTED_DELIVERY_CHANNELS and prepared["target_valid"] and required_auth_present
    status = "prepared_not_sent"
    provider_response: dict[str, Any] | None = None
    network_call_performed = False
    error: str | None = None
    if mode == "live":
        if not can_send:
            status = "not_sent_missing_target_or_auth"
        else:
            try:
                if prepared.get("request_format") == "form":
                    provider_response = _request_form(
                        url=str(prepared["live_url"] or prepared["endpoint"]),
                        payload=prepared["payload"],
                        headers=prepared["headers"],
                    )
                else:
                    http_method = str(prepared.get("http_method") or "POST")
                    if http_method == "POST":
                        provider_response = _request_json(
                            url=str(prepared["live_url"] or prepared["endpoint"]),
                            payload=prepared["payload"],
                            headers=prepared["headers"],
                        )
                    else:
                        provider_response = _request_json(
                            url=str(prepared["live_url"] or prepared["endpoint"]),
                            payload=prepared["payload"],
                            headers=prepared["headers"],
                            method=http_method,
                        )
                network_call_performed = True
                status = "sent" if provider_response.get("ok", True) else "provider_rejected"
            except Exception as exc:
                network_call_performed = True
                status = "send_failed"
                error = str(exc)[:800]
    result = {
        "schema": OPENCLAW_CHANNEL_DELIVERY_RUN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "status": status,
        "channel_id": channel_id,
        "delivery_method": delivery_method,
        "adapter": prepared["adapter"],
        "endpoint": prepared["endpoint"],
        "payload": prepared["payload"],
        "headers": _redact_headers(prepared["headers"]),
        "auth": prepared["auth"],
        "http_method": prepared.get("http_method", "POST"),
        "request_format": prepared.get("request_format", "json"),
        "target_valid": prepared["target_valid"],
        "network_call_performed": network_call_performed,
        "provider_response": provider_response,
        "error": error,
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
    if output_path is not None:
        _write_json(output_path, result)
    return result
