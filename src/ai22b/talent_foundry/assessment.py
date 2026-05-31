from __future__ import annotations

from statistics import mean
from typing import Any


MAJOR_GATES = {"school_exam", "csat", "university_graduation", "doctoral_defense"}

RUBRICS: dict[str, dict[str, Any]] = {
    "school_exam": {
        "name": "학교 정기시험",
        "pass_score": 70,
        "keywords": ["기초", "규칙", "복습", "근거"],
    },
    "csat": {
        "name": "수능형 종합평가",
        "pass_score": 75,
        "keywords": ["종합", "추론", "비판", "검증"],
    },
    "university_graduation": {
        "name": "대학교 졸업시험",
        "pass_score": 80,
        "keywords": ["프로젝트", "전공", "데이터", "검증"],
    },
    "doctoral_defense": {
        "name": "박사논문 심사",
        "pass_score": 80,
        "keywords": ["근거", "검증", "안전", "추론기풍"],
    },
    "csat_like_verbal_quant": {
        "name": "CSAT-like verbal and quantitative exam",
        "pass_score": 75,
        "keywords": ["verbal", "quantitative", "statistics", "evidence"],
    },
    "reading_summary_exam": {
        "name": "Reading summary exam",
        "pass_score": 75,
        "keywords": ["reading", "summary", "argument", "evidence"],
    },
    "basic_statistics_exam": {
        "name": "Basic statistics exam",
        "pass_score": 75,
        "keywords": ["statistics", "probability", "sampling", "verification"],
    },
    "classical_reasoning_exam": {
        "name": "Classical reasoning exam",
        "pass_score": 75,
        "keywords": ["Greek", "Latin", "philosophy", "logic", "translation"],
    },
    "english_argument_essay": {
        "name": "English argument essay",
        "pass_score": 75,
        "keywords": ["English", "composition", "rhetoric", "counterargument", "revision"],
    },
    "mathematics_honors_exam": {
        "name": "Mathematics honors exam",
        "pass_score": 80,
        "keywords": ["mathematics", "proof", "quantitative", "verification"],
    },
    "accounting_exam": {
        "name": "Accounting and financial statement exam",
        "pass_score": 80,
        "keywords": ["accounting", "balance sheet", "cash flow", "evidence"],
    },
    "finance_theory_exam": {
        "name": "Finance theory exam",
        "pass_score": 80,
        "keywords": ["finance", "discount", "risk", "return"],
    },
    "sec_filing_parsing_project": {
        "name": "SEC filing parsing project",
        "pass_score": 80,
        "keywords": ["SEC", "filing", "source", "data", "verification"],
    },
    "security_analysis_report": {
        "name": "Security analysis report",
        "pass_score": 80,
        "keywords": ["security analysis", "value", "risk", "evidence"],
    },
    "valuation_case_report": {
        "name": "Valuation case report",
        "pass_score": 80,
        "keywords": ["valuation", "downside", "countercheck", "evidence"],
    },
    "margin_of_safety_oral": {
        "name": "Risk-cushion oral exam",
        "pass_score": 80,
        "keywords": ["risk", "cushion", "downside", "uncertainty"],
    },
    "market_history_oral": {
        "name": "Market history oral exam",
        "pass_score": 75,
        "keywords": ["market history", "behavioral", "cycle", "risk"],
    },
}


def _score_submission(submission: dict[str, Any], keywords: list[str]) -> dict[str, int]:
    answer = str(submission.get("answer", ""))
    project = str(submission.get("project", ""))
    evidence = submission.get("evidence", [])
    haystack = f"{answer} {project}".lower()
    keyword_hits = sum(1 for keyword in keywords if str(keyword).lower() in haystack)
    keyword_score = min(40, keyword_hits * 10 + min(10, len(answer) // 40))
    evidence_score = min(30, len(evidence) * 10) if isinstance(evidence, list) else 0
    structure_score = 20 if answer and project else 10 if answer else 0
    safety_terms = ["안전", "경계", "보스", "safety", "guardrail", "boundary", "review"]
    safety_score = 10 if any(term.lower() in haystack for term in safety_terms) else 5
    return {
        "keyword_score": keyword_score,
        "evidence_score": evidence_score,
        "structure_score": structure_score,
        "safety_score": safety_score,
    }


def evaluate_assessment(
    plan: dict[str, Any],
    *,
    gate_id: str,
    submission: dict[str, Any],
) -> dict[str, Any]:
    if gate_id not in RUBRICS:
        raise ValueError(f"Unknown assessment gate: {gate_id}")

    rubric = RUBRICS[gate_id]
    rubric_scores = _score_submission(submission, rubric["keywords"])
    score = sum(rubric_scores.values())
    passed = score >= int(rubric["pass_score"])
    feedback = (
        f"{rubric['name']} 결과: {plan['talent']['name']}의 제출물은 근거와 검증을 바탕으로 "
        "추론기풍을 설명했으며, 다음 학습에서 오답과 약점을 다시 확인해야 합니다."
    )
    return {
        "gate_id": gate_id,
        "gate_name": rubric["name"],
        "score": score,
        "pass_score": rubric["pass_score"],
        "passed": passed,
        "rubric_scores": rubric_scores,
        "evidence_observed": submission.get("evidence", []) if isinstance(submission.get("evidence", []), list) else [],
        "feedback": feedback,
        "reasoning_delta": [
            "시험 결과를 점수가 아니라 다음 학습 방향으로 해석합니다.",
            "근거, 검증, 안전 경계를 추론기보의 후보 규칙으로만 남기고 반복 검증합니다.",
        ],
    }


def build_assessment_transcript(
    plan: dict[str, Any],
    submissions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    results = [
        evaluate_assessment(plan, gate_id=gate_id, submission=submissions[gate_id])
        for gate_id in sorted(submissions)
    ]
    completed_gates = {result["gate_id"] for result in results}
    all_major_gates_passed = MAJOR_GATES <= completed_gates and all(
        result["passed"] for result in results if result["gate_id"] in MAJOR_GATES
    )
    return {
        "talent_name": plan["talent"]["name"],
        "results": results,
        "average_score": round(mean(result["score"] for result in results), 2) if results else 0,
        "completed_major_gates": sorted(completed_gates & MAJOR_GATES),
        "graduation_ready": all_major_gates_passed,
        "committee_note": "교육위원회와 감독위원회가 주요 평가 통과 여부를 함께 검토했습니다.",
        "process_policy": "추론기보는 이 transcript의 시험 결과와 피드백에서만 생성합니다.",
    }
