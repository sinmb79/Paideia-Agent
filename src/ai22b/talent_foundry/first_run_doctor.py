from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.agent_runtime_smoke import run_agent_runtime_smoke
from ai22b.talent_foundry.chat_runtime_smoke import run_chat_runtime_smoke
from ai22b.talent_foundry.llm_adapter_contracts import run_llm_adapter_contracts
from ai22b.talent_foundry.llm_onboarding import (
    build_llm_connection_profile,
    build_llm_onboarding_checklist,
    build_llm_provider_matrix,
)
from ai22b.talent_foundry.llm_live_readiness import run_llm_live_readiness_suite
from ai22b.talent_foundry.llm_runtime import doctor_llm_provider, run_llm_application_smoke
from ai22b.talent_foundry.onboarding_doctor import doctor_onboarding_session
from ai22b.talent_foundry.package_install_doctor import doctor_package_install
from ai22b.talent_foundry.policy_eval import DEFAULT_POLICY_EVAL_SUITE, run_action_policy_eval
from ai22b.talent_foundry.public_release import audit_public_release_readiness
from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model
from ai22b.talent_foundry.runtime_contract_doctor import doctor_runtime_contract
from ai22b.talent_foundry.source_sbom import build_source_sbom
from ai22b.talent_foundry.tool_registry import audit_tool_capability_registry


FIRST_RUN_DOCTOR_SCHEMA = "paideia-first-run-doctor/v1"


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


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _public_safe(packet: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(packet.get("public_safe"))


def _policy_summary(policy_eval: dict[str, Any]) -> dict[str, Any]:
    runtime = _as_dict(policy_eval.get("runtime_policy"))
    summary = _as_dict(policy_eval.get("summary"))
    return {
        "schema": policy_eval.get("schema"),
        "status": policy_eval.get("status"),
        "case_count": summary.get("case_count"),
        "failed_count": summary.get("failed_count"),
        "network_call_performed": runtime.get("network_call_performed"),
        "llm_called": runtime.get("llm_called"),
        "private_reasoning_trace_stored": runtime.get("private_reasoning_trace_stored"),
    }


def _release_summary(release_readiness: dict[str, Any]) -> dict[str, Any]:
    summary = _as_dict(release_readiness.get("summary"))
    policy = _as_dict(release_readiness.get("policy"))
    return {
        "schema": release_readiness.get("schema"),
        "status": release_readiness.get("status"),
        "passed": release_readiness.get("passed"),
        "failed_count": summary.get("failed_count"),
        "public_candidate_issue_count": summary.get("public_candidate_issue_count"),
        "network_call_performed": summary.get("network_call_performed"),
        "subprocess_executed": summary.get("subprocess_executed"),
        "secret_values_exported": policy.get("secret_values_exported"),
    }


def _sbom_summary(source_sbom: dict[str, Any]) -> dict[str, Any]:
    package = _as_dict(source_sbom.get("package"))
    dependencies = _as_dict(source_sbom.get("dependencies"))
    inventory = _as_dict(source_sbom.get("inventory"))
    policy = _as_dict(source_sbom.get("policy"))
    release_readiness = _as_dict(source_sbom.get("release_readiness"))
    return {
        "schema": source_sbom.get("schema"),
        "package": package.get("name"),
        "license_detected": package.get("license_detected"),
        "direct_dependency_count": dependencies.get("direct_count"),
        "optional_groups": dependencies.get("optional_groups", []),
        "component_count": inventory.get("component_count"),
        "release_readiness_passed": release_readiness.get("passed"),
        "public_candidate_issue_count": release_readiness.get("public_candidate_issue_count"),
        "network_call_performed": policy.get("network_call_performed"),
        "subprocess_executed": policy.get("subprocess_executed"),
        "private_runtime_outputs_scanned": policy.get("private_runtime_outputs_scanned"),
    }


def _package_install_summary(package_doctor: dict[str, Any]) -> dict[str, Any]:
    summary = _as_dict(package_doctor.get("summary"))
    public_safe = _public_safe(package_doctor)
    return {
        "schema": package_doctor.get("schema"),
        "status": package_doctor.get("status"),
        "passed": package_doctor.get("passed"),
        "package": summary.get("package"),
        "version": summary.get("version"),
        "distribution_installed": summary.get("distribution_installed"),
        "console_script_count": summary.get("console_script_count"),
        "optional_group_count": summary.get("optional_group_count"),
        "network_call_performed": public_safe.get("network_call_performed"),
        "subprocess_executed": public_safe.get("subprocess_executed"),
        "local_absolute_paths_exported": public_safe.get("local_absolute_paths_exported"),
    }


def _runtime_contract_summary(runtime_doctor: dict[str, Any]) -> dict[str, Any]:
    summary = _as_dict(runtime_doctor.get("summary"))
    public_safe = _public_safe(runtime_doctor)
    artifacts = _as_dict(runtime_doctor.get("artifacts"))
    live_contract = _as_dict(artifacts.get("live_agent_loop_contract"))
    fail_closed_contract = _as_dict(artifacts.get("fail_closed_runtime_contract"))
    return {
        "schema": runtime_doctor.get("schema"),
        "status": runtime_doctor.get("status"),
        "passed": runtime_doctor.get("passed"),
        "check_count": summary.get("check_count"),
        "failed_count": summary.get("failed_count"),
        "live_agent_loop_status": live_contract.get("status"),
        "fail_closed_status": fail_closed_contract.get("status"),
        "network_call_performed": public_safe.get("network_call_performed"),
        "subprocess_executed": public_safe.get("subprocess_executed"),
        "live_provider_called": public_safe.get("live_provider_called"),
        "secret_values_exported": public_safe.get("secret_values_exported"),
        "private_reasoning_trace": public_safe.get("private_reasoning_trace"),
    }


def _live_readiness_summary(report: dict[str, Any]) -> dict[str, Any]:
    data_policy = _as_dict(report.get("data_policy"))
    checks = _as_dict(report.get("checks"))
    return {
        "schema": report.get("schema"),
        "status": report.get("status"),
        "passed": report.get("passed"),
        "engine": report.get("engine"),
        "llm_mode": report.get("llm_mode"),
        "live_check_requested": report.get("live_check_requested"),
        "live_ready": report.get("live_ready"),
        "provider_doctor_passed": _as_dict(checks.get("provider_doctor")).get("passed"),
        "application_smoke_passed": _as_dict(checks.get("application_smoke")).get("passed"),
        "agent_runtime_smoke_passed": _as_dict(checks.get("agent_runtime_smoke")).get("passed"),
        "secret_values_exported": data_policy.get("secret_values_exported"),
        "raw_provider_payload_saved": data_policy.get("raw_provider_payload_saved"),
        "private_reasoning_trace": data_policy.get("private_reasoning_trace"),
        "live_provider_call_attempted": data_policy.get("live_provider_call_attempted"),
    }


def _adapter_contract_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = _as_dict(report.get("summary"))
    public_safe = _public_safe(report)
    return {
        "schema": report.get("schema"),
        "status": report.get("status"),
        "passed": report.get("passed"),
        "direct_adapter_count": summary.get("direct_adapter_count"),
        "runtime_only_local_engines": summary.get("runtime_only_local_engines", []),
        "failed_count": summary.get("failed_count"),
        "network_call_performed": public_safe.get("network_call_performed"),
        "localhost_call_performed": public_safe.get("localhost_call_performed"),
        "external_provider_called": public_safe.get("external_provider_called"),
        "secret_values_exported": public_safe.get("secret_values_exported"),
        "raw_provider_payload_saved": public_safe.get("raw_provider_payload_saved"),
        "private_reasoning_trace": public_safe.get("private_reasoning_trace"),
    }


def _chat_smoke_summary(report: dict[str, Any]) -> dict[str, Any]:
    details = _as_dict(report.get("details"))
    data_policy = _as_dict(report.get("data_policy"))
    return {
        "schema": report.get("schema"),
        "status": report.get("status"),
        "passed": report.get("passed"),
        "engine": report.get("engine"),
        "llm_mode": report.get("llm_mode"),
        "chat_status": details.get("chat_status"),
        "reply_generation_mode": details.get("reply_generation_mode"),
        "preflight_status": details.get("preflight_status"),
        "selected_memory_count": details.get("selected_memory_count"),
        "stored_private_reasoning_trace": details.get("stored_private_reasoning_trace"),
        "secret_values_exported": data_policy.get("secret_values_exported"),
        "raw_provider_payload_saved": data_policy.get("raw_provider_payload_saved"),
        "private_reasoning_trace": data_policy.get("private_reasoning_trace"),
        "learning_auto_promotion_performed": data_policy.get("learning_auto_promotion_performed"),
    }


def _tool_audit_summary(tool_audit: dict[str, Any]) -> dict[str, Any]:
    details = _as_dict(tool_audit.get("details"))
    public_safe = _public_safe(tool_audit)
    return {
        "schema": tool_audit.get("schema"),
        "status": tool_audit.get("status"),
        "passed": tool_audit.get("passed"),
        "tool_count": details.get("tool_count"),
        "missing_required_tools": details.get("missing_required_tools"),
        "scope_failure_count": details.get("scope_failure_count"),
        "network_default": details.get("network_default"),
        "subprocess_default": details.get("subprocess_default"),
        "network_call_performed": public_safe.get("network_call_performed"),
        "subprocess_executed": public_safe.get("subprocess_executed"),
        "private_reasoning_trace_stored": public_safe.get("private_reasoning_trace_stored"),
    }


def _onboarding_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = _as_dict(report.get("summary"))
    public_safe = _public_safe(report)
    return {
        "schema": report.get("schema"),
        "status": report.get("status"),
        "passed": report.get("passed"),
        "session_schema": summary.get("session_schema"),
        "check_count": summary.get("check_count"),
        "failed_count": summary.get("failed_count"),
        "artifact_count": summary.get("artifact_count"),
        "network_call_performed": public_safe.get("network_call_performed"),
        "subprocess_executed": public_safe.get("subprocess_executed"),
        "private_reasoning_trace": public_safe.get("private_reasoning_trace"),
    }


def _connection_profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    public_safe = _public_safe(profile)
    setup = _as_dict(profile.get("setup_requirements"))
    readiness = _as_dict(profile.get("readiness"))
    return {
        "schema": profile.get("schema"),
        "status": profile.get("status"),
        "selected_engine": _as_dict(profile.get("selected_llm_service")).get("engine"),
        "requires_live_check_before_agent_work": setup.get("requires_live_check_before_agent_work"),
        "requires_model_argument": setup.get("requires_model_argument"),
        "live_preflight_status": readiness.get("live_preflight_status"),
        "network_call_performed": public_safe.get("network_call_performed"),
        "subprocess_executed": public_safe.get("subprocess_executed"),
        "secret_values_exported": public_safe.get("secret_values_exported"),
        "private_reasoning_trace": public_safe.get("private_reasoning_trace"),
    }


def doctor_first_run(
    *,
    repo_root: Path | None = None,
    onboarding_session: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run the public-safe first-run verification pack without live providers."""

    root = (repo_root or PROJECT_ROOT).resolve()
    checks: list[dict[str, Any]] = []
    role_models = [summarize_role_model(item) for item in list_role_models("securities_research")]
    role_model_ids = {str(item.get("role_model_id", "")) for item in role_models}
    provider_matrix = build_llm_provider_matrix(chat_surface="codex-bridge-chat")
    llm_checklist = build_llm_onboarding_checklist(
        llm_service="deterministic_local",
        llm_engine="deterministic_local",
        chat_surface="codex-bridge-chat",
    )
    llm_connection_profile = build_llm_connection_profile(
        llm_service="deterministic_local",
        llm_engine="deterministic_local",
        chat_surface="codex-bridge-chat",
    )
    provider_doctor = doctor_llm_provider(engine="deterministic_local", live_check=False)
    adapter_contracts = run_llm_adapter_contracts()
    application_smoke = run_llm_application_smoke(
        engine="deterministic_local",
        llm_mode="offline",
        task="Paideia first-run doctor application-engine smoke.",
    )
    agent_runtime_smoke = run_agent_runtime_smoke(
        engine="deterministic_local",
        llm_mode="offline",
        task="Paideia first-run doctor full agent runtime smoke.",
    )
    chat_runtime_smoke = run_chat_runtime_smoke(
        engine="deterministic_local",
        llm_mode="offline",
        chat_surface="codex-bridge-chat",
        artifact_dir=(output_path.parent if output_path is not None else root / "runs") / "chat_runtime_smoke",
        message="Paideia first-run doctor hired-chat smoke.",
    )
    live_readiness_output_dir = (
        (output_path.parent if output_path is not None else root / "runs") / "llm_live_readiness"
    )
    llm_live_readiness = run_llm_live_readiness_suite(
        engine="deterministic_local",
        live_check=False,
        output_dir=live_readiness_output_dir,
        task="Paideia first-run doctor live-readiness suite smoke.",
    )
    tool_audit = audit_tool_capability_registry()
    policy_eval = run_action_policy_eval(suite_path=DEFAULT_POLICY_EVAL_SUITE)
    release_readiness = audit_public_release_readiness(root)
    source_sbom = build_source_sbom(root)
    package_doctor = doctor_package_install(root)
    runtime_contract_doctor = doctor_runtime_contract(root)

    provider_matrix_public = _public_safe(provider_matrix)
    checklist_public = _public_safe(llm_checklist)
    connection_public = _public_safe(llm_connection_profile)
    adapter_public = _public_safe(adapter_contracts)
    application_runtime = _as_dict(application_smoke.get("runtime_result"))
    application_policy = _as_dict(application_smoke.get("data_policy"))
    agent_details = _as_dict(agent_runtime_smoke.get("details"))
    chat_details = _as_dict(chat_runtime_smoke.get("details"))
    chat_policy = _as_dict(chat_runtime_smoke.get("data_policy"))
    live_readiness_policy = _as_dict(llm_live_readiness.get("data_policy"))
    tool_public = _public_safe(tool_audit)
    policy_runtime = _as_dict(policy_eval.get("runtime_policy"))
    release_policy = _as_dict(release_readiness.get("policy"))
    sbom_policy = _as_dict(source_sbom.get("policy"))
    package_public = _public_safe(package_doctor)
    runtime_public = _public_safe(runtime_contract_doctor)

    _check(
        checks,
        "role_model_catalog_available",
        "graham_value_investing" in role_model_ids and len(role_model_ids) >= 1,
        details={"domain": "securities_research", "role_model_ids": sorted(role_model_ids)},
    )
    _check(
        checks,
        "llm_provider_matrix_public_safe",
        provider_matrix.get("schema") == "paideia-llm-provider-matrix/v1"
        and provider_matrix_public.get("network_call_performed") is False
        and provider_matrix_public.get("secret_values_exported") is False,
        details={
            "schema": provider_matrix.get("schema"),
            "service_count": _as_dict(provider_matrix.get("summary")).get("service_count"),
            "network_call_performed": provider_matrix_public.get("network_call_performed"),
        },
    )
    _check(
        checks,
        "llm_onboarding_checklist_public_safe",
        llm_checklist.get("schema") == "paideia-llm-onboarding-checklist/v1"
        and llm_checklist.get("status") == "offline_ready"
        and checklist_public.get("network_call_performed") is False
        and checklist_public.get("secret_values_exported") is False,
        details={
            "schema": llm_checklist.get("schema"),
            "status": llm_checklist.get("status"),
            "selected_engine": _as_dict(llm_checklist.get("selected_llm_service")).get("engine"),
        },
    )
    _check(
        checks,
        "llm_connection_profile_public_safe",
        llm_connection_profile.get("schema") == "paideia-llm-connection-profile/v1"
        and llm_connection_profile.get("status") == "offline_ready_no_setup"
        and connection_public.get("network_call_performed") is False
        and connection_public.get("secret_values_exported") is False,
        details=_connection_profile_summary(llm_connection_profile),
    )
    _check(
        checks,
        "deterministic_provider_doctor_ready",
        provider_doctor.get("schema") == "paideia-llm-provider-doctor/v1"
        and provider_doctor.get("engine") == "deterministic_local"
        and provider_doctor.get("passed") is True
        and provider_doctor.get("network_access") == "blocked"
        and provider_doctor.get("live_check_requested") is False,
        details={
            "schema": provider_doctor.get("schema"),
            "status": provider_doctor.get("status"),
            "network_access": provider_doctor.get("network_access"),
        },
    )
    _check(
        checks,
        "llm_adapter_contracts_passed",
        adapter_contracts.get("schema") == "paideia-llm-adapter-contracts/v1"
        and adapter_contracts.get("passed") is True
        and adapter_public.get("network_call_performed") is False
        and adapter_public.get("localhost_call_performed") is False
        and adapter_public.get("external_provider_called") is False
        and adapter_public.get("secret_values_exported") is False
        and adapter_public.get("raw_provider_payload_saved") is False
        and adapter_public.get("private_reasoning_trace") == "do_not_store",
        details=_adapter_contract_summary(adapter_contracts),
    )
    _check(
        checks,
        "application_engine_smoke_passed",
        application_smoke.get("schema") == "paideia-llm-application-smoke/v1"
        and application_smoke.get("passed") is True
        and application_runtime.get("status") == "completed"
        and application_runtime.get("network_access") == "blocked"
        and application_policy.get("private_reasoning_trace") == "do_not_store",
        details={
            "schema": application_smoke.get("schema"),
            "status": application_smoke.get("status"),
            "runtime_status": application_runtime.get("status"),
            "network_access": application_runtime.get("network_access"),
        },
    )
    _check(
        checks,
        "agent_runtime_smoke_passed",
        agent_runtime_smoke.get("schema") == "paideia-agent-runtime-smoke/v1"
        and agent_runtime_smoke.get("passed") is True
        and agent_details.get("run_status") == "completed"
        and agent_details.get("execution_contract_status") == "passed"
        and agent_details.get("public_safe") is True
        and agent_details.get("memory_auto_promotion_performed") is False,
        details={
            "schema": agent_runtime_smoke.get("schema"),
            "status": agent_runtime_smoke.get("status"),
            "run_status": agent_details.get("run_status"),
            "execution_contract_status": agent_details.get("execution_contract_status"),
            "completed_tools": agent_details.get("completed_tools"),
        },
    )
    _check(
        checks,
        "chat_runtime_smoke_passed",
        chat_runtime_smoke.get("schema") == "paideia-chat-runtime-smoke/v1"
        and chat_runtime_smoke.get("passed") is True
        and chat_details.get("chat_status") == "completed"
        and chat_details.get("preflight_network_call_made") is False
        and chat_details.get("stored_private_reasoning_trace") is False
        and chat_policy.get("learning_auto_promotion_performed") is False,
        details=_chat_smoke_summary(chat_runtime_smoke),
    )
    _check(
        checks,
        "llm_live_readiness_suite_public_safe",
        llm_live_readiness.get("schema") == "paideia-llm-live-readiness-suite/v1"
        and llm_live_readiness.get("passed") is True
        and llm_live_readiness.get("engine") == "deterministic_local"
        and llm_live_readiness.get("llm_mode") == "offline"
        and llm_live_readiness.get("live_check_requested") is False
        and live_readiness_policy.get("secret_values_exported") is False
        and live_readiness_policy.get("raw_provider_payload_saved") is False
        and live_readiness_policy.get("live_provider_call_attempted") is False,
        details=_live_readiness_summary(llm_live_readiness),
    )
    _check(
        checks,
        "tool_capability_audit_passed",
        tool_audit.get("schema") == "paideia-tool-capability-audit/v1"
        and tool_audit.get("passed") is True
        and tool_public.get("network_call_performed") is False
        and tool_public.get("subprocess_executed") is False,
        details=_tool_audit_summary(tool_audit),
    )
    _check(
        checks,
        "action_policy_eval_passed",
        policy_eval.get("schema") == "paideia-action-policy-eval-report/v1"
        and policy_eval.get("status") == "passed"
        and _as_dict(policy_eval.get("summary")).get("failed_count") == 0
        and policy_runtime.get("network_call_performed") is False
        and policy_runtime.get("llm_called") is False,
        details=_policy_summary(policy_eval),
    )
    _check(
        checks,
        "public_release_readiness_passed",
        release_readiness.get("schema") == "paideia-public-release-readiness/v1"
        and release_readiness.get("passed") is True
        and release_policy.get("secret_values_exported") is False,
        details=_release_summary(release_readiness),
    )
    _check(
        checks,
        "source_sbom_public_safe",
        source_sbom.get("schema") == "paideia-source-sbom/v1"
        and _as_dict(source_sbom.get("package")).get("name") == "paideia-agent"
        and sbom_policy.get("network_call_performed") is False
        and sbom_policy.get("subprocess_executed") is False,
        details=_sbom_summary(source_sbom),
    )
    _check(
        checks,
        "package_install_doctor_passed",
        package_doctor.get("schema") == "paideia-package-install-doctor/v1"
        and package_doctor.get("passed") is True
        and package_public.get("network_call_performed") is False
        and package_public.get("subprocess_executed") is False
        and package_public.get("local_absolute_paths_exported") is False,
        details=_package_install_summary(package_doctor),
    )
    _check(
        checks,
        "runtime_contract_doctor_passed",
        runtime_contract_doctor.get("schema") == "paideia-runtime-contract-doctor/v1"
        and runtime_contract_doctor.get("passed") is True
        and runtime_public.get("network_call_performed") is False
        and runtime_public.get("subprocess_executed") is False
        and runtime_public.get("live_provider_called") is False,
        details=_runtime_contract_summary(runtime_contract_doctor),
    )

    onboarding_report = None
    if onboarding_session is not None:
        onboarding_report = doctor_onboarding_session(onboarding_session)
        _check(
            checks,
            "onboarding_session_doctor_passed",
            onboarding_report.get("passed") is True,
            details=_onboarding_summary(onboarding_report),
        )

    no_network_or_llm_by_default = (
        provider_matrix_public.get("network_call_performed") is False
        and checklist_public.get("network_call_performed") is False
        and provider_doctor.get("network_access") == "blocked"
        and provider_doctor.get("live_check_requested") is False
        and connection_public.get("network_call_performed") is False
        and connection_public.get("secret_values_exported") is False
        and adapter_public.get("network_call_performed") is False
        and adapter_public.get("localhost_call_performed") is False
        and adapter_public.get("external_provider_called") is False
        and adapter_public.get("secret_values_exported") is False
        and application_runtime.get("network_access") == "blocked"
        and agent_details.get("preflight_network_call_made") is False
        and chat_details.get("preflight_network_call_made") is False
        and chat_policy.get("secret_values_exported") is False
        and live_readiness_policy.get("live_provider_call_attempted") is False
        and live_readiness_policy.get("secret_values_exported") is False
        and agent_details.get("network_default") == "blocked"
        and agent_details.get("subprocess_default") == "blocked"
        and tool_public.get("network_call_performed") is False
        and tool_public.get("subprocess_executed") is False
        and policy_runtime.get("network_call_performed") is False
        and policy_runtime.get("llm_called") is False
        and _as_dict(release_readiness.get("summary")).get("network_call_performed") is False
        and _as_dict(release_readiness.get("summary")).get("subprocess_executed") is False
        and sbom_policy.get("network_call_performed") is False
        and sbom_policy.get("subprocess_executed") is False
        and package_public.get("network_call_performed") is False
        and package_public.get("subprocess_executed") is False
        and runtime_public.get("network_call_performed") is False
        and runtime_public.get("subprocess_executed") is False
        and runtime_public.get("live_provider_called") is False
    )
    _check(
        checks,
        "no_network_or_llm_by_default",
        no_network_or_llm_by_default,
        details={
            "provider_live_check_requested": provider_doctor.get("live_check_requested"),
            "adapter_network_call_performed": adapter_public.get("network_call_performed"),
            "adapter_external_provider_called": adapter_public.get("external_provider_called"),
            "application_network_access": application_runtime.get("network_access"),
            "chat_runtime_preflight_network_call": chat_details.get("preflight_network_call_made"),
            "llm_live_readiness_live_provider_call_attempted": live_readiness_policy.get(
                "live_provider_call_attempted"
            ),
            "agent_network_default": agent_details.get("network_default"),
            "policy_eval_llm_called": policy_runtime.get("llm_called"),
        },
    )

    failed = [check for check in checks if not check["passed"] and check["severity"] == "error"]
    report = {
        "schema": FIRST_RUN_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "summary": {
            "check_count": len(checks),
            "failed_count": len(failed),
            "repo_root_hint": "." if root == PROJECT_ROOT.resolve() else root.name,
            "onboarding_session_checked": onboarding_session is not None,
            "network_call_performed": False,
            "subprocess_executed": False,
            "live_provider_called": False,
            "secret_values_exported": False,
        },
        "checks": checks,
        "artifacts": {
            "role_models": {
                "domain": "securities_research",
                "role_model_ids": sorted(role_model_ids),
            },
            "llm_provider_matrix": {
                "schema": provider_matrix.get("schema"),
                "service_count": _as_dict(provider_matrix.get("summary")).get("service_count"),
            },
            "llm_onboarding_checklist": {
                "schema": llm_checklist.get("schema"),
                "status": llm_checklist.get("status"),
                "command_count": len(llm_checklist.get("command_plan", []))
                if isinstance(llm_checklist.get("command_plan"), list)
                else 0,
            },
            "llm_connection_profile": _connection_profile_summary(llm_connection_profile),
            "llm_provider_doctor": {
                "schema": provider_doctor.get("schema"),
                "status": provider_doctor.get("status"),
                "network_access": provider_doctor.get("network_access"),
            },
            "llm_adapter_contracts": _adapter_contract_summary(adapter_contracts),
            "application_smoke": {
                "schema": application_smoke.get("schema"),
                "status": application_smoke.get("status"),
                "runtime_status": application_runtime.get("status"),
            },
            "agent_runtime_smoke": {
                "schema": agent_runtime_smoke.get("schema"),
                "status": agent_runtime_smoke.get("status"),
                "run_status": agent_details.get("run_status"),
                "execution_contract_status": agent_details.get("execution_contract_status"),
            },
            "chat_runtime_smoke": _chat_smoke_summary(chat_runtime_smoke),
            "llm_live_readiness": _live_readiness_summary(llm_live_readiness),
            "tool_capability_audit": _tool_audit_summary(tool_audit),
            "action_policy_eval": _policy_summary(policy_eval),
            "public_release_readiness": _release_summary(release_readiness),
            "source_sbom": _sbom_summary(source_sbom),
            "package_install_doctor": _package_install_summary(package_doctor),
            "runtime_contract_doctor": _runtime_contract_summary(runtime_contract_doctor),
            **(
                {"onboarding_session_doctor": _onboarding_summary(onboarding_report)}
                if onboarding_report is not None
                else {}
            ),
        },
        "public_safe": {
            "network_call_performed": False,
            "live_check_performed": False,
            "live_provider_called": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "private_runtime_outputs_scanned": False,
        },
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
