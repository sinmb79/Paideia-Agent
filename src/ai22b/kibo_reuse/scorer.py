from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .models import KiboRecord, ReuseDecision, TaskFingerprint


@dataclass(frozen=True)
class KiboScore:
    record: KiboRecord
    reuse_score: float
    domain_score: float
    task_type_score: float
    capability_overlap: float
    success_score: float
    user_style_score: float
    risk_penalty: float
    freshness_penalty: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kibo": self.record.to_dict(),
            "reuse_score": round(self.reuse_score, 4),
            "score_breakdown": {
                "domain_score": round(self.domain_score, 4),
                "task_type_score": round(self.task_type_score, 4),
                "capability_overlap": round(self.capability_overlap, 4),
                "success_score": round(self.success_score, 4),
                "user_style_score": round(self.user_style_score, 4),
                "risk_penalty": round(self.risk_penalty, 4),
                "freshness_penalty": round(self.freshness_penalty, 4),
            },
            "reason": self.reason,
        }


def _tokens(value: Any) -> set[str]:
    if isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    elif isinstance(value, (list, tuple, set)):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value or "")
    return {token.casefold() for token in re.findall(r"\w+", text, flags=re.UNICODE)}


def _compatible_domain(task_domain: str, kibo_domain: str) -> float:
    task = task_domain.casefold()
    kibo = kibo_domain.casefold()
    if task == kibo:
        return 1.0
    investment = {"investment_research", "securities_research", "finance", "valuation"}
    software = {"software_agent_engineering", "coding", "software", "devtools"}
    if task in investment and kibo in investment:
        return 0.75
    if task in software and kibo in software:
        return 0.75
    return 0.0


def _task_type_score(task_type: str, kibo_task_type: str) -> float:
    if task_type == kibo_task_type:
        return 1.0
    analysis = {"comparative_analysis", "research", "question_answering"}
    implementation = {"implementation", "implementation_planning"}
    if task_type in analysis and kibo_task_type in analysis:
        return 0.55
    if task_type in implementation and kibo_task_type in implementation:
        return 0.6
    return 0.0


def _capability_overlap(task: TaskFingerprint, record: KiboRecord) -> float:
    required = set(task.required_capabilities)
    record_caps = _tokens(
        [
            record.required_inputs,
            record.reusable_logic,
            record.problem_signature,
            record.solution_steps,
        ]
    )
    if not required:
        return 1.0
    matched = {cap for cap in required if cap.casefold() in record_caps or cap in record.required_inputs}
    return len(matched) / len(required)


def _style_score(task: TaskFingerprint, record: KiboRecord) -> float:
    markers = set(task.user_style_markers)
    if not markers:
        return 0.5
    record_tokens = _tokens([record.output_template, record.reusable_logic, record.problem_signature])
    matched = {marker for marker in markers if marker.casefold() in record_tokens}
    return len(matched) / len(markers)


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _freshness_penalty(task: TaskFingerprint, record: KiboRecord, *, now: datetime | None = None) -> float:
    if not task.freshness_required:
        return 0.0
    timestamp = _parse_timestamp(record.updated_at or record.created_at)
    if timestamp is None:
        return 1.0
    age_days = ((now or datetime.now(timezone.utc)) - timestamp).days
    if age_days <= 30:
        return 0.0
    if age_days <= 180:
        return 0.4
    return 1.0


def _risk_penalty(task: TaskFingerprint) -> float:
    if task.risk_level == "high":
        return 0.65
    if task.risk_level == "medium":
        return 0.25
    return 0.0


def score_kibo_record(
    task: TaskFingerprint,
    record: KiboRecord,
    *,
    now: datetime | None = None,
) -> KiboScore:
    domain = _compatible_domain(task.domain, record.domain)
    task_type = _task_type_score(task.task_type, record.task_type)
    capability = _capability_overlap(task, record)
    success = max(0.0, min(1.0, record.success_score / 100.0))
    style = _style_score(task, record)
    risk = _risk_penalty(task)
    freshness = _freshness_penalty(task, record, now=now)
    score = (
        0.30 * domain
        + 0.25 * task_type
        + 0.20 * capability
        + 0.15 * success
        + 0.10 * style
        - 0.20 * risk
        - 0.20 * freshness
    )
    if domain == 0.0:
        score = min(score, 0.44)
    score = max(0.0, min(1.0, score))
    reason = (
        f"domain={domain:.2f}; task_type={task_type:.2f}; "
        f"capability={capability:.2f}; success={success:.2f}; "
        f"risk_penalty={risk:.2f}; freshness_penalty={freshness:.2f}"
    )
    return KiboScore(
        record=record,
        reuse_score=score,
        domain_score=domain,
        task_type_score=task_type,
        capability_overlap=capability,
        success_score=success,
        user_style_score=style,
        risk_penalty=risk,
        freshness_penalty=freshness,
        reason=reason,
    )


def reuse_mode_for_score(score: float, *, risk_level: str) -> str:
    if score >= 0.85 and risk_level != "high":
        return "direct_reuse"
    if score >= 0.65:
        return "partial_reuse"
    if score >= 0.45:
        return "reference_only"
    return "reject_and_solve_fresh"


def _decision_id(task_id: str, scores: list[KiboScore]) -> str:
    raw = task_id + "|" + "|".join(score.record.kibo_id for score in scores)
    return "reuse-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def llm_required_parts(task: TaskFingerprint, top_score: KiboScore | None, mode: str) -> tuple[str, ...]:
    parts: list[str] = []
    if mode == "reject_and_solve_fresh":
        parts.append("novel_case")
    if task.freshness_required:
        parts.append("fresh_external_data")
    if task.risk_level == "high":
        parts.append("validation_failure")
    if top_score is None:
        parts.append("missing_context")
    else:
        record_caps = _tokens([top_score.record.required_inputs, top_score.record.reusable_logic])
        for capability in task.required_capabilities:
            if capability.casefold() not in record_caps and capability not in top_score.record.required_inputs:
                parts.append(f"missing_context:{capability}")
    if not task.intent or task.intent == "answer_user_request":
        parts.append("ambiguous_user_intent")
    return tuple(dict.fromkeys(parts))


def make_reuse_decision(task: TaskFingerprint, scores: list[KiboScore]) -> ReuseDecision:
    eligible = [score for score in scores if score.record.is_runtime_eligible]
    if not eligible:
        mode = "reject_and_solve_fresh"
        return ReuseDecision(
            decision_id=_decision_id(task.task_id, []),
            task_id=task.task_id,
            selected_kibo_ids=(),
            similarity_score=0.0,
            confidence_score=0.0,
            risk_score=1.0 if task.risk_level == "high" else 0.5,
            reuse_mode=mode,
            llm_required_parts=llm_required_parts(task, None, mode),
            reason="no_reviewed_runtime_eligible_kibo_found",
        )

    top = eligible[0]
    mode = reuse_mode_for_score(top.reuse_score, risk_level=task.risk_level)
    selected = tuple(score.record.kibo_id for score in eligible[:3] if score.reuse_score >= 0.45)
    return ReuseDecision(
        decision_id=_decision_id(task.task_id, eligible),
        task_id=task.task_id,
        selected_kibo_ids=selected if mode != "reject_and_solve_fresh" else (),
        similarity_score=top.reuse_score,
        confidence_score=max(0.0, min(1.0, top.reuse_score - (0.10 if task.freshness_required else 0.0))),
        risk_score=1.0 if task.risk_level == "high" else 0.5 if task.risk_level == "medium" else 0.1,
        reuse_mode=mode,
        llm_required_parts=llm_required_parts(task, top, mode),
        reason=("high_risk_direct_reuse_blocked; " if task.risk_level == "high" and top.reuse_score >= 0.85 else "")
        + top.reason,
    )
