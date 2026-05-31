from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.openclaw_channel_flow import doctor_openclaw_channel_flow
from ai22b.talent_foundry.openclaw_channel_pairing import doctor_openclaw_channel_pairing
from ai22b.talent_foundry.openclaw_gateway_llm import doctor_openclaw_gateway_llm
from ai22b.talent_foundry.openclaw_native_handoff import doctor_openclaw_native_handoff
from ai22b.talent_foundry.openclaw_provider_auth import doctor_openclaw_provider_auth


OPENCLAW_RUNTIME_PREFLIGHT_SCHEMA = "ai22b-openclaw-runtime-preflight/v1"

PASSING_PROVIDER_AUTH_STATUSES = {
    "ready_for_paideia_live_llm",
    "ready_for_codex_host_or_api_key",
    "ready_for_local_server_probe",
    "ready_for_openclaw_gateway_review",
}
PASSING_PAIRING_STATUSES = {
    "ready",
    "ready_for_live_when_env_configured",
    "ready_for_qr_pairing",
    "ready_for_bridge_probe",
    "ready_for_enterprise_bot_review",
    "ready_for_plugin_review",
    "manual_review",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_bundle_path(bundle_path: Path, ref: str | None) -> Path | None:
    if not ref:
        return None
    path = Path(str(ref)).expanduser()
    if not path.is_absolute():
        path = bundle_path.parent / path
    return path.resolve()


def _load_bundle_artifact(bundle_path: Path, bundle: dict[str, Any], key: str) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    path = _resolve_bundle_path(bundle_path, bundle.get("artifacts", {}).get(key))
    if path is None:
        return None, None, "artifact_not_declared"
    if not path.exists():
        return path, None, "artifact_missing"
    try:
        return path, _read_json(path), None
    except Exception as exc:
        return path, None, f"{type(exc).__name__}: {str(exc)[:400]}"


def _artifact_check(bundle_path: Path, bundle: dict[str, Any], key: str, schema: str | None = None) -> dict[str, Any]:
    path, data, error = _load_bundle_artifact(bundle_path, bundle, key)
    schema_ok = bool(data) and (schema is None or data.get("schema") == schema)
    return {
        "id": f"artifact:{key}",
        "passed": bool(data) and schema_ok,
        "artifact": key,
        "path": str(path) if path else None,
        "schema": data.get("schema") if data else None,
        "expected_schema": schema,
        "error": error,
    }


def _status_gate(id_: str, status: str | None, passing: set[str], *, path: str | None = None) -> dict[str, Any]:
    return {
        "id": id_,
        "passed": bool(status) and status in passing,
        "status": status,
        "path": path,
    }


def _overall_status(gates: list[dict[str, Any]]) -> str:
    failed = [gate for gate in gates if not gate.get("passed")]
    if not failed:
        return "pass"
    owner_step_failures = [
        gate
        for gate in failed
        if str(gate.get("status") or "").startswith(("needs_", "manual_", "ready_for_"))
        or gate.get("id") in {"gateway_llm_doctor", "native_handoff_doctor"}
    ]
    if len(owner_step_failures) == len(failed):
        return "ready_with_owner_steps"
    return "needs_attention"


def doctor_openclaw_runtime_preflight(
    runtime_bundle_path: Path,
    *,
    output_path: Path | None = None,
    output_dir: Path | None = None,
    probe_openclaw: bool = False,
    probe_gateway: bool = False,
    probe_chat: bool = False,
    run_channel_flow: bool = False,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    runtime_bundle_path = runtime_bundle_path.expanduser().resolve()
    bundle = _read_json(runtime_bundle_path)
    if bundle.get("schema") != "ai22b-openclaw-runtime-bundle/v1":
        raise ValueError("Unsupported OpenClaw runtime bundle schema")
    output_dir = (
        output_dir.expanduser().resolve()
        if output_dir is not None
        else (output_path.expanduser().resolve().parent if output_path is not None else runtime_bundle_path.parent / "openclaw_runtime_preflight")
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path.expanduser().resolve() if output_path else output_dir / "openclaw_runtime_preflight.json"

    selection = bundle.get("selection", {})
    provider_id = str(selection.get("provider_id") or "")
    channels = [str(channel) for channel in selection.get("channels", [])]
    employment_record = _resolve_bundle_path(runtime_bundle_path, bundle.get("employment", {}).get("employment_record"))
    native_handoff_path = _resolve_bundle_path(runtime_bundle_path, bundle.get("artifacts", {}).get("openclaw_native_handoff"))
    config_patch_path = _resolve_bundle_path(runtime_bundle_path, bundle.get("artifacts", {}).get("openclaw_config_patch"))
    existing_config_path = Path(str(selection.get("existing_openclaw_config_path") or Path.home() / ".openclaw" / "openclaw.json")).expanduser()

    provider_auth_path = output_dir / "openclaw_provider_auth_doctor.current.json"
    provider_auth = doctor_openclaw_provider_auth(
        providers=[provider_id] if provider_id else None,
        openclaw_config_path=existing_config_path,
        output_path=provider_auth_path,
    )
    channel_pairing_path = output_dir / "openclaw_channel_pairing_doctor.current.json"
    channel_pairing = doctor_openclaw_channel_pairing(
        channels=channels or None,
        output_path=channel_pairing_path,
    )

    native_handoff_doctor: dict[str, Any] | None = None
    native_handoff_doctor_path: Path | None = None
    if native_handoff_path and native_handoff_path.exists():
        native_handoff_doctor_path = output_dir / "openclaw_native_handoff_doctor.json"
        native_handoff_doctor = doctor_openclaw_native_handoff(
            native_handoff_path,
            output_path=native_handoff_doctor_path,
            probe_openclaw=probe_openclaw,
            timeout_seconds=timeout_seconds,
        )

    gateway_llm_doctor: dict[str, Any] | None = None
    gateway_llm_doctor_path: Path | None = None
    employment_engine = ""
    if employment_record and employment_record.exists():
        try:
            employment = _read_json(employment_record)
            employment_engine = str(employment.get("llm_runtime", {}).get("engine") or "")
        except Exception:
            employment_engine = ""
    if employment_record and employment_record.exists() and employment_engine == "openclaw_gateway_http":
        gateway_llm_doctor_path = output_dir / "openclaw_gateway_llm_doctor.preflight.json"
        gateway_llm_doctor = doctor_openclaw_gateway_llm(
            employment_record,
            runtime_bundle_path=runtime_bundle_path,
            config_patch_path=config_patch_path,
            output_path=gateway_llm_doctor_path,
            probe_gateway=probe_gateway,
            probe_chat=probe_chat,
            timeout_seconds=timeout_seconds,
        )

    channel_flow: dict[str, Any] | None = None
    channel_flow_path: Path | None = None
    if run_channel_flow and employment_record and employment_record.exists():
        channel_flow_path = output_dir / "openclaw_channel_flow_doctor.preflight.json"
        channel_flow = doctor_openclaw_channel_flow(
            employment_record,
            channels=channels or None,
            output_path=channel_flow_path,
            output_dir=output_dir / "channel_flow_artifacts",
            llm_mode="offline",
            message="Paideia OpenClaw runtime preflight dry-run message.",
        )

    artifact_checks = [
        _artifact_check(runtime_bundle_path, bundle, "openclaw_config_patch", "ai22b-openclaw-config-patch/v1"),
        _artifact_check(runtime_bundle_path, bundle, "openclaw_native_handoff", "ai22b-openclaw-native-handoff/v1"),
        _artifact_check(runtime_bundle_path, bundle, "provider_auth_doctor", "ai22b-openclaw-provider-auth-doctor/v1"),
        _artifact_check(runtime_bundle_path, bundle, "channel_pairing_doctor", "ai22b-openclaw-channel-pairing-doctor/v1"),
        _artifact_check(runtime_bundle_path, bundle, "gateway_config", "ai22b-openclaw-channel-gateway-config/v1"),
        _artifact_check(runtime_bundle_path, bundle, "channel_access_config", "ai22b-openclaw-channel-access-config/v1"),
    ]
    provider_auth_results = provider_auth.get("results", [])
    channel_pairing_results = channel_pairing.get("results", [])
    gates: list[dict[str, Any]] = [
        *artifact_checks,
        _status_gate(
            "provider_auth",
            str(provider_auth_results[0].get("auth_status")) if provider_auth_results else None,
            PASSING_PROVIDER_AUTH_STATUSES,
            path=str(provider_auth_path),
        ),
        {
            "id": "channel_pairing",
            "passed": all(str(item.get("pairing_status")) in PASSING_PAIRING_STATUSES for item in channel_pairing_results),
            "status": "pass" if channel_pairing_results else "not_checked",
            "path": str(channel_pairing_path),
            "channel_count": len(channel_pairing_results),
        },
    ]
    if native_handoff_doctor is not None:
        gates.append(
            _status_gate(
                "native_handoff_doctor",
                str(native_handoff_doctor.get("status")),
                {"pass", "ready_for_openclaw_install"},
                path=str(native_handoff_doctor_path),
            )
        )
    if gateway_llm_doctor is not None:
        gates.append(
            _status_gate(
                "gateway_llm_doctor",
                str(gateway_llm_doctor.get("status")),
                {"pass", "ready_for_gateway_start"},
                path=str(gateway_llm_doctor_path),
            )
        )
    if channel_flow is not None:
        gates.append(
            _status_gate(
                "channel_flow_doctor",
                str(channel_flow.get("status")),
                {"pass"},
                path=str(channel_flow_path),
            )
        )

    report = {
        "schema": OPENCLAW_RUNTIME_PREFLIGHT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": _overall_status(gates),
        "runtime_bundle": str(runtime_bundle_path),
        "selection": {
            "provider_id": provider_id,
            "model": selection.get("model"),
            "channels": channels,
            "bind_host": selection.get("bind_host"),
            "port": selection.get("port"),
            "llm_engine": employment_engine or None,
        },
        "artifacts": {
            "provider_auth_doctor": str(provider_auth_path),
            "channel_pairing_doctor": str(channel_pairing_path),
            "native_handoff_doctor": str(native_handoff_doctor_path) if native_handoff_doctor_path else None,
            "gateway_llm_doctor": str(gateway_llm_doctor_path) if gateway_llm_doctor_path else None,
            "channel_flow_doctor": str(channel_flow_path) if channel_flow_path else None,
        },
        "gates": gates,
        "summary": {
            "gate_count": len(gates),
            "passed_gate_count": sum(1 for gate in gates if gate.get("passed")),
            "failed_gate_count": sum(1 for gate in gates if not gate.get("passed")),
            "provider_auth_statuses": [item.get("auth_status") for item in provider_auth_results],
            "channel_pairing_statuses": {
                item.get("channel_id"): item.get("pairing_status")
                for item in channel_pairing_results
            },
            "network_probe_requested": bool(probe_openclaw or probe_gateway or probe_chat),
            "channel_flow_run": bool(channel_flow),
        },
        "next_commands": {
            "run_again_static": (
                f"ai22b-talent-foundry doctor-openclaw-runtime-preflight --runtime-bundle {runtime_bundle_path} "
                f"--output {output_path}"
            ),
            "run_with_gateway_probe": (
                f"ai22b-talent-foundry doctor-openclaw-runtime-preflight --runtime-bundle {runtime_bundle_path} "
                "--probe-gateway --probe-chat "
                f"--output {output_dir / 'openclaw_runtime_preflight.live.json'}"
            ),
            "run_channel_flow": (
                f"ai22b-talent-foundry doctor-openclaw-runtime-preflight --runtime-bundle {runtime_bundle_path} "
                "--run-channel-flow "
                f"--output {output_dir / 'openclaw_runtime_preflight.channel_flow.json'}"
            ),
        },
        "policy": {
            "secret_values_stored": False,
            "private_training_files_exported": False,
            "external_network_call_performed": bool(probe_gateway or probe_chat),
            "openclaw_cli_probe_performed": bool(probe_openclaw),
            "dry_run_channel_flow_only": bool(channel_flow),
        },
        "source_docs_checked": [
            "https://docs.openclaw.ai/providers",
            "https://docs.openclaw.ai/channels",
            "https://docs.openclaw.ai/gateway/openai-http-api",
            "https://docs.openclaw.ai/cli/gateway",
        ],
    }
    _write_json(output_path, report)
    return report
