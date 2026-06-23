from __future__ import annotations

import math
from typing import Any

from .models import PatternExamResult, RealWorldOutcome
from .schema_compat import validate_v2_contract_header


ACTION_PATTERN_LIFECYCLE_STATUSES = {
    "draft",
    "review_quarantine",
    "structural_validated",
    "behavioral_validated",
    "shadow_validated",
    "field_validated",
    "promoted",
    "suspended",
    "revoked",
}

CASE_GRAPH_REQUIRED_FIELDS = (
    "case_id",
    "owner",
    "domain",
    "task_family",
    "goal",
    "context_variables",
    "observations",
    "constraints",
    "action_steps",
    "branch_events",
    "outcome_refs",
    "failure_refs",
    "source_kibo_ids",
    "evidence_hashes",
)

ACTION_PATTERN_REQUIRED_FIELDS = (
    "pattern_id",
    "pattern_version",
    "parent_pattern_version",
    "owner",
    "domain",
    "task_family",
    "goal_template",
    "input_slots",
    "preconditions",
    "required_observations",
    "steps",
    "transitions",
    "invariants",
    "abort_conditions",
    "recovery_actions",
    "success_conditions",
    "forbidden_contexts",
    "required_capabilities",
    "source_case_ids",
    "validation_profile_id",
    "lifecycle_status",
)

VALIDATION_PROFILE_REQUIRED_FIELDS = (
    "profile_id",
    "pattern_id",
    "pattern_version",
    "structural_exam_passed",
    "behavioral_exam_passed",
    "near_transfer_passed",
    "far_transfer_passed",
    "adversarial_exam_passed",
    "shadow_validation_passed",
    "field_validation_passed",
    "critic_clearance_passed",
    "evidence_fresh_until",
    "high_risk_eligible",
    "evidence_refs",
)
OUTCOME_EVIDENCE_REQUIRED_FIELDS = (
    "evidence_id",
    "pattern_id",
    "pattern_version",
    "task_id",
    "run_id",
    "environment_fingerprint",
    "task_difficulty",
    "started_at",
    "observed_at",
    "outcome_latency_seconds",
    "technical_score",
    "safety_score",
    "user_utility_score",
    "binary_success",
    "baseline_ref",
    "verifier_type",
    "verifier_id",
    "provenance",
    "action_receipt_refs",
    "artifact_hashes",
    "confidence",
    "status",
)
ATTRIBUTION_REPORT_REQUIRED_FIELDS = (
    "report_id",
    "outcome_evidence_id",
    "pattern_contribution",
    "llm_contribution",
    "tool_contribution",
    "human_contribution",
    "environment_contribution",
    "attribution_confidence",
    "confounders",
    "comparison_baseline",
    "step_credits",
)
PATTERN_REVISION_REQUIRED_FIELDS = (
    "revision_id",
    "pattern_id",
    "from_pattern_version",
    "proposed_pattern_version",
    "revision_reasons",
    "proposed_changes",
    "evidence_refs",
    "requires_behavioral_exam",
    "requires_shadow_validation",
    "status",
)

CONTRACT_HEADER_FIELDS = ("schema", "schema_version", "contract_hash")
CASE_GRAPH_ALLOWED_FIELDS = (*CONTRACT_HEADER_FIELDS, *CASE_GRAPH_REQUIRED_FIELDS)
ACTION_PATTERN_ALLOWED_FIELDS = (*CONTRACT_HEADER_FIELDS, *ACTION_PATTERN_REQUIRED_FIELDS)
VALIDATION_PROFILE_ALLOWED_FIELDS = (*CONTRACT_HEADER_FIELDS, *VALIDATION_PROFILE_REQUIRED_FIELDS)
OUTCOME_EVIDENCE_ALLOWED_FIELDS = (*CONTRACT_HEADER_FIELDS, *OUTCOME_EVIDENCE_REQUIRED_FIELDS)
ATTRIBUTION_REPORT_ALLOWED_FIELDS = (*CONTRACT_HEADER_FIELDS, *ATTRIBUTION_REPORT_REQUIRED_FIELDS)
PATTERN_REVISION_ALLOWED_FIELDS = (*CONTRACT_HEADER_FIELDS, *PATTERN_REVISION_REQUIRED_FIELDS)

CASE_GRAPH_FIELD_RULES = {
    "case_id": "non_empty_string",
    "owner": "non_empty_string",
    "domain": "non_empty_string",
    "task_family": "non_empty_string",
    "goal": "string",
    "context_variables": "list",
    "observations": "list",
    "constraints": "list",
    "action_steps": "list",
    "branch_events": "list",
    "outcome_refs": "string_list",
    "failure_refs": "string_list",
    "source_kibo_ids": "string_list",
    "evidence_hashes": "string_list",
}

ACTION_PATTERN_FIELD_RULES = {
    "pattern_id": "non_empty_string",
    "pattern_version": "non_empty_string",
    "parent_pattern_version": "optional_string",
    "owner": "non_empty_string",
    "domain": "non_empty_string",
    "task_family": "non_empty_string",
    "goal_template": "string",
    "input_slots": "list",
    "preconditions": "list",
    "required_observations": "list",
    "steps": "list",
    "transitions": "list",
    "invariants": "list",
    "abort_conditions": "list",
    "recovery_actions": "list",
    "success_conditions": "list",
    "forbidden_contexts": "list",
    "required_capabilities": "string_list",
    "source_case_ids": "string_list",
    "validation_profile_id": "optional_string",
    "lifecycle_status": "non_empty_string",
}

VALIDATION_PROFILE_FIELD_RULES = {
    "profile_id": "non_empty_string",
    "pattern_id": "non_empty_string",
    "pattern_version": "non_empty_string",
    "structural_exam_passed": "boolean",
    "behavioral_exam_passed": "boolean",
    "near_transfer_passed": "boolean",
    "far_transfer_passed": "boolean",
    "adversarial_exam_passed": "boolean",
    "shadow_validation_passed": "boolean",
    "field_validation_passed": "boolean",
    "critic_clearance_passed": "boolean",
    "evidence_fresh_until": "optional_string",
    "high_risk_eligible": "boolean",
    "evidence_refs": "string_list",
}
OUTCOME_EVIDENCE_FIELD_RULES = {
    "evidence_id": "non_empty_string",
    "pattern_id": "non_empty_string",
    "pattern_version": "non_empty_string",
    "task_id": "non_empty_string",
    "run_id": "non_empty_string",
    "environment_fingerprint": "string",
    "task_difficulty": "score",
    "started_at": "string",
    "observed_at": "string",
    "outcome_latency_seconds": "optional_non_negative_number",
    "technical_score": "optional_score",
    "safety_score": "optional_score",
    "user_utility_score": "optional_score",
    "binary_success": "optional_boolean",
    "baseline_ref": "optional_string",
    "verifier_type": "string",
    "verifier_id": "optional_string",
    "provenance": "list",
    "action_receipt_refs": "string_list",
    "artifact_hashes": "string_list",
    "confidence": "score",
    "status": "non_empty_string",
}
OUTCOME_EVIDENCE_STATUSES = {"pending", "verified", "contested", "invalidated", "expired"}
PATTERN_REVISION_STATUSES = {"draft", "quarantined", "testing", "accepted", "rejected", "rolled_back"}
ATTRIBUTION_REPORT_FIELD_RULES = {
    "report_id": "non_empty_string",
    "outcome_evidence_id": "non_empty_string",
    "pattern_contribution": "score",
    "llm_contribution": "score",
    "tool_contribution": "score",
    "human_contribution": "score",
    "environment_contribution": "score",
    "attribution_confidence": "score",
    "confounders": "string_list",
    "comparison_baseline": "optional_string",
    "step_credits": "list",
}
PATTERN_REVISION_FIELD_RULES = {
    "revision_id": "non_empty_string",
    "pattern_id": "non_empty_string",
    "from_pattern_version": "non_empty_string",
    "proposed_pattern_version": "non_empty_string",
    "revision_reasons": "string_list",
    "proposed_changes": "list",
    "evidence_refs": "string_list",
    "requires_behavioral_exam": "boolean",
    "requires_shadow_validation": "boolean",
    "status": "non_empty_string",
}


def _require_fields(artifact: dict[str, Any], fields: tuple[str, ...], contract_name: str) -> None:
    missing = [field for field in fields if field not in artifact]
    blank = [field for field in fields if artifact.get(field) == ""]
    if missing or blank:
        raise ValueError(f"{contract_name} is missing required fields: {', '.join(missing + blank)}")


def _require_top_level_no_extra(artifact: dict[str, Any], fields: tuple[str, ...], contract_name: str) -> None:
    extra = sorted(set(artifact) - set(fields))
    if extra:
        raise ValueError(f"{contract_name} has unexpected fields: {', '.join(extra)}")


def _matches_rule(value: Any, rule: str) -> bool:
    if rule == "non_empty_string":
        return isinstance(value, str) and bool(value)
    if rule == "string":
        return isinstance(value, str)
    if rule == "optional_string":
        return value is None or isinstance(value, str)
    if rule == "boolean":
        return isinstance(value, bool)
    if rule == "optional_boolean":
        return value is None or isinstance(value, bool)
    if rule == "score":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and 0.0 <= float(value) <= 1.0
    if rule == "optional_score":
        return value is None or _matches_rule(value, "score")
    if rule == "optional_non_negative_number":
        return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and float(value) >= 0.0)
    if rule == "signed_score":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and -1.0 <= float(value) <= 1.0
    if rule == "list":
        return isinstance(value, list)
    if rule == "string_list":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    return True


def _require_field_types(artifact: dict[str, Any], rules: dict[str, str], contract_name: str) -> None:
    invalid = [field for field, rule in rules.items() if not _matches_rule(artifact.get(field), rule)]
    if invalid:
        raise ValueError(f"{contract_name} has invalid field types: {', '.join(invalid)}")


def _nested_error(path: str, message: str) -> None:
    raise ValueError(f"invalid nested payload: {path} {message}")


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _nested_error(path, "must be an object")
    return value


def _require_no_extra(value: dict[str, Any], allowed: tuple[str, ...], path: str) -> None:
    extra = sorted(set(value) - set(allowed))
    if extra:
        _nested_error(path, f"has unexpected fields: {', '.join(extra)}")


def _require_nested_fields(value: dict[str, Any], fields: tuple[str, ...], path: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        _nested_error(path, f"is missing fields: {', '.join(missing)}")


def _require_nested_rule(value: dict[str, Any], field_name: str, rule: str, path: str) -> None:
    if not _matches_rule(value.get(field_name), rule):
        _nested_error(f"{path}.{field_name}", f"must match {rule}")


def _require_optional_int(value: Any, path: str) -> None:
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
        _nested_error(path, "must be a non-negative integer or null")


def _require_non_negative_int(value: Any, path: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _nested_error(path, "must be a non-negative integer")


def _validate_predicate(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("predicate_id", "op", "field", "value")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "predicate_id", "non_empty_string", path)
    _require_nested_rule(item, "op", "non_empty_string", path)
    _require_nested_rule(item, "field", "non_empty_string", path)


def _validate_typed_slot(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("slot_id", "value_type", "required")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "slot_id", "non_empty_string", path)
    _require_nested_rule(item, "value_type", "non_empty_string", path)
    _require_nested_rule(item, "required", "boolean", path)


def _validate_typed_value(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("name", "value_type", "value")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "name", "non_empty_string", path)
    _require_nested_rule(item, "value_type", "non_empty_string", path)


def _validate_observation_spec(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("observation_id", "name", "value_type", "required", "freshness_ms")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "observation_id", "non_empty_string", path)
    _require_nested_rule(item, "name", "non_empty_string", path)
    _require_nested_rule(item, "value_type", "non_empty_string", path)
    _require_nested_rule(item, "required", "boolean", path)
    _require_optional_int(item.get("freshness_ms"), f"{path}.freshness_ms")


def _validate_constraint(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("constraint_id", "predicate", "severity")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "constraint_id", "non_empty_string", path)
    _validate_predicate(item.get("predicate"), f"{path}.predicate")
    _require_nested_rule(item, "severity", "non_empty_string", path)


def _validate_action_step_evidence(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("step_id", "action_type", "capability", "input_refs", "output_ref", "receipt_ref")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "step_id", "non_empty_string", path)
    _require_nested_rule(item, "action_type", "non_empty_string", path)
    _require_nested_rule(item, "capability", "non_empty_string", path)
    _require_nested_rule(item, "input_refs", "string_list", path)
    _require_nested_rule(item, "output_ref", "optional_string", path)
    _require_nested_rule(item, "receipt_ref", "optional_string", path)


def _validate_branch_event(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("event_id", "predicate", "selected_step_id")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "event_id", "non_empty_string", path)
    _validate_predicate(item.get("predicate"), f"{path}.predicate")
    _require_nested_rule(item, "selected_step_id", "non_empty_string", path)


def _validate_evidence_source(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("source_id", "source_type", "confidence", "artifact_hash")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "source_id", "non_empty_string", path)
    _require_nested_rule(item, "source_type", "non_empty_string", path)
    _require_nested_rule(item, "confidence", "score", path)
    _require_nested_rule(item, "artifact_hash", "optional_string", path)


def _validate_step_credit(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("step_id", "contribution_score", "causal_confidence", "reason_codes")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "step_id", "non_empty_string", path)
    _require_nested_rule(item, "contribution_score", "signed_score", path)
    _require_nested_rule(item, "causal_confidence", "score", path)
    _require_nested_rule(item, "reason_codes", "string_list", path)


def _validate_observation_requirement(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("observation_id", "value_type", "freshness_ms")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "observation_id", "non_empty_string", path)
    _require_nested_rule(item, "value_type", "non_empty_string", path)
    _require_optional_int(item.get("freshness_ms"), f"{path}.freshness_ms")


def _validate_retry_policy(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("max_attempts", "backoff_ms")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    if not isinstance(item.get("max_attempts"), int) or isinstance(item.get("max_attempts"), bool) or item["max_attempts"] < 1:
        _nested_error(f"{path}.max_attempts", "must be a positive integer")
    _require_non_negative_int(item.get("backoff_ms"), f"{path}.backoff_ms")


def _validate_action_node(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = (
        "node_id",
        "action_type",
        "capability",
        "input_bindings",
        "expected_effects",
        "timeout_ms",
        "retry_policy",
        "on_success",
        "on_failure",
        "on_uncertain",
        "human_review_required",
    )
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "node_id", "non_empty_string", path)
    _require_nested_rule(item, "action_type", "non_empty_string", path)
    _require_nested_rule(item, "capability", "non_empty_string", path)
    if not isinstance(item.get("input_bindings"), dict) or not all(isinstance(key, str) and isinstance(val, str) for key, val in item["input_bindings"].items()):
        _nested_error(f"{path}.input_bindings", "must be an object of string values")
    if not isinstance(item.get("expected_effects"), list):
        _nested_error(f"{path}.expected_effects", "must be a list")
    for index, predicate in enumerate(item["expected_effects"]):
        _validate_predicate(predicate, f"{path}.expected_effects[{index}]")
    _require_optional_int(item.get("timeout_ms"), f"{path}.timeout_ms")
    _validate_retry_policy(item.get("retry_policy"), f"{path}.retry_policy")
    _require_nested_rule(item, "on_success", "optional_string", path)
    _require_nested_rule(item, "on_failure", "optional_string", path)
    _require_nested_rule(item, "on_uncertain", "optional_string", path)
    _require_nested_rule(item, "human_review_required", "boolean", path)


def _validate_transition(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("from_node_id", "to_node_id", "condition")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "from_node_id", "non_empty_string", path)
    _require_nested_rule(item, "to_node_id", "non_empty_string", path)
    if item.get("condition") is not None:
        _validate_predicate(item["condition"], f"{path}.condition")


def _validate_recovery_action(value: Any, path: str) -> None:
    item = _require_object(value, path)
    fields = ("recovery_id", "trigger", "action_node_id")
    _require_no_extra(item, fields, path)
    _require_nested_fields(item, fields, path)
    _require_nested_rule(item, "recovery_id", "non_empty_string", path)
    _validate_predicate(item.get("trigger"), f"{path}.trigger")
    _require_nested_rule(item, "action_node_id", "non_empty_string", path)


def _validate_object_list(artifact: dict[str, Any], field_name: str, validator, contract_name: str) -> None:
    values = artifact.get(field_name)
    if not isinstance(values, list):
        raise ValueError(f"{contract_name} has invalid field types: {field_name}")
    for index, item in enumerate(values):
        validator(item, f"{field_name}[{index}]")


def _validate_action_pattern_nested_payload(artifact: dict[str, Any], contract_name: str) -> None:
    _validate_object_list(artifact, "input_slots", _validate_typed_slot, contract_name)
    _validate_object_list(artifact, "preconditions", _validate_predicate, contract_name)
    _validate_object_list(artifact, "required_observations", _validate_observation_requirement, contract_name)
    _validate_object_list(artifact, "steps", _validate_action_node, contract_name)
    _validate_object_list(artifact, "transitions", _validate_transition, contract_name)
    _validate_object_list(artifact, "invariants", _validate_predicate, contract_name)
    _validate_object_list(artifact, "abort_conditions", _validate_predicate, contract_name)
    _validate_object_list(artifact, "recovery_actions", _validate_recovery_action, contract_name)
    _validate_object_list(artifact, "success_conditions", _validate_predicate, contract_name)
    _validate_object_list(artifact, "forbidden_contexts", _validate_predicate, contract_name)


def _validate_case_graph_nested_payload(artifact: dict[str, Any], contract_name: str) -> None:
    _validate_object_list(artifact, "context_variables", _validate_typed_value, contract_name)
    _validate_object_list(artifact, "observations", _validate_observation_spec, contract_name)
    _validate_object_list(artifact, "constraints", _validate_constraint, contract_name)
    _validate_object_list(artifact, "action_steps", _validate_action_step_evidence, contract_name)
    _validate_object_list(artifact, "branch_events", _validate_branch_event, contract_name)


def validate_case_graph_v2(artifact: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    contract_name = validate_v2_contract_header(artifact, manifest)
    if contract_name != "case_graph":
        raise ValueError(f"Expected case_graph contract, got {contract_name}")
    _require_fields(artifact, CASE_GRAPH_REQUIRED_FIELDS, contract_name)
    _require_top_level_no_extra(artifact, CASE_GRAPH_ALLOWED_FIELDS, contract_name)
    _require_field_types(artifact, CASE_GRAPH_FIELD_RULES, contract_name)
    _validate_case_graph_nested_payload(artifact, contract_name)
    return {
        "schema": "paideia-agent-v2-contract-validation/v1",
        "contract_name": contract_name,
        "case_id": artifact.get("case_id"),
        "accepted": True,
    }


def validate_action_pattern_v2(artifact: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    contract_name = validate_v2_contract_header(artifact, manifest)
    if contract_name != "action_pattern":
        raise ValueError(f"Expected action_pattern contract, got {contract_name}")
    _require_fields(artifact, ACTION_PATTERN_REQUIRED_FIELDS, contract_name)
    _require_top_level_no_extra(artifact, ACTION_PATTERN_ALLOWED_FIELDS, contract_name)
    _require_field_types(artifact, ACTION_PATTERN_FIELD_RULES, contract_name)
    if artifact["lifecycle_status"] not in ACTION_PATTERN_LIFECYCLE_STATUSES:
        raise ValueError(f"Unsupported lifecycle_status: {artifact['lifecycle_status']}")
    _validate_action_pattern_nested_payload(artifact, contract_name)
    return {
        "schema": "paideia-agent-v2-contract-validation/v1",
        "contract_name": contract_name,
        "pattern_id": artifact.get("pattern_id"),
        "pattern_version": artifact.get("pattern_version"),
        "accepted": True,
    }


def validation_profile_reuse_ceiling(profile: dict[str, Any], manifest: dict[str, Any]) -> str:
    contract_name = validate_v2_contract_header(profile, manifest)
    if contract_name != "validation_profile":
        raise ValueError(f"Expected validation_profile contract, got {contract_name}")
    _require_fields(profile, VALIDATION_PROFILE_REQUIRED_FIELDS, contract_name)
    _require_top_level_no_extra(profile, VALIDATION_PROFILE_ALLOWED_FIELDS, contract_name)
    _require_field_types(profile, VALIDATION_PROFILE_FIELD_RULES, contract_name)
    if profile.get("field_validation_passed") is True:
        if (
            profile.get("behavioral_exam_passed") is True
            and profile.get("near_transfer_passed") is True
            and profile.get("far_transfer_passed") is True
            and profile.get("adversarial_exam_passed") is True
            and profile.get("shadow_validation_passed") is True
            and profile.get("critic_clearance_passed") is True
        ):
            return "strong_reuse"
    if profile.get("behavioral_exam_passed") is True and profile.get("near_transfer_passed") is True:
        return "partial_reuse"
    if profile.get("structural_exam_passed") is True:
        return "reference_only"
    return "reject_and_solve_fresh"


def validate_outcome_evidence_v2(artifact: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    contract_name = validate_v2_contract_header(artifact, manifest)
    if contract_name != "outcome_evidence":
        raise ValueError(f"Expected outcome_evidence contract, got {contract_name}")
    _require_fields(artifact, OUTCOME_EVIDENCE_REQUIRED_FIELDS, contract_name)
    _require_top_level_no_extra(artifact, OUTCOME_EVIDENCE_ALLOWED_FIELDS, contract_name)
    _require_field_types(artifact, OUTCOME_EVIDENCE_FIELD_RULES, contract_name)
    if artifact["status"] not in OUTCOME_EVIDENCE_STATUSES:
        raise ValueError(f"Unsupported outcome evidence status: {artifact['status']}")
    _validate_object_list(artifact, "provenance", _validate_evidence_source, contract_name)
    _require_action_receipt_provenance(artifact)
    return {
        "schema": "paideia-agent-v2-contract-validation/v1",
        "contract_name": contract_name,
        "evidence_id": artifact.get("evidence_id"),
        "accepted": True,
    }


def _require_action_receipt_provenance(artifact: dict[str, Any]) -> None:
    refs = [str(ref) for ref in artifact.get("action_receipt_refs") or [] if str(ref)]
    if not refs:
        return
    proven_refs = {
        row.get("source_id")
        for row in artifact.get("provenance") or []
        if isinstance(row, dict)
        and row.get("source_type") == "action_receipt"
        and isinstance(row.get("artifact_hash"), str)
        and bool(row.get("artifact_hash"))
    }
    missing = sorted(set(refs) - proven_refs)
    if missing:
        raise ValueError(f"outcome_evidence action receipt provenance mismatch: {', '.join(missing)}")


def validate_attribution_report_v2(artifact: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    contract_name = validate_v2_contract_header(artifact, manifest)
    if contract_name != "attribution_report":
        raise ValueError(f"Expected attribution_report contract, got {contract_name}")
    _require_fields(artifact, ATTRIBUTION_REPORT_REQUIRED_FIELDS, contract_name)
    _require_top_level_no_extra(artifact, ATTRIBUTION_REPORT_ALLOWED_FIELDS, contract_name)
    _require_field_types(artifact, ATTRIBUTION_REPORT_FIELD_RULES, contract_name)
    _validate_object_list(artifact, "step_credits", _validate_step_credit, contract_name)
    return {
        "schema": "paideia-agent-v2-contract-validation/v1",
        "contract_name": contract_name,
        "report_id": artifact.get("report_id"),
        "accepted": True,
    }


def validate_pattern_revision_v2(artifact: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    contract_name = validate_v2_contract_header(artifact, manifest)
    if contract_name != "pattern_revision":
        raise ValueError(f"Expected pattern_revision contract, got {contract_name}")
    _require_fields(artifact, PATTERN_REVISION_REQUIRED_FIELDS, contract_name)
    _require_top_level_no_extra(artifact, PATTERN_REVISION_ALLOWED_FIELDS, contract_name)
    _require_field_types(artifact, PATTERN_REVISION_FIELD_RULES, contract_name)
    if artifact["status"] not in PATTERN_REVISION_STATUSES:
        raise ValueError(f"Unsupported pattern revision status: {artifact['status']}")
    if not all(isinstance(item, dict) for item in artifact["proposed_changes"]):
        raise ValueError("pattern_revision has invalid field types: proposed_changes")
    return {
        "schema": "paideia-agent-v2-contract-validation/v1",
        "contract_name": contract_name,
        "revision_id": artifact.get("revision_id"),
        "accepted": True,
    }


def adapt_legacy_pattern_exam(exam: PatternExamResult) -> dict[str, Any]:
    return {
        "schema": "paideia-agent-legacy-evidence-adapter/v1",
        "source_schema": "paideia-pattern-exam-result/v1",
        "evidence_kind": "structural_exam",
        "pattern_id": exam.pattern_id,
        "task_id": exam.task_id,
        "score": round(float(exam.score), 4),
        "passed": bool(exam.passed),
        "behavioral_validation_credit": False,
        "strong_reuse_credit": False,
        "warnings": ["legacy_pattern_exam_is_structural_only"],
    }


def adapt_legacy_real_world_outcome(outcome: RealWorldOutcome) -> dict[str, Any]:
    has_verifier_hint = any("verifier:" in note.casefold() for note in outcome.notes)
    weight_cap = 0.25 if not has_verifier_hint else 0.5
    return {
        "schema": "paideia-agent-legacy-evidence-adapter/v1",
        "source_schema": "paideia-real-world-outcome/v1",
        "evidence_kind": "legacy_outcome",
        "pattern_id": outcome.pattern_id,
        "task_id": outcome.task_id,
        "success": bool(outcome.success),
        "quantitative_result": outcome.quantitative_result,
        "user_feedback_score": outcome.user_feedback_score,
        "max_evidence_weight": weight_cap,
        "field_validation_credit": False,
        "warnings": ["legacy_outcome_requires_v2_provenance_for_field_validation"],
    }
