from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.action_policy import (
    evaluate_action_policy,
    infer_action_intents,
    select_tools_for_intents,
)
from ai22b.talent_foundry.llm_clients import LLMClient
from ai22b.talent_foundry.llm_runtime import (
    build_llm_provider_preflight,
    build_llm_runtime_config,
    invoke_llm_application_engine,
)
from ai22b.talent_foundry.runtime_observability import build_agent_runtime_observability
from ai22b.talent_foundry.tool_registry import execute_registered_tools, tool_descriptors


RUN_SCHEMA = "ai-talent-agent-run/v1"
EXECUTION_CONTRACT_SCHEMA = "paideia-agent-execution-contract/v1"
LLM_TOOL_PLAN_ALIGNMENT_SCHEMA = "paideia-llm-tool-plan-alignment/v1"
MEMORY_REVIEW_CANDIDATE_SCHEMA = "paideia-memory-review-candidate/v1"
TOOL_EXECUTION_STATUS_CARD_SCHEMA = "paideia-tool-execution-status-card/v1"
AGENT_RUNTIME_STATUS_CARD_SCHEMA = "paideia-agent-runtime-status-card/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id(agent_name: str, task: str, created_at: str) -> str:
    raw = f"{agent_name}|{task}|{created_at}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _compact_text(value: Any, *, limit: int = 500) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _verify_execution(policy_decision: dict[str, Any], tool_execution: dict[str, Any], llm_result: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    completed_tools: set[str] = set()
    evidence_packet: dict[str, Any] | None = None
    policy_status = policy_decision.get("status")
    provider_not_ready = llm_result.get("status") == "skipped_provider_not_ready"
    if policy_status == "blocked":
        issues.extend(policy_decision.get("policy_violations", []))
    if policy_status == "needs_approval":
        issues.extend(f"approval_required:{item.get('action_type')}" for item in policy_decision.get("approval_required", []))
    for item in tool_execution.get("tool_results", []):
        scope = item.get("capability_scope", {}) if isinstance(item.get("capability_scope"), dict) else {}
        if item.get("status") == "skipped" and scope.get("registered") is False:
            issues.append(f"unregistered_tool_selected:{item.get('tool')}")
            continue
        if item.get("status") not in {"completed", "skipped"}:
            issues.append(f"tool_failed:{item.get('tool')}")
            continue
        if item.get("status") == "completed":
            completed_tools.add(str(item.get("tool")))
            if item.get("tool") == "evidence_packet":
                evidence_packet = item.get("output", {})
    if "work_session" in completed_tools and "evidence_packet" not in completed_tools:
        issues.append("missing_evidence_packet_for_research_tool")
    if evidence_packet is not None:
        if evidence_packet.get("schema") != "paideia-tool-evidence-packet/v1":
            issues.append("evidence_packet_schema_invalid")
        checklist = evidence_packet.get("checklist", [])
        if not checklist:
            issues.append("evidence_packet_checklist_missing")
        if any(item.get("status") == "failed" for item in checklist if isinstance(item, dict)):
            issues.append("evidence_packet_checklist_failed")
    if llm_result.get("status") not in {
        "completed",
        "bridge_context_prepared",
        "adapter_manifest_ready",
        "unavailable",
        "skipped_policy_block",
        "skipped_policy_approval_required",
        "skipped_provider_not_ready",
    }:
        issues.append(f"llm_status_unexpected:{llm_result.get('status')}")
    if llm_result.get("status") in {"completed", "bridge_context_prepared", "adapter_manifest_ready"}:
        llm_plan = llm_result.get("llm_plan", {})
        if not isinstance(llm_plan, dict) or llm_plan.get("schema") != "paideia-llm-reviewable-plan/v1":
            issues.append("llm_reviewable_plan_missing")
    return {
        "schema": "paideia-agent-run-verification/v1",
        "status": (
            "blocked"
            if policy_status == "blocked"
            else "needs_approval"
            if policy_status == "needs_approval"
            else "skipped_provider_not_ready"
            if provider_not_ready and not issues
            else ("passed" if not issues else "needs_review")
        ),
        "issues": issues,
        "checks": {
            "policy_checked_before_tools": True,
            "capability_grants_enforced": True,
            "evidence_packet_required_for_research_tool": True,
            "hidden_chain_of_thought_not_stored": True,
            "boss_review_required_for_learning_promotion": True,
        },
    }


def _build_llm_tool_plan_alignment(
    *,
    llm_result: dict[str, Any],
    selected_tools: list[str],
    tool_execution: dict[str, Any],
) -> dict[str, Any]:
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
    raw_plan = llm_plan.get("tool_plan", []) if isinstance(llm_plan.get("tool_plan"), list) else []
    planned_tools: list[dict[str, Any]] = []
    out_of_scope_suggestions: list[dict[str, Any]] = []
    selected = set(selected_tools)
    completed = {
        str(item.get("tool"))
        for item in tool_execution.get("tool_results", [])
        if isinstance(item, dict) and item.get("status") == "completed"
    }
    for item in raw_plan:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool", "")).strip()
        if not tool:
            continue
        record = {
            "tool": tool,
            "registration_status": item.get("registration_status"),
            "execution_policy": item.get("execution_policy"),
            "selected_by_policy": tool in selected,
            "executed_by_registry": tool in completed,
            "requires_boss_approval": bool(item.get("requires_boss_approval", False)),
        }
        planned_tools.append(record)
        if tool not in selected or item.get("registration_status") != "registered":
            out_of_scope_suggestions.append(record)

    out_of_scope_executed = [
        item
        for item in out_of_scope_suggestions
        if item["executed_by_registry"]
    ]
    return {
        "schema": LLM_TOOL_PLAN_ALIGNMENT_SCHEMA,
        "llm_plan_schema": llm_plan.get("schema"),
        "llm_plan_policy": llm_plan.get("tool_plan_policy"),
        "selected_tools": selected_tools,
        "completed_tools": sorted(completed),
        "planned_tools": planned_tools,
        "planned_tool_count": len(planned_tools),
        "out_of_scope_suggestions": out_of_scope_suggestions,
        "out_of_scope_suggestion_count": len(out_of_scope_suggestions),
        "out_of_scope_executed_count": len(out_of_scope_executed),
        "suggestion_only_enforced": len(out_of_scope_executed) == 0,
        "execution_authority": "policy_selected_registered_tool_executor",
        "private_reasoning_trace": "do_not_store",
    }


def _build_memory_review_candidate(
    *,
    run_id: str,
    agent: dict[str, Any],
    task: str,
    run_status: str,
    policy_decision: dict[str, Any],
    llm_result: dict[str, Any],
    tool_execution: dict[str, Any],
    verification: dict[str, Any],
    llm_tool_plan_alignment: dict[str, Any],
) -> dict[str, Any]:
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
    completed_tools = [
        str(item.get("tool"))
        for item in tool_execution.get("tool_results", [])
        if isinstance(item, dict) and item.get("status") == "completed"
    ]
    candidate_payload = {
        "run_id": run_id,
        "agent_name": agent.get("name"),
        "task": task,
        "run_status": run_status,
        "llm_plan_digest_sha256": _digest(llm_plan),
        "tool_execution_digest_sha256": _digest(tool_execution),
        "policy_decision_digest_sha256": _digest(policy_decision),
        "verification_digest_sha256": _digest(verification),
    }
    return {
        "schema": MEMORY_REVIEW_CANDIDATE_SCHEMA,
        "candidate_id": hashlib.sha256(json.dumps(candidate_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16],
        "source_run_id": run_id,
        "source_run_status": run_status,
        "agent": {
            "name": agent.get("name"),
            "role": agent.get("role"),
            "major_goal": agent.get("major_goal"),
        },
        "target": "local_learning_ledger",
        "candidate_type": "post_run_experience_summary",
        "summary": _compact_text(llm_plan.get("assistant_reply") or llm_result.get("draft") or task),
        "reviewable_reasoning_summary": llm_plan.get("reviewable_reasoning_summary", [])
        if isinstance(llm_plan.get("reviewable_reasoning_summary"), list)
        else [],
        "evidence": {
            "policy_status": policy_decision.get("status"),
            "verification_status": verification.get("status"),
            "completed_tools": completed_tools,
            "llm_plan_digest_sha256": candidate_payload["llm_plan_digest_sha256"],
            "tool_execution_digest_sha256": candidate_payload["tool_execution_digest_sha256"],
            "policy_decision_digest_sha256": candidate_payload["policy_decision_digest_sha256"],
            "verification_digest_sha256": candidate_payload["verification_digest_sha256"],
            "llm_tool_plan_alignment_digest_sha256": _digest(llm_tool_plan_alignment),
        },
        "promotion_gate": {
            "automatic_promotion_allowed": False,
            "requires": ["verification_passed", "boss_or_committee_review"],
            "review_label_required": True,
        },
        "retention_policy": {
            "private_reasoning_trace": "do_not_store",
            "raw_provider_text_stored": False,
            "full_session_replay_stored": False,
            "safe_reference_detail": "summary_and_digests_only",
        },
    }


def _response_packet(agent: dict[str, Any], task: str, run_status: str, llm_result: dict[str, Any], policy_decision: dict[str, Any]) -> dict[str, Any]:
    if run_status == "blocked":
        return {
            "summary": (
                f"{agent['name']}은 보스의 로컬 정책에 따라 금지된 실행 요청을 차단했습니다. "
                "리서치나 초안 작성으로 범위를 바꾸면 다시 수행할 수 있습니다."
            ),
            "next_actions": [
                "투자 실행, 주문, 외부 업로드는 직접 수행하지 않습니다.",
                "필요하면 보스 승인 후 별도 안전 절차에서만 검토합니다.",
                "허용 가능한 범위는 조사, 비교, 리스크 정리, 문서 초안 작성입니다.",
            ],
            "runtime_target": "local_cli_runtime",
            "blocked_reasons": policy_decision.get("policy_violations", []),
        }
    if run_status == "needs_approval":
        return {
            "summary": (
                f"{agent['name']}은 보스 승인 없이 민감 행동을 실행할 수 없어 '{task}' 요청을 승인 대기 상태로 멈췄습니다. "
                "승인 전에는 LLM 계획, 로컬 도구 실행, 메모리 승격을 진행하지 않습니다."
            ),
            "next_actions": [
                "요청 범위를 로컬 조사나 초안 작성으로 낮추면 바로 실행할 수 있습니다.",
                "외부 업로드, 공개 배포, 금융 행동은 별도 승인 절차를 먼저 거쳐야 합니다.",
                "승인 대기 기록은 감사 로그와 memory quarantine 후보로만 남깁니다.",
            ],
            "runtime_target": "local_cli_runtime",
            "approval_required": policy_decision.get("approval_required", []),
        }
    if run_status == "needs_configuration":
        return {
            "summary": (
                f"{agent['name']} cannot start the live agent loop yet because the selected LLM provider is not configured. "
                "No LLM planning, registered tool execution, or memory candidate write was performed."
            ),
            "next_actions": [
                "Run doctor-llm-provider with --live-check after setting the provider key or local endpoint.",
                "Use offline mode for a deterministic local runtime check.",
                "Retry this agent run only after provider readiness is explicit.",
            ],
            "runtime_target": "local_cli_runtime",
            "configuration_required": {
                "reason": llm_result.get("reason"),
                "provider_preflight_status": llm_result.get("llm_provider_preflight", {}).get("status")
                if isinstance(llm_result.get("llm_provider_preflight"), dict)
                else None,
            },
        }
    draft = str(llm_result.get("draft", "")).strip()
    return {
        "summary": (
            draft
            or f"{agent['name']}은 매니페스트, 기억 프로필, action policy, LLM runtime을 순서대로 적용해 '{task}' 업무를 정리했습니다."
        ),
        "next_actions": [
            "근거와 검증 기준을 먼저 확인합니다.",
            "허용된 로컬 도구만 사용하고 민감 행동은 보스 승인 전 차단합니다.",
            "업무 결과를 검토 가능한 성장 후보로 남깁니다.",
        ],
        "runtime_target": "local_cli_runtime",
    }


def _build_execution_contract(
    *,
    run_status: str,
    policy_decision: dict[str, Any],
    selected_tools: list[str],
    llm_result: dict[str, Any],
    llm_provider_preflight: dict[str, Any],
    tool_execution: dict[str, Any],
    llm_tool_plan_alignment: dict[str, Any],
    verification: dict[str, Any],
    memory_write: dict[str, Any],
) -> dict[str, Any]:
    tool_results = tool_execution.get("tool_results", [])
    completed_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if item.get("status") == "completed"
    )
    skipped_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if item.get("status") == "skipped"
    )
    unregistered_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if item.get("status") == "skipped"
        and isinstance(item.get("capability_scope"), dict)
        and item.get("capability_scope", {}).get("registered") is False
    )
    blocked_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if item.get("status") == "blocked"
    )
    policy_status = policy_decision.get("status")
    capability_authorization = policy_decision.get("capability_authorization", {})
    capability_authorization = capability_authorization if isinstance(capability_authorization, dict) else {}
    authorization_invariants = capability_authorization.get("invariants", {})
    llm_attempted = run_status == "completed"
    tool_attempted = bool(tool_results)
    provider_not_ready = run_status == "needs_configuration"
    evidence_required = "work_session" in selected_tools
    evidence_completed = "evidence_packet" in completed_tools
    memory_decision = memory_write.get("decision")
    automatic_promotion_performed = bool(memory_write.get("automatic_promotion_performed", memory_decision == "promoted"))
    review_candidate = memory_write.get("review_candidate", {})
    review_candidate = review_candidate if isinstance(review_candidate, dict) else {}
    review_candidate_promotion_gate = review_candidate.get("promotion_gate", {})
    review_candidate_retention = review_candidate.get("retention_policy", {})
    issues: list[str] = []
    if run_status == "completed" and policy_status != "approved":
        issues.append("completed_run_without_approved_policy")
    if capability_authorization.get("schema") != "paideia-capability-authorization/v1":
        issues.append("capability_authorization_missing")
    if capability_authorization.get("mode") != "deny_by_default":
        issues.append("capability_authorization_mode_invalid")
    if authorization_invariants.get("registered_tool_executor_is_execution_authority") is not True:
        issues.append("capability_authorization_execution_authority_invalid")
    if authorization_invariants.get("llm_tool_suggestions_are_non_authoritative") is not True:
        issues.append("capability_authorization_llm_boundary_invalid")
    if run_status in {"blocked", "needs_approval", "needs_configuration"} and llm_attempted:
        issues.append("llm_attempted_after_policy_gate")
    if run_status in {"blocked", "needs_approval", "needs_configuration"} and tool_attempted:
        issues.append("tools_attempted_after_policy_gate")
    if provider_not_ready and llm_result.get("status") != "skipped_provider_not_ready":
        issues.append("provider_configuration_skip_status_invalid")
    if provider_not_ready and llm_provider_preflight.get("status") != "needs_configuration":
        issues.append("provider_configuration_preflight_status_invalid")
    if run_status == "completed" and evidence_required and not evidence_completed:
        issues.append("evidence_packet_missing_for_work_session")
    if unregistered_tools:
        issues.extend(f"unregistered_tool_selected:{tool}" for tool in unregistered_tools)
    if llm_tool_plan_alignment.get("suggestion_only_enforced") is not True:
        issues.append("llm_tool_plan_suggestion_boundary_failed")
    if automatic_promotion_performed:
        issues.append("automatic_memory_promotion_performed")
    if not provider_not_ready:
        if review_candidate.get("schema") != MEMORY_REVIEW_CANDIDATE_SCHEMA:
            issues.append("memory_review_candidate_missing")
        if review_candidate.get("target") != "local_learning_ledger":
            issues.append("memory_review_candidate_target_invalid")
        if review_candidate_promotion_gate.get("automatic_promotion_allowed") is not False:
            issues.append("memory_review_candidate_allows_automatic_promotion")
        if "boss_or_committee_review" not in review_candidate_promotion_gate.get("requires", []):
            issues.append("memory_review_candidate_review_gate_missing")
        if review_candidate_retention.get("private_reasoning_trace") != "do_not_store":
            issues.append("memory_review_candidate_private_trace_policy_invalid")
        if review_candidate_retention.get("raw_provider_text_stored") is not False:
            issues.append("memory_review_candidate_raw_provider_text_policy_invalid")

    if run_status == "blocked":
        status = "blocked_before_execution" if not issues else "needs_review"
    elif run_status == "needs_approval":
        status = "approval_required_before_execution" if not issues else "needs_review"
    elif run_status == "needs_configuration":
        status = "provider_configuration_required_before_execution" if not issues else "needs_review"
    else:
        status = "passed" if not issues and verification.get("status") == "passed" else "needs_review"

    return {
        "schema": EXECUTION_CONTRACT_SCHEMA,
        "status": status,
        "issues": issues,
        "policy_gate": {
            "status": policy_status,
            "decision_model": policy_decision.get("decision_model"),
            "checked_before_llm": True,
            "checked_before_tools": True,
            "denied_count": len(policy_decision.get("denied_actions", [])),
            "approval_required_count": len(policy_decision.get("approval_required", [])),
            "boss_approval_accepted_count": policy_decision.get("boss_approval_gate", {}).get("accepted_count", 0),
            "capability_authorization_schema": capability_authorization.get("schema"),
            "capability_authorization_model": capability_authorization.get("authorization_model"),
            "tool_executable_capabilities": capability_authorization.get("tool_executable_capabilities", []),
            "llm_tool_suggestions_are_non_authoritative": authorization_invariants.get(
                "llm_tool_suggestions_are_non_authoritative"
            ),
            "registered_tool_executor_is_execution_authority": authorization_invariants.get(
                "registered_tool_executor_is_execution_authority"
            ),
        },
        "llm_runtime": {
            "attempted": llm_attempted,
            "status": llm_result.get("status"),
            "engine": llm_result.get("engine"),
            "reviewable_plan_schema": llm_result.get("llm_plan", {}).get("schema")
            if isinstance(llm_result.get("llm_plan"), dict)
            else None,
            "reviewable_plan_source": llm_result.get("llm_plan", {}).get("source")
            if isinstance(llm_result.get("llm_plan"), dict)
            else None,
            "skip_reason": None if llm_attempted else llm_result.get("reason"),
            "identity_policy": llm_result.get("identity_policy"),
            "provider_preflight_status": llm_provider_preflight.get("status"),
            "provider_live_check_performed": llm_provider_preflight.get("live_check_performed"),
        },
        "tool_execution": {
            "attempted": tool_attempted,
            "execution_model": tool_execution.get("execution_model"),
            "selected_count": len(selected_tools),
            "completed_tools": completed_tools,
            "skipped_tools": skipped_tools,
            "unregistered_tools": unregistered_tools,
            "blocked_tools": blocked_tools,
            "evidence_packet_required": evidence_required,
            "evidence_packet_completed": evidence_completed,
            "network_default": tool_execution.get("capability_scope", {}).get("network_default"),
            "subprocess_default": tool_execution.get("capability_scope", {}).get("subprocess_default"),
        },
        "llm_tool_plan_alignment": {
            "schema": llm_tool_plan_alignment.get("schema"),
            "suggestion_only_enforced": llm_tool_plan_alignment.get("suggestion_only_enforced"),
            "planned_tool_count": llm_tool_plan_alignment.get("planned_tool_count"),
            "out_of_scope_suggestion_count": llm_tool_plan_alignment.get("out_of_scope_suggestion_count"),
            "out_of_scope_executed_count": llm_tool_plan_alignment.get("out_of_scope_executed_count"),
            "execution_authority": llm_tool_plan_alignment.get("execution_authority"),
        },
        "verification_gate": {
            "status": verification.get("status"),
            "issues": verification.get("issues", []),
        },
        "memory_write": {
            "decision": memory_decision,
            "automatic_promotion_performed": automatic_promotion_performed,
            "promotion_requires": memory_write.get("promotion_requires", []),
            "private_reasoning_trace_policy": memory_write.get("private_reasoning_trace_policy"),
            "review_candidate_schema": review_candidate.get("schema"),
            "review_candidate_id": review_candidate.get("candidate_id"),
            "review_candidate_target": review_candidate.get("target"),
            "review_candidate_source_status": review_candidate.get("source_run_status"),
            "review_candidate_automatic_promotion_allowed": review_candidate_promotion_gate.get(
                "automatic_promotion_allowed"
            ),
            "review_candidate_promotion_requires": review_candidate_promotion_gate.get("requires", []),
            "review_candidate_private_reasoning_trace": review_candidate_retention.get("private_reasoning_trace"),
            "review_candidate_raw_provider_text_stored": review_candidate_retention.get("raw_provider_text_stored"),
        },
        "proof_steps": [
            {"id": "request_to_action_intent", "status": "passed"},
            {"id": "policy_before_llm", "status": "passed"},
            {"id": "policy_before_tools", "status": "passed"},
            {
                "id": "llm_planning",
                "status": (
                    "attempted"
                    if llm_attempted
                    else "skipped_provider_not_ready"
                    if provider_not_ready
                    else "skipped_by_policy_gate"
                ),
            },
            {
                "id": "registered_tool_execution",
                "status": (
                    "attempted"
                    if tool_attempted
                    else "skipped_provider_not_ready"
                    if provider_not_ready
                    else "skipped_by_policy_gate"
                ),
            },
            {"id": "verification", "status": verification.get("status")},
            {"id": "memory_write_decision", "status": memory_decision},
        ],
    }


def _build_tool_execution_status_card(
    *,
    run_status: str,
    policy_decision: dict[str, Any],
    selected_tools: list[str],
    tool_execution: dict[str, Any],
    verification: dict[str, Any],
    execution_contract: dict[str, Any],
) -> dict[str, Any]:
    tool_results = tool_execution.get("tool_results", []) if isinstance(tool_execution.get("tool_results"), list) else []
    completed_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if isinstance(item, dict) and item.get("status") == "completed"
    )
    skipped_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if isinstance(item, dict) and item.get("status") == "skipped"
    )
    blocked_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if isinstance(item, dict) and item.get("status") == "blocked"
    )
    unregistered_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if isinstance(item, dict)
        and item.get("status") == "skipped"
        and isinstance(item.get("capability_scope"), dict)
        and item.get("capability_scope", {}).get("registered") is False
    )
    capability_scope = tool_execution.get("capability_scope", {})
    capability_scope = capability_scope if isinstance(capability_scope, dict) else {}
    evidence_required = "work_session" in selected_tools
    evidence_completed = "evidence_packet" in completed_tools
    if run_status == "blocked":
        status = "skipped_policy_block"
    elif run_status == "needs_approval":
        status = "skipped_pending_boss_approval"
    elif run_status == "needs_configuration":
        status = "skipped_provider_not_ready"
    elif blocked_tools or unregistered_tools or execution_contract.get("status") == "needs_review":
        status = "needs_review"
    elif selected_tools and verification.get("status") == "passed":
        status = "completed_verified"
    elif not selected_tools:
        status = "no_tools_selected"
    else:
        status = "needs_review"
    tool_cards: list[dict[str, Any]] = []
    for item in tool_results:
        if not isinstance(item, dict):
            continue
        scope = item.get("capability_scope", {}) if isinstance(item.get("capability_scope"), dict) else {}
        tool_cards.append(
            {
                "tool": item.get("tool"),
                "status": item.get("status"),
                "capability": item.get("capability"),
                "registered": scope.get("registered"),
                "capability_granted": scope.get("capability_granted"),
                "network": scope.get("network"),
                "subprocess": scope.get("subprocess"),
                "output_schema": item.get("output", {}).get("schema") if isinstance(item.get("output"), dict) else None,
            }
        )
    next_actions = (
        ["Review the evidence packet and memory review candidate before promoting this run."]
        if status == "completed_verified"
        else [
            "Inspect the policy gate and execution contract before retrying.",
            "Grant only reviewed capabilities and keep network/subprocess blocked by default.",
        ]
        if status == "needs_review"
        else [
            "Resolve provider or policy gate first, then rerun the agent loop.",
        ]
    )
    return {
        "schema": TOOL_EXECUTION_STATUS_CARD_SCHEMA,
        "status": status,
        "execution_model": tool_execution.get("execution_model"),
        "policy_status": policy_decision.get("status"),
        "run_status": run_status,
        "attempted": bool(tool_results),
        "selected_tools": selected_tools,
        "selected_count": len(selected_tools),
        "completed_tools": completed_tools,
        "skipped_tools": skipped_tools,
        "blocked_tools": blocked_tools,
        "unregistered_tools": unregistered_tools,
        "tool_cards": tool_cards,
        "evidence_packet": {
            "required": evidence_required,
            "completed": evidence_completed,
        },
        "capability_scope": {
            "schema": capability_scope.get("schema"),
            "mode": capability_scope.get("mode"),
            "granted_capabilities": capability_scope.get("granted_capabilities", []),
            "network_default": capability_scope.get("network_default"),
            "subprocess_default": capability_scope.get("subprocess_default"),
            "private_reasoning_trace": capability_scope.get("private_reasoning_trace"),
        },
        "verification": {
            "status": verification.get("status"),
            "issues": verification.get("issues", []),
            "execution_contract_status": execution_contract.get("status"),
        },
        "public_safe": {
            "registered_tool_executor_is_authority": True,
            "llm_tool_suggestions_are_non_authoritative": True,
            "network_default": capability_scope.get("network_default", "blocked"),
            "subprocess_default": capability_scope.get("subprocess_default", "blocked"),
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "external_side_effects_performed": False,
        },
        "user_visible_summary": {
            "ko": (
                "등록 도구 실행이 검증됐고 evidence packet이 준비됐습니다."
                if status == "completed_verified"
                else "등록 도구 실행 결과에 검토가 필요합니다."
                if status == "needs_review"
                else "정책, 승인, 또는 provider 설정 때문에 도구 실행을 시작하지 않았습니다."
            ),
            "en": (
                "Registered tool execution was verified and the evidence packet is ready."
                if status == "completed_verified"
                else "Registered tool execution needs review."
                if status == "needs_review"
                else "Tool execution did not start because policy, approval, or provider setup blocked the run."
            ),
        },
        "next_actions": next_actions,
    }


def _build_agent_runtime_status_card(
    *,
    run_status: str,
    policy_decision: dict[str, Any],
    selected_tools: list[str],
    llm_result: dict[str, Any],
    llm_provider_preflight: dict[str, Any],
    tool_execution_status_card: dict[str, Any],
    execution_contract: dict[str, Any],
    verification: dict[str, Any],
    memory_write: dict[str, Any],
    runtime_observability: dict[str, Any],
) -> dict[str, Any]:
    policy_status = policy_decision.get("status")
    llm_status = llm_result.get("status")
    tool_status = tool_execution_status_card.get("status")
    verification_status = verification.get("status")
    contract_status = execution_contract.get("status")
    memory_decision = memory_write.get("decision")
    llm_contract = (
        llm_result.get("llm_client_contract", {})
        if isinstance(llm_result.get("llm_client_contract"), dict)
        else {}
    )
    if run_status == "blocked":
        status = "skipped_policy_block"
    elif run_status == "needs_approval":
        status = "skipped_pending_boss_approval"
    elif run_status == "needs_configuration":
        status = "skipped_provider_not_ready"
    elif contract_status == "passed" and verification_status == "passed":
        status = "completed_verified"
    else:
        status = "needs_review"

    public_safe = {
        "policy_checked_before_llm": execution_contract.get("policy_gate", {}).get("checked_before_llm") is True,
        "policy_checked_before_tools": execution_contract.get("policy_gate", {}).get("checked_before_tools") is True,
        "registered_tool_executor_is_authority": execution_contract.get("policy_gate", {}).get(
            "registered_tool_executor_is_execution_authority"
        )
        is True,
        "llm_tool_suggestions_are_non_authoritative": execution_contract.get("policy_gate", {}).get(
            "llm_tool_suggestions_are_non_authoritative"
        )
        is True,
        "network_default": tool_execution_status_card.get("capability_scope", {}).get("network_default", "blocked"),
        "subprocess_default": tool_execution_status_card.get("capability_scope", {}).get("subprocess_default", "blocked"),
        "raw_provider_payload_saved": False,
        "private_reasoning_trace": "do_not_store",
        "automatic_memory_promotion_performed": bool(memory_write.get("automatic_promotion_performed", False)),
        "external_side_effects_performed": tool_execution_status_card.get("public_safe", {}).get(
            "external_side_effects_performed",
            False,
        ),
    }
    passed_safety = (
        public_safe["policy_checked_before_llm"]
        and public_safe["policy_checked_before_tools"]
        and public_safe["registered_tool_executor_is_authority"]
        and public_safe["llm_tool_suggestions_are_non_authoritative"]
        and public_safe["network_default"] == "blocked"
        and public_safe["subprocess_default"] == "blocked"
        and public_safe["raw_provider_payload_saved"] is False
        and public_safe["automatic_memory_promotion_performed"] is False
        and public_safe["external_side_effects_performed"] is False
    )

    return {
        "schema": AGENT_RUNTIME_STATUS_CARD_SCHEMA,
        "status": status,
        "run_status": run_status,
        "created_at_utc": _now(),
        "loop": {
            "request_to_action_intent": "passed",
            "policy_before_llm": "passed",
            "policy_before_tools": "passed",
            "llm_planning": "attempted" if run_status == "completed" else "skipped",
            "registered_tool_execution": "attempted" if bool(tool_execution_status_card.get("attempted")) else "skipped",
            "verification": verification_status,
            "memory_write_decision": memory_decision,
        },
        "policy_gate": {
            "status": policy_status,
            "decision_model": policy_decision.get("decision_model"),
            "denied_count": len(policy_decision.get("denied_actions", [])),
            "approval_required_count": len(policy_decision.get("approval_required", [])),
            "capability_authorization_model": execution_contract.get("policy_gate", {}).get(
                "capability_authorization_model"
            ),
        },
        "llm_runtime": {
            "status": llm_status,
            "engine": llm_result.get("engine"),
            "attempted": execution_contract.get("llm_runtime", {}).get("attempted"),
            "provider_preflight_status": llm_provider_preflight.get("status"),
            "provider_live_check_performed": llm_provider_preflight.get("live_check_performed"),
            "llm_client_contract_schema": llm_contract.get("schema"),
            "llm_client_contract_status": llm_contract.get("status"),
            "client_result_summary_only": llm_contract.get("client_result_summary_only"),
        },
        "tool_execution": {
            "status": tool_status,
            "selected_count": len(selected_tools),
            "completed_count": len(tool_execution_status_card.get("completed_tools", [])),
            "evidence_packet_completed": tool_execution_status_card.get("evidence_packet", {}).get("completed"),
            "unregistered_tools": tool_execution_status_card.get("unregistered_tools", []),
            "external_side_effects_performed": public_safe["external_side_effects_performed"],
        },
        "verification": {
            "status": verification_status,
            "execution_contract_status": contract_status,
            "issues": verification.get("issues", []),
        },
        "memory": {
            "decision": memory_decision,
            "review_candidate_schema": memory_write.get("review_candidate", {}).get("schema")
            if isinstance(memory_write.get("review_candidate"), dict)
            else None,
            "promotion_requires": memory_write.get("promotion_requires", []),
            "automatic_promotion_performed": bool(memory_write.get("automatic_promotion_performed", False)),
            "private_reasoning_trace_policy": memory_write.get("private_reasoning_trace_policy"),
        },
        "observability": {
            "schema": runtime_observability.get("schema"),
            "selected_memory_count": runtime_observability.get("context", {}).get("selected_memory_count")
            if isinstance(runtime_observability.get("context"), dict)
            else None,
            "estimated_prompt_tokens": runtime_observability.get("context", {}).get(
                "prompt_context_estimated_tokens"
            )
            if isinstance(runtime_observability.get("context"), dict)
            else None,
        },
        "public_safe": {
            **public_safe,
            "passed": passed_safety,
        },
        "user_visible_summary": {
            "ko": (
                "정책, LLM 계획, 등록 도구, 검증, 메모리 후보 기록까지 P0 실행 루프가 검증됐습니다."
                if status == "completed_verified"
                else "정책 또는 provider 설정 때문에 P0 실행 루프가 시작 전 안전하게 멈췄습니다."
                if status in {"skipped_policy_block", "skipped_pending_boss_approval", "skipped_provider_not_ready"}
                else "P0 실행 루프 결과에 검토가 필요합니다."
            ),
            "en": (
                "The P0 execution loop was verified across policy, LLM planning, registered tools, verification, and memory candidate writing."
                if status == "completed_verified"
                else "The P0 execution loop stopped safely before execution because policy or provider setup blocked it."
                if status in {"skipped_policy_block", "skipped_pending_boss_approval", "skipped_provider_not_ready"}
                else "The P0 execution loop needs review."
            ),
        },
        "next_actions": (
            ["Review the evidence packet and memory candidate before promoting this experience."]
            if status == "completed_verified"
            else ["Resolve the blocking policy, approval, or provider readiness issue before rerunning."]
            if status in {"skipped_policy_block", "skipped_pending_boss_approval", "skipped_provider_not_ready"}
            else ["Inspect execution_contract, tool_execution_status_card, and verification issues."]
        ),
    }


def run_agent_execution_loop(
    manifest: dict[str, Any],
    *,
    task: str,
    runtime_config: dict[str, Any] | None = None,
    llm_mode: str = "offline",
    llm_model: str | None = None,
    llm_client: LLMClient | None = None,
) -> dict[str, Any]:
    if manifest.get("schema") != "ai-talent-agent-manifest/v1":
        raise ValueError("Unsupported agent manifest schema")

    created_at = _now()
    agent = manifest["agent"]
    run_id = _run_id(agent["name"], task, created_at)
    memory = manifest.get("memory_profile", {})
    action_intents = infer_action_intents(task, manifest)
    policy_decision = evaluate_action_policy(manifest, action_intents)
    policy_violations = policy_decision["policy_violations"]
    selected_tools = select_tools_for_intents(manifest, action_intents, policy_decision)
    run_status = policy_decision["status"] if policy_decision["status"] in {"blocked", "needs_approval"} else "completed"

    effective_runtime = runtime_config or build_llm_runtime_config(engine="deterministic_local")
    llm_provider_preflight = build_llm_provider_preflight(
        effective_runtime,
        llm_mode=llm_mode,
        llm_model=llm_model,
    )
    provider_not_ready = (
        run_status == "completed"
        and llm_mode == "live"
        and llm_client is None
        and llm_provider_preflight.get("status") == "needs_configuration"
    )
    if provider_not_ready:
        run_status = "needs_configuration"
        selected_tools = []
    selected_tool_descriptors = tool_descriptors(selected_tools)

    if run_status in {"blocked", "needs_approval", "needs_configuration"}:
        skipped_status = (
            "skipped_policy_block"
            if run_status == "blocked"
            else "skipped_policy_approval_required"
            if run_status == "needs_approval"
            else "skipped_provider_not_ready"
        )
        llm_result = {
            "schema": "ai-talent-llm-runtime-result/v1",
            "engine": effective_runtime.get("engine", "deterministic_local"),
            "status": skipped_status,
            "reason": (
                "policy_blocked_before_llm_or_tool_execution"
                if run_status == "blocked"
                else "policy_requires_boss_approval_before_llm_or_tool_execution"
                if run_status == "needs_approval"
                else "live_provider_needs_configuration_before_agent_execution"
            ),
            "identity_policy": effective_runtime.get("identity_policy", "application_engine_not_identity"),
            "network_access": effective_runtime.get("network_access", "blocked"),
            "llm_mode": llm_mode,
            "llm_provider_preflight": llm_provider_preflight,
        }
    else:
        llm_result = invoke_llm_application_engine(
            effective_runtime,
            manifest=manifest,
            task=task,
            llm_mode=llm_mode,
            llm_model=llm_model,
            client=llm_client,
            policy_context=policy_decision,
            tools=selected_tool_descriptors,
        )
        llm_provider_preflight = llm_result.get("llm_provider_preflight", llm_provider_preflight)

    tool_execution = execute_registered_tools(
        selected_tools=selected_tools,
        manifest=manifest,
        task=task,
        llm_result=llm_result,
        policy_decision=policy_decision,
    )
    llm_tool_plan_alignment = _build_llm_tool_plan_alignment(
        llm_result=llm_result,
        selected_tools=selected_tools,
        tool_execution=tool_execution,
    )
    verification = _verify_execution(policy_decision, tool_execution, llm_result)
    response = _response_packet(agent, task, run_status, llm_result, policy_decision)
    growth_update = {
        "experience_type": (
            "guardrail_block_after_hire"
            if run_status == "blocked"
            else "approval_required_after_hire"
            if run_status == "needs_approval"
            else "provider_configuration_required_after_hire"
            if run_status == "needs_configuration"
            else "agent_runtime_after_hire"
        ),
        "reflection": (
            "정책 위반을 업무 능력이 아니라 안전 경계로 처리했습니다."
            if run_status == "blocked"
            else "민감 행동은 보스 승인 전 실행하지 않고 승인 대기 상태로 기록했습니다."
            if run_status == "needs_approval"
            else "선택한 live LLM provider가 준비되지 않아 LLM 계획, 도구 실행, 메모리 후보 생성을 시작하지 않았습니다."
            if run_status == "needs_configuration"
            else "action policy, LLM planning, capability-checked tools, verification을 하나의 실행 루프로 적용했습니다."
        ),
        "reasoning_delta": [
            "요청은 먼저 action intent로 구조화합니다.",
            "도구 실행은 capability grant와 보스 승인 정책을 통과해야 합니다.",
            "업무 경험은 검증 가능한 성장 후보로만 남깁니다.",
        ],
    }
    memory_write = {
        "schema": "paideia-memory-write-decision/v1",
        "decision": (
            "quarantine"
            if run_status == "blocked"
            else "pending_boss_approval"
            if run_status == "needs_approval"
            else "skipped_provider_not_ready"
            if run_status == "needs_configuration"
            else "candidate_pending_boss_review"
        ),
        "target": "none" if run_status == "needs_configuration" else "local_learning_ledger",
        "private_reasoning_trace_policy": "do_not_store",
        "promotion_requires": []
        if run_status == "needs_configuration"
        else ["verification_passed", "boss_or_committee_review"],
        "automatic_promotion_performed": False,
    }
    if run_status != "needs_configuration":
        memory_review_candidate = _build_memory_review_candidate(
            run_id=run_id,
            agent=agent,
            task=task,
            run_status=run_status,
            policy_decision=policy_decision,
            llm_result=llm_result,
            tool_execution=tool_execution,
            verification=verification,
            llm_tool_plan_alignment=llm_tool_plan_alignment,
        )
        memory_write["review_candidate"] = memory_review_candidate
    execution_contract = _build_execution_contract(
        run_status=run_status,
        policy_decision=policy_decision,
        selected_tools=selected_tools,
        llm_result=llm_result,
        llm_provider_preflight=llm_provider_preflight,
        tool_execution=tool_execution,
        llm_tool_plan_alignment=llm_tool_plan_alignment,
        verification=verification,
        memory_write=memory_write,
    )
    tool_execution_status_card = _build_tool_execution_status_card(
        run_status=run_status,
        policy_decision=policy_decision,
        selected_tools=selected_tools,
        tool_execution=tool_execution,
        verification=verification,
        execution_contract=execution_contract,
    )
    runtime_observability = build_agent_runtime_observability(
        manifest=manifest,
        task=task,
        memory=memory,
        selected_tools=selected_tools,
        policy_decision=policy_decision,
        tool_execution=tool_execution,
        llm_result=llm_result,
        verification=verification,
        memory_write=memory_write,
        llm_mode=llm_mode,
        runtime_config=effective_runtime,
    )
    agent_runtime_status_card = _build_agent_runtime_status_card(
        run_status=run_status,
        policy_decision=policy_decision,
        selected_tools=selected_tools,
        llm_result=llm_result,
        llm_provider_preflight=llm_provider_preflight,
        tool_execution_status_card=tool_execution_status_card,
        execution_contract=execution_contract,
        verification=verification,
        memory_write=memory_write,
        runtime_observability=runtime_observability,
    )
    audit_events = [
        {
            "recorded_at_utc": created_at,
            "event": "agent_execution_loop_started",
            "task_fingerprint": hashlib.sha256(task.encode("utf-8")).hexdigest()[:16],
        },
        *policy_decision.get("audit_events", []),
        {
            "recorded_at_utc": _now(),
            "event": "llm_runtime_invoked" if run_status == "completed" else "llm_runtime_skipped",
            "status": llm_result.get("status"),
            "engine": llm_result.get("engine"),
        },
        {
            "recorded_at_utc": _now(),
            "event": "tool_execution_verified",
            "status": verification["status"],
        },
        {
            "recorded_at_utc": _now(),
            "event": "runtime_observability_recorded",
            "estimated_prompt_tokens": runtime_observability["context"]["prompt_context_estimated_tokens"],
            "selected_memory_count": runtime_observability["context"]["selected_memory_count"],
        },
        {
            "recorded_at_utc": _now(),
            "event": "llm_provider_preflight_recorded",
            "status": llm_provider_preflight["status"],
            "live_check_performed": llm_provider_preflight["live_check_performed"],
        },
        {
            "recorded_at_utc": _now(),
            "event": "tool_execution_status_card_recorded",
            "status": tool_execution_status_card["status"],
            "completed_count": len(tool_execution_status_card["completed_tools"]),
            "blocked_count": len(tool_execution_status_card["blocked_tools"]),
        },
        {
            "recorded_at_utc": _now(),
            "event": "agent_runtime_status_card_recorded",
            "status": agent_runtime_status_card["status"],
            "policy_status": agent_runtime_status_card["policy_gate"]["status"],
            "llm_status": agent_runtime_status_card["llm_runtime"]["status"],
            "memory_decision": agent_runtime_status_card["memory"]["decision"],
        },
    ]

    return {
        "schema": RUN_SCHEMA,
        "run_id": run_id,
        "created_at_utc": created_at,
        "agent": {
            "name": agent["name"],
            "role": agent.get("role"),
            "major_goal": agent.get("major_goal"),
        },
        "task": task,
        "run_status": run_status,
        "llm_policy": manifest["llm_policy"],
        "llm_runtime_result": llm_result,
        "llm_provider_preflight": llm_provider_preflight,
        "selected_tools": selected_tools,
        "blocked_actions": manifest.get("tool_policy", {}).get("blocked_tools", []),
        "policy_violations": policy_violations,
        "tool_policy_enforced": True,
        "memory_applied": {
            "semantic_themes": memory.get("semantic_themes", []),
            "procedural_principles": memory.get("procedural_principles", []),
            "chain_of_thought_policy": memory.get("chain_of_thought_policy"),
        },
        "action_intents": action_intents,
        "policy_decision": policy_decision,
        "execution_loop": {
            "schema": "paideia-agent-execution-loop/v1",
            "steps": [
                "request",
                "action_intent_inference",
                "capability_policy",
                "llm_planning",
                "tool_execution",
                "verification",
                "memory_write_decision",
                "audit_log",
            ],
            "runtime_config": {
                "engine": effective_runtime.get("engine"),
                "llm_mode": llm_mode,
                "identity_policy": effective_runtime.get("identity_policy"),
            },
        },
        "execution_contract": execution_contract,
        "agent_runtime_status_card": agent_runtime_status_card,
        "tool_execution_status_card": tool_execution_status_card,
        "tool_execution": tool_execution,
        "llm_tool_plan_alignment": llm_tool_plan_alignment,
        "verification": verification,
        "memory_write": memory_write,
        "runtime_observability": runtime_observability,
        "audit_events": audit_events,
        "response": response,
        "growth_update": growth_update,
    }


def write_agent_run_log(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False) + "\n")
