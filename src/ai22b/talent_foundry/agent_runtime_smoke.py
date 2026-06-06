from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
from ai22b.talent_foundry.llm_clients import LLMClient
from ai22b.talent_foundry.llm_runtime import build_llm_provider_preflight, build_llm_runtime_config


AGENT_RUNTIME_SMOKE_SCHEMA = "paideia-agent-runtime-smoke/v1"
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


def run_agent_runtime_smoke(
    *,
    engine: str,
    model: str | None = None,
    model_path: str | None = None,
    service: str | None = None,
    llm_mode: str = "offline",
    task: str = "Run a public-safe Paideia agent runtime smoke and leave a reviewable evidence packet.",
    client: LLMClient | None = None,
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
        return {
            "schema": AGENT_RUNTIME_SMOKE_SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "needs_configuration",
            "passed": False,
            "details": {
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
                "selected_tools": [],
                "completed_tools": [],
                "missing_required_tools": sorted(AGENT_RUNTIME_SMOKE_REQUIRED_TOOLS),
                "tool_statuses": {},
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
            },
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
    run = run_agent_from_manifest(
        _smoke_manifest(),
        task=task,
        runtime_config=runtime_config,
        llm_mode=llm_mode,
        llm_model=model,
        llm_client=client,
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
    completed_tools = _completed_tools(tool_execution)
    missing_required_tools = sorted(AGENT_RUNTIME_SMOKE_REQUIRED_TOOLS - set(completed_tools))
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
        "policy_authorization_model": policy_decision.get("capability_authorization", {}).get(
            "authorization_model"
        )
        if isinstance(policy_decision.get("capability_authorization"), dict)
        else None,
        "selected_tools": run.get("selected_tools", []),
        "completed_tools": completed_tools,
        "tool_statuses": _tool_statuses(tool_execution),
        "missing_required_tools": missing_required_tools,
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
        and details["llm_status"] in AGENT_RUNTIME_SMOKE_ACCEPTED_LLM_STATUSES
        and details["llm_plan_schema"] == "paideia-llm-reviewable-plan/v1"
        and details["tool_execution_model"] == "registered_capability_checked_local_tools_v1"
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
    return {
        "schema": AGENT_RUNTIME_SMOKE_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "passed": passed,
        "details": details,
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
