from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.openclaw_compat import (
    OPENCLAW_MANIFEST_ONLY_PROVIDERS,
    OPENCLAW_MODEL_PROVIDERS,
    find_openclaw_channel,
    find_openclaw_provider,
    openclaw_channel_manifest,
    openclaw_provider_manifest,
)


OPENCLAW_PARITY_AUDIT_SCHEMA = "ai22b-openclaw-parity-audit/v1"

OPENCLAW_OFFICIAL_PROVIDER_SNAPSHOT = {
    "source": "official_openclaw_docs_provider_directory_and_llms_index_checked_2026-05-31",
    "source_urls": [
        "https://docs.openclaw.ai/providers",
        "https://docs.openclaw.ai/llms.txt",
        "https://docs.openclaw.ai/concepts/model-providers",
    ],
    "provider_ids": [
        "alibaba",
        "amazon-bedrock",
        "amazon-bedrock-mantle",
        "anthropic",
        "anthropic-vertex",
        "arcee",
        "azure-speech",
        "byteplus",
        "cerebras",
        "chutes",
        "claude-max-api-proxy",
        "cloudflare-ai-gateway",
        "comfyui",
        "deepgram",
        "deepinfra",
        "deepseek",
        "ds4",
        "elevenlabs",
        "fal",
        "fireworks",
        "github-copilot",
        "gmi",
        "google",
        "google-gemini-cli",
        "google-vertex",
        "gradium",
        "groq",
        "huggingface",
        "inferrs",
        "inworld",
        "kilocode",
        "litellm",
        "lmstudio",
        "minimax",
        "mistral",
        "moonshot",
        "novita",
        "nvidia",
        "ollama",
        "ollama-cloud",
        "openai",
        "opencode",
        "opencode-go",
        "openrouter",
        "perplexity",
        "pixverse",
        "qianfan",
        "qwen",
        "qwen-oauth",
        "runway",
        "senseaudio",
        "sglang",
        "stepfun",
        "synthetic",
        "tencent-tokenhub",
        "together",
        "venice",
        "vercel-ai-gateway",
        "vllm",
        "volcengine",
        "vydra",
        "xai",
        "xiaomi",
        "zai",
    ],
}

OPENCLAW_OFFICIAL_CHANNEL_SNAPSHOT = {
    "source": "official_openclaw_docs_channel_index_and_llms_index_checked_2026-05-31",
    "source_urls": [
        "https://docs.openclaw.ai/channels",
        "https://docs.openclaw.ai/llms.txt",
        "https://docs.openclaw.ai/gateway/config-channels",
        "https://docs.openclaw.ai/announcements/bluebubbles-imessage",
        "https://docs.openclaw.ai/channels/bluebubbles",
    ],
    "channel_ids": [
        "bluebubbles",
        "clickclack",
        "discord",
        "feishu",
        "google-chat",
        "imessage",
        "irc",
        "line",
        "matrix",
        "mattermost",
        "microsoft-teams",
        "nextcloud-talk",
        "nostr",
        "qa-channel",
        "qq-bot",
        "signal",
        "slack",
        "sms",
        "synology-chat",
        "telegram",
        "tlon",
        "twitch",
        "voice-call",
        "webchat",
        "wechat",
        "whatsapp",
        "yuanbao",
        "zalo",
        "zalo-personal",
    ],
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _sorted_set(items: list[str]) -> list[str]:
    return sorted({str(item).strip() for item in items if str(item).strip()})


def _coverage(expected: list[str], actual: list[str]) -> dict[str, Any]:
    expected_ids = _sorted_set(expected)
    actual_ids = _sorted_set(actual)
    missing = sorted(set(expected_ids) - set(actual_ids))
    extra = sorted(set(actual_ids) - set(expected_ids))
    covered = sorted(set(expected_ids) & set(actual_ids))
    return {
        "expected_count": len(expected_ids),
        "actual_count": len(actual_ids),
        "covered_count": len(covered),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "covered_ids": covered,
        "missing_ids": missing,
        "extra_local_ids": extra,
        "complete": not missing,
    }


def _selector_checks() -> dict[str, Any]:
    provider_samples = [
        "arcee",
        "qwen-oauth",
        "google-gemini-cli",
        "claude-max-api-proxy",
        "lmstudio",
        "vercel-ai-gateway",
    ]
    channel_samples = [
        "googlechat",
        "msteams",
        "click-clack",
        "qa_channel",
        "zalouser",
        "openclaw-channel-telegram",
    ]
    return {
        "provider_id_resolution": [
            {
                "input": sample,
                "resolved_provider_id": (find_openclaw_provider(sample) or {}).get("provider_id"),
                "resolved": find_openclaw_provider(sample) is not None,
            }
            for sample in provider_samples
        ],
        "channel_id_resolution": [
            {
                "input": sample,
                "resolved_channel_id": (find_openclaw_channel(sample) or {}).get("channel_id"),
                "resolved": find_openclaw_channel(sample) is not None,
            }
            for sample in channel_samples
        ],
    }


def audit_openclaw_parity(*, output_path: Path | None = None) -> dict[str, Any]:
    provider_manifest = openclaw_provider_manifest()
    channel_manifest = openclaw_channel_manifest()
    local_provider_ids = [
        *[provider["provider_id"] for provider in OPENCLAW_MODEL_PROVIDERS],
        *OPENCLAW_MANIFEST_ONLY_PROVIDERS,
    ]
    local_channel_ids = [channel["channel_id"] for channel in channel_manifest["channels"]]
    provider_coverage = _coverage(
        OPENCLAW_OFFICIAL_PROVIDER_SNAPSHOT["provider_ids"],
        local_provider_ids,
    )
    channel_coverage = _coverage(
        OPENCLAW_OFFICIAL_CHANNEL_SNAPSHOT["channel_ids"],
        local_channel_ids,
    )
    selector_checks = _selector_checks()
    selector_complete = all(item["resolved"] for item in selector_checks["provider_id_resolution"]) and all(
        item["resolved"] for item in selector_checks["channel_id_resolution"]
    )
    audit = {
        "schema": OPENCLAW_PARITY_AUDIT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if provider_coverage["complete"] and channel_coverage["complete"] and selector_complete else "needs_update",
        "source_snapshots": {
            "providers": OPENCLAW_OFFICIAL_PROVIDER_SNAPSHOT,
            "channels": OPENCLAW_OFFICIAL_CHANNEL_SNAPSHOT,
        },
        "local_manifests": {
            "provider_manifest_schema": provider_manifest["schema"],
            "provider_source_version": provider_manifest["source_version"],
            "channel_manifest_schema": channel_manifest["schema"],
            "channel_source_version": channel_manifest["source_version"],
        },
        "coverage": {
            "providers": provider_coverage,
            "channels": channel_coverage,
        },
        "connector_strategy": {
            "direct_llm_adapters": [
                provider["provider_id"]
                for provider in OPENCLAW_MODEL_PROVIDERS
                if provider["engine"] != "openclaw_manifest_only"
            ],
            "manifest_only_provider_count": len(OPENCLAW_MANIFEST_ONLY_PROVIDERS),
            "all_channels_normalized_gateway_ready": channel_coverage["complete"],
            "live_platform_tokens_stored": False,
        },
        "selector_checks": selector_checks,
        "policy": {
            "claim_boundary": "This audit proves catalog/selector parity with the checked OpenClaw docs snapshot, not that every external OAuth/plugin has been locally authenticated.",
            "secrets": "No provider key, bot token, QR session, or private training file is read or stored.",
            "future_docs_drift": "Refresh this snapshot when OpenClaw provider/channel docs change.",
        },
    }
    if output_path is not None:
        _write_json(output_path, audit)
    return audit
