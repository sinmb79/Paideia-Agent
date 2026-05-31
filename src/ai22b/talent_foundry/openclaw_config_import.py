from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.channel_connectors import doctor_openclaw_channel_connectors
from ai22b.talent_foundry.openclaw_compat import (
    find_openclaw_channel,
    find_openclaw_provider,
    normalize_openclaw_channel_id,
)
from ai22b.talent_foundry.openclaw_runtime_bundle import OPENCLAW_REFERENCE_URLS
from ai22b.talent_foundry.provider_connectors import doctor_openclaw_provider_connectors


OPENCLAW_CONFIG_IMPORT_SCHEMA = "ai22b-openclaw-config-import/v1"
OPENCLAW_CONFIG_IMPORT_SETUP_PLAN_SCHEMA = "ai22b-openclaw-config-import-setup-plan/v1"

IGNORED_CHANNEL_CONFIG_KEYS = {
    "default",
    "defaults",
    "model",
    "modelbychannel",
    "model-by-channel",
    "models",
    "router",
    "routing",
}

SECRET_KEY_PATTERNS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "bot_token",
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


def _secret_like_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.casefold())
    return any(pattern in normalized for pattern in SECRET_KEY_PATTERNS)


def _redact(value: Any, *, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if _secret_like_key(str(key)) else _redact(item, parent_key=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, parent_key=parent_key) for item in value]
    if parent_key and _secret_like_key(parent_key):
        return "<redacted>"
    return value


def _walk_secret_refs(value: Any, *, path: str = "") -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            if _secret_like_key(str(key)):
                refs.append(
                    {
                        "path": item_path,
                        "source_key": str(key),
                        "value_present_in_source": bool(item),
                        "secret_value_stored": False,
                    }
                )
            refs.extend(_walk_secret_refs(item, path=item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            refs.extend(_walk_secret_refs(item, path=f"{path}[{index}]"))
    return refs


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_primary_model(config: dict[str, Any]) -> str | None:
    agents = _as_dict(config.get("agents"))
    defaults = _as_dict(agents.get("defaults"))
    model = defaults.get("model")
    if isinstance(model, str):
        return model
    if isinstance(model, dict):
        primary = model.get("primary") or model.get("default") or model.get("model")
        if primary:
            return str(primary)
    root_model = config.get("model")
    if isinstance(root_model, str):
        return root_model
    models = _as_dict(config.get("models"))
    default_model = models.get("default")
    if isinstance(default_model, str):
        return default_model
    if isinstance(default_model, dict):
        candidate = default_model.get("model") or default_model.get("primary")
        if candidate:
            return str(candidate)
    return None


def _provider_from_model(model: str | None) -> str | None:
    if model and "/" in model:
        return model.split("/", 1)[0].strip()
    return None


def _extract_model_provider_ids(config: dict[str, Any], primary_provider: str | None) -> list[str]:
    ids: list[str] = []
    if primary_provider:
        ids.append(primary_provider)
    models = _as_dict(config.get("models"))
    providers = _as_dict(models.get("providers"))
    ids.extend(str(key) for key in providers.keys())
    model_providers = _as_dict(config.get("modelProviders"))
    ids.extend(str(key) for key in model_providers.keys())
    model_by_channel, _diagnostics = _extract_model_by_channel(config)
    for target_map in model_by_channel.values():
        for model_selector in target_map.values():
            provider_id = _provider_from_model(model_selector)
            if provider_id:
                ids.append(provider_id)
    return _dedupe(ids)


def _channel_from_key(key: str) -> tuple[str | None, str]:
    normalized = normalize_openclaw_channel_id(key)
    if normalized in IGNORED_CHANNEL_CONFIG_KEYS:
        return None, "ignored_config_key"
    channel = find_openclaw_channel(normalized)
    if channel is None:
        return None, "unsupported_or_unknown_channel"
    return str(channel["channel_id"]), "supported"


def _extract_channels(config: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    supported: list[str] = []
    diagnostics: list[dict[str, Any]] = []
    channels = _as_dict(config.get("channels"))
    for key in channels.keys():
        channel_id, status = _channel_from_key(str(key))
        diagnostics.append({"source": f"channels.{key}", "channel_id": channel_id, "status": status})
        if channel_id:
            supported.append(channel_id)
    bindings = config.get("bindings")
    if isinstance(bindings, list):
        for index, binding in enumerate(bindings):
            match = _as_dict(_as_dict(binding).get("match"))
            raw_channel = match.get("channel") or match.get("provider") or _as_dict(binding).get("channel")
            if raw_channel:
                channel_id, status = _channel_from_key(str(raw_channel))
                diagnostics.append(
                    {"source": f"bindings[{index}].match.channel", "channel_id": channel_id, "status": status}
                )
                if channel_id:
                    supported.append(channel_id)
    model_by_channel, _model_diagnostics = _extract_model_by_channel(config)
    supported.extend(model_by_channel.keys())
    return _dedupe(supported), diagnostics


def _model_selector_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        candidate = value.get("model") or value.get("primary") or value.get("default")
        if candidate:
            return str(candidate).strip() or None
    return None


def _extract_model_by_channel(config: dict[str, Any]) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    model_by_channel: dict[str, dict[str, str]] = {}
    diagnostics: list[dict[str, Any]] = []
    channels = _as_dict(config.get("channels"))
    candidate_sources = [
        ("channels.modelByChannel", channels.get("modelByChannel")),
        ("channels.model-by-channel", channels.get("model-by-channel")),
        ("channels.models", channels.get("models")),
        ("modelByChannel", config.get("modelByChannel")),
    ]
    for source, mapping in candidate_sources:
        if not isinstance(mapping, dict):
            continue
        for raw_channel, targets in mapping.items():
            channel_id, status = _channel_from_key(str(raw_channel))
            diagnostic = {"source": f"{source}.{raw_channel}", "channel_id": channel_id, "status": status}
            if not channel_id:
                diagnostics.append(diagnostic)
                continue

            target_map: dict[str, str] = {}
            direct_model = _model_selector_from_value(targets)
            if direct_model:
                target_map["*"] = direct_model
            elif isinstance(targets, dict):
                for raw_target, raw_model in targets.items():
                    model_selector = _model_selector_from_value(raw_model)
                    if model_selector:
                        target_map[str(raw_target)] = model_selector

            diagnostic["target_count"] = len(target_map)
            diagnostics.append(diagnostic)
            if target_map:
                model_by_channel.setdefault(channel_id, {}).update(target_map)
    return model_by_channel, diagnostics


def _sanitize_match(match: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    allowed_keys = {
        "accountId",
        "channel",
        "channelId",
        "conversation",
        "guildId",
        "peer",
        "provider",
        "roles",
        "roomId",
        "teamId",
        "threadId",
        "topicId",
    }
    for key, value in match.items():
        if str(key) not in allowed_keys:
            continue
        if _secret_like_key(str(key)):
            continue
        if str(key) in {"channel", "provider"}:
            channel_id, status = _channel_from_key(str(value))
            if status == "supported" and channel_id:
                safe["channel"] = channel_id
            continue
        if isinstance(value, dict):
            nested = {
                str(nested_key): str(nested_value)
                for nested_key, nested_value in value.items()
                if str(nested_key) in {"id", "kind", "name", "type"} and not _secret_like_key(str(nested_key))
            }
            if nested:
                safe[str(key)] = nested
        elif isinstance(value, list):
            safe[str(key)] = [str(item) for item in value if str(item).strip()]
        elif value is not None:
            safe[str(key)] = str(value)
    return safe


def _extract_bindings(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bindings = config.get("bindings")
    if not isinstance(bindings, list):
        return [], []

    normalized: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for index, raw_binding in enumerate(bindings):
        binding = _as_dict(raw_binding)
        match = _as_dict(binding.get("match"))
        raw_channel = match.get("channel") or match.get("provider") or binding.get("channel")
        channel_id = None
        status = "missing_channel"
        if raw_channel:
            channel_id, status = _channel_from_key(str(raw_channel))
        diagnostics.append(
            {
                "source": f"bindings[{index}]",
                "channel_id": channel_id,
                "status": status,
                "secret_values_stored": False,
            }
        )
        if not channel_id:
            continue
        safe_match = _sanitize_match({**match, "channel": channel_id})
        agent_id = binding.get("agentId") or binding.get("agent_id") or binding.get("agent")
        if not agent_id:
            agent_id = "main"
        normalized.append(
            {
                "source": f"bindings[{index}]",
                "match": safe_match,
                "channel_id": channel_id,
                "agent_id": str(agent_id),
                "secret_values_stored": False,
            }
        )
    return normalized, diagnostics


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


def _build_setup_plan(
    *,
    config_path: Path,
    primary_model: str | None,
    primary_provider: str | None,
    provider_ids: list[str],
    channel_ids: list[str],
    model_by_channel: dict[str, dict[str, str]],
    bindings: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    provider_doctor = doctor_openclaw_provider_connectors(providers=provider_ids or None)
    channel_doctor = doctor_openclaw_channel_connectors(channels=channel_ids or None)
    return {
        "schema": OPENCLAW_CONFIG_IMPORT_SETUP_PLAN_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_openclaw_config": str(config_path),
        "selection": {
            "primary_model": primary_model,
            "primary_provider_id": primary_provider,
            "provider_ids": provider_ids,
            "channel_ids": channel_ids,
            "model_by_channel": model_by_channel,
            "binding_count": len(bindings),
        },
        "provider_setup": [
            {
                "provider_id": item["provider_id"],
                "runtime_status": item["runtime_status"],
                "ready_for_live_llm": item["ready_for_live_llm"],
                "next_step": item["next_step"],
                "checks": item["checks"],
            }
            for item in provider_doctor["results"]
        ],
        "channel_setup": [
            {
                "channel_id": item["channel_id"],
                "connector_status": item["connector_status"],
                "ready_for_live_delivery": item["ready_for_live_delivery"],
                "generic_normalized_gateway_ready": item["generic_normalized_gateway_ready"],
                "next_step": item["next_step"],
                "checks": item["checks"],
            }
            for item in channel_doctor["results"]
        ],
        "recommended_paideia_commands": {
            "hire_with_imported_model": (
                "ai22b-talent-foundry hire-installed --installed-manifest <installed_agent_manifest.json> "
                f"--llm-service {primary_model or primary_provider or '<provider/model>'} "
                f"--chat-surface openclaw-channel-{channel_ids[0] if channel_ids else 'webchat'}"
            ),
            "build_runtime_bundle": (
                "ai22b-talent-foundry build-openclaw-runtime-bundle "
                "--employment-record <employment_record.json> "
                + " ".join(f"--channel {channel}" for channel in (channel_ids or ["webchat"]))
                + " "
                + " ".join(
                    f"--channel-model {channel}:{target}={model}"
                    for channel, targets in model_by_channel.items()
                    for target, model in targets.items()
                )
                + f" --existing-openclaw-config {config_path} --config-action modify "
                + f"--output-dir {output_dir / 'runtime_bundle'}"
            ),
        },
        "secret_values_stored": False,
        "source_docs_checked": OPENCLAW_REFERENCE_URLS,
    }


def import_openclaw_config(
    config_path: Path,
    *,
    output_dir: Path,
) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "paideia_openclaw_config_import.json"
    redacted_snapshot_path = output_dir / "openclaw_config.redacted.json"
    setup_plan_path = output_dir / "openclaw_import_setup_plan.json"
    suggested_answers_path = output_dir / "paideia_onboarding.answers.suggested.json"

    if not config_path.exists():
        result = {
            "schema": OPENCLAW_CONFIG_IMPORT_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "not_found",
            "source_openclaw_config": str(config_path),
            "secret_values_stored": False,
            "artifacts": {"manifest": str(manifest_path)},
        }
        _write_json(manifest_path, result)
        return result

    try:
        config = _read_json(config_path)
    except Exception as exc:
        result = {
            "schema": OPENCLAW_CONFIG_IMPORT_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "invalid_json",
            "source_openclaw_config": str(config_path),
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "secret_values_stored": False,
            "artifacts": {"manifest": str(manifest_path)},
        }
        _write_json(manifest_path, result)
        return result

    redacted_config = _redact(config)
    _write_json(redacted_snapshot_path, redacted_config)

    primary_model = _extract_primary_model(config)
    primary_provider = _provider_from_model(primary_model)
    provider_ids = _extract_model_provider_ids(config, primary_provider)
    supported_providers = [provider_id for provider_id in provider_ids if find_openclaw_provider(provider_id)]
    unsupported_providers = [provider_id for provider_id in provider_ids if not find_openclaw_provider(provider_id)]
    channel_ids, channel_diagnostics = _extract_channels(config)
    model_by_channel, model_by_channel_diagnostics = _extract_model_by_channel(config)
    bindings, binding_diagnostics = _extract_bindings(config)
    setup_plan = _build_setup_plan(
        config_path=config_path,
        primary_model=primary_model,
        primary_provider=primary_provider,
        provider_ids=supported_providers or ([primary_provider] if primary_provider else []),
        channel_ids=channel_ids,
        model_by_channel=model_by_channel,
        bindings=bindings,
        output_dir=output_dir,
    )
    _write_json(setup_plan_path, setup_plan)

    suggested_answers = {
        "schema": "ai22b-paideia-openclaw-imported-answers/v1",
        "source_openclaw_config": str(config_path),
        "llm_service": primary_model or primary_provider,
        "chat_surface": f"openclaw-channel-{channel_ids[0]}" if channel_ids else "openclaw-channel-webchat",
        "channels": [f"openclaw-channel-{channel_id}" for channel_id in channel_ids],
        "openclaw_model_by_channel": model_by_channel,
        "openclaw_bindings": bindings,
        "secret_values_stored": False,
    }
    _write_json(suggested_answers_path, suggested_answers)

    result = {
        "schema": OPENCLAW_CONFIG_IMPORT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "import_ready",
        "source_openclaw_config": str(config_path),
        "detected": {
            "primary_model": primary_model,
            "primary_provider_id": primary_provider,
            "supported_provider_ids": supported_providers,
            "unsupported_provider_ids": unsupported_providers,
            "channel_ids": channel_ids,
            "channel_diagnostics": channel_diagnostics,
            "model_by_channel": model_by_channel,
            "model_by_channel_diagnostics": model_by_channel_diagnostics,
            "bindings": bindings,
            "binding_diagnostics": binding_diagnostics,
            "secret_references": _walk_secret_refs(config),
        },
        "paideia_selection": {
            "llm_service": primary_model or primary_provider,
            "chat_surface": suggested_answers["chat_surface"],
            "channels": suggested_answers["channels"],
            "model_by_channel": model_by_channel,
            "bindings": bindings,
            "provider_supported": bool(primary_provider and find_openclaw_provider(primary_provider)),
            "all_detected_channels_supported": all(item["status"] != "unsupported_or_unknown_channel" for item in channel_diagnostics),
        },
        "artifacts": {
            "manifest": str(manifest_path),
            "redacted_snapshot": str(redacted_snapshot_path),
            "setup_plan": str(setup_plan_path),
            "suggested_answers": str(suggested_answers_path),
        },
        "source_docs_checked": OPENCLAW_REFERENCE_URLS,
        "secret_values_stored": False,
    }
    _write_json(manifest_path, result)
    return result
