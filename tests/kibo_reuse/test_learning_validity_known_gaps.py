import pytest

from ai22b.kibo_reuse.models import (
    FailureMemory,
    PatternCandidate,
    PatternExamResult,
    RealWorldOutcome,
    TaskFingerprint,
)
from ai22b.kibo_reuse.pattern_layer import (
    build_pattern_exam_result,
    reinforce_pattern_candidate,
    search_failure_memory,
)


def _pattern(**overrides):
    data = {
        "pattern_id": "pattern-validity-gap",
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_family": "implementation",
        "abstract_strategy": ("inspect current code", "add parser path", "run tests"),
        "required_conditions": ("repo_available", "tests_available"),
        "known_failure_modes": ("missing_holdout_behavior",),
        "source_kibo_ids": ("kibo-1", "kibo-2"),
        "exam_score": None,
        "real_world_score": None,
        "reinforcement_score": 0.4,
        "status": "draft",
    }
    data.update(overrides)
    return PatternCandidate(**data)


@pytest.mark.xfail(
    reason=(
        "PR-0 known gap: build_pattern_exam_result is a structural artifact check; "
        "it can pass without executing an unseen behavioral holdout task."
    ),
    strict=True,
)
def test_known_gap_structural_exam_passes_without_behavioral_holdout_execution():
    result = build_pattern_exam_result(_pattern(), task_id="holdout-task-not-executed")

    assert result.passed is False


@pytest.mark.xfail(
    reason=(
        "PR-0 known gap: FailureMemory search uses token overlap before structured "
        "applicability checks, so generic shared words can create false positives."
    ),
    strict=True,
)
def test_known_gap_token_overlap_failure_matching_false_positive():
    task = TaskFingerprint(
        task_id="task-1",
        owner="Boss",
        domain="software_agent_engineering",
        task_type="implementation",
        intent="review deployment plan",
        constraints=("review",),
        required_capabilities=("code_inspection",),
        risk_level="low",
        freshness_required=False,
        expected_output_type="patch",
        user_style_markers=(),
    )
    unrelated_failure = FailureMemory(
        failure_id="failure-unrelated",
        pattern_id="pattern-other",
        task_id="task-old",
        error_type="formatting_error",
        severity="low",
        trigger_conditions=("review",),
        missed_signals=("style nit",),
        prevention_rules=("review prose",),
        created_at="2026-06-23T00:00:00Z",
    )

    assert search_failure_memory(task, [unrelated_failure]) == []


@pytest.mark.xfail(
    reason=(
        "PR-0 known gap: a manually supplied high RealWorldOutcome score can promote "
        "field confidence without verifier provenance, baseline, or action receipts."
    ),
    strict=True,
)
def test_known_gap_manual_high_outcome_score_overstates_field_confidence():
    pattern = _pattern(status="exam_validated", exam_score=0.95, reinforcement_score=0.6)
    report = reinforce_pattern_candidate(
        pattern,
        exam_results=[PatternExamResult("exam-1", pattern.pattern_id, "task-1", 0.95, True, (), ())],
        outcomes=[
            RealWorldOutcome(
                "outcome-manual",
                pattern.pattern_id,
                "task-1",
                "2026-06-23T00:00:00Z",
                "manual_task_score",
                True,
                1.0,
                None,
                10,
                None,
                ("manual score only; no verifier receipt",),
            )
        ],
        reuse_stability_score=0.8,
    )

    assert report["pattern"]["status"] == "exam_validated"
