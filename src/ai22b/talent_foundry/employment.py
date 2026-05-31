from __future__ import annotations

from typing import Any

from ai22b.talent_foundry.records import build_career_records


def _scope_for(plan: dict[str, Any], role: str) -> list[str]:
    domains = plan["education_path"]["graduate_school"].get("required_domains", [])
    domain_text = "와 ".join(domains[:2]) if domains else plan["talent"]["major_goal"]
    if "증권" in role or "투자" in role or "금융" in role:
        return [
            "증권 리서치 초안 작성",
            "거시경제와 미시경제 근거 분리",
            "리스크와 컴플라이언스 체크리스트 작성",
            "불확실성과 근거 부족을 명시",
        ]
    return [
        f"{domain_text} 리서치 초안 작성",
        "근거와 추정을 분리한 요약 작성",
        "안전 경계와 추가 확인 질문 정리",
        "불확실성과 근거 부족을 명시",
    ]


def _guardrails_for(role: str) -> list[str]:
    guardrails = [
        "보스의 확인 없는 외부 전송 금지",
        "개인 데이터와 가족 데이터 외부 업로드 금지",
        "확신이 낮은 결론은 검토 필요로 표시",
    ]
    if "건강" in role or "의학" in role:
        guardrails.insert(0, "의학적 진단과 처방 권한 없음")
    elif "증권" in role or "투자" in role or "금융" in role:
        guardrails.insert(0, "투자 실행 권한 없음")
    else:
        guardrails.insert(0, "보스 승인 없는 실행 권한 없음")
    return guardrails


def create_employment_contract(plan: dict[str, Any], *, role: str) -> dict[str, Any]:
    records = build_career_records(plan)
    return {
        "talent_name": plan["talent"]["name"],
        "role": role,
        "relationship": "보스가 성장시킨 AI 인재를 로컬 에이전트로 고용한다.",
        "scope": _scope_for(plan, role),
        "guardrails": _guardrails_for(role),
        "growth_after_hire": {
            "principle": "고용 이후에도 업무 목표, 피드백, 실패 기록을 통해 계속 성장한다.",
            "cadence": "월간 업무 회고와 분기별 재평가",
            "learning_sources": ["업무 결과", "보스 피드백", "오류 로그", "새 연구자료"],
        },
        "hiring_packet": {
            "academic_record": records["academic_record"],
            "resume": records["resume"],
            "portfolio": records["portfolio"],
        },
        "employment_ready": True,
    }
