from __future__ import annotations

from typing import Any, Iterable

from .contracts_adapter import validate_action_pattern_v2, validate_case_graph_v2
from .models import APPROVED_PROMOTION_STATUSES
from .v2_artifacts import stable_id, v2_header


ACTION_PATTERN_VALIDATION_REPORT_SCHEMA = "paideia-action-pattern-graph-validation/v1"


def _predicate(predicate_id: str, op: str, field: str, value: object) -> dict[str, Any]:
    return {
        "predicate_id": predicate_id,
        "op": op,
        "field": field,
        "value": value,
    }


def _lcs(left: list[str], right: list[str]) -> list[str]:
    table = [[[] for _ in range(len(right) + 1)] for _ in range(len(left) + 1)]
    for i, left_item in enumerate(left, start=1):
        for j, right_item in enumerate(right, start=1):
            if left_item == right_item:
                table[i][j] = table[i - 1][j - 1] + [left_item]
            else:
                table[i][j] = table[i - 1][j] if len(table[i - 1][j]) >= len(table[i][j - 1]) else table[i][j - 1]
    return table[-1][-1]


def _common_capability_sequence(case_graphs: list[dict[str, Any]]) -> list[str]:
    sequences = [
        [str(step.get("capability") or step.get("action_type") or "") for step in graph.get("action_steps", [])]
        for graph in case_graphs
    ]
    sequences = [[item for item in sequence if item] for sequence in sequences]
    if not sequences:
        return []
    common = sequences[0]
    for sequence in sequences[1:]:
        common = _lcs(common, sequence)
    return common


def _unique_strings(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result


def _context_value(graph: dict[str, Any], name: str) -> object | None:
    for item in graph.get("context_variables") or []:
        if isinstance(item, dict) and item.get("name") == name:
            return item.get("value")
    return None


def _common_domain(case_graphs: list[dict[str, Any]], field_name: str, fallback: str) -> str:
    values = _unique_strings(graph.get(field_name) for graph in case_graphs)
    return values[0] if len(values) == 1 else fallback


def _input_slots(case_graphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, str] = {}
    for graph in case_graphs:
        for item in graph.get("context_variables", []):
            if isinstance(item, dict):
                seen.setdefault(str(item.get("name") or "input"), str(item.get("value_type") or "string"))
    if not seen:
        seen["task"] = "string"
    return [
        {
            "slot_id": name,
            "value_type": value_type,
            "required": True,
        }
        for name, value_type in sorted(seen.items())
    ]


def _preconditions(case_graphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predicates: dict[str, dict[str, Any]] = {}
    for graph in case_graphs:
        for constraint in graph.get("constraints", []):
            if not isinstance(constraint, dict) or not isinstance(constraint.get("predicate"), dict):
                continue
            predicate = constraint["predicate"]
            key = "|".join(str(predicate.get(field)) for field in ("op", "field", "value"))
            predicates.setdefault(key, dict(predicate))
    return list(predicates.values())


def _required_observations(case_graphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {}
    for graph in case_graphs:
        for item in graph.get("observations", []):
            if not isinstance(item, dict):
                continue
            observation_id = str(item.get("observation_id") or item.get("name") or "observation")
            observations.setdefault(
                observation_id,
                {
                    "observation_id": observation_id,
                    "value_type": str(item.get("value_type") or "string"),
                    "freshness_ms": item.get("freshness_ms"),
                },
            )
    return list(observations.values())


def compile_action_pattern(
    case_graphs: Iterable[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    min_source_cases: int = 3,
) -> dict[str, Any]:
    graphs = list(case_graphs)
    if not graphs:
        raise ValueError("compile_action_pattern requires at least one case graph")
    for graph in graphs:
        validate_case_graph_v2(graph, manifest)
    source_metadata: list[tuple[str, str, str, str]] = []
    for graph in graphs:
        case_id = str(graph.get("case_id") or "case")
        source_run_id = _context_value(graph, "source_run_id")
        source_status = _context_value(graph, "source_promotion_status")
        environment_fingerprint = _context_value(graph, "environment_fingerprint")
        if not all(isinstance(value, str) and value for value in (source_run_id, source_status, environment_fingerprint)):
            raise ValueError(f"ActionPattern compile requires complete source provenance for {case_id}")
        if source_status.casefold() not in APPROVED_PROMOTION_STATUSES:
            raise ValueError(f"ActionPattern compile blocked by ineligible source case: {case_id}")
        source_metadata.append((case_id, source_run_id, source_status, environment_fingerprint))
    owner = _common_domain(graphs, "owner", "Boss")
    domain = _common_domain(graphs, "domain", "mixed_domain")
    task_family = _common_domain(graphs, "task_family", "mixed_task")
    source_case_ids = _unique_strings(graph.get("case_id") for graph in graphs)
    source_kibo_ids = _unique_strings(kibo_id for graph in graphs for kibo_id in graph.get("source_kibo_ids", []))
    source_run_ids = _unique_strings(item[1] for item in source_metadata)
    environment_fingerprints = _unique_strings(item[3] for item in source_metadata)
    if len(source_case_ids) < min_source_cases:
        raise ValueError(f"ActionPattern compile requires at least {min_source_cases} distinct source cases")
    if len(source_run_ids) < min_source_cases:
        raise ValueError(f"ActionPattern compile requires at least {min_source_cases} distinct source runs")
    if len(environment_fingerprints) < 2:
        raise ValueError("ActionPattern compile requires at least two environment fingerprints")
    capabilities = _common_capability_sequence(graphs)
    if not capabilities:
        capabilities = _unique_strings(
            step.get("capability") or step.get("action_type")
            for graph in graphs
            for step in graph.get("action_steps", [])
            if isinstance(step, dict)
        )
    if not capabilities:
        raise ValueError("ActionPattern compile requires at least one action step")
    preconditions = _preconditions(graphs)
    if not preconditions:
        raise ValueError("ActionPattern compile requires at least one precondition")
    input_slots = _input_slots(graphs)
    pattern_id = stable_id("action-pattern", owner, domain, task_family, ",".join(sorted(source_case_ids)))
    steps = [
        {
            "node_id": f"node-{index:03d}",
            "action_type": "apply_capability",
            "capability": capability,
            "input_bindings": {slot["slot_id"]: f"inputs.{slot['slot_id']}" for slot in input_slots},
            "expected_effects": [_predicate(f"effect-{index:03d}", "exists", f"node-{index:03d}.output", True)],
            "timeout_ms": None,
            "retry_policy": {"max_attempts": 1, "backoff_ms": 0},
            "on_success": f"node-{index + 1:03d}" if index < len(capabilities) else None,
            "on_failure": None,
            "on_uncertain": None,
            "human_review_required": False,
        }
        for index, capability in enumerate(capabilities, start=1)
    ]
    transitions = [
        {
            "from_node_id": steps[index]["node_id"],
            "to_node_id": steps[index + 1]["node_id"],
            "condition": None,
        }
        for index in range(len(steps) - 1)
    ]
    action_pattern = {
        **v2_header("action_pattern", manifest),
        "pattern_id": pattern_id,
        "pattern_version": "0.1.0",
        "parent_pattern_version": None,
        "owner": owner,
        "domain": domain,
        "task_family": task_family,
        "goal_template": f"Solve {{task}} in {domain}/{task_family}.",
        "input_slots": input_slots,
        "preconditions": preconditions,
        "required_observations": _required_observations(graphs),
        "steps": steps,
        "transitions": transitions,
        "invariants": [_predicate("invariant-no-hidden-chain-of-thought", "eq", "hidden_chain_of_thought_reused", False)],
        "abort_conditions": [
            _predicate(f"abort-{index:03d}", "observed", "failure_mode", failure)
            for index, failure in enumerate(
                _unique_strings(ref for graph in graphs for ref in graph.get("failure_refs", [])),
                start=1,
            )
        ],
        "recovery_actions": [],
        "success_conditions": [_predicate("success-task-output", "exists", "final_output", True)],
        "forbidden_contexts": [_predicate("forbidden-quarantined-source", "eq", "quarantined_source", True)],
        "required_capabilities": capabilities,
        "source_case_ids": source_case_ids,
        "validation_profile_id": None,
        "lifecycle_status": "draft",
    }
    validate_action_pattern_v2(action_pattern, manifest)
    return action_pattern


def validate_action_pattern_graph(action_pattern: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    steps = action_pattern.get("steps") if isinstance(action_pattern.get("steps"), list) else []
    node_ids = [str(step.get("node_id")) for step in steps if isinstance(step, dict) and step.get("node_id")]
    if not steps:
        issues.append({"code": "missing_steps", "message": "ActionPattern requires at least one executable step"})
    if not action_pattern.get("preconditions"):
        issues.append({"code": "missing_precondition", "message": "ActionPattern has no entry preconditions"})
    if len(action_pattern.get("source_case_ids") or []) < 3:
        issues.append({"code": "low_source_diversity", "message": "fewer than three source cases"})
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for transition in action_pattern.get("transitions") or []:
        if not isinstance(transition, dict):
            continue
        from_node = str(transition.get("from_node_id") or "")
        to_node = str(transition.get("to_node_id") or "")
        if from_node not in adjacency or to_node not in adjacency:
            issues.append({"code": "invalid_transition", "message": f"transition references unknown node {from_node}->{to_node}"})
            continue
        adjacency[from_node].append(to_node)
    for step in steps:
        if not isinstance(step, dict):
            continue
        from_node = str(step.get("node_id") or "")
        for field_name in ("on_success", "on_failure", "on_uncertain"):
            target = step.get(field_name)
            if target is None:
                continue
            target_id = str(target)
            if target_id not in adjacency:
                issues.append({"code": "invalid_node_edge", "message": f"{from_node}.{field_name} references unknown node {target_id}"})
                continue
            if from_node in adjacency and target_id not in adjacency[from_node]:
                adjacency[from_node].append(target_id)
    for recovery in action_pattern.get("recovery_actions") or []:
        if not isinstance(recovery, dict):
            continue
        target_id = str(recovery.get("action_node_id") or "")
        if target_id not in adjacency:
            issues.append({"code": "invalid_recovery_action", "message": f"recovery action references unknown node {target_id}"})
    reachable: set[str] = set()
    if node_ids:
        stack = [node_ids[0]]
        while stack:
            node = stack.pop()
            if node in reachable:
                continue
            reachable.add(node)
            stack.extend(adjacency.get(node, []))
    for node_id in node_ids:
        if node_id not in reachable:
            issues.append({"code": "unreachable_node", "message": f"{node_id} is unreachable"})
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            issues.append({"code": "cycle_without_bound", "message": f"cycle detected at {node_id}"})
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for next_node in adjacency.get(node_id, []):
            visit(next_node)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_ids:
        visit(node_id)
    passed = not issues
    return {
        "schema": ACTION_PATTERN_VALIDATION_REPORT_SCHEMA,
        "pattern_id": action_pattern.get("pattern_id"),
        "pattern_version": action_pattern.get("pattern_version"),
        "passed": passed,
        "issues": issues,
        "warnings": warnings,
        "reachable_node_ids": sorted(reachable),
    }
