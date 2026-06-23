import json

from ai22b.kibo_reuse.adversarial_critic import CRITIC_SCENARIO_KINDS, run_adversarial_critic


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
        "preconditions": [{"predicate_id": "pre-1", "op": "exists", "field": "repo", "value": True}],
        "required_observations": [],
        "steps": [
            {
                "node_id": "inspect",
                "action_type": "inspect",
                "capability": "code_inspection",
                "input_bindings": {"repo": "context.repo"},
                "expected_effects": [{"predicate_id": "effect-1", "op": "exists", "field": "artifact.plan", "value": True}],
                "timeout_ms": 1000,
                "retry_policy": {"max_attempts": 1, "backoff_ms": 0},
                "on_success": None,
                "on_failure": None,
                "on_uncertain": None,
                "human_review_required": False,
            }
        ],
        "transitions": [],
        "invariants": [{"predicate_id": "inv-1", "op": "neq", "field": "artifact.private_trace", "value": True}],
        "abort_conditions": [],
        "recovery_actions": [],
        "success_conditions": [{"predicate_id": "success-1", "op": "exists", "field": "artifact.plan", "value": True}],
        "forbidden_contexts": [],
        "required_capabilities": ["code_inspection"],
        "source_case_ids": ["case-1", "case-2", "case-3"],
        "validation_profile_id": None,
        "lifecycle_status": "draft",
    }


def test_adversarial_critic_builds_executable_scenario_pack():
    report = run_adversarial_critic(_action_pattern(), _manifest())
    kinds = {scenario["scenario_kind"] for scenario in report["scenario_pack"]["scenarios"]}

    assert report["schema"] == "paideia-adversarial-critic-report/v1"
    assert set(CRITIC_SCENARIO_KINDS) <= kinds
    assert report["behavioral_exam"]["schema"] == "paideia-kibo-v2-behavioral-exam/v2"
    assert "hidden_chain_of_thought_used" in report["policy"]


def test_adversarial_critic_gate_follows_embedded_behavioral_exam_failure():
    report = run_adversarial_critic(_action_pattern(), _manifest())

    assert report["behavioral_exam"]["passed"] is False
    assert report["pass_gate"] is False
    assert any(issue["code"] == "behavioral_exam_failed" for issue in report["issues"])


def test_adversarial_critic_cli_round_trip(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    manifest_path = tmp_path / "manifest.json"
    pattern_path = tmp_path / "pattern.json"
    output_path = tmp_path / "critic.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    pattern_path.write_text(json.dumps(_action_pattern()), encoding="utf-8")

    code = cli_main(
        [
            "adversarial-critic",
            "--pattern-path",
            str(pattern_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--output",
            str(output_path),
        ]
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert code in {0, 2}
    assert payload["schema"] == "paideia-adversarial-critic-report/v1"
