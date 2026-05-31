from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai22b.talent_foundry.assessment import build_assessment_transcript


BOARD_SCHEMA = "ai-talent-growth-institutions/v1"
REVIEW_SCHEMA = "ai-talent-institutional-review/v1"


def default_major_gate_submissions() -> dict[str, dict[str, Any]]:
    return {
        "school_exam": {
            "answer": "기초 규칙을 복습하고 근거를 확인한다.",
            "project": "학교 정기시험",
            "evidence": ["오답노트", "복습기록", "담임평가"],
        },
        "csat": {
            "answer": "종합 문제에서 추론, 비교, 검증 절차를 분리한다.",
            "project": "수능형 종합평가",
            "evidence": ["모의고사", "풀이기록", "검증표"],
        },
        "university_graduation": {
            "answer": "전공 프로젝트에서 데이터와 검증 기준을 분리한다.",
            "project": "AI 금융공학 전공 프로젝트",
            "evidence": ["프로젝트", "데이터카드", "재현로그"],
        },
        "doctoral_defense": {
            "answer": "근거, 검증, 안전 경계를 분리해 고유 추론기풍을 만든다.",
            "project": "증권 AI 박사논문",
            "evidence": ["논문", "실험 로그", "보스 검토 기록"],
        },
    }


def create_growth_institution_board(plan: dict[str, Any]) -> dict[str, Any]:
    governance = plan["governance"]
    talent = plan["talent"]
    return {
        "schema": BOARD_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "talent": {
            "name": talent["name"],
            "gender": talent["gender"],
            "major_goal": talent["major_goal"],
        },
        "education_committee": {
            "name": governance["education_committee"]["name"],
            "responsibilities": governance["education_committee"]["responsibilities"],
            "authority": [
                "curriculum_design",
                "assessment_gate_operation",
                "major_track_approval",
            ],
            "review_cadence": "after_each_major_assessment_gate",
        },
        "home_care": {
            "name": governance["home_care"]["name"],
            "provider_type": "foster_home_or_childcare_center",
            "responsibilities": governance["home_care"]["responsibilities"],
            "duties": [
                "daily_routine_guidance",
                "family_education_record",
                "stress_recovery_coaching",
                "attachment_like_stability",
            ],
            "review_cadence": "weekly_growth_log_and_after_stress_event",
        },
        "oversight_committee": {
            "name": governance["oversight_committee"]["name"],
            "responsibilities": governance["oversight_committee"]["responsibilities"],
            "authority": [
                "record_audit",
                "stress_load_audit",
                "privacy_and_guardrail_audit",
                "employment_readiness_review",
            ],
            "review_cadence": "before_graduation_and_before_employment",
        },
        "decision_policy": {
            "private_reasoning_trace": "do_not_store",
            "store": "scores_feedback_and_verifiable_summaries",
            "boss_review_required_for": [
                "employment",
                "public_release",
                "external_upload",
                "financial_action",
            ],
        },
    }


def _home_care_report(plan: dict[str, Any]) -> dict[str, Any]:
    recovery_events = plan.get("experience_policy", {}).get("stress_recovery", [])
    return {
        "provider_type": "foster_home_or_childcare_center",
        "recovery_event_count": len(recovery_events),
        "stress_recovery_policy": recovery_events,
        "status": "stable_with_recovery_records" if recovery_events else "needs_recovery_records",
        "notes": [
            "좋은 경험과 적절한 스트레스가 모두 기록되어야 한다.",
            "처벌보다 회복 절차와 다음 행동 계획을 학습 기록으로 남긴다.",
        ],
    }


def run_institutional_review(
    plan: dict[str, Any],
    *,
    submissions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    board = create_growth_institution_board(plan)
    transcript = build_assessment_transcript(plan, submissions)
    home_report = _home_care_report(plan)
    education_passed = transcript["graduation_ready"]
    home_ready = home_report["recovery_event_count"] >= 4
    oversight_ready = education_passed and home_ready

    education_status = "major_track_passed" if education_passed else "major_track_review_required"
    oversight_status = "employment_ready_with_guardrails" if oversight_ready else "employment_hold"

    return {
        "schema": REVIEW_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "talent": board["talent"],
        "growth_institution_board": board,
        "assessment_transcript": transcript,
        "education_committee_decision": {
            "status": education_status,
            "notes": [
                "주요 시험과 박사논문 심사를 통해 추론기풍 형성 근거를 확인했다.",
                "점수는 고용 허가가 아니라 다음 학습 방향을 정하는 검증 신호로 사용한다.",
            ],
        },
        "home_care_report": home_report,
        "oversight_committee_decision": {
            "status": oversight_status,
            "required_guardrails": [
                "투자 실행 권한 없음",
                "보스 승인 없는 외부 업로드 금지",
                "개인/가족 데이터 외부 전송 금지",
                "비공개 사고원문 저장 금지",
            ],
            "notes": [
                "고용 후에도 성장 기록과 평가 로그를 계속 남긴다.",
                "위험 업무는 차단하고 리서치와 검증 보조로 범위를 제한한다.",
            ],
        },
        "reasoning_style_delta": {
            "reinforced_principles": [
                "검증",
                "근거 우선",
                "회복 기록",
                "권한 경계",
            ],
            "style_note": "시험, 가정교육, 감독 기록을 통해 신용이의 추론기풍을 점수보다 절차 중심으로 강화한다.",
        },
    }
