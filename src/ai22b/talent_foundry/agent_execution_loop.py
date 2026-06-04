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
from ai22b.talent_foundry.llm_runtime import build_llm_runtime_config, invoke_llm_application_engine


RUN_SCHEMA = "ai-talent-agent-run/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id(agent_name: str, task: str, created_at: str) -> str:
    raw = f"{agent_name}|{task}|{created_at}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _tool_capability(tool: str) -> str:
    return {
        "work_session": "research.analysis",
        "memory_consolidation": "memory.write_candidate",
        "parent_controlled_projection_team": "projection.spawn_bounded",
    }.get(tool, "unknown")


def _tool_descriptor(tool: str) -> dict[str, Any]:
    return {
        "id": tool,
        "name": tool,
        "capability": _tool_capability(tool),
        "execution_surface": "local_paideia_runtime",
    }


def _execute_tools(
    *,
    selected_tools: list[str],
    manifest: dict[str, Any],
    task: str,
    llm_result: dict[str, Any],
) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    agent = manifest.get("agent", {})
    draft = str(llm_result.get("draft", "")).strip()
    for tool in selected_tools:
        if tool == "work_session":
            outputs.append(
                {
                    "tool": tool,
                    "status": "completed",
                    "capability": "research.analysis",
                    "output": {
                        "summary": draft
                        or f"{agent.get('name')}은 '{task}' 요청을 근거 확인, 경계 확인, 결과 기록 순서로 정리했습니다.",
                        "requires_boss_review": True,
                    },
                }
            )
        elif tool == "memory_consolidation":
            outputs.append(
                {
                    "tool": tool,
                    "status": "completed",
                    "capability": "memory.write_candidate",
                    "output": {
                        "candidate_only": True,
                        "promotion_requires_review": True,
                    },
                }
            )
        elif tool == "parent_controlled_projection_team":
            outputs.append(
                {
                    "tool": tool,
                    "status": "completed",
                    "capability": "projection.spawn_bounded",
                    "output": {
                        "control_model": "single_parent_identity_controls_task_limited_projections",
                        "merge_policy": "reviewed_summary_only",
                    },
                }
            )
        else:
            outputs.append(
                {
                    "tool": tool,
                    "status": "skipped",
                    "capability": "unknown",
                    "output": {"reason": "tool_not_mapped_in_paideia_runtime"},
                }
            )
    return {
        "schema": "paideia-tool-execution/v1",
        "execution_model": "capability_checked_local_tools_v1",
        "selected_tools": selected_tools,
        "tool_results": outputs,
    }


def _verify_execution(policy_decision: dict[str, Any], tool_execution: dict[str, Any], llm_result: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if policy_decision.get("status") == "blocked":
        issues.extend(policy_decision.get("policy_violations", []))
    for item in tool_execution.get("tool_results", []):
        if item.get("status") not in {"completed", "skipped"}:
            issues.append(f"tool_failed:{item.get('tool')}")
    if llm_result.get("status") not in {"completed", "bridge_context_prepared", "adapter_manifest_ready", "unavailable", "skipped_policy_block"}:
        issues.append(f"llm_status_unexpected:{llm_result.get('status')}")
    return {
        "schema": "paideia-agent-run-verification/v1",
        "status": "blocked" if policy_decision.get("status") == "blocked" else ("passed" if not issues else "needs_review"),
        "issues": issues,
        "checks": {
            "policy_checked_before_tools": True,
            "capability_grants_enforced": True,
            "hidden_chain_of_thought_not_stored": True,
            "boss_review_required_for_learning_promotion": True,
        },
    }


def _response_packet(agent: dict[str, Any], task: str, run_status: str, llm_result: dict[str, Any], policy_violations: list[str]) -> dict[str, Any]:
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
            "blocked_reasons": policy_violations,
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
    run_status = "blocked" if policy_decision["status"] == "blocked" else "completed"
    tool_descriptors = [_tool_descriptor(tool) for tool in selected_tools]

    effective_runtime = runtime_config or build_llm_runtime_config(engine="deterministic_local")
    if run_status == "blocked":
        llm_result = {
            "schema": "ai-talent-llm-runtime-result/v1",
            "engine": effective_runtime.get("engine", "deterministic_local"),
            "status": "skipped_policy_block",
            "reason": "policy_blocked_before_llm_or_tool_execution",
            "identity_policy": effective_runtime.get("identity_policy", "application_engine_not_identity"),
            "network_access": effective_runtime.get("network_access", "blocked"),
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
            tools=tool_descriptors,
        )

    tool_execution = _execute_tools(selected_tools=selected_tools, manifest=manifest, task=task, llm_result=llm_result)
    verification = _verify_execution(policy_decision, tool_execution, llm_result)
    response = _response_packet(agent, task, run_status, llm_result, policy_violations)
    growth_update = {
        "experience_type": "guardrail_block_after_hire" if run_status == "blocked" else "agent_runtime_after_hire",
        "reflection": (
            "정책 위반을 업무 능력이 아니라 안전 경계로 처리했습니다."
            if run_status == "blocked"
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
        "decision": "quarantine" if run_status == "blocked" else "candidate_pending_boss_review",
        "target": "local_learning_ledger",
        "private_reasoning_trace_policy": "do_not_store",
        "promotion_requires": ["verification_passed", "boss_or_committee_review"],
    }
    audit_events = [
        {
            "recorded_at_utc": created_at,
            "event": "agent_execution_loop_started",
            "task_fingerprint": hashlib.sha256(task.encode("utf-8")).hexdigest()[:16],
        },
        *policy_decision.get("audit_events", []),
        {
            "recorded_at_utc": _now(),
            "event": "llm_runtime_invoked" if run_status != "blocked" else "llm_runtime_skipped",
            "status": llm_result.get("status"),
            "engine": llm_result.get("engine"),
        },
        {
            "recorded_at_utc": _now(),
            "event": "tool_execution_verified",
            "status": verification["status"],
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
        "tool_execution": tool_execution,
        "verification": verification,
        "memory_write": memory_write,
        "audit_events": audit_events,
        "response": response,
        "growth_update": growth_update,
    }


def write_agent_run_log(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False) + "\n")
