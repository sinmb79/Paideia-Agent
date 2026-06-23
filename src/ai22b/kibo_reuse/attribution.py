from __future__ import annotations

from typing import Any, Iterable

from .contracts_adapter import validate_action_pattern_v2, validate_attribution_report_v2, validate_outcome_evidence_v2
from .outcome_evidence import ACTION_RECEIPT_SCHEMA
from .outcome_evidence import SUCCESS_RECEIPT_STATUSES
from .outcome_evidence import _validate_action_receipt as _validate_action_receipt_payload
from .v2_artifacts import stable_id, v2_header


ATTRIBUTION_BUILD_RESULT_SCHEMA = "paideia-outcome-attribution-build-result/v1"


def build_outcome_attribution_report(
    action_pattern: dict[str, Any],
    outcome_evidence: dict[str, Any],
    manifest: dict[str, Any],
    *,
    action_receipts: Iterable[dict[str, Any]] = (),
    comparison_baseline: str | None = None,
) -> dict[str, Any]:
    validate_action_pattern_v2(action_pattern, manifest)
    validate_outcome_evidence_v2(outcome_evidence, manifest)
    if outcome_evidence.get("status") != "verified":
        raise ValueError("Outcome attribution requires verified OutcomeEvidence")
    if outcome_evidence.get("binary_success") is None:
        raise ValueError("Outcome attribution requires binary_success to be observed")
    if outcome_evidence["pattern_id"] != action_pattern["pattern_id"]:
        raise ValueError("Outcome evidence pattern_id mismatch")
    if outcome_evidence["pattern_version"] != action_pattern["pattern_version"]:
        raise ValueError("Outcome evidence pattern_version mismatch")
    receipts = [_validate_receipt_for_outcome(dict(receipt), action_pattern, outcome_evidence) for receipt in action_receipts]
    step_credits = _step_credits(action_pattern, outcome_evidence, receipts)
    report = {
        **v2_header("attribution_report", manifest),
        "report_id": stable_id(
            "attribution",
            outcome_evidence["evidence_id"],
            action_pattern["pattern_id"],
            action_pattern["pattern_version"],
        ),
        "outcome_evidence_id": outcome_evidence["evidence_id"],
        "pattern_contribution": _pattern_contribution(outcome_evidence, receipts),
        "llm_contribution": 0.1,
        "tool_contribution": 0.1 if receipts else 0.0,
        "human_contribution": 0.25 if str(outcome_evidence.get("verifier_type")).casefold() == "manual" else 0.0,
        "environment_contribution": 0.2 if outcome_evidence.get("environment_fingerprint") in {"", "unknown"} else 0.1,
        "attribution_confidence": min(float(outcome_evidence.get("confidence") or 0.0), 0.9 if receipts else 0.5),
        "confounders": _confounders(outcome_evidence, receipts),
        "comparison_baseline": comparison_baseline if comparison_baseline is not None else outcome_evidence.get("baseline_ref"),
        "step_credits": step_credits,
    }
    validate_attribution_report_v2(report, manifest)
    return report


def build_outcome_attribution_report_result(
    action_pattern: dict[str, Any],
    outcome_evidence: dict[str, Any],
    manifest: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    report = build_outcome_attribution_report(action_pattern, outcome_evidence, manifest, **kwargs)
    return {
        "schema": ATTRIBUTION_BUILD_RESULT_SCHEMA,
        "attribution_report": report,
        "negative_step_count": sum(1 for credit in report["step_credits"] if credit["contribution_score"] < 0),
    }


def _step_credits(action_pattern: dict[str, Any], outcome_evidence: dict[str, Any], receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    receipt_by_node = {str(receipt.get("action_node_id") or ""): receipt for receipt in receipts}
    steps = [step for step in action_pattern.get("steps") or [] if isinstance(step, dict)]
    if not steps:
        return []
    success = outcome_evidence.get("binary_success") is True
    confidence = min(float(outcome_evidence.get("confidence") or 0.0), 0.9)
    per_step_success = round(1.0 / len(steps), 4)
    credits: list[dict[str, Any]] = []
    for step in steps:
        node_id = str(step.get("node_id") or "")
        receipt = receipt_by_node.get(node_id)
        receipt_failed = receipt is not None and str(receipt.get("result_status") or "").casefold() not in SUCCESS_RECEIPT_STATUSES
        negative = receipt_failed or (not success and receipt is None)
        credits.append(
            {
                "step_id": node_id,
                "contribution_score": -per_step_success if negative else per_step_success,
                "causal_confidence": confidence if receipt is not None else min(confidence, 0.5),
                "reason_codes": _reason_codes(success=success, receipt_failed=receipt_failed, receipt_present=receipt is not None),
            }
        )
    return credits


def _validate_receipt_for_outcome(receipt: dict[str, Any], action_pattern: dict[str, Any], outcome_evidence: dict[str, Any]) -> dict[str, Any]:
    _validate_action_receipt_payload(receipt)
    if receipt.get("schema") != ACTION_RECEIPT_SCHEMA:
        raise ValueError(f"Unsupported ActionReceipt schema: {receipt.get('schema')}")
    if receipt.get("pattern_id") != action_pattern.get("pattern_id"):
        raise ValueError("Action receipt pattern_id mismatch")
    if receipt.get("pattern_version") != action_pattern.get("pattern_version"):
        raise ValueError("Action receipt pattern_version mismatch")
    if receipt.get("run_id") != outcome_evidence.get("run_id"):
        raise ValueError("Action receipt run_id mismatch")
    receipt_id = receipt.get("receipt_id")
    if receipt_id not in set(outcome_evidence.get("action_receipt_refs") or []):
        raise ValueError("Action receipt is not referenced by OutcomeEvidence")
    valid_nodes = {step.get("node_id") for step in action_pattern.get("steps") or [] if isinstance(step, dict)}
    if receipt.get("action_node_id") not in valid_nodes:
        raise ValueError("Action receipt action_node_id is not in ActionPattern")
    return receipt


def _pattern_contribution(outcome_evidence: dict[str, Any], receipts: list[dict[str, Any]]) -> float:
    base = min(float(outcome_evidence.get("confidence") or 0.0), 1.0)
    if outcome_evidence.get("binary_success") is False:
        return round(base * 0.2, 4)
    return round(base * (0.7 if receipts else 0.3), 4)


def _confounders(outcome_evidence: dict[str, Any], receipts: list[dict[str, Any]]) -> list[str]:
    confounders: list[str] = []
    if not receipts:
        confounders.append("missing_action_receipts")
    if not outcome_evidence.get("baseline_ref"):
        confounders.append("missing_baseline")
    if outcome_evidence.get("status") != "verified":
        confounders.append(f"status_{outcome_evidence.get('status')}")
    return confounders


def _reason_codes(*, success: bool, receipt_failed: bool, receipt_present: bool) -> list[str]:
    if receipt_failed:
        return ["receipt_failed", "negative_step_credit"]
    if not success and not receipt_present:
        return ["outcome_failed", "missing_step_receipt"]
    if receipt_present:
        return ["receipt_matched", "goal_progress"]
    return ["inferred_credit"]
