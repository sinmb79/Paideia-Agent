from __future__ import annotations

from typing import Any

from .models import REUSE_PLAN_SCHEMA, ReuseDecision, TaskFingerprint
from .scorer import KiboScore
from .token_meter import estimate_token_saving_ratio


def _selected_scores(scores: list[KiboScore], decision: ReuseDecision) -> list[KiboScore]:
    selected = set(decision.selected_kibo_ids)
    return [score for score in scores if score.record.kibo_id in selected]


def _reused_steps(scores: list[KiboScore], mode: str) -> list[str]:
    if mode in {"reject_and_solve_fresh", "quarantine_required"}:
        return []
    steps: list[str] = []
    for score in scores:
        steps.extend(score.record.solution_steps)
        if not score.record.solution_steps and score.record.reusable_logic:
            steps.extend(score.record.reusable_logic)
    return list(dict.fromkeys(str(step) for step in steps if step))[:12]


def _risk_warnings(task: TaskFingerprint, decision: ReuseDecision) -> list[str]:
    warnings: list[str] = []
    if task.risk_level == "high":
        warnings.append("high_risk_task_direct_reuse_forbidden")
    if task.freshness_required:
        warnings.append("freshness_required_verify_current_external_data")
    if decision.reuse_mode == "reference_only":
        warnings.append("reference_only_requires_fresh_solution_validation")
    warnings.extend(decision.failure_warnings)
    if decision.critic_required:
        warnings.append("self_critic_gate_required")
    return warnings


def build_kibo_reuse_plan(
    task: TaskFingerprint,
    scores: list[KiboScore],
    decision: ReuseDecision,
    pattern_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_scores = _selected_scores(scores, decision)
    reused_steps = _reused_steps(selected_scores, decision.reuse_mode)
    llm_required_parts = list(decision.llm_required_parts)
    plan = {
        "schema": REUSE_PLAN_SCHEMA,
        "task_fingerprint": task.to_dict(),
        "reuse_decision": decision.to_dict(),
        "reuse_mode": decision.reuse_mode,
        "selected_kibo_ids": list(decision.selected_kibo_ids),
        "selected_kibo": [score.to_dict() for score in selected_scores],
        "reused_steps": reused_steps,
        "llm_required_parts": llm_required_parts,
        "risk_warnings": _risk_warnings(task, decision),
        "estimated_token_saving_ratio": estimate_token_saving_ratio(
            task=task.to_dict(),
            reused_steps=reused_steps,
            llm_required_parts=llm_required_parts,
        ),
        "execution_policy": {
            "llm_called_for_reused_steps": False,
            "llm_allowed_parts": llm_required_parts,
            "hidden_chain_of_thought_reused": False,
            "reviewable_kibo_only": True,
            "quarantined_records_excluded": True,
            "pattern_direct_reuse_requires_exam_validation": True,
            "high_risk_pattern_requires_field_validation_and_critic": True,
        },
    }
    if pattern_context:
        plan["pattern_context"] = pattern_context
    return plan
