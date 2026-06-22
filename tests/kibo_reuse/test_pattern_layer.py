import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from ai22b.kibo_reuse.models import (
    CriticReport,
    FailureMemory,
    KiboRecord,
    PatternCandidate,
    PatternExamResult,
    RealWorldOutcome,
    TaskFingerprint,
    UserDecisionModel,
)
from ai22b.kibo_reuse.pattern_layer import (
    build_critic_report,
    reinforce_pattern_candidate,
    score_pattern_for_task,
    user_decision_fit_score,
)
from ai22b.kibo_reuse.router import build_kibo_reuse_plan
from ai22b.kibo_reuse.skill_graph import build_skill_gap_report
from ai22b.kibo_reuse.models import SkillNode


ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _task(**overrides):
    data = {
        "task_id": "task-1",
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_type": "implementation",
        "intent": "implement_cli",
        "constraints": (),
        "required_capabilities": ("code_inspection", "test_execution", "cli_design"),
        "risk_level": "low",
        "freshness_required": False,
        "expected_output_type": "patch",
        "user_style_markers": ("practical", "conclusion_first"),
    }
    data.update(overrides)
    return TaskFingerprint(**data)


def _kibo(**overrides):
    data = {
        "kibo_id": "kibo-1",
        "source_run_id": "run-1",
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_type": "implementation",
        "problem_signature": "Implement CLI command with tests.",
        "solution_steps": ("inspect CLI", "add parser", "add tests"),
        "reusable_logic": ("code_inspection", "test_execution", "cli_design", "practical"),
        "failure_modes": (),
        "required_inputs": ("code_inspection", "test_execution", "cli_design"),
        "output_template": "patch",
        "evidence_refs": ("reviewed-run",),
        "success_score": 98,
        "promotion_status": "promoted",
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-10T00:00:00Z",
    }
    data.update(overrides)
    return KiboRecord(**data)


def _pattern(**overrides):
    data = {
        "pattern_id": "pattern-cli",
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_family": "implementation",
        "abstract_strategy": ("inspect CLI", "add parser", "add tests", "practical"),
        "required_conditions": ("code_inspection", "test_execution", "cli_design"),
        "known_failure_modes": ("missing tests",),
        "source_kibo_ids": ("kibo-1", "kibo-2"),
        "exam_score": None,
        "real_world_score": None,
        "reinforcement_score": 0.4,
        "status": "draft",
    }
    data.update(overrides)
    return PatternCandidate(**data)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_pattern_before_exam_cannot_direct_reuse(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    pattern_path = tmp_path / "patterns.jsonl"
    _write_jsonl(kibo_path, [_kibo().to_dict()])
    _write_jsonl(pattern_path, [_pattern(status="draft").to_dict()])

    plan = build_kibo_reuse_plan(
        _task(),
        kibo_paths=[kibo_path],
        pattern_paths=[pattern_path],
    )

    assert plan["reuse_decision"]["reuse_mode"] == "reference_only"
    assert plan["reuse_decision"]["pattern_status"] == "draft"
    assert plan["reuse_decision"]["exam_validated"] is False


def test_high_exam_low_real_world_score_does_not_reinforce():
    pattern = _pattern(status="exam_validated", exam_score=0.95, reinforcement_score=0.6)
    report = reinforce_pattern_candidate(
        pattern,
        exam_results=[PatternExamResult("exam-1", pattern.pattern_id, "task-1", 0.95, True, (), ())],
        outcomes=[
            RealWorldOutcome(
                "outcome-1",
                pattern.pattern_id,
                "task-1",
                "2026-06-22T00:00:00Z",
                "task_outcome",
                False,
                0.1,
                None,
                2,
                "overgeneralization",
                (),
            )
        ],
        critic_reports=[CriticReport("critic-1", pattern.pattern_id, (), (), (), ("guard",), True)],
    )

    assert report["pattern"]["status"] != "reinforced"
    assert report["pattern"]["reinforcement_score"] < 0.85


def test_failure_memory_collision_reduces_pattern_score():
    task = _task(required_capabilities=("code_inspection", "test_execution"))
    pattern = _pattern(status="field_validated", real_world_score=0.8, reinforcement_score=0.78)
    failure = FailureMemory(
        "failure-1",
        pattern.pattern_id,
        "task-old",
        "risk_underestimated",
        "critical",
        ("code_inspection",),
        ("missed regression signal",),
        ("force validation",),
        "2026-06-22T00:00:00Z",
    )

    clean = score_pattern_for_task(task, pattern)
    risky = score_pattern_for_task(task, pattern, failures=[failure])

    assert risky.score < clean.score
    assert risky.failure_warnings


def test_critical_failure_quarantines_pattern():
    pattern = _pattern(status="field_validated", exam_score=0.8, real_world_score=0.8)
    report = reinforce_pattern_candidate(
        pattern,
        outcomes=[
            RealWorldOutcome(
                "outcome-1",
                pattern.pattern_id,
                "task-1",
                "2026-06-22T00:00:00Z",
                "task_outcome",
                False,
                0.0,
                None,
                1,
                "domain_mismatch",
                (),
            )
        ],
    )

    assert report["pattern"]["status"] == "quarantined"


def test_user_decision_model_fit_increases_for_matching_pattern():
    task = _task(user_style_markers=("practical",), constraints=("ROI",))
    pattern = _pattern(abstract_strategy=("practical", "ROI", "execution_feasibility"))
    model = UserDecisionModel(
        owner="Boss",
        preferred_output_style=("practical",),
        risk_preference="balanced",
        decision_biases=(),
        recurring_priorities=("ROI", "execution_feasibility"),
        rejected_patterns=(),
        favored_patterns=(),
    )

    assert user_decision_fit_score(task, pattern, model) > user_decision_fit_score(task, pattern, None)


def test_high_risk_pattern_without_critic_pass_is_reference_only(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    pattern_path = tmp_path / "patterns.jsonl"
    _write_jsonl(kibo_path, [_kibo().to_dict()])
    _write_jsonl(pattern_path, [_pattern(status="field_validated", exam_score=0.8, real_world_score=0.8).to_dict()])

    plan = build_kibo_reuse_plan(
        _task(risk_level="high"),
        kibo_paths=[kibo_path],
        pattern_paths=[pattern_path],
    )

    assert plan["reuse_decision"]["reuse_mode"] == "reference_only"
    assert plan["reuse_decision"]["critic_required"] is True
    assert "validation_failure:self_critic_gate" in plan["llm_required_parts"]


def test_pattern_candidate_requires_source_kibo_ids():
    with pytest.raises(ValueError):
        _pattern(source_kibo_ids=())


def test_real_world_outcomes_change_reinforcement_score():
    pattern = _pattern(status="exam_validated", exam_score=0.8, reinforcement_score=0.5)
    poor = reinforce_pattern_candidate(
        pattern,
        outcomes=[
            RealWorldOutcome("o1", pattern.pattern_id, "t1", "now", "task", False, 0.1, None, 2, None, ())
        ],
    )
    strong = reinforce_pattern_candidate(
        pattern,
        outcomes=[
            RealWorldOutcome("o1", pattern.pattern_id, "t1", "now", "task", True, 0.9, None, 9, None, ())
        ],
        critic_reports=[CriticReport("c1", pattern.pattern_id, (), (), (), ("guard",), True)],
    )

    assert strong["pattern"]["reinforcement_score"] > poor["pattern"]["reinforcement_score"]


def test_skill_graph_detects_missing_skills():
    report = build_skill_gap_report(
        _task(required_capabilities=("code_inspection", "test_execution", "cli_design")),
        [
            SkillNode("code_inspection", "code_inspection", "software_agent_engineering", 0.9),
            SkillNode("test_execution", "test_execution", "software_agent_engineering", 0.4),
        ],
    )

    assert "cli_design" in report["missing_skills"]
    assert "test_execution" in report["weak_skills"]


def test_pattern_contracts_validate_schemas():
    pattern = _pattern()
    exam = build_critic_report(pattern)
    Draft202012Validator(_schema("pattern_candidate.v1.schema.json")).validate(pattern.to_dict())
    Draft202012Validator(_schema("critic_report.v1.schema.json")).validate(exam.to_dict())
    Draft202012Validator(_schema("failure_memory.v1.schema.json")).validate(
        FailureMemory(
            "failure-1",
            pattern.pattern_id,
            "task-1",
            "overgeneralization",
            "medium",
            ("condition",),
            ("signal",),
            ("rule",),
            "2026-06-22T00:00:00Z",
        ).to_dict()
    )
