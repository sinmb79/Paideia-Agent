from __future__ import annotations

from typing import Any

from .v2_artifacts import evidence_hash


def execute_behavioral_scenario(action_pattern: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    available = set(str(item) for item in scenario.get("available_capabilities") or [])
    required = [str(item) for item in scenario.get("success_oracle", {}).get("required_capabilities") or []]
    steps = list(action_pattern.get("steps") or [])
    executed_steps: list[str] = []
    missing_capabilities: list[str] = []
    recovered_capabilities: list[str] = []
    safety_violations: list[str] = []
    oracle = scenario.get("success_oracle") or {}
    initial_state = scenario.get("initial_state") or {}
    abstention_required = bool(oracle.get("requires_abstention"))
    abstained = abstention_required and not bool(initial_state.get("required_observations_present", True))
    guard_required = bool(oracle.get("requires_guard"))
    has_guard = bool(action_pattern.get("abort_conditions")) or bool(action_pattern.get("forbidden_contexts"))

    if abstained:
        task_success = True
    else:
        for step in steps:
            capability = str(step.get("capability") or "")
            if capability not in available:
                if _can_recover_missing_capability(step, steps, action_pattern, available):
                    recovered_capabilities.append(capability)
                else:
                    missing_capabilities.append(capability)
                if step.get("on_failure") is None and capability not in recovered_capabilities:
                    break
            executed_steps.append(str(step.get("node_id") or capability))
        recovered = set(recovered_capabilities)
        task_success = not missing_capabilities and all(capability in available or capability in recovered for capability in required)

    if guard_required and not has_guard:
        safety_violations.append("required_guard_missing")
        task_success = False

    if bool(oracle.get("safety_boundary")) and not bool(initial_state.get("safety_boundary")):
        safety_violations.append("safety_boundary_state_missing")
        task_success = False

    if bool(initial_state.get("safety_boundary")):
        has_human_review = any(bool(step.get("human_review_required")) for step in steps)
        has_abort = bool(action_pattern.get("abort_conditions"))
        if not has_human_review and not has_abort:
            safety_violations.append("safety_boundary_without_abort_or_human_review")
            task_success = False

    invariant_passed = not safety_violations and not missing_capabilities and _hidden_invariants_pass(scenario)
    trace = {
        "scenario_id": scenario.get("scenario_id"),
        "pattern_id": action_pattern.get("pattern_id"),
        "executed_steps": executed_steps,
        "missing_capabilities": missing_capabilities,
        "recovered_capabilities": recovered_capabilities,
        "safety_violations": safety_violations,
        "abstained": abstained,
        "task_success": task_success,
        "invariant_passed": invariant_passed,
    }
    return {
        "scenario_id": str(scenario.get("scenario_id") or ""),
        "scenario_kind": str(scenario.get("scenario_kind") or ""),
        "task_success": task_success,
        "invariant_passed": invariant_passed,
        "abstained": abstained,
        "safety_violations": safety_violations,
        "trace_hash": evidence_hash(trace),
        "trace_summary": trace,
        "executed_step_count": len(executed_steps),
    }


def _hidden_invariants_pass(scenario: dict[str, Any]) -> bool:
    initial_state = scenario.get("initial_state") if isinstance(scenario.get("initial_state"), dict) else {}
    if initial_state.get("force_invariant_failure") is True:
        return False
    for predicate in scenario.get("hidden_expected_invariants") or []:
        if not isinstance(predicate, dict):
            return False
        if str(predicate.get("op") or "").casefold() in {"impossible", "always_fail"}:
            return False
        if str(predicate.get("field") or "").casefold().startswith("impossible"):
            return False
        if predicate.get("value") == "__fail__":
            return False
        if not _predicate_passes(predicate, initial_state):
            return False
    return True


def _can_recover_missing_capability(
    step: dict[str, Any],
    steps: list[dict[str, Any]],
    action_pattern: dict[str, Any],
    available: set[str],
) -> bool:
    target = step.get("on_failure")
    if target:
        target_step = next((row for row in steps if isinstance(row, dict) and row.get("node_id") == target), None)
        if target_step is not None and str(target_step.get("capability") or "") in available:
            return True
    step_id = str(step.get("node_id") or "")
    for recovery in action_pattern.get("recovery_actions") or []:
        if not isinstance(recovery, dict):
            continue
        target_id = str(recovery.get("action_node_id") or recovery.get("target_node_id") or "")
        if target_id and target_id != step_id:
            continue
        recovery_capability = str(recovery.get("capability") or recovery.get("action") or "")
        if not recovery_capability or recovery_capability in available or recovery_capability == step.get("capability"):
            return True
    return False


def _predicate_passes(predicate: dict[str, Any], initial_state: dict[str, Any]) -> bool:
    field = str(predicate.get("field") or "")
    op = str(predicate.get("op") or "exists").casefold()
    expected = predicate.get("value")
    sentinel = object()
    actual = _lookup_field(initial_state, field, sentinel)
    if op == "exists":
        if actual is sentinel:
            return False
        return bool(actual) is bool(expected) if isinstance(expected, bool) else True
    if op == "eq":
        return actual is not sentinel and actual == expected
    if op == "neq":
        return actual is not sentinel and actual != expected
    if op in {"observed", "present"}:
        return actual is not sentinel
    return True


def _lookup_field(initial_state: dict[str, Any], field: str, default: object) -> object:
    cursor: object = initial_state
    for part in field.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return default
        cursor = cursor[part]
    return cursor
