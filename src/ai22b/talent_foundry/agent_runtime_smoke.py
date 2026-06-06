from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.agent_execution_loop import (
    AGENT_RUNTIME_STATUS_CARD_SCHEMA,
    TOOL_EXECUTION_STATUS_CARD_SCHEMA,
)
from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
from ai22b.talent_foundry.llm_clients import LLMClient
from ai22b.talent_foundry.llm_runtime import build_llm_provider_preflight, build_llm_runtime_config
from ai22b.talent_foundry.tool_registry import TOOL_ARTIFACT_MANIFEST_SCHEMA


AGENT_RUNTIME_SMOKE_SCHEMA = "paideia-agent-runtime-smoke/v1"
LIVE_LLM_AGENT_PROOF_SCHEMA = "paideia-live-llm-agent-proof/v1"
AGENT_RUNTIME_SMOKE_ACCEPTED_LLM_STATUSES = {
    "completed",
    "bridge_context_prepared",
    "adapter_manifest_ready",
}
AGENT_RUNTIME_SMOKE_REQUIRED_TOOLS = {
    "local_file_read",
    "local_file_write",
    "work_session",
    "evidence_packet",
    "assessment",
    "memory_consolidation",
}


def _smoke_manifest() -> dict[str, Any]:
    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "paideia-runtime-smoke-agent",
            "role": "public-safe P0 agent runtime smoke fixture",
            "major_goal": "Prove the selected LLM engine reaches policy, tools, verification, memory, and audit.",
        },
        "memory_profile": {
            "procedural_principles": [
                "Policy must be checked before LLM planning.",
                "Registered tools are the only execution authority.",
                "Learning is written as a review candidate, not promoted automatically.",
            ],
            "semantic_themes": ["P0 runtime smoke", "local-first agent execution", "reviewable evidence"],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
        "llm_policy": {
            "role": "application_engine_not_identity",
            "private_reasoning_trace": "do_not_store",
        },
        "tool_policy": {
            "allowed_tools": sorted(AGENT_RUNTIME_SMOKE_REQUIRED_TOOLS),
            "blocked_tools": ["external_upload", "financial_action", "personal_data_transfer"],
        },
    }


def _completed_tools(tool_execution: dict[str, Any]) -> list[str]:
    return sorted(
        str(item.get("tool"))
        for item in tool_execution.get("tool_results", [])
        if isinstance(item, dict) and item.get("status") == "completed"
    )


def _tool_statuses(tool_execution: dict[str, Any]) -> dict[str, str]:
    return {
        str(item.get("tool")): str(item.get("status"))
        for item in tool_execution.get("tool_results", [])
        if isinstance(item, dict)
    }


def _artifact_manifest_summary(
    *,
    artifact_dir: Path | None,
    tool_execution: dict[str, Any],
    tool_status_card: dict[str, Any],
) -> dict[str, Any]:
    manifest = tool_execution.get("artifact_manifest", {})
    manifest = manifest if isinstance(manifest, dict) else {}
    status_card_manifest = tool_status_card.get("artifact_manifest", {})
    status_card_manifest = status_card_manifest if isinstance(status_card_manifest, dict) else {}
    public_safe = manifest.get("public_safe", {})
    public_safe = public_safe if isinstance(public_safe, dict) else {}
    artifacts = [item for item in manifest.get("artifacts", []) if isinstance(item, dict)]
    relative_paths_only = all(
        item.get("relative_path")
        and not Path(str(item.get("relative_path"))).is_absolute()
        and ".." not in Path(str(item.get("relative_path"))).parts
        for item in artifacts
    )
    manifest_file = manifest.get("manifest_file")
    manifest_file_relative = bool(
        manifest_file
        and not Path(str(manifest_file)).is_absolute()
        and ".." not in Path(str(manifest_file)).parts
    )
    artifact_files_exist = False
    manifest_file_exists = False
    if artifact_dir is not None and artifact_dir.exists():
        artifact_files_exist = all((artifact_dir / str(item.get("relative_path", ""))).is_file() for item in artifacts)
        if manifest_file:
            manifest_file_exists = (artifact_dir / str(manifest_file)).is_file()
    evidence_packet_artifact = next(
        (item for item in artifacts if item.get("tool") == "evidence_packet"),
        {},
    )
    return {
        "schema": manifest.get("schema"),
        "status": manifest.get("status"),
        "artifact_count": manifest.get("artifact_count", 0),
        "artifact_root": manifest.get("artifact_root"),
        "manifest_file": manifest_file,
        "manifest_sha256_present": bool(manifest.get("manifest_sha256")),
        "manifest_file_relative": manifest_file_relative,
        "manifest_file_exists": manifest_file_exists,
        "artifact_files_exist": artifact_files_exist,
        "relative_paths_only": relative_paths_only,
        "status_card_schema": status_card_manifest.get("schema"),
        "status_card_status": status_card_manifest.get("status"),
        "status_card_artifact_count": status_card_manifest.get("artifact_count", 0),
        "evidence_packet_artifact_materialized": bool(evidence_packet_artifact.get("relative_path")),
        "public_safe": {
            "network_call_performed": public_safe.get("network_call_performed"),
            "subprocess_executed": public_safe.get("subprocess_executed"),
            "external_side_effects_performed": public_safe.get("external_side_effects_performed"),
            "raw_provider_payload_saved": public_safe.get("raw_provider_payload_saved"),
            "private_reasoning_trace": public_safe.get("private_reasoning_trace"),
            "absolute_paths_exported": public_safe.get("absolute_paths_exported"),
        },
    }


def _build_live_llm_agent_proof(
    *,
    engine: str,
    service: str | None,
    llm_mode: str,
    run_attempted: bool,
    client_override_used: bool,
    preflight: dict[str, Any],
    details: dict[str, Any],
    llm_client_contract: dict[str, Any] | None = None,
    public_safe: bool,
    report_passed: bool,
) -> dict[str, Any]:
    contract = llm_client_contract if isinstance(llm_client_contract, dict) else {}
    client_executor = contract.get("client_executor")
    llm_status = details.get("llm_status")
    if llm_mode != "live":
        proof_status = "offline_verified"
        provider_path = "offline_deterministic_no_provider_call"
        proof_level = "offline_no_network"
    elif not run_attempted:
        proof_status = "needs_configuration"
        provider_path = "fail_closed_before_agent_loop"
        proof_level = "configuration_gate"
    elif client_executor == "injected_client" or client_override_used:
        proof_status = "live_like_client_verified" if report_passed else "live_like_client_failed"
        provider_path = "injected_live_client_contract"
        proof_level = "injected_client_live_like"
    elif client_executor == "built_in_client":
        proof_status = "real_live_provider_verified" if report_passed and llm_status == "completed" else "real_live_provider_not_ready"
        provider_path = "built_in_live_provider_client"
        proof_level = "real_provider_client"
    elif llm_status in {"bridge_context_prepared", "adapter_manifest_ready"}:
        proof_status = "adapter_context_prepared" if report_passed else "adapter_context_failed"
        provider_path = "adapter_context_no_live_generation"
        proof_level = "adapter_context"
    else:
        proof_status = "failed" if not report_passed else "verified"
        provider_path = "unknown_or_unclassified_live_path"
        proof_level = "unknown"

    live_client_generate_called = bool(
        llm_mode == "live"
        and run_attempted
        and (
            client_override_used
            or client_executor in {"injected_client", "built_in_client"}
            or llm_status in {"completed", "unavailable"}
        )
    )
    built_in_provider_client_called = bool(llm_mode == "live" and run_attempted and client_executor == "built_in_client")
    injected_client_used = bool(client_override_used or client_executor == "injected_client")
    sensitive_retention_passed = (
        details.get("client_result_text_omitted") is not False
        and details.get("client_result_raw_output_saved") is not True
        and details.get("llm_client_contract_raw_payload_saved") is not True
        and details.get("llm_client_contract_private_reasoning_values_stored") is not True
        and details.get("raw_or_hidden_trace_absent") is True
    )
    proof_passed = bool(
        public_safe
        and (
            proof_status
            in {
                "offline_verified",
                "live_like_client_verified",
                "real_live_provider_verified",
                "adapter_context_prepared",
            }
            or proof_status == "needs_configuration"
        )
        and sensitive_retention_passed
    )
    return {
        "schema": LIVE_LLM_AGENT_PROOF_SCHEMA,
        "status": proof_status,
        "passed": proof_passed,
        "proof_level": proof_level,
        "provider_path": provider_path,
        "engine": engine,
        "service": service or engine,
        "llm_mode": llm_mode,
        "run_attempted": run_attempted,
        "live_runtime_path_selected": llm_mode == "live",
        "live_client_generate_called": live_client_generate_called,
        "client_override_used": injected_client_used,
        "built_in_provider_client_called": built_in_provider_client_called,
        "provider_preflight": {
            "status": preflight.get("status"),
            "live_path_selected": preflight.get("live_path_selected"),
            "live_check_performed": preflight.get("live_check_performed"),
            "network_call_made": preflight.get("network_call_made_by_preflight"),
            "blocking_check_count": len(preflight.get("blocking_checks", []))
            if isinstance(preflight.get("blocking_checks"), list)
            else None,
        },
        "runtime": {
            "llm_status": llm_status,
            "run_status": details.get("run_status"),
            "policy_status": details.get("policy_status"),
            "verification_status": details.get("verification_status"),
            "execution_contract_status": details.get("execution_contract_status"),
            "tool_execution_status": details.get("tool_execution_status_card_status"),
            "memory_decision": details.get("memory_decision"),
        },
        "llm_client_contract": {
            "schema": contract.get("schema"),
            "status": contract.get("status"),
            "client_executor": client_executor,
            "runtime_status": contract.get("runtime_status"),
            "summary_only": contract.get("client_result_summary_only"),
            "raw_provider_payload_saved": contract.get("raw_provider_payload_saved", False),
            "private_reasoning_values_stored": contract.get("private_reasoning_field_values_stored", False),
            "private_reasoning_trace": contract.get("private_reasoning_trace", "do_not_store")
            if contract
            else "do_not_store",
        },
        "evidence": {
            "registered_tool_executor_is_authority": True,
            "tool_evidence_packet_completed": details.get("tool_execution_status_card_evidence_completed"),
            "tool_artifact_manifest_schema": details.get("tool_artifact_manifest_schema"),
            "tool_artifact_manifest_status": details.get("tool_artifact_manifest_status"),
            "tool_artifact_evidence_packet_materialized": details.get(
                "tool_artifact_evidence_packet_materialized"
            ),
            "memory_review_candidate_schema": details.get("memory_review_candidate_schema"),
            "automatic_memory_promotion_performed": details.get("memory_auto_promotion_performed"),
            "raw_or_hidden_trace_absent": details.get("raw_or_hidden_trace_absent"),
            "sensitive_retention_passed": sensitive_retention_passed,
        },
        "public_safe": {
            "passed": public_safe,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "preflight_network_call_made": preflight.get("network_call_made_by_preflight"),
            "network_default": details.get("network_default"),
            "subprocess_default": details.get("subprocess_default"),
            "external_side_effects_performed": details.get(
                "tool_execution_status_card_external_side_effects_performed"
            ),
            "local_tool_artifacts_materialized": details.get("tool_artifact_manifest_status") == "materialized",
        },
    }


def run_agent_runtime_smoke(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    service: str | None = None,
    llm_mode: str = "offline",
    task: str = "Run a public-safe Paideia agent runtime smoke and leave a reviewable evidence packet.",
    client: LLMClient | None = None,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    """Run one public-safe agent loop from LLM selection through memory candidate and audit."""

    runtime_config = build_llm_runtime_config(
        engine=engine,
        model=model,
        model_path=model_path,
        service=service,
    )
    preflight = build_llm_provider_preflight(runtime_config, llm_mode=llm_mode, llm_model=model)
    live_provider_not_ready = (
        llm_mode == "live"
        and client is None
        and preflight.get("status") == "needs_configuration"
    )
    if live_provider_not_ready:
        details = {
            "schema": "paideia-agent-runtime-smoke-details/v1",
            "run_attempted": False,
            "failure_mode": "live_provider_not_ready",
            "engine": engine,
            "service": service or engine,
            "llm_mode": llm_mode,
            "llm_status": "skipped_provider_not_ready",
            "preflight_status": preflight.get("status"),
            "preflight_blocking_check_count": len(preflight.get("blocking_checks", [])),
            "preflight_live_path_selected": preflight.get("live_path_selected"),
            "preflight_live_check_performed": preflight.get("live_check_performed"),
            "preflight_network_call_made": preflight.get("network_call_made_by_preflight"),
            "policy_status": "skipped_provider_not_ready",
            "agent_runtime_status_card_schema": AGENT_RUNTIME_STATUS_CARD_SCHEMA,
            "agent_runtime_status_card_status": "skipped_provider_not_ready",
            "agent_runtime_status_card_public_safe": True,
            "agent_runtime_status_card_memory_decision": "skipped_provider_not_ready",
            "selected_tools": [],
            "completed_tools": [],
            "missing_required_tools": sorted(AGENT_RUNTIME_SMOKE_REQUIRED_TOOLS),
            "tool_statuses": {},
            "tool_execution_status_card_schema": TOOL_EXECUTION_STATUS_CARD_SCHEMA,
            "tool_execution_status_card_status": "skipped_provider_not_ready",
            "tool_execution_status_card_completed_count": 0,
            "tool_execution_status_card_evidence_completed": False,
            "tool_execution_status_card_external_side_effects_performed": False,
            "tool_artifact_manifest_schema": TOOL_ARTIFACT_MANIFEST_SCHEMA,
            "tool_artifact_manifest_status": "not_requested",
            "tool_artifact_manifest_count": 0,
            "tool_artifact_manifest_file": None,
            "tool_artifact_manifest_file_exists": False,
            "tool_artifact_files_exist": False,
            "tool_artifact_relative_paths_only": True,
            "tool_artifact_evidence_packet_materialized": False,
            "tool_artifact_public_safe": True,
            "tool_execution_status_card_local_artifacts_materialized": False,
            "network_default": "blocked",
            "subprocess_default": "blocked",
            "verification_status": "skipped_provider_not_ready",
            "execution_contract_status": "skipped_provider_not_ready",
            "memory_decision": "skipped_provider_not_ready",
            "memory_review_candidate_schema": None,
            "memory_auto_promotion_performed": False,
            "audit_event_count": 0,
            "raw_or_hidden_trace_absent": True,
            "public_safe": True,
        }
        live_llm_agent_proof = _build_live_llm_agent_proof(
            engine=engine,
            service=service,
            llm_mode=llm_mode,
            run_attempted=False,
            client_override_used=False,
            preflight=preflight,
            details=details,
            llm_client_contract=None,
            public_safe=True,
            report_passed=False,
        )
        return {
            "schema": AGENT_RUNTIME_SMOKE_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "needs_configuration",
            "passed": False,
            "details": details,
            "live_llm_agent_proof": live_llm_agent_proof,
            "preflight": preflight,
            "data_policy": {
                "secret_values_exported": False,
                "send_private_training_files": False,
                "send_full_session_replay": False,
                "store_raw_provider_payload": False,
                "private_reasoning_trace": "do_not_store",
                "automatic_memory_promotion": False,
            },
            "runtime_path": [
                "provider_preflight",
                "fail_closed_before_agent_loop",
            ],
            "next_actions": [
                "Set the required provider environment variable or local endpoint.",
                "Run doctor-llm-provider with --live-check before retrying the full agent runtime smoke.",
                "Use --llm-mode offline for a deterministic no-network runtime check.",
            ],
        }
    resolved_artifact_dir = artifact_dir or Path(tempfile.mkdtemp(prefix="paideia_agent_runtime_smoke_tools_"))
    run = run_agent_from_manifest(
        _smoke_manifest(),
        task=task,
        runtime_config=runtime_config,
        llm_mode=llm_mode,
        llm_model=model,
        llm_client=client,
        tool_artifact_dir=resolved_artifact_dir,
    )
    llm_result = run.get("llm_runtime_result", {}) if isinstance(run.get("llm_runtime_result"), dict) else {}
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
    client_result = llm_result.get("client_result", {}) if isinstance(llm_result.get("client_result"), dict) else {}
    llm_client_contract = (
        llm_result.get("llm_client_contract", {}) if isinstance(llm_result.get("llm_client_contract"), dict) else {}
    )
    preflight = run.get("llm_provider_preflight", {}) if isinstance(run.get("llm_provider_preflight"), dict) else preflight
    policy_decision = run.get("policy_decision", {}) if isinstance(run.get("policy_decision"), dict) else {}
    tool_execution = run.get("tool_execution", {}) if isinstance(run.get("tool_execution"), dict) else {}
    tool_status_card = (
        run.get("tool_execution_status_card", {})
        if isinstance(run.get("tool_execution_status_card"), dict)
        else {}
    )
    tool_status_card_public_safe = (
        tool_status_card.get("public_safe", {})
        if isinstance(tool_status_card.get("public_safe"), dict)
        else {}
    )
    tool_status_card_evidence = (
        tool_status_card.get("evidence_packet", {})
        if isinstance(tool_status_card.get("evidence_packet"), dict)
        else {}
    )
    tool_scope = (
        tool_execution.get("capability_scope", {})
        if isinstance(tool_execution.get("capability_scope"), dict)
        else {}
    )
    verification = run.get("verification", {}) if isinstance(run.get("verification"), dict) else {}
    execution_contract = (
        run.get("execution_contract", {}) if isinstance(run.get("execution_contract"), dict) else {}
    )
    alignment = run.get("llm_tool_plan_alignment", {}) if isinstance(run.get("llm_tool_plan_alignment"), dict) else {}
    memory_write = run.get("memory_write", {}) if isinstance(run.get("memory_write"), dict) else {}
    review_candidate = (
        memory_write.get("review_candidate", {})
        if isinstance(memory_write.get("review_candidate"), dict)
        else {}
    )
    runtime_observability = (
        run.get("runtime_observability", {}) if isinstance(run.get("runtime_observability"), dict) else {}
    )
    agent_runtime_status_card = (
        run.get("agent_runtime_status_card", {})
        if isinstance(run.get("agent_runtime_status_card"), dict)
        else {}
    )
    completed_tools = _completed_tools(tool_execution)
    missing_required_tools = sorted(AGENT_RUNTIME_SMOKE_REQUIRED_TOOLS - set(completed_tools))
    artifact_summary = _artifact_manifest_summary(
        artifact_dir=resolved_artifact_dir,
        tool_execution=tool_execution,
        tool_status_card=tool_status_card,
    )
    serialized = json.dumps(run, ensure_ascii=False)
    raw_or_hidden_absent = (
        "hidden provider smoke trace" not in serialized
        and client_result.get("private_reasoning_field_values_stored", False) is False
        and client_result.get("raw_output_saved", False) is False
    )
    public_safe = (
        preflight.get("network_call_made_by_preflight") is False
        and tool_scope.get("network_default") == "blocked"
        and tool_scope.get("subprocess_default") == "blocked"
        and llm_plan.get("private_reasoning_trace") == "do_not_store"
        and llm_plan.get("raw_provider_text_stored") is not True
        and (not llm_client_contract or llm_client_contract.get("status") == "passed")
        and artifact_summary["status"] == "materialized"
        and artifact_summary["artifact_files_exist"] is True
        and artifact_summary["manifest_file_exists"] is True
        and artifact_summary["relative_paths_only"] is True
        and artifact_summary["public_safe"]["absolute_paths_exported"] is False
        and artifact_summary["public_safe"]["network_call_performed"] is False
        and artifact_summary["public_safe"]["subprocess_executed"] is False
        and artifact_summary["public_safe"]["raw_provider_payload_saved"] is False
        and artifact_summary["public_safe"]["private_reasoning_trace"] == "do_not_store"
        and memory_write.get("automatic_promotion_performed") is False
        and raw_or_hidden_absent
    )
    details = {
        "schema": "paideia-agent-runtime-smoke-details/v1",
        "run_attempted": True,
        "failure_mode": "none",
        "run_schema": run.get("schema"),
        "run_status": run.get("run_status"),
        "engine": engine,
        "service": service or engine,
        "llm_mode": llm_mode,
        "llm_status": llm_result.get("status"),
        "llm_engine": llm_result.get("engine"),
        "llm_applied_as": llm_result.get("applied_as"),
        "llm_plan_schema": llm_plan.get("schema"),
        "llm_plan_source": llm_plan.get("source"),
        "client_result_text_omitted": client_result.get("text_omitted"),
        "client_result_raw_output_saved": client_result.get("raw_output_saved"),
        "client_result_private_reasoning_fields_omitted": client_result.get(
            "private_reasoning_fields_omitted",
            0,
        ),
        "client_result_private_reasoning_values_stored": client_result.get(
            "private_reasoning_field_values_stored",
            False,
        ),
        "llm_client_contract_schema": llm_client_contract.get("schema"),
        "llm_client_contract_status": llm_client_contract.get("status"),
        "llm_client_contract_summary_only": llm_client_contract.get("client_result_summary_only"),
        "llm_client_contract_raw_payload_saved": llm_client_contract.get("raw_provider_payload_saved"),
        "llm_client_contract_private_reasoning_values_stored": llm_client_contract.get(
            "private_reasoning_field_values_stored"
        ),
        "preflight_status": preflight.get("status"),
        "preflight_live_path_selected": preflight.get("live_path_selected"),
        "preflight_live_check_performed": preflight.get("live_check_performed"),
        "preflight_network_call_made": preflight.get("network_call_made_by_preflight"),
        "policy_status": policy_decision.get("status"),
        "agent_runtime_status_card_schema": agent_runtime_status_card.get("schema"),
        "agent_runtime_status_card_status": agent_runtime_status_card.get("status"),
        "agent_runtime_status_card_public_safe": agent_runtime_status_card.get("public_safe", {}).get("passed")
        if isinstance(agent_runtime_status_card.get("public_safe"), dict)
        else None,
        "agent_runtime_status_card_memory_decision": agent_runtime_status_card.get("memory", {}).get("decision")
        if isinstance(agent_runtime_status_card.get("memory"), dict)
        else None,
        "policy_authorization_model": policy_decision.get("capability_authorization", {}).get(
            "authorization_model"
        )
        if isinstance(policy_decision.get("capability_authorization"), dict)
        else None,
        "selected_tools": run.get("selected_tools", []),
        "completed_tools": completed_tools,
        "tool_statuses": _tool_statuses(tool_execution),
        "missing_required_tools": missing_required_tools,
        "tool_execution_status_card_schema": tool_status_card.get("schema"),
        "tool_execution_status_card_status": tool_status_card.get("status"),
        "tool_execution_status_card_completed_count": len(tool_status_card.get("completed_tools", []))
        if isinstance(tool_status_card.get("completed_tools"), list)
        else None,
        "tool_execution_status_card_evidence_completed": tool_status_card_evidence.get("completed"),
        "tool_execution_status_card_external_side_effects_performed": tool_status_card_public_safe.get(
            "external_side_effects_performed"
        ),
        "tool_execution_status_card_local_artifacts_materialized": tool_status_card_public_safe.get(
            "local_tool_artifacts_materialized"
        ),
        "tool_artifact_manifest_schema": artifact_summary["schema"],
        "tool_artifact_manifest_status": artifact_summary["status"],
        "tool_artifact_manifest_count": artifact_summary["artifact_count"],
        "tool_artifact_manifest_file": artifact_summary["manifest_file"],
        "tool_artifact_manifest_file_exists": artifact_summary["manifest_file_exists"],
        "tool_artifact_files_exist": artifact_summary["artifact_files_exist"],
        "tool_artifact_relative_paths_only": artifact_summary["relative_paths_only"],
        "tool_artifact_evidence_packet_materialized": artifact_summary["evidence_packet_artifact_materialized"],
        "tool_artifact_public_safe": (
            artifact_summary["public_safe"]["network_call_performed"] is False
            and artifact_summary["public_safe"]["subprocess_executed"] is False
            and artifact_summary["public_safe"]["external_side_effects_performed"] is False
            and artifact_summary["public_safe"]["raw_provider_payload_saved"] is False
            and artifact_summary["public_safe"]["private_reasoning_trace"] == "do_not_store"
            and artifact_summary["public_safe"]["absolute_paths_exported"] is False
        ),
        "tool_execution_model": tool_execution.get("execution_model"),
        "network_default": tool_scope.get("network_default"),
        "subprocess_default": tool_scope.get("subprocess_default"),
        "verification_status": verification.get("status"),
        "execution_contract_status": execution_contract.get("status"),
        "llm_tool_suggestion_only_enforced": alignment.get("suggestion_only_enforced"),
        "out_of_scope_executed_count": alignment.get("out_of_scope_executed_count"),
        "memory_decision": memory_write.get("decision"),
        "memory_review_candidate_schema": review_candidate.get("schema"),
        "memory_auto_promotion_performed": memory_write.get("automatic_promotion_performed"),
        "audit_event_count": len(run.get("audit_events", [])),
        "runtime_observability_schema": runtime_observability.get("schema"),
        "raw_or_hidden_trace_absent": raw_or_hidden_absent,
        "public_safe": public_safe,
    }
    passed = (
        details["run_schema"] == "ai-talent-agent-run/v1"
        and details["run_status"] == "completed"
        and details["policy_status"] == "approved"
        and details["agent_runtime_status_card_schema"] == AGENT_RUNTIME_STATUS_CARD_SCHEMA
        and details["agent_runtime_status_card_status"] == "completed_verified"
        and details["agent_runtime_status_card_public_safe"] is True
        and details["agent_runtime_status_card_memory_decision"] == "candidate_pending_boss_review"
        and details["llm_status"] in AGENT_RUNTIME_SMOKE_ACCEPTED_LLM_STATUSES
        and details["llm_plan_schema"] == "paideia-llm-reviewable-plan/v1"
        and details["tool_execution_model"] == "registered_capability_checked_local_tools_v1"
        and details["tool_execution_status_card_schema"] == TOOL_EXECUTION_STATUS_CARD_SCHEMA
        and details["tool_execution_status_card_status"] == "completed_verified"
        and details["tool_execution_status_card_evidence_completed"] is True
        and details["tool_execution_status_card_external_side_effects_performed"] is False
        and details["tool_execution_status_card_local_artifacts_materialized"] is True
        and details["tool_artifact_manifest_schema"] == TOOL_ARTIFACT_MANIFEST_SCHEMA
        and details["tool_artifact_manifest_status"] == "materialized"
        and details["tool_artifact_manifest_count"] >= len(AGENT_RUNTIME_SMOKE_REQUIRED_TOOLS)
        and details["tool_artifact_manifest_file"] == "tool_execution_artifact_manifest.json"
        and details["tool_artifact_manifest_file_exists"] is True
        and details["tool_artifact_files_exist"] is True
        and details["tool_artifact_relative_paths_only"] is True
        and details["tool_artifact_evidence_packet_materialized"] is True
        and details["tool_artifact_public_safe"] is True
        and details["missing_required_tools"] == []
        and details["verification_status"] == "passed"
        and details["execution_contract_status"] == "passed"
        and details["llm_tool_suggestion_only_enforced"] is True
        and details["out_of_scope_executed_count"] == 0
        and details["memory_decision"] == "candidate_pending_boss_review"
        and details["memory_review_candidate_schema"] == "paideia-memory-review-candidate/v1"
        and details["memory_auto_promotion_performed"] is False
        and details["audit_event_count"] >= 4
        and details["network_default"] == "blocked"
        and details["subprocess_default"] == "blocked"
        and details["llm_client_contract_status"] in {None, "passed"}
        and details["preflight_network_call_made"] is False
        and public_safe
    )
    live_llm_agent_proof = _build_live_llm_agent_proof(
        engine=engine,
        service=service,
        llm_mode=llm_mode,
        run_attempted=True,
        client_override_used=client is not None,
        preflight=preflight,
        details=details,
        llm_client_contract=llm_client_contract,
        public_safe=public_safe,
        report_passed=passed,
    )
    return {
        "schema": AGENT_RUNTIME_SMOKE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "passed": passed,
        "details": details,
        "live_llm_agent_proof": live_llm_agent_proof,
        "data_policy": {
            "secret_values_exported": False,
            "send_private_training_files": False,
            "send_full_session_replay": False,
            "store_raw_provider_payload": False,
            "private_reasoning_trace": "do_not_store",
            "automatic_memory_promotion": False,
        },
        "runtime_path": [
            "manifest",
            "action_intent_policy",
            "llm_application_engine",
            "registered_tool_executor",
            "verification",
            "memory_review_candidate",
            "audit_log",
        ],
    }
