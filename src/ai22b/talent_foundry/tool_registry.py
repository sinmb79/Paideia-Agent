from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable


TOOL_EXECUTION_SCHEMA = "paideia-tool-execution/v1"
TOOL_CAPABILITY_SCOPE_SCHEMA = "paideia-tool-capability-scope/v1"

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    capability: str
    description: str
    side_effects: str
    handler: ToolHandler
    data_classes: tuple[str, ...] = ()
    filesystem_scope: str = "none"
    network_scope: str = "blocked"
    subprocess_scope: str = "blocked"

    def descriptor(self) -> dict[str, Any]:
        return {
            "id": self.tool_id,
            "name": self.tool_id,
            "capability": self.capability,
            "description": self.description,
            "side_effects": self.side_effects,
            "execution_surface": "local_paideia_runtime",
            "capability_scope": self.capability_scope(granted=False),
        }

    def capability_scope(self, *, granted: bool) -> dict[str, Any]:
        return {
            "tool": self.tool_id,
            "registered": True,
            "capability": self.capability,
            "granted": granted,
            "data_classes": list(self.data_classes),
            "filesystem": self.filesystem_scope,
            "filesystem_scope": self.filesystem_scope,
            "network": self.network_scope,
            "network_scope": self.network_scope,
            "subprocess": self.subprocess_scope,
            "subprocess_scope": self.subprocess_scope,
            "side_effects": self.side_effects,
        }


def _local_file_read(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "paideia-tool-local-file-read-plan/v1",
        "mode": "declared_local_context_only",
        "direct_file_read_performed": False,
        "read_sources": [
            "agent_manifest",
            "memory_profile_summary",
            "policy_decision",
            "workspace_outputs_declared_by_sandbox",
        ],
        "path_policy": {
            "absolute_paths_rejected_for_public_artifacts": True,
            "workspace_escape_rejected": True,
            "private_training_files_not_read_by_default": True,
        },
        "delegated_runtime": "WorkspaceSandbox when workspace execution is requested",
    }


def _local_file_write(context: dict[str, Any]) -> dict[str, Any]:
    task = str(context.get("task", ""))
    return {
        "schema": "paideia-tool-local-file-write-plan/v1",
        "mode": "sandbox_declared_outputs_only",
        "direct_file_write_performed": False,
        "declared_output_candidates": [
            "task_plan.md",
            "result_summary.md",
            "runtime_execution.json",
            "trace.jsonl",
            "rollback_manifest.json",
            "workspace_sandbox.json",
        ],
        "task_fingerprint": hashlib.sha256(task.encode("utf-8")).hexdigest()[:16],
        "path_policy": {
            "write_root": "workspace_root_only",
            "rollback_manifest_required": True,
            "network_side_effects": "blocked",
            "subprocess_side_effects": "blocked",
        },
        "delegated_runtime": "WorkspaceSandbox.safe_path/write_* methods",
    }


def _work_session(context: dict[str, Any]) -> dict[str, Any]:
    agent = context.get("manifest", {}).get("agent", {})
    task = context.get("task", "")
    llm_result = context.get("llm_result", {})
    draft = str(llm_result.get("draft", "")).strip()
    return {
        "summary": draft or f"{agent.get('name')}은 '{task}' 요청을 근거 확인, 경계 확인, 결과 기록 순서로 정리했습니다.",
        "requires_boss_review": True,
        "artifact_policy": "in_memory_summary_only_for_cli_run",
    }


def _evidence_packet(context: dict[str, Any]) -> dict[str, Any]:
    manifest = context.get("manifest", {})
    memory = manifest.get("memory_profile", {})
    llm_result = context.get("llm_result", {})
    policy_decision = context.get("policy_decision", {})
    previous_tools = context.get("tool_results_so_far", [])
    task = str(context.get("task", ""))
    draft = str(llm_result.get("draft", "")).strip()
    procedural = list(memory.get("procedural_principles", []))[:5]
    semantic = list(memory.get("semantic_themes", []))[:5]
    previous_completed = [item.get("tool") for item in previous_tools if item.get("status") == "completed"]
    evidence_items = [
        {
            "id": "request",
            "source": "boss_task",
            "summary": task,
            "trust_level": "direct_user_request",
        },
        {
            "id": "runtime_draft",
            "source": llm_result.get("engine", "unknown_runtime"),
            "summary": draft or "No runtime draft was produced; keep conclusions tentative.",
            "trust_level": "draft_requires_review",
        },
        {
            "id": "memory_profile",
            "source": "local_verified_memory_summaries",
            "summary": "; ".join(procedural + semantic) or "No memory profile detail was selected.",
            "trust_level": "local_summary_not_private_trace",
        },
        {
            "id": "policy_boundary",
            "source": "action_intent_capability_policy",
            "summary": f"policy_status={policy_decision.get('status')}; violations={policy_decision.get('policy_violations', [])}",
            "trust_level": "guardrail_record",
        },
    ]
    checklist = [
        {
            "id": "request_understood",
            "status": "satisfied",
            "evidence": "boss_task",
        },
        {
            "id": "policy_checked_before_tools",
            "status": "satisfied" if policy_decision.get("schema") == "paideia-action-policy/v1" else "needs_review",
            "evidence": "action_intent_capability_policy",
        },
        {
            "id": "runtime_draft_marked_reviewable",
            "status": "satisfied" if llm_result.get("status") in {"completed", "bridge_context_prepared", "adapter_manifest_ready"} else "needs_review",
            "evidence": "runtime_draft",
        },
        {
            "id": "source_dates_required_for_external_claims",
            "status": "manual_review_required",
            "evidence": "not_performed_by_local_in_memory_tool",
        },
        {
            "id": "hidden_chain_of_thought_not_stored",
            "status": "satisfied",
            "evidence": "memory_profile",
        },
    ]
    return {
        "schema": "paideia-tool-evidence-packet/v1",
        "task_fingerprint": hashlib.sha256(task.encode("utf-8")).hexdigest()[:16],
        "evidence_items": evidence_items,
        "checklist": checklist,
        "previous_completed_tools": previous_completed,
        "unsupported_claim_policy": "unsupported_external_claims_remain_open_questions",
        "open_questions": [
            "Which source date and document version support each external factual claim?",
            "Which counterevidence would change the draft conclusion?",
            "Does the boss want a full dataflow run before promoting this into memory?",
        ],
    }


def _memory_consolidation(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_only": True,
        "promotion_requires_review": True,
        "target": "local_learning_ledger",
        "private_reasoning_trace_policy": "do_not_store",
    }


def _projection_team(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "control_model": "single_parent_identity_controls_task_limited_projections",
        "merge_policy": "reviewed_summary_only",
        "separate_consciousness": False,
    }


def _assessment(context: dict[str, Any]) -> dict[str, Any]:
    policy_decision = context.get("policy_decision", {})
    llm_result = context.get("llm_result", {})
    previous_tools = context.get("tool_results_so_far", [])
    previous_completed = [item.get("tool") for item in previous_tools if item.get("status") == "completed"]
    evidence_packet_seen = "evidence_packet" in previous_completed
    return {
        "schema": "paideia-tool-assessment-review/v1",
        "assessment_mode": "post_run_review_packet",
        "status": "ready_for_boss_review",
        "checks": {
            "policy_status": policy_decision.get("status"),
            "llm_status": llm_result.get("status"),
            "evidence_packet_seen": evidence_packet_seen,
            "hidden_chain_of_thought_not_stored": True,
            "promotion_without_review": False,
        },
        "previous_completed_tools": previous_completed,
        "recommended_review_label": {
            "status": "needs_boss_review",
            "score": None,
        },
    }


def build_default_tool_registry() -> dict[str, ToolSpec]:
    tools = [
        ToolSpec(
            tool_id="local_file_read",
            capability="research.analysis",
            description="Declare safe local read surfaces without reading arbitrary files.",
            side_effects="none",
            handler=_local_file_read,
            data_classes=("manifest_summary", "verified_memory_summaries", "workspace_output_references"),
            filesystem_scope="declared_context_only",
        ),
        ToolSpec(
            tool_id="local_file_write",
            capability="research.analysis",
            description="Declare sandbox-only workspace write intentions; actual writes are performed by WorkspaceSandbox.",
            side_effects="sandbox_declared_outputs_only",
            handler=_local_file_write,
            data_classes=("task_context", "workspace_output_manifest"),
            filesystem_scope="workspace_root_declared_outputs",
        ),
        ToolSpec(
            tool_id="work_session",
            capability="research.analysis",
            description="Summarize a bounded local work session from manifest, memory, policy, and LLM draft.",
            side_effects="none",
            handler=_work_session,
            data_classes=("task_context", "manifest_summary", "verified_memory_summaries"),
        ),
        ToolSpec(
            tool_id="evidence_packet",
            capability="research.analysis",
            description="Create a reviewable evidence packet from task, runtime draft, policy decision, and local memory summaries.",
            side_effects="none",
            handler=_evidence_packet,
            data_classes=("task_context", "runtime_draft", "policy_decision", "verified_memory_summaries"),
        ),
        ToolSpec(
            tool_id="assessment",
            capability="assessment.review",
            description="Prepare a post-run review packet; it does not promote learning by itself.",
            side_effects="review_packet_only",
            handler=_assessment,
            data_classes=("policy_decision", "runtime_status", "review_label_candidate"),
        ),
        ToolSpec(
            tool_id="memory_consolidation",
            capability="memory.write_candidate",
            description="Create a reviewed learning candidate without promoting it automatically.",
            side_effects="candidate_memory_only",
            handler=_memory_consolidation,
            data_classes=("reviewed_growth_candidate", "quality_label"),
            filesystem_scope="local_learning_ledger_candidate",
        ),
        ToolSpec(
            tool_id="parent_controlled_projection_team",
            capability="projection.spawn_bounded",
            description="Represent bounded projection work controlled by the parent agent identity.",
            side_effects="bounded_projection_summary_only",
            handler=_projection_team,
            data_classes=("task_context", "projection_role_summary"),
        ),
    ]
    return {tool.tool_id: tool for tool in tools}


def tool_descriptors(tool_ids: list[str], registry: dict[str, ToolSpec] | None = None) -> list[dict[str, Any]]:
    active_registry = registry or build_default_tool_registry()
    descriptors: list[dict[str, Any]] = []
    for tool_id in tool_ids:
        tool = active_registry.get(tool_id)
        if tool:
            descriptors.append(tool.descriptor())
        else:
            descriptors.append(
                {
                    "id": tool_id,
                    "name": tool_id,
                    "capability": "unknown",
                    "description": "Tool is allowed by manifest but not implemented in the local registry.",
                    "side_effects": "unknown",
                    "execution_surface": "local_paideia_runtime",
                    "capability_scope": _unknown_tool_scope(tool_id),
                }
            )
    return descriptors


def _unknown_tool_scope(tool_id: str) -> dict[str, Any]:
    return {
        "tool": tool_id,
        "registered": False,
        "capability": "unknown",
        "granted": False,
        "data_classes": [],
        "filesystem": "none",
        "filesystem_scope": "none",
        "network": "blocked",
        "network_scope": "blocked",
        "subprocess": "blocked",
        "subprocess_scope": "blocked",
        "side_effects": "unknown",
    }


def build_tool_capability_scope(
    *,
    selected_tools: list[str],
    policy_decision: dict[str, Any],
    registry: dict[str, ToolSpec] | None = None,
) -> dict[str, Any]:
    active_registry = registry or build_default_tool_registry()
    granted = set(policy_decision.get("capability_grants", {}).get("allowed_capabilities", []))
    per_tool: list[dict[str, Any]] = []
    for tool_id in selected_tools:
        tool = active_registry.get(tool_id)
        if tool is None:
            per_tool.append(_unknown_tool_scope(tool_id))
        else:
            per_tool.append(tool.capability_scope(granted=tool.capability in granted))
    return {
        "schema": TOOL_CAPABILITY_SCOPE_SCHEMA,
        "mode": "deny_by_default",
        "selected_tools": selected_tools,
        "granted_capabilities": sorted(granted),
        "tool_scopes": per_tool,
        "network_default": "blocked",
        "subprocess_default": "blocked",
        "private_reasoning_trace": "do_not_store",
    }


def execute_registered_tools(
    *,
    selected_tools: list[str],
    manifest: dict[str, Any],
    task: str,
    llm_result: dict[str, Any],
    policy_decision: dict[str, Any],
    registry: dict[str, ToolSpec] | None = None,
) -> dict[str, Any]:
    active_registry = registry or build_default_tool_registry()
    granted = policy_decision.get("capability_grants", {}).get("allowed_capabilities", [])
    capability_scope = build_tool_capability_scope(
        selected_tools=selected_tools,
        policy_decision=policy_decision,
        registry=active_registry,
    )
    scope_by_tool = {item["tool"]: item for item in capability_scope["tool_scopes"]}
    results: list[dict[str, Any]] = []
    for tool_id in selected_tools:
        tool = active_registry.get(tool_id)
        if not tool:
            results.append(
                {
                    "tool": tool_id,
                    "status": "skipped",
                    "capability": "unknown",
                    "capability_scope": scope_by_tool.get(tool_id, _unknown_tool_scope(tool_id)),
                    "output": {"reason": "tool_not_registered"},
                }
            )
            continue
        if tool.capability not in granted:
            results.append(
                {
                    "tool": tool_id,
                    "status": "blocked",
                    "capability": tool.capability,
                    "capability_scope": scope_by_tool[tool_id],
                    "output": {"reason": "capability_not_granted"},
                }
            )
            continue
        output = tool.handler(
            {
                "manifest": manifest,
                "task": task,
                "llm_result": llm_result,
                "policy_decision": policy_decision,
                "tool_results_so_far": results,
            }
        )
        results.append(
            {
                "tool": tool_id,
                "status": "completed",
                "capability": tool.capability,
                "capability_scope": scope_by_tool[tool_id],
                "output": output,
            }
        )
    return {
        "schema": TOOL_EXECUTION_SCHEMA,
        "execution_model": "registered_capability_checked_local_tools_v1",
        "selected_tools": selected_tools,
        "capability_scope": capability_scope,
        "tool_results": results,
    }
