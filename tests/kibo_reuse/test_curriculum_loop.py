import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ai22b.kibo_reuse.cli import handle_kibo_reuse_command, register_kibo_reuse_commands
from ai22b.kibo_reuse.curriculum_loop import (
    apply_curriculum_completion,
    build_adaptive_exam_report,
    build_curriculum_generation_report,
    detect_weaknesses,
    generate_adaptive_exam,
    generate_curriculum_plan,
    load_weakness_records,
)
from ai22b.kibo_reuse.models import (
    FailureMemory,
    KiboRecord,
    TaskFingerprint,
    WeaknessRecord,
)
from ai22b.kibo_reuse.router import build_kibo_reuse_plan


ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _failure(**overrides):
    data = {
        "failure_id": "failure-1",
        "pattern_id": "pattern-1",
        "task_id": "task-1",
        "error_type": "macro_ignored",
        "severity": "high",
        "trigger_conditions": ("investment_research",),
        "missed_signals": ("yield_curve",),
        "prevention_rules": ("check_macro_regime",),
        "created_at": "2026-06-22T00:00:00Z",
    }
    data.update(overrides)
    return FailureMemory(**data)


def _task(**overrides):
    data = {
        "task_id": "task-1",
        "owner": "Boss",
        "domain": "investment_research",
        "task_type": "comparative_analysis",
        "intent": "assess_buy_opportunity",
        "constraints": ("macro_regime_analysis",),
        "required_capabilities": ("valuation", "macro_regime_analysis"),
        "risk_level": "low",
        "freshness_required": False,
        "expected_output_type": "report",
        "user_style_markers": (),
    }
    data.update(overrides)
    return TaskFingerprint(**data)


def _kibo(**overrides):
    data = {
        "kibo_id": "kibo-1",
        "source_run_id": "run-1",
        "owner": "Boss",
        "domain": "investment_research",
        "task_type": "comparative_analysis",
        "problem_signature": "valuation macro regime analysis",
        "solution_steps": ("value", "macro", "risk"),
        "reusable_logic": ("valuation", "macro_regime_analysis"),
        "failure_modes": (),
        "required_inputs": ("valuation", "macro_regime_analysis"),
        "output_template": "report",
        "evidence_refs": ("reviewed-run",),
        "success_score": 95,
        "promotion_status": "promoted",
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-10T00:00:00Z",
    }
    data.update(overrides)
    return KiboRecord(**data)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_failure_to_weakness_to_curriculum_to_exam_loop_validates_schemas():
    weakness = detect_weaknesses([_failure()], owner="Boss", domain="investment_research")[0]
    curriculum = generate_curriculum_plan(weakness, related_skills=("liquidity",))
    exam = generate_adaptive_exam(curriculum, weakness=weakness)
    completion = apply_curriculum_completion(weakness, passed=True, score=0.9, transfer_passed=True, retention_passed=True)

    assert weakness.skill_id == "macro_regime_analysis"
    assert "liquidity" in curriculum.learning_goals
    assert exam.difficulty == "remediation"
    assert completion["updated_weakness"]["severity"] < weakness.severity
    Draft202012Validator(_schema("weakness_record.v1.schema.json")).validate(weakness.to_dict())
    Draft202012Validator(_schema("curriculum_plan.v1.schema.json")).validate(curriculum.to_dict())
    Draft202012Validator(_schema("adaptive_exam.v1.schema.json")).validate(exam.to_dict())
    Draft202012Validator(_schema("curriculum_completion.v1.schema.json")).validate(completion)


def test_existing_weakness_merge_does_not_duplicate_same_evidence():
    first = detect_weaknesses([_failure()], domain="investment_research")[0]
    merged = detect_weaknesses([_failure()], domain="investment_research", existing_weaknesses=[first])[0]

    assert merged.evidence_refs == first.evidence_refs
    assert merged.recurrence_count == 1


def test_completion_below_target_increases_weakness():
    weakness = detect_weaknesses([_failure()], owner="Boss", domain="investment_research")[0]

    completion = apply_curriculum_completion(weakness, passed=True, score=0.6, target_score=0.85)

    assert completion["effective_passed"] is False
    assert completion["action"] == "weakness_increased"
    assert completion["updated_weakness"]["severity"] > weakness.severity


def test_completion_requires_transfer_and_retention_before_weakness_reduction():
    weakness = detect_weaknesses([_failure()], owner="Boss", domain="investment_research")[0]

    completion = apply_curriculum_completion(weakness, passed=True, score=0.95, target_score=0.85)

    assert completion["effective_passed"] is False
    assert completion["transfer_passed"] is False
    assert completion["retention_passed"] is False
    assert completion["action"] == "weakness_increased"


def test_completion_rejects_non_finite_score_fail_closed():
    weakness = detect_weaknesses([_failure()], owner="Boss", domain="investment_research")[0]

    completion = apply_curriculum_completion(
        weakness,
        passed=True,
        score=float("nan"),
        target_score=0.85,
        transfer_passed=True,
        retention_passed=True,
    )

    assert completion["effective_passed"] is False
    assert completion["score"] == 0.0
    assert completion["action"] == "weakness_increased"
    assert completion["updated_weakness"]["severity"] > weakness.severity


def test_weakness_record_rejects_non_finite_severity_fail_closed():
    weakness = WeaknessRecord(
        "weakness-nan",
        "Boss",
        "investment_research",
        "macro_regime_analysis",
        "knowledge_gap",
        ("failure-1",),
        float("nan"),
        1,
    )

    assert weakness.severity == 0.0


def test_curriculum_completion_schema_accepts_legacy_v1_without_transfer_flags():
    weakness = detect_weaknesses([_failure()], owner="Boss", domain="investment_research")[0]
    completion = apply_curriculum_completion(weakness, passed=False, score=0.3)
    del completion["transfer_passed"]
    del completion["retention_passed"]

    Draft202012Validator(_schema("curriculum_completion.v1.schema.json")).validate(completion)


def test_repeated_failure_increases_weakness_and_adaptive_exam_difficulty():
    weakness = detect_weaknesses(
        [
            _failure(failure_id="f1"),
            _failure(failure_id="f2"),
            _failure(failure_id="f3"),
        ],
        domain="investment_research",
    )[0]
    exam = generate_adaptive_exam(generate_curriculum_plan(weakness), weakness=weakness)

    assert weakness.recurrence_count == 3
    assert weakness.severity >= 0.85
    assert exam.difficulty == "remediation"
    assert len(exam.questions) >= 6


def test_weakness_path_blocks_direct_reuse_without_pattern(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    weakness_path = tmp_path / "weakness.jsonl"
    _write_jsonl(kibo_path, [_kibo().to_dict()])
    _write_jsonl(
        weakness_path,
        [
            WeaknessRecord(
                "weakness-1",
                "Boss",
                "investment_research",
                "macro_regime_analysis",
                "knowledge_gap",
                ("failure-1",),
                0.85,
                2,
            ).to_dict()
        ],
    )

    plan = build_kibo_reuse_plan(
        _task(),
        kibo_paths=[kibo_path],
        weakness_paths=[weakness_path],
    )

    assert plan["reuse_decision"]["reuse_mode"] != "direct_reuse"
    assert "curriculum_remediation:macro_regime_analysis" in plan["llm_required_parts"]
    assert plan["reuse_decision"]["failure_warnings"]


def test_single_high_failure_weakness_blocks_direct_reuse_without_pattern(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    weakness_path = tmp_path / "weakness.jsonl"
    weakness = detect_weaknesses([_failure()], owner="Boss", domain="investment_research")[0]
    _write_jsonl(kibo_path, [_kibo().to_dict()])
    _write_jsonl(weakness_path, [weakness.to_dict()])

    plan = build_kibo_reuse_plan(
        _task(),
        kibo_paths=[kibo_path],
        weakness_paths=[weakness_path],
    )

    assert weakness.severity == 0.75
    assert plan["reuse_decision"]["reuse_mode"] != "direct_reuse"
    assert any("weakness_blocking" in warning for warning in plan["reuse_decision"]["failure_warnings"])


def test_unrelated_owner_weakness_does_not_block_direct_reuse(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    weakness_path = tmp_path / "weakness.jsonl"
    _write_jsonl(kibo_path, [_kibo().to_dict()])
    _write_jsonl(
        weakness_path,
        [
            WeaknessRecord(
                "weakness-1",
                "OtherOwner",
                "investment_research",
                "macro_regime_analysis",
                "knowledge_gap",
                ("failure-1",),
                0.95,
                4,
            ).to_dict()
        ],
    )

    plan = build_kibo_reuse_plan(_task(), kibo_paths=[kibo_path], weakness_paths=[weakness_path])

    assert plan["reuse_decision"]["reuse_mode"] == "direct_reuse"


def test_completion_report_can_be_loaded_as_weakness_record(tmp_path):
    weakness = detect_weaknesses([_failure()], owner="Boss", domain="investment_research")[0]
    completion = apply_curriculum_completion(
        weakness,
        passed=True,
        score=0.9,
        target_score=0.85,
        evidence_refs=("adaptive-exam-1",),
        transfer_passed=True,
        retention_passed=True,
    )
    completion_path = tmp_path / "completion.json"
    completion_path.write_text(json.dumps(completion), encoding="utf-8")

    loaded = load_weakness_records([completion_path])

    assert len(loaded) == 1
    assert loaded[0].weakness_id == weakness.weakness_id
    assert loaded[0].severity < weakness.severity


def test_curriculum_report_builders_are_reviewable():
    weakness = detect_weaknesses([_failure()], domain="investment_research")[0]
    curriculum_report = build_curriculum_generation_report([weakness])
    exam_report = build_adaptive_exam_report(generate_curriculum_plan(weakness), weakness=weakness)

    assert curriculum_report["schema"] == "paideia-curriculum-generation-report/v1"
    assert exam_report["schema"] == "paideia-adaptive-exam-generation-report/v1"


def test_curriculum_cli_commands_round_trip(tmp_path):
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_kibo_reuse_commands(subparsers)

    failure_path = tmp_path / "failure.jsonl"
    weakness_path = tmp_path / "weakness.json"
    curricula_path = tmp_path / "curricula.jsonl"
    exam_path = tmp_path / "exam.json"
    completion_path = tmp_path / "completion.json"
    updated_weakness_path = tmp_path / "updated_weakness.jsonl"
    report_path = tmp_path / "report.json"
    _write_jsonl(failure_path, [_failure().to_dict()])

    for argv in [
        [
            "weakness-detect",
            "--failure-path",
            str(failure_path),
            "--domain",
            "investment_research",
            "--output",
            str(weakness_path),
        ],
        [
            "curriculum-generate",
            "--weakness-path",
            str(weakness_path),
            "--output",
            str(curricula_path),
        ],
        [
            "adaptive-exam",
            "--curriculum-path",
            str(curricula_path),
            "--weakness-path",
            str(weakness_path),
            "--output",
            str(exam_path),
        ],
        [
            "curriculum-complete",
            "--weakness-path",
            str(weakness_path),
            "--curriculum-path",
            str(curricula_path),
            "--passed",
            "true",
            "--score",
            "0.9",
            "--evidence-ref",
            "adaptive-exam-cli",
            "--transfer-passed",
            "--retention-passed",
            "--output",
            str(completion_path),
            "--updated-weakness-output",
            str(updated_weakness_path),
        ],
        [
            "curriculum-report",
            "--weakness-path",
            str(weakness_path),
            "--curriculum-path",
            str(curricula_path),
            "--exam-path",
            str(exam_path),
            "--output",
            str(report_path),
        ],
    ]:
        assert handle_kibo_reuse_command(parser.parse_args(argv)) == 0

    assert json.loads(weakness_path.read_text(encoding="utf-8"))["schema"] == "paideia-weakness-detection-report/v1"
    assert json.loads(exam_path.read_text(encoding="utf-8"))["schema"] == "paideia-adaptive-exam-generation-report/v1"
    assert json.loads(completion_path.read_text(encoding="utf-8"))["action"] == "weakness_reduced"
    assert load_weakness_records([completion_path])[0].weakness_id
    assert load_weakness_records([updated_weakness_path])[0].weakness_id
    assert json.loads(report_path.read_text(encoding="utf-8"))["schema"] == "paideia-curriculum-feedback-report/v1"
