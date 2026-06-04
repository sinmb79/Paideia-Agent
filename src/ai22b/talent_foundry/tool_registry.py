from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


TOOL_EXECUTION_SCHEMA = "paideia-tool-execution/v1"

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    capability: str
    description: str
    side_effects: str
    handler: ToolHandler

    def descriptor(self) -> dict[str, Any]:
        return {
            "id": self.tool_id,
            "name": self.tool_id,
            "capability": self.capability,
            "description": self.description,
            "side_effects": self.side_effects,
            "execution_surface": "local_paideia_runtime",
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
        ),
        ToolSpec(
            tool_id="memory_consolidation",
            capability="memory.write_candidate",
            description="Create a reviewed learning candidate without promoting it automatically.",
            side_effects="candidate_memory_only",
            handler=_memory_consolidation,
        ),
        ToolSpec(
            tool_id="parent_controlled_projection_team",
            capability="projection.spawn_bounded",
            description="Represent bounded projection work controlled by the parent agent identity.",
            side_effects="bounded_projection_summary_only",
            handler=_projection_team,
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
                }
            )
    return descriptors


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
    results: list[dict[str, Any]] = []
    for tool_id in selected_tools:
        tool = active_registry.get(tool_id)
        if not tool:
            results.append(
                {
                    "tool": tool_id,
                    "status": "skipped",
                    "capability": "unknown",
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
                "output": output,
            }
        )
    return {
        "schema": TOOL_EXECUTION_SCHEMA,
        "execution_model": "registered_capability_checked_local_tools_v1",
        "selected_tools": selected_tools,
        "tool_results": results,
    }
