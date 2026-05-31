from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from ai22b.talent_foundry.openclaw_compat import (
    OPENCLAW_MANIFEST_ONLY_PROVIDERS,
    OPENCLAW_MODEL_PROVIDERS,
    find_openclaw_channel,
    find_openclaw_provider,
    openclaw_channel_manifest,
    openclaw_provider_manifest,
)


OPENCLAW_PARITY_AUDIT_SCHEMA = "ai22b-openclaw-parity-audit/v1"
OPENCLAW_LIVE_DOCS_TIMEOUT_SECONDS = 15
OPENCLAW_LIVE_DOC_URLS = [
    "https://docs.openclaw.ai/providers",
    "https://docs.openclaw.ai/channels",
    "https://docs.openclaw.ai/llms.txt",
]

PROVIDER_DOC_NON_ENTRY_SLUGS = {
    "index",
    "models",
}

CHANNEL_DOC_NON_ENTRY_SLUGS = {
    "access-groups",
    "ambient-room-events",
    "bot-loop-protection",
    "broadcast-groups",
    "channel-routing",
    "group-messages",
    "groups",
    "location",
    "matrix-migration",
    "matrix-presentation",
    "matrix-presentation-metadata",
    "matrix-push-rules",
    "pairing",
    "security",
    "troubleshooting",
}

PROVIDER_DOC_SLUG_IDS: dict[str, list[str]] = {
    "alibaba": ["alibaba"],
    "amazon-bedrock": ["amazon-bedrock"],
    "anthropic": ["anthropic"],
    "anthropic-vertex": ["anthropic-vertex"],
    "arcee": ["arcee"],
    "azure-speech": ["azure-speech"],
    "bedrock": ["amazon-bedrock"],
    "bedrock-mantle": ["amazon-bedrock-mantle"],
    "byteplus": ["byteplus", "byteplus-plan"],
    "cerebras": ["cerebras"],
    "chutes": ["chutes"],
    "claude-max-api-proxy": ["claude-max-api-proxy"],
    "cloudflare-ai-gateway": ["cloudflare-ai-gateway"],
    "comfy": ["comfyui"],
    "comfyui": ["comfyui"],
    "deepgram": ["deepgram"],
    "deepinfra": ["deepinfra"],
    "deepseek": ["deepseek"],
    "ds4": ["ds4"],
    "elevenlabs": ["elevenlabs"],
    "fal": ["fal"],
    "fireworks": ["fireworks"],
    "github-copilot": ["github-copilot"],
    "gmi": ["gmi"],
    "google": ["google", "google-gemini-cli", "google-vertex"],
    "google-gemini-cli": ["google-gemini-cli"],
    "google-vertex": ["google-vertex"],
    "gradium": ["gradium"],
    "groq": ["groq"],
    "huggingface": ["huggingface"],
    "inferrs": ["inferrs"],
    "inworld": ["inworld"],
    "kilocode": ["kilocode"],
    "kimi": ["moonshot"],
    "litellm": ["litellm"],
    "lmstudio": ["lmstudio"],
    "minimax": ["minimax", "minimax-portal"],
    "mistral": ["mistral"],
    "moonshot": ["moonshot"],
    "novita": ["novita"],
    "nvidia": ["nvidia"],
    "ollama": ["ollama", "ollama-cloud"],
    "ollama-cloud": ["ollama-cloud"],
    "openai": ["openai"],
    "opencode": ["opencode"],
    "opencode-go": ["opencode-go"],
    "openrouter": ["openrouter"],
    "perplexity": ["perplexity"],
    "perplexity-provider": ["perplexity"],
    "pixverse": ["pixverse"],
    "qianfan": ["qianfan"],
    "qwen": ["qwen", "qwen-oauth"],
    "qwen-oauth": ["qwen-oauth"],
    "runway": ["runway"],
    "senseaudio": ["senseaudio"],
    "sglang": ["sglang"],
    "stepfun": ["stepfun", "stepfun-plan"],
    "synthetic": ["synthetic"],
    "tencent": ["tencent-tokenhub"],
    "tencent-tokenhub": ["tencent-tokenhub"],
    "together": ["together"],
    "venice": ["venice"],
    "vercel-ai-gateway": ["vercel-ai-gateway"],
    "vllm": ["vllm"],
    "volcengine": ["volcengine", "volcengine-plan"],
    "vydra": ["vydra"],
    "xai": ["xai"],
    "xiaomi": ["xiaomi", "xiaomi-token-plan"],
    "zai": ["zai"],
}

CHANNEL_DOC_SLUG_IDS: dict[str, list[str]] = {
    "bluebubbles": ["bluebubbles"],
    "clickclack": ["clickclack"],
    "discord": ["discord"],
    "feishu": ["feishu"],
    "googlechat": ["google-chat"],
    "imessage": ["imessage"],
    "imessage-from-bluebubbles": ["bluebubbles"],
    "irc": ["irc"],
    "line": ["line"],
    "matrix": ["matrix"],
    "mattermost": ["mattermost"],
    "msteams": ["microsoft-teams"],
    "nextcloud-talk": ["nextcloud-talk"],
    "nostr": ["nostr"],
    "qa-channel": ["qa-channel"],
    "qqbot": ["qq-bot"],
    "signal": ["signal"],
    "slack": ["slack"],
    "sms": ["sms"],
    "synology-chat": ["synology-chat"],
    "telegram": ["telegram"],
    "tlon": ["tlon"],
    "twitch": ["twitch"],
    "voice-call": ["voice-call"],
    "webchat": ["webchat"],
    "wechat": ["wechat"],
    "whatsapp": ["whatsapp"],
    "yuanbao": ["yuanbao"],
    "zalo": ["zalo"],
    "zalouser": ["zalo-personal"],
}

OPENCLAW_OFFICIAL_PROVIDER_SNAPSHOT = {
    "source": "official_openclaw_docs_provider_directory_and_llms_index_checked_2026-06-01",
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
    "source": "official_openclaw_docs_channel_index_and_llms_index_checked_2026-06-01",
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


def _ids_from_doc_slugs(
    text: str,
    *,
    prefix: str,
    slug_ids: dict[str, list[str]],
) -> list[str]:
    ids, _unknown = _ids_and_unknown_from_doc_slugs(text, prefix=prefix, slug_ids=slug_ids)
    return ids


def _ids_and_unknown_from_doc_slugs(
    text: str,
    *,
    prefix: str,
    slug_ids: dict[str, list[str]],
    ignored_slugs: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    unknown_slugs: list[str] = []
    ignored = ignored_slugs or set()
    for raw_slug in re.findall(rf"https://docs\.openclaw\.ai/{re.escape(prefix)}/([a-z0-9-]+)", text):
        if raw_slug in ignored:
            continue
        mapped = slug_ids.get(raw_slug, [])
        if mapped:
            ids.extend(mapped)
        else:
            unknown_slugs.append(raw_slug)
    return _sorted_set(ids), _sorted_set(unknown_slugs)


def _provider_ids_from_doc_texts(texts: list[str]) -> list[str]:
    joined = "\n".join(texts)
    provider_ids = _provider_doc_scan(joined)["provider_ids"]
    return _sorted_set(provider_ids)


def _channel_ids_from_doc_texts(texts: list[str]) -> list[str]:
    joined = "\n".join(texts)
    channel_scan = _channel_doc_scan(joined)
    channel_ids = [*channel_scan["channel_ids"]]
    if re.search(r"\bWebChat\b", joined):
        channel_ids.append("webchat")
    if re.search(r"\bBlueBubbles\b", joined):
        channel_ids.append("bluebubbles")
    return _sorted_set(channel_ids)


def _provider_doc_scan(text: str) -> dict[str, list[str]]:
    provider_doc_ids, unknown_provider_doc_slugs = _ids_and_unknown_from_doc_slugs(
        text,
        prefix="providers",
        slug_ids=PROVIDER_DOC_SLUG_IDS,
        ignored_slugs=PROVIDER_DOC_NON_ENTRY_SLUGS,
    )
    plugin_ids, unmapped_plugin_reference_slugs = _ids_and_unknown_from_doc_slugs(
        text,
        prefix="plugins/reference",
        slug_ids=PROVIDER_DOC_SLUG_IDS,
    )
    return {
        "provider_ids": _sorted_set([*provider_doc_ids, *plugin_ids]),
        "unknown_provider_doc_slugs": unknown_provider_doc_slugs,
        "unmapped_plugin_reference_slugs": unmapped_plugin_reference_slugs,
    }


def _channel_doc_scan(text: str) -> dict[str, list[str]]:
    channel_doc_ids, unknown_channel_doc_slugs = _ids_and_unknown_from_doc_slugs(
        text,
        prefix="channels",
        slug_ids=CHANNEL_DOC_SLUG_IDS,
        ignored_slugs=CHANNEL_DOC_NON_ENTRY_SLUGS,
    )
    plugin_ids, unmapped_plugin_reference_slugs = _ids_and_unknown_from_doc_slugs(
        text,
        prefix="plugins/reference",
        slug_ids=CHANNEL_DOC_SLUG_IDS,
    )
    web_ids, unknown_web_slugs = _ids_and_unknown_from_doc_slugs(
        text,
        prefix="web",
        slug_ids=CHANNEL_DOC_SLUG_IDS,
    )
    platform_ids, unknown_platform_slugs = _ids_and_unknown_from_doc_slugs(
        text,
        prefix="platforms/mac",
        slug_ids=CHANNEL_DOC_SLUG_IDS,
    )
    return {
        "channel_ids": _sorted_set([*channel_doc_ids, *plugin_ids, *web_ids, *platform_ids]),
        "unknown_channel_doc_slugs": unknown_channel_doc_slugs,
        "unmapped_plugin_reference_slugs": unmapped_plugin_reference_slugs,
        "unknown_web_slugs": unknown_web_slugs,
        "unknown_platform_slugs": unknown_platform_slugs,
    }


def _fetch_openclaw_doc_text(url: str, *, timeout: int = OPENCLAW_LIVE_DOCS_TIMEOUT_SECONDS) -> str:
    request = Request(url, headers={"User-Agent": "Paideia-Agent-OpenClaw-Parity-Audit/1.0"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def _live_official_snapshots(*, timeout: int = OPENCLAW_LIVE_DOCS_TIMEOUT_SECONDS) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    texts: list[str] = []
    fetch_errors: list[dict[str, str]] = []
    fetched_urls: list[str] = []
    for url in OPENCLAW_LIVE_DOC_URLS:
        try:
            texts.append(_fetch_openclaw_doc_text(url, timeout=timeout))
            fetched_urls.append(url)
        except Exception as exc:  # Network and docs hosts can fail independently of local parity.
            fetch_errors.append({"url": url, "error_type": type(exc).__name__, "error": str(exc)[:300]})
    if fetch_errors and not texts:
        raise RuntimeError("Could not fetch any OpenClaw official docs for live parity audit")
    joined = "\n".join(texts)
    provider_scan = _provider_doc_scan(joined)
    channel_scan = _channel_doc_scan(joined)
    provider_ids = _sorted_set(provider_scan["provider_ids"])
    channel_ids = _sorted_set(channel_scan["channel_ids"])
    if re.search(r"\bWebChat\b", joined):
        channel_ids = _sorted_set([*channel_ids, "webchat"])
    if re.search(r"\bBlueBubbles\b", joined):
        channel_ids = _sorted_set([*channel_ids, "bluebubbles"])
    providers = {
        "source": "official_openclaw_docs_live_fetch",
        "source_urls": fetched_urls,
        "provider_ids": provider_ids,
        "unknown_provider_doc_slugs": provider_scan["unknown_provider_doc_slugs"],
        "unmapped_plugin_reference_slugs": provider_scan["unmapped_plugin_reference_slugs"],
    }
    channels = {
        "source": "official_openclaw_docs_live_fetch",
        "source_urls": fetched_urls,
        "channel_ids": channel_ids,
        "unknown_channel_doc_slugs": channel_scan["unknown_channel_doc_slugs"],
        "unmapped_plugin_reference_slugs": channel_scan["unmapped_plugin_reference_slugs"],
        "unknown_web_slugs": channel_scan["unknown_web_slugs"],
        "unknown_platform_slugs": channel_scan["unknown_platform_slugs"],
    }
    return providers, channels, fetch_errors


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


def audit_openclaw_parity(
    *,
    output_path: Path | None = None,
    refresh_docs: bool = False,
    docs_timeout: int = OPENCLAW_LIVE_DOCS_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    provider_manifest = openclaw_provider_manifest()
    channel_manifest = openclaw_channel_manifest()
    fetch_errors: list[dict[str, str]] = []
    if refresh_docs:
        provider_snapshot, channel_snapshot, fetch_errors = _live_official_snapshots(timeout=docs_timeout)
    else:
        provider_snapshot = OPENCLAW_OFFICIAL_PROVIDER_SNAPSHOT
        channel_snapshot = OPENCLAW_OFFICIAL_CHANNEL_SNAPSHOT
    local_provider_ids = [
        *[provider["provider_id"] for provider in OPENCLAW_MODEL_PROVIDERS],
        *OPENCLAW_MANIFEST_ONLY_PROVIDERS,
    ]
    local_channel_ids = [channel["channel_id"] for channel in channel_manifest["channels"]]
    provider_coverage = _coverage(
        provider_snapshot["provider_ids"],
        local_provider_ids,
    )
    channel_coverage = _coverage(
        channel_snapshot["channel_ids"],
        local_channel_ids,
    )
    selector_checks = _selector_checks()
    selector_complete = all(item["resolved"] for item in selector_checks["provider_id_resolution"]) and all(
        item["resolved"] for item in selector_checks["channel_id_resolution"]
    )
    doc_drift = {
        "unknown_provider_doc_slugs": provider_snapshot.get("unknown_provider_doc_slugs", []),
        "unknown_channel_doc_slugs": channel_snapshot.get("unknown_channel_doc_slugs", []),
        "unknown_web_slugs": channel_snapshot.get("unknown_web_slugs", []),
        "unknown_platform_slugs": channel_snapshot.get("unknown_platform_slugs", []),
        "unmapped_provider_reference_slug_count": len(provider_snapshot.get("unmapped_plugin_reference_slugs", [])),
        "unmapped_channel_reference_slug_count": len(channel_snapshot.get("unmapped_plugin_reference_slugs", [])),
    }
    unmapped_docs_block_parity = bool(
        doc_drift["unknown_provider_doc_slugs"]
        or doc_drift["unknown_channel_doc_slugs"]
    )
    audit = {
        "schema": OPENCLAW_PARITY_AUDIT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "pass"
            if provider_coverage["complete"]
            and channel_coverage["complete"]
            and selector_complete
            and not unmapped_docs_block_parity
            else "needs_update"
        ),
        "source_mode": "live_docs" if refresh_docs else "checked_snapshot",
        "source_snapshots": {
            "providers": provider_snapshot,
            "channels": channel_snapshot,
        },
        "live_fetch_errors": fetch_errors,
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
        "doc_drift": doc_drift,
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
            "unknown_provider_or_channel_doc_slugs_block_pass": True,
            "unmapped_plugin_reference_slugs_are_reported_only": True,
        },
    }
    if output_path is not None:
        _write_json(output_path, audit)
    return audit
