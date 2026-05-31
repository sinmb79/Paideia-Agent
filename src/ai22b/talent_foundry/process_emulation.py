from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


PROCESS_EMULATION_SCHEMA = "ai-talent-role-model-process-emulation/v1"


def build_process_emulation_plan(
    *,
    role_model_profile: dict[str, Any],
    curriculum_manifest: dict[str, Any],
    saju_seed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stages = curriculum_manifest.get("stages", [])
    assessment_ladder: list[dict[str, Any]] = []
    for stage in stages:
        for gate_id in stage.get("assessments", []):
            assessment_ladder.append(
                {
                    "gate_id": gate_id,
                    "stage_id": stage.get("id"),
                    "stage_label": stage.get("label"),
                    "purpose": "학습 결과를 시험, 리포트, 구술, 프로젝트로 확인합니다.",
                }
            )

    return {
        "schema": PROCESS_EMULATION_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "role_model_id": role_model_profile.get("role_model_id"),
        "domain": role_model_profile.get("domain"),
        "design_principle": {
            "summary": (
                "대표 인물의 결론, 성격 키워드, 투자 철학을 주입하지 않고 "
                "그 인물이 통과한 교육 환경, 과제, 시험, 피드백 압력을 재현합니다."
            ),
            "mode": "learning_path_replication_not_personality_injection",
            "expected_outcome": "AI가 초등학교부터 대학원, 고용 후 업무까지 학습 데이터와 시험을 누적하며 자기 추론기보를 계속 형성합니다.",
        },
        "allowed_inputs": [
            "verified_public_life_events",
            "verified_or_cited_school_path",
            "open_or_boss_provided_curriculum_materials",
            "exam_results_and_recovery_feedback",
            "public_financial_data_with_sources",
        ],
        "forbidden_shortcuts": [
            "preload_interpreted_personality_traits",
            "preload_worldview_keywords_as_identity",
            "claim_exact_historical_coursework_without_source",
            "claim_the_ai_is_the_role_model",
            "store_private_chain_of_thought",
        ],
        "saju_boundary": {
            "used": saju_seed is not None,
            "use": "simulation_initial_condition_only",
            "precision": (saju_seed or {}).get("confidence", {}).get("saju_precision"),
        },
        "historical_path_evidence": role_model_profile.get("historical_education_evidence", []),
        "evidence_gap_policy": {
            "verified_fact": "그대로 교육 서사와 기록에 반영합니다.",
            "not_yet_sourced": "추정으로 표시하고, 정확한 과정명이나 성적처럼 단정하지 않습니다.",
            "modern_replacement": "현대 로컬 AI 업무 수행에 필요한 대체 과목으로 분리 표기합니다.",
        },
        "curriculum_stages": [
            {
                "stage_id": stage.get("id"),
                "label": stage.get("label"),
                "courses": stage.get("courses", []),
                "assessments": stage.get("assessments", []),
                "student_action": "자료를 먼저 접하고, 과제물을 만들고, 평가를 받은 뒤에만 기보 후보를 남깁니다.",
            }
            for stage in stages
        ],
        "assessment_ladder": assessment_ladder,
        "kibo_policy": {
            "created_before_learning": False,
            "created_from": "yearly_learning_data_assignments_exams_feedback_and_reviewed_work",
            "promotion_rule": "같은 원칙이 여러 학년의 과제와 시험, 이후 업무에서 반복 검증될 때만 안정된 추론 습관으로 승격합니다.",
            "post_hire_rule": "에이전트로 일한 뒤 새 이론과 업무 경험이 쌓이면 기존 기보를 확장하거나 분화합니다.",
        },
    }
