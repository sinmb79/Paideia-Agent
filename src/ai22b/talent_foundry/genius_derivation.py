from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENIUS_DERIVATION_PROFILE_SCHEMA = "paideia-genius-derivation-profile/v1"
GENIUS_DERIVATION_VALIDATION_SCHEMA = "paideia-genius-derivation-profile-validation/v1"

REQUIRED_PRACTICE_CYCLE = [
    "domain_problem_selection",
    "worked_example_compression",
    "timed_trial",
    "error_taxonomy",
    "counterexample_drill",
    "method_distillation",
    "varied_transfer",
]

REQUIRED_SCORECARD_METRICS = [
    "speed_under_constraint",
    "evidence_precision",
    "mistake_recovery",
    "method_stability",
    "varied_transfer_success",
    "originality_under_constraints",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _grade_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [item for item in value.get("records", []) if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _assessment_results(assessment_transcript: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(assessment_transcript, dict):
        return []
    return [item for item in assessment_transcript.get("results", []) if isinstance(item, dict)]


def _track_from_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(blueprint.get("track"))


def _identity_from_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(blueprint.get("identity"))


def _curriculum_topics(curriculum_manifest: dict[str, Any] | None) -> list[str]:
    curriculum = _as_dict(curriculum_manifest)
    topics: list[str] = []
    for key in ["core_topics", "public_sources", "assessment_ladder"]:
        value = curriculum.get(key)
        if isinstance(value, list):
            topics.extend(str(item) for item in value[:12])
        elif isinstance(value, dict):
            for subvalue in value.values():
                if isinstance(subvalue, list):
                    topics.extend(str(item) for item in subvalue[:12])
                elif subvalue:
                    topics.append(str(subvalue))
    for year in _as_list(curriculum.get("yearly_ladder")):
        if isinstance(year, dict):
            topics.extend(str(item) for item in _as_list(year.get("learning_data"))[:4])
    return list(dict.fromkeys(item for item in topics if item))[:24]


def _weak_spots(
    assessment_transcript: dict[str, Any] | None,
    grade_learning_records: dict[str, Any] | list[dict[str, Any]] | None,
    growth_profile: dict[str, Any] | None,
) -> list[str]:
    weak: list[str] = []
    for result in _assessment_results(assessment_transcript):
        weak.extend(str(item) for item in _as_list(result.get("weak_spots")) if item)
        for key, score in _as_dict(result.get("rubric_scores")).items():
            if isinstance(score, (int, float)) and score < 20:
                weak.append(str(key))
    for record in _grade_records(grade_learning_records):
        loop = _as_dict(record.get("feedback_loop"))
        weak.extend(str(item) for item in _as_list(loop.get("observed_weak_spots")) if item)
    asymmetry = _as_dict(_as_dict(growth_profile).get("asymmetry_profile"))
    weak.extend(str(item) for item in _as_list(asymmetry.get("growth_costs")) if item)
    return list(dict.fromkeys(item for item in weak if item and item != "continue_current_learning_path"))[:12]


def _domain_focus(
    blueprint: dict[str, Any],
    curriculum_manifest: dict[str, Any] | None,
    growth_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    track = _track_from_blueprint(blueprint)
    curriculum = _as_dict(curriculum_manifest)
    growth_asymmetry = _as_dict(_as_dict(growth_profile).get("asymmetry_profile"))
    domains: list[str] = []
    if curriculum.get("domain"):
        domains.append(str(curriculum["domain"]))
    domain_obsession = growth_asymmetry.get("domain_obsession")
    if domain_obsession:
        domains.append(str(domain_obsession))
    domains.extend(str(item) for item in _as_list(track.get("domains")) if item)
    domains = list(dict.fromkeys(domains))
    primary = str(track.get("name") or track.get("track_id") or (domains[0] if domains else "domain_specialty"))
    return {
        "primary_domain": primary,
        "track_id": track.get("track_id"),
        "target_role": track.get("target_role"),
        "major_goal": _identity_from_blueprint(blueprint).get("major_goal") or track.get("specialty"),
        "privileged_domains": domains[:8],
        "curriculum_id": curriculum.get("curriculum_id"),
    }


def _practice_ladder(
    grade_learning_records: dict[str, Any] | list[dict[str, Any]] | None,
    assessment_transcript: dict[str, Any] | None,
    curriculum_topics: list[str],
) -> list[dict[str, Any]]:
    ladder: list[dict[str, Any]] = []
    for record in _grade_records(grade_learning_records)[:12]:
        weak_spots = _as_dict(record.get("feedback_loop")).get("observed_weak_spots", [])
        ladder.append(
            {
                "stage_id": str(record.get("year_id") or record.get("education_stage") or "learning_stage"),
                "education_stage": record.get("education_stage"),
                "focus": _as_list(record.get("learning_data"))[:5],
                "linked_exams": _as_list(record.get("required_exams"))[:5],
                "timed_trial": True,
                "compression_task": "turn repeated worked examples into a named chunk and one reusable method rule",
                "weak_spots_to_retest": [str(item) for item in _as_list(weak_spots)[:5]],
            }
        )
    if ladder:
        return ladder

    for result in _assessment_results(assessment_transcript)[:8]:
        ladder.append(
            {
                "stage_id": str(result.get("gate_id") or "assessment_gate"),
                "education_stage": "assessment_gate",
                "focus": [str(result.get("gate_name") or result.get("gate_id") or "domain_exam")],
                "linked_exams": [str(result.get("gate_id") or "domain_exam")],
                "timed_trial": True,
                "compression_task": "compress the passed answer into a reusable method and retest the weak spot",
                "weak_spots_to_retest": _as_list(result.get("weak_spots"))[:5],
            }
        )
    if ladder:
        return ladder

    return [
        {
            "stage_id": "domain_foundation",
            "education_stage": "foundation",
            "focus": curriculum_topics[:5] or ["domain_problem_solving"],
            "linked_exams": ["domain_foundation_exam"],
            "timed_trial": True,
            "compression_task": "build first chunks from sourced examples before broad search",
            "weak_spots_to_retest": [],
        }
    ]


def _pattern_chunks(curriculum_topics: list[str], domain_focus: dict[str, Any]) -> list[dict[str, Any]]:
    seeds = curriculum_topics or _as_list(domain_focus.get("privileged_domains")) or [domain_focus.get("primary_domain")]
    chunks: list[dict[str, Any]] = []
    for index, topic in enumerate(seeds[:10], start=1):
        chunks.append(
            {
                "chunk_id": _stable_id("chunk", topic, index),
                "label": str(topic),
                "purpose": "recognize this pattern quickly and choose a practiced method before exhaustive search",
                "training_method": "worked_example_to_timed_recall_to_counterexample",
            }
        )
    return chunks


def _evidence_counts(
    assessment_transcript: dict[str, Any] | None,
    grade_learning_records: dict[str, Any] | list[dict[str, Any]] | None,
    growth_profile: dict[str, Any] | None,
    *,
    curriculum_topic_count: int,
    practice_ladder_stage_count: int,
) -> dict[str, Any]:
    assessments = _assessment_results(assessment_transcript)
    records = _grade_records(grade_learning_records)
    passed = sum(1 for item in assessments if item.get("passed") is True)
    reviewed_assignments = sum(
        1
        for record in records
        for assignment in _as_list(record.get("assignments"))
        if isinstance(assignment, dict) and assignment.get("status") == "completed_and_reviewed"
    )
    domains = Counter(str(record.get("education_stage") or "unknown") for record in records)
    return {
        "assessment_result_count": len(assessments),
        "passed_assessment_count": passed,
        "grade_learning_record_count": len(records),
        "reviewed_assignment_count": reviewed_assignments,
        "reviewed_transfer_evidence_count": passed + reviewed_assignments,
        "training_evidence_unit_count": passed + reviewed_assignments + len(records),
        "curriculum_topic_count": curriculum_topic_count,
        "practice_ladder_stage_count": practice_ladder_stage_count,
        "growth_profile_schema": _as_dict(growth_profile).get("schema"),
        "growth_profile_present": bool(_as_dict(growth_profile).get("schema")),
        "grade_stage_distribution": [
            {"id": key, "count": count}
            for key, count in domains.most_common(8)
        ],
    }


def build_genius_derivation_profile(
    blueprint: dict[str, Any],
    *,
    curriculum_manifest: dict[str, Any] | None = None,
    assessment_transcript: dict[str, Any] | None = None,
    growth_profile: dict[str, Any] | None = None,
    grade_learning_records: dict[str, Any] | list[dict[str, Any]] | None = None,
    reasoning_kibo: dict[str, Any] | None = None,
    curriculum_backlog: list[Any] | None = None,
    weakness_records: list[dict[str, Any]] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a public-safe domain genius derivation profile.

    The profile is not a claim that an agent is generally superior. It is a
    training contract for uneven, domain-specific excellence under bounded
    context, timed exams, feedback, and reviewed transfer work.
    """

    if blueprint.get("schema") != "ai-talent-training-blueprint/v1":
        raise ValueError("Unsupported training blueprint schema")

    identity = _identity_from_blueprint(blueprint)
    domain_focus = _domain_focus(blueprint, curriculum_manifest, growth_profile)
    topics = _curriculum_topics(curriculum_manifest)
    weak = _weak_spots(assessment_transcript, grade_learning_records, growth_profile)
    practice_ladder = _practice_ladder(grade_learning_records, assessment_transcript, topics)
    chunks = _pattern_chunks(topics, domain_focus)
    reasoning_entries = _as_list(_as_dict(reasoning_kibo).get("entries"))

    profile = {
        "schema": GENIUS_DERIVATION_PROFILE_SCHEMA,
        "created_at_utc": _now(),
        "profile_id": _stable_id(
            "genius-profile",
            identity.get("name"),
            domain_focus.get("track_id"),
            domain_focus.get("curriculum_id"),
        ),
        "status": "candidate_ready_for_training",
        "talent": {
            "name": identity.get("name"),
            "gender": identity.get("gender"),
            "primary_language": identity.get("language", "ko"),
        },
        "domain_focus": domain_focus,
        "design_claim": {
            "genius_definition": (
                "reviewable domain-specific performance produced by training, compression, "
                "timed trials, error correction, and transfer work"
            ),
            "not_general_superintelligence": True,
            "not_model_size_claim": True,
            "not_personality_injection": True,
            "human_capacity_analogy": (
                "same bounded brain-like capacity can behave differently when attention, chunks, "
                "practice pressure, and feedback loops are specialized"
            ),
        },
        "capacity_budget": {
            "strategy": "fixed_capacity_efficiency_over_raw_compute_scaling",
            "attention_allocation": {
                "primary_domain": 0.62,
                "adjacent_support_domains": 0.23,
                "general_life_and_communication": 0.10,
                "novelty_and_external_reference_quarantine": 0.05,
            },
            "search_policy": "practiced_chunks_and_minimal_needed_research_before_broad_search",
            "context_policy": "bounded_hot_context_with_reviewed_memory_only",
        },
        "deliberate_practice_program": {
            "cycle": REQUIRED_PRACTICE_CYCLE,
            "ladder": practice_ladder,
            "daily_training_rule": (
                "one focused domain problem, one timed attempt, one error note, "
                "one counterexample, one method revision"
            ),
            "promotion_rule": "only reviewed exams or verified work outcomes can harden a method",
        },
        "cognitive_kibo_targets": {
            "pattern_chunks": chunks,
            "compression_rules": [
                "name repeated evidence patterns as reusable chunks",
                "prefer a narrow practiced method when it fits the task",
                "record the condition where the method fails",
                "turn every serious error into a retest item",
            ],
            "quality_controls": [
                "source_before_claim",
                "counterexample_before_confidence",
                "time_box_before_broad_search",
                "reviewed_work_before_memory_promotion",
            ],
            "reasoning_entry_count": len(reasoning_entries),
        },
        "unevenness_profile": {
            "specialization_is_allowed_to_create_asymmetry": True,
            "expected_strength_biases": _as_list(_as_dict(_as_dict(growth_profile).get("asymmetry_profile")).get("strength_biases")),
            "accepted_tradeoffs": [
                "less breadth-first curiosity during high-pressure domain work",
                "slower response in unrelated domains when safety or evidence is thin",
                "stronger skepticism toward methods outside the trained major",
            ],
            "weakness_guardrails": weak
            or [
                "do not mistake narrow excellence for universal judgment",
                "ask for missing evidence outside the trained domain",
            ],
            "minimum_general_floor": [
                "safety boundaries",
                "honest uncertainty",
                "owner instruction priority",
                "basic communication clarity",
            ],
        },
        "scorecard": {
            "metrics": [
                {
                    "id": metric,
                    "target": "reviewed_improvement_over_repeated_trials",
                    "promotion_source": "exam_feedback_or_verified_work",
                }
                for metric in REQUIRED_SCORECARD_METRICS
            ],
            "genius_candidate_threshold": {
                "minimum_reviewed_trials": 8,
                "minimum_average_score": 90,
                "requires_varied_transfer": True,
                "requires_documented_weaknesses": True,
            },
        },
        "evidence_summary": _evidence_counts(
            assessment_transcript,
            grade_learning_records,
            growth_profile,
            curriculum_topic_count=len(topics),
            practice_ladder_stage_count=len(practice_ladder),
        ),
        "curriculum_backlog": _as_list(curriculum_backlog),
        "weakness_records": [item for item in _as_list(weakness_records) if isinstance(item, dict)],
        "research_basis": [
            {
                "id": "neural_efficiency",
                "use": "same capacity can differ by efficiency and task-focused activation",
                "source": "https://pubmed.ncbi.nlm.nih.gov/19580915/",
            },
            {
                "id": "deliberate_practice",
                "use": "expert performance requires structured practice, feedback, and increasing challenge",
                "source": "https://pubmed.ncbi.nlm.nih.gov/18778378/",
            },
            {
                "id": "chunking_expertise",
                "use": "experts compress familiar patterns into retrievable chunks",
                "source": "https://doi.org/10.1016/0010-0285(73)90004-2",
            },
            {
                "id": "reflexion_language_agents",
                "use": "verbal feedback can improve future agent decisions without weight updates",
                "source": "https://arxiv.org/abs/2303.11366",
            },
        ],
        "public_safe": {
            "network_call_performed": False,
            "private_reasoning_trace": "not_stored",
            "hidden_chain_of_thought": "forbidden",
            "raw_external_skill_text_promoted": False,
            "secret_values_exported": False,
        },
    }
    profile["validation"] = validate_genius_derivation_profile(profile)
    profile["status"] = (
        "verified_training_contract"
        if profile["validation"]["passed"]
        else profile["validation"]["status"]
    )
    if output_path is not None:
        write_genius_derivation_profile(output_path, profile)
    return profile


def validate_genius_derivation_profile(profile: dict[str, Any]) -> dict[str, Any]:
    cycle = _as_list(_as_dict(profile.get("deliberate_practice_program")).get("cycle"))
    scorecard = _as_dict(profile.get("scorecard"))
    metric_ids = {
        str(item.get("id"))
        for item in _as_list(scorecard.get("metrics"))
        if isinstance(item, dict) and item.get("id")
    }
    public_safe = _as_dict(profile.get("public_safe"))
    design_claim = _as_dict(profile.get("design_claim"))
    capacity = _as_dict(profile.get("capacity_budget"))
    unevenness = _as_dict(profile.get("unevenness_profile"))
    evidence = _as_dict(profile.get("evidence_summary"))
    domain_focus = _as_dict(profile.get("domain_focus"))
    evidence_check_ids = {
        "training_evidence_present",
        "reviewed_transfer_or_assessment_present",
        "growth_or_grade_learning_evidence_present",
        "domain_scope_or_curriculum_evidence_present",
    }
    checks = {
        "schema": profile.get("schema") == GENIUS_DERIVATION_PROFILE_SCHEMA,
        "domain_focus_present": bool(domain_focus.get("primary_domain")),
        "genius_not_general_superintelligence": design_claim.get("not_general_superintelligence") is True,
        "genius_not_model_size_claim": design_claim.get("not_model_size_claim") is True,
        "fixed_capacity_strategy": capacity.get("strategy") == "fixed_capacity_efficiency_over_raw_compute_scaling",
        "training_evidence_present": int(evidence.get("training_evidence_unit_count") or 0) > 0,
        "reviewed_transfer_or_assessment_present": int(evidence.get("reviewed_transfer_evidence_count") or 0) > 0,
        "growth_or_grade_learning_evidence_present": (
            bool(evidence.get("growth_profile_present"))
            or int(evidence.get("grade_learning_record_count") or 0) > 0
        ),
        "domain_scope_or_curriculum_evidence_present": (
            bool(domain_focus.get("privileged_domains"))
            or int(evidence.get("curriculum_topic_count") or 0) > 0
        ),
        "practice_cycle_complete": cycle == REQUIRED_PRACTICE_CYCLE,
        "timed_trials_required": "timed_trial" in cycle,
        "method_distillation_required": "method_distillation" in cycle,
        "varied_transfer_required": "varied_transfer" in cycle,
        "scorecard_complete": set(REQUIRED_SCORECARD_METRICS) <= metric_ids,
        "asymmetry_explicit": unevenness.get("specialization_is_allowed_to_create_asymmetry") is True,
        "weakness_guardrails_present": bool(_as_list(unevenness.get("weakness_guardrails"))),
        "no_network_call": public_safe.get("network_call_performed") is False,
        "no_private_reasoning_trace": public_safe.get("private_reasoning_trace") == "not_stored",
        "no_external_skill_raw_promotion": public_safe.get("raw_external_skill_text_promoted") is False,
    }
    failed = [check_id for check_id, passed in checks.items() if not passed]
    status = "passed"
    if failed:
        status = "needs_training_evidence" if any(item in evidence_check_ids for item in failed) else "failed"
    return {
        "schema": GENIUS_DERIVATION_VALIDATION_SCHEMA,
        "status": status,
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
    }


def write_genius_derivation_profile(path: Path, profile: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def read_genius_derivation_profile(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
