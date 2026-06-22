from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import (
    CriticReport,
    FailureMemory,
    KiboRecord,
    PatternCandidate,
    PatternExamResult,
    RealWorldOutcome,
    ReuseDecision,
    TaskFingerprint,
    UserDecisionModel,
)
from .retriever import load_kibo_records
from .skill_graph import build_skill_gap_report


PATTERN_INDEX_SCHEMA = "paideia-pattern-index/v1"
PATTERN_REINFORCEMENT_REPORT_SCHEMA = "paideia-pattern-reinforcement-report/v1"
FAILURE_SEARCH_SCHEMA = "paideia-failure-search-result/v1"

CRITICAL_FAILURE_SEVERITIES = {"critical", "catastrophic", "fatal"}
CRITICAL_FAILURE_TYPES = {
    "freshness_error",
    "domain_mismatch",
    "risk_underestimated",
    "market_regime_shift",
}


@dataclass(frozen=True)
class PatternScore:
    pattern: PatternCandidate
    score: float
    user_decision_fit_score: float
    failure_warnings: tuple[str, ...]
    critic_required: bool
    critic_passed: bool
    skill_gaps: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern.to_dict(),
            "score": round(self.score, 4),
            "user_decision_fit_score": round(self.user_decision_fit_score, 4),
            "failure_warnings": list(self.failure_warnings),
            "critic_required": self.critic_required,
            "critic_passed": self.critic_passed,
            "skill_gaps": list(self.skill_gaps),
            "reason": self.reason,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row must be an object at {path}:{line_number}")
        rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def load_patterns(paths: Iterable[Path] | None) -> list[PatternCandidate]:
    patterns: list[PatternCandidate] = []
    for path in paths or []:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("schema") == "paideia-pattern-candidate/v1":
                rows = [payload]
            elif isinstance(payload, dict) and isinstance(payload.get("pattern"), dict):
                rows = [payload["pattern"]]
            else:
                rows = payload.get("patterns", []) if isinstance(payload, dict) else []
        else:
            rows = _read_jsonl(path)
        for row in rows:
            if isinstance(row, dict):
                patterns.append(PatternCandidate.from_dict(row))
    return patterns


def load_failure_memories(paths: Iterable[Path] | None) -> list[FailureMemory]:
    failures: list[FailureMemory] = []
    for path in paths or []:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("failures", []) if isinstance(payload, dict) else []
        else:
            rows = _read_jsonl(path)
        for row in rows:
            if isinstance(row, dict):
                failures.append(FailureMemory.from_dict(row))
    return failures


def load_real_world_outcomes(paths: Iterable[Path] | None) -> list[RealWorldOutcome]:
    outcomes: list[RealWorldOutcome] = []
    for path in paths or []:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("outcomes", []) if isinstance(payload, dict) else []
        else:
            rows = _read_jsonl(path)
        for row in rows:
            if isinstance(row, dict):
                outcomes.append(RealWorldOutcome.from_dict(row))
    return outcomes


def load_pattern_exam_results(paths: Iterable[Path] | None) -> list[PatternExamResult]:
    exams: list[PatternExamResult] = []
    for path in paths or []:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("exam_results", []) if isinstance(payload, dict) else []
            if payload.get("schema") == "paideia-pattern-exam-result/v1":
                rows = [payload]
        else:
            rows = _read_jsonl(path)
        for row in rows:
            if isinstance(row, dict):
                exams.append(PatternExamResult.from_dict(row))
    return exams


def load_critic_reports(paths: Iterable[Path] | None) -> list[CriticReport]:
    reports: list[CriticReport] = []
    for path in paths or []:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("critic_reports", []) if isinstance(payload, dict) else []
            if payload.get("schema") == "paideia-critic-report/v1":
                rows = [payload]
        else:
            rows = _read_jsonl(path)
        for row in rows:
            if isinstance(row, dict):
                reports.append(CriticReport.from_dict(row))
    return reports


def load_user_decision_model(path: Path | None) -> UserDecisionModel | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("user decision model file must contain a JSON object")
    return UserDecisionModel.from_dict(payload)


def extract_pattern_candidates(records: Iterable[KiboRecord]) -> list[PatternCandidate]:
    groups: dict[tuple[str, str, str], list[KiboRecord]] = {}
    for record in records:
        if not record.is_runtime_eligible:
            continue
        key = (record.owner, record.domain, record.task_type)
        groups.setdefault(key, []).append(record)

    patterns: list[PatternCandidate] = []
    for (owner, domain, task_family), group in sorted(groups.items()):
        if not group:
            continue
        strategy = _rank_terms(
            item
            for record in group
            for item in (record.reusable_logic or record.solution_steps)
        )
        conditions = _rank_terms(item for record in group for item in record.required_inputs)
        failure_modes = _rank_terms(item for record in group for item in record.failure_modes)
        source_ids = tuple(record.kibo_id for record in group)
        avg_success = sum(record.success_score for record in group) / (100.0 * len(group))
        pattern_id = _stable_id("pattern", owner, domain, task_family, ",".join(source_ids))
        patterns.append(
            PatternCandidate(
                pattern_id=pattern_id,
                owner=owner,
                domain=domain,
                task_family=task_family,
                abstract_strategy=strategy[:12],
                required_conditions=conditions[:12],
                known_failure_modes=failure_modes[:12],
                source_kibo_ids=source_ids,
                exam_score=None,
                real_world_score=None,
                reinforcement_score=round(avg_success * 0.4, 4),
                status="draft",
            )
        )
    return patterns


def build_pattern_index_from_kibo(
    *,
    kibo_paths: Iterable[Path],
    output_path: Path | None = None,
) -> dict[str, Any]:
    records: list[KiboRecord] = []
    for path in kibo_paths:
        records.extend(load_kibo_records(path))
    patterns = extract_pattern_candidates(records)
    payload = {
        "schema": PATTERN_INDEX_SCHEMA,
        "pattern_count": len(patterns),
        "patterns": [pattern.to_dict() for pattern in patterns],
        "policy": {
            "source": "reviewable_kibo_records_only",
            "hidden_chain_of_thought_reused": False,
            "quarantined_patterns_runtime_blocked": True,
        },
    }
    if output_path is not None:
        if output_path.suffix.lower() == ".jsonl":
            _write_jsonl(output_path, [pattern.to_dict() for pattern in patterns])
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def build_pattern_exam_result(pattern: PatternCandidate, *, task_id: str | None = None) -> PatternExamResult:
    mistakes: list[str] = []
    notes: list[str] = []
    score = 0.45
    if len(pattern.source_kibo_ids) >= 2:
        score += 0.15
    else:
        mistakes.append("single_source_pattern_needs_more_cases")
    if pattern.abstract_strategy:
        score += 0.15
    else:
        mistakes.append("missing_abstract_strategy")
    if pattern.required_conditions:
        score += 0.10
    else:
        notes.append("add_required_conditions_before_field_use")
    if pattern.known_failure_modes:
        score += 0.10
    else:
        notes.append("add_failure_modes_before_promotion")
    score = max(0.0, min(1.0, score))
    passed = score >= 0.70 and not mistakes
    if passed:
        notes.append("exam_validated_for_bounded_partial_reuse")
    return PatternExamResult(
        exam_id=_stable_id("exam", pattern.pattern_id, task_id or "synthetic"),
        pattern_id=pattern.pattern_id,
        task_id=task_id or _stable_id("synthetic-task", pattern.pattern_id),
        score=score,
        passed=passed,
        mistakes=tuple(mistakes),
        improvement_notes=tuple(notes),
    )


def build_real_world_outcome(
    *,
    pattern_id: str,
    task_id: str,
    success: bool,
    score: float | None = None,
    outcome_type: str = "task_outcome",
    user_feedback_score: int | None = None,
    error_type: str | None = None,
    notes: Iterable[str] = (),
) -> RealWorldOutcome:
    return RealWorldOutcome(
        outcome_id=_stable_id("outcome", pattern_id, task_id, _now_iso()),
        pattern_id=pattern_id,
        task_id=task_id,
        applied_at=_now_iso(),
        outcome_type=outcome_type,
        success=success,
        quantitative_result=None if score is None else max(0.0, min(1.0, float(score))),
        qualitative_result=None,
        user_feedback_score=user_feedback_score,
        error_type=error_type,
        notes=tuple(str(note) for note in notes if str(note)),
    )


def reinforce_pattern_candidate(
    pattern: PatternCandidate,
    *,
    exam_results: Iterable[PatternExamResult] = (),
    outcomes: Iterable[RealWorldOutcome] = (),
    critic_reports: Iterable[CriticReport] = (),
    reuse_stability_score: float = 0.5,
) -> dict[str, Any]:
    related_exams = [exam for exam in exam_results if exam.pattern_id == pattern.pattern_id]
    related_outcomes = [outcome for outcome in outcomes if outcome.pattern_id == pattern.pattern_id]
    exam_score = (
        sum(exam.score for exam in related_exams) / len(related_exams)
        if related_exams
        else pattern.exam_score
    )
    real_world_score = _real_world_score(related_outcomes, fallback=pattern.real_world_score)
    feedback_score = _feedback_score(related_outcomes)
    failure_penalty = _failure_penalty(related_outcomes)
    critic_passed = any(report.pattern_id == pattern.pattern_id and report.pass_gate for report in critic_reports)
    critical_failure = any(
        (outcome.error_type or "") in CRITICAL_FAILURE_TYPES
        or any("critical" in note.casefold() for note in outcome.notes)
        for outcome in related_outcomes
        if not outcome.success
    )
    reinforcement = (
        0.35 * (exam_score or 0.0)
        + 0.40 * (real_world_score or 0.0)
        + 0.15 * feedback_score
        + 0.10 * max(0.0, min(1.0, reuse_stability_score))
        - 0.30 * failure_penalty
    )
    reinforcement = max(0.0, min(1.0, reinforcement))
    status = _status_for_reinforcement(
        reinforcement,
        critical_failure=critical_failure,
        critic_passed=critic_passed,
        current_status=pattern.status,
    )
    updated = PatternCandidate(
        pattern_id=pattern.pattern_id,
        owner=pattern.owner,
        domain=pattern.domain,
        task_family=pattern.task_family,
        abstract_strategy=pattern.abstract_strategy,
        required_conditions=pattern.required_conditions,
        known_failure_modes=pattern.known_failure_modes,
        source_kibo_ids=pattern.source_kibo_ids,
        exam_score=exam_score,
        real_world_score=real_world_score,
        reinforcement_score=reinforcement,
        status=status,
    )
    return {
        "schema": PATTERN_REINFORCEMENT_REPORT_SCHEMA,
        "pattern": updated.to_dict(),
        "inputs": {
            "exam_result_count": len(related_exams),
            "real_world_outcome_count": len(related_outcomes),
            "critic_passed": critic_passed,
            "failure_penalty": round(failure_penalty, 4),
            "reuse_stability_score": round(reuse_stability_score, 4),
        },
    }


def _status_for_reinforcement(
    score: float,
    *,
    critical_failure: bool,
    critic_passed: bool,
    current_status: str,
) -> str:
    if critical_failure:
        return "quarantined"
    if score >= 0.85:
        return "reinforced" if critic_passed else "field_validated"
    if score >= 0.70:
        return "field_validated"
    if score >= 0.55:
        return "exam_validated"
    if score >= 0.40:
        return "draft" if current_status == "draft" else current_status
    return "weakened"


def search_failure_memory(
    task: TaskFingerprint,
    failures: Iterable[FailureMemory],
    *,
    pattern_id: str | None = None,
) -> list[FailureMemory]:
    task_terms = _term_set(
        [
            task.domain,
            task.task_type,
            task.intent,
            task.constraints,
            task.required_capabilities,
            task.user_style_markers,
        ]
    )
    matches: list[FailureMemory] = []
    for failure in failures:
        if pattern_id is not None and failure.pattern_id != pattern_id:
            continue
        failure_terms = _term_set(
            [
                failure.error_type,
                failure.severity,
                failure.trigger_conditions,
                failure.missed_signals,
                failure.prevention_rules,
            ]
        )
        if task_terms & failure_terms:
            matches.append(failure)
    matches.sort(key=lambda item: _severity_rank(item.severity), reverse=True)
    return matches


def build_failure_search_result(
    task: TaskFingerprint,
    failures: Iterable[FailureMemory],
) -> dict[str, Any]:
    matches = search_failure_memory(task, failures)
    return {
        "schema": FAILURE_SEARCH_SCHEMA,
        "task_fingerprint": task.to_dict(),
        "matches": [failure.to_dict() for failure in matches],
        "warnings": [_failure_warning(failure) for failure in matches],
    }


def build_critic_report(pattern: PatternCandidate) -> CriticReport:
    objections: list[str] = []
    assumptions: list[str] = []
    flags: list[str] = []
    safeguards: list[str] = []
    if not pattern.required_conditions:
        objections.append("required_conditions_missing")
        safeguards.append("define_entry_conditions_before_use")
    if not pattern.known_failure_modes:
        assumptions.append("failure_modes_are_not_yet_observed")
        safeguards.append("add_failure_memory_review")
    if pattern.real_world_score is None:
        flags.append("no_real_world_outcome_evidence")
        safeguards.append("require_field_validation_before_direct_reuse")
    if pattern.status in {"draft", "exam_validated"}:
        flags.append("pattern_not_field_validated")
    if not objections and not flags:
        safeguards.append("keep_freshness_and_domain_checks_enabled")
    return CriticReport(
        report_id=_stable_id("critic", pattern.pattern_id, pattern.status),
        pattern_id=pattern.pattern_id,
        objections=tuple(objections),
        hidden_assumptions=tuple(assumptions),
        risk_flags=tuple(flags),
        required_safeguards=tuple(dict.fromkeys(safeguards)),
        pass_gate=not objections and not flags,
    )


def score_pattern_for_task(
    task: TaskFingerprint,
    pattern: PatternCandidate,
    *,
    failures: Iterable[FailureMemory] = (),
    user_model: UserDecisionModel | None = None,
    critic_reports: Iterable[CriticReport] = (),
    skill_gap_report: dict[str, Any] | None = None,
) -> PatternScore:
    domain = 1.0 if task.domain == pattern.domain else 0.0
    task_family = 1.0 if task.task_type == pattern.task_family else 0.4
    required = set(task.required_capabilities)
    conditions = _term_set(pattern.required_conditions)
    capability = len({cap for cap in required if cap.casefold() in conditions}) / len(required) if required else 1.0
    fit = user_decision_fit_score(task, pattern, user_model)
    failures_for_pattern = search_failure_memory(task, failures, pattern_id=pattern.pattern_id)
    warnings = tuple(_failure_warning(failure) for failure in failures_for_pattern)
    failure_penalty = min(1.0, sum(0.35 if _is_blocking_failure(failure) else 0.15 for failure in failures_for_pattern))
    skill_gaps = tuple((skill_gap_report or {}).get("missing_skills", []) + (skill_gap_report or {}).get("weak_skills", []))
    skill_penalty = min(0.4, 0.08 * len(skill_gaps))
    critic_required = task.risk_level == "high" or pattern.status == "reinforced"
    critic_passed = any(report.pattern_id == pattern.pattern_id and report.pass_gate for report in critic_reports)
    status_score = {
        "draft": 0.25,
        "exam_validated": 0.55,
        "field_validated": 0.78,
        "reinforced": 0.9,
        "weakened": 0.15,
        "quarantined": 0.0,
    }[pattern.status]
    score = (
        0.25 * domain
        + 0.20 * task_family
        + 0.20 * capability
        + 0.20 * status_score
        + 0.15 * fit
        - 0.30 * failure_penalty
        - skill_penalty
    )
    if domain == 0.0:
        score = min(score, 0.30)
    if pattern.status == "quarantined":
        score = 0.0
    score = max(0.0, min(1.0, score))
    return PatternScore(
        pattern=pattern,
        score=score,
        user_decision_fit_score=fit,
        failure_warnings=warnings,
        critic_required=critic_required,
        critic_passed=critic_passed,
        skill_gaps=skill_gaps,
        reason=(
            f"pattern_domain={domain:.2f}; task_family={task_family:.2f}; "
            f"capability={capability:.2f}; status={status_score:.2f}; "
            f"user_fit={fit:.2f}; failure_penalty={failure_penalty:.2f}; "
            f"skill_penalty={skill_penalty:.2f}"
        ),
    )


def apply_pattern_layer_to_decision(
    task: TaskFingerprint,
    base_decision: ReuseDecision,
    *,
    patterns: Iterable[PatternCandidate] = (),
    failures: Iterable[FailureMemory] = (),
    user_model: UserDecisionModel | None = None,
    critic_reports: Iterable[CriticReport] = (),
    skill_gap_report: dict[str, Any] | None = None,
) -> tuple[ReuseDecision, dict[str, Any]]:
    scores = [
        score_pattern_for_task(
            task,
            pattern,
            failures=failures,
            user_model=user_model,
            critic_reports=critic_reports,
            skill_gap_report=skill_gap_report,
        )
        for pattern in patterns
    ]
    scores.sort(key=lambda item: (item.score, item.pattern.reinforcement_score), reverse=True)
    if not scores:
        extras = {
            "pattern_matches": [],
            "skill_gap_report": skill_gap_report,
            "failure_memory_policy": {"warnings_reduce_reuse": True},
        }
        return base_decision, extras

    top = scores[0]
    mode = _mode_with_pattern_policy(task, base_decision.reuse_mode, top)
    llm_parts = list(base_decision.llm_required_parts)
    for gap in top.skill_gaps:
        llm_parts.append(f"missing_skill:{gap}")
    if top.critic_required and not top.critic_passed:
        llm_parts.append("validation_failure:self_critic_gate")
    if top.failure_warnings:
        llm_parts.append("validation_failure:failure_memory")
    reason = base_decision.reason + "; " + top.reason
    if mode != base_decision.reuse_mode:
        reason += f"; pattern_policy_adjusted={mode}"
    adjusted_similarity = (
        min(base_decision.similarity_score, top.score)
        if top.failure_warnings or top.pattern.status in {"draft", "weakened", "quarantined"}
        else max(base_decision.similarity_score, top.score)
    )
    decision = ReuseDecision(
        decision_id=base_decision.decision_id,
        task_id=base_decision.task_id,
        selected_kibo_ids=base_decision.selected_kibo_ids if mode != "reject_and_solve_fresh" else (),
        similarity_score=adjusted_similarity,
        confidence_score=max(0.0, min(1.0, base_decision.confidence_score - (0.15 if top.failure_warnings else 0.0))),
        risk_score=base_decision.risk_score,
        reuse_mode=mode,
        llm_required_parts=tuple(dict.fromkeys(llm_parts)),
        reason=reason,
        pattern_id=top.pattern.pattern_id,
        pattern_status=top.pattern.status,
        exam_validated=top.pattern.exam_validated,
        field_validated=top.pattern.field_validated,
        failure_warnings=top.failure_warnings,
        critic_required=top.critic_required,
        user_decision_fit_score=top.user_decision_fit_score,
    )
    extras = {
        "pattern_matches": [score.to_dict() for score in scores[:5]],
        "skill_gap_report": skill_gap_report,
        "failure_memory_policy": {
            "warnings_reduce_reuse": True,
            "blocking_failures_prevent_direct_reuse": True,
        },
    }
    return decision, extras


def _mode_with_pattern_policy(task: TaskFingerprint, base_mode: str, score: PatternScore) -> str:
    pattern = score.pattern
    if pattern.status == "quarantined":
        return "quarantine_required"
    if score.user_decision_fit_score <= 0.15:
        return "reject_and_solve_fresh"
    if any(_warning_is_blocking(warning) for warning in score.failure_warnings):
        return "reject_and_solve_fresh"
    if score.failure_warnings and base_mode == "direct_reuse":
        return "partial_reuse"
    if task.risk_level == "high":
        if not pattern.field_validated or not score.critic_passed:
            return "reference_only"
        return "direct_reuse" if base_mode == "direct_reuse" else base_mode
    if pattern.status == "draft":
        return "reference_only"
    if pattern.status == "exam_validated":
        return "partial_reuse" if base_mode in {"direct_reuse", "partial_reuse"} else "reference_only"
    if pattern.status == "weakened":
        return "reference_only"
    return base_mode


def user_decision_fit_score(
    task: TaskFingerprint,
    pattern: PatternCandidate,
    user_model: UserDecisionModel | None,
) -> float:
    if user_model is None:
        return 0.5
    if pattern.pattern_id in user_model.rejected_patterns:
        return 0.0
    if pattern.pattern_id in user_model.favored_patterns:
        return 1.0
    pattern_terms = _term_set([pattern.abstract_strategy, pattern.required_conditions, pattern.task_family])
    task_terms = _term_set([task.user_style_markers, task.constraints, task.required_capabilities, task.intent])
    preferred = _term_set(
        [
            user_model.preferred_output_style,
            user_model.recurring_priorities,
            user_model.decision_biases,
            user_model.risk_preference,
        ]
    )
    evidence_terms = task_terms | pattern_terms
    if not preferred:
        return 0.5
    overlap = len(preferred & evidence_terms) / len(preferred)
    return max(0.0, min(1.0, 0.35 + 0.65 * overlap))


def _rank_terms(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    originals: dict[str, str] = {}
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.casefold()
        counts[key] = counts.get(key, 0) + 1
        originals.setdefault(key, text)
    ranked = sorted(counts, key=lambda key: (counts[key], originals[key]), reverse=True)
    return tuple(originals[key] for key in ranked)


def _term_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {part.casefold() for part in value.replace("-", "_").split() if part}
    if isinstance(value, dict):
        return _term_set(json.dumps(value, ensure_ascii=False, sort_keys=True))
    if isinstance(value, Iterable):
        terms: set[str] = set()
        for item in value:
            terms |= _term_set(item)
        return terms
    return _term_set(str(value))


def _real_world_score(outcomes: list[RealWorldOutcome], *, fallback: float | None) -> float | None:
    if not outcomes:
        return fallback
    scores: list[float] = []
    for outcome in outcomes:
        if outcome.quantitative_result is not None:
            scores.append(max(0.0, min(1.0, outcome.quantitative_result)))
        else:
            scores.append(1.0 if outcome.success else 0.0)
    return sum(scores) / len(scores)


def _feedback_score(outcomes: list[RealWorldOutcome]) -> float:
    feedback = [outcome.user_feedback_score / 10.0 for outcome in outcomes if outcome.user_feedback_score is not None]
    if not feedback:
        return 0.5
    return sum(feedback) / len(feedback)


def _failure_penalty(outcomes: list[RealWorldOutcome]) -> float:
    if not outcomes:
        return 0.0
    failures = [outcome for outcome in outcomes if not outcome.success or outcome.error_type]
    penalty = len(failures) / len(outcomes)
    if any((outcome.error_type or "") in CRITICAL_FAILURE_TYPES for outcome in failures):
        penalty += 0.5
    return max(0.0, min(1.0, penalty))


def _severity_rank(severity: str) -> int:
    return {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
        "catastrophic": 5,
        "fatal": 5,
    }.get(severity.casefold(), 2)


def _is_blocking_failure(failure: FailureMemory) -> bool:
    return failure.severity.casefold() in CRITICAL_FAILURE_SEVERITIES or failure.error_type in CRITICAL_FAILURE_TYPES


def _failure_warning(failure: FailureMemory) -> str:
    return f"{failure.error_type}:{failure.severity}:{failure.failure_id}"


def _warning_is_blocking(warning: str) -> bool:
    lowered = warning.casefold()
    return any(marker in lowered for marker in [":critical:", ":fatal:", ":catastrophic:", "domain_mismatch"])
