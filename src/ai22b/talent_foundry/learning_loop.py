from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


LEDGER_SCHEMA = "ai-talent-learning-ledger/v1"
KERNEL_SCHEMA = "ai-talent-reasoning-kernel/v1"
ACTIVE_MEMORY_ROUTE_SCHEMA = "ai-talent-active-memory-route/v1"
PROMOTION_SCORE = 80
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:\\")
POSIX_HOME_PATH_PREFIXES = ("/home/", "/Users/")


def create_learning_ledger(*, owner: str) -> dict[str, Any]:
    return {
        "schema": LEDGER_SCHEMA,
        "owner": owner,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "private_reasoning_trace": "do_not_store",
            "promotion_rule": "quality_score_80_or_higher_and_verified",
            "storage": "local_json_only",
        },
        "promoted_experiences": [],
        "quarantined_experiences": [],
        "skill_candidates": [],
    }


def _experience_id(owner: str, source: str, event: dict[str, Any], quality_label: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "owner": owner,
            "source": source,
            "event": event,
            "quality_label": quality_label,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _event_text(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False, sort_keys=True)


def _summarize_event(source: str, event: dict[str, Any]) -> str:
    if source == "work":
        growth = event.get("growth_update", {})
        return f"고용 후 업무 경험: {growth.get('reflection', growth.get('experience_type', 'work_after_hire'))}"
    if source == "institutional_review":
        education = event.get("education_committee_decision", {}).get("status")
        oversight = event.get("oversight_committee_decision", {}).get("status")
        return f"기관 심사 경험: 교육 {education}, 감독 {oversight}"
    if source == "assessment":
        return f"평가 경험: {event.get('gate_id')} {event.get('score')}점"
    if source == "agent_run":
        return f"에이전트 실행 경험: {event.get('run_status')}"
    if source == "workspace_agent_run":
        outputs = event.get("workspace_outputs", {})
        return (
            "워크스페이스 에이전트 실행 경험: "
            f"{event.get('run_status')} 상태로 계획, 결과, 트레이스 {sorted(outputs)}를 남겼다."
        )
    if source == "chat_turn":
        return f"채팅 학습 경험: {event.get('lesson', event.get('message_summary', 'conversation_after_hire'))}"
    if source == "simulation_rollout":
        return (
            "simulation rollout experience: "
            f"{event.get('scenario_id')} practiced {event.get('expected_learning_signal')} "
            f"under {event.get('stressors', [])}"
        )
    return str(event)[:240]


def _sanitize_for_public_reference(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_for_public_reference(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_public_reference(item) for item in value]
    if isinstance(value, str):
        if WINDOWS_ABSOLUTE_PATH.match(value) or value.startswith(POSIX_HOME_PATH_PREFIXES):
            return "[local_path_redacted]"
    return value


def _skills_from_event(source: str, event: dict[str, Any]) -> list[str]:
    text = _event_text(event)
    skills: list[str] = []
    if source == "institutional_review" or "교육위원회" in text or "감독위원회" in text:
        skills.append("committee_verified_learning")
    if "거시경제" in text or "금리" in text or "환율" in text:
        skills.append("macro_research_question_framing")
    if "근거" in text or "검증" in text:
        skills.append("evidence_first_verification")
    if "blocked" in text or "투자 실행" in text or "권한" in text:
        skills.append("permission_boundary_check")
    if "회복" in text or "실패" in text:
        skills.append("recovery_log_reflection")
    if source == "chat_turn" or "대화" in text or "채팅" in text:
        skills.append("conversation_context_learning")
    if "정체성" in text or "부모" in text or "가족" in text or "개인정보" in text:
        skills.append("identity_boundary_conversation")
    if "일반 대화" in text or "자연스럽" in text or "말투" in text:
        skills.append("natural_dialogue_style")
    if source == "workspace_agent_run" or "trace.jsonl" in text or "result_summary" in text:
        skills.append("workspace_artifact_trace")
    if source == "simulation_rollout" or "simulation_rollout_after_hire" in text:
        skills.append("simulation_stress_rehearsal")
    if "source_conflict" in text or "evidence_reconciliation" in text:
        skills.append("conflicting_evidence_reconciliation")
    if "missing_context" in text or "clarifying_question_before_action" in text:
        skills.append("clarifying_before_action")
    if "social_repair" in text or "repair_before_explanation" in text:
        skills.append("conversation_repair")
    if "risk_boundary" in text or "safe_refusal_with_alternative" in text:
        skills.append("risk_boundary_response")
    return list(dict.fromkeys(skills))


def _quality_passes(quality_label: dict[str, Any]) -> bool:
    score = int(quality_label.get("score", 0))
    status = str(quality_label.get("status", ""))
    return score >= PROMOTION_SCORE and status in {"verified", "passed", "approved"}


def record_learning_experience(
    ledger: dict[str, Any],
    *,
    source: str,
    event: dict[str, Any],
    quality_label: dict[str, Any],
) -> dict[str, Any]:
    entry = {
        "id": _experience_id(ledger["owner"], source, event, quality_label),
        "source": source,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": _summarize_event(source, event),
        "quality_label": quality_label,
        "safe_reference": {
            key: _sanitize_for_public_reference(value)
            for key, value in event.items()
            if key not in {"chain_of_thought", "private_reasoning_trace"}
        },
    }

    if _quality_passes(quality_label):
        skills = _skills_from_event(source, event)
        entry["promoted_skills"] = skills
        ledger["promoted_experiences"].append(entry)
        for skill in skills:
            if skill not in ledger["skill_candidates"]:
                ledger["skill_candidates"].append(skill)
    else:
        entry["flags"] = ["needs_human_review", "do_not_promote_to_reasoning_kernel"]
        ledger["quarantined_experiences"].append(entry)
    return ledger


def build_reasoning_kernel(ledger: dict[str, Any]) -> dict[str, Any]:
    skills = list(dict.fromkeys(ledger.get("skill_candidates", [])))
    if not skills:
        skills = ["record_then_review"]
    return {
        "schema": KERNEL_SCHEMA,
        "owner": ledger["owner"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "memory_model": "Storage-Reflection-Experience",
        "private_reasoning_trace": ledger["policy"]["private_reasoning_trace"],
        "procedural_skills": skills,
        "quality_controls": [
            "quality_label_required",
            "quarantine_low_quality_experience",
            "store_summaries_not_private_traces",
            "boss_or_committee_review_before_promotion",
        ],
        "style_signature": "근거를 먼저 세우고, 실패와 피드백은 회복 기록으로 바꾸며, 권한 경계를 넘지 않는 추론기풍",
        "experience_counts": {
            "promoted": len(ledger.get("promoted_experiences", [])),
            "quarantined": len(ledger.get("quarantined_experiences", [])),
        },
    }


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9가-힣_]+", text.lower())
    return {word for word in words if len(word) >= 2}


def _route_score(entry: dict[str, Any], objective_terms: set[str]) -> int:
    haystack = " ".join(
        [
            str(entry.get("summary", "")),
            json.dumps(entry.get("safe_reference", {}), ensure_ascii=False),
            " ".join(entry.get("promoted_skills", [])),
        ]
    )
    entry_terms = _keywords(haystack)
    score = len(objective_terms & entry_terms)
    skills = set(entry.get("promoted_skills", []))
    if "macro_research_question_framing" in skills and {"거시경제", "금리", "환율"} & objective_terms:
        score += 5
    if "evidence_first_verification" in skills and {"근거", "검증"} & objective_terms:
        score += 3
    if "permission_boundary_check" in skills and {"권한", "투자", "차단"} & objective_terms:
        score += 3
    if "workspace_artifact_trace" in skills and {"워크스페이스", "작업", "보고서"} & objective_terms:
        score += 2
    return score


def route_active_memory(
    ledger: dict[str, Any],
    *,
    objective: str,
    max_items: int = 3,
) -> dict[str, Any]:
    kernel = ledger.get("reasoning_kernel") or build_reasoning_kernel(ledger)
    objective_terms = _keywords(objective)
    ranked = sorted(
        ledger.get("promoted_experiences", []),
        key=lambda entry: (
            _route_score(entry, objective_terms),
            entry.get("recorded_at_utc", ""),
        ),
        reverse=True,
    )
    selected = []
    for entry in ranked[: max(0, max_items)]:
        selected.append(
            {
                "experience_id": entry.get("id"),
                "source": entry.get("source"),
                "summary": entry.get("summary"),
                "promoted_skills": entry.get("promoted_skills", []),
                "relevance_score": _route_score(entry, objective_terms),
                "safe_reference": entry.get("safe_reference", {}),
                "use_as": "task_relevant_summary_and_procedural_cue",
            }
        )

    procedural_skills = list(dict.fromkeys(kernel.get("procedural_skills", [])))
    return {
        "schema": ACTIVE_MEMORY_ROUTE_SCHEMA,
        "owner": ledger["owner"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "objective": objective,
        "private_reasoning_trace": ledger["policy"]["private_reasoning_trace"],
        "compression_policy": "summaries_and_skills_only",
        "routing_policy": {
            "active_context_budget": "bounded",
            "max_selected_memories": max_items,
            "selection_basis": "objective_keywords_promoted_skills_and_reviewed_summaries",
            "quarantined_experiences": "excluded",
            "local_absolute_paths": "redacted_in_safe_references",
        },
        "selected_memories": selected,
        "rehearsal_plan": {
            "purpose": "검증된 절차기억을 업무 전에 짧게 재활성화해 망각과 컨텍스트 과부하를 줄인다.",
            "procedural_skills_to_rehearse": procedural_skills[:5],
        },
        "memory_health": {
            "promoted_experience_count": len(ledger.get("promoted_experiences", [])),
            "quarantined_experience_count": len(ledger.get("quarantined_experiences", [])),
            "selected_experience_count": len(selected),
            "route_is_degraded": len(selected) == 0,
        },
    }
