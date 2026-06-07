from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ONBOARDING_SESSION_DOCTOR_SCHEMA = "paideia-onboarding-session-doctor/v1"
ONBOARDING_LAUNCH_PLAN_SCHEMA = "paideia-onboarding-launch-plan/v1"
SUPPORTED_SESSION_SCHEMAS = {
    "ai-talent-guided-console-session/v1",
    "ai-talent-onboarding-session/v1",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    *,
    severity: str = "error",
    details: dict[str, Any] | None = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": "passed" if passed else "failed",
            "passed": passed,
            "severity": severity,
            "details": details or {},
        }
    )


def _artifact_paths(session: dict[str, Any]) -> dict[str, Path]:
    artifacts = session.get("artifacts", {}) if isinstance(session.get("artifacts"), dict) else {}
    return {
        str(key): Path(str(value))
        for key, value in artifacts.items()
        if isinstance(value, str) and value.strip()
    }


def _safe_read_artifact_json(path_by_id: dict[str, Path], artifact_id: str) -> dict[str, Any]:
    path = path_by_id.get(artifact_id)
    if path is None or not path.exists():
        return {}
    try:
        value = _read_json(path)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _public_safe_ok(packet: dict[str, Any]) -> bool:
    public_safe = packet.get("public_safe", {}) if isinstance(packet.get("public_safe"), dict) else {}
    return (
        public_safe.get("network_call_performed") is False
        and public_safe.get("secret_values_exported") is False
        and public_safe.get("raw_provider_payload_saved") is False
        and public_safe.get("private_reasoning_trace") == "do_not_store"
    )


def _ids(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")}


def doctor_onboarding_session(
    session_path: Path,
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Verify a generated onboarding session without executing providers or tools."""

    resolved_session_path = session_path.resolve()
    checks: list[dict[str, Any]] = []
    session: dict[str, Any] = {}
    if resolved_session_path.exists():
        try:
            session = _read_json(resolved_session_path)
        except Exception as exc:
            _check(
                checks,
                "source_session_readable",
                False,
                details={"path": str(resolved_session_path), "error_type": type(exc).__name__},
            )
    else:
        _check(
            checks,
            "source_session_exists",
            False,
            details={"path": str(resolved_session_path)},
        )
    if session:
        _check(
            checks,
            "source_session_readable",
            True,
            details={"path": str(resolved_session_path)},
        )

    schema = session.get("schema")
    _check(
        checks,
        "supported_session_schema",
        schema in SUPPORTED_SESSION_SCHEMAS,
        details={"schema": schema, "supported": sorted(SUPPORTED_SESSION_SCHEMAS)},
    )

    artifacts = _artifact_paths(session)
    required_artifacts = {
        "onboarding_session",
        "llm_onboarding_checklist",
        "llm_connection_profile",
        "llm_live_setup_guide",
        "employment_record",
        "first_goal_cycle",
    }
    if schema == "ai-talent-guided-console-session/v1":
        required_artifacts |= {
            "answers",
            "llm_provider_matrix",
            "llm_live_setup_guide",
            "onboarding_launch_plan",
            "paideia_onboarding_config",
        }
    missing_required = sorted(key for key in required_artifacts if key not in artifacts)
    missing_files = sorted(key for key in required_artifacts if key in artifacts and not artifacts[key].exists())
    _check(
        checks,
        "required_artifacts_exist",
        not missing_required and not missing_files,
        details={
            "required": sorted(required_artifacts),
            "missing_artifacts": missing_required,
            "missing_files": missing_files,
        },
    )

    provider_matrix = _safe_read_artifact_json(artifacts, "llm_provider_matrix")
    if schema == "ai-talent-guided-console-session/v1":
        _check(
            checks,
            "llm_provider_matrix_valid",
            provider_matrix.get("schema") == "paideia-llm-provider-matrix/v1" and _public_safe_ok(provider_matrix),
            details={
                "schema": provider_matrix.get("schema"),
                "service_count": provider_matrix.get("summary", {}).get("service_count"),
                "network_call_performed": provider_matrix.get("public_safe", {}).get("network_call_performed"),
            },
        )

    llm_checklist = _safe_read_artifact_json(artifacts, "llm_onboarding_checklist")
    _check(
        checks,
        "llm_onboarding_checklist_valid",
        llm_checklist.get("schema") == "paideia-llm-onboarding-checklist/v1" and _public_safe_ok(llm_checklist),
        details={
            "schema": llm_checklist.get("schema"),
            "status": llm_checklist.get("status"),
            "command_count": len(llm_checklist.get("command_plan", []))
            if isinstance(llm_checklist.get("command_plan"), list)
            else 0,
        },
    )
    llm_connection_profile = _safe_read_artifact_json(artifacts, "llm_connection_profile")
    setup_requirements = (
        llm_connection_profile.get("setup_requirements", {})
        if isinstance(llm_connection_profile.get("setup_requirements"), dict)
        else {}
    )
    _check(
        checks,
        "llm_connection_profile_valid",
        llm_connection_profile.get("schema") == "paideia-llm-connection-profile/v1"
        and _public_safe_ok(llm_connection_profile)
        and setup_requirements.get("requires_live_check_before_agent_work") in {True, False},
        details={
            "schema": llm_connection_profile.get("schema"),
            "status": llm_connection_profile.get("status"),
            "selected_engine": (
                llm_connection_profile.get("selected_llm_service", {}).get("engine")
                if isinstance(llm_connection_profile.get("selected_llm_service"), dict)
                else None
            ),
            "requires_live_check_before_agent_work": setup_requirements.get(
                "requires_live_check_before_agent_work"
            ),
            "network_call_performed": llm_connection_profile.get("public_safe", {}).get("network_call_performed"),
        },
    )
    llm_live_setup_guide = _safe_read_artifact_json(artifacts, "llm_live_setup_guide")
    readiness_gate = (
        llm_live_setup_guide.get("readiness_gate", {})
        if isinstance(llm_live_setup_guide.get("readiness_gate"), dict)
        else {}
    )
    _check(
        checks,
        "llm_live_setup_guide_valid",
        llm_live_setup_guide.get("schema") == "paideia-llm-live-setup-guide/v1"
        and _public_safe_ok(llm_live_setup_guide)
        and readiness_gate.get("requires_explicit_live_check") in {True, False},
        details={
            "schema": llm_live_setup_guide.get("schema"),
            "status": llm_live_setup_guide.get("status"),
            "selected_engine": (
                llm_live_setup_guide.get("selected_llm_service", {}).get("engine")
                if isinstance(llm_live_setup_guide.get("selected_llm_service"), dict)
                else None
            ),
            "requires_explicit_live_check": readiness_gate.get("requires_explicit_live_check"),
            "network_call_performed": llm_live_setup_guide.get("public_safe", {}).get(
                "network_call_performed"
            ),
        },
    )

    config = _safe_read_artifact_json(artifacts, "paideia_onboarding_config")
    launch_plan = _safe_read_artifact_json(artifacts, "onboarding_launch_plan")
    if schema == "ai-talent-guided-console-session/v1":
        model_auth = config.get("model_auth", {}) if isinstance(config.get("model_auth"), dict) else {}
        runtime = config.get("runtime", {}) if isinstance(config.get("runtime"), dict) else {}
        config_launch_plan = config.get("launch_plan", {}) if isinstance(config.get("launch_plan"), dict) else {}
        _check(
            checks,
            "config_links_llm_artifacts",
            (
                config.get("schema") == "ai22b-paideia-openclaw-style-config/v1"
                and model_auth.get("llm_provider_matrix") == str(artifacts.get("llm_provider_matrix"))
                and model_auth.get("llm_onboarding_checklist") == str(artifacts.get("llm_onboarding_checklist"))
                and model_auth.get("llm_connection_profile") == str(artifacts.get("llm_connection_profile"))
                and model_auth.get("llm_live_setup_guide") == str(artifacts.get("llm_live_setup_guide"))
                and model_auth.get("default_provider_call") == "none_without_explicit_live_check"
                and runtime.get("onboarding_launch_plan") == str(artifacts.get("onboarding_launch_plan"))
                and config_launch_plan.get("path") == str(artifacts.get("onboarding_launch_plan"))
            ),
            details={
                "schema": config.get("schema"),
                "default_provider_call": model_auth.get("default_provider_call"),
                "launch_plan": config_launch_plan.get("path"),
            },
        )
        launch_flow_ids = _ids(launch_plan.get("flow"))
        launch_command_ids = _ids(launch_plan.get("command_plan"))
        required_flow_ids = {
            "existing_config",
            "model_auth",
            "gateway_channels",
            "education_path",
            "raise_install_hire",
            "health_check",
            "finish",
        }
        required_command_ids = {
            "connection_profile",
            "live_setup_guide",
            "provider_doctor_no_network",
            "llm_live_readiness_suite",
            "agent_runtime_smoke",
            "chat_runtime_smoke",
            "first_chat_offline",
            "doctor_onboarding_session",
        }
        selected_llm = (
            launch_plan.get("selected_llm", {})
            if isinstance(launch_plan.get("selected_llm"), dict)
            else {}
        )
        selected_chat = (
            launch_plan.get("selected_chat_surface", {})
            if isinstance(launch_plan.get("selected_chat_surface"), dict)
            else {}
        )
        _check(
            checks,
            "onboarding_launch_plan_valid",
            (
                launch_plan.get("schema") == ONBOARDING_LAUNCH_PLAN_SCHEMA
                and _public_safe_ok(launch_plan)
                and required_flow_ids.issubset(launch_flow_ids)
                and required_command_ids.issubset(launch_command_ids)
                and bool(selected_llm.get("engine"))
                and bool(selected_chat.get("id"))
                and launch_plan.get("public_safe", {}).get("external_registration_performed") is False
            ),
            details={
                "schema": launch_plan.get("schema"),
                "status": launch_plan.get("status"),
                "missing_flow_ids": sorted(required_flow_ids - launch_flow_ids),
                "missing_command_ids": sorted(required_command_ids - launch_command_ids),
                "selected_engine": selected_llm.get("engine"),
                "selected_chat_surface": selected_chat.get("id"),
                "external_registration_performed": launch_plan.get("public_safe", {}).get(
                    "external_registration_performed"
                ),
            },
        )

    wizard = session.get("wizard", {}) if isinstance(session.get("wizard"), dict) else {}
    health = wizard.get("health", {}) if isinstance(wizard.get("health"), dict) else {}
    health_step = None
    for step in wizard.get("steps", []) if isinstance(wizard.get("steps"), list) else []:
        if isinstance(step, dict) and step.get("id") == "health":
            health_step = step
            break
    if schema == "ai-talent-guided-console-session/v1":
        _check(
            checks,
            "wizard_health_passed",
            health.get("status") == "passed"
            and health.get("local_only") is True
            and health.get("external_registration_performed") is False
            and isinstance(health_step, dict)
            and health_step.get("status") == "passed",
            details={
                "health_status": health.get("status"),
                "step_status": health_step.get("status") if isinstance(health_step, dict) else None,
                "local_only": health.get("local_only"),
            },
        )

    local_policy = session.get("local_policy", {}) if isinstance(session.get("local_policy"), dict) else {}
    _check(
        checks,
        "local_policy_safe",
        local_policy.get("local_first") is True
        and local_policy.get("private_data_upload") in {"forbidden", "forbidden_without_boss_approval"}
        and local_policy.get("private_reasoning_trace") == "do_not_store",
        details={
            "local_first": local_policy.get("local_first"),
            "private_data_upload": local_policy.get("private_data_upload"),
            "private_reasoning_trace": local_policy.get("private_reasoning_trace"),
        },
    )

    failed = [check for check in checks if not check["passed"] and check["severity"] == "error"]
    report = {
        "schema": ONBOARDING_SESSION_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "session_path": str(resolved_session_path),
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "summary": {
            "check_count": len(checks),
            "failed_count": len(failed),
            "artifact_count": len(artifacts),
            "session_schema": schema,
            "network_call_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
        },
        "checks": checks,
        "public_safe": {
            "network_call_performed": False,
            "live_check_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
        },
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
