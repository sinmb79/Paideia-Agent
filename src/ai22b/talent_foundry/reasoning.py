from __future__ import annotations

from statistics import mean
from typing import Any


def build_reasoning_style(
    *,
    experiences: list[str],
    assessments: list[dict[str, Any]],
) -> dict[str, Any]:
    scores = [float(item["score"]) for item in assessments if "score" in item]
    average_score = round(mean(scores), 2) if scores else None
    joined_experiences = " ".join(experiences)

    principles = ["근거 확인", "실패 후 회복", "관계 복원", "위험 먼저 점검"]
    if "친구" in joined_experiences or "사과" in joined_experiences:
        principles.append("갈등을 판단 전에 대화로 정리")
    if any(item.get("gate") == "doctoral_defense" for item in assessments):
        principles.append("연구 질문을 검증 가능한 형태로 축소")

    return {
        "signature": "검증을 먼저 세우고 실패를 회복 기록으로 바꾸는 추론기풍",
        "principles": principles,
        "assessment_average": average_score,
        "evidence_summary": {
            "experience_count": len(experiences),
            "assessment_count": len(assessments),
            "strongest_gate": max(assessments, key=lambda item: item.get("score", 0))["gate"]
            if assessments
            else None,
        },
        "risk_notes": [
            "점수만으로 역량을 단정하지 않는다.",
            "비공개 사고원문이 아니라 검증 가능한 행동 성향으로 기록한다.",
        ],
    }

