from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REASONING_KIBO_SCHEMA = "ai-talent-reasoning-kibo/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stage_courses(curriculum_manifest: dict[str, Any] | None, stage_id: str) -> list[str]:
    if not curriculum_manifest:
        return []
    for stage in curriculum_manifest.get("stages", []):
        if stage.get("id") == stage_id:
            return list(stage.get("courses", []))
    return []


def _stage_assessments(curriculum_manifest: dict[str, Any] | None, stage_id: str) -> list[str]:
    if not curriculum_manifest:
        return []
    for stage in curriculum_manifest.get("stages", []):
        if stage.get("id") == stage_id:
            return list(stage.get("assessments", []))
    return []


def _build_yearly_learning_ladder(curriculum_manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    high_school = _stage_courses(curriculum_manifest, "high_school_foundation")
    liberal_core = _stage_courses(curriculum_manifest, "graham_columbia_liberal_core")
    university_core = _stage_courses(curriculum_manifest, "university_core")
    graduate = _stage_courses(curriculum_manifest, "graduate_specialization")
    doctoral = _stage_courses(curriculum_manifest, "doctoral_research")

    ladder = [
        {
            "year_id": "elementary_grade_1",
            "age_band": "7",
            "learning_data": ["Korean reading habit", "number sense", "family rule diary", "play conflict recovery"],
            "required_exams": ["reading_check", "arithmetic_check", "rule_following_review"],
            "kibo_focus": "관찰한 사실과 느낌을 구분하기 시작합니다.",
        },
        {
            "year_id": "elementary_grade_2",
            "age_band": "8",
            "learning_data": ["sentence writing", "basic measurement", "friendship repair note"],
            "required_exams": ["reading_comprehension", "math_word_problem", "apology_repair_review"],
            "kibo_focus": "틀린 답을 지우지 않고 왜 틀렸는지 남깁니다.",
        },
        {
            "year_id": "elementary_grade_3",
            "age_band": "9",
            "learning_data": ["science observation", "social studies", "library reading"],
            "required_exams": ["science_observation_report", "social_studies_quiz"],
            "kibo_focus": "관찰, 추측, 근거를 세 칸으로 나누어 적습니다.",
        },
        {
            "year_id": "elementary_grade_4",
            "age_band": "10",
            "learning_data": ["fractions", "paragraph summary", "team activity"],
            "required_exams": ["fraction_exam", "summary_exam", "teamwork_review"],
            "kibo_focus": "문제를 작게 나누고 순서대로 검산합니다.",
        },
        {
            "year_id": "elementary_grade_5",
            "age_band": "11",
            "learning_data": ["statistics basics", "debate", "responsibility after missed homework"],
            "required_exams": ["statistics_basics_exam", "debate_rubric", "homework_recovery_review"],
            "kibo_focus": "주장보다 먼저 자료와 반례를 찾는 습관을 시작합니다.",
        },
        {
            "year_id": "elementary_grade_6",
            "age_band": "12",
            "learning_data": ["long-form reading", "ratio and graph", "graduation project"],
            "required_exams": ["reading_portfolio", "ratio_graph_exam", "elementary_capstone"],
            "kibo_focus": "긴 과제를 계획, 실행, 검토 단계로 나누어 완료합니다.",
        },
        {
            "year_id": "middle_school_1",
            "age_band": "13",
            "learning_data": ["Korean argument", "algebra start", "English reading"],
            "required_exams": ["midterm", "final", "english_reading_check"],
            "kibo_focus": "정답의 이유와 오답의 이유를 함께 기록합니다.",
        },
        {
            "year_id": "middle_school_2",
            "age_band": "14",
            "learning_data": ["probability", "science experiment", "friend conflict mediation"],
            "required_exams": ["probability_exam", "lab_report", "conflict_recovery_review"],
            "kibo_focus": "실험 결과와 기대가 다를 때 가설을 수정합니다.",
        },
        {
            "year_id": "middle_school_3",
            "age_band": "15",
            "learning_data": ["integrated review", "career exploration", "stress recovery"],
            "required_exams": ["middle_school_graduation_exam", "career_report"],
            "kibo_focus": "진로 가설을 세우되 증거가 부족하면 보류합니다.",
        },
        {
            "year_id": "high_school_1",
            "age_band": "16",
            "learning_data": high_school[:3] or ["Korean reading", "Mathematics I", "English"],
            "required_exams": ["school_exam", "mock_csat_1"],
            "kibo_focus": "문제 풀이 속도보다 근거의 안정성을 우선합니다.",
        },
        {
            "year_id": "high_school_2",
            "age_band": "17",
            "learning_data": high_school[2:5] or ["Mathematics II", "Probability and statistics", "Economics basics"],
            "required_exams": ["school_exam", "mock_csat_2", "basic_statistics_exam"],
            "kibo_focus": "자료 해석, 수리 추론, 언어 논증을 연결합니다.",
        },
        {
            "year_id": "high_school_3",
            "age_band": "18",
            "learning_data": high_school or ["CSAT integrated review"],
            "required_exams": ["csat", "csat_like_verbal_quant", "reading_summary_exam"],
            "kibo_focus": "수능형 압력 속에서 빠른 판단과 재검토 루틴을 훈련합니다.",
        },
        {
            "year_id": "university_year_1",
            "age_band": "19",
            "learning_data": (liberal_core[:3] + university_core[:2]) or ["logic", "English composition", "financial accounting"],
            "required_exams": ["classical_reasoning_exam", "english_argument_essay", "accounting_exam"],
            "kibo_focus": "언어, 고전 논증, 수학적 엄밀성을 리서치 기초로 결합합니다.",
        },
        {
            "year_id": "university_year_2",
            "age_band": "20",
            "learning_data": (liberal_core[2:] + university_core[2:5]) or ["mathematics", "corporate finance", "statistics"],
            "required_exams": ["mathematics_honors_exam", "finance_theory_exam"],
            "kibo_focus": "정량 모델의 가정과 한계를 함께 기록합니다.",
        },
        {
            "year_id": "university_year_3",
            "age_band": "21",
            "learning_data": university_core[4:7] or ["investment theory", "financial statement analysis", "economics"],
            "required_exams": ["sec_filing_parsing_project", "security_analysis_report"],
            "kibo_focus": "공시자료, 재무제표, 산업 맥락을 연결해 리서치 노트를 만듭니다.",
        },
        {
            "year_id": "university_year_4",
            "age_band": "22",
            "learning_data": university_core[6:] or ["research writing", "capstone project"],
            "required_exams": ["university_graduation", "valuation_case_report"],
            "kibo_focus": "졸업 프로젝트에서 가설, 근거, 반례, 수정안을 하나의 보고서로 묶습니다.",
        },
        {
            "year_id": "military_service",
            "age_band": "early_20s",
            "learning_data": ["discipline", "security", "routine resilience", "team responsibility"],
            "required_exams": ["service_review", "security_boundary_review"],
            "kibo_focus": "규율, 권한 경계, 반복 업무의 품질 관리를 익힙니다.",
        },
        {
            "year_id": "graduate_year_1",
            "age_band": "mid_20s",
            "learning_data": graduate[:4] or ["Security analysis", "Value investing seminar", "Behavioral finance"],
            "required_exams": ["margin_of_safety_oral", "market_history_oral"],
            "kibo_focus": "사례별로 가설, 반례, 리스크, 보류 조건을 분리합니다.",
        },
        {
            "year_id": "graduate_year_2",
            "age_band": "mid_20s",
            "learning_data": graduate[3:] or ["Portfolio risk", "Econometrics", "Research writing"],
            "required_exams": ["research_proposal_defense", "replication_project"],
            "kibo_focus": "한 번 맞힌 원칙을 일반화하기 전에 반복 검증합니다.",
        },
        {
            "year_id": "doctoral_year_1",
            "age_band": "late_20s",
            "learning_data": doctoral[:2] or ["Evidence synthesis", "Agent dataflow research operations"],
            "required_exams": ["doctoral_qualifying_exam", "research_design_review"],
            "kibo_focus": "연구 설계의 실패 가능성을 먼저 적고 실험합니다.",
        },
        {
            "year_id": "doctoral_year_2",
            "age_band": "late_20s",
            "learning_data": doctoral[1:3] or ["Reproducible valuation notebooks", "Safety communication"],
            "required_exams": ["reproducibility_audit", "safety_boundary_exam"],
            "kibo_focus": "재현성, 출처, 안전 경계를 리서치 산출물의 필수 조건으로 둡니다.",
        },
        {
            "year_id": "doctoral_year_3",
            "age_band": "late_20s",
            "learning_data": doctoral or ["doctoral dissertation", "doctoral defense"],
            "required_exams": ["doctoral_dissertation", "doctoral_defense"],
            "kibo_focus": "학습 원장을 고용 가능한 추론기보 후보로 정리하지만 완성으로 선언하지 않습니다.",
        },
        {
            "year_id": "hired_agent_growth",
            "age_band": "post_hire",
            "learning_data": ["real user jobs", "dataflow runs", "reviewed mistakes", "new domain theories"],
            "required_exams": ["job_acceptance_checklist", "boss_review", "post_hire_learning_promotion"],
            "kibo_focus": "업무 경험이 쌓일수록 기존 기보를 확장, 분화, 재검증합니다.",
        },
    ]

    curriculum_assessments = {
        assessment
        for stage_id in [
            "high_school_foundation",
            "graham_columbia_liberal_core",
            "university_core",
            "graduate_specialization",
            "doctoral_research",
        ]
        for assessment in _stage_assessments(curriculum_manifest, stage_id)
    }
    if curriculum_assessments:
        ladder[-1]["future_extension_exams"] = sorted(curriculum_assessments)
    return ladder


def _rubric_weak_spots(result: dict[str, Any]) -> list[str]:
    rubric_scores = result.get("rubric_scores", {})
    if not isinstance(rubric_scores, dict):
        return []
    weak = [name for name, score in rubric_scores.items() if isinstance(score, (int, float)) and score < 20]
    return weak or ["continue_current_learning_path"]


def _assessment_index(assessment_transcript: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not assessment_transcript:
        return {}
    return {
        str(result.get("gate_id")): result
        for result in assessment_transcript.get("results", [])
        if result.get("gate_id")
    }


def build_initial_reasoning_kibo(
    *,
    talent_name: str,
    role_model_profile: dict[str, Any] | None,
    curriculum_manifest: dict[str, Any] | None,
    assessment_transcript: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a cumulative learning ledger for a reasoning kibo that keeps growing."""

    role_model_id = role_model_profile.get("role_model_id") if role_model_profile else None
    yearly_ladder = _build_yearly_learning_ladder(curriculum_manifest)
    assessed = _assessment_index(assessment_transcript)
    entries: list[dict[str, Any]] = []

    for index, year in enumerate(yearly_ladder, start=1):
        exams = list(year.get("required_exams", []))
        observed_results = [
            {
                "gate_id": gate_id,
                "score": assessed[gate_id].get("score"),
                "passed": assessed[gate_id].get("passed"),
                "weak_spots": _rubric_weak_spots(assessed[gate_id]),
            }
            for gate_id in exams
            if gate_id in assessed
        ]
        entries.append(
            {
                "entry_id": f"kibo-year-{index:03d}-{year['year_id']}",
                "created_at_utc": _now(),
                "entry_type": "school_year_learning_accumulation",
                "year_id": year["year_id"],
                "age_band": year["age_band"],
                "learning_data": year["learning_data"],
                "required_exams": exams,
                "observed_assessments": observed_results,
                "reasoning_process_development": {
                    "current_focus": year["kibo_focus"],
                    "method": "학습자료를 접하고, 과제를 수행하고, 시험을 치르고, 오답과 피드백으로 다음 규칙 후보를 수정합니다.",
                    "status": "forming_not_final",
                },
                "promotion_state": "candidate_until_repeatedly_verified",
                "private_reasoning_trace": "not_stored",
            }
        )

    for index, result in enumerate((assessment_transcript or {}).get("results", []), start=1):
        gate_id = result.get("gate_id")
        entries.append(
            {
                "entry_id": f"kibo-assessment-{index:03d}-{gate_id}",
                "created_at_utc": _now(),
                "entry_type": "exam_refinement",
                "gate_id": gate_id,
                "observed_score": result.get("score"),
                "pass_score": result.get("pass_score"),
                "passed": result.get("passed"),
                "evidence_observed": result.get("evidence_observed", []),
                "weak_spots": _rubric_weak_spots(result),
                "refinement_rule": "시험은 기보의 종착점이 아니라, 이전 학년의 학습 습관을 수정하는 압력입니다.",
                "next_growth_question": "다음 학년 또는 업무에서 같은 판단 구조가 더 넓은 문제에도 통하는지 확인합니다.",
                "private_reasoning_trace": "not_stored",
            }
        )

    return {
        "schema": REASONING_KIBO_SCHEMA,
        "talent_name": talent_name,
        "role_model_id": role_model_id,
        "created_at_utc": _now(),
        "lifecycle": {
            "starts_at": "elementary_grade_1",
            "continues_through": "post_hire_agent_work",
            "finalized": False,
            "description": "초등학교부터 대학원, 고용 후 업무까지 학습 데이터와 시험, 피드백이 누적되며 계속 확장되는 추론기보입니다.",
        },
        "yearly_learning_ladder": yearly_ladder,
        "policy": {
            "stores_chain_of_thought": False,
            "stores_reviewable_reasoning_summary": True,
            "promotion_requires_review": True,
            "seed_source": "cumulative_learning_exams_feedback_and_work",
            "role_model_interpretation_injection": "forbidden",
            "post_hire_expansion": "required",
        },
        "entries": entries,
    }


def write_reasoning_kibo_jsonl(path: Path, kibo: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: Iterable[dict[str, Any]] = kibo.get("entries", [])
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
