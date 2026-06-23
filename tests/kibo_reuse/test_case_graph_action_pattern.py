import json

import pytest

from ai22b.kibo_reuse.action_pattern import compile_action_pattern, validate_action_pattern_graph
from ai22b.kibo_reuse.case_graph import build_case_graphs_from_records
from ai22b.kibo_reuse.contracts_adapter import validate_action_pattern_v2, validate_case_graph_v2
from ai22b.kibo_reuse.models import KiboRecord


def _manifest():
    return {
        "schema": "paideia-cross-repo-compatibility/v1",
        "contracts_release": "2.0.0",
        "paideia_agent": ">=0.x,<1.0",
        "paideia_engines": ">=0.x,<1.0",
        "genius_derivation": ">=0.x,<1.0",
        "contract_hashes": {
            "case_graph": "c" * 64,
            "action_pattern": "a" * 64,
            "validation_profile": "b" * 64,
        },
    }


def _kibo(
    kibo_id: str,
    *,
    promotion_status: str = "approved",
    source_run_id: str | None = None,
    evidence_ref: str | None = None,
) -> KiboRecord:
    return KiboRecord.from_dict(
        {
            "kibo_id": kibo_id,
            "source_run_id": source_run_id or f"run-{kibo_id}",
            "owner": "Boss",
            "domain": "software_agent_engineering",
            "task_type": "implementation",
            "problem_signature": "Implement a bounded CLI command with tests.",
            "solution_steps": ["Inspect repository", "Implement command", "Run tests"],
            "reusable_logic": ["inspect_repository", "implement_command", "test_execution"],
            "failure_modes": ["missing_input", "test_regression"],
            "required_inputs": ["repository path", "acceptance tests"],
            "output_template": "patch plus test report",
            "evidence_refs": [evidence_ref or f"evidence-{kibo_id}"],
            "success_score": 92,
            "promotion_status": promotion_status,
            "created_at": "2026-06-23T00:00:00Z",
            "updated_at": "2026-06-23T00:00:00Z",
        }
    )


def test_case_graph_build_excludes_ineligible_kibo_and_validates_v2_payload():
    graphs = build_case_graphs_from_records(
        [_kibo("one"), _kibo("two", promotion_status="quarantined")],
        _manifest(),
    )

    assert len(graphs) == 1
    assert graphs[0]["schema"] == "paideia-kibo-v2-case-graph/v2"
    assert graphs[0]["source_kibo_ids"] == ["one"]
    assert validate_case_graph_v2(graphs[0], _manifest())["accepted"] is True


def test_case_graph_from_ineligible_kibo_fails_closed():
    from ai22b.kibo_reuse.case_graph import case_graph_from_kibo

    with pytest.raises(ValueError, match="not runtime eligible"):
        case_graph_from_kibo(_kibo("blocked", promotion_status="quarantined"), _manifest())


def test_action_pattern_compile_emits_valid_draft_from_three_case_graphs():
    graphs = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    pattern = compile_action_pattern(graphs, _manifest())
    report = validate_action_pattern_graph(pattern)

    assert pattern["schema"] == "paideia-kibo-v2-action-pattern/v2"
    assert pattern["lifecycle_status"] == "draft"
    assert pattern["required_capabilities"] == ["inspect_repository", "implement_command", "test_execution"]
    assert len(pattern["source_case_ids"]) == 3
    assert validate_action_pattern_v2(pattern, _manifest())["accepted"] is True
    assert report["passed"] is True


def test_action_pattern_compile_rejects_ineligible_source_case():
    graphs = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    for item in graphs[0]["context_variables"]:
        if item["name"] == "source_promotion_status":
            item["value"] = "quarantined"

    with pytest.raises(ValueError, match="ineligible source"):
        compile_action_pattern(graphs, _manifest())


def test_action_pattern_compile_validates_case_graph_inputs_before_compile():
    graphs = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    del graphs[0]["schema"]

    with pytest.raises(ValueError, match="Artifact schema"):
        compile_action_pattern(graphs, _manifest())


def test_action_pattern_compile_rejects_missing_or_unknown_source_provenance():
    missing = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    missing[0]["context_variables"] = [
        item for item in missing[0]["context_variables"] if item["name"] != "source_promotion_status"
    ]
    unknown = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    for item in unknown[0]["context_variables"]:
        if item["name"] == "source_promotion_status":
            item["value"] = "pending"

    with pytest.raises(ValueError, match="complete source provenance"):
        compile_action_pattern(missing, _manifest())
    with pytest.raises(ValueError, match="ineligible source"):
        compile_action_pattern(unknown, _manifest())


def test_action_pattern_compile_requires_source_diversity():
    two_cases = build_case_graphs_from_records([_kibo("one"), _kibo("two")], _manifest())
    same_run = build_case_graphs_from_records(
        [
            _kibo("one", source_run_id="same-run"),
            _kibo("two", source_run_id="same-run"),
            _kibo("three", source_run_id="same-run"),
        ],
        _manifest(),
    )

    with pytest.raises(ValueError, match="distinct source cases"):
        compile_action_pattern(two_cases, _manifest())
    with pytest.raises(ValueError, match="distinct source runs"):
        compile_action_pattern(same_run, _manifest())


def test_action_pattern_compile_requires_environment_diversity():
    graphs = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    for graph in graphs:
        for item in graph["context_variables"]:
            if item["name"] == "environment_fingerprint":
                item["value"] = "same-environment"

    with pytest.raises(ValueError, match="environment fingerprints"):
        compile_action_pattern(graphs, _manifest())


def test_action_pattern_compile_rejects_empty_action_evidence():
    graphs = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    for graph in graphs:
        graph["action_steps"] = []
        graph["constraints"] = []

    with pytest.raises(ValueError, match="at least one action step"):
        compile_action_pattern(graphs, _manifest())


def test_action_pattern_graph_validator_catches_unreachable_node_and_cycles():
    graphs = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    pattern = compile_action_pattern(graphs, _manifest())
    dead_node = dict(pattern["steps"][0])
    dead_node["node_id"] = "node-dead"
    pattern["steps"].append(dead_node)
    pattern["transitions"].append({"from_node_id": "node-003", "to_node_id": "node-001", "condition": None})

    report = validate_action_pattern_graph(pattern)

    assert report["passed"] is False
    assert {"unreachable_node", "cycle_without_bound"} <= {issue["code"] for issue in report["issues"]}


def test_action_pattern_graph_validator_checks_node_and_recovery_edges():
    graphs = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    pattern = compile_action_pattern(graphs, _manifest())
    pattern["steps"][0]["on_success"] = "missing-node"
    pattern["recovery_actions"] = [
        {
            "recovery_id": "recover-1",
            "trigger": {"predicate_id": "trigger-1", "op": "exists", "field": "failure", "value": True},
            "action_node_id": "missing-recovery-node",
        }
    ]

    report = validate_action_pattern_graph(pattern)

    assert report["passed"] is False
    assert {"invalid_node_edge", "invalid_recovery_action"} <= {issue["code"] for issue in report["issues"]}


def test_action_pattern_compile_cli_round_trip(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    manifest_path = tmp_path / "manifest.json"
    kibo_path = tmp_path / "kibo.jsonl"
    case_graph_path = tmp_path / "case_graphs.jsonl"
    pattern_path = tmp_path / "action_pattern.json"
    validation_path = tmp_path / "validation.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    kibo_path.write_text(
        "".join(json.dumps(_kibo(str(index)).to_dict()) + "\n" for index in range(1, 4)),
        encoding="utf-8",
    )

    case_graph_code = cli_main(
        [
            "case-graph-build",
            "--kibo-path",
            str(kibo_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--output",
            str(case_graph_path),
        ]
    )
    pattern_code = cli_main(
        [
            "action-pattern-compile",
            "--case-graph-path",
            str(case_graph_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--output",
            str(pattern_path),
            "--validation-output",
            str(validation_path),
        ]
    )
    pattern = json.loads(pattern_path.read_text(encoding="utf-8"))["action_pattern"]
    validation = json.loads(validation_path.read_text(encoding="utf-8"))

    assert case_graph_code == 0
    assert pattern_code == 0
    assert case_graph_path.exists()
    assert pattern["schema"] == "paideia-kibo-v2-action-pattern/v2"
    assert validation["passed"] is True


def test_action_pattern_compile_cli_blocks_invalid_graph_validation(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    manifest_path = tmp_path / "manifest.json"
    case_graph_path = tmp_path / "case_graphs.jsonl"
    pattern_path = tmp_path / "action_pattern.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    graphs = build_case_graphs_from_records([_kibo("one"), _kibo("two"), _kibo("three")], _manifest())
    for graph in graphs:
        graph["action_steps"] = []
        graph["constraints"] = []
    case_graph_path.write_text("".join(json.dumps(graph) + "\n" for graph in graphs), encoding="utf-8")

    pattern_code = cli_main(
        [
            "action-pattern-compile",
            "--case-graph-path",
            str(case_graph_path),
            "--compatibility-manifest",
            str(manifest_path),
            "--output",
            str(pattern_path),
        ]
    )
    result = json.loads(pattern_path.read_text(encoding="utf-8"))

    assert pattern_code == 2
    assert result["status"] == "blocked"
    assert result["validation"]["passed"] is False
