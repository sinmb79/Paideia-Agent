from __future__ import annotations

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


def build_default_tool_registry() -> dict[str, ToolSpec]:
    tools = [
        ToolSpec(
            tool_id="work_session",
            capability="research.analysis",
            description="Summarize a bounded local work session from manifest, memory, policy, and LLM draft.",
            side_effects="none",
            handler=_work_session,
            data_classes=("task_context", "manifest_summary", "verified_memory_summaries"),
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
