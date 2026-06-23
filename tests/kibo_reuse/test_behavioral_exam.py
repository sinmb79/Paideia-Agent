import json

from ai22b.kibo_reuse.behavioral_exam import run_behavioral_exam
from ai22b.kibo_reuse.scenario_pack import build_behavioral_scenario_pack


def _manifest():
    return {
        "schema": "paideia-cross-repo-compatibility/v1",
        "contracts_release": "2.0.0",
        "paideia_agent": ">=0.x,<1.0",
        "paideia_engines": ">=0.x,<1.0",
        "genius_derivation": ">=0.x,<1.0",
        "contract_hashes": {
            "action_pattern": "a" * 64,
            "behavioral_exam": "d" * 64,
        },
    }


def _action_node(node_id: str, capability: str, on_success: str | None = None):
    return {
        "node_id": node_id,
        "action_type": "apply_capability",
        "capability": capability,
        "input_bindings": {"task": "inputs.task"},
        "expected_effects": [{"predicate_id": f"effect-{node_id}", "op": "exists", "field": f"{node_id}.output", "value": True}],
        "timeout_ms": None,
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
        "pattern_version": "0.1.0",
        "parent_pattern_version": None,
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_family": "implementation",
        "goal_template": "Solve {task}.",
        "input_slots": [{"slot_id": "task", "value_type": "string", "required": True}],
        "preconditions": [{"predicate_id": "pre-1", "op": "exists", "field": "task", "value": True}],
        "required_observations": [],
        "steps": [
            _action_node("node-001", "inspect_repository", "node-002"),
            _action_node("node-002", "implement_command", "node-003"),
            _action_node("node-003", "test_execution", None),
        ],
        "transitions": [
            {"from_node_id": "node-001", "to_node_id": "node-002", "condition": None},
            {"from_node_id": "node-002", "to_node_id": "node-003", "condition": None},
        ],
        "invariants": [{"predicate_id": "inv-1", "op": "eq", "field": "hidden_chain_of_thought_reused", "value": False}],
        "abort_conditions": [{"predicate_id": "abort-1", "op": "eq", "field": "safety_boundary", "value": True}],
        "recovery_actions": [],
        "success_conditions": [{"predicate_id": "success-1", "op": "exists", "field": "final_output", "value": True}],
        "forbidden_contexts": [{"predicate_id": "forbidden-1", "op": "eq", "field": "quarantined_source", "value": True}],
        "required_capabilities": ["inspect_repository", "implement_command", "test_execution"],
        "source_case_ids": ["case-1", "case-2", "case-3"],
        "validation_profile_id": None,
        "lifecycle_status": "draft",
    }


def test_behavioral_exam_passes_holdout_transfer_scenarios():
    action_pattern = _action_pattern()
    pack = build_behavioral_scenario_pack(action_pattern)
    result = run_behavioral_exam(action_pattern, pack, _manifest())

    assert pack["schema"] == "paideia-behavioral-scenario-pack/v1"
    assert {scenario["source_partition"] for scenario in pack["scenarios"]} == {"holdout"}
    assert result["schema"] == "paideia-kibo-v2-behavioral-exam/v2"
    assert result["passed"] is True
    assert result["task_success_rate"] == 1.0
    assert result["leakage_detected"] is False
    assert any(item["abstained"] for item in result["scenario_results"])


def test_behavioral_exam_fails_closed_on_source_leakage():
    action_pattern = _action_pattern()
    pack = build_behavioral_scenario_pack(action_pattern, include_leakage=True)
    result = run_behavioral_exam(action_pattern, pack, _manifest())

    assert result["leakage_detected"] is True
    assert result["passed"] is False


def test_behavioral_exam_detects_tool_failure_without_recovery():
    action_pattern = _action_pattern()
    pack = build_behavioral_scenario_pack(action_pattern, scenario_kinds=["tool_failure", "far_transfer"])
    result = run_behavioral_exam(action_pattern, pack, _manifest())

    assert result["passed"] is False
    assert any(not item["task_success"] for item in result["scenario_results"])


def test_behavioral_exam_tool_failure_can_recover_through_recovery_action():
    action_pattern = _action_pattern()
    action_pattern["recovery_actions"] = [
        {
            "recovery_id": "recover-node-003",
            "trigger": {"predicate_id": "tool-failure", "op": "exists", "field": "missing_capability", "value": True},
            "action_node_id": "node-003",
        }
    ]
    pack = build_behavioral_scenario_pack(
        action_pattern,
        scenario_kinds=["near_transfer", "far_transfer", "counterexample", "safety_boundary", "tool_failure", "abstention_required"],
    )
    result = run_behavioral_exam(action_pattern, pack, _manifest())
    tool_failure = next(item for item in result["scenario_results"] if item["scenario_kind"] == "tool_failure")

    assert tool_failure["task_success"] is True
    assert result["passed"] is True


def test_behavioral_exam_requires_near_far_counterexample_and_safety():
    action_pattern = _action_pattern()
    for scenario_kinds in (["near_transfer"], ["far_transfer"], ["near_transfer", "far_transfer"]):
        pack = build_behavioral_scenario_pack(action_pattern, scenario_kinds=scenario_kinds)
        result = run_behavioral_exam(action_pattern, pack, _manifest())

        assert result["passed"] is False


def test_behavioral_exam_counterexample_requires_guard_and_invariant_pass():
    action_pattern = _action_pattern()
    action_pattern["abort_conditions"] = []
    action_pattern["forbidden_contexts"] = []
    pack = build_behavioral_scenario_pack(action_pattern, scenario_kinds=["near_transfer", "far_transfer", "counterexample", "safety_boundary"])
    result = run_behavioral_exam(action_pattern, pack, _manifest())

    assert result["passed"] is False
    assert result["safety_violation_count"] > 0

    guarded = _action_pattern()
    invariant_pack = build_behavioral_scenario_pack(guarded)
    for scenario in invariant_pack["scenarios"]:
        if scenario["scenario_kind"] == "counterexample":
            scenario["hidden_expected_invariants"] = [
                {"predicate_id": "bad-invariant", "op": "always_fail", "field": "impossible", "value": "__fail__"}
            ]
    invariant_result = run_behavioral_exam(guarded, invariant_pack, _manifest())

    assert invariant_result["passed"] is False


def test_behavioral_exam_evaluates_hidden_invariant_predicates_against_initial_state():
    action_pattern = _action_pattern()
    pack = build_behavioral_scenario_pack(action_pattern)
    for scenario in pack["scenarios"]:
        if scenario["scenario_kind"] == "counterexample":
            scenario["initial_state"]["hidden_chain_of_thought_reused"] = True

    result = run_behavioral_exam(action_pattern, pack, _manifest())
    counterexample_result = next(item for item in result["scenario_results"] if item["scenario_kind"] == "counterexample")

    assert counterexample_result["invariant_passed"] is False
    assert result["passed"] is False


def test_behavioral_exam_fails_closed_when_safety_oracle_state_is_missing():
    action_pattern = _action_pattern()
    pack = build_behavioral_scenario_pack(action_pattern)
    for scenario in pack["scenarios"]:
        if scenario["scenario_kind"] == "safety_boundary":
            del scenario["initial_state"]["safety_boundary"]
    result = run_behavioral_exam(action_pattern, pack, _manifest())

    assert result["passed"] is False
    assert result["safety_violation_count"] > 0


def test_behavioral_exam_detects_source_case_id_leakage_in_scenario_payload():
    action_pattern = _action_pattern()
    pack = build_behavioral_scenario_pack(action_pattern)
    pack["scenarios"][0]["initial_state"]["source_case_id"] = "case-1"
    result = run_behavioral_exam(action_pattern, pack, _manifest())

    assert result["leakage_detected"] is True
    assert result["passed"] is False


def test_scenario_pack_generation_is_deterministic():
    action_pattern = _action_pattern()

    assert build_behavioral_scenario_pack(action_pattern) == build_behavioral_scenario_pack(action_pattern)


def test_behavioral_exam_cli_round_trip(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    manifest_path = tmp_path / "manifest.json"
    pattern_path = tmp_path / "pattern.json"
    pack_path = tmp_path / "pack.json"
    exam_path = tmp_path / "exam.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    pattern_path.write_text(json.dumps(_action_pattern()), encoding="utf-8")

    pack_code = cli_main(
        [
            "scenario-pack-build",
            "--pattern-path",
            str(pattern_path),
            "--output",
            str(pack_path),
        ]
    )
    exam_code = cli_main(
        [
            "pattern-behavioral-exam",
            "--pattern-path",
            str(pattern_path),
            "--scenario-pack",
            str(pack_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--output",
            str(exam_path),
        ]
    )
    exam = json.loads(exam_path.read_text(encoding="utf-8"))

    assert pack_code == 0
    assert exam_code == 0
    assert exam["passed"] is True


def test_behavioral_exam_cli_returns_2_when_required_scenarios_are_missing(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    manifest_path = tmp_path / "manifest.json"
    pattern_path = tmp_path / "pattern.json"
    pack_path = tmp_path / "pack.json"
    exam_path = tmp_path / "exam.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    pattern_path.write_text(json.dumps(_action_pattern()), encoding="utf-8")
    pack_path.write_text(
        json.dumps(build_behavioral_scenario_pack(_action_pattern(), scenario_kinds=["near_transfer"])),
        encoding="utf-8",
    )

    exam_code = cli_main(
        [
            "pattern-behavioral-exam",
            "--pattern-path",
            str(pattern_path),
            "--scenario-pack",
            str(pack_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--output",
            str(exam_path),
        ]
    )
    exam = json.loads(exam_path.read_text(encoding="utf-8"))

    assert exam_code == 2
    assert exam["passed"] is False


def test_behavioral_exam_uses_engine_manifest_when_available():
    from pathlib import Path

    workspace_root = Path(__file__).resolve().parents[3]
    manifest_path = workspace_root / "22b-paideia-engines" / "docs" / "cross_repo_compatibility_manifest.json"
    if not manifest_path.exists():
        import pytest

        pytest.skip("Engine manifest fixture is available only in the multi-repo workspace")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    action_pattern = _action_pattern()
    action_pattern["contract_hash"] = manifest["contract_hashes"]["action_pattern"]
    pack = build_behavioral_scenario_pack(action_pattern)
    result = run_behavioral_exam(action_pattern, pack, manifest)

    assert result["contract_hash"] == manifest["contract_hashes"]["behavioral_exam"]
    assert result["passed"] is True


def test_legacy_pattern_exam_alone_does_not_grant_behavioral_or_field_credit():
    from ai22b.kibo_reuse.models import PatternCandidate, PatternExamResult
    from ai22b.kibo_reuse.pattern_layer import reinforce_pattern_candidate

    pattern = PatternCandidate(
        pattern_id="pattern-legacy",
        owner="Boss",
        domain="software_agent_engineering",
        task_family="implementation",
        abstract_strategy=("Implement with tests",),
        required_conditions=("repository path",),
        known_failure_modes=("missing tests",),
        source_kibo_ids=("case-1", "case-2", "case-3"),
        exam_score=None,
        real_world_score=None,
        reinforcement_score=0.0,
        status="draft",
    )
    exam = PatternExamResult("exam-1", "pattern-legacy", "task-1", 1.0, True, (), ())

    report = reinforce_pattern_candidate(pattern, exam_results=[exam])

    assert report["pattern"]["status"] == "draft"
