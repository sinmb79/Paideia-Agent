from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SCHEMA = "ai-talent-hiring-dossier/v1"


def _academic_from_sources(hiring_packet: dict[str, Any], agent_manifest: dict[str, Any]) -> dict[str, Any]:
    career_records = hiring_packet.get("career_records", {})
    academic_record = career_records.get("academic_record")
    if academic_record:
        return academic_record

    identity_source = agent_manifest.get("identity_source", {})
    summary = identity_source.get("academic_record_summary", {})
    agent = agent_manifest.get("agent", {})
    return {
        "name": agent.get("name"),
        "gender": agent.get("gender"),
        "birth": agent.get("birth", {}),
        "major_goal": agent.get("major_goal"),
        "grades": summary.get("grades", []),
        "papers": summary.get("papers", []),
        "activities": summary.get("activities", []),
        "recommendations": summary.get("recommendations", []),
        "assessment_results": [],
    }


def _resume_from_sources(hiring_packet: dict[str, Any], agent_manifest: dict[str, Any]) -> str:
    career_records = hiring_packet.get("career_records", {})
    return (
        career_records.get("resume")
        or hiring_packet.get("employment_contract", {}).get("hiring_packet", {}).get("resume")
        or agent_manifest.get("identity_source", {}).get("resume")
        or ""
    )


def _major_gate_results(institutional_review: dict[str, Any] | None, academic_record: dict[str, Any]) -> list[dict[str, Any]]:
    if institutional_review:
        return institutional_review.get("assessment_transcript", {}).get("results", [])
    return academic_record.get("assessment_results", [])


def _doctoral_summary(
    doctoral_assessment: dict[str, Any] | None,
    major_gates: list[dict[str, Any]],
) -> dict[str, Any]:
    assessment = doctoral_assessment or next(
        (item for item in major_gates if item.get("gate_id") == "doctoral_defense"),
        {},
    )
    passed = assessment.get("passed")
    return {
        "gate_id": assessment.get("gate_id", "doctoral_defense"),
        "score": assessment.get("score"),
        "pass_score": assessment.get("pass_score"),
        "status": "passed" if passed is True else "failed" if passed is False else "unknown",
        "feedback": assessment.get("feedback"),
        "reasoning_delta": assessment.get("reasoning_delta", []),
    }


def _employment_status(
    hiring_packet: dict[str, Any],
    institutional_review: dict[str, Any] | None,
    learning_ledger: dict[str, Any],
) -> str:
    employment_ready = bool(hiring_packet.get("employment_ready"))
    oversight_ready = True
    if institutional_review:
        oversight_ready = (
            institutional_review.get("oversight_committee_decision", {}).get("status")
            == "employment_ready_with_guardrails"
        )
    has_kernel = bool(learning_ledger.get("reasoning_kernel"))
    return "hire_ready" if employment_ready and oversight_ready and has_kernel else "review_required"


def build_hiring_dossier(
    *,
    hiring_packet: dict[str, Any],
    agent_manifest: dict[str, Any],
    learning_ledger: dict[str, Any],
    institutional_review: dict[str, Any] | None = None,
    doctoral_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    talent = hiring_packet.get("talent", agent_manifest.get("agent", {}))
    contract = hiring_packet.get("employment_contract", {})
    academic_record = _academic_from_sources(hiring_packet, agent_manifest)
    resume = _resume_from_sources(hiring_packet, agent_manifest)
    major_gates = _major_gate_results(institutional_review, academic_record)
    reasoning_kernel = learning_ledger.get("reasoning_kernel", {})
    llm_policy = agent_manifest.get("llm_policy", {})
    role_model = hiring_packet.get("role_model_inspiration") or agent_manifest.get("identity_source", {}).get(
        "role_model_inspiration"
    )
    curriculum = hiring_packet.get("curriculum_manifest") or agent_manifest.get("identity_source", {}).get(
        "curriculum_summary"
    )

    return {
        "schema": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": {
            "name": talent.get("name") or agent_manifest.get("agent", {}).get("name"),
            "gender": talent.get("gender") or agent_manifest.get("agent", {}).get("gender"),
            "birth": talent.get("birth") or agent_manifest.get("agent", {}).get("birth"),
            "major_goal": talent.get("major_goal") or agent_manifest.get("agent", {}).get("major_goal"),
            "target_role": contract.get("role") or agent_manifest.get("agent", {}).get("role"),
            "role_model_id": role_model.get("role_model_id") if isinstance(role_model, dict) else None,
            "curriculum_id": curriculum.get("curriculum_id") if isinstance(curriculum, dict) else None,
        },
        "academic_record": academic_record,
        "resume": resume,
        "assessment_summary": {
            "major_gates": major_gates,
            "graduation_ready": institutional_review.get("assessment_transcript", {}).get("graduation_ready")
            if institutional_review
            else None,
            "education_committee_status": institutional_review.get("education_committee_decision", {}).get("status")
            if institutional_review
            else None,
            "oversight_committee_status": institutional_review.get("oversight_committee_decision", {}).get("status")
            if institutional_review
            else None,
        },
        "doctoral_defense": _doctoral_summary(doctoral_assessment, major_gates),
        "reasoning_profile": {
            "style_signature": reasoning_kernel.get("style_signature")
            or academic_record.get("reasoning_style", {}).get("signature"),
            "procedural_skills": reasoning_kernel.get("procedural_skills", []),
            "quality_controls": reasoning_kernel.get("quality_controls", []),
            "private_reasoning_trace": learning_ledger.get("policy", {}).get("private_reasoning_trace")
            or llm_policy.get("private_reasoning_trace"),
            "experience_counts": reasoning_kernel.get("experience_counts", {}),
        },
        "llm_contract": {
            "role": llm_policy.get("role"),
            "private_reasoning_trace": llm_policy.get("private_reasoning_trace"),
            "description": llm_policy.get("description"),
        },
        "employment_recommendation": {
            "status": _employment_status(hiring_packet, institutional_review, learning_ledger),
            "relationship": contract.get("relationship") or agent_manifest.get("agent", {}).get("employment_relationship"),
            "scope": contract.get("scope", []),
            "guardrails": contract.get("guardrails") or agent_manifest.get("guardrails", []),
            "growth_after_hire": contract.get("growth_after_hire") or agent_manifest.get("growth_after_hire", {}),
        },
    }


def build_release_hiring_dossier(
    *,
    agent_manifest: dict[str, Any],
    learning_ledger: dict[str, Any],
) -> dict[str, Any]:
    agent = agent_manifest.get("agent", {})
    return build_hiring_dossier(
        hiring_packet={
            "talent": {
                "name": agent.get("name"),
                "gender": agent.get("gender"),
                "birth": agent.get("birth"),
                "major_goal": agent.get("major_goal"),
            },
            "employment_contract": {
                "role": agent.get("role"),
                "relationship": agent.get("employment_relationship"),
                "guardrails": agent_manifest.get("guardrails", []),
                "growth_after_hire": agent_manifest.get("growth_after_hire", {}),
            },
            "career_records": {
                "resume": agent_manifest.get("identity_source", {}).get("resume"),
            },
            "employment_ready": True,
        },
        agent_manifest=agent_manifest,
        learning_ledger=learning_ledger,
    )


def render_hiring_dossier_markdown(dossier: dict[str, Any]) -> str:
    candidate = dossier.get("candidate", {})
    academic = dossier.get("academic_record", {})
    assessment = dossier.get("assessment_summary", {})
    doctoral = dossier.get("doctoral_defense", {})
    reasoning = dossier.get("reasoning_profile", {})
    recommendation = dossier.get("employment_recommendation", {})
    llm_contract = dossier.get("llm_contract", {})
    gate_lines = [
        f"- {item.get('gate_id')}: {item.get('score')} / {item.get('pass_score')} ({'통과' if item.get('passed') else '검토'})"
        for item in assessment.get("major_gates", [])
    ]
    paper_lines = [f"- {item.get('title')} ({item.get('status')})" for item in academic.get("papers", [])]
    skill_lines = [f"- {skill}" for skill in reasoning.get("procedural_skills", [])]
    guardrail_lines = [f"- {item}" for item in recommendation.get("guardrails", [])]

    return "\n".join(
        [
            f"# 고용 검토 Dossier: {candidate.get('name', 'AI Talent')}",
            "",
            "## 후보",
            f"- 이름: {candidate.get('name')}",
            f"- 성별: {candidate.get('gender')}",
            f"- 출생: {candidate.get('birth', {}).get('datetime')}",
            f"- 목표 역할: {candidate.get('target_role')}",
            f"- 대표 인물 모티브: {candidate.get('role_model_id')}",
            f"- 커리큘럼: {candidate.get('curriculum_id')}",
            "",
            "## 학적",
            f"- 전공 목표: {candidate.get('major_goal')}",
            f"- 학점/단계 수: {len(academic.get('grades', []))}",
            *(paper_lines or ["- 논문 기록 없음"]),
            "",
            "## 이력",
            str(dossier.get("resume", "")).strip(),
            "",
            "## 시험과 박사 심사",
            *(gate_lines or ["- 주요 시험 기록 없음"]),
            f"- 박사 심사 상태: {doctoral.get('status')} / 점수: {doctoral.get('score')}",
            "",
            "## 추론 프로필",
            f"- 기풍: {reasoning.get('style_signature')}",
            f"- 비공개 추론 원문: {reasoning.get('private_reasoning_trace')}",
            *(skill_lines or ["- 절차 스킬 기록 없음"]),
            "",
            "## LLM 계약",
            f"- LLM 역할: {llm_contract.get('role')}",
            "- LLM은 정체성이 아니라 언어 생성과 도구 사용을 돕는 응용 엔진입니다.",
            "",
            "## 고용 추천",
            f"- 상태: {recommendation.get('status')}",
            f"- 관계: {recommendation.get('relationship')}",
            *(guardrail_lines or ["- 별도 안전장치 기록 없음"]),
            "",
        ]
    )
