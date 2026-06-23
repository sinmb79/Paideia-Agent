from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Iterable

from .contracts_adapter import validate_action_pattern_v2, validate_outcome_evidence_v2
from .v2_artifacts import evidence_hash, stable_id, v2_header


ACTION_RECEIPT_SCHEMA = "paideia-kibo-action-receipt/v1"
OUTCOME_INGEST_RESULT_SCHEMA = "paideia-outcome-ingest-result/v1"
EDGE_ACTION_RECEIPT_SCHEMA = "paideia-edge-action-receipt/v1"
INDEPENDENT_VERIFIER_TYPES = {
    "automated_verifier",
    "certified_controller",
    "external_audit",
    "independent_test",
    "independent_verifier",
}
MANUAL_VERIFIER_TYPES = {"", "manual", "none", "self_report", "user", "user_feedback"}
SUCCESS_RECEIPT_STATUSES = {"completed", "passed", "success", "succeeded"}
OUTCOME_STATUSES = {"pending", "verified", "contested", "invalidated", "expired"}


def build_action_receipt(
    *,
    run_id: str,
    pattern_id: str,
    pattern_version: str,
    action_node_id: str,
    capability: str,
    started_at: str,
    completed_at: str | None,
    result_status: str,
    requested_inputs: dict[str, Any] | None = None,
    requested_inputs_hash: str | None = None,
    observed_effects: Iterable[dict[str, Any]] = (),
    error_code: str | None = None,
    retry_count: int = 0,
    resource_usage: dict[str, float] | None = None,
    artifact_hashes: Iterable[str] = (),
) -> dict[str, Any]:
    inputs_hash = requested_inputs_hash or _digest(requested_inputs or {})
    receipt = {
        "schema": ACTION_RECEIPT_SCHEMA,
        "receipt_id": stable_id("action-receipt", run_id, pattern_id, pattern_version, action_node_id, started_at),
        "run_id": run_id,
        "pattern_id": pattern_id,
        "pattern_version": pattern_version,
        "action_node_id": action_node_id,
        "capability": capability,
        "requested_inputs_hash": inputs_hash,
        "started_at": started_at,
        "completed_at": completed_at,
        "result_status": result_status,
        "observed_effects": [dict(item) for item in observed_effects],
        "error_code": error_code,
        "retry_count": max(0, int(retry_count)),
        "resource_usage": {str(key): float(value) for key, value in (resource_usage or {}).items()},
        "artifact_hashes": list(dict.fromkeys(str(item) for item in artifact_hashes if str(item))),
    }
    _validate_action_receipt(receipt)
    return receipt


def build_outcome_evidence(
    action_pattern: dict[str, Any],
    manifest: dict[str, Any],
    *,
    task_id: str,
    action_receipts: Iterable[dict[str, Any]] = (),
    verifier_report: dict[str, Any] | None = None,
    run_id: str | None = None,
    environment_fingerprint: str | None = None,
    task_difficulty: float = 0.5,
    started_at: str | None = None,
    observed_at: str | None = None,
    baseline_ref: str | None = None,
) -> dict[str, Any]:
    validate_action_pattern_v2(action_pattern, manifest)
    receipts = [
        _normalize_action_receipt(receipt, action_pattern=action_pattern, run_id=run_id)
        for receipt in action_receipts
    ]
    resolved_run_id = run_id or _first_string((receipt.get("run_id") for receipt in receipts)) or stable_id(
        "run",
        action_pattern["pattern_id"],
        task_id,
    )
    for receipt in receipts:
        if receipt["run_id"] != resolved_run_id:
            raise ValueError("Action receipt run_id mismatch")
    verifier = dict(verifier_report or {})
    verifier_type = str(verifier.get("verifier_type") or "manual")
    started = started_at or _first_string((receipt.get("started_at") for receipt in receipts)) or str(verifier.get("started_at") or "") or _now_utc()
    observed = observed_at or str(verifier.get("observed_at") or "") or _first_string(
        (receipt.get("completed_at") for receipt in receipts if receipt.get("completed_at"))
    ) or _now_utc()
    binary_success = _optional_bool(verifier.get("binary_success"), field_name="binary_success")
    if binary_success is None and receipts:
        binary_success = all(_receipt_succeeded(receipt) for receipt in receipts)
    safety_score = _optional_score(verifier.get("safety_score"))
    status = _resolve_status(verifier, verifier_type=verifier_type, receipts=receipts)
    evidence = {
        **v2_header("outcome_evidence", manifest),
        "evidence_id": stable_id(
            "outcome-evidence",
            action_pattern["pattern_id"],
            action_pattern["pattern_version"],
            task_id,
            resolved_run_id,
            observed,
        ),
        "pattern_id": action_pattern["pattern_id"],
        "pattern_version": action_pattern["pattern_version"],
        "task_id": task_id,
        "run_id": resolved_run_id,
        "environment_fingerprint": environment_fingerprint or str(verifier.get("environment_fingerprint") or "unknown"),
        "task_difficulty": _score(task_difficulty, default=0.5),
        "started_at": started,
        "observed_at": observed,
        "outcome_latency_seconds": _optional_non_negative(verifier.get("outcome_latency_seconds")),
        "technical_score": _optional_score(verifier.get("technical_score")),
        "safety_score": safety_score,
        "user_utility_score": _optional_score(verifier.get("user_utility_score")),
        "binary_success": binary_success,
        "baseline_ref": baseline_ref if baseline_ref is not None else verifier.get("baseline_ref"),
        "verifier_type": verifier_type,
        "verifier_id": verifier.get("verifier_id"),
        "provenance": _provenance(receipts, verifier),
        "action_receipt_refs": [receipt["receipt_id"] for receipt in receipts],
        "artifact_hashes": _artifact_hashes(receipts, verifier),
        "confidence": _confidence(verifier, verifier_type=verifier_type, receipts=receipts, status=status),
        "status": status,
    }
    validate_outcome_evidence_v2(evidence, manifest)
    return evidence


def build_outcome_ingest_report(
    action_pattern: dict[str, Any],
    manifest: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    evidence = build_outcome_evidence(action_pattern, manifest, **kwargs)
    return {
        "schema": OUTCOME_INGEST_RESULT_SCHEMA,
        "status": evidence["status"],
        "outcome_evidence": evidence,
        "field_validation_candidate": _field_validation_candidate(evidence),
    }


def _normalize_action_receipt(receipt: dict[str, Any], *, action_pattern: dict[str, Any], run_id: str | None) -> dict[str, Any]:
    if receipt.get("schema") == EDGE_ACTION_RECEIPT_SCHEMA:
        normalized = build_action_receipt(
            run_id=str(run_id or receipt.get("decision_cycle_id") or ""),
            pattern_id=action_pattern["pattern_id"],
            pattern_version=action_pattern["pattern_version"],
            action_node_id=str(receipt.get("step_id") or ""),
            capability=str(receipt.get("capability_id") or ""),
            requested_inputs_hash=str(receipt.get("input_digest") or ""),
            started_at=str(receipt.get("requested_at") or ""),
            completed_at=receipt.get("completed_at"),
            result_status=str(receipt.get("status") or "unknown"),
            observed_effects=({"side_effect": item} for item in receipt.get("observed_side_effects") or []),
            error_code=receipt.get("error_code"),
            artifact_hashes=[item for item in (receipt.get("output_digest"),) if item],
        )
        return normalized
    normalized = dict(receipt)
    _validate_action_receipt(normalized)
    if normalized["pattern_id"] != action_pattern["pattern_id"]:
        raise ValueError("Action receipt pattern_id mismatch")
    if normalized["pattern_version"] != action_pattern["pattern_version"]:
        raise ValueError("Action receipt pattern_version mismatch")
    return normalized


def _validate_action_receipt(receipt: dict[str, Any]) -> None:
    required = (
        "schema",
        "receipt_id",
        "run_id",
        "pattern_id",
        "pattern_version",
        "action_node_id",
        "capability",
        "requested_inputs_hash",
        "started_at",
        "completed_at",
        "result_status",
        "observed_effects",
        "error_code",
        "retry_count",
        "resource_usage",
        "artifact_hashes",
    )
    missing = [field for field in required if field not in receipt]
    if missing:
        raise ValueError(f"ActionReceipt missing required fields: {', '.join(missing)}")
    if receipt.get("schema") != ACTION_RECEIPT_SCHEMA:
        raise ValueError(f"Unsupported ActionReceipt schema: {receipt.get('schema')}")
    for field in ("receipt_id", "run_id", "pattern_id", "pattern_version", "action_node_id", "capability", "requested_inputs_hash", "started_at", "result_status"):
        if not isinstance(receipt.get(field), str) or not receipt[field]:
            raise ValueError(f"ActionReceipt {field} must be a non-empty string")
    if receipt.get("completed_at") is not None and not isinstance(receipt.get("completed_at"), str):
        raise ValueError("ActionReceipt completed_at must be a string or null")
    if not isinstance(receipt.get("observed_effects"), list) or not all(isinstance(item, dict) for item in receipt["observed_effects"]):
        raise ValueError("ActionReceipt observed_effects must be a list of objects")
    if receipt.get("error_code") is not None and not isinstance(receipt.get("error_code"), str):
        raise ValueError("ActionReceipt error_code must be a string or null")
    if not isinstance(receipt.get("retry_count"), int) or isinstance(receipt.get("retry_count"), bool) or receipt["retry_count"] < 0:
        raise ValueError("ActionReceipt retry_count must be a non-negative integer")
    if not isinstance(receipt.get("resource_usage"), dict):
        raise ValueError("ActionReceipt resource_usage must be an object")
    if not isinstance(receipt.get("artifact_hashes"), list) or not all(isinstance(item, str) for item in receipt["artifact_hashes"]):
        raise ValueError("ActionReceipt artifact_hashes must be a list of strings")


def _resolve_status(verifier: dict[str, Any], *, verifier_type: str, receipts: list[dict[str, Any]]) -> str:
    raw_status = str(verifier.get("status") or "").casefold()
    if raw_status in {"pending", "contested", "invalidated", "expired"}:
        return raw_status
    if raw_status and raw_status not in OUTCOME_STATUSES:
        raise ValueError(f"Unsupported verifier outcome status: {raw_status}")
    if _is_independent_verifier(verifier_type) and receipts:
        if not all(_receipt_succeeded(receipt) for receipt in receipts) and verifier.get("binary_success") is not False:
            return "pending"
        return "verified"
    return "pending"


def _provenance(receipts: list[dict[str, Any]], verifier: dict[str, Any]) -> list[dict[str, Any]]:
    provenance = [
        {
            "source_id": receipt["receipt_id"],
            "source_type": "action_receipt",
            "confidence": 1.0 if _receipt_succeeded(receipt) else 0.7,
            "artifact_hash": _digest(receipt),
        }
        for receipt in receipts
    ]
    if verifier:
        provenance.append(
            {
                "source_id": str(verifier.get("verifier_id") or "verifier-report"),
                "source_type": str(verifier.get("verifier_type") or "manual"),
                "confidence": _score(verifier.get("confidence"), default=0.25),
                "artifact_hash": _digest(verifier),
            }
        )
    return provenance


def _artifact_hashes(receipts: list[dict[str, Any]], verifier: dict[str, Any]) -> list[str]:
    hashes: list[str] = []
    for receipt in receipts:
        hashes.extend(receipt.get("artifact_hashes") or [])
        hashes.append(_digest(receipt))
    if verifier:
        raw_hashes = verifier.get("artifact_hashes") or verifier.get("artifact_refs") or []
        if isinstance(raw_hashes, str):
            raw_hashes = [raw_hashes]
        hashes.extend(str(item) for item in raw_hashes if str(item))
        hashes.append(_digest(verifier))
    return list(dict.fromkeys(hashes))


def _confidence(verifier: dict[str, Any], *, verifier_type: str, receipts: list[dict[str, Any]], status: str) -> float:
    confidence = _score(verifier.get("confidence"), default=0.25)
    if status != "verified":
        return min(confidence, 0.25)
    if not _is_independent_verifier(verifier_type):
        return min(confidence, 0.25)
    if not receipts:
        return min(confidence, 0.5)
    return confidence


def _field_validation_candidate(evidence: dict[str, Any]) -> bool:
    safety_score = evidence.get("safety_score")
    return bool(
        _is_independent_verifier(str(evidence.get("verifier_type") or ""))
        and evidence.get("status") == "verified"
        and evidence.get("binary_success") is True
        and safety_score is not None
        and float(safety_score) >= 0.95
        and _has_receipt_provenance(evidence)
    )


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


def _is_independent_verifier(verifier_type: str) -> bool:
    return verifier_type.casefold() in INDEPENDENT_VERIFIER_TYPES


def _receipt_succeeded(receipt: dict[str, Any]) -> bool:
    return str(receipt.get("result_status") or "").casefold() in SUCCESS_RECEIPT_STATUSES


def _score(value: Any, *, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(numeric):
        raise ValueError("score values must be finite")
    return max(0.0, min(1.0, numeric))


def _optional_score(value: Any) -> float | None:
    return None if value is None else _score(value)


def _optional_non_negative(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        raise ValueError("numeric values must be finite")
    return max(0.0, numeric)


def _optional_bool(value: Any, *, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().casefold()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    raise ValueError(f"{field_name} must be a boolean")


def _first_string(values: Iterable[Any]) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + evidence_hash(payload)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
