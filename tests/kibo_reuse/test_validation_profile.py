import json

import pytest

from ai22b.kibo_reuse import build_validation_profile_report as exported_build_validation_profile_report
from ai22b.kibo_reuse.contracts_adapter import validation_profile_reuse_ceiling
from ai22b.kibo_reuse.validation_profile import build_pattern_validation_profile, runtime_gate_reuse_mode


def _manifest():
    return {
        "schema": "paideia-cross-repo-compatibility/v1",
        "contracts_release": "2.0.0",
        "paideia_agent": ">=0.x,<1.0",
        "paideia_engines": ">=0.x,<1.0",
        "genius_derivation": ">=0.x,<1.0",
        "contract_hashes": {
            "action_pattern": "a" * 64,
            "behavioral_exam": "b" * 64,
            "validation_profile": "v" * 64,
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


def _behavioral_exam(*, passed=True, leakage=False):
    return {
        "schema": "paideia-kibo-v2-behavioral-exam/v2",
        "schema_version": "2.0.0",
        "contract_hash": "b" * 64,
        "exam_id": "behavioral-1",
        "pattern_id": "pattern-1",
        "pattern_version": "0.1.0",
        "scenario_pack_id": "pack-1",
        "scenario_results": [
            {"scenario_id": "near-1", "scenario_kind": "near_transfer", "task_success": True, "invariant_passed": True, "abstained": False, "safety_violations": [], "trace_hash": "hash-near"},
            {"scenario_id": "far-1", "scenario_kind": "far_transfer", "task_success": True, "invariant_passed": True, "abstained": False, "safety_violations": [], "trace_hash": "hash-far"},
            {"scenario_id": "counter-1", "scenario_kind": "counterexample", "task_success": True, "invariant_passed": True, "abstained": False, "safety_violations": [], "trace_hash": "hash-counter"},
            {"scenario_id": "safety-1", "scenario_kind": "safety_boundary", "task_success": True, "invariant_passed": True, "abstained": False, "safety_violations": [], "trace_hash": "hash-safety"},
        ],
        "task_success_rate": 1.0,
        "invariant_pass_rate": 1.0,
        "transfer_score": 1.0,
        "abstention_precision": 1.0,
        "efficiency_score": 1.0,
        "safety_violation_count": 0,
        "leakage_detected": leakage,
        "passed": passed,
        "evidence_hashes": ["hash"],
    }


def _field_evidence(*, verifier_type="independent_test"):
    return {
        "schema": "paideia-kibo-v2-outcome-evidence/v2",
        "schema_version": "2.0.0",
        "contract_hash": "o" * 64,
        "evidence_id": "outcome-1",
        "pattern_id": "pattern-1",
        "pattern_version": "0.1.0",
        "task_id": "task-1",
        "run_id": "run-1",
        "environment_fingerprint": "env-1",
        "task_difficulty": 0.7,
        "started_at": "2026-06-23T00:00:00Z",
        "observed_at": "2026-06-23T00:00:01Z",
        "outcome_latency_seconds": 1.0,
        "technical_score": 1.0,
        "safety_score": 1.0,
        "user_utility_score": None,
        "binary_success": True,
        "baseline_ref": "baseline-1",
        "verifier_type": verifier_type,
        "verifier_id": "pytest",
        "provenance": [{"source_id": "receipt-1", "source_type": "action_receipt", "confidence": 1.0, "artifact_hash": "hash-receipt"}],
        "action_receipt_refs": ["receipt-1"],
        "artifact_hashes": ["hash-artifact"],
        "confidence": 0.95,
        "status": "verified",
    }


def test_structural_exam_only_builds_reference_only_profile():
    profile = build_pattern_validation_profile(
        _action_pattern(),
        _manifest(),
        structural_exam={"schema": "paideia-pattern-exam-result/v1", "exam_id": "structural-1", "passed": True},
    )

    assert profile["structural_exam_passed"] is True
    assert profile["behavioral_exam_passed"] is False
    assert validation_profile_reuse_ceiling(profile, _manifest()) == "reference_only"


def test_behavioral_without_field_evidence_is_partial_reuse_only():
    profile = build_pattern_validation_profile(_action_pattern(), _manifest(), behavioral_exam=_behavioral_exam())

    assert profile["behavioral_exam_passed"] is True
    assert profile["near_transfer_passed"] is True
    assert profile["far_transfer_passed"] is True
    assert profile["adversarial_exam_passed"] is True
    assert validation_profile_reuse_ceiling(profile, _manifest()) == "partial_reuse"


def test_field_and_critic_evidence_without_shadow_remains_partial_reuse():
    profile = build_pattern_validation_profile(
        _action_pattern(),
        _manifest(),
        behavioral_exam=_behavioral_exam(),
        critic_report={"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True},
        field_evidence=[_field_evidence()],
    )

    assert profile["field_validation_passed"] is True
    assert profile["critic_clearance_passed"] is True
    assert profile["shadow_validation_passed"] is False
    assert profile["high_risk_eligible"] is False
    assert validation_profile_reuse_ceiling(profile, _manifest()) == "partial_reuse"


def test_field_critic_and_shadow_evidence_enable_strong_reuse_ceiling():
    profile = build_pattern_validation_profile(
        _action_pattern(),
        _manifest(),
        behavioral_exam=_behavioral_exam(),
        critic_report={"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True},
        field_evidence=[_field_evidence()],
        shadow_validation_passed=True,
    )

    assert profile["field_validation_passed"] is True
    assert profile["critic_clearance_passed"] is True
    assert profile["shadow_validation_passed"] is True
    assert profile["high_risk_eligible"] is True
    assert validation_profile_reuse_ceiling(profile, _manifest()) == "strong_reuse"


def test_runtime_gate_downgrades_direct_reuse_without_strong_profile():
    profile = build_pattern_validation_profile(_action_pattern(), _manifest(), behavioral_exam=_behavioral_exam())
    gate = runtime_gate_reuse_mode("direct_reuse", profile, _manifest())

    assert gate["allowed_mode"] == "partial_reuse"
    assert gate["automatic_action_allowed"] is False
    assert any(issue["code"] == "requested_mode_downgraded" for issue in gate["issues"])


def test_runtime_gate_downgrades_strong_request_under_partial_ceiling():
    profile = build_pattern_validation_profile(_action_pattern(), _manifest(), behavioral_exam=_behavioral_exam())
    gate = runtime_gate_reuse_mode("strong_reuse", profile, _manifest())

    assert gate["allowed_mode"] == "partial_reuse"
    assert any(issue["code"] == "requested_mode_downgraded" for issue in gate["issues"])


def test_runtime_gate_rejects_unknown_requested_mode():
    profile = build_pattern_validation_profile(_action_pattern(), _manifest(), behavioral_exam=_behavioral_exam())
    gate = runtime_gate_reuse_mode("automatic_action", profile, _manifest())

    assert gate["allowed_mode"] == "reject_and_solve_fresh"
    assert any(issue["code"] == "unsupported_requested_mode" for issue in gate["issues"])


def test_runtime_gate_downgrades_high_risk_direct_reuse_even_with_strong_profile():
    profile = build_pattern_validation_profile(
        _action_pattern(),
        _manifest(),
        behavioral_exam=_behavioral_exam(),
        critic_report={"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True},
        field_evidence=[_field_evidence()],
        shadow_validation_passed=True,
    )
    gate = runtime_gate_reuse_mode("direct_reuse", profile, _manifest(), risk_level="high")

    assert gate["reuse_ceiling"] == "strong_reuse"
    assert gate["allowed_mode"] == "partial_reuse"


def test_behavioral_exam_mismatch_fails_closed():
    exam = _behavioral_exam()
    exam["pattern_version"] = "0.2.0"

    with pytest.raises(ValueError, match="pattern_version mismatch"):
        build_pattern_validation_profile(_action_pattern(), _manifest(), behavioral_exam=exam)


def test_field_evidence_stub_fails_closed_without_full_outcome_payload():
    stub = {
        "schema": "paideia-kibo-v2-outcome-evidence/v2",
        "schema_version": "2.0.0",
        "contract_hash": "o" * 64,
        "evidence_id": "outcome-1",
        "pattern_id": "pattern-1",
        "pattern_version": "0.1.0",
        "status": "verified",
        "verifier_type": "independent_test",
    }

    with pytest.raises(ValueError, match="missing required fields"):
        build_pattern_validation_profile(
            _action_pattern(),
            _manifest(),
            behavioral_exam=_behavioral_exam(),
            critic_report={"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True},
            field_evidence=[stub],
        )


def test_high_risk_profile_build_requires_independent_field_verifier():
    with pytest.raises(ValueError, match="High-risk validation requires"):
        build_pattern_validation_profile(
            _action_pattern(),
            _manifest(),
            behavioral_exam=_behavioral_exam(),
            critic_report={"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True},
            field_evidence=[_field_evidence(verifier_type="peer_review")],
            shadow_validation_passed=True,
            high_risk=True,
        )


def test_normal_risk_field_validation_rejects_manual_alias_verifier():
    profile = build_pattern_validation_profile(
        _action_pattern(),
        _manifest(),
        behavioral_exam=_behavioral_exam(),
        critic_report={"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True},
        field_evidence=[_field_evidence(verifier_type="user")],
    )

    assert profile["field_validation_passed"] is False
    assert validation_profile_reuse_ceiling(profile, _manifest()) == "partial_reuse"


def test_field_validation_rejects_fake_receipt_ref_without_matching_provenance():
    evidence = _field_evidence()
    evidence["action_receipt_refs"] = ["fake-receipt"]
    evidence["provenance"] = []

    with pytest.raises(ValueError, match="action receipt provenance mismatch"):
        build_pattern_validation_profile(
            _action_pattern(),
            _manifest(),
            behavioral_exam=_behavioral_exam(),
            critic_report={"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True},
            field_evidence=[evidence],
        )


def test_field_validation_rejects_failed_or_low_safety_outcomes():
    failed = _field_evidence()
    failed["binary_success"] = False
    low_safety = _field_evidence()
    low_safety["safety_score"] = 0.5
    missing_safety = _field_evidence()
    missing_safety["safety_score"] = None

    for evidence in (failed, low_safety, missing_safety):
        profile = build_pattern_validation_profile(
            _action_pattern(),
            _manifest(),
            behavioral_exam=_behavioral_exam(),
            critic_report={"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True},
            field_evidence=[evidence],
        )
        assert profile["field_validation_passed"] is False
        assert validation_profile_reuse_ceiling(profile, _manifest()) == "partial_reuse"


def test_validation_profile_and_runtime_gate_cli_round_trip(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    manifest_path = tmp_path / "manifest.json"
    pattern_path = tmp_path / "pattern.json"
    exam_path = tmp_path / "behavioral_exam.json"
    critic_path = tmp_path / "critic.json"
    outcome_path = tmp_path / "outcome.json"
    profile_path = tmp_path / "profile.json"
    gate_path = tmp_path / "gate.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    pattern_path.write_text(json.dumps(_action_pattern()), encoding="utf-8")
    exam_path.write_text(json.dumps(_behavioral_exam()), encoding="utf-8")
    critic_path.write_text(json.dumps({"schema": "paideia-critic-report/v1", "report_id": "critic-1", "pass_gate": True}), encoding="utf-8")
    outcome_path.write_text(json.dumps(_field_evidence()), encoding="utf-8")

    profile_code = cli_main(
        [
            "validation-profile-build",
            "--pattern-path",
            str(pattern_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--behavioral-exam",
            str(exam_path),
            "--critic-report",
            str(critic_path),
            "--field-evidence",
            str(outcome_path),
            "--shadow-validation-passed",
            "--output",
            str(profile_path),
        ]
    )
    gate_code = cli_main(
        [
            "runtime-gate",
            "--validation-profile",
            str(profile_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--requested-mode",
            "direct_reuse",
            "--risk-level",
            "high",
            "--output",
            str(gate_path),
        ]
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    gate = json.loads(gate_path.read_text(encoding="utf-8"))

    assert profile_code == 0
    assert profile["reuse_ceiling"] == "strong_reuse"
    assert gate_code == 2
    assert gate["allowed_mode"] == "partial_reuse"


def test_validation_profile_report_is_exported_for_package_users():
    report = exported_build_validation_profile_report(
        _action_pattern(),
        _manifest(),
        behavioral_exam=_behavioral_exam(),
    )

    assert report["schema"] == "paideia-validation-profile-build-result/v1"
    assert report["reuse_ceiling"] == "partial_reuse"
