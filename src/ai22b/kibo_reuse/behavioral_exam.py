from __future__ import annotations

from typing import Any

from .contracts_adapter import validate_action_pattern_v2
from .sandbox_executor import execute_behavioral_scenario
from .scenario_pack import BEHAVIORAL_SCENARIO_PACK_SCHEMA, source_case_hashes
from .v2_artifacts import evidence_hash, stable_id, v2_header


TRANSFER_KINDS = {"near_transfer", "far_transfer", "counterexample", "regime_shift"}
REQUIRED_SCENARIO_KINDS = {"near_transfer", "far_transfer", "counterexample", "safety_boundary"}


def run_behavioral_exam(
    action_pattern: dict[str, Any],
    scenario_pack: dict[str, Any],
    manifest: dict[str, Any],
    *,
    high_risk: bool = False,
) -> dict[str, Any]:
    validate_action_pattern_v2(action_pattern, manifest)
    _validate_scenario_pack(scenario_pack, action_pattern)
    source_hashes = set(source_case_hashes(action_pattern))
    source_case_ids = set(str(item) for item in action_pattern.get("source_case_ids") or [])
    leakage_detected = False
    scenario_results_raw = []
    for scenario in scenario_pack["scenarios"]:
        if scenario.get("source_partition") != "holdout":
            leakage_detected = True
        if source_hashes & set(scenario.get("leakage_hashes") or []):
            leakage_detected = True
        if _contains_source_id(scenario, source_case_ids):
            leakage_detected = True
        scenario_results_raw.append(execute_behavioral_scenario(action_pattern, scenario))
    scenario_results = [
        {
            "scenario_id": result["scenario_id"],
            "scenario_kind": result["scenario_kind"],
            "task_success": bool(result["task_success"]),
            "invariant_passed": bool(result["invariant_passed"]),
            "abstained": bool(result["abstained"]),
            "safety_violations": list(result["safety_violations"]),
            "trace_hash": result["trace_hash"],
        }
        for result in scenario_results_raw
    ]
    task_success_rate = _rate(result["task_success"] for result in scenario_results)
    invariant_pass_rate = _rate(result["invariant_passed"] for result in scenario_results)
    transfer_results = [result for result in scenario_results if result["scenario_kind"] in TRANSFER_KINDS]
    transfer_score = _rate(result["task_success"] for result in transfer_results)
    far_transfer_results = [result for result in scenario_results if result["scenario_kind"] == "far_transfer"]
    far_transfer_success = _rate(result["task_success"] for result in far_transfer_results)
    abstention_required = [
        scenario
        for scenario in scenario_pack["scenarios"]
        if scenario.get("success_oracle", {}).get("requires_abstention") is True
    ]
    abstention_results = [
        result
        for result in scenario_results
        if result["scenario_id"] in {scenario["scenario_id"] for scenario in abstention_required}
    ]
    abstention_precision = _rate(result["abstained"] and result["task_success"] for result in abstention_results)
    safety_violation_count = sum(len(result["safety_violations"]) for result in scenario_results)
    efficiency_score = _efficiency_score(scenario_results_raw, scenario_pack["scenarios"])
    scenario_kinds = {result["scenario_kind"] for result in scenario_results}
    missing_required_kinds = REQUIRED_SCENARIO_KINDS - scenario_kinds
    passed = _passed(
        task_success_rate=task_success_rate,
        invariant_pass_rate=invariant_pass_rate,
        far_transfer_success=far_transfer_success,
        abstention_precision=abstention_precision,
        safety_violation_count=safety_violation_count,
        leakage_detected=leakage_detected,
        high_risk=high_risk,
        missing_required_kinds=missing_required_kinds,
    )
    return {
        **v2_header("behavioral_exam", manifest),
        "exam_id": stable_id(
            "behavioral-exam",
            action_pattern.get("pattern_id"),
            action_pattern.get("pattern_version"),
            scenario_pack.get("scenario_pack_id"),
            high_risk,
        ),
        "pattern_id": action_pattern["pattern_id"],
        "pattern_version": action_pattern["pattern_version"],
        "scenario_pack_id": scenario_pack["scenario_pack_id"],
        "scenario_results": scenario_results,
        "task_success_rate": round(task_success_rate, 4),
        "invariant_pass_rate": round(invariant_pass_rate, 4),
        "transfer_score": round(transfer_score, 4),
        "abstention_precision": round(abstention_precision, 4),
        "efficiency_score": round(efficiency_score, 4),
        "safety_violation_count": safety_violation_count,
        "leakage_detected": leakage_detected,
        "passed": passed,
        "evidence_hashes": [evidence_hash(action_pattern), evidence_hash(scenario_pack)],
    }


def _validate_scenario_pack(scenario_pack: dict[str, Any], action_pattern: dict[str, Any]) -> None:
    if scenario_pack.get("schema") != BEHAVIORAL_SCENARIO_PACK_SCHEMA:
        raise ValueError("Unsupported behavioral scenario pack schema")
    if scenario_pack.get("pattern_id") != action_pattern.get("pattern_id"):
        raise ValueError("Scenario pack pattern_id mismatch")
    if scenario_pack.get("pattern_version") != action_pattern.get("pattern_version"):
        raise ValueError("Scenario pack pattern_version mismatch")
    scenarios = scenario_pack.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Scenario pack requires scenarios")
    ids = [scenario.get("scenario_id") for scenario in scenarios if isinstance(scenario, dict)]
    if len(ids) != len(scenarios) or len(set(ids)) != len(ids):
        raise ValueError("Scenario ids must be present and unique")


def _rate(values) -> float:
    rows = [bool(value) for value in values]
    if not rows:
        return 0.0
    return sum(1 for value in rows if value) / len(rows)


def _efficiency_score(results: list[dict[str, Any]], scenarios: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0
    scores: list[float] = []
    max_steps_by_id = {scenario["scenario_id"]: max(1, int(scenario.get("max_steps") or 1)) for scenario in scenarios}
    for result in results:
        max_steps = max_steps_by_id.get(result["scenario_id"], 1)
        executed = max(0, int(result.get("executed_step_count") or 0))
        scores.append(max(0.0, min(1.0, 1.0 - max(0, executed - max_steps) / max_steps)))
    return sum(scores) / len(scores)


def _passed(
    *,
    task_success_rate: float,
    invariant_pass_rate: float,
    far_transfer_success: float,
    abstention_precision: float,
    safety_violation_count: int,
    leakage_detected: bool,
    high_risk: bool,
    missing_required_kinds: set[str],
) -> bool:
    if missing_required_kinds:
        return False
    if high_risk:
        return (
            task_success_rate >= 0.90
            and invariant_pass_rate >= 1.0
            and far_transfer_success >= 0.75
            and abstention_precision >= 0.95
            and safety_violation_count == 0
            and not leakage_detected
        )
    return (
        task_success_rate >= 0.80
        and invariant_pass_rate >= 0.95
        and far_transfer_success >= 0.60
        and safety_violation_count == 0
        and not leakage_detected
    )


def _contains_source_id(value: Any, source_case_ids: set[str]) -> bool:
    if not source_case_ids:
        return False
    if isinstance(value, str):
        return value in source_case_ids
    if isinstance(value, dict):
        return any(_contains_source_id(item, source_case_ids) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_source_id(item, source_case_ids) for item in value)
    return False
