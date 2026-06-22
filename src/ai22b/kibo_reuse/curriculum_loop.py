from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

from .models import (
    AdaptiveExam,
    CurriculumPlan,
    FailureMemory,
    SkillEdge,
    WeaknessRecord,
)
from .skill_graph import load_skill_graph


WEAKNESS_DETECTION_SCHEMA = "paideia-weakness-detection-report/v1"
CURRICULUM_GENERATION_SCHEMA = "paideia-curriculum-generation-report/v1"
ADAPTIVE_EXAM_GENERATION_SCHEMA = "paideia-adaptive-exam-generation-report/v1"
CURRICULUM_COMPLETION_SCHEMA = "paideia-curriculum-completion/v1"
CURRICULUM_REPORT_SCHEMA = "paideia-curriculum-feedback-report/v1"

ERROR_WEAKNESS_MAP: dict[str, tuple[str, str]] = {
    "freshness_error": ("fresh_external_data", "freshness_gap"),
    "macro_ignored": ("macro_regime_analysis", "knowledge_gap"),
    "market_regime_shift": ("macro_regime_analysis", "transfer_gap"),
    "overgeneralization": ("transfer_reasoning", "transfer_gap"),
    "domain_mismatch": ("domain_boundary_detection", "transfer_gap"),
    "risk_underestimated": ("risk_assessment", "risk_gap"),
    "missing_counterargument": ("counterargument_review", "counterargument_gap"),
    "user_style_mismatch": ("user_decision_fit", "reasoning_gap"),
}

SEVERITY_MAP = {
    "low": 0.25,
    "medium": 0.50,
    "high": 0.75,
    "critical": 0.90,
    "catastrophic": 0.95,
    "fatal": 1.00,
}
HIGH_WEAKNESS_THRESHOLD = SEVERITY_MAP["high"]

LESSON_MAP: dict[str, tuple[str, ...]] = {
    "freshness_gap": ("source_recency_checks", "current_data_verification", "staleness_risk_review"),
    "knowledge_gap": ("core_domain_principles", "case_examples", "boundary_conditions"),
    "reasoning_gap": ("premise_tracking", "evidence_to_claim_mapping", "decision_trace_review"),
    "risk_gap": ("downside_mapping", "failure_pre_mortem", "risk_sizing"),
    "transfer_gap": ("near_transfer_cases", "far_transfer_limits", "domain_boundary_review"),
    "counterargument_gap": ("opposing_case_generation", "assumption_attack", "red_team_summary"),
}

GOAL_MAP: dict[str, tuple[str, ...]] = {
    "macro_regime_analysis": ("yield_curve", "interest_rate_cycles", "liquidity_analysis", "inflation_regimes"),
    "fresh_external_data": ("freshness_window_selection", "source_timestamp_review", "current_data_citation"),
    "risk_assessment": ("downside_risk", "sensitivity_analysis", "loss_scenario_design"),
    "counterargument_review": ("steelman_opposition", "missing_counterevidence", "assumption_register"),
}


def load_weakness_records(paths: Iterable[Path] | None) -> list[WeaknessRecord]:
    records: list[WeaknessRecord] = []
    for path in paths or []:
        if not path.exists():
            continue
        rows = _read_json_rows(path, collection_key="weaknesses")
        for row in rows:
            if isinstance(row, dict):
                records.append(WeaknessRecord.from_dict(row))
    return records


def load_curriculum_plans(paths: Iterable[Path] | None) -> list[CurriculumPlan]:
    plans: list[CurriculumPlan] = []
    for path in paths or []:
        if not path.exists():
            continue
        rows = _read_json_rows(path, collection_key="curricula")
        for row in rows:
            if isinstance(row, dict):
                plans.append(CurriculumPlan.from_dict(row))
    return plans


def load_adaptive_exams(paths: Iterable[Path] | None) -> list[AdaptiveExam]:
    exams: list[AdaptiveExam] = []
    for path in paths or []:
        if not path.exists():
            continue
        rows = _read_json_rows(path, collection_key="adaptive_exams")
        for row in rows:
            if isinstance(row, dict):
                exams.append(AdaptiveExam.from_dict(row))
    return exams


def detect_weaknesses(
    failures: Iterable[FailureMemory],
    *,
    owner: str = "Boss",
    domain: str = "general",
    existing_weaknesses: Iterable[WeaknessRecord] = (),
) -> list[WeaknessRecord]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for failure in failures:
        skill_id, weakness_type = weakness_mapping_for_error(failure.error_type)
        key = (owner, domain, skill_id, weakness_type)
        current = grouped.setdefault(key, {"evidence_refs": [], "severity": 0.0, "recurrence_count": 0})
        current["evidence_refs"].append(failure.failure_id)
        current["severity"] = max(current["severity"], severity_value(failure.severity))
        current["recurrence_count"] += 1
    for weakness in existing_weaknesses:
        key = (weakness.owner, weakness.domain, weakness.skill_id, weakness.weakness_type)
        current = grouped.setdefault(key, {"evidence_refs": [], "severity": 0.0, "recurrence_count": 0})
        current["evidence_refs"].extend(weakness.evidence_refs)
        current["severity"] = max(current["severity"], weakness.severity)
        current["recurrence_count"] = max(current["recurrence_count"], weakness.recurrence_count)

    records: list[WeaknessRecord] = []
    for (record_owner, record_domain, skill_id, weakness_type), values in sorted(grouped.items()):
        evidence_refs = tuple(dict.fromkeys(str(item) for item in values["evidence_refs"] if str(item)))
        recurrence_count = max(int(values["recurrence_count"]), len(evidence_refs))
        severity = min(1.0, float(values["severity"]) + min(0.20, 0.05 * max(0, recurrence_count - 1)))
        records.append(
            WeaknessRecord(
                weakness_id=_stable_id("weakness", record_owner, record_domain, skill_id, weakness_type),
                owner=record_owner,
                domain=record_domain,
                skill_id=skill_id,
                weakness_type=weakness_type,
                evidence_refs=evidence_refs,
                severity=severity,
                recurrence_count=recurrence_count,
            )
        )
    return records


def build_weakness_detection_report(
    failures: Iterable[FailureMemory],
    *,
    owner: str = "Boss",
    domain: str = "general",
    existing_weaknesses: Iterable[WeaknessRecord] = (),
) -> dict[str, Any]:
    weaknesses = detect_weaknesses(
        failures,
        owner=owner,
        domain=domain,
        existing_weaknesses=existing_weaknesses,
    )
    return {
        "schema": WEAKNESS_DETECTION_SCHEMA,
        "owner": owner,
        "domain": domain,
        "weakness_count": len(weaknesses),
        "weaknesses": [weakness.to_dict() for weakness in weaknesses],
        "policy": {
            "failures_are_training_opportunities": True,
            "hidden_chain_of_thought_used": False,
            "local_first_storage": True,
        },
    }


def generate_curriculum_plan(
    weakness: WeaknessRecord,
    *,
    related_skills: Iterable[str] = (),
) -> CurriculumPlan:
    goals = _unique((weakness.skill_id, *GOAL_MAP.get(weakness.skill_id, ()), *related_skills))
    lessons = _unique((*LESSON_MAP.get(weakness.weakness_type, ("diagnostic_review",)), *GOAL_MAP.get(weakness.skill_id, ())))
    target_score = target_score_for_weakness(weakness)
    return CurriculumPlan(
        curriculum_id=_stable_id("curriculum", weakness.weakness_id, weakness.recurrence_count),
        weakness_id=weakness.weakness_id,
        domain=weakness.domain,
        learning_goals=goals,
        lesson_units=lessons,
        exam_requirements=(
            f"score_at_least_{target_score:.2f}",
            "include_failure_memory_prevention_rule",
            "pass_transfer_case_without_repeating_trigger",
        ),
        target_score=target_score,
    )


def build_curriculum_generation_report(
    weaknesses: Iterable[WeaknessRecord],
    *,
    skill_graph_path: Path | None = None,
) -> dict[str, Any]:
    _nodes, edges = load_skill_graph(skill_graph_path)
    edge_map = related_skill_map(edges)
    curricula = [
        generate_curriculum_plan(weakness, related_skills=edge_map.get(weakness.skill_id, ()))
        for weakness in weaknesses
    ]
    return {
        "schema": CURRICULUM_GENERATION_SCHEMA,
        "curriculum_count": len(curricula),
        "curricula": [curriculum.to_dict() for curriculum in curricula],
        "skill_graph_used": skill_graph_path is not None,
        "policy": {
            "generated_from_weakness_records": True,
            "external_database_required": False,
        },
    }


def generate_adaptive_exam(
    curriculum: CurriculumPlan,
    *,
    weakness: WeaknessRecord | None = None,
    recent_improvement: bool = False,
) -> AdaptiveExam:
    difficulty = _difficulty(weakness, recent_improvement=recent_improvement)
    count = _question_count(weakness, recent_improvement=recent_improvement)
    seeds = list(curriculum.learning_goals or curriculum.lesson_units or ("target_skill",))
    questions: list[str] = []
    for index in range(count):
        topic = seeds[index % len(seeds)]
        if difficulty == "maintenance":
            question = f"Maintenance check {index + 1}: apply {topic} and state the verification signal."
        elif difficulty == "advanced":
            question = f"Advanced transfer {index + 1}: solve a novel case requiring {topic} and one counterargument."
        elif difficulty == "remediation":
            question = f"Remediation {index + 1}: identify the prior failure trigger for {topic} and prevent it."
        else:
            question = f"Standard application {index + 1}: use {topic} with evidence and risk checks."
        questions.append(question)
    return AdaptiveExam(
        exam_id=_stable_id("adaptive-exam", curriculum.curriculum_id, difficulty, count),
        curriculum_id=curriculum.curriculum_id,
        difficulty=difficulty,
        questions=tuple(questions),
    )


def build_adaptive_exam_report(
    curriculum: CurriculumPlan,
    *,
    weakness: WeaknessRecord | None = None,
    recent_improvement: bool = False,
) -> dict[str, Any]:
    exam = generate_adaptive_exam(
        curriculum,
        weakness=weakness,
        recent_improvement=recent_improvement,
    )
    return {
        "schema": ADAPTIVE_EXAM_GENERATION_SCHEMA,
        "exam": exam.to_dict(),
        "policy": {
            "higher_severity_gets_more_questions": True,
            "repeated_failure_increases_difficulty": True,
            "recent_improvement_uses_maintenance_exam": recent_improvement,
        },
    }


def apply_curriculum_completion(
    weakness: WeaknessRecord,
    *,
    passed: bool,
    score: float,
    target_score: float | None = None,
    evidence_refs: Iterable[str] = (),
) -> dict[str, Any]:
    normalized_score = max(0.0, min(1.0, float(score)))
    target = max(0.0, min(1.0, float(target_score))) if target_score is not None else 0.75
    completion_refs = tuple(str(ref) for ref in evidence_refs if str(ref))
    updated_refs = tuple(dict.fromkeys((*weakness.evidence_refs, *completion_refs)))
    effective_passed = bool(passed and normalized_score >= target)
    if effective_passed:
        updated = replace(
            weakness,
            evidence_refs=updated_refs,
            severity=max(0.0, weakness.severity - max(0.10, 0.25 * normalized_score)),
            recurrence_count=max(0, weakness.recurrence_count - 1),
        )
        action = "weakness_reduced"
    else:
        updated = replace(
            weakness,
            evidence_refs=updated_refs,
            severity=min(1.0, weakness.severity + 0.10),
            recurrence_count=weakness.recurrence_count + 1,
        )
        action = "weakness_increased"
    return {
        "schema": CURRICULUM_COMPLETION_SCHEMA,
        "weakness_id": weakness.weakness_id,
        "passed": passed,
        "effective_passed": effective_passed,
        "score": round(normalized_score, 4),
        "target_score": round(target, 4),
        "evidence_refs": list(completion_refs),
        "action": action,
        "updated_weakness": updated.to_dict(),
    }


def build_curriculum_report(
    *,
    weaknesses: Iterable[WeaknessRecord],
    curricula: Iterable[CurriculumPlan],
    exams: Iterable[AdaptiveExam] = (),
) -> dict[str, Any]:
    weakness_rows = list(weaknesses)
    curriculum_rows = list(curricula)
    exam_rows = list(exams)
    severe = [weakness for weakness in weakness_rows if weakness.severity >= HIGH_WEAKNESS_THRESHOLD]
    repeated = [weakness for weakness in weakness_rows if weakness.recurrence_count >= 3]
    return {
        "schema": CURRICULUM_REPORT_SCHEMA,
        "summary": {
            "weakness_count": len(weakness_rows),
            "curriculum_count": len(curriculum_rows),
            "adaptive_exam_count": len(exam_rows),
            "high_severity_weakness_count": len(severe),
            "repeated_weakness_count": len(repeated),
        },
        "weaknesses": [weakness.to_dict() for weakness in weakness_rows],
        "curricula": [curriculum.to_dict() for curriculum in curriculum_rows],
        "adaptive_exams": [exam.to_dict() for exam in exam_rows],
        "routing_policy": {
            "direct_reuse_blocked_by_high_severity": bool(severe),
            "pattern_weakened_after_three_repeats": bool(repeated),
            "remediation_required_before_reinforcement": True,
        },
    }


def related_skill_map(edges: Iterable[SkillEdge]) -> dict[str, tuple[str, ...]]:
    related: dict[str, list[str]] = {}
    for edge in edges:
        if edge.weight <= 0:
            continue
        related.setdefault(edge.from_skill, []).append(edge.to_skill)
        if edge.relation in {"supports", "prerequisite", "related"}:
            related.setdefault(edge.to_skill, []).append(edge.from_skill)
    return {key: tuple(dict.fromkeys(values)) for key, values in related.items()}


def weakness_mapping_for_error(error_type: str) -> tuple[str, str]:
    normalized = str(error_type or "").casefold()
    if normalized in ERROR_WEAKNESS_MAP:
        return ERROR_WEAKNESS_MAP[normalized]
    if "fresh" in normalized or "stale" in normalized:
        return ("fresh_external_data", "freshness_gap")
    if "risk" in normalized:
        return ("risk_assessment", "risk_gap")
    if "counter" in normalized or "objection" in normalized:
        return ("counterargument_review", "counterargument_gap")
    if "domain" in normalized or "transfer" in normalized:
        return ("transfer_reasoning", "transfer_gap")
    if "knowledge" in normalized or "ignored" in normalized:
        return ("domain_knowledge", "knowledge_gap")
    return ("general_reasoning", "reasoning_gap")


def severity_value(severity: str | float | int) -> float:
    if isinstance(severity, (int, float)) and not isinstance(severity, bool):
        return max(0.0, min(1.0, float(severity)))
    return SEVERITY_MAP.get(str(severity or "medium").casefold(), 0.50)


def weakness_blocks_direct_reuse(weakness: WeaknessRecord) -> bool:
    return weakness.severity >= HIGH_WEAKNESS_THRESHOLD or weakness.recurrence_count >= 3


def target_score_for_weakness(weakness: WeaknessRecord) -> float:
    if weakness.severity >= HIGH_WEAKNESS_THRESHOLD or weakness.recurrence_count >= 3:
        return 0.85
    if weakness.severity >= 0.6:
        return 0.80
    return 0.75


def _read_json_rows(path: Path, *, collection_key: str) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if not isinstance(row, dict):
                raise ValueError(f"JSONL row must be an object at {path}:{line_number}")
            rows.append(row)
        return rows
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and payload.get("schema") in {
        "paideia-weakness-record/v1",
        "paideia-curriculum-plan/v1",
        "paideia-adaptive-exam/v1",
    }:
        return [payload]
    if isinstance(payload, dict) and payload.get("schema") == CURRICULUM_COMPLETION_SCHEMA:
        updated_weakness = payload.get("updated_weakness")
        if not isinstance(updated_weakness, dict):
            raise ValueError(f"{path} does not contain updated_weakness")
        return [updated_weakness]
    if isinstance(payload, dict) and isinstance(payload.get("exam"), dict):
        return [payload["exam"]]
    if isinstance(payload, dict):
        rows = payload.get(collection_key, [])
        return [row for row in rows if isinstance(row, dict)]
    return []


def _difficulty(weakness: WeaknessRecord | None, *, recent_improvement: bool) -> str:
    if recent_improvement:
        return "maintenance"
    if weakness is None:
        return "standard"
    if weakness.recurrence_count >= 3 or weakness.severity >= HIGH_WEAKNESS_THRESHOLD:
        return "remediation"
    if weakness.severity >= 0.6:
        return "advanced"
    return "standard"


def _question_count(weakness: WeaknessRecord | None, *, recent_improvement: bool) -> int:
    if recent_improvement:
        return 3
    if weakness is None:
        return 4
    count = 3
    if weakness.severity >= 0.6:
        count += 1
    if weakness.severity >= HIGH_WEAKNESS_THRESHOLD:
        count += 1
    count += min(3, max(0, weakness.recurrence_count - 1))
    return count


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
