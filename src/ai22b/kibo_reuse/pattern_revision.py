from __future__ import annotations

from typing import Any, Iterable

from .contracts_adapter import validate_action_pattern_v2, validate_attribution_report_v2, validate_pattern_revision_v2
from .v2_artifacts import stable_id, v2_header


PATTERN_REVISION_RESULT_SCHEMA = "paideia-pattern-revision-proposal-result/v1"


def build_pattern_revision_proposal(
    action_pattern: dict[str, Any],
    attribution_reports: Iterable[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    proposed_pattern_version: str | None = None,
) -> dict[str, Any]:
    validate_action_pattern_v2(action_pattern, manifest)
    reports = [dict(report) for report in attribution_reports]
    for report in reports:
        validate_attribution_report_v2(report, manifest)
    valid_step_ids = {step.get("node_id") for step in action_pattern.get("steps") or [] if isinstance(step, dict)}
    negative_step_credits = _negative_step_credits(reports)
    invalid_steps = sorted({credit.get("step_id") for credit in negative_step_credits if credit.get("step_id") not in valid_step_ids})
    if invalid_steps:
        raise ValueError(f"Attribution step credit references unknown ActionPattern nodes: {', '.join(map(str, invalid_steps))}")
    proposed_version = proposed_pattern_version or _bump_patch_version(str(action_pattern["pattern_version"]))
    status = "quarantined" if negative_step_credits else "draft"
    proposal = {
        **v2_header("pattern_revision", manifest),
        "revision_id": stable_id(
            "pattern-revision",
            action_pattern["pattern_id"],
            action_pattern["pattern_version"],
            proposed_version,
            ",".join(report.get("report_id", "") for report in reports),
        ),
        "pattern_id": action_pattern["pattern_id"],
        "from_pattern_version": action_pattern["pattern_version"],
        "proposed_pattern_version": proposed_version,
        "revision_reasons": _revision_reasons(negative_step_credits),
        "proposed_changes": _proposed_changes(negative_step_credits),
        "evidence_refs": [report["report_id"] for report in reports if report.get("report_id")],
        "requires_behavioral_exam": True,
        "requires_shadow_validation": True,
        "status": status,
    }
    validate_pattern_revision_v2(proposal, manifest)
    return proposal


def build_pattern_revision_result(
    action_pattern: dict[str, Any],
    attribution_reports: Iterable[dict[str, Any]],
    manifest: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    proposal = build_pattern_revision_proposal(action_pattern, attribution_reports, manifest, **kwargs)
    return {
        "schema": PATTERN_REVISION_RESULT_SCHEMA,
        "status": proposal["status"],
        "pattern_revision": proposal,
        "requires_retest": proposal["requires_behavioral_exam"] or proposal["requires_shadow_validation"],
    }


def _negative_step_credits(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    credits: list[dict[str, Any]] = []
    for report in reports:
        for credit in report.get("step_credits") or []:
            if isinstance(credit, dict) and float(credit.get("contribution_score") or 0.0) < 0.0:
                credits.append({**credit, "report_id": report.get("report_id")})
    return credits


def _revision_reasons(negative_step_credits: list[dict[str, Any]]) -> list[str]:
    reasons = ["negative_step_credit"] if negative_step_credits else ["no_revision_evidence"]
    for credit in negative_step_credits:
        for reason in credit.get("reason_codes") or []:
            if reason not in reasons:
                reasons.append(str(reason))
    return reasons


def _proposed_changes(negative_step_credits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for credit in negative_step_credits:
        step_id = str(credit.get("step_id") or "")
        if not step_id or step_id in seen:
            continue
        seen.add(step_id)
        changes.append(
            {
                "op": "quarantine_and_revise_action_node",
                "node_id": step_id,
                "reason_codes": list(credit.get("reason_codes") or ("negative_step_credit",)),
                "source_report_id": credit.get("report_id"),
            }
        )
    return changes


def _bump_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return f"{int(parts[0])}.{int(parts[1])}.{int(parts[2]) + 1}"
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        return f"{int(parts[0])}.{int(parts[1])}.1"
    return f"{version}.rev1"
