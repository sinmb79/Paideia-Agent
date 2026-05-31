from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.channel_connectors import (
    build_openclaw_channel_connector_catalog,
    doctor_openclaw_channel_connectors,
)
from ai22b.talent_foundry.channel_delivery import (
    SUPPORTED_DELIVERY_CHANNELS,
    build_openclaw_channel_delivery_config,
)
from ai22b.talent_foundry.channel_gateway import build_openclaw_gateway_config
from ai22b.talent_foundry.channel_ingress import build_openclaw_channel_access_config
from ai22b.talent_foundry.onboarding_choices import build_llm_service_health
from ai22b.talent_foundry.openclaw_compat import (
    find_openclaw_channel,
    find_openclaw_provider,
    openclaw_channel_manifest,
    openclaw_provider_manifest,
)
from ai22b.talent_foundry.openclaw_gateway_llm import doctor_openclaw_gateway_llm
from ai22b.talent_foundry.provider_connectors import doctor_openclaw_provider_connectors


OPENCLAW_RUNTIME_BUNDLE_SCHEMA = "ai22b-openclaw-runtime-bundle/v1"
OPENCLAW_CONFIG_PATCH_SCHEMA = "ai22b-openclaw-config-patch/v1"
OPENCLAW_EXISTING_CONFIG_REVIEW_SCHEMA = "ai22b-openclaw-existing-config-review/v1"
OPENCLAW_CONFIG_MERGE_PREVIEW_SCHEMA = "ai22b-openclaw-config-merge-preview/v1"
OPENCLAW_CONFIG_RESET_PLAN_SCHEMA = "ai22b-openclaw-config-reset-plan/v1"
OPENCLAW_NATIVE_HANDOFF_SCHEMA = "ai22b-openclaw-native-handoff/v1"

OPENCLAW_REFERENCE_URLS = [
    "https://docs.openclaw.ai/start/wizard-cli-flow",
    "https://docs.openclaw.ai/configuration",
    "https://docs.openclaw.ai/providers",
    "https://docs.openclaw.ai/concepts/model-providers",
    "https://docs.openclaw.ai/channels",
    "https://docs.openclaw.ai/channels/channel-routing",
    "https://docs.openclaw.ai/gateway/config-agents",
    "https://docs.openclaw.ai/gateway/config-channels",
    "https://docs.openclaw.ai/gateway/openai-http-api",
    "https://docs.openclaw.ai/cli/gateway",
    "https://docs.openclaw.ai/cli/channels",
    "https://docs.openclaw.ai/concepts/agent-runtimes",
    "https://docs.openclaw.ai/agent-workspace",
    "https://docs.openclaw.ai/announcements/bluebubbles-imessage",
    "https://docs.openclaw.ai/channels/bluebubbles",
]

CONFIG_ACTIONS = {"keep", "modify", "reset"}
SECRET_KEY_PATTERNS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "cookie",
    "credential",
    "key",
    "password",
    "private",
    "secret",
    "session",
    "token",
    "webhook",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _default_openclaw_config_path() -> Path:
    return Path.home() / ".openclaw" / "openclaw.json"


def _secret_like_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.casefold())
    return any(pattern in normalized for pattern in SECRET_KEY_PATTERNS)


def _redact_config(value: Any, *, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if _secret_like_key(str(key)) else _redact_config(item, parent_key=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_config(item, parent_key=parent_key) for item in value]
    if parent_key and _secret_like_key(parent_key):
        return "<redacted>"
    return value


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _relative_or_name(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _load_employment(employment_record_path: Path) -> dict[str, Any]:
    employment = _read_json(employment_record_path)
    if employment.get("schema") != "ai-talent-local-employment/v1":
        raise ValueError("Unsupported local employment record schema")
    if employment.get("status") != "active":
        raise ValueError("Local employment record is not active")
    return employment


def _safe_agent_key(employment: dict[str, Any]) -> str:
    raw = f"paideia-{employment.get('employment_id', 'agent')}"
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-").casefold()
    return value or "paideia-agent"


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
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


def _infer_provider_id(employment: dict[str, Any]) -> str:
    llm_service = employment.get("llm_service", {})
    llm_runtime = employment.get("llm_runtime", {})
    model_selector = str(llm_service.get("openclaw_model") or llm_runtime.get("openclaw_model") or "")
    if (
        llm_service.get("engine") == "openclaw_gateway_http"
        or llm_runtime.get("engine") == "openclaw_gateway_http"
    ) and "/" in model_selector:
        return model_selector.split("/", 1)[0]
    provider_id = llm_service.get("openclaw_provider_id") or llm_runtime.get("openclaw_provider_id")
    if provider_id:
        return str(provider_id)
    if "/" in model_selector:
        return model_selector.split("/", 1)[0]
    service_id = str(llm_service.get("service_id") or llm_runtime.get("service") or "")
    provider = find_openclaw_provider(service_id)
    if provider is not None:
        return str(provider["provider_id"])
    return "openai"


def _model_selector(employment: dict[str, Any], provider_id: str) -> str:
    llm_service = employment.get("llm_service", {})
    llm_runtime = employment.get("llm_runtime", {})
    openclaw_model = llm_service.get("openclaw_model") or llm_runtime.get("openclaw_model")
    if openclaw_model:
        return str(openclaw_model)
    provider = find_openclaw_provider(provider_id)
    selected_model = llm_service.get("selected_model") or llm_runtime.get("model") or (
        provider.get("default_model") if provider else None
    )
    if selected_model:
        selected = str(selected_model)
        return selected if "/" in selected else f"{provider_id}/{selected}"
    return f"{provider_id}/<select-model>"


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
    for channel_id in requested:
        channel = find_openclaw_channel(channel_id)
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel: {channel_id}")
        normalized.append(str(channel["channel_id"]))
    return _dedupe(normalized)


def _validate_model_selector(model_selector: str) -> str:
    model = model_selector.strip()
    if not model:
        raise ValueError("OpenClaw model selector cannot be empty")
    if "/" in model:
        provider_id = model.split("/", 1)[0].strip()
        if not find_openclaw_provider(provider_id):
            raise ValueError(f"Unsupported OpenClaw provider in channel model: {provider_id}")
    return model


def _merge_channel_model_maps(
    base: dict[str, dict[str, str]],
    override: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    merged: dict[str, dict[str, str]] = {channel: dict(targets) for channel, targets in base.items()}
    for channel_id, targets in override.items():
        merged.setdefault(channel_id, {}).update(targets)
    return merged


def _normalize_channel_model_map(raw: Any) -> dict[str, dict[str, str]]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for raw_channel, raw_targets in raw.items():
        channel = find_openclaw_channel(str(raw_channel))
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel in channel model map: {raw_channel}")
        channel_id = str(channel["channel_id"])
        if isinstance(raw_targets, str):
            normalized.setdefault(channel_id, {})["*"] = _validate_model_selector(raw_targets)
        elif isinstance(raw_targets, dict):
            for target, raw_model in raw_targets.items():
                if isinstance(raw_model, str):
                    normalized.setdefault(channel_id, {})[str(target)] = _validate_model_selector(raw_model)
                elif isinstance(raw_model, dict):
                    model = raw_model.get("model") or raw_model.get("primary") or raw_model.get("default")
                    if model:
                        normalized.setdefault(channel_id, {})[str(target)] = _validate_model_selector(str(model))
    return normalized


def _parse_channel_model_specs(specs: list[str] | None) -> dict[str, dict[str, str]]:
    parsed: dict[str, dict[str, str]] = {}
    for spec in specs or []:
        if "=" not in spec:
            raise ValueError("Channel model specs must look like CHANNEL[:TARGET]=PROVIDER/MODEL")
        left, model = spec.split("=", 1)
        left = left.strip()
        if not left:
            raise ValueError("Channel model spec is missing a channel")
        if ":" in left:
            raw_channel, target = left.split(":", 1)
            target = target.strip() or "*"
        else:
            raw_channel, target = left, "*"
        channel = find_openclaw_channel(raw_channel)
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel in channel model spec: {raw_channel}")
        channel_id = str(channel["channel_id"])
        parsed.setdefault(channel_id, {})[target] = _validate_model_selector(model)
    return parsed


def _binding_to_openclaw(binding: dict[str, Any], default_agent_id: str) -> dict[str, Any] | None:
    match = binding.get("match") if isinstance(binding.get("match"), dict) else {}
    raw_channel = match.get("channel") or binding.get("channel_id") or binding.get("channel")
    if not raw_channel:
        return None
    channel = find_openclaw_channel(str(raw_channel))
    if channel is None:
        raise ValueError(f"Unsupported OpenClaw channel in binding: {raw_channel}")
    openclaw_match: dict[str, Any] = {"channel": str(channel["channel_id"])}
    for key in (
        "accountId",
        "channelId",
        "conversation",
        "guildId",
        "peer",
        "roles",
        "roomId",
        "teamId",
        "threadId",
        "topicId",
    ):
        if key in match and match[key] not in (None, ""):
            openclaw_match[key] = match[key]
    return {
        "match": openclaw_match,
        "agentId": str(binding.get("agentId") or binding.get("agent_id") or binding.get("agent") or default_agent_id),
        "secretValuesStored": False,
    }


def _parse_binding_specs(specs: list[str] | None, *, default_agent_id: str) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for spec in specs or []:
        if "=" not in spec:
            raise ValueError("Binding specs must look like CHANNEL[:CONVERSATION]=AGENT_ID")
        left, agent_id = spec.split("=", 1)
        left = left.strip()
        agent_id = agent_id.strip() or default_agent_id
        if not left:
            raise ValueError("Binding spec is missing a channel")
        if ":" in left:
            raw_channel, conversation = left.split(":", 1)
        else:
            raw_channel, conversation = left, ""
        channel = find_openclaw_channel(raw_channel)
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel in binding spec: {raw_channel}")
        match: dict[str, Any] = {"channel": str(channel["channel_id"])}
        if conversation.strip() and conversation.strip() != "*":
            match["conversation"] = conversation.strip()
        bindings.append({"match": match, "agentId": agent_id, "secretValuesStored": False})
    return bindings


def _load_openclaw_import_hints(import_manifest_path: Path | None, *, default_agent_id: str) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    if import_manifest_path is None:
        return {}, []
    manifest = _read_json(import_manifest_path.expanduser().resolve())
    if manifest.get("schema") != "ai22b-openclaw-config-import/v1":
        raise ValueError("Unsupported OpenClaw import manifest schema")
    selection = manifest.get("paideia_selection", {})
    detected = manifest.get("detected", {})
    channel_models = _normalize_channel_model_map(selection.get("model_by_channel") or detected.get("model_by_channel") or {})
    bindings: list[dict[str, Any]] = []
    for binding in selection.get("bindings") or detected.get("bindings") or []:
        if isinstance(binding, dict):
            normalized = _binding_to_openclaw(binding, default_agent_id)
            if normalized is not None:
                bindings.append(normalized)
    return channel_models, bindings


def _channels_from_channel_models(model_by_channel: dict[str, dict[str, str]]) -> list[str]:
    return sorted(model_by_channel.keys())


def _channels_from_bindings(bindings: list[dict[str, Any]]) -> list[str]:
    channels: list[str] = []
    for binding in bindings:
        match = binding.get("match", {})
        if isinstance(match, dict) and match.get("channel"):
            channels.append(str(match["channel"]))
    return _dedupe(channels)


def _default_bindings_for_channels(channels: list[str], *, agent_id: str) -> list[dict[str, Any]]:
    return [
        {
            "match": {"channel": channel_id, "accountId": "*"},
            "agentId": agent_id,
            "source": "paideia_runtime_default_channel_binding",
            "secretValuesStored": False,
        }
        for channel_id in channels
    ]


def _channel_env_vars(channel_doctor: dict[str, Any]) -> list[str]:
    env_vars: list[str] = []
    for result in channel_doctor.get("results", []):
        for check in result.get("checks", []):
            check_id = str(check.get("id") or "")
            if check_id.startswith("env:"):
                env_vars.extend(_env_alternatives(check_id.removeprefix("env:")))
    return _dedupe(env_vars)


def _provider_env_vars(provider_doctor: dict[str, Any]) -> list[str]:
    env_vars: list[str] = []
    for result in provider_doctor.get("results", []):
        for check in result.get("checks", []):
            check_id = str(check.get("id") or "")
            if check_id.startswith("env:"):
                env_vars.extend(_env_alternatives(check_id.removeprefix("env:")))
    return _dedupe(env_vars)


def _build_env_template(
    *,
    provider_id: str,
    channels: list[str],
    provider_env_vars: list[str],
    channel_env_vars: list[str],
    bind_host: str,
    port: int,
) -> str:
    lines = [
        "# Paideia Agent OpenClaw runtime environment template",
        "# Set these values only in your local shell. Do not commit real secrets.",
        f"# Provider: {provider_id}",
    ]
    if provider_env_vars:
        lines.append("# Choose one compatible provider secret unless your provider requires more.")
        for env_var in provider_env_vars:
            lines.append(f'# $env:{env_var} = "<set-locally>"')
    else:
        lines.append("# No provider secret is required by the selected local/offline adapter.")
    lines.extend(
        [
            "",
            "# Channel bridge secrets and paths",
            f"# Channels: {', '.join(channels)}",
        ]
    )
    if channel_env_vars:
        for env_var in channel_env_vars:
            lines.append(f'# $env:{env_var} = "<set-locally>"')
    else:
        lines.append("# No channel secret is required for the selected local channel.")
    lines.extend(
        [
            "",
            "# Local Paideia OpenClaw-compatible gateway",
            f'$env:PAIDEIA_OPENCLAW_GATEWAY_URL = "http://{bind_host}:{port}/openclaw/channel-message"',
            "",
        ]
    )
    return "\n".join(lines)


def _build_config_patch(
    *,
    employment_record_path: Path,
    employment: dict[str, Any],
    provider_id: str,
    model_selector: str,
    provider: dict[str, Any] | None,
    channels: list[str],
    bind_host: str,
    port: int,
    provider_env_vars: list[str],
    channel_doctor: dict[str, Any],
    channel_model_map: dict[str, dict[str, str]],
    bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    agent_key = _safe_agent_key(employment)
    gateway_url = f"http://{bind_host}:{port}/openclaw/channel-message"
    channel_connectors = {item["channel_id"]: item for item in channel_doctor.get("results", [])}
    agent_workspace = str(employment_record_path.parent)
    provider_config = {
        "provider": provider_id,
        "model": model_selector,
        "apiProtocol": (provider or {}).get("api_protocol"),
        "baseURL": (provider or {}).get("base_url"),
        "auth": {
            "envCandidates": provider_env_vars,
            "secretValuesStored": False,
        },
    }
    return {
        "schema": OPENCLAW_CONFIG_PATCH_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_runtime": "OpenClaw-compatible local gateway",
        "source_docs_checked": OPENCLAW_REFERENCE_URLS,
        "employment": {
            "employment_id": employment["employment_id"],
            "agent": employment["agent"],
            "employment_record": str(employment_record_path),
            "identity_boundary": "Paideia local training records remain identity; the selected LLM is an application engine.",
        },
        "openclaw_json_patch": {
            "agents": {
                "defaults": {
                    "model": {"primary": model_selector},
                    "workspace": agent_workspace,
                },
                "list": [
                    {
                        "id": agent_key,
                        "name": employment["agent"]["name"],
                        "workspace": agent_workspace,
                        "model": {"primary": model_selector},
                        "default": True,
                    }
                ],
                agent_key: {
                    "name": employment["agent"]["name"],
                    "role": employment["agent"].get("role"),
                    "workspace": agent_workspace,
                    "model": {"primary": model_selector},
                    "channels": channels,
                    "gateway": {
                        "type": "paideia-local-openclaw-channel-gateway",
                        "url": gateway_url,
                        "health": f"http://{bind_host}:{port}/health",
                    },
                    "memory": {
                        "source": "Paideia memory_substrate, learning ledger, curriculum, and Reasoning Ledger artifacts",
                        "private_reasoning_trace": "do_not_store",
                    },
                },
            },
            "models": {
                "providers": {
                    provider_id: provider_config,
                },
            },
            "gateway": {
                "mode": "local",
                "http": {
                    "endpoints": {
                        "chatCompletions": {
                            "enabled": True,
                        },
                    },
                },
            },
            "channels": {
                **{
                    channel_id: {
                        "enabled": True,
                        "gatewayURL": gateway_url,
                        "connectorStatus": channel_connectors.get(channel_id, {}).get("connector_status"),
                        "nextStep": channel_connectors.get(channel_id, {}).get("next_step"),
                    }
                    for channel_id in channels
                },
                "modelByChannel": channel_model_map,
            },
            "bindings": bindings,
        },
        "operator_policy": {
            "existing_openclaw_config": "merge_or_review; do_not_reset_without_user_choice",
            "secret_values_stored": False,
            "private_training_files_exported": False,
            "recommended_bind_host": "127.0.0.1",
            "live_channel_send": "explicit_plugin_or_send_command_required",
        },
    }


def _build_native_handoff(
    *,
    employment_record_path: Path,
    employment: dict[str, Any],
    provider_id: str,
    model_selector: str,
    channels: list[str],
    bind_host: str,
    port: int,
    config_patch_path: Path,
    existing_config_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    agent_key = _safe_agent_key(employment)
    workspace = employment_record_path.parent
    openclaw_bin = shutil.which("openclaw")
    channel_add_help = {
        channel_id: f"openclaw channels add --channel {channel_id} --help"
        for channel_id in channels
        if channel_id != "webchat"
    }
    handoff = {
        "schema": OPENCLAW_NATIVE_HANDOFF_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_owner_review",
        "claim_boundary": (
            "This handoff lets a reviewed Paideia talent be mounted into an installed OpenClaw runtime. "
            "OpenClaw owns native provider auth, channel plugins, gateway sessions, and final platform delivery."
        ),
        "openclaw_cli": {
            "binary": openclaw_bin or "openclaw",
            "detected_on_path": bool(openclaw_bin),
            "setup_required_if_missing": True,
        },
        "paideia_agent": {
            "employment_id": employment["employment_id"],
            "agent_id": agent_key,
            "agent_name": employment["agent"]["name"],
            "employment_record": str(employment_record_path),
            "workspace": str(workspace),
            "identity_boundary": "Paideia local education records and Reasoning Ledger remain the agent memory substrate.",
        },
        "native_openclaw_selection": {
            "provider_id": provider_id,
            "model": model_selector,
            "channels": channels,
            "gateway_mode": "local",
            "bindings_expected": True,
            "channel_model_overrides_expected": True,
        },
        "config_files": {
            "existing_openclaw_config": str(existing_config_path),
            "review_first_patch": str(config_patch_path),
            "patch_contains": [
                "gateway.mode",
                "gateway.http.endpoints.chatCompletions.enabled",
                "models.providers",
                "agents.defaults.workspace",
                "agents.list",
                "channels.modelByChannel",
                "bindings",
            ],
            "direct_write_performed": False,
        },
        "operator_commands": {
            "setup_workspace": f'openclaw setup --workspace "{workspace}"',
            "review_model_auth": "openclaw models auth list",
            "configure_model_interactive": "openclaw config --section model",
            "set_gateway_local_dry_run": "openclaw config set gateway.mode local --dry-run",
            "doctor_before_merge": "openclaw doctor",
            "list_channels": "openclaw channels list --all",
            "channel_add_help": channel_add_help,
            "channel_status_probe": "openclaw channels status --probe --json",
            "run_gateway": "openclaw gateway run",
            "paideia_loopback_gateway": (
                "ai22b-talent-foundry run-openclaw-channel-gateway-server "
                f"--employment-record {employment_record_path} "
                + " ".join(f"--channel {channel}" for channel in channels)
                + f" --bind-host {bind_host} --port {port}"
            ),
        },
        "native_runtime_notes": [
            "Use OpenClaw's provider/model auth and plugin setup for providers Paideia marks as provider_plugin_required.",
            "Use `openclaw channels add --channel <id> --help` to see the current native flags for each channel.",
            "OpenClaw routes replies back to the origin channel; the selected model should not choose the outbound channel.",
            "Review and merge the patch manually or through an owner-approved OpenClaw config workflow.",
        ],
        "security": {
            "secret_values_stored": False,
            "private_training_files_exported": False,
            "existing_config_overwritten": False,
            "channel_tokens_managed_by": "OpenClaw native CLI or user environment, not Paideia public artifacts",
        },
        "source_docs_checked": OPENCLAW_REFERENCE_URLS,
    }
    _write_json(output_path, handoff)
    return handoff


def _review_existing_openclaw_config(
    *,
    existing_config_path: Path,
    config_action: str,
    config_patch: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    if config_action not in CONFIG_ACTIONS:
        raise ValueError(f"config_action must be one of: {', '.join(sorted(CONFIG_ACTIONS))}")

    review_path = output_dir / "openclaw_existing_config_review.json"
    redacted_snapshot_path = output_dir / "openclaw_existing_config.redacted.json"
    merge_preview_path = output_dir / "openclaw_config_merge.preview.json"
    reset_plan_path = output_dir / "openclaw_config_reset_plan.json"
    base = {
        "schema": OPENCLAW_EXISTING_CONFIG_REVIEW_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_docs_checked": [
            "https://docs.openclaw.ai/start/wizard-cli-flow",
            "https://docs.openclaw.ai/configuration",
        ],
        "path": str(existing_config_path),
        "exists": existing_config_path.exists(),
        "requested_action": config_action,
        "destructive_reset_performed": False,
        "secret_values_stored": False,
        "artifacts": {"review": str(review_path)},
    }
    if not existing_config_path.exists():
        review = {
            **base,
            "status": "not_found",
            "recommended_action": "create_or_review_patch",
            "operator_message": "No existing OpenClaw config was found at the selected path.",
        }
        _write_json(review_path, review)
        return review

    try:
        existing = _read_json(existing_config_path)
    except Exception as exc:
        review = {
            **base,
            "status": "invalid_json",
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "recommended_action": "run_openclaw_doctor_before_paideia_merge",
            "operator_message": "OpenClaw wizard behavior stops on invalid config; Paideia only wrote this review file.",
        }
        _write_json(review_path, review)
        return review

    redacted_existing = _redact_config(existing)
    _write_json(redacted_snapshot_path, redacted_existing)
    top_level_keys = sorted(str(key) for key in existing.keys())
    legacy_key_candidates = sorted(
        key for key in top_level_keys if key in {"provider", "providers", "modelProvider", "chatProvider"}
    )

    artifacts = {
        "review": str(review_path),
        "redacted_snapshot": str(redacted_snapshot_path),
    }
    status = "kept_for_manual_review"
    operator_message = "Existing config was detected and left untouched."

    if config_action == "modify":
        merged_preview = _deep_merge(redacted_existing, config_patch["openclaw_json_patch"])
        preview = {
            "schema": OPENCLAW_CONFIG_MERGE_PREVIEW_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "action": "modify_preview_only",
            "source_config": str(existing_config_path),
            "base_config_is_redacted": True,
            "secret_values_stored": False,
            "merge_strategy": "deep_merge_paideia_patch_into_redacted_existing_config",
            "not_directly_applyable_if_existing_config_had_secrets": True,
            "base_top_level_keys": top_level_keys,
            "paideia_patch": config_patch["openclaw_json_patch"],
            "preview_config_redacted": merged_preview,
        }
        _write_json(merge_preview_path, preview)
        artifacts["merge_preview"] = str(merge_preview_path)
        status = "modify_preview_written"
        operator_message = "A redacted merge preview was written; review before manually applying to OpenClaw."
    elif config_action == "reset":
        reset_plan = {
            "schema": OPENCLAW_CONFIG_RESET_PLAN_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "action": "reset_plan_only",
            "source_config": str(existing_config_path),
            "backup_recommendation": str(existing_config_path.with_suffix(".json.bak")),
            "destructive_reset_performed": False,
            "secret_values_stored": False,
            "replacement_patch": config_patch["openclaw_json_patch"],
            "operator_steps": [
                "Back up the existing OpenClaw config.",
                "Run OpenClaw doctor or config schema validation.",
                "Apply only the reviewed replacement patch if reset is still intended.",
            ],
        }
        _write_json(reset_plan_path, reset_plan)
        artifacts["reset_plan"] = str(reset_plan_path)
        status = "reset_plan_written"
        operator_message = "Reset was requested, but Paideia wrote a plan only and did not delete or overwrite the config."

    review = {
        **base,
        "status": status,
        "valid_json": True,
        "top_level_keys": top_level_keys,
        "legacy_key_candidates": legacy_key_candidates,
        "recommended_action": "review_then_apply_manually",
        "operator_message": operator_message,
        "artifacts": artifacts,
    }
    _write_json(review_path, review)
    return review


def build_openclaw_runtime_bundle(
    employment_record_path: Path,
    *,
    channels: list[str] | None = None,
    channel_models: list[str] | None = None,
    bindings: list[str] | None = None,
    import_manifest_path: Path | None = None,
    output_dir: Path | None = None,
    bind_host: str = "127.0.0.1",
    port: int = 8722,
    existing_openclaw_config_path: Path | None = None,
    config_action: str = "modify",
) -> dict[str, Any]:
    employment_record_path = employment_record_path.resolve()
    employment = _load_employment(employment_record_path)
    agent_key = _safe_agent_key(employment)
    imported_channel_models, imported_bindings = _load_openclaw_import_hints(
        import_manifest_path,
        default_agent_id=agent_key,
    )
    explicit_channel_models = _parse_channel_model_specs(channel_models)
    channel_model_overrides = _merge_channel_model_maps(imported_channel_models, explicit_channel_models)
    explicit_bindings = _parse_binding_specs(bindings, default_agent_id=agent_key)
    imported_and_explicit_bindings = [*imported_bindings, *explicit_bindings]
    extra_channels = [
        *_channels_from_channel_models(channel_model_overrides),
        *_channels_from_bindings(imported_and_explicit_bindings),
    ]
    selected_channels = _normalize_channels(employment, _dedupe(list(channels or []) + extra_channels))
    provider_id = _infer_provider_id(employment)
    provider = find_openclaw_provider(provider_id)
    if provider is None:
        raise ValueError(f"Unsupported OpenClaw provider: {provider_id}")
    model = _model_selector(employment, provider_id)
    channel_model_map = _merge_channel_model_maps(
        {channel_id: {"*": model} for channel_id in selected_channels},
        channel_model_overrides,
    )
    openclaw_bindings = imported_and_explicit_bindings or _default_bindings_for_channels(
        selected_channels,
        agent_id=agent_key,
    )

    output_dir = (output_dir or employment_record_path.parent / "openclaw_runtime_bundle").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    gateway_config_path = output_dir / "openclaw_gateway_config.json"
    access_config_path = output_dir / "openclaw_channel_access_config.json"
    provider_doctor_path = output_dir / "openclaw_provider_doctor.json"
    channel_connector_catalog_path = output_dir / "openclaw_channel_connectors.json"
    channel_doctor_path = output_dir / "openclaw_channel_doctor.json"
    llm_health_path = output_dir / "llm_service_health.json"
    gateway_llm_doctor_path = output_dir / "openclaw_gateway_llm_doctor.json"
    config_patch_path = output_dir / "openclaw_config_patch.json"
    native_handoff_path = output_dir / "openclaw_native_handoff.json"
    env_template_path = output_dir / "openclaw.env.example.ps1"
    manifest_path = output_dir / "openclaw_runtime_bundle.json"

    gateway_config = build_openclaw_gateway_config(
        employment_record_path,
        channels=selected_channels,
        bind_host=bind_host,
        port=port,
        output_path=gateway_config_path,
    )
    build_openclaw_channel_access_config(
        channels=selected_channels,
        output_path=access_config_path,
    )
    provider_doctor = doctor_openclaw_provider_connectors(
        providers=[provider_id],
        output_path=provider_doctor_path,
    )
    channel_connector_catalog = build_openclaw_channel_connector_catalog(
        channels=selected_channels,
        output_path=channel_connector_catalog_path,
    )
    channel_doctor = doctor_openclaw_channel_connectors(
        channels=selected_channels,
        output_path=channel_doctor_path,
    )
    llm_health = build_llm_service_health(employment.get("llm_service", {}))
    _write_json(llm_health_path, llm_health)

    delivery_channels = [channel for channel in selected_channels if channel in SUPPORTED_DELIVERY_CHANNELS]
    delivery_config_path: Path | None = None
    if delivery_channels:
        delivery_config_path = output_dir / "openclaw_channel_delivery_config.json"
        build_openclaw_channel_delivery_config(
            channels=delivery_channels,
            output_path=delivery_config_path,
        )

    provider_envs = _provider_env_vars(provider_doctor)
    channel_envs = _channel_env_vars(channel_doctor)
    config_patch = _build_config_patch(
        employment_record_path=employment_record_path,
        employment=employment,
        provider_id=provider_id,
        model_selector=model,
        provider=provider,
        channels=selected_channels,
        bind_host=bind_host,
        port=port,
        provider_env_vars=provider_envs,
        channel_doctor=channel_doctor,
        channel_model_map=channel_model_map,
        bindings=openclaw_bindings,
    )
    _write_json(config_patch_path, config_patch)
    gateway_llm_doctor: dict[str, Any] | None = None
    if employment.get("llm_runtime", {}).get("engine") == "openclaw_gateway_http":
        gateway_llm_doctor = doctor_openclaw_gateway_llm(
            employment_record_path,
            output_path=gateway_llm_doctor_path,
            config_patch_path=config_patch_path,
        )
    _write_text(
        env_template_path,
        _build_env_template(
            provider_id=provider_id,
            channels=selected_channels,
            provider_env_vars=provider_envs,
            channel_env_vars=channel_envs,
            bind_host=bind_host,
            port=port,
        ),
    )
    selected_existing_config_path = (
        existing_openclaw_config_path.expanduser().resolve()
        if existing_openclaw_config_path is not None
        else _default_openclaw_config_path().expanduser()
    )
    existing_config_review = _review_existing_openclaw_config(
        existing_config_path=selected_existing_config_path,
        config_action=config_action,
        config_patch=config_patch,
        output_dir=output_dir,
    )
    native_handoff = _build_native_handoff(
        employment_record_path=employment_record_path,
        employment=employment,
        provider_id=provider_id,
        model_selector=model,
        channels=selected_channels,
        bind_host=bind_host,
        port=port,
        config_patch_path=config_patch_path,
        existing_config_path=selected_existing_config_path,
        output_path=native_handoff_path,
    )

    artifacts = {
        "manifest": str(manifest_path),
        "openclaw_config_patch": str(config_patch_path),
        "openclaw_native_handoff": str(native_handoff_path),
        "openclaw_env_template": str(env_template_path),
        "existing_openclaw_config_review": existing_config_review["artifacts"]["review"],
        "gateway_config": str(gateway_config_path),
        "channel_access_config": str(access_config_path),
        "provider_doctor": str(provider_doctor_path),
        "channel_connector_catalog": str(channel_connector_catalog_path),
        "channel_doctor": str(channel_doctor_path),
        "llm_service_health": str(llm_health_path),
    }
    if gateway_llm_doctor is not None:
        artifacts["gateway_llm_doctor"] = str(gateway_llm_doctor_path)
    for key, value in existing_config_review.get("artifacts", {}).items():
        if key != "review":
            artifacts[f"existing_openclaw_config_{key}"] = value
    if delivery_config_path is not None:
        artifacts["channel_delivery_config"] = str(delivery_config_path)

    bundle = {
        "schema": OPENCLAW_RUNTIME_BUNDLE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_owner_review",
        "employment": {
            "employment_id": employment["employment_id"],
            "agent": employment["agent"],
            "employment_record": str(employment_record_path),
        },
        "selection": {
            "provider_id": provider_id,
            "model": model,
            "channels": selected_channels,
            "channel_model_map": channel_model_map,
            "bindings": openclaw_bindings,
            "chat_surface": employment.get("chat_surface", {}),
            "bind_host": bind_host,
            "port": port,
            "config_action": config_action,
            "existing_openclaw_config_path": str(selected_existing_config_path),
            "import_manifest_path": str(import_manifest_path.expanduser().resolve()) if import_manifest_path else None,
        },
        "readiness": {
            "llm_service_health": llm_health,
            "provider_doctor_summary": provider_doctor["summary"],
            "channel_connector_summary": channel_connector_catalog["summary"],
            "channel_doctor_summary": channel_doctor["summary"],
            "gateway_llm_doctor": gateway_llm_doctor,
            "existing_openclaw_config": {
                "status": existing_config_review["status"],
                "exists": existing_config_review["exists"],
                "requested_action": existing_config_review["requested_action"],
                "destructive_reset_performed": existing_config_review["destructive_reset_performed"],
            },
            "secret_values_stored": False,
        },
        "artifacts": artifacts,
        "next_commands": {
            "doctor_provider": (
                "ai22b-talent-foundry doctor-openclaw-provider-connectors "
                f"--provider {provider_id} --output {provider_doctor_path}"
            ),
            "doctor_channels": (
                "ai22b-talent-foundry doctor-openclaw-channel-connectors "
                + " ".join(f"--channel {channel}" for channel in selected_channels)
                + f" --output {channel_doctor_path}"
            ),
            "run_channel_gateway": (
                "ai22b-talent-foundry run-openclaw-channel-gateway-server "
                f"--employment-record {employment_record_path} "
                + " ".join(f"--channel {channel}" for channel in selected_channels)
                + f" --access-config {access_config_path} --bind-host {bind_host} --port {port}"
            ),
            "run_webchat": (
                "ai22b-talent-foundry run-openclaw-webchat-server "
                f"--employment-record {employment_record_path} --bind-host {bind_host} --port {port}"
            ),
            "check_llm_service": (
                "ai22b-talent-foundry check-llm-service "
                f"--llm-service {employment.get('llm_service', {}).get('service_id', '')} "
                f"--llm-model {employment.get('llm_service', {}).get('selected_model') or ''} "
                f"--output {llm_health_path}"
            ),
            "doctor_gateway_llm": (
                "ai22b-talent-foundry doctor-openclaw-gateway-llm "
                f"--employment-record {employment_record_path} "
                f"--config-patch {config_patch_path} "
                f"--output {gateway_llm_doctor_path}"
            ),
            "probe_gateway_llm": (
                "ai22b-talent-foundry doctor-openclaw-gateway-llm "
                f"--employment-record {employment_record_path} "
                "--probe-gateway --probe-chat "
                f"--output {output_dir / 'openclaw_gateway_llm_doctor.live.json'}"
            ),
            "review_openclaw_merge": (
                "Review "
                f"{_relative_or_name(Path(artifacts['openclaw_config_patch']), output_dir)} and "
                f"{_relative_or_name(Path(artifacts['existing_openclaw_config_review']), output_dir)} before applying to OpenClaw."
            ),
            "openclaw_native_setup": native_handoff["operator_commands"]["setup_workspace"],
            "openclaw_native_gateway": native_handoff["operator_commands"]["run_gateway"],
            "rebuild_with_channel_model": (
                "ai22b-talent-foundry build-openclaw-runtime-bundle "
                f"--employment-record {employment_record_path} --channel <channel> "
                "--channel-model <channel>:<conversation>=<provider/model> "
                f"--output-dir {output_dir}"
            ),
        },
        "openclaw_reference": {
            "provider_catalog": openclaw_provider_manifest(),
            "channel_catalog": openclaw_channel_manifest(),
            "docs": OPENCLAW_REFERENCE_URLS,
        },
        "notes": [
            "Review openclaw_config_patch.json before merging into an existing OpenClaw config.",
            "Review openclaw_native_handoff.json when you want OpenClaw itself to own provider auth, channel plugins, gateway sessions, and platform delivery.",
            "Existing OpenClaw config review follows Keep/Modify/Reset semantics and never overwrites the config.",
            "Set secrets in the local shell using openclaw.env.example.ps1; real values are never written.",
            "Channel access config starts deny-by-default and needs allowlisted senders or conversations before raw platform events are routed.",
        ],
        "existing_openclaw_config_review": existing_config_review,
        "openclaw_native_handoff": native_handoff,
        "generated_gateway_config": gateway_config,
    }
    if gateway_llm_doctor is None:
        bundle["next_commands"].pop("doctor_gateway_llm", None)
        bundle["next_commands"].pop("probe_gateway_llm", None)
    _write_json(manifest_path, bundle)
    return bundle
