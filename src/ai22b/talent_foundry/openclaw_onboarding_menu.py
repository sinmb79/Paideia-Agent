from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.onboarding_choices import CHAT_SURFACE_CATALOG, LLM_SERVICE_CATALOG
from ai22b.talent_foundry.openclaw_support_matrix import build_openclaw_support_matrix


OPENCLAW_ONBOARDING_MENU_SCHEMA = "ai22b-openclaw-onboarding-menu/v1"

RECOMMENDED_LLM_SERVICE_IDS = [
    "openai_chatgpt_codex",
    "openclaw_gateway_http",
    "openrouter_api",
    "anthropic_claude_api",
    "google_gemini_api",
    "ollama_local",
    "lm_studio_local",
    "deterministic_local",
]

RECOMMENDED_CHAT_SURFACE_IDS = [
    "codex-bridge-chat",
    "openclaw-channel-webchat",
    "openclaw-channel-telegram",
    "openclaw-channel-discord",
    "openclaw-channel-slack",
    "openclaw-channel-whatsapp",
    "openclaw-channel-signal",
    "openclaw-channel-imessage",
    "openclaw-channel-matrix",
    "cli-console",
]

PROVIDER_MODEL_EXAMPLES = [
    "openai/gpt-5.5",
    "openrouter/meta-llama/llama-3.1-70b",
    "anthropic/claude-sonnet-4.5",
    "google/gemini-3.1-flash-lite",
    "ollama/qwen3:8b",
    "lmstudio/local-model",
    "qwen-oauth/qwen3-coder-plus",
]

CHAT_SURFACE_EXAMPLES = [
    "codex-bridge-chat",
    "openclaw-channel-webchat",
    "openclaw-channel-telegram",
    "openclaw-channel-whatsapp",
    "openclaw-channel-microsoft-teams",
    "openclaw-channel-zalo-personal",
]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _catalog_by_id(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in catalog}


def _choice_entry(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "label": item.get("label", item["id"]),
        "status": item.get("status"),
        "best_for": item.get("best_for") or item.get("researcher_fit"),
        "openclaw_provider_id": item.get("openclaw_provider_id"),
        "openclaw_channel_id": item.get("openclaw_channel_id"),
        "api_protocol": item.get("api_protocol"),
        "channel_policy": item.get("channel_policy"),
        "requires": item.get("requires", []),
        "secret_values_stored": False,
    }


def _recommended_entries(catalog: list[dict[str, Any]], ids: list[str]) -> list[dict[str, Any]]:
    by_id = _catalog_by_id(catalog)
    return [_choice_entry(by_id[item_id]) for item_id in ids if item_id in by_id]


def _provider_counts(provider_support: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(provider_support),
        "paideia_direct_adapter_ready": sum(1 for item in provider_support if item["paideia_direct_adapter_ready"]),
        "openclaw_gateway_route_ready": sum(1 for item in provider_support if item["openclaw_gateway_route_ready"]),
        "plugin_or_oauth_required": sum(1 for item in provider_support if item["provider_plugin_or_oauth_required"]),
        "local_endpoint": sum(1 for item in provider_support if item["local_endpoint"]),
    }


def _channel_counts(channel_support: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(channel_support),
        "direct_or_loopback_ready": sum(
            1 for item in channel_support if item["support_level"] in {"paideia_direct_flow_ready", "loopback_chat_ready"}
        ),
        "normalized_gateway_ready": sum(1 for item in channel_support if item["generic_normalized_gateway_ready"]),
        "plugin_or_bridge_required": sum(1 for item in channel_support if item["openclaw_plugin_or_bridge_required"]),
    }


def build_openclaw_onboarding_menu(
    *,
    output_path: Path | None = None,
    markdown_output_path: Path | None = None,
    refresh_docs: bool = False,
    docs_timeout: int = 15,
) -> dict[str, Any]:
    support_matrix = build_openclaw_support_matrix(refresh_docs=refresh_docs, docs_timeout=docs_timeout)
    provider_support = support_matrix["provider_support"]
    channel_support = support_matrix["channel_support"]
    menu = {
        "schema": OPENCLAW_ONBOARDING_MENU_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": support_matrix["status"],
        "source_mode": support_matrix["source_mode"],
        "purpose": "First-run menu for selecting any OpenClaw-compatible LLM provider/model and chat channel in Paideia onboarding.",
        "llm_selection": {
            "prompt": "Choose a built-in service id or type any OpenClaw provider/model selector.",
            "accepts_freeform_provider_model": True,
            "provider_model_examples": PROVIDER_MODEL_EXAMPLES,
            "recommended_choices": _recommended_entries(LLM_SERVICE_CATALOG, RECOMMENDED_LLM_SERVICE_IDS),
            "full_provider_support": provider_support,
            "counts": _provider_counts(provider_support),
        },
        "chat_selection": {
            "prompt": "Choose a built-in surface id or type any openclaw-channel-<channel> selector.",
            "accepts_freeform_openclaw_channel": True,
            "chat_surface_examples": CHAT_SURFACE_EXAMPLES,
            "recommended_choices": _recommended_entries(CHAT_SURFACE_CATALOG, RECOMMENDED_CHAT_SURFACE_IDS),
            "full_channel_support": channel_support,
            "counts": _channel_counts(channel_support),
        },
        "parity_summary": support_matrix["parity_summary"],
        "next_commands": {
            "doctor_selection": (
                "ai22b-talent-foundry doctor-openclaw-selection "
                "--llm-service <provider/model-or-service-id> --chat-surface <chat-surface-or-channel> "
                "--output openclaw_selection_doctor.json"
            ),
            "build_runtime_bundle": (
                "ai22b-talent-foundry build-openclaw-runtime-bundle "
                "--employment-record <employment_record.json> --channel <channel> --output-dir openclaw_runtime_bundle"
            ),
            "build_native_onboarding_runbook": (
                "ai22b-talent-foundry build-openclaw-native-onboarding-runbook "
                "--runtime-bundle openclaw_runtime_bundle/openclaw_runtime_bundle.json "
                "--output OPENCLAW_NATIVE_ONBOARDING_RUNBOOK.json "
                "--markdown-output OPENCLAW_NATIVE_ONBOARDING_RUNBOOK.md"
            ),
            "runtime_preflight": (
                "ai22b-talent-foundry doctor-openclaw-runtime-preflight "
                "--runtime-bundle openclaw_runtime_bundle/openclaw_runtime_bundle.json --run-channel-flow "
                "--output openclaw_runtime_preflight.json"
            ),
        },
        "policy": {
            "secret_values_stored": False,
            "external_network_call_performed": bool(refresh_docs),
            "private_training_files_exported": False,
            "selection_values_are_metadata_only": True,
        },
    }
    if output_path is not None:
        _write_json(output_path, menu)
    if markdown_output_path is not None:
        render_openclaw_onboarding_menu_markdown(menu, output_path=markdown_output_path)
    return menu


def _markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return lines


def render_openclaw_onboarding_menu_markdown(menu: dict[str, Any], *, output_path: Path | None = None) -> str:
    lines = [
        "# Paideia OpenClaw Onboarding Menu",
        "",
        f"- Status: `{menu['status']}`",
        f"- Source mode: `{menu['source_mode']}`",
        "- Secrets stored: `false`",
        "",
        "## LLM Selection",
        "",
        menu["llm_selection"]["prompt"],
        "",
        "Examples: " + ", ".join(f"`{item}`" for item in menu["llm_selection"]["provider_model_examples"]),
        "",
        "### Recommended LLM Choices",
        "",
    ]
    lines.extend(
        _markdown_table(
            ["ID", "Label", "Status", "Provider"],
            [
                [
                    item["id"],
                    item.get("label", ""),
                    item.get("status", ""),
                    item.get("openclaw_provider_id") or "",
                ]
                for item in menu["llm_selection"]["recommended_choices"]
            ],
        )
    )
    lines.extend(
        [
            "",
            "### All OpenClaw Providers",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Provider", "Support", "Protocol", "Recommended Path"],
            [
                [
                    item["provider_id"],
                    item["support_level"],
                    item["api_protocol"],
                    item["recommended_path"],
                ]
                for item in menu["llm_selection"]["full_provider_support"]
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Chat Selection",
            "",
            menu["chat_selection"]["prompt"],
            "",
            "Examples: " + ", ".join(f"`{item}`" for item in menu["chat_selection"]["chat_surface_examples"]),
            "",
            "### Recommended Chat Choices",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["ID", "Label", "Status", "Channel"],
            [
                [
                    item["id"],
                    item.get("label", ""),
                    item.get("status", ""),
                    item.get("openclaw_channel_id") or "",
                ]
                for item in menu["chat_selection"]["recommended_choices"]
            ],
        )
    )
    lines.extend(
        [
            "",
            "### All OpenClaw Channels",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Channel", "Support", "Transport", "Recommended Path"],
            [
                [
                    item["channel_id"],
                    item["support_level"],
                    item["transport"],
                    item["recommended_path"],
                ]
                for item in menu["chat_selection"]["full_channel_support"]
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Next Commands",
            "",
        ]
    )
    for key, command in menu["next_commands"].items():
        lines.append(f"- `{key}`: `{command}`")
    text = "\n".join(lines) + "\n"
    if output_path is not None:
        _write_text(output_path, text)
    return text
