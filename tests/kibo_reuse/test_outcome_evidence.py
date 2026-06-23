import json

import pytest

from ai22b.kibo_reuse.contracts_adapter import validate_outcome_evidence_v2
from ai22b.kibo_reuse.outcome_evidence import build_action_receipt, build_outcome_evidence, build_outcome_ingest_report


def _manifest():
    return {
        "schema": "paideia-cross-repo-compatibility/v1",
        "contracts_release": "2.0.0",
        "paideia_agent": ">=0.x,<1.0",
        "paideia_engines": ">=0.x,<1.0",
        "genius_derivation": ">=0.x,<1.0",
        "contract_hashes": {
            "action_pattern": "a" * 64,
            "outcome_evidence": "o" * 64,
        },
    }


def _action_pattern():
    return {
        "schema": "paideia-kibo-v2-action-pattern/v2",
        "schema_version": "2.0.0",
        "contract_hash": "a" * 64,
        "pattern_id": "pattern-1",
        "pattern_version": "0.1.0",
        "parent_pattern_version": None,
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_family": "implementation",
        "goal_template": "Solve {task}.",
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
        "required_capabilities": [],
        "source_case_ids": ["case-1", "case-2", "case-3"],
        "validation_profile_id": None,
        "lifecycle_status": "draft",
    }


def _receipt(**overrides):
    receipt = build_action_receipt(
        run_id="run-1",
        pattern_id="pattern-1",
        pattern_version="0.1.0",
        action_node_id="inspect",
        capability="code_inspection",
        requested_inputs={"repo": "."},
        started_at="2026-06-23T00:00:00Z",
        completed_at="2026-06-23T00:00:01Z",
        result_status="succeeded",
        observed_effects=({"predicate_id": "effect-1", "passed": True},),
        artifact_hashes=("hash-output",),
    )
    receipt.update(overrides)
    return receipt


def _verifier(**overrides):
    report = {
        "schema": "paideia-verifier-report/v1",
        "verifier_type": "independent_test",
        "verifier_id": "pytest",
        "technical_score": 1.0,
        "safety_score": 1.0,
        "user_utility_score": None,
        "binary_success": True,
        "confidence": 0.95,
        "observed_at": "2026-06-23T00:00:02Z",
        "artifact_hashes": ["hash-verifier"],
    }
    report.update(overrides)
    return report


def test_action_receipt_builder_emits_reviewable_receipt_with_artifact_hashes():
    receipt = _receipt()

    assert receipt["schema"] == "paideia-kibo-action-receipt/v1"
    assert receipt["receipt_id"].startswith("action-receipt-")
    assert receipt["requested_inputs_hash"].startswith("sha256:")
    assert receipt["artifact_hashes"] == ["hash-output"]


def test_outcome_evidence_requires_independent_verifier_and_receipt_for_verified_status():
    evidence = build_outcome_evidence(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt()],
        verifier_report=_verifier(),
        environment_fingerprint="env-1",
        task_difficulty=0.7,
        baseline_ref="baseline-1",
    )

    assert evidence["schema"] == "paideia-kibo-v2-outcome-evidence/v2"
    assert evidence["status"] == "verified"
    assert evidence["action_receipt_refs"]
    assert evidence["confidence"] == 0.95
    assert validate_outcome_evidence_v2(evidence, _manifest())["accepted"] is True


def test_manual_verifier_claim_is_capped_to_pending_evidence():
    report = build_outcome_ingest_report(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt()],
        verifier_report=_verifier(verifier_type="manual", status="verified", confidence=1.0),
    )

    assert report["status"] == "pending"
    assert report["field_validation_candidate"] is False
    assert report["outcome_evidence"]["confidence"] <= 0.25


def test_explicit_pending_status_is_not_auto_verified():
    report = build_outcome_ingest_report(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt()],
        verifier_report=_verifier(status="pending"),
    )

    assert report["status"] == "pending"
    assert report["field_validation_candidate"] is False


def test_failed_binary_outcome_is_verified_evidence_but_not_field_candidate():
    report = build_outcome_ingest_report(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt()],
        verifier_report=_verifier(binary_success=False),
    )

    assert report["status"] == "verified"
    assert report["field_validation_candidate"] is False
    assert report["outcome_evidence"]["binary_success"] is False


def test_string_false_binary_success_is_not_coerced_to_true():
    report = build_outcome_ingest_report(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt()],
        verifier_report=_verifier(binary_success="false"),
    )

    assert report["status"] == "verified"
    assert report["field_validation_candidate"] is False
    assert report["outcome_evidence"]["binary_success"] is False


def test_invalid_binary_success_string_fails_closed():
    with pytest.raises(ValueError, match="binary_success must be a boolean"):
        build_outcome_ingest_report(
            _action_pattern(),
            _manifest(),
            task_id="task-1",
            action_receipts=[_receipt()],
            verifier_report=_verifier(binary_success="definitely"),
        )


def test_failed_receipt_without_failure_verdict_is_pending_not_field_candidate():
    report = build_outcome_ingest_report(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt(result_status="failed")],
        verifier_report=_verifier(binary_success=True),
    )

    assert report["status"] == "pending"
    assert report["field_validation_candidate"] is False


def test_low_safety_outcome_is_not_field_candidate():
    report = build_outcome_ingest_report(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt()],
        verifier_report=_verifier(safety_score=0.4),
    )

    assert report["status"] == "verified"
    assert report["field_validation_candidate"] is False


def test_missing_safety_score_is_not_field_candidate():
    report = build_outcome_ingest_report(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt()],
        verifier_report=_verifier(safety_score=None),
    )

    assert report["status"] == "verified"
    assert report["field_validation_candidate"] is False


def test_nan_safety_score_fails_closed():
    with pytest.raises(ValueError, match="score values must be finite"):
        build_outcome_ingest_report(
            _action_pattern(),
            _manifest(),
            task_id="task-1",
            action_receipts=[_receipt()],
            verifier_report=_verifier(safety_score=float("nan")),
        )


def test_outcome_evidence_rejects_receipt_pattern_version_mismatch():
    receipt = _receipt(pattern_version="0.2.0")

    with pytest.raises(ValueError, match="pattern_version mismatch"):
        build_outcome_evidence(
            _action_pattern(),
            _manifest(),
            task_id="task-1",
            action_receipts=[receipt],
            verifier_report=_verifier(),
        )


def test_contested_verifier_report_does_not_create_verified_field_candidate():
    report = build_outcome_ingest_report(
        _action_pattern(),
        _manifest(),
        task_id="task-1",
        action_receipts=[_receipt()],
        verifier_report=_verifier(status="contested"),
    )

    assert report["status"] == "contested"
    assert report["field_validation_candidate"] is False


def test_outcome_ingest_cli_round_trip(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    manifest_path = tmp_path / "manifest.json"
    pattern_path = tmp_path / "pattern.json"
    receipt_path = tmp_path / "receipt.json"
    verifier_path = tmp_path / "verifier.json"
    output_path = tmp_path / "outcome.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    pattern_path.write_text(json.dumps(_action_pattern()), encoding="utf-8")
    verifier_path.write_text(json.dumps(_verifier()), encoding="utf-8")
    receipt_path.write_text(json.dumps({"schema": "paideia-action-receipt-build-result/v1", "action_receipt": _receipt()}), encoding="utf-8")

    code = cli_main(
        [
            "outcome-ingest",
            "--pattern-path",
            str(pattern_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--task-id",
            "task-1",
            "--action-receipt",
            str(receipt_path),
            "--verifier-report",
            str(verifier_path),
            "--environment-fingerprint",
            "env-1",
            "--task-difficulty",
            "0.7",
            "--baseline-ref",
            "baseline-1",
            "--output",
            str(output_path),
        ]
    )
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert code == 0
    assert report["status"] == "verified"
    assert report["outcome_evidence"]["schema"] == "paideia-kibo-v2-outcome-evidence/v2"
