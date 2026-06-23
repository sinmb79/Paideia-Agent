import json

from ai22b.kibo_reuse.applicability import evaluate_kibo_applicability
from ai22b.kibo_reuse.models import FailureMemory, KiboRecord, TaskFingerprint
from ai22b.kibo_reuse.retriever import search_kibo
from ai22b.kibo_reuse.router import route_task
from ai22b.kibo_reuse.sqlite_index import build_sqlite_kibo_index, search_sqlite_kibo_index


def _task(**overrides):
    data = {
        "task_id": "task-1",
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_type": "implementation",
        "intent": "implement cli command with tests",
        "constraints": (),
        "required_capabilities": ("code_inspection", "test_execution"),
        "risk_level": "low",
        "freshness_required": False,
        "expected_output_type": "patch",
        "user_style_markers": (),
    }
    data.update(overrides)
    return TaskFingerprint(**data)


def _record(**overrides):
    data = {
        "kibo_id": "kibo-1",
        "source_run_id": "run-1",
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_type": "implementation",
        "problem_signature": "Implement CLI command with tests.",
        "solution_steps": ("inspect code", "run tests"),
        "reusable_logic": ("code_inspection", "test_execution"),
        "failure_modes": (),
        "required_inputs": ("code_inspection", "test_execution"),
        "output_template": "patch",
        "evidence_refs": ("reviewed-run",),
        "success_score": 95,
        "promotion_status": "promoted",
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-10T00:00:00Z",
    }
    data.update(overrides)
    return KiboRecord(**data)


def _failure(**overrides):
    data = {
        "failure_id": "failure-1",
        "pattern_id": "kibo-1",
        "task_id": "task-old",
        "error_type": "stale_data_reuse",
        "severity": "critical",
        "trigger_conditions": ("stale_data",),
        "missed_signals": ("freshness_required",),
        "prevention_rules": ("solve fresh",),
        "created_at": "2026-06-22T00:00:00Z",
    }
    data.update(overrides)
    return FailureMemory(**data)


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_applicability_blocks_domain_task_and_missing_capability_before_scoring():
    task = _task(required_capabilities=("code_inspection", "test_execution", "cli_design"))
    report = evaluate_kibo_applicability(
        task,
        _record(domain="legal_research", task_type="research", required_inputs=("code_inspection",), reusable_logic=("code_inspection",)),
    )

    issue_codes = {issue["code"] for issue in report["issues"]}
    assert report["applicable"] is False
    assert {"domain_mismatch", "task_type_mismatch", "missing_required_capability"} <= issue_codes


def test_search_excludes_records_with_missing_required_capability(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_jsonl(kibo_path, [_record(required_inputs=("code_inspection",), reusable_logic=("code_inspection",)).to_dict()])

    matches = search_kibo(_task(required_capabilities=("code_inspection", "test_execution")), kibo_paths=[kibo_path])

    assert matches == []


def test_structured_failure_memory_blocks_exact_trigger_only(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_jsonl(kibo_path, [_record().to_dict()])

    matches = search_kibo(
        _task(constraints=("stale_data",)),
        kibo_paths=[kibo_path],
        failure_memories=[_failure()],
    )

    assert matches == []


def test_catastrophic_failure_memory_blocks_even_when_not_named_critical(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_jsonl(kibo_path, [_record().to_dict()])

    for severity in ("severe", "fatal"):
        matches = search_kibo(
            _task(constraints=("stale_data",)),
            kibo_paths=[kibo_path],
            failure_memories=[_failure(severity=severity)],
        )

        assert matches == []


def test_critical_error_type_blocks_when_trigger_matches_without_high_severity(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_jsonl(kibo_path, [_record().to_dict()])

    matches = search_kibo(
        _task(constraints=("freshness_required",)),
        kibo_paths=[kibo_path],
        failure_memories=[_failure(error_type="freshness_error", severity="medium", trigger_conditions=("freshness_required",))],
    )

    assert matches == []


def test_pattern_scoped_failure_memory_fails_closed_when_trigger_matches(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_jsonl(kibo_path, [_record().to_dict()])

    matches = search_kibo(
        _task(constraints=("stale_data",)),
        kibo_paths=[kibo_path],
        failure_memories=[_failure(pattern_id="pattern-1")],
    )

    assert matches == []


def test_multi_condition_failure_memory_requires_all_triggers(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_jsonl(kibo_path, [_record(domain="valuation", required_inputs=("code_inspection",), reusable_logic=("code_inspection",)).to_dict()])

    matches = search_kibo(
        _task(domain="valuation", task_type="implementation", constraints=("valuation",), required_capabilities=("code_inspection",)),
        kibo_paths=[kibo_path],
        failure_memories=[_failure(pattern_id="*", trigger_conditions=("freshness_required", "valuation"))],
    )

    assert [match.record.kibo_id for match in matches] == ["kibo-1"]


def test_single_token_overlap_failure_memory_does_not_false_positive(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_jsonl(kibo_path, [_record().to_dict()])

    matches = search_kibo(
        _task(constraints=("risk_return",)),
        kibo_paths=[kibo_path],
        failure_memories=[_failure(trigger_conditions=("risk",), error_type="risk_overlap")],
    )

    assert [match.record.kibo_id for match in matches] == ["kibo-1"]


def test_unicode_trigger_conditions_can_warn_on_near_match():
    report = evaluate_kibo_applicability(
        _task(intent="포트폴리오 리스크분석 보고서 작성"),
        _record(),
        failures=[
            _failure(
                severity="low",
                error_type="style_gap",
                trigger_conditions=("포트폴리오 리스크분석",),
            )
        ],
    )

    assert report["applicable"] is True
    assert any(warning["code"] == "failure_memory_near_miss" for warning in report["warnings"])


def test_kibo_search_cli_accepts_failure_path_hard_gate(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    task_path = tmp_path / "task.json"
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    failure_path = tmp_path / "failure_memory.jsonl"
    output_path = tmp_path / "search.json"
    task_path.write_text(
        json.dumps(
            {
                "schema": "paideia-task-fingerprint/v1",
                **_task(constraints=("stale_data",)).to_dict(),
            }
        ),
        encoding="utf-8",
    )
    _write_jsonl(kibo_path, [_record().to_dict()])
    _write_jsonl(failure_path, [_failure().to_dict()])

    code = cli_main(
        [
            "kibo-search",
            "--task",
            str(task_path),
            "--kibo-path",
            str(kibo_path),
            "--failure-path",
            str(failure_path),
            "--output",
            str(output_path),
        ]
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert code == 0
    assert payload["matches"] == []


def test_sqlite_kibo_index_round_trip(tmp_path):
    db_path = tmp_path / "kibo.sqlite"
    index = build_sqlite_kibo_index([_record()], db_path)
    rows = search_sqlite_kibo_index(db_path, "CLI tests")

    assert index["record_count"] == 1
    assert rows[0]["kibo_id"] == "kibo-1"


def test_sqlite_kibo_index_orders_fts_matches_by_rank(tmp_path):
    db_path = tmp_path / "kibo.sqlite"
    broad = _record(kibo_id="broad", problem_signature="CLI")
    specific = _record(kibo_id="specific", problem_signature="CLI tests", solution_steps=("CLI tests", "pytest tests"))
    build_sqlite_kibo_index([broad, specific], db_path)

    rows = search_sqlite_kibo_index(db_path, "CLI tests", limit=2)

    assert [row["kibo_id"] for row in rows] == ["specific", "broad"]


def test_search_kibo_uses_sqlite_index_candidates(tmp_path):
    db_path = tmp_path / "kibo.sqlite"
    build_sqlite_kibo_index([_record()], db_path)

    matches = search_kibo(_task(), sqlite_index_path=db_path)

    assert [match.record.kibo_id for match in matches] == ["kibo-1"]


def test_route_task_uses_sqlite_index_candidates(tmp_path):
    db_path = tmp_path / "kibo.sqlite"
    build_sqlite_kibo_index([_record()], db_path)

    plan = route_task(_task(), sqlite_index_path=db_path, limit=1)

    assert plan["selected_kibo_ids"] == ["kibo-1"]


def test_kibo_search_cli_accepts_sqlite_index(tmp_path):
    from ai22b.talent_foundry.cli import main as cli_main

    task_path = tmp_path / "task.json"
    db_path = tmp_path / "kibo.sqlite"
    output_path = tmp_path / "search.json"
    task_path.write_text(json.dumps({"schema": "paideia-task-fingerprint/v1", **_task().to_dict()}), encoding="utf-8")
    build_sqlite_kibo_index([_record()], db_path)

    code = cli_main(
        [
            "kibo-search",
            "--task",
            str(task_path),
            "--repo-root",
            str(tmp_path),
            "--sqlite-index",
            str(db_path),
            "--output",
            str(output_path),
        ]
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert code == 0
    assert payload["matches"][0]["kibo"]["kibo_id"] == "kibo-1"
