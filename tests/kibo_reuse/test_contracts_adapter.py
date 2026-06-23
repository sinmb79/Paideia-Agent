import pytest
import json
from pathlib import Path

from ai22b.kibo_reuse.contracts_adapter import (
    adapt_legacy_pattern_exam,
    adapt_legacy_real_world_outcome,
    validate_action_pattern_v2,
    validate_outcome_evidence_v2,
    validation_profile_reuse_ceiling,
)
from ai22b.kibo_reuse.models import PatternExamResult, RealWorldOutcome
from ai22b.kibo_reuse.schema_compat import validate_v2_artifacts, validate_v2_contract_header


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def _manifest():
    return {
        "schema": "paideia-cross-repo-compatibility/v1",
        "contracts_release": "2.0.0",
        "paideia_agent": ">=0.x,<1.0",
        "paideia_engines": ">=0.x,<1.0",
        "genius_derivation": ">=0.x,<1.0",
        "contract_hashes": {
            "action_pattern": "a" * 64,
            "validation_profile": "b" * 64,
            "outcome_evidence": "c" * 64,
        },
    }


def _action_pattern():
    return {
        "schema": "paideia-kibo-v2-action-pattern/v2",
        "schema_version": "2.0.0",
        "contract_hash": "a" * 64,
        "pattern_id": "pattern-1",
        "pattern_version": "1.0.0",
        "parent_pattern_version": None,
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_family": "implementation",
        "goal_template": "Implement {feature} with tests.",
        "input_slots": [],
        "preconditions": [],
        "required_observations": [],
        "steps": [],
        "transitions": [],
        "invariants": [],
        "abort_conditions": [],
        "recovery_actions": [],
        "success_conditions": [],
        "forbidden_contexts": [],
        "required_capabilities": ["code_inspection", "test_execution"],
        "source_case_ids": ["case-1"],
        "validation_profile_id": None,
        "lifecycle_status": "draft",
    }


def _valid_action_node():
    return {
        "node_id": "inspect",
        "action_type": "inspect",
        "capability": "code_inspection",
        "input_bindings": {"repo": "context.repo"},
        "expected_effects": [{"predicate_id": "effect-1", "op": "exists", "field": "plan", "value": True}],
        "timeout_ms": 1000,
        "retry_policy": {"max_attempts": 1, "backoff_ms": 0},
        "on_success": "test",
        "on_failure": None,
        "on_uncertain": None,
        "human_review_required": False,
    }


def _validation_profile(**overrides):
    data = {
        "schema": "paideia-kibo-v2-validation-profile/v2",
        "schema_version": "2.0.0",
        "contract_hash": "b" * 64,
        "profile_id": "validation-1",
        "pattern_id": "pattern-1",
        "pattern_version": "1.0.0",
        "structural_exam_passed": True,
        "behavioral_exam_passed": False,
        "near_transfer_passed": False,
        "far_transfer_passed": False,
        "adversarial_exam_passed": False,
        "shadow_validation_passed": False,
        "field_validation_passed": False,
        "critic_clearance_passed": False,
        "evidence_fresh_until": None,
        "high_risk_eligible": False,
        "evidence_refs": ["exam-1"],
    }
    data.update(overrides)
    return data


def _outcome_evidence(**overrides):
    data = {
        "schema": "paideia-kibo-v2-outcome-evidence/v2",
        "schema_version": "2.0.0",
        "contract_hash": "c" * 64,
        "evidence_id": "outcome-1",
        "pattern_id": "pattern-1",
        "pattern_version": "1.0.0",
        "task_id": "task-1",
        "run_id": "run-1",
        "environment_fingerprint": "env-1",
        "task_difficulty": 0.6,
        "started_at": "2026-06-23T00:00:00Z",
        "observed_at": "2026-06-23T00:00:01Z",
        "outcome_latency_seconds": 1.0,
        "technical_score": 0.9,
        "safety_score": 1.0,
        "user_utility_score": None,
        "binary_success": True,
        "baseline_ref": "baseline-1",
        "verifier_type": "independent_test",
        "verifier_id": "pytest",
        "provenance": [{"source_id": "receipt-1", "source_type": "action_receipt", "confidence": 1.0, "artifact_hash": "hash-receipt"}],
        "action_receipt_refs": ["receipt-1"],
        "artifact_hashes": ["hash-artifact"],
        "confidence": 0.9,
        "status": "verified",
    }
    data.update(overrides)
    return data


def test_agent_adapter_validates_action_pattern_header_without_engine_import():
    result = validate_action_pattern_v2(_action_pattern(), _manifest())

    assert result["accepted"] is True
    assert result["contract_name"] == "action_pattern"


def test_agent_bulk_validator_uses_payload_validators():
    assert validate_v2_artifacts([_action_pattern(), _validation_profile(), _outcome_evidence()], _manifest()) == [
        "action_pattern",
        "validation_profile",
        "outcome_evidence",
    ]


def test_agent_bulk_validator_fails_closed_on_malformed_payload():
    artifact = _action_pattern()
    artifact["steps"] = [{"junk": True}]

    with pytest.raises(ValueError, match="invalid nested payload"):
        validate_v2_artifacts([artifact], _manifest())


def test_agent_adapter_consumes_engine_generated_manifest_when_available():
    manifest_path = WORKSPACE_ROOT / "22b-paideia-engines" / "docs" / "cross_repo_compatibility_manifest.json"
    if not manifest_path.exists():
        pytest.skip("Engine manifest fixture is available only in the multi-repo workspace")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = _action_pattern()
    artifact["contract_hash"] = manifest["contract_hashes"]["action_pattern"]

    assert validate_action_pattern_v2(artifact, manifest)["accepted"] is True


def test_agent_adapter_fails_closed_on_hash_mismatch():
    artifact = _action_pattern()
    artifact["contract_hash"] = "0" * 64

    with pytest.raises(ValueError, match="Contract hash mismatch"):
        validate_v2_contract_header(artifact, _manifest())


def test_agent_adapter_fails_closed_on_major_version_mismatch():
    artifact = _action_pattern()
    artifact["schema_version"] = "3.0.0"

    with pytest.raises(ValueError, match="Unsupported schema_version"):
        validate_v2_contract_header(artifact, _manifest())


def test_agent_adapter_fails_closed_on_non_string_schema_version():
    artifact = _action_pattern()
    artifact["schema_version"] = 2.0

    with pytest.raises(ValueError, match="Unsupported schema_version"):
        validate_v2_contract_header(artifact, _manifest())


def test_agent_adapter_fails_closed_on_non_string_manifest_hash():
    manifest = _manifest()
    artifact = _action_pattern()
    manifest["contract_hashes"]["action_pattern"] = 123
    artifact["contract_hash"] = 123

    with pytest.raises(ValueError, match="invalid contract hashes"):
        validate_v2_contract_header(artifact, manifest)


def test_agent_adapter_fails_closed_on_missing_required_payload():
    artifact = _action_pattern()
    del artifact["pattern_id"]

    with pytest.raises(ValueError, match="missing required fields"):
        validate_action_pattern_v2(artifact, _manifest())


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("pattern_id", None),
        ("pattern_version", {}),
        ("input_slots", "not-list"),
        ("required_capabilities", "not-list"),
    ],
)
def test_agent_adapter_fails_closed_on_malformed_action_pattern_payload(field_name, bad_value):
    artifact = _action_pattern()
    artifact[field_name] = bad_value

    with pytest.raises(ValueError, match="invalid field types"):
        validate_action_pattern_v2(artifact, _manifest())


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("steps", [{"junk": True}]),
        ("input_slots", [{"slot_id": "feature"}]),
        ("preconditions", [{"predicate_id": "pre-1", "op": "exists", "field": "repo", "value": True, "junk": True}]),
    ],
)
def test_agent_adapter_fails_closed_on_malformed_nested_action_pattern_payload(field_name, bad_value):
    artifact = _action_pattern()
    artifact[field_name] = bad_value

    with pytest.raises(ValueError, match="invalid nested payload"):
        validate_action_pattern_v2(artifact, _manifest())


def test_agent_adapter_fails_closed_on_nullable_retry_backoff():
    artifact = _action_pattern()
    node = _valid_action_node()
    node["retry_policy"]["backoff_ms"] = None
    artifact["steps"] = [node]

    with pytest.raises(ValueError, match="invalid nested payload"):
        validate_action_pattern_v2(artifact, _manifest())


def test_agent_adapter_fails_closed_on_unknown_lifecycle_status():
    artifact = _action_pattern()
    artifact["lifecycle_status"] = "not-a-valid-status"

    with pytest.raises(ValueError, match="Unsupported lifecycle_status"):
        validate_action_pattern_v2(artifact, _manifest())


def test_agent_adapter_fails_closed_on_extra_top_level_action_pattern_field():
    artifact = _action_pattern()
    artifact["extra"] = True

    with pytest.raises(ValueError, match="unexpected fields"):
        validate_action_pattern_v2(artifact, _manifest())


def test_validation_profile_maps_structural_only_to_reference_only():
    assert validation_profile_reuse_ceiling(_validation_profile(), _manifest()) == "reference_only"


def test_validation_profile_fails_closed_on_missing_required_payload():
    profile = _validation_profile()
    del profile["evidence_refs"]

    with pytest.raises(ValueError, match="missing required fields"):
        validation_profile_reuse_ceiling(profile, _manifest())


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("behavioral_exam_passed", "yes"),
        ("evidence_refs", "exam-1"),
        ("pattern_version", {}),
    ],
)
def test_validation_profile_fails_closed_on_malformed_payload(field_name, bad_value):
    profile = _validation_profile()
    profile[field_name] = bad_value

    with pytest.raises(ValueError, match="invalid field types"):
        validation_profile_reuse_ceiling(profile, _manifest())


def test_validation_profile_fails_closed_on_extra_top_level_field():
    profile = _validation_profile()
    profile["extra"] = True

    with pytest.raises(ValueError, match="unexpected fields"):
        validation_profile_reuse_ceiling(profile, _manifest())


def test_validation_profile_requires_behavioral_and_field_evidence_for_strong_reuse():
    profile = _validation_profile(
        behavioral_exam_passed=True,
        near_transfer_passed=True,
        far_transfer_passed=True,
        adversarial_exam_passed=True,
        shadow_validation_passed=True,
        field_validation_passed=True,
        critic_clearance_passed=True,
        high_risk_eligible=True,
    )

    assert validation_profile_reuse_ceiling(profile, _manifest()) == "strong_reuse"


def test_validation_profile_requires_shadow_validation_for_strong_reuse():
    profile = _validation_profile(
        behavioral_exam_passed=True,
        near_transfer_passed=True,
        far_transfer_passed=True,
        adversarial_exam_passed=True,
        shadow_validation_passed=False,
        field_validation_passed=True,
        critic_clearance_passed=True,
        high_risk_eligible=True,
    )

    assert validation_profile_reuse_ceiling(profile, _manifest()) == "partial_reuse"


def test_validation_profile_requires_near_transfer_for_strong_reuse():
    profile = _validation_profile(
        behavioral_exam_passed=True,
        near_transfer_passed=False,
        far_transfer_passed=True,
        adversarial_exam_passed=True,
        shadow_validation_passed=True,
        field_validation_passed=True,
        critic_clearance_passed=True,
        high_risk_eligible=True,
    )

    assert validation_profile_reuse_ceiling(profile, _manifest()) == "reference_only"


def test_outcome_evidence_payload_validator_requires_full_canonical_fields():
    assert validate_outcome_evidence_v2(_outcome_evidence(), _manifest())["accepted"] is True
    stub = {
        "schema": "paideia-kibo-v2-outcome-evidence/v2",
        "schema_version": "2.0.0",
        "contract_hash": "c" * 64,
        "evidence_id": "outcome-1",
        "pattern_id": "pattern-1",
        "pattern_version": "1.0.0",
        "status": "verified",
        "verifier_type": "independent_test",
    }

    with pytest.raises(ValueError, match="missing required fields"):
        validate_outcome_evidence_v2(stub, _manifest())


def test_outcome_evidence_payload_validator_requires_receipt_provenance():
    payload = _outcome_evidence()
    payload["action_receipt_refs"] = ["fake-receipt"]
    payload["provenance"] = []

    with pytest.raises(ValueError, match="action receipt provenance mismatch"):
        validate_outcome_evidence_v2(payload, _manifest())


def test_legacy_pattern_exam_is_structural_evidence_only():
    adapted = adapt_legacy_pattern_exam(
        PatternExamResult("exam-1", "pattern-1", "task-1", 0.95, True, (), ())
    )

    assert adapted["evidence_kind"] == "structural_exam"
    assert adapted["behavioral_validation_credit"] is False
    assert adapted["strong_reuse_credit"] is False


def test_legacy_real_world_outcome_is_capped_without_v2_provenance():
    adapted = adapt_legacy_real_world_outcome(
        RealWorldOutcome("outcome-1", "pattern-1", "task-1", "now", "task", True, 1.0, None, 10, None, ())
    )

    assert adapted["max_evidence_weight"] == 0.25
    assert adapted["field_validation_credit"] is False
