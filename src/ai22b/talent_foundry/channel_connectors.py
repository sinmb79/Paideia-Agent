from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.openclaw_compat import OPENCLAW_CHANNELS, find_openclaw_channel, openclaw_channel_manifest


OPENCLAW_CHANNEL_CONNECTOR_CATALOG_SCHEMA = "ai22b-openclaw-channel-connector-catalog/v1"
OPENCLAW_CHANNEL_CONNECTOR_DOCTOR_SCHEMA = "ai22b-openclaw-channel-connector-doctor/v1"


CHANNEL_CONNECTOR_OVERRIDES: dict[str, dict[str, Any]] = {
    "bluebubbles": {
        "connector_status": "legacy_openclaw_config_migration_required",
        "ingress": "migrate_to_imessage_imsg_then_normalized_gateway",
        "delivery": "migrate_to_imessage_imsg",
        "required_env_vars": [],
        "setup": "Current OpenClaw removed BlueBubbles support. Migrate old channels.bluebubbles settings to channels.imessage, verify imsg on the Messages Mac, then use the imessage bridge.",
    },
    "clickclack": {
        "connector_status": "external_plugin_required",
        "ingress": "clickclack_bot_event_to_normalized_gateway",
        "delivery": "clickclack_bot_token_plugin",
        "required_env_vars": ["CLICKCLACK_BOT_TOKEN"],
        "setup": "Configure the ClickClack bot-token channel plugin, then bridge allowlisted conversations through the Paideia gateway.",
    },
    "discord": {
        "connector_status": "paideia_direct_ingress_delivery_ready",
        "ingress": "raw_MESSAGE_CREATE_or_normalized_gateway",
        "delivery": "discord_webhook_or_bot_message",
        "required_env_vars": ["DISCORD_WEBHOOK_URL or DISCORD_BOT_TOKEN"],
        "setup": "Create a Discord app/bot or webhook, then allowlist channel/user ids.",
    },
    "slack": {
        "connector_status": "paideia_direct_ingress_delivery_ready",
        "ingress": "slack_events_api_message_or_normalized_gateway",
        "delivery": "slack_chat_post_message",
        "required_env_vars": ["SLACK_BOT_TOKEN"],
        "setup": "Create a Slack app, subscribe to message events, and allowlist channels/users.",
    },
    "telegram": {
        "connector_status": "paideia_direct_ingress_delivery_ready",
        "ingress": "telegram_update_or_normalized_gateway",
        "delivery": "telegram_send_message",
        "required_env_vars": ["TELEGRAM_BOT_TOKEN"],
        "setup": "Create a bot with BotFather, configure webhook/getUpdates bridge, and allowlist chats/users.",
    },
    "webchat": {
        "connector_status": "paideia_loopback_ready",
        "ingress": "local_webchat_http",
        "delivery": "local_browser_response",
        "required_env_vars": [],
        "setup": "Run run-openclaw-webchat-server on 127.0.0.1.",
    },
    "whatsapp": {
        "connector_status": "external_plugin_required_qr_pairing",
        "ingress": "normalized_gateway_after_baileys_plugin",
        "delivery": "external_whatsapp_plugin",
        "required_env_vars": ["WHATSAPP_SESSION_DIR"],
        "setup": "Install/configure a Baileys-compatible plugin, complete QR pairing, then post normalized events to Paideia.",
    },
    "signal": {
        "connector_status": "local_bridge_required",
        "ingress": "normalized_gateway_after_signal_cli_bridge",
        "delivery": "signal_cli_bridge",
        "required_env_vars": ["SIGNAL_CLI_PATH", "SIGNAL_PHONE_NUMBER"],
        "setup": "Install signal-cli, register/link a number, and bridge events to the Paideia gateway.",
    },
    "matrix": {
        "connector_status": "external_plugin_required",
        "ingress": "normalized_gateway_after_matrix_plugin",
        "delivery": "matrix_plugin",
        "required_env_vars": ["MATRIX_HOMESERVER_URL", "MATRIX_ACCESS_TOKEN", "MATRIX_USER_ID"],
        "setup": "Configure a Matrix bot account and room allowlist, then bridge events through the gateway.",
    },
    "microsoft-teams": {
        "connector_status": "external_plugin_required_enterprise",
        "ingress": "normalized_gateway_after_bot_framework",
        "delivery": "bot_framework_plugin",
        "required_env_vars": ["MICROSOFT_APP_ID", "MICROSOFT_APP_PASSWORD"],
        "setup": "Configure Bot Framework credentials and tenant/channel allowlists.",
    },
    "google-chat": {
        "connector_status": "external_plugin_required",
        "ingress": "google_chat_http_event_to_normalized_gateway",
        "delivery": "google_chat_webhook_or_api_plugin",
        "required_env_vars": ["GOOGLE_CHAT_WEBHOOK_URL"],
        "setup": "Configure a Google Chat app or webhook and map spaces to allowlisted conversations.",
    },
    "imessage": {
        "connector_status": "openclaw_bundled_imsg_bridge_required",
        "ingress": "normalized_gateway_after_imsg_json_rpc_bridge",
        "delivery": "imsg_json_rpc_bridge",
        "required_env_vars": ["IMSG_CLI_PATH", "IMSG_REMOTE_HOST"],
        "setup": "Install and verify imsg on the Mac where Messages.app is signed in, enable channels.imessage, run openclaw channels status --probe --channel imessage, then allowlist chats.",
    },
    "irc": {
        "connector_status": "local_bridge_required",
        "ingress": "normalized_gateway_after_irc_bridge",
        "delivery": "irc_bridge",
        "required_env_vars": ["IRC_SERVER", "IRC_NICK"],
        "setup": "Connect an IRC bridge and map channels/DMs to Paideia conversation ids.",
    },
    "line": {
        "connector_status": "external_plugin_required",
        "ingress": "line_webhook_to_normalized_gateway",
        "delivery": "line_messaging_api_plugin",
        "required_env_vars": ["LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET"],
        "setup": "Configure LINE Messaging API webhook and allowlist user/group ids.",
    },
    "mattermost": {
        "connector_status": "external_plugin_required",
        "ingress": "normalized_gateway_after_mattermost_plugin",
        "delivery": "mattermost_bot_api",
        "required_env_vars": ["MATTERMOST_URL", "MATTERMOST_BOT_TOKEN"],
        "setup": "Create a Mattermost bot account and channel allowlist.",
    },
    "nextcloud-talk": {
        "connector_status": "external_plugin_required",
        "ingress": "normalized_gateway_after_nextcloud_talk_plugin",
        "delivery": "nextcloud_talk_plugin",
        "required_env_vars": ["NEXTCLOUD_BASE_URL", "NEXTCLOUD_TALK_TOKEN"],
        "setup": "Configure Nextcloud Talk credentials and room allowlists.",
    },
    "nostr": {
        "connector_status": "external_plugin_required",
        "ingress": "normalized_gateway_after_nostr_plugin",
        "delivery": "nostr_dm_plugin",
        "required_env_vars": ["NOSTR_PRIVATE_KEY", "NOSTR_RELAYS"],
        "setup": "Configure Nostr relay/private key handling outside Paideia artifacts.",
    },
    "qa-channel": {
        "connector_status": "openclaw_synthetic_qa_plugin_required",
        "ingress": "qa_channel_scenario_event_to_normalized_gateway",
        "delivery": "qa_channel_scenario_capture",
        "required_env_vars": [],
        "setup": "Use OpenClaw's QA channel scenarios for deterministic channel behavior tests; no real external chat is contacted.",
    },
    "qq-bot": {
        "connector_status": "external_plugin_required",
        "ingress": "qq_bot_webhook_to_normalized_gateway",
        "delivery": "qq_bot_api_plugin",
        "required_env_vars": ["QQ_BOT_APP_ID", "QQ_BOT_TOKEN"],
        "setup": "Configure QQ bot credentials and private/group allowlists.",
    },
    "sms": {
        "connector_status": "external_plugin_required",
        "ingress": "twilio_webhook_to_normalized_gateway",
        "delivery": "twilio_sms_plugin",
        "required_env_vars": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
        "setup": "Configure Twilio webhook and phone-number allowlists.",
    },
    "synology-chat": {
        "connector_status": "external_plugin_required",
        "ingress": "synology_outgoing_webhook_to_normalized_gateway",
        "delivery": "synology_incoming_webhook",
        "required_env_vars": ["SYNOLOGY_CHAT_WEBHOOK_URL"],
        "setup": "Configure Synology outgoing and incoming webhooks.",
    },
    "tlon": {
        "connector_status": "external_plugin_required",
        "ingress": "normalized_gateway_after_tlon_plugin",
        "delivery": "tlon_plugin",
        "required_env_vars": ["TLON_SHIP", "TLON_CODE"],
        "setup": "Configure Tlon/Urbit bridge and allowlisted peers.",
    },
    "twitch": {
        "connector_status": "local_bridge_required",
        "ingress": "twitch_irc_to_normalized_gateway",
        "delivery": "twitch_irc_bridge",
        "required_env_vars": ["TWITCH_BOT_TOKEN", "TWITCH_CHANNEL"],
        "setup": "Configure Twitch IRC credentials and channel allowlist.",
    },
    "voice-call": {
        "connector_status": "external_plugin_required",
        "ingress": "telephony_webhook_to_normalized_gateway",
        "delivery": "plivo_or_twilio_voice_plugin",
        "required_env_vars": ["TWILIO_ACCOUNT_SID or PLIVO_AUTH_ID"],
        "setup": "Configure telephony webhook, caller allowlist, and voice/TTS policy.",
    },
    "wechat": {
        "connector_status": "external_plugin_required_qr_pairing",
        "ingress": "normalized_gateway_after_wechat_plugin",
        "delivery": "wechat_ilink_plugin",
        "required_env_vars": ["WECHAT_SESSION_DIR"],
        "setup": "Configure Tencent iLink/QR flow and allowlisted private chats.",
    },
    "yuanbao": {
        "connector_status": "external_plugin_required",
        "ingress": "normalized_gateway_after_yuanbao_plugin",
        "delivery": "yuanbao_plugin",
        "required_env_vars": ["YUANBAO_TOKEN"],
        "setup": "Configure Yuanbao plugin credentials and conversation allowlists.",
    },
    "zalo": {
        "connector_status": "external_plugin_required",
        "ingress": "zalo_webhook_to_normalized_gateway",
        "delivery": "zalo_bot_api_plugin",
        "required_env_vars": ["ZALO_ACCESS_TOKEN"],
        "setup": "Configure Zalo Bot API webhook and allowlists.",
    },
    "zalo-personal": {
        "connector_status": "external_plugin_required_qr_pairing",
        "ingress": "normalized_gateway_after_zalo_personal_plugin",
        "delivery": "zalo_personal_plugin",
        "required_env_vars": ["ZALO_PERSONAL_SESSION_DIR"],
        "setup": "Complete QR login in a separate plugin and expose only allowlisted chats.",
    },
    "feishu": {
        "connector_status": "external_plugin_required",
        "ingress": "feishu_websocket_to_normalized_gateway",
        "delivery": "feishu_lark_bot_plugin",
        "required_env_vars": ["FEISHU_APP_ID", "FEISHU_APP_SECRET"],
        "setup": "Configure Feishu/Lark bot credentials and group allowlists.",
    },
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _connector_entry(channel: dict[str, Any]) -> dict[str, Any]:
    channel_id = channel["channel_id"]
    override = CHANNEL_CONNECTOR_OVERRIDES.get(channel_id, {})
    connector_status = override.get("connector_status", "external_plugin_required")
    generic_gateway_ready = True
    return {
        "channel_id": channel_id,
        "label": channel["label"],
        "transport": channel["transport"],
        "connector_status": connector_status,
        "generic_normalized_gateway_ready": generic_gateway_ready,
        "direct_raw_ingress_ready": connector_status in {
            "paideia_direct_ingress_delivery_ready",
            "paideia_loopback_ready",
        },
        "direct_delivery_ready": connector_status in {
            "paideia_direct_ingress_delivery_ready",
            "paideia_loopback_ready",
        },
        "ingress": override.get("ingress", "normalized_gateway_after_external_plugin"),
        "delivery": override.get("delivery", "external_plugin_delivery"),
        "required_env_vars": override.get("required_env_vars", []),
        "setup": override.get("setup", "Configure an OpenClaw-compatible channel plugin and post normalized messages to Paideia."),
    }


def build_openclaw_channel_connector_catalog(
    *,
    channels: list[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    selected = channels or [channel["channel_id"] for channel in OPENCLAW_CHANNELS]
    entries = []
    for channel_id in selected:
        channel = find_openclaw_channel(channel_id)
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel: {channel_id}")
        entries.append(_connector_entry(channel))
    catalog = {
        "schema": OPENCLAW_CHANNEL_CONNECTOR_CATALOG_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_channel_manifest": openclaw_channel_manifest(),
        "channels": entries,
        "summary": {
            "channel_count": len(entries),
            "direct_raw_ingress_ready_count": sum(1 for item in entries if item["direct_raw_ingress_ready"]),
            "direct_delivery_ready_count": sum(1 for item in entries if item["direct_delivery_ready"]),
            "generic_normalized_gateway_ready_count": sum(1 for item in entries if item["generic_normalized_gateway_ready"]),
        },
        "policy": {
            "raw_platform_events": "direct adapters only where implemented; all channels can use normalized gateway envelopes",
            "live_delivery": "explicit opt-in only; secrets are read from environment and not written to artifacts",
            "allowlist": "inbound platform events require access config before routing",
        },
    }
    if output_path is not None:
        _write_json(output_path, catalog)
    return catalog


def doctor_openclaw_channel_connectors(
    *,
    channels: list[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    catalog = build_openclaw_channel_connector_catalog(channels=channels)
    results = []
    for channel in catalog["channels"]:
        checks = []
        for env_var in channel["required_env_vars"]:
            alternatives = [part.strip() for part in env_var.split(" or ")]
            present = any(os.environ.get(part) for part in alternatives)
            checks.append(
                {
                    "id": f"env:{env_var}",
                    "kind": "environment_secret_or_path",
                    "passed": present,
                    "secret_value_stored": False,
                    "message": "configured" if present else f"{env_var} is not set in this shell.",
                }
            )
        ready_for_live = bool(channel["direct_delivery_ready"]) and all(check["passed"] for check in checks)
        if channel["channel_id"] == "webchat":
            ready_for_live = True
        results.append(
            {
                "channel_id": channel["channel_id"],
                "connector_status": channel["connector_status"],
                "generic_normalized_gateway_ready": channel["generic_normalized_gateway_ready"],
                "direct_raw_ingress_ready": channel["direct_raw_ingress_ready"],
                "direct_delivery_ready": channel["direct_delivery_ready"],
                "ready_for_live_delivery": ready_for_live,
                "checks": checks,
                "next_step": channel["setup"],
            }
        )
    doctor = {
        "schema": OPENCLAW_CHANNEL_CONNECTOR_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": {
            "channel_count": len(results),
            "ready_for_normalized_gateway_count": sum(1 for item in results if item["generic_normalized_gateway_ready"]),
            "ready_for_live_delivery_count": sum(1 for item in results if item["ready_for_live_delivery"]),
            "needs_plugin_or_bridge_count": sum(
                1
                for item in results
                if item["connector_status"] not in {"paideia_direct_ingress_delivery_ready", "paideia_loopback_ready"}
            ),
        },
        "secret_values_stored": False,
    }
    if output_path is not None:
        _write_json(output_path, doctor)
    return doctor
