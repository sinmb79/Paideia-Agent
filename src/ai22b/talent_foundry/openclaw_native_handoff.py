from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENCLAW_NATIVE_HANDOFF_DOCTOR_SCHEMA = "ai22b-openclaw-native-handoff-doctor/v1"
OPENCLAW_NATIVE_HANDOFF_SCHEMA = "ai22b-openclaw-native-handoff/v1"
OPENCLAW_NATIVE_CONFIG_MERGE_SCHEMA = "ai22b-openclaw-native-config-merge/v1"
OPENCLAW_NATIVE_CONFIG_MERGE_MODES = {"plan", "write-copy", "apply"}

SECRET_KEY_PATTERNS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "bot_token",
    "client_secret",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "session",
    "token",
    "webhook",
)

PATCH_REQUIRED_PATHS = (
    "gateway.mode",
    "gateway.http.endpoints.chatCompletions.enabled",
    "models.providers",
    "agents.defaults.workspace",
    "agents.list",
    "channels.modelByChannel",
    "bindings",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _secret_like_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.casefold())
    return any(pattern in normalized for pattern in SECRET_KEY_PATTERNS)


def _get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


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


def _check_patch_paths(config_patch: dict[str, Any]) -> list[dict[str, Any]]:
    openclaw_patch = config_patch.get("openclaw_json_patch", {})
    return [
        {
            "id": f"patch:{path}",
            "passed": _get_path(openclaw_patch, path) not in (None, {}, []),
            "path": path,
        }
        for path in PATCH_REQUIRED_PATHS
    ]


def _walk_secret_values(value: Any, *, path: str = "") -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            if _secret_like_key(str(key)):
                refs.append(
                    {
                        "path": item_path,
                        "key": str(key),
                        "value_present": bool(item),
                        "secret_value_stored": False if item in (False, None, [], {}, "<redacted>") else item == [],
                    }
                )
            refs.extend(_walk_secret_values(item, path=item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            refs.extend(_walk_secret_values(item, path=f"{path}[{index}]"))
    return refs


def _safe_command_result(command: list[str], *, timeout_seconds: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return {
            "command": command,
            "ran": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "secret_values_stored": False,
        }
    return {
        "command": command,
        "ran": True,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout_preview": completed.stdout[:1000],
        "stderr_preview": completed.stderr[:1000],
        "secret_values_stored": False,
    }


def _probe_openclaw_cli(openclaw_binary: str, *, timeout_seconds: int) -> list[dict[str, Any]]:
    probe_commands = [
        [openclaw_binary, "--version"],
        [openclaw_binary, "gateway", "status", "--json", "--no-probe"],
        [openclaw_binary, "channels", "status", "--json"],
    ]
    return [_safe_command_result(command, timeout_seconds=timeout_seconds) for command in probe_commands]


def doctor_openclaw_native_handoff(
    handoff_path: Path,
    *,
    output_path: Path | None = None,
    probe_openclaw: bool = False,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    handoff_path = handoff_path.expanduser().resolve()
    handoff = _read_json(handoff_path)
    if handoff.get("schema") != OPENCLAW_NATIVE_HANDOFF_SCHEMA:
        raise ValueError("Unsupported OpenClaw native handoff schema")

    config_files = handoff.get("config_files", {})
    paideia_agent = handoff.get("paideia_agent", {})
    patch_path = Path(str(config_files.get("review_first_patch") or "")).expanduser()
    employment_path = Path(str(paideia_agent.get("employment_record") or "")).expanduser()
    workspace_path = Path(str(paideia_agent.get("workspace") or "")).expanduser()
    detected_binary = shutil.which("openclaw")
    configured_binary = str(handoff.get("openclaw_cli", {}).get("binary") or "openclaw")
    openclaw_binary = detected_binary or (configured_binary if configured_binary != "openclaw" else "openclaw")

    config_patch: dict[str, Any] | None = None
    patch_read_error: str | None = None
    if patch_path.exists():
        try:
            config_patch = _read_json(patch_path)
        except Exception as exc:
            patch_read_error = f"{type(exc).__name__}: {str(exc)[:300]}"

    patch_checks = _check_patch_paths(config_patch or {}) if config_patch else []
    secret_refs = _walk_secret_values(config_patch or {})
    explicit_secret_storage = any(
        ref["value_present"] and ref["path"].split(".")[-1] not in {"secretValuesStored", "envCandidates"}
        for ref in secret_refs
    )

    static_checks = [
        {
            "id": "openclaw_cli_on_path",
            "passed": bool(detected_binary),
            "binary": detected_binary,
            "severity": "warning",
            "next_step": "Install OpenClaw or add it to PATH before native runtime handoff." if not detected_binary else None,
        },
        {
            "id": "review_first_patch_exists",
            "passed": patch_path.exists(),
            "path": str(patch_path),
            "error": patch_read_error,
        },
        {
            "id": "employment_record_exists",
            "passed": employment_path.exists(),
            "path": str(employment_path),
        },
        {
            "id": "workspace_exists",
            "passed": workspace_path.exists(),
            "path": str(workspace_path),
        },
        {
            "id": "secret_values_not_serialized",
            "passed": not explicit_secret_storage,
            "secret_reference_count": len(secret_refs),
        },
        {
            "id": "direct_openclaw_config_write_not_performed",
            "passed": config_files.get("direct_write_performed") is False,
        },
        *patch_checks,
    ]

    probes = _probe_openclaw_cli(openclaw_binary, timeout_seconds=timeout_seconds) if probe_openclaw and detected_binary else []
    blocking_static_failures = [
        item
        for item in static_checks
        if not item.get("passed") and item.get("id") not in {"openclaw_cli_on_path"}
    ]
    probe_failures = [item for item in probes if item.get("ran") and item.get("passed") is False]
    status = "pass" if not blocking_static_failures and not probe_failures else "needs_attention"
    if not detected_binary and not probe_openclaw:
        status = "ready_for_openclaw_install"

    doctor = {
        "schema": OPENCLAW_NATIVE_HANDOFF_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "handoff": {
            "path": str(handoff_path),
            "agent_id": paideia_agent.get("agent_id"),
            "workspace": paideia_agent.get("workspace"),
            "provider_id": handoff.get("native_openclaw_selection", {}).get("provider_id"),
            "model": handoff.get("native_openclaw_selection", {}).get("model"),
            "channels": handoff.get("native_openclaw_selection", {}).get("channels", []),
        },
        "static_checks": static_checks,
        "openclaw_cli_probes": probes,
        "next_commands": handoff.get("operator_commands", {}),
        "operator_notes": [
            "This doctor never writes OpenClaw config and never stores provider or channel secrets.",
            "Use --probe-openclaw only when you want Paideia to execute read-only OpenClaw CLI probes.",
            "Apply the review_first_patch only through an owner-approved OpenClaw config workflow.",
        ],
        "secret_values_stored": False,
    }
    if output_path is not None:
        _write_json(output_path, doctor)
    return doctor


def prepare_openclaw_native_config(
    handoff_path: Path,
    *,
    output_path: Path | None = None,
    mode: str = "plan",
    target_config_path: Path | None = None,
    merged_output_path: Path | None = None,
    backup_dir: Path | None = None,
    confirm_apply: bool = False,
) -> dict[str, Any]:
    if mode not in OPENCLAW_NATIVE_CONFIG_MERGE_MODES:
        raise ValueError(f"mode must be one of: {', '.join(sorted(OPENCLAW_NATIVE_CONFIG_MERGE_MODES))}")

    handoff_path = handoff_path.expanduser().resolve()
    handoff = _read_json(handoff_path)
    if handoff.get("schema") != OPENCLAW_NATIVE_HANDOFF_SCHEMA:
        raise ValueError("Unsupported OpenClaw native handoff schema")

    config_files = handoff.get("config_files", {})
    patch_path = Path(str(config_files.get("review_first_patch") or "")).expanduser().resolve()
    selected_target_path = (
        target_config_path.expanduser().resolve()
        if target_config_path is not None
        else Path(str(config_files.get("existing_openclaw_config") or Path.home() / ".openclaw" / "openclaw.json"))
        .expanduser()
        .resolve()
    )
    if not patch_path.exists():
        raise FileNotFoundError(f"OpenClaw config patch was not found: {patch_path}")

    config_patch = _read_json(patch_path)
    openclaw_patch = config_patch.get("openclaw_json_patch")
    if not isinstance(openclaw_patch, dict):
        raise ValueError("OpenClaw config patch must contain openclaw_json_patch")

    target_exists_before_merge = selected_target_path.exists()
    existing_config: dict[str, Any] = {}
    existing_valid_json = True
    existing_read_error: str | None = None
    if target_exists_before_merge:
        try:
            existing_config = _read_json(selected_target_path)
        except Exception as exc:
            existing_valid_json = False
            existing_read_error = f"{type(exc).__name__}: {str(exc)[:500]}"

    if not existing_valid_json:
        report = {
            "schema": OPENCLAW_NATIVE_CONFIG_MERGE_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "invalid_existing_config",
            "mode": mode,
            "handoff": {"path": str(handoff_path)},
            "target_config": {
                "path": str(selected_target_path),
                "exists": selected_target_path.exists(),
                "valid_json": False,
                "error": existing_read_error,
            },
            "patch": {
                "path": str(patch_path),
                "required_checks": _check_patch_paths(config_patch),
            },
            "security": {
                "secret_values_stored_in_report": False,
                "direct_openclaw_config_write_performed": False,
            },
            "operator_notes": [
                "Existing OpenClaw config is not valid JSON. Run OpenClaw doctor or repair it before merging.",
            ],
        }
        if output_path is not None:
            _write_json(output_path, report)
        return report

    merged_config = _deep_merge(existing_config, openclaw_patch)
    existing_secret_refs = _walk_secret_values(existing_config)
    patch_secret_refs = _walk_secret_values(config_patch)
    required_patch_checks = _check_patch_paths(config_patch)
    merged_config_path: str | None = None
    backup_path: str | None = None
    direct_write_performed = False

    if mode == "write-copy":
        if merged_output_path is None:
            raise ValueError("--merged-output is required in write-copy mode because the merged config may preserve local secrets")
        merged_output = merged_output_path.expanduser().resolve()
        _write_json(merged_output, merged_config)
        merged_config_path = str(merged_output)
    elif mode == "apply":
        if not confirm_apply:
            raise ValueError("--confirm-apply is required in apply mode")
        selected_target_path.parent.mkdir(parents=True, exist_ok=True)
        if selected_target_path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_root = (
                backup_dir.expanduser().resolve()
                if backup_dir is not None
                else selected_target_path.parent / "paideia_backups"
            )
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_file = backup_root / f"{selected_target_path.name}.{timestamp}.bak"
            shutil.copy2(selected_target_path, backup_file)
            backup_path = str(backup_file)
        _write_json(selected_target_path, merged_config)
        merged_config_path = str(selected_target_path)
        direct_write_performed = True

    status_by_mode = {
        "plan": "planned",
        "write-copy": "copy_written",
        "apply": "applied",
    }
    report = {
        "schema": OPENCLAW_NATIVE_CONFIG_MERGE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status_by_mode[mode],
        "mode": mode,
        "handoff": {
            "path": str(handoff_path),
            "agent_id": handoff.get("paideia_agent", {}).get("agent_id"),
            "provider_id": handoff.get("native_openclaw_selection", {}).get("provider_id"),
            "model": handoff.get("native_openclaw_selection", {}).get("model"),
            "channels": handoff.get("native_openclaw_selection", {}).get("channels", []),
        },
        "target_config": {
            "path": str(selected_target_path),
            "exists_before_merge": target_exists_before_merge,
            "valid_json": True,
            "top_level_keys_before_merge": sorted(str(key) for key in existing_config.keys()),
            "backup_path": backup_path,
        },
        "patch": {
            "path": str(patch_path),
            "schema": config_patch.get("schema"),
            "top_level_keys": sorted(str(key) for key in openclaw_patch.keys()),
            "required_checks": required_patch_checks,
        },
        "merge": {
            "strategy": "deep_merge_paideia_patch_into_existing_openclaw_config",
            "base_config_redacted_preview": _redact_config(existing_config),
            "merged_config_redacted_preview": _redact_config(merged_config),
            "merged_config_written": merged_config_path is not None,
            "merged_config_path": merged_config_path,
            "direct_openclaw_config_write_performed": direct_write_performed,
        },
        "secret_field_audit": {
            "existing_secret_field_paths": [item["path"] for item in existing_secret_refs],
            "patch_secret_field_paths": [item["path"] for item in patch_secret_refs],
            "secret_values_stored_in_report": False,
            "existing_secret_values_preserved_only_in_local_written_config": bool(
                existing_secret_refs and mode in {"write-copy", "apply"}
            ),
        },
        "security": {
            "secret_values_stored_in_report": False,
            "private_training_files_exported": False,
            "direct_openclaw_config_write_performed": direct_write_performed,
            "apply_requires_confirm_apply": True,
            "write_copy_requires_explicit_merged_output": True,
        },
        "operator_notes": [
            "Plan mode is non-mutating and writes only this redacted report.",
            "write-copy mode can preserve existing OpenClaw secrets inside the local merged config copy; keep it out of public repos.",
            "apply mode backs up the target config first and requires --confirm-apply.",
            "Run OpenClaw doctor after applying the merged config.",
        ],
        "next_commands": {
            "doctor_native_handoff": (
                f"ai22b-talent-foundry doctor-openclaw-native-handoff --handoff {handoff_path} "
                "--output openclaw_native_handoff_doctor.json"
            ),
            "openclaw_doctor": "openclaw doctor",
            "openclaw_gateway": handoff.get("operator_commands", {}).get("run_gateway", "openclaw gateway run"),
        },
        "source_docs_checked": handoff.get("source_docs_checked", []),
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
