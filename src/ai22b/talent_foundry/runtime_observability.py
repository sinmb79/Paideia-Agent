from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


RUNTIME_OBSERVABILITY_SCHEMA = "paideia-runtime-observability/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def _json_chars(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _count_completed_tools(tool_execution: dict[str, Any]) -> int:
    return sum(1 for item in tool_execution.get("tool_results", []) if item.get("status") == "completed")


def _learning_flow(memory_write: dict[str, Any]) -> dict[str, Any]:
    decision = memory_write.get("decision")
    return {
        "memory_write_decision": decision,
        "promotion_candidate_count": 1 if decision == "candidate_pending_boss_review" else 0,
        "quarantine_count": 1 if decision == "quarantine" else 0,
        "approval_pending_count": 1 if decision == "pending_boss_approval" else 0,
        "review_required_count": 1 if decision in {"candidate_pending_boss_review", "pending_boss_approval"} else 0,
    }


def build_agent_runtime_observability(
    *,
    manifest: dict[str, Any],
    task: str,
    memory: dict[str, Any],
    selected_tools: list[str],
    policy_decision: dict[str, Any],
    tool_execution: dict[str, Any],
    llm_result: dict[str, Any],
    verification: dict[str, Any],
    memory_write: dict[str, Any],
    llm_mode: str,
    runtime_config: dict[str, Any],
) -> dict[str, Any]:
    semantic_themes = [str(item) for item in memory.get("semantic_themes", [])]
    procedural_principles = [str(item) for item in memory.get("procedural_principles", [])]
    selected_memory = semantic_themes + procedural_principles
    selected_memory_text = "\n".join(selected_memory)
    prompt_context = {
        "agent": manifest.get("agent", {}),
        "task": task,
        "selected_memory": {
            "semantic_themes": semantic_themes,
            "procedural_principles": procedural_principles,
        },
        "policy_status": policy_decision.get("status"),
        "selected_tools": selected_tools,
    }
    network_access = llm_result.get("network_access") or runtime_config.get("network_access", "blocked")
    live_or_external = network_access in {
        "external_api_selected_data_minimized",
        "codex_host_managed_data_minimized",
        "codex_or_openai_data_minimized",
        "localhost_only",
    }
    provider_usage = llm_result.get("usage")
    return {
        "schema": RUNTIME_OBSERVABILITY_SCHEMA,
        "created_at_utc": _now(),
        "estimation_policy": {
            "token_estimate": "ceil(characters/4)",
            "provider_usage_is_authoritative_when_present": True,
            "private_reasoning_trace": "do_not_store",
        },
        "context": {
            "task_characters": len(task),
            "task_estimated_tokens": estimate_tokens(task),
            "selected_memory_count": len(selected_memory),
            "selected_memory_characters": len(selected_memory_text),
            "selected_memory_estimated_tokens": estimate_tokens(selected_memory_text),
            "prompt_context_characters": _json_chars(prompt_context),
            "prompt_context_estimated_tokens": estimate_tokens(prompt_context),
            "full_session_replay_used": False,
            "selected_memory_only": True,
        },
        "cost_proxy": {
            "network_access": network_access,
            "billable_provider_possible": bool(live_or_external and llm_mode in {"auto", "live"}),
            "provider_usage_present": provider_usage is not None,
            "provider_usage_summary": str(provider_usage)[:500] if provider_usage is not None else None,
            "raw_provider_payload_saved": False,
        },
        "performance_proxy": {
            "llm_mode": llm_mode,
            "llm_engine": llm_result.get("engine") or runtime_config.get("engine"),
            "llm_status": llm_result.get("status"),
            "fallback_used": bool(llm_result.get("fallback_used")),
            "policy_status": policy_decision.get("status"),
            "policy_violation_count": len(policy_decision.get("policy_violations", [])),
            "approval_required_count": len(policy_decision.get("approval_required", [])),
            "selected_tool_count": len(selected_tools),
            "completed_tool_count": _count_completed_tools(tool_execution),
            "verification_status": verification.get("status"),
        },
        "learning_flow": _learning_flow(memory_write),
        "privacy": {
            "private_reasoning_trace_stored": False,
            "full_chat_or_session_replay_stored": False,
            "local_absolute_paths_exported": False,
        },
    }


def build_dataflow_runtime_observability(
    *,
    formatted_job: dict[str, Any],
    active_memory_cache: dict[str, Any],
    tile_matrix: dict[str, Any],
    shadow_buffers: dict[str, Any],
    verification: dict[str, Any],
    growth_candidate: dict[str, Any],
) -> dict[str, Any]:
    selected_memory = active_memory_cache.get("selected_memory_tiles", [])
    prompt_context = {
        "formatted_job": {
            "objective": formatted_job.get("objective"),
            "deliverables": formatted_job.get("deliverables", []),
            "acceptance_criteria": formatted_job.get("acceptance_criteria", []),
        },
        "selected_memory_tiles": selected_memory,
        "tiles": [item.get("tile_id") for item in tile_matrix.get("tiles", [])],
    }
    promotion_status = growth_candidate.get("promotion_status")
    return {
        "schema": RUNTIME_OBSERVABILITY_SCHEMA,
        "created_at_utc": _now(),
        "estimation_policy": {
            "token_estimate": "ceil(characters/4)",
            "provider_usage_is_authoritative_when_present": True,
            "private_reasoning_trace": "do_not_store",
        },
        "context": {
            "task_characters": len(str(formatted_job.get("objective", ""))),
            "task_estimated_tokens": estimate_tokens(str(formatted_job.get("objective", ""))),
            "selected_memory_count": len(selected_memory),
            "selected_memory_characters": _json_chars(selected_memory),
            "selected_memory_estimated_tokens": estimate_tokens(selected_memory),
            "prompt_context_characters": _json_chars(prompt_context),
            "prompt_context_estimated_tokens": estimate_tokens(prompt_context),
            "full_session_replay_used": False,
            "selected_memory_only": True,
        },
        "cost_proxy": {
            "network_access": "blocked",
            "billable_provider_possible": False,
            "provider_usage_present": False,
            "provider_usage_summary": None,
            "raw_provider_payload_saved": False,
        },
        "performance_proxy": {
            "runtime_model": "agent_dataflow_runtime_v1",
            "tile_count": len(tile_matrix.get("tiles", [])),
            "buffer_count": len(shadow_buffers.get("buffers", [])),
            "verification_status": verification.get("status"),
            "memory_route_degraded": active_memory_cache.get("memory_health", {}).get("route_is_degraded"),
        },
        "learning_flow": {
            "memory_write_decision": promotion_status,
            "promotion_candidate_count": 1 if promotion_status == "promote_to_learning_ledger" else 0,
            "quarantine_count": 1 if promotion_status == "quarantine" else 0,
            "approval_pending_count": 0,
            "review_required_count": 0 if promotion_status == "promote_to_learning_ledger" else 1,
        },
        "privacy": {
            "private_reasoning_trace_stored": False,
            "full_chat_or_session_replay_stored": False,
            "local_absolute_paths_exported": False,
        },
    }
