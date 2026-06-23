import json

import pytest

from ai22b.kibo_reuse.attribution import build_outcome_attribution_report
from ai22b.kibo_reuse.contracts_adapter import validate_attribution_report_v2, validate_pattern_revision_v2
from ai22b.kibo_reuse.outcome_evidence import build_action_receipt, build_outcome_evidence
from ai22b.kibo_reuse.pattern_revision import build_pattern_revision_proposal


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
            "attribution_report": "r" * 64,
            "pattern_revision": "p" * 64,
        },
    }


def _node(node_id, on_success=None):
    return {
        "node_id": node_id,
        "action_type": node_id,
        "capability": f"{node_id}_capability",
        "input_bindings": {"repo": "context.repo"},
        "expected_effects": [{"predicate_id": f"effect-{node_id}", "op": "exists", "field": f"{node_id}.result", "value": True}],
        "timeout_ms": 1000,
        "retry_policy": {"max_attempts": 1, "backoff_ms": 0},
        "on_success": on_success,
        "on_failure": None,
        "on_uncertain": None,
        "human_review_required": False,
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
        "goal_template": "Solve {task}.",
        "input_slots": [],
        "preconditions": [],
        "required_observations": [],
        "steps": [_node("inspect", "test"), _node("test")],
        "transitions": [{"from_node_id": "inspect", "to_node_id": "test", "condition": None}],
        "invariants": [],
        "abort_conditions": [],
        "recovery_actions": [],
        "success_conditions": [],
        "forbidden_contexts": [],
        "required_capabilities": ["inspect_capability", "test_capability"],
        "source_case_ids": ["case-1", "case-2", "case-3"],
        "validation_profile_id": None,
        "lifecycle_status": "draft",
    }


def _receipt(node_id, *, status="succeeded"):
    return build_action_receipt(
        run_id="run-1",
        pattern_id="pattern-1",
        pattern_version="1.0.0",
        action_node_id=node_id,
        capability=f"{node_id}_capability",
        requested_inputs={"repo": "."},
        started_at=f"2026-06-23T00:00:0{0 if node_id == 'inspect' else 1}Z",
        completed_at=f"2026-06-23T00:00:0{1 if node_id == 'inspect' else 2}Z",
        result_status=status,
        observed_effects=({"predicate_id": f"effect-{node_id}", "passed": status == "succeeded"},),
        artifact_hashes=(f"hash-{node_id}",),
    )


def _outcome(action_pattern, receipts, *, success=True):
    return build_outcome_evidence(
        action_pattern,
        _manifest(),
        task_id="task-1",
        action_receipts=receipts,
        verifier_report={
            "schema": "paideia-verifier-report/v1",
            "verifier_type": "independent_test",
            "verifier_id": "pytest",
            "technical_score": 1.0 if success else 0.2,
            "safety_score": 1.0,
            "binary_success": success,
            "confidence": 0.9,
            "observed_at": "2026-06-23T00:00:03Z",
        },
        environment_fingerprint="env-1",
        baseline_ref="baseline-1",
    )


def test_attribution_assigns_negative_credit_to_failed_step():
    action_pattern = _action_pattern()
    receipts = [_receipt("inspect", status="failed"), _receipt("test")]
    outcome = _outcome(action_pattern, receipts, success=False)
    report = build_outcome_attribution_report(action_pattern, outcome, _manifest(), action_receipts=receipts)

    failed_credit = next(credit for credit in report["step_credits"] if credit["step_id"] == "inspect")
    assert failed_credit["contribution_score"] < 0
    assert "receipt_failed" in failed_credit["reason_codes"]
    assert validate_attribution_report_v2(report, _manifest())["accepted"] is True


def test_attribution_rejects_receipts_from_other_pattern_or_unreferenced_receipts():
    action_pattern = _action_pattern()
    receipts = [_receipt("inspect")]
    outcome = _outcome(action_pattern, receipts)
    foreign = _receipt("inspect")
    foreign["pattern_version"] = "9.9.9"

    for bad_receipt in (foreign, _receipt("test")):
        with pytest.raises(ValueError, match="Action receipt"):
            build_outcome_attribution_report(action_pattern, outcome, _manifest(), action_receipts=[bad_receipt])


def test_attribution_rejects_malformed_referenced_action_receipt():
    action_pattern = _action_pattern()
    receipts = [_receipt("inspect")]
    outcome = _outcome(action_pattern, receipts)
    malformed = dict(receipts[0])
    del malformed["result_status"]

    with pytest.raises(ValueError, match="ActionReceipt missing required fields"):
        build_outcome_attribution_report(action_pattern, outcome, _manifest(), action_receipts=[malformed])


def test_attribution_requires_verified_observed_outcome():
    action_pattern = _action_pattern()
    receipts = [_receipt("inspect"), _receipt("test")]
    outcome = _outcome(action_pattern, receipts)
    outcome["status"] = "pending"

    with pytest.raises(ValueError, match="verified"):
        build_outcome_attribution_report(action_pattern, outcome, _manifest(), action_receipts=receipts)


def test_pattern_revision_from_negative_credit_is_quarantined_and_requires_retest():
    action_pattern = _action_pattern()
    receipts = [_receipt("inspect", status="failed"), _receipt("test")]
    outcome = _outcome(action_pattern, receipts, success=False)
    report = build_outcome_attribution_report(action_pattern, outcome, _manifest(), action_receipts=receipts)
    proposal = build_pattern_revision_proposal(action_pattern, [report], _manifest())

    assert proposal["status"] == "quarantined"
    assert proposal["from_pattern_version"] == "1.0.0"
    assert proposal["proposed_pattern_version"] == "1.0.1"
    assert proposal["requires_behavioral_exam"] is True
    assert proposal["requires_shadow_validation"] is True
    assert proposal["proposed_changes"][0]["node_id"] == "inspect"
    assert validate_pattern_revision_v2(proposal, _manifest())["accepted"] is True


def test_pattern_revision_rejects_negative_step_credit_for_unknown_node():
    action_pattern = _action_pattern()
    receipts = [_receipt("inspect", status="failed"), _receipt("test")]
    outcome = _outcome(action_pattern, receipts, success=False)
    report = build_outcome_attribution_report(action_pattern, outcome, _manifest(), action_receipts=receipts)
    report["step_credits"][0]["step_id"] = "unknown-node"

    with pytest.raises(ValueError, match="unknown ActionPattern nodes"):
        build_pattern_revision_proposal(action_pattern, [report], _manifest())


def test_pattern_revision_without_negative_credit_stays_draft():
    action_pattern = _action_pattern()
    receipts = [_receipt("inspect"), _receipt("test")]
    outcome = _outcome(action_pattern, receipts)
    report = build_outcome_attribution_report(action_pattern, outcome, _manifest(), action_receipts=receipts)
    proposal = build_pattern_revision_proposal(action_pattern, [report], _manifest())

    assert proposal["status"] == "draft"
    assert proposal["proposed_changes"] == []


def test_attribution_and_revision_cli_round_trip(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    manifest_path = tmp_path / "manifest.json"
    pattern_path = tmp_path / "pattern.json"
    outcome_path = tmp_path / "outcome.json"
    receipt_path = tmp_path / "receipts.json"
    attribution_path = tmp_path / "attribution.json"
    revision_path = tmp_path / "revision.json"
    action_pattern = _action_pattern()
    receipts = [_receipt("inspect", status="failed"), _receipt("test")]
    outcome = _outcome(action_pattern, receipts, success=False)
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    pattern_path.write_text(json.dumps(action_pattern), encoding="utf-8")
    outcome_path.write_text(json.dumps({"outcome_evidence": outcome}), encoding="utf-8")
    receipt_path.write_text(json.dumps({"action_receipts": receipts}), encoding="utf-8")

    attribute_code = cli_main(
        [
            "outcome-attribute",
            "--pattern-path",
            str(pattern_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--outcome-path",
            str(outcome_path),
            "--action-receipt",
            str(receipt_path),
            "--output",
            str(attribution_path),
        ]
    )
    revision_code = cli_main(
        [
            "pattern-revision-propose",
            "--pattern-path",
            str(pattern_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--attribution-path",
            str(attribution_path),
            "--output",
            str(revision_path),
        ]
    )
    attribution = json.loads(attribution_path.read_text(encoding="utf-8"))
    revision = json.loads(revision_path.read_text(encoding="utf-8"))

    assert attribute_code == 0
    assert revision_code == 0
    assert attribution["negative_step_count"] == 1
    assert revision["pattern_revision"]["status"] == "quarantined"
