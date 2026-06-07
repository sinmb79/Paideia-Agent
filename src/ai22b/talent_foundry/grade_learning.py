from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GRADE_LEARNING_RECORDS_SCHEMA = "paideia-grade-learning-records/v1"
GRADE_LEARNING_RECORD_SCHEMA = "paideia-grade-learning-record/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _assessment_index(assessment_transcript: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not assessment_transcript:
        return {}
    return {
        str(result.get("gate_id")): result
        for result in assessment_transcript.get("results", [])
        if result.get("gate_id")
    }


def _entries_by_year(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        year_id = entry.get("year_id")
        if year_id:
            indexed.setdefault(str(year_id), []).append(entry)
    return indexed


def _entries_by_gate(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        gate_id = entry.get("gate_id")
        if gate_id:
            indexed.setdefault(str(gate_id), []).append(entry)
    return indexed


def _age_candidates(age_band: str) -> set[int]:
    numbers = {int(item) for item in re.findall(r"\d+", age_band)}
    if numbers:
        return {age for age in numbers if 0 <= age <= 20} or {20}
    if "early" in age_band:
        return {20}
    if "mid" in age_band or "late" in age_band or "post" in age_band:
        return {20}
    return set()


def _education_stage(year_id: str) -> str:
    if year_id.startswith("elementary"):
        return "elementary_school"
    if year_id.startswith("middle"):
        return "middle_school"
    if year_id.startswith("high"):
        return "high_school"
    if year_id.startswith("university"):
        return "university"
    if year_id.startswith("graduate"):
        return "graduate_school"
    if year_id.startswith("doctoral"):
        return "doctoral_research"
    if year_id == "military_service":
        return "military_service"
    return "post_hire_growth"


def _event_score(event: dict[str, Any], *, ages: set[int], year_id: str, index: int) -> tuple[int, int]:
    score = 0
    age = event.get("age_year")
    if isinstance(age, int) and age in ages:
        score += 6
    stage_id = str(event.get("stage_id") or "")
    if "elementary" in year_id and "elementary" in stage_id:
        score += 3
    if "middle" in year_id and "middle_school" in stage_id:
        score += 3
    if "high" in year_id and "high_school" in stage_id:
        score += 3
    if "university" in year_id and "university" in stage_id:
        score += 3
    if year_id in {"military_service", "graduate_year_1", "graduate_year_2"} and age == 20:
        score += 2
    domain = str(event.get("domain") or "")
    if domain in {"school_challenge", "domain_obsession"}:
        score += 3
    if domain in {"peer_world", "emotional_recovery"}:
        score += 2
    score += min(int(event.get("stress_level") or 0), 5)
    return (-score, index)


def _select_life_trace_links(
    events: list[dict[str, Any]] | None,
    *,
    year_id: str,
    age_band: str,
    limit: int = 4,
) -> list[dict[str, Any]]:
    if not events:
        return []
    ages = _age_candidates(age_band)
    ranked = sorted(
        enumerate(events),
        key=lambda item: _event_score(item[1], ages=ages, year_id=year_id, index=item[0]),
    )
    links: list[dict[str, Any]] = []
    seen_domains: set[str] = set()
    for _index, event in ranked:
        domain = str(event.get("domain") or "life_event")
        if len(links) >= limit:
            break
        if domain in seen_domains and len(links) < limit - 1:
            continue
        seen_domains.add(domain)
        links.append(
            {
                "event_id": event.get("event_id"),
                "age_year": event.get("age_year"),
                "stage_id": event.get("stage_id"),
                "domain": domain,
                "stress_level": event.get("stress_level"),
                "learning_delta": event.get("learning_delta"),
                "recovery": event.get("recovery"),
            }
        )
    return links


def _assignment_cards(year: dict[str, Any], observed_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observed_gates = {str(result.get("gate_id")) for result in observed_results if result.get("gate_id")}
    topics = [str(item) for item in year.get("learning_data", [])][:4]
    exams = [str(item) for item in year.get("required_exams", [])]
    assignments: list[dict[str, Any]] = []
    for index, topic in enumerate(topics or [year.get("year_id", "learning_cycle")], start=1):
        linked_gate = exams[(index - 1) % len(exams)] if exams else None
        assignments.append(
            {
                "assignment_id": f"{year['year_id']}-assignment-{index:02d}",
                "topic": topic,
                "linked_exam": linked_gate,
                "expected_evidence": [
                    "work_product",
                    "feedback_note",
                    "revision_log",
                ],
                "status": "completed_and_reviewed" if linked_gate in observed_gates else "scheduled_or_synthetic",
            }
        )
    return assignments


def _stressors(year_id: str, observed_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = [
        {
            "type": "exam_pressure",
            "description": "Convert pressure into a visible work product, not a personality label.",
        },
        {
            "type": "feedback_acceptance",
            "description": "Record weak spots and revise the next study routine.",
        },
    ]
    if "elementary" in year_id or "middle" in year_id:
        base.append(
            {
                "type": "peer_or_homework_repair",
                "description": "Practice apology, missed-homework recovery, and friend-conflict repair.",
            }
        )
    if "university" in year_id or "graduate" in year_id or "doctoral" in year_id:
        base.append(
            {
                "type": "source_and_counterexample_stress",
                "description": "Find primary sources and counterexamples before accepting a conclusion.",
            }
        )
    if any(not result.get("passed", False) for result in observed_results):
        base.append(
            {
                "type": "failed_gate_recovery",
                "description": "Retake or revise before the next promotion checkpoint.",
            }
        )
    return base


def _feedback_loop(
    *,
    year: dict[str, Any],
    observed_results: list[dict[str, Any]],
    life_links: list[dict[str, Any]],
) -> dict[str, Any]:
    weak_spots = []
    for result in observed_results:
        weak_spots.extend(result.get("weak_spots", []))
    weak_spots = list(dict.fromkeys(str(item) for item in weak_spots if item))
    if not weak_spots:
        weak_spots = ["continue_current_learning_path"]
    next_exam = (year.get("required_exams") or ["next_review"])[0]
    return {
        "cycle": ["study_material", "assignment", "exam", "feedback", "revised_principle"],
        "observed_weak_spots": weak_spots,
        "life_trace_pressure_count": len(life_links),
        "revised_principle_summary": (
            "Use exam results and age-appropriate stress events to revise the next visible learning habit."
        ),
        "next_practice": f"Prepare {next_exam} with one evidence note, one counterexample, and one revision log.",
        "private_reasoning_trace": "not_stored",
    }


def build_grade_learning_records(
    *,
    talent_name: str,
    curriculum_manifest: dict[str, Any] | None,
    assessment_transcript: dict[str, Any] | None,
    reasoning_kibo: dict[str, Any] | None,
    life_trace_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create reviewable yearly education records linked to exams and the Reasoning Ledger."""

    ladder = list((reasoning_kibo or {}).get("yearly_learning_ladder", []))
    kibo_entries = list((reasoning_kibo or {}).get("entries", []))
    by_year = _entries_by_year(kibo_entries)
    by_gate = _entries_by_gate(kibo_entries)
    assessments = _assessment_index(assessment_transcript)
    records: list[dict[str, Any]] = []

    for sequence, year in enumerate(ladder, start=1):
        year_id = str(year.get("year_id") or f"year_{sequence:03d}")
        required_exams = [str(item) for item in year.get("required_exams", [])]
        observed_results = [
            {
                "gate_id": gate_id,
                "gate_name": assessments[gate_id].get("gate_name"),
                "score": assessments[gate_id].get("score"),
                "pass_score": assessments[gate_id].get("pass_score"),
                "passed": assessments[gate_id].get("passed"),
                "evidence_observed": assessments[gate_id].get("evidence_observed", []),
                "weak_spots": [
                    key
                    for key, score in assessments[gate_id].get("rubric_scores", {}).items()
                    if isinstance(score, (int, float)) and score < 20
                ]
                or ["continue_current_learning_path"],
            }
            for gate_id in required_exams
            if gate_id in assessments
        ]
        ledger_updates = [
            str(entry.get("entry_id"))
            for entry in by_year.get(year_id, [])
            if entry.get("entry_id")
        ]
        for gate_id in required_exams:
            ledger_updates.extend(
                str(entry.get("entry_id"))
                for entry in by_gate.get(gate_id, [])
                if entry.get("entry_id")
            )
        ledger_updates = list(dict.fromkeys(ledger_updates))
        life_links = _select_life_trace_links(
            life_trace_events,
            year_id=year_id,
            age_band=str(year.get("age_band") or ""),
        )
        assignments = _assignment_cards(year, observed_results)
        records.append(
            {
                "schema": GRADE_LEARNING_RECORD_SCHEMA,
                "record_id": _stable_id("grade-learning", talent_name, year_id),
                "sequence": sequence,
                "talent_name": talent_name,
                "year_id": year_id,
                "education_stage": _education_stage(year_id),
                "age_band": year.get("age_band"),
                "learning_data": list(year.get("learning_data", [])),
                "required_exams": required_exams,
                "assignments": assignments,
                "stressors": _stressors(year_id, observed_results),
                "observed_assessments": observed_results,
                "life_trace_links": life_links,
                "reasoning_ledger_updates": ledger_updates,
                "feedback_loop": _feedback_loop(
                    year=year,
                    observed_results=observed_results,
                    life_links=life_links,
                ),
                "promotion_state": (
                    "reviewed_with_exam_evidence"
                    if observed_results
                    else "forming_until_assessed"
                ),
                "private_reasoning_trace": "not_stored",
            }
        )

    assessment_link_count = sum(len(record["observed_assessments"]) for record in records)
    life_trace_link_count = sum(len(record["life_trace_links"]) for record in records)
    reasoning_ledger_link_count = sum(len(record["reasoning_ledger_updates"]) for record in records)
    return {
        "schema": GRADE_LEARNING_RECORDS_SCHEMA,
        "created_at_utc": _now(),
        "talent_name": talent_name,
        "curriculum_id": (curriculum_manifest or {}).get("curriculum_id"),
        "summary": {
            "record_count": len(records),
            "assessment_link_count": assessment_link_count,
            "life_trace_link_count": life_trace_link_count,
            "reasoning_ledger_link_count": reasoning_ledger_link_count,
            "grade_loop": "learning_data_to_assignment_to_exam_to_feedback_to_reasoning_ledger",
        },
        "policy": {
            "stores_chain_of_thought": False,
            "stores_reviewable_reasoning_summary": True,
            "uses_role_model_personality_keywords": False,
            "uses_exam_and_assignment_outcomes": True,
            "continues_after_hire": True,
            "public_safe": True,
        },
        "records": records,
    }


def write_grade_learning_records(path: Path, records: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
