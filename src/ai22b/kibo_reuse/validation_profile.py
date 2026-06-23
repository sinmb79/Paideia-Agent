from __future__ import annotations

from typing import Any, Iterable

from .contracts_adapter import validate_outcome_evidence_v2, validation_profile_reuse_ceiling
from .schema_compat import validate_v2_contract_header
from .v2_artifacts import stable_id, v2_header


VALIDATION_PROFILE_BUILD_SCHEMA = "paideia-validation-profile-build-result/v1"
RUNTIME_GATE_SCHEMA = "paideia-v2-runtime-gate/v1"
REQUESTED_REUSE_MODES = {"reject_and_solve_fresh", "reference_only", "partial_reuse", "direct_reuse", "strong_reuse"}
CEILING_RANK = {
    "reject_and_solve_fresh": 0,
    "reference_only": 1,
    "partial_reuse": 2,
    "strong_reuse": 3,
}
REQUESTED_MODE_RANK = {
    "reject_and_solve_fresh": 0,
    "reference_only": 1,
    "partial_reuse": 2,
    "direct_reuse": 3,
    "strong_reuse": 3,
}
RANK_MODE = {
    0: "reject_and_solve_fresh",
    1: "reference_only",
    2: "partial_reuse",
    3: "direct_reuse",
}
FIELD_VALIDATION_VERIFIERS = {"automated_verifier", "certified_controller", "external_audit", "independent_test", "independent_verifier"}


def build_pattern_validation_profile(
    action_pattern: dict[str, Any],
    manifest: dict[str, Any],
    *,
    structural_exam: dict[str, Any] | None = None,
    behavioral_exam: dict[str, Any] | None = None,
    critic_report: dict[str, Any] | None = None,
    field_evidence: Iterable[dict[str, Any]] = (),
    evidence_fresh_until: str | None = None,
    shadow_validation_passed: bool = False,
    high_risk: bool = False,
) -> dict[str, Any]:
    action_contract = validate_v2_contract_header(action_pattern, manifest)
    if action_contract != "action_pattern":
        raise ValueError(f"Expected action_pattern contract, got {action_contract}")
    behavioral = _behavioral_flags(behavioral_exam, action_pattern, manifest)
    field_passed = _field_validation_passed(field_evidence, action_pattern, manifest)
    critic_passed = bool(critic_report and critic_report.get("pass_gate") is True)
    high_risk_eligible = bool(
        behavioral["behavioral_exam_passed"]
        and behavioral["near_transfer_passed"]
        and behavioral["far_transfer_passed"]
        and behavioral["adversarial_exam_passed"]
        and shadow_validation_passed
        and critic_passed
        and field_passed
    )
    if high_risk and not high_risk_eligible:
        raise ValueError("High-risk validation requires behavioral near/far/adversarial, shadow, field, and critic evidence")
    profile = {
        **v2_header("validation_profile", manifest),
        "profile_id": stable_id(
            "validation-profile",
            action_pattern["pattern_id"],
            action_pattern["pattern_version"],
            evidence_fresh_until or "no-expiry",
        ),
        "pattern_id": action_pattern["pattern_id"],
        "pattern_version": action_pattern["pattern_version"],
        "structural_exam_passed": _structural_exam_passed(structural_exam),
        "behavioral_exam_passed": behavioral["behavioral_exam_passed"],
        "near_transfer_passed": behavioral["near_transfer_passed"],
        "far_transfer_passed": behavioral["far_transfer_passed"],
        "adversarial_exam_passed": behavioral["adversarial_exam_passed"],
        "shadow_validation_passed": bool(shadow_validation_passed),
        "field_validation_passed": field_passed,
        "critic_clearance_passed": critic_passed,
        "evidence_fresh_until": evidence_fresh_until,
        "high_risk_eligible": high_risk_eligible,
        "evidence_refs": _evidence_refs(structural_exam, behavioral_exam, critic_report, field_evidence),
    }
    validation_profile_reuse_ceiling(profile, manifest)
    return profile


def build_validation_profile_report(
    action_pattern: dict[str, Any],
    manifest: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    profile = build_pattern_validation_profile(action_pattern, manifest, **kwargs)
    return {
        "schema": VALIDATION_PROFILE_BUILD_SCHEMA,
        "validation_profile": profile,
        "reuse_ceiling": validation_profile_reuse_ceiling(profile, manifest),
    }


def runtime_gate_reuse_mode(
    requested_mode: str,
    validation_profile: dict[str, Any],
    manifest: dict[str, Any],
    *,
    risk_level: str = "normal",
) -> dict[str, Any]:
    ceiling = validation_profile_reuse_ceiling(validation_profile, manifest)
    allowed_mode, issues = _mode_for_ceiling(ceiling, requested_mode=requested_mode, risk_level=risk_level)
    return {
        "schema": RUNTIME_GATE_SCHEMA,
        "requested_mode": requested_mode,
        "allowed_mode": allowed_mode,
        "reuse_ceiling": ceiling,
        "risk_level": risk_level,
        "pattern_id": validation_profile.get("pattern_id"),
        "pattern_version": validation_profile.get("pattern_version"),
        "strong_reuse_allowed": ceiling == "strong_reuse" and allowed_mode == requested_mode,
        "automatic_action_allowed": False,
        "issues": issues,
    }


def _mode_for_ceiling(ceiling: str, *, requested_mode: str, risk_level: str) -> tuple[str, list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    if requested_mode not in REQUESTED_REUSE_MODES:
        return "reject_and_solve_fresh", [{"code": "unsupported_requested_mode", "message": f"unsupported requested mode: {requested_mode}"}]
    if ceiling not in CEILING_RANK:
        return "reject_and_solve_fresh", [{"code": "unsupported_reuse_ceiling", "message": f"unsupported reuse ceiling: {ceiling}"}]
    requested_rank = REQUESTED_MODE_RANK[requested_mode]
    ceiling_rank = CEILING_RANK[ceiling]
    allowed_rank = min(requested_rank, ceiling_rank)
    if risk_level.casefold() in {"high", "critical"} and allowed_rank >= REQUESTED_MODE_RANK["direct_reuse"]:
        allowed_rank = REQUESTED_MODE_RANK["partial_reuse"]
        issues.append({"code": "high_risk_direct_reuse_blocked", "message": "high-risk direct reuse requires a separate certified controller gate"})
    allowed_mode = requested_mode if allowed_rank == requested_rank and allowed_rank == REQUESTED_MODE_RANK["direct_reuse"] else RANK_MODE[allowed_rank]
    if allowed_rank < requested_rank:
        issues.append({"code": "requested_mode_downgraded", "message": f"{requested_mode} exceeds {ceiling} ceiling"})
    return allowed_mode, issues


def _structural_exam_passed(structural_exam: dict[str, Any] | None) -> bool:
    return bool(structural_exam and structural_exam.get("schema") == "paideia-pattern-exam-result/v1" and structural_exam.get("passed") is True)


def _behavioral_flags(
    behavioral_exam: dict[str, Any] | None,
    action_pattern: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, bool]:
    flags = {
        "behavioral_exam_passed": False,
        "near_transfer_passed": False,
        "far_transfer_passed": False,
        "adversarial_exam_passed": False,
    }
    if not behavioral_exam:
        return flags
    contract_name = validate_v2_contract_header(behavioral_exam, manifest)
    if contract_name != "behavioral_exam":
        raise ValueError(f"Expected behavioral_exam contract, got {contract_name}")
    if behavioral_exam.get("pattern_id") != action_pattern.get("pattern_id"):
        raise ValueError("Behavioral exam pattern_id mismatch")
    if behavioral_exam.get("pattern_version") != action_pattern.get("pattern_version"):
        raise ValueError("Behavioral exam pattern_version mismatch")
    results = [row for row in behavioral_exam.get("scenario_results") or [] if isinstance(row, dict)]
    flags["behavioral_exam_passed"] = bool(
        behavioral_exam.get("passed") is True
        and behavioral_exam.get("leakage_detected") is False
        and int(behavioral_exam.get("safety_violation_count") or 0) == 0
    )
    flags["near_transfer_passed"] = _all_kind_success(results, "near_transfer")
    flags["far_transfer_passed"] = _all_kind_success(results, "far_transfer")
    flags["adversarial_exam_passed"] = _all_kind_success(results, "counterexample") and _all_kind_success(results, "safety_boundary")
    return flags


def _all_kind_success(results: list[dict[str, Any]], scenario_kind: str) -> bool:
    kind_rows = [row for row in results if row.get("scenario_kind") == scenario_kind]
    return bool(kind_rows) and all(row.get("task_success") is True and row.get("invariant_passed") is True for row in kind_rows)


def _field_validation_passed(
    field_evidence: Iterable[dict[str, Any]],
    action_pattern: dict[str, Any],
    manifest: dict[str, Any],
) -> bool:
    rows = list(field_evidence)
    if not rows:
        return False
    for evidence in rows:
        validate_outcome_evidence_v2(evidence, manifest)
        if evidence.get("pattern_id") != action_pattern.get("pattern_id"):
            return False
        if evidence.get("pattern_version") != action_pattern.get("pattern_version"):
            return False
        if evidence.get("status") != "verified":
            return False
        if str(evidence.get("verifier_type") or "").casefold() not in FIELD_VALIDATION_VERIFIERS:
            return False
        if evidence.get("binary_success") is not True:
            return False
        safety_score = evidence.get("safety_score")
        if safety_score is None or float(safety_score) < 0.95:
            return False
        if not _has_receipt_provenance(evidence):
            return False
    return True


def _has_receipt_provenance(evidence: dict[str, Any]) -> bool:
    refs = [str(ref) for ref in evidence.get("action_receipt_refs") or [] if str(ref)]
    if not refs:
        return False
    provenance = evidence.get("provenance") or []
    if not isinstance(provenance, list):
        return False
    proven_refs = {
        row.get("source_id")
        for row in provenance
        if isinstance(row, dict)
        and row.get("source_type") == "action_receipt"
        and isinstance(row.get("artifact_hash"), str)
        and bool(row.get("artifact_hash"))
    }
    return set(refs).issubset(proven_refs)


def _evidence_refs(*groups: Any) -> list[str]:
    refs: list[str] = []
    for group in groups:
        if group is None:
            continue
        rows = list(group) if isinstance(group, (list, tuple)) else [group]
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in ("exam_id", "profile_id", "report_id", "evidence_id"):
                if row.get(key):
                    refs.append(str(row[key]))
                    break
    return list(dict.fromkeys(refs))
