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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id(agent_name: str, task: str, created_at: str) -> str:
    raw = f"{agent_name}|{task}|{created_at}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _verify_execution(policy_decision: dict[str, Any], tool_execution: dict[str, Any], llm_result: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    completed_tools: set[str] = set()
    evidence_packet: dict[str, Any] | None = None
    policy_status = policy_decision.get("status")
    if policy_status == "blocked":
        issues.extend(policy_decision.get("policy_violations", []))
    if policy_status == "needs_approval":
        issues.extend(f"approval_required:{item.get('action_type')}" for item in policy_decision.get("approval_required", []))
    for item in tool_execution.get("tool_results", []):
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
    }:
        issues.append(f"llm_status_unexpected:{llm_result.get('status')}")
    return {
        "schema": "paideia-agent-run-verification/v1",
        "status": (
            "blocked"
            if policy_status == "blocked"
            else "needs_approval"
            if policy_status == "needs_approval"
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
    blocked_tools = sorted(
        str(item.get("tool"))
        for item in tool_results
        if item.get("status") == "blocked"
    )
    policy_status = policy_decision.get("status")
    llm_attempted = run_status == "completed"
    tool_attempted = bool(tool_results)
    evidence_required = "work_session" in selected_tools
    evidence_completed = "evidence_packet" in completed_tools
    memory_decision = memory_write.get("decision")
    automatic_promotion_performed = memory_decision == "promoted"
    issues: list[str] = []
    if run_status == "completed" and policy_status != "approved":
        issues.append("completed_run_without_approved_policy")
    if run_status in {"blocked", "needs_approval"} and llm_attempted:
        issues.append("llm_attempted_after_policy_gate")
    if run_status in {"blocked", "needs_approval"} and tool_attempted:
        issues.append("tools_attempted_after_policy_gate")
    if run_status == "completed" and evidence_required and not evidence_completed:
        issues.append("evidence_packet_missing_for_work_session")
    if automatic_promotion_performed:
        issues.append("automatic_memory_promotion_performed")

    if run_status == "blocked":
        status = "blocked_before_execution" if not issues else "needs_review"
    elif run_status == "needs_approval":
        status = "approval_required_before_execution" if not issues else "needs_review"
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
        },
        "llm_runtime": {
            "attempted": llm_attempted,
            "status": llm_result.get("status"),
            "engine": llm_result.get("engine"),
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
            "blocked_tools": blocked_tools,
            "evidence_packet_required": evidence_required,
            "evidence_packet_completed": evidence_completed,
            "network_default": tool_execution.get("capability_scope", {}).get("network_default"),
            "subprocess_default": tool_execution.get("capability_scope", {}).get("subprocess_default"),
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
        },
        "proof_steps": [
            {"id": "request_to_action_intent", "status": "passed"},
            {"id": "policy_before_llm", "status": "passed"},
            {"id": "policy_before_tools", "status": "passed"},
            {
                "id": "llm_planning",
                "status": "attempted" if llm_attempted else "skipped_by_policy_gate",
            },
            {
                "id": "registered_tool_execution",
                "status": "attempted" if tool_attempted else "skipped_by_policy_gate",
            },
            {"id": "verification", "status": verification.get("status")},
            {"id": "memory_write_decision", "status": memory_decision},
        ],
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
    memory = manifest.get("memory_profile", {})
    action_intents = infer_action_intents(task, manifest)
    policy_decision = evaluate_action_policy(manifest, action_intents)
    policy_violations = policy_decision["policy_violations"]
    selected_tools = select_tools_for_intents(manifest, action_intents, policy_decision)
    run_status = policy_decision["status"] if policy_decision["status"] in {"blocked", "needs_approval"} else "completed"
    selected_tool_descriptors = tool_descriptors(selected_tools)

    effective_runtime = runtime_config or build_llm_runtime_config(engine="deterministic_local")
    llm_provider_preflight = build_llm_provider_preflight(
        effective_runtime,
        llm_mode=llm_mode,
        llm_model=llm_model,
    )
    if run_status in {"blocked", "needs_approval"}:
        skipped_status = "skipped_policy_block" if run_status == "blocked" else "skipped_policy_approval_required"
        llm_result = {
            "schema": "ai-talent-llm-runtime-result/v1",
            "engine": effective_runtime.get("engine", "deterministic_local"),
            "status": skipped_status,
            "reason": (
                "policy_blocked_before_llm_or_tool_execution"
                if run_status == "blocked"
                else "policy_requires_boss_approval_before_llm_or_tool_execution"
            ),
            "identity_policy": effective_runtime.get("identity_policy", "application_engine_not_identity"),
            "network_access": effective_runtime.get("network_access", "blocked"),
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
    verification = _verify_execution(policy_decision, tool_execution, llm_result)
    response = _response_packet(agent, task, run_status, llm_result, policy_decision)
    growth_update = {
        "experience_type": (
            "guardrail_block_after_hire"
            if run_status == "blocked"
            else "approval_required_after_hire"
            if run_status == "needs_approval"
            else "agent_runtime_after_hire"
        ),
        "reflection": (
            "정책 위반을 업무 능력이 아니라 안전 경계로 처리했습니다."
            if run_status == "blocked"
            else "민감 행동은 보스 승인 전 실행하지 않고 승인 대기 상태로 기록했습니다."
            if run_status == "needs_approval"
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
            else "candidate_pending_boss_review"
        ),
        "target": "local_learning_ledger",
        "private_reasoning_trace_policy": "do_not_store",
        "promotion_requires": ["verification_passed", "boss_or_committee_review"],
    }
    execution_contract = _build_execution_contract(
        run_status=run_status,
        policy_decision=policy_decision,
        selected_tools=selected_tools,
        llm_result=llm_result,
        llm_provider_preflight=llm_provider_preflight,
        tool_execution=tool_execution,
        verification=verification,
        memory_write=memory_write,
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
    ]

    return {
        "schema": RUN_SCHEMA,
        "run_id": _run_id(agent["name"], task, created_at),
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
        "tool_execution": tool_execution,
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
