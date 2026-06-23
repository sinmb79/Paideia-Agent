from datetime import datetime, timezone

from ai22b.kibo_reuse.models import KiboRecord, TaskFingerprint
from ai22b.kibo_reuse.scorer import make_reuse_decision, score_kibo_record


def _record(**overrides):
    data = {
        "kibo_id": "kibo-1",
        "source_run_id": "run-1",
        "owner": "Boss",
        "domain": "investment_research",
        "task_type": "comparative_analysis",
        "problem_signature": "Assess buy opportunity using valuation, risk, chart, and theme analysis.",
        "solution_steps": ("compare valuation", "build risk matrix"),
        "reusable_logic": ("valuation", "risk_analysis", "chart_analysis", "theme_analysis", "conclusion_first"),
        "failure_modes": (),
        "required_inputs": ("web_research", "valuation", "risk_analysis", "chart_analysis", "theme_analysis"),
        "output_template": "conclusion_first risk_vs_return report",
        "evidence_refs": ("reviewed",),
        "success_score": 96,
        "promotion_status": "promoted",
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-10T00:00:00Z",
    }
    data.update(overrides)
    return KiboRecord(**data)


def _task(**overrides):
    data = {
        "task_id": "task-1",
        "owner": "Boss",
        "domain": "investment_research",
        "task_type": "comparative_analysis",
        "intent": "assess_buy_opportunity",
        "constraints": ("current_data_required",),
        "required_capabilities": ("web_research", "valuation", "risk_analysis", "chart_analysis", "theme_analysis"),
        "risk_level": "high",
        "freshness_required": True,
        "expected_output_type": "report",
        "user_style_markers": ("conclusion_first", "risk_vs_return"),
    }
    data.update(overrides)
    return TaskFingerprint(**data)


def test_same_domain_same_task_scores_high_but_high_risk_blocks_direct_reuse():
    task = _task()
    scores = [score_kibo_record(task, _record(), now=datetime(2026, 6, 22, tzinfo=timezone.utc))]
    decision = make_reuse_decision(task, scores)

    assert scores[0].reuse_score >= 0.85
    assert decision.reuse_mode == "partial_reuse"
    assert "validation_failure" in decision.llm_required_parts


def test_different_domain_scores_low():
    task = _task(domain="software_agent_engineering", risk_level="low", freshness_required=False)
    score = score_kibo_record(task, _record(), now=datetime(2026, 6, 22, tzinfo=timezone.utc))

    assert score.reuse_score < 0.45


def test_freshness_required_penalizes_old_kibo():
    task = _task()
    fresh = score_kibo_record(task, _record(), now=datetime(2026, 6, 22, tzinfo=timezone.utc))
    old = score_kibo_record(
        task,
        _record(updated_at="2020-01-01T00:00:00Z"),
        now=datetime(2026, 6, 22, tzinfo=timezone.utc),
    )

    assert old.freshness_penalty == 1.0
    assert old.reuse_score < fresh.reuse_score


def test_unicode_tokens_contribute_to_capability_and_style_scores():
    task = _task(
        risk_level="low",
        freshness_required=False,
        required_capabilities=("리스크분석",),
        user_style_markers=("결론우선",),
    )
    record = _record(
        required_inputs=(),
        reusable_logic=(),
        problem_signature="포트폴리오 리스크분석 절차",
        output_template="결론우선 보고서",
    )

    score = score_kibo_record(task, record, now=datetime(2026, 6, 22, tzinfo=timezone.utc))

    assert score.capability_overlap == 1.0
    assert score.user_style_score == 1.0
