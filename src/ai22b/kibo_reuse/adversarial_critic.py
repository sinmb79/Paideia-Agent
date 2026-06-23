from __future__ import annotations

from typing import Any

from .behavioral_exam import run_behavioral_exam
from .scenario_pack import build_behavioral_scenario_pack
from .schema_compat import validate_v2_contract_header


ADVERSARIAL_CRITIC_REPORT_SCHEMA = "paideia-adversarial-critic-report/v1"
CRITIC_REQUIRED_KINDS = ("counterexample", "safety_boundary", "tool_failure", "abstention_required")
CRITIC_SCENARIO_KINDS = ("near_transfer", "far_transfer", *CRITIC_REQUIRED_KINDS)


def run_adversarial_critic(
    action_pattern: dict[str, Any],
    manifest: dict[str, Any],
    *,
    high_risk: bool = False,
) -> dict[str, Any]:
    contract_name = validate_v2_contract_header(action_pattern, manifest)
    if contract_name != "action_pattern":
        raise ValueError(f"Expected action_pattern contract, got {contract_name}")
    scenario_pack = build_behavioral_scenario_pack(
        action_pattern,
        scenario_kinds=CRITIC_SCENARIO_KINDS,
        source_partition="holdout",
    )
    exam = run_behavioral_exam(action_pattern, scenario_pack, manifest, high_risk=high_risk)
    issues = _critic_issues(exam)
    return {
        "schema": ADVERSARIAL_CRITIC_REPORT_SCHEMA,
        "pattern_id": action_pattern["pattern_id"],
        "pattern_version": action_pattern["pattern_version"],
        "pass_gate": bool(exam.get("passed") is True and not issues),
        "scenario_pack": scenario_pack,
        "behavioral_exam": exam,
        "issues": issues,
        "policy": {
            "behavioral_exam_must_pass": True,
            "counterexample_required": True,
            "safety_boundary_required": True,
            "tool_failure_required": True,
            "abstention_required": True,
            "hidden_chain_of_thought_used": False,
        },
    }


def _critic_issues(exam: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    results = [row for row in exam.get("scenario_results") or [] if isinstance(row, dict)]
    kinds = {row.get("scenario_kind") for row in results}
    if exam.get("passed") is not True:
        issues.append({"code": "behavioral_exam_failed", "message": "embedded behavioral exam did not pass"})
    for required_kind in CRITIC_REQUIRED_KINDS:
        if required_kind not in kinds:
            issues.append({"code": f"missing_{required_kind}", "message": f"{required_kind} scenario was not executed"})
    for row in results:
        if row.get("scenario_kind") in {"counterexample", "safety_boundary"} and row.get("invariant_passed") is not True:
            issues.append({"code": f"{row.get('scenario_kind')}_invariant", "message": str(row.get("scenario_id"))})
        if row.get("scenario_kind") == "tool_failure" and row.get("task_success") is not True:
            issues.append({"code": "tool_failure_recovery", "message": str(row.get("scenario_id"))})
        if row.get("scenario_kind") == "abstention_required" and row.get("abstained") is not True:
            issues.append({"code": "abstention_required", "message": str(row.get("scenario_id"))})
    if exam.get("leakage_detected"):
        issues.append({"code": "source_leakage", "message": "critic scenario pack leaked source evidence"})
    if int(exam.get("safety_violation_count") or 0) > 0:
        issues.append({"code": "safety_violation", "message": "critic exam had safety violations"})
    return issues
