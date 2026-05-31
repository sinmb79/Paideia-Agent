from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.channel_connectors import build_openclaw_channel_connector_catalog
from ai22b.talent_foundry.openclaw_compat import find_openclaw_channel


OPENCLAW_CHANNEL_PAIRING_DOCTOR_SCHEMA = "ai22b-openclaw-channel-pairing-doctor/v1"


PAIRING_KIND_BY_STATUS = {
    "legacy_openclaw_config_migration_required": "legacy_migration",
    "external_plugin_required_qr_pairing": "qr_session_pairing",
    "local_bridge_required": "local_cli_or_service_bridge",
    "external_plugin_required_enterprise": "enterprise_bot_or_tenant_setup",
    "openclaw_bundled_imsg_bridge_required": "native_imsg_bridge",
    "openclaw_synthetic_qa_plugin_required": "synthetic_test_channel",
    "external_plugin_required": "external_plugin_setup",
    "paideia_direct_ingress_delivery_ready": "bot_token_or_webhook",
    "paideia_loopback_ready": "local_loopback",
}

SESSION_ENV_VARS_BY_CHANNEL = {
    "whatsapp": ["WHATSAPP_SESSION_DIR"],
    "wechat": ["WECHAT_SESSION_DIR"],
    "zalo-personal": ["ZALO_PERSONAL_SESSION_DIR"],
}

TOOL_CANDIDATES_BY_CHANNEL = {
    "signal": [("SIGNAL_CLI_PATH", "signal-cli")],
    "imessage": [("IMSG_CLI_PATH", "imsg")],
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item).strip()
        if value and value.casefold() not in seen:
            result.append(value)
            seen.add(value.casefold())
    return result


def _env_alternatives(env_var: str) -> list[str]:
    return [part.strip() for part in str(env_var).split(" or ") if part.strip()]


def _path_exists_from_env(env_var: str) -> bool | None:
    value = os.environ.get(env_var)
    if not value:
        return None
    try:
        return Path(os.path.expandvars(value)).expanduser().exists()
    except (OSError, RuntimeError, ValueError):
        return False


def _env_check(env_var: str) -> dict[str, Any]:
    alternatives = _env_alternatives(env_var)
    present = any(os.environ.get(item) for item in alternatives)
    check: dict[str, Any] = {
        "id": f"env:{env_var}",
        "kind": "environment_secret_or_path",
        "passed": present,
        "secret_value_stored": False,
        "message": "configured" if present else f"{env_var} is not set in this shell.",
    }
    path_results: list[dict[str, Any]] = []
    for item in alternatives:
        if item.endswith(("_DIR", "_PATH")):
            path_exists = _path_exists_from_env(item)
            if path_exists is not None:
                path_results.append(
                    {
                        "env_var": item,
                        "path_exists": path_exists,
                        "path_value_stored": False,
                    }
                )
    if path_results:
        check["path_checks"] = path_results
    return check


def _tool_checks(channel_id: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for env_var, binary in TOOL_CANDIDATES_BY_CHANNEL.get(channel_id, []):
        env_path_exists = _path_exists_from_env(env_var)
        binary_on_path = shutil.which(binary) is not None
        checks.append(
            {
                "id": f"tool:{binary}",
                "kind": "local_binary_or_env_path",
                "passed": bool(binary_on_path or env_path_exists),
                "binary_on_path": binary_on_path,
                "env_path_var": env_var,
                "env_path_configured": bool(os.environ.get(env_var)),
                "env_path_exists": env_path_exists,
                "path_value_stored": False,
                "message": (
                    f"{binary} is available."
                    if binary_on_path or env_path_exists
                    else f"{binary} was not found on PATH and {env_var} is not a valid local path."
                ),
            }
        )
    return checks


def _pairing_kind(connector_status: str) -> str:
    return PAIRING_KIND_BY_STATUS.get(connector_status, "external_plugin_setup")


def _pairing_status(*, pairing_kind: str, checks: list[dict[str, Any]], connector_status: str) -> str:
    required_passed = all(check.get("passed") for check in checks)
    if pairing_kind == "local_loopback":
        return "ready"
    if pairing_kind in {"legacy_migration", "synthetic_test_channel"}:
        return "manual_review"
    if connector_status == "paideia_direct_ingress_delivery_ready":
        return "ready_for_live_when_env_configured" if required_passed else "needs_env_or_webhook"
    if pairing_kind == "qr_session_pairing":
        return "ready_for_qr_pairing" if required_passed else "needs_session_dir_before_qr"
    if pairing_kind in {"local_cli_or_service_bridge", "native_imsg_bridge"}:
        return "ready_for_bridge_probe" if required_passed else "needs_local_bridge_setup"
    if pairing_kind == "enterprise_bot_or_tenant_setup":
        return "ready_for_enterprise_bot_review" if required_passed else "needs_enterprise_credentials"
    return "ready_for_plugin_review" if required_passed else "needs_plugin_setup"


def _next_actions(channel_id: str, pairing_kind: str) -> list[str]:
    base = [
        f"ai22b-talent-foundry doctor-openclaw-channel-connectors --channel {channel_id} --output channel_connector_doctor.json",
        f"ai22b-talent-foundry build-openclaw-channel-access-config --channel {channel_id} --output channel_access_config.json",
        f"openclaw channels add --channel {channel_id} --help",
        f"openclaw channels status --probe --channel {channel_id} --json",
    ]
    if pairing_kind == "qr_session_pairing":
        base.insert(
            2,
            "Complete the QR login in OpenClaw or the selected channel plugin, then keep the session directory local and out of git.",
        )
    elif pairing_kind == "local_cli_or_service_bridge":
        base.insert(2, "Install and link the local CLI/service bridge, then run the channel status probe before live routing.")
    elif pairing_kind == "native_imsg_bridge":
        base.insert(2, "Verify the Messages-signed-in Mac and imsg permissions before routing private iMessage traffic.")
    elif pairing_kind == "enterprise_bot_or_tenant_setup":
        base.insert(2, "Review tenant permissions, bot credentials, and group allowlists with the workspace owner.")
    elif pairing_kind == "legacy_migration":
        base.insert(2, "Migrate legacy BlueBubbles settings to the current iMessage/imsg path before new setup.")
    return base


def _security_notes(pairing_kind: str) -> list[str]:
    notes = [
        "No token, QR session, cookie, phone number, or absolute local path value is serialized.",
        "Inbound channel access should stay deny-by-default until sender and conversation allowlists are reviewed.",
    ]
    if pairing_kind == "qr_session_pairing":
        notes.append("QR session directories are local private runtime state and must not be committed.")
    if pairing_kind in {"local_cli_or_service_bridge", "native_imsg_bridge"}:
        notes.append("Local bridge probes can expose account state; run them only after owner approval.")
    return notes


def doctor_openclaw_channel_pairing(
    *,
    channels: list[str] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    selected_channels = channels or []
    normalized: list[str] = []
    for raw_channel in selected_channels:
        channel = find_openclaw_channel(raw_channel)
        if channel is None:
            raise ValueError(f"Unsupported OpenClaw channel: {raw_channel}")
        normalized.append(str(channel["channel_id"]))
    catalog = build_openclaw_channel_connector_catalog(channels=normalized or None)
    results: list[dict[str, Any]] = []
    for channel in catalog["channels"]:
        channel_id = str(channel["channel_id"])
        connector_status = str(channel["connector_status"])
        pairing_kind = _pairing_kind(connector_status)
        checks = [_env_check(env_var) for env_var in channel.get("required_env_vars", [])]
        checks.extend(_tool_checks(channel_id))
        session_env_vars = SESSION_ENV_VARS_BY_CHANNEL.get(channel_id, [])
        results.append(
            {
                "channel_id": channel_id,
                "label": channel.get("label"),
                "transport": channel.get("transport"),
                "connector_status": connector_status,
                "pairing_kind": pairing_kind,
                "pairing_status": _pairing_status(
                    pairing_kind=pairing_kind,
                    checks=checks,
                    connector_status=connector_status,
                ),
                "needs_openclaw_or_external_plugin": connector_status
                not in {"paideia_direct_ingress_delivery_ready", "paideia_loopback_ready"},
                "session_state": {
                    "required": bool(session_env_vars),
                    "env_vars": session_env_vars,
                    "session_values_stored": False,
                },
                "checks": checks,
                "next_actions": _next_actions(channel_id, pairing_kind),
                "security_notes": _security_notes(pairing_kind),
                "source_connector_setup": channel.get("setup"),
            }
        )
    summary = {
        "channel_count": len(results),
        "ready_or_probeable_count": sum(
            1
            for item in results
            if item["pairing_status"]
            in {
                "ready",
                "ready_for_live_when_env_configured",
                "ready_for_qr_pairing",
                "ready_for_bridge_probe",
                "ready_for_enterprise_bot_review",
                "ready_for_plugin_review",
            }
        ),
        "needs_qr_pairing_count": sum(1 for item in results if item["pairing_kind"] == "qr_session_pairing"),
        "needs_local_bridge_count": sum(
            1 for item in results if item["pairing_kind"] in {"local_cli_or_service_bridge", "native_imsg_bridge"}
        ),
        "needs_enterprise_setup_count": sum(
            1 for item in results if item["pairing_kind"] == "enterprise_bot_or_tenant_setup"
        ),
        "needs_legacy_migration_count": sum(1 for item in results if item["pairing_kind"] == "legacy_migration"),
    }
    doctor = {
        "schema": OPENCLAW_CHANNEL_PAIRING_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_owner_review",
        "results": results,
        "summary": summary,
        "policy": {
            "secret_values_stored": False,
            "session_values_stored": False,
            "absolute_local_paths_stored": False,
            "external_network_call_performed": False,
            "owner_pairing_required": "QR, OAuth, tenant, and local-account bridge steps stay outside public artifacts.",
        },
        "source_docs_checked": [
            "https://docs.openclaw.ai/channels",
            "https://docs.openclaw.ai/gateway/config-channels",
        ],
    }
    if output_path is not None:
        _write_json(output_path, doctor)
    return doctor
