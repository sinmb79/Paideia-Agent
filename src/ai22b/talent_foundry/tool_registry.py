from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


TOOL_EXECUTION_SCHEMA = "paideia-tool-execution/v1"
TOOL_RESULT_RECORD_SCHEMA = "paideia-tool-result-record/v1"
TOOL_CAPABILITY_SCOPE_SCHEMA = "paideia-tool-capability-scope/v1"
TOOL_CAPABILITY_AUDIT_SCHEMA = "paideia-tool-capability-audit/v1"
TOOL_ARTIFACT_MANIFEST_SCHEMA = "paideia-tool-execution-artifact-manifest/v1"
REQUIRED_DEFAULT_TOOLS = {
    "local_file_read",
    "local_file_write",
    "work_session",
    "evidence_packet",
    "assessment",
    "memory_consolidation",
    "parent_controlled_projection_team",
}
SAFE_SIDE_EFFECTS = {
    "none",
    "sandbox_declared_outputs_only",
    "review_packet_only",
    "candidate_memory_only",
    "bounded_projection_summary_only",
}
SAFE_FILESYSTEM_SCOPES = {
    "none",
    "declared_context_only",
    "workspace_root_declared_outputs",
    "local_learning_ledger_candidate",
}

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
            "capability_granted": granted,
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
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
    draft = str(llm_result.get("draft", "")).strip()
    return {
        "summary": draft or f"{agent.get('name')}은 '{task}' 요청을 근거 확인, 경계 확인, 결과 기록 순서로 정리했습니다.",
        "llm_plan_schema": llm_plan.get("schema"),
        "llm_plan_source": llm_plan.get("source"),
        "reviewable_reasoning_summary": llm_plan.get("reviewable_reasoning_summary", []),
        "suggested_next_actions": llm_plan.get("suggested_next_actions", []),
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
    llm_plan = llm_result.get("llm_plan", {}) if isinstance(llm_result.get("llm_plan"), dict) else {}
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
            "id": "llm_reviewable_plan",
            "source": llm_result.get("engine", "unknown_runtime"),
            "summary": "; ".join(
                str(item.get("summary", ""))
                for item in llm_plan.get("reviewable_reasoning_summary", [])
                if isinstance(item, dict)
            )
            or "No structured LLM plan was produced.",
            "trust_level": "reviewable_summary_not_private_trace",
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
            "id": "llm_plan_marked_reviewable",
            "status": "satisfied" if llm_plan.get("schema") == "paideia-llm-reviewable-plan/v1" else "needs_review",
            "evidence": "llm_reviewable_plan",
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
        "llm_tool_plan": llm_plan.get("tool_plan", []),
        "llm_plan_policy": llm_plan.get("tool_plan_policy"),
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
        "capability_granted": False,
        "data_classes": [],
        "filesystem": "none",
        "filesystem_scope": "none",
        "network": "blocked",
        "network_scope": "blocked",
        "subprocess": "blocked",
        "subprocess_scope": "blocked",
        "side_effects": "unknown",
    }


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _safe_tool_artifact_name(tool_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in tool_id)
    return f"{safe or 'tool'}_result.json"


def _write_tool_execution_artifacts(
    *,
    artifact_dir: Path,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    for item in results:
        tool_id = str(item.get("tool", "tool"))
        file_name = _safe_tool_artifact_name(tool_id)
        artifact_path = artifact_dir / file_name
        payload = {
            "schema": "paideia-tool-output-artifact/v1",
            "tool": tool_id,
            "status": item.get("status"),
            "capability": item.get("capability"),
            "capability_scope": item.get("capability_scope", {}),
            "output": item.get("output", {}),
            "output_digest_sha256": item.get("output_digest_sha256"),
            "execution_record": item.get("execution_record", {}),
            "public_safe": {
                "network_call_performed": False,
                "subprocess_executed": False,
                "raw_provider_payload_saved": False,
                "private_reasoning_trace": "do_not_store",
                "absolute_paths_exported": False,
            },
        }
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        file_bytes = artifact_path.read_bytes()
        file_digest = hashlib.sha256(file_bytes).hexdigest()
        record = item.get("execution_record", {})
        if isinstance(record, dict):
            record["local_artifact_written"] = True
            record["local_artifact_file"] = file_name
            record["local_artifact_sha256"] = file_digest
        artifacts.append(
            {
                "tool": tool_id,
                "status": item.get("status"),
                "relative_path": file_name,
                "bytes": len(file_bytes),
                "sha256": file_digest,
                "output_digest_sha256": item.get("output_digest_sha256"),
            }
        )

    manifest = {
        "schema": TOOL_ARTIFACT_MANIFEST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "materialized" if artifacts else "no_tool_results",
        "artifact_root": artifact_dir.name,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "public_safe": {
            "network_call_performed": False,
            "subprocess_executed": False,
            "external_side_effects_performed": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "absolute_paths_exported": False,
        },
    }
    manifest_path = artifact_dir / "tool_execution_artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_file"] = manifest_path.name
    manifest["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return manifest


def _artifact_manifest_not_requested() -> dict[str, Any]:
    return {
        "schema": TOOL_ARTIFACT_MANIFEST_SCHEMA,
        "status": "not_requested",
        "artifact_count": 0,
        "artifacts": [],
        "public_safe": {
            "network_call_performed": False,
            "subprocess_executed": False,
            "external_side_effects_performed": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "absolute_paths_exported": False,
        },
    }


def _tool_result_record(
    *,
    tool_id: str,
    status: str,
    capability: str,
    capability_scope: dict[str, Any],
    output: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": TOOL_RESULT_RECORD_SCHEMA,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "tool": tool_id,
        "status": status,
        "capability": capability,
        "registered": capability_scope.get("registered"),
        "capability_granted": capability_scope.get("capability_granted", capability_scope.get("granted")),
        "output_digest_sha256": _stable_digest(output),
        "side_effects_declared": capability_scope.get("side_effects"),
        "side_effects_performed": False,
        "network_call_performed": False,
        "subprocess_executed": False,
        "raw_provider_payload_saved": False,
        "private_reasoning_trace": "do_not_store",
        "local_artifact_written": False,
    }


def _tool_result(
    *,
    tool_id: str,
    status: str,
    capability: str,
    capability_scope: dict[str, Any],
    output: dict[str, Any],
) -> dict[str, Any]:
    record = _tool_result_record(
        tool_id=tool_id,
        status=status,
        capability=capability,
        capability_scope=capability_scope,
        output=output,
    )
    return {
        "tool": tool_id,
        "status": status,
        "capability": capability,
        "capability_scope": capability_scope,
        "output": output,
        "output_digest_sha256": record["output_digest_sha256"],
        "execution_record": record,
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
    artifact_dir: Path | None = None,
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
            scope = scope_by_tool.get(tool_id, _unknown_tool_scope(tool_id))
            results.append(
                _tool_result(
                    tool_id=tool_id,
                    status="skipped",
                    capability="unknown",
                    capability_scope=scope,
                    output={"reason": "tool_not_registered"},
                )
            )
            continue
        if tool.capability not in granted:
            results.append(
                _tool_result(
                    tool_id=tool_id,
                    status="blocked",
                    capability=tool.capability,
                    capability_scope=scope_by_tool[tool_id],
                    output={"reason": "capability_not_granted"},
                )
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
            _tool_result(
                tool_id=tool_id,
                status="completed",
                capability=tool.capability,
                capability_scope=scope_by_tool[tool_id],
                output=output,
            )
        )
    artifact_manifest = (
        _write_tool_execution_artifacts(artifact_dir=artifact_dir, results=results)
        if artifact_dir is not None and results
        else _artifact_manifest_not_requested()
    )
    return {
        "schema": TOOL_EXECUTION_SCHEMA,
        "execution_model": "registered_capability_checked_local_tools_v1",
        "selected_tools": selected_tools,
        "capability_scope": capability_scope,
        "artifact_manifest": artifact_manifest,
        "tool_results": results,
    }


def _audit_manifest() -> dict[str, Any]:
    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "paideia-tool-auditor",
            "role": "local tool capability audit agent",
            "major_goal": "Verify registered tool capability contracts without executing external side effects.",
        },
        "memory_profile": {
            "procedural_principles": ["deny by default", "review before memory promotion"],
            "semantic_themes": ["tool capability safety", "local-first runtime"],
        },
    }


def _audit_llm_result() -> dict[str, Any]:
    return {
        "schema": "ai-talent-llm-runtime-result/v1",
        "engine": "deterministic_local",
        "status": "completed",
        "identity_policy": "application_engine_not_identity",
        "network_access": "blocked",
        "draft": "Review the local registered tool capability contract.",
        "llm_plan": {
            "schema": "paideia-llm-reviewable-plan/v1",
            "source": "audit_fixture",
            "reviewable_reasoning_summary": [
                {"step": "tool_registry", "summary": "Registered tools must be capability-gated."}
            ],
            "suggested_next_actions": ["Keep tool execution under registered local executors."],
            "tool_plan": [],
            "tool_plan_policy": "suggestions_only_registered_executor_decides",
            "private_reasoning_trace": "do_not_store",
            "raw_provider_text_stored": False,
        },
    }


def audit_tool_capability_registry(registry: dict[str, ToolSpec] | None = None) -> dict[str, Any]:
    """Audit the default local tool registry as a public-safe P0 capability contract."""

    from ai22b.talent_foundry.action_policy import TOOL_CAPABILITIES

    active_registry = registry or build_default_tool_registry()
    tool_ids = sorted(active_registry)
    policy_tool_ids = sorted(TOOL_CAPABILITIES)
    missing_required = sorted(REQUIRED_DEFAULT_TOOLS - set(tool_ids))
    unregistered_policy_tools = sorted(set(policy_tool_ids) - set(tool_ids))
    registry_tools_without_policy_capabilities = sorted(set(tool_ids) - set(policy_tool_ids))
    descriptors = [active_registry[tool_id].descriptor() for tool_id in tool_ids]
    scope_failures: list[dict[str, Any]] = []
    for tool_id in tool_ids:
        tool = active_registry[tool_id]
        scope = tool.capability_scope(granted=False)
        failures: list[str] = []
        if scope.get("registered") is not True:
            failures.append("not_registered")
        if not str(scope.get("capability", "")).strip():
            failures.append("capability_missing")
        if scope.get("network_scope") != "blocked":
            failures.append("network_not_blocked")
        if scope.get("subprocess_scope") != "blocked":
            failures.append("subprocess_not_blocked")
        if scope.get("filesystem_scope") not in SAFE_FILESYSTEM_SCOPES:
            failures.append("filesystem_scope_not_safe")
        if scope.get("side_effects") not in SAFE_SIDE_EFFECTS:
            failures.append("side_effects_not_safe")
        if failures:
            scope_failures.append({"tool": tool_id, "failures": failures, "scope": scope})

    denied_policy = {
        "schema": "paideia-action-policy/v1",
        "status": "approved",
        "policy_violations": [],
        "capability_grants": {
            "schema": "paideia-capability-grants/v1",
            "mode": "deny_by_default",
            "allowed_capabilities": [],
        },
    }
    denied_execution = execute_registered_tools(
        selected_tools=tool_ids,
        manifest=_audit_manifest(),
        task="Audit deny-by-default tool behavior.",
        llm_result=_audit_llm_result(),
        policy_decision=denied_policy,
        registry=active_registry,
    )

    allowed_capabilities = sorted({tool.capability for tool in active_registry.values()})
    granted_policy = {
        **denied_policy,
        "capability_grants": {
            "schema": "paideia-capability-grants/v1",
            "mode": "deny_by_default",
            "allowed_capabilities": allowed_capabilities,
        },
    }
    granted_execution = execute_registered_tools(
        selected_tools=tool_ids,
        manifest=_audit_manifest(),
        task="Audit granted local registered tool behavior.",
        llm_result=_audit_llm_result(),
        policy_decision=granted_policy,
        registry=active_registry,
    )
    unknown_execution = execute_registered_tools(
        selected_tools=["unknown_unregistered_tool"],
        manifest=_audit_manifest(),
        task="Audit unregistered tool behavior.",
        llm_result=_audit_llm_result(),
        policy_decision=granted_policy,
        registry=active_registry,
    )

    denied_statuses = {item["tool"]: item["status"] for item in denied_execution["tool_results"]}
    granted_results = {item["tool"]: item for item in granted_execution["tool_results"]}
    granted_statuses = {tool: item["status"] for tool, item in granted_results.items()}
    output_checks = {
        "local_file_read_no_direct_read": granted_results.get("local_file_read", {})
        .get("output", {})
        .get("direct_file_read_performed")
        is False,
        "local_file_write_no_direct_write": granted_results.get("local_file_write", {})
        .get("output", {})
        .get("direct_file_write_performed")
        is False,
        "evidence_packet_schema": granted_results.get("evidence_packet", {}).get("output", {}).get("schema")
        == "paideia-tool-evidence-packet/v1",
        "assessment_requires_review": granted_results.get("assessment", {})
        .get("output", {})
        .get("recommended_review_label", {})
        .get("status")
        == "needs_boss_review",
        "memory_candidate_only": granted_results.get("memory_consolidation", {})
        .get("output", {})
        .get("candidate_only")
        is True,
        "projection_not_separate_consciousness": granted_results.get("parent_controlled_projection_team", {})
        .get("output", {})
        .get("separate_consciousness")
        is False,
    }
    result_records = [
        item.get("execution_record", {})
        for item in [
            *denied_execution.get("tool_results", []),
            *granted_execution.get("tool_results", []),
            *unknown_execution.get("tool_results", []),
        ]
        if isinstance(item, dict)
    ]
    result_record_checks = {
        "all_have_execution_record_schema": bool(result_records)
        and all(record.get("schema") == TOOL_RESULT_RECORD_SCHEMA for record in result_records),
        "all_have_output_digest": bool(result_records)
        and all(len(str(record.get("output_digest_sha256", ""))) == 64 for record in result_records),
        "no_network_calls": all(record.get("network_call_performed") is False for record in result_records),
        "no_subprocess_execution": all(record.get("subprocess_executed") is False for record in result_records),
        "no_side_effects_performed": all(record.get("side_effects_performed") is False for record in result_records),
        "private_reasoning_not_stored": all(
            record.get("private_reasoning_trace") == "do_not_store" for record in result_records
        ),
    }
    unknown_result = unknown_execution["tool_results"][0] if unknown_execution["tool_results"] else {}
    details = {
        "tool_count": len(tool_ids),
        "registered_tool_ids": tool_ids,
        "policy_tool_ids": policy_tool_ids,
        "required_tool_ids": sorted(REQUIRED_DEFAULT_TOOLS),
        "missing_required_tools": missing_required,
        "unregistered_policy_tools": unregistered_policy_tools,
        "registry_tools_without_policy_capabilities": registry_tools_without_policy_capabilities,
        "safe_side_effects": sorted(SAFE_SIDE_EFFECTS),
        "safe_filesystem_scopes": sorted(SAFE_FILESYSTEM_SCOPES),
        "scope_failure_count": len(scope_failures),
        "scope_failures": scope_failures,
        "denied_execution_schema": denied_execution.get("schema"),
        "denied_execution_model": denied_execution.get("execution_model"),
        "denied_all_blocked": bool(denied_statuses) and all(status == "blocked" for status in denied_statuses.values()),
        "denied_statuses": denied_statuses,
        "granted_execution_schema": granted_execution.get("schema"),
        "granted_execution_model": granted_execution.get("execution_model"),
        "granted_all_completed": bool(granted_statuses)
        and all(status == "completed" for status in granted_statuses.values()),
        "granted_statuses": granted_statuses,
        "output_checks": output_checks,
        "result_record_checks": result_record_checks,
        "unknown_tool_status": unknown_result.get("status"),
        "unknown_tool_registered": unknown_result.get("capability_scope", {}).get("registered"),
        "network_default": denied_execution.get("capability_scope", {}).get("network_default"),
        "subprocess_default": denied_execution.get("capability_scope", {}).get("subprocess_default"),
        "private_reasoning_trace": denied_execution.get("capability_scope", {}).get("private_reasoning_trace"),
    }
    passed = (
        not missing_required
        and not unregistered_policy_tools
        and not registry_tools_without_policy_capabilities
        and not scope_failures
        and details["denied_execution_schema"] == TOOL_EXECUTION_SCHEMA
        and details["denied_execution_model"] == "registered_capability_checked_local_tools_v1"
        and details["denied_all_blocked"] is True
        and details["granted_execution_schema"] == TOOL_EXECUTION_SCHEMA
        and details["granted_execution_model"] == "registered_capability_checked_local_tools_v1"
        and details["granted_all_completed"] is True
        and all(output_checks.values())
        and all(result_record_checks.values())
        and details["unknown_tool_status"] == "skipped"
        and details["unknown_tool_registered"] is False
        and details["network_default"] == "blocked"
        and details["subprocess_default"] == "blocked"
        and details["private_reasoning_trace"] == "do_not_store"
    )
    return {
        "schema": TOOL_CAPABILITY_AUDIT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "passed": passed,
        "descriptors": descriptors,
        "details": details,
        "public_safe": {
            "network_call_performed": False,
            "subprocess_executed": False,
            "direct_arbitrary_file_read": False,
            "direct_arbitrary_file_write": False,
            "private_reasoning_trace_stored": False,
            "raw_provider_payload_saved": False,
        },
    }
