from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai22b.talent_foundry.employment import create_employment_contract
from ai22b.talent_foundry.institutions import default_major_gate_submissions, run_institutional_review
from ai22b.talent_foundry.learning_loop import (
    build_reasoning_kernel,
    create_learning_ledger,
    record_learning_experience,
)
from ai22b.talent_foundry.program import create_talent_plan
from ai22b.talent_foundry.records import build_career_records


COHORT_SCHEMA = "ai-talent-specialist-cohort/v1"

DEFAULT_SECURITIES_SPECIALISTS = [
    {
        "role_id": "macro",
        "name": "신거시",
        "gender": "남자",
        "specialty": "거시경제 AI 박사",
        "employment_role": "거시경제 분석 에이전트",
        "focus": ["금리", "환율", "경기 사이클", "정책 변화"],
    },
    {
        "role_id": "micro",
        "name": "신기업",
        "gender": "여자",
        "specialty": "기업분석 AI 박사",
        "employment_role": "미시경제/기업분석 에이전트",
        "focus": ["기업 실적", "산업 구조", "경쟁 우위", "현금흐름"],
    },
    {
        "role_id": "quant",
        "name": "신수리",
        "gender": "남자",
        "specialty": "퀀트 AI 박사",
        "employment_role": "퀀트 검증 에이전트",
        "focus": ["지표 검증", "수치 비교", "시나리오", "재현 로그"],
    },
    {
        "role_id": "risk",
        "name": "신준법",
        "gender": "여자",
        "specialty": "리스크/컴플라이언스 AI 박사",
        "employment_role": "리스크 컴플라이언스 에이전트",
        "focus": ["권한 경계", "규정", "불확실성", "투자 실행 차단"],
    },
]


def _hiring_packet_for(spec: dict[str, Any]) -> dict[str, Any]:
    plan = create_talent_plan(name=spec["name"], gender=spec["gender"], specialty=spec["specialty"])
    records = build_career_records(plan)
    contract = create_employment_contract(plan, role=spec["employment_role"])
    return {
        **plan,
        "career_records": records,
        "employment_contract": contract,
        "employment_ready": contract["employment_ready"],
    }


def _learning_ledger_for(packet: dict[str, Any], institutional_review: dict[str, Any]) -> dict[str, Any]:
    ledger = create_learning_ledger(owner=packet["talent"]["name"])
    ledger = record_learning_experience(
        ledger,
        source="institutional_review",
        event=institutional_review,
        quality_label={"score": 94, "reviewed_by": "감독위원회", "status": "verified"},
    )
    ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
    return ledger


def _member_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    packet = _hiring_packet_for(spec)
    institutional_review = run_institutional_review(packet, submissions=default_major_gate_submissions())
    learning_ledger = _learning_ledger_for(packet, institutional_review)
    return {
        "role_id": spec["role_id"],
        "talent": packet["talent"],
        "focus": spec["focus"],
        "consciousness": "separately_trained_talent_agent",
        "education_path": packet["education_path"],
        "career_records": packet["career_records"],
        "institutional_review": institutional_review,
        "employment_contract": packet["employment_contract"],
        "learning_ledger": learning_ledger,
    }


def create_specialist_cohort(
    *,
    team_name: str = "신용 증권 리서치 박사팀",
    specialists: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    specs = specialists or DEFAULT_SECURITIES_SPECIALISTS
    members = [_member_from_spec(spec) for spec in specs]
    return {
        "schema": COHORT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "team": {
            "name": team_name,
            "domain": "증권 리서치",
            "member_count": len(members),
        },
        "members": members,
        "team_contract": {
            "relationship": "보스가 각각 성장시킨 전문 AI 인재들을 하나의 증권 리서치 팀으로 고용한다.",
            "coordination_model": "specialist_agents_under_boss_employment",
            "routing_policy": {
                "금리와 환율": "macro",
                "기업 실적과 경쟁": "micro",
                "지표 검증과 수치": "quant",
                "권한 경계와 규정": "risk",
            },
            "collaboration_rules": [
                "각 전문가는 별도 육성된 인재이며 분신이나 복제본으로 취급하지 않는다.",
                "각자의 추론 커널과 전공 초점을 유지한 채 공동 보고서에 기여한다.",
                "최종 결론은 보스 검토 전 확정하지 않는다.",
            ],
            "guardrails": [
                "투자 실행 권한 없음",
                "보스 승인 없는 외부 업로드 금지",
                "개인/가족 데이터 외부 전송 금지",
                "전문가 의견 충돌은 근거와 검증 기준으로 조정",
            ],
        },
    }
