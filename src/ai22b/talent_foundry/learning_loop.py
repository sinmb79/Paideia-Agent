from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from ai22b.talent_foundry.memory_lifecycle import audit_learning_ledger


LEDGER_SCHEMA = "ai-talent-learning-ledger/v1"
KERNEL_SCHEMA = "ai-talent-reasoning-kernel/v1"
ACTIVE_MEMORY_ROUTE_SCHEMA = "ai-talent-active-memory-route/v1"
PROMOTION_SCORE = 80
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:\\")
POSIX_HOME_PATH_PREFIXES = ("/home/", "/Users/")
SAFE_REFERENCE_OMIT_KEYS = {"chain_of_thought", "private_reasoning_trace"}
HEAVY_SAFE_REFERENCE_KEYS = {
    "active_memory_route",
    "base_agent_run",
    "execution_contract",
    "learning_update",
    "llm_runtime_result",
    "memory_write",
    "policy_decision",
    "runtime_observability",
    "tool_execution",
    "workspace_run",
}
OUTPUT_REFERENCE_KEYS = {"workspace_outputs", "job_outputs"}
MAX_SAFE_REFERENCE_DEPTH = 4
MAX_SAFE_REFERENCE_LIST_ITEMS = 8
MAX_SAFE_REFERENCE_DICT_ITEMS = 24
MAX_SAFE_REFERENCE_TEXT_CHARS = 700


def create_learning_ledger(*, owner: str) -> dict[str, Any]:
    ledger = {
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
    ledger["memory_lifecycle"] = audit_learning_ledger(ledger)
    return ledger


def _experience_id(owner: str, source: str, event_reference: dict[str, Any], quality_label: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "owner": owner,
            "source": source,
            "event_reference": event_reference,
            "quality_label": quality_label,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _event_text(event: dict[str, Any], *, source: str | None = None) -> str:
    return json.dumps(_safe_event_reference(source or str(event.get("schema", "event")), event), ensure_ascii=False, sort_keys=True)


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
    if source == "simulation_rollout_winner":
        episode = event.get("selected_episode", {})
        return (
            "검토된 병렬 시뮬레이션 winner 경험: "
            f"{episode.get('label', episode.get('scenario_id', 'rollout'))} "
            f"{episode.get('score', 'unscored')}점"
        )
    status = (
        event.get("run_status")
        or event.get("job_status")
        or event.get("cycle_status")
        or event.get("status")
        or "recorded"
    )
    objective = event.get("objective") or event.get("task") or event.get("summary") or event.get("message_summary")
    if objective:
        return f"{source} experience: {status} - {str(objective)[:160]}"
    return f"{source} experience: {status}"


def _sanitize_for_public_reference(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_for_public_reference(item)
            for key, item in value.items()
            if key not in SAFE_REFERENCE_OMIT_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_for_public_reference(item) for item in value]
    if isinstance(value, str):
        if WINDOWS_ABSOLUTE_PATH.match(value) or value.startswith(POSIX_HOME_PATH_PREFIXES):
            return "[local_path_redacted]"
    return value


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _public_file_reference(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _public_file_reference(item)
            for key, item in list(value.items())[:MAX_SAFE_REFERENCE_DICT_ITEMS]
        }
    if isinstance(value, list):
        return [_public_file_reference(item) for item in value[:MAX_SAFE_REFERENCE_LIST_ITEMS]]
    if isinstance(value, str):
        normalized = value.replace("\\", "/").rstrip("/")
        if WINDOWS_ABSOLUTE_PATH.match(value) or value.startswith(POSIX_HOME_PATH_PREFIXES):
            return {
                "file_name": normalized.split("/")[-1],
                "path_fingerprint_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                "absolute_path_redacted": True,
            }
        return value[:MAX_SAFE_REFERENCE_TEXT_CHARS]
    return value


def _summary_of_named_packet(key: str, value: Any) -> Any:
    if not isinstance(value, dict):
        return _bounded_public_reference(value)
    if key in OUTPUT_REFERENCE_KEYS:
        return _public_file_reference(value)
    if key in {"workspace_run", "base_agent_run"}:
        base = value.get("base_agent_run", {}) if isinstance(value.get("base_agent_run"), dict) else value
        contract = base.get("execution_contract", {}) if isinstance(base.get("execution_contract"), dict) else {}
        verification = base.get("verification", {}) if isinstance(base.get("verification"), dict) else {}
        return {
            "schema": value.get("schema"),
            "run_status": value.get("run_status") or base.get("run_status"),
            "agent": value.get("agent") or base.get("agent") or {},
            "task_fingerprint_sha256": hashlib.sha256(str(value.get("task") or base.get("task") or "").encode("utf-8")).hexdigest(),
            "selected_tools": base.get("selected_tools", value.get("selected_tools", [])),
            "verification_status": verification.get("status"),
            "execution_contract_status": contract.get("status"),
            "workspace_outputs": _public_file_reference(value.get("workspace_outputs", {})),
            "private_reasoning_trace_stored": False,
        }
    if key == "learning_update":
        lifecycle = value.get("memory_lifecycle", {}) if isinstance(value.get("memory_lifecycle"), dict) else {}
        return {
            "schema": value.get("schema"),
            "decision": value.get("decision"),
            "source": value.get("source"),
            "latest_experience_id": value.get("latest_experience_id"),
            "latest_promoted_skills": value.get("latest_promoted_skills", []),
            "experience_counts": value.get("experience_counts", {}),
            "memory_lifecycle_status": lifecycle.get("status"),
        }
    if key == "llm_runtime_result":
        return {
            "schema": value.get("schema"),
            "engine": value.get("engine"),
            "status": value.get("status"),
            "reason": value.get("reason"),
            "model": value.get("model"),
            "identity_policy": value.get("identity_policy"),
            "raw_output_saved": value.get("raw_output_saved", False),
        }
    if key == "policy_decision":
        return {
            "schema": value.get("schema"),
            "status": value.get("status"),
            "decision_model": value.get("decision_model"),
            "policy_violations": value.get("policy_violations", []),
            "approval_required_count": len(value.get("approval_required", [])),
            "denied_count": len(value.get("denied_actions", [])),
        }
    if key == "tool_execution":
        results = []
        for item in value.get("tool_results", [])[:MAX_SAFE_REFERENCE_LIST_ITEMS]:
            if not isinstance(item, dict):
                continue
            output = item.get("output", {})
            results.append(
                {
                    "tool": item.get("tool"),
                    "status": item.get("status"),
                    "capability": item.get("capability"),
                    "output_schema": output.get("schema") if isinstance(output, dict) else None,
                }
            )
        return {
            "schema": value.get("schema"),
            "execution_model": value.get("execution_model"),
            "selected_tools": value.get("selected_tools", []),
            "tool_results": results,
        }
    if key == "execution_contract":
        policy_gate = value.get("policy_gate", {}) if isinstance(value.get("policy_gate"), dict) else {}
        tool_execution = value.get("tool_execution", {}) if isinstance(value.get("tool_execution"), dict) else {}
        return {
            "schema": value.get("schema"),
            "status": value.get("status"),
            "issues": value.get("issues", []),
            "policy_status": policy_gate.get("status"),
            "completed_tools": tool_execution.get("completed_tools", []),
        }
    if key == "memory_write":
        candidate = value.get("review_candidate", {}) if isinstance(value.get("review_candidate"), dict) else {}
        return {
            "schema": value.get("schema"),
            "decision": value.get("decision"),
            "target": value.get("target"),
            "automatic_promotion_performed": value.get("automatic_promotion_performed", False),
            "review_candidate_schema": candidate.get("schema"),
            "review_candidate_id": candidate.get("candidate_id"),
        }
    if key == "runtime_observability":
        context = value.get("context", {}) if isinstance(value.get("context"), dict) else {}
        return {
            "schema": value.get("schema"),
            "selected_memory_count": context.get("selected_memory_count"),
            "prompt_context_estimated_tokens": context.get("prompt_context_estimated_tokens"),
            "full_session_replay_used": context.get("full_session_replay_used"),
            "private_reasoning_trace_stored": context.get("private_reasoning_trace_stored", False),
        }
    if key == "active_memory_route":
        health = value.get("memory_health", {}) if isinstance(value.get("memory_health"), dict) else {}
        return {
            "schema": value.get("schema"),
            "compression_policy": value.get("compression_policy"),
            "selected_experience_count": health.get("selected_experience_count"),
            "private_reasoning_trace_policy": value.get("private_reasoning_trace"),
        }
    return _bounded_public_reference(value)


def _bounded_public_reference(value: Any, *, depth: int = 0) -> Any:
    if depth >= MAX_SAFE_REFERENCE_DEPTH:
        return {"omitted": type(value).__name__, "reason": "max_safe_reference_depth"}
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in list(value.items())[:MAX_SAFE_REFERENCE_DICT_ITEMS]:
            key_text = str(key)
            if key_text in SAFE_REFERENCE_OMIT_KEYS:
                continue
            if key_text in HEAVY_SAFE_REFERENCE_KEYS or key_text in OUTPUT_REFERENCE_KEYS:
                safe[key_text] = _summary_of_named_packet(key_text, item)
            else:
                safe[key_text] = _bounded_public_reference(_sanitize_for_public_reference(item), depth=depth + 1)
        if len(value) > MAX_SAFE_REFERENCE_DICT_ITEMS:
            safe["omitted_key_count"] = len(value) - MAX_SAFE_REFERENCE_DICT_ITEMS
        return safe
    if isinstance(value, list):
        items = [_bounded_public_reference(item, depth=depth + 1) for item in value[:MAX_SAFE_REFERENCE_LIST_ITEMS]]
        if len(value) > MAX_SAFE_REFERENCE_LIST_ITEMS:
            items.append({"omitted_item_count": len(value) - MAX_SAFE_REFERENCE_LIST_ITEMS})
        return items
    if isinstance(value, str):
        sanitized = _sanitize_for_public_reference(value)
        if isinstance(sanitized, str) and len(sanitized) > MAX_SAFE_REFERENCE_TEXT_CHARS:
            return sanitized[:MAX_SAFE_REFERENCE_TEXT_CHARS].rstrip() + "..."
        return sanitized
    return value


def _contribution_reference(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "projection_id": item.get("projection_id"),
        "projection_of": item.get("projection_of"),
        "role_id": item.get("role_id"),
        "role_name": item.get("role_name"),
        "focus": item.get("focus"),
        "consciousness": item.get("consciousness"),
        "run_status": item.get("run_status"),
        "workspace_run": _summary_of_named_packet("workspace_run", item.get("workspace_run", {})),
        "learning_update": _summary_of_named_packet("learning_update", item.get("learning_update", {})),
    }


def _safe_event_reference(source: str, event: dict[str, Any]) -> dict[str, Any]:
    reference = _bounded_public_reference(event)
    if isinstance(event.get("contributions"), list):
        reference["contributions"] = [
            _contribution_reference(item)
            for item in event["contributions"][:MAX_SAFE_REFERENCE_LIST_ITEMS]
            if isinstance(item, dict)
        ]
        if len(event["contributions"]) > MAX_SAFE_REFERENCE_LIST_ITEMS:
            reference["contributions"].append(
                {"omitted_item_count": len(event["contributions"]) - MAX_SAFE_REFERENCE_LIST_ITEMS}
            )
    reference["source"] = source
    reference["event_digest_sha256"] = _stable_digest(_bounded_public_reference(event, depth=1))
    reference["safe_reference_policy"] = {
        "bounded_summary_only": True,
        "full_session_replay_stored": False,
        "private_reasoning_trace_policy": "do_not_store",
    }
    return reference


def _skills_from_event(source: str, event: dict[str, Any], event_reference: dict[str, Any] | None = None) -> list[str]:
    text = json.dumps(event_reference or _safe_event_reference(source, event), ensure_ascii=False, sort_keys=True)
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
    if source == "simulation_rollout_winner" or "simulation_rollout" in text or "rollout" in text:
        skills.append("parallel_rollout_review")
        skills.append("reviewed_simulation_learning")
    if "정체성" in text or "부모" in text or "가족" in text or "개인정보" in text:
        skills.append("identity_boundary_conversation")
    if "일반 대화" in text or "자연스럽" in text or "말투" in text:
        skills.append("natural_dialogue_style")
    if source == "workspace_agent_run" or "trace.jsonl" in text or "result_summary" in text:
        skills.append("workspace_artifact_trace")
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
    event_reference = _safe_event_reference(source, event)
    entry = {
        "id": _experience_id(ledger["owner"], source, event_reference, quality_label),
        "source": source,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": _summarize_event(source, event),
        "quality_label": quality_label,
        "safe_reference": event_reference,
    }

    if _quality_passes(quality_label):
        skills = _skills_from_event(source, event, event_reference)
        entry["promoted_skills"] = skills
        ledger["promoted_experiences"].append(entry)
        for skill in skills:
            if skill not in ledger["skill_candidates"]:
                ledger["skill_candidates"].append(skill)
    else:
        entry["flags"] = ["needs_human_review", "do_not_promote_to_reasoning_kernel"]
        ledger["quarantined_experiences"].append(entry)
    ledger["memory_lifecycle"] = audit_learning_ledger(ledger)
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


def refresh_learning_ledger(ledger: dict[str, Any], *, objective: str | None = None) -> dict[str, Any]:
    """Rebuild derived learning-ledger fields after a maintenance operation."""

    skills: list[str] = []
    for entry in ledger.get("promoted_experiences", []):
        for skill in entry.get("promoted_skills", []):
            if skill not in skills:
                skills.append(skill)
    ledger["skill_candidates"] = skills
    ledger["reasoning_kernel"] = build_reasoning_kernel(ledger)
    ledger["memory_lifecycle"] = audit_learning_ledger(ledger, objective=objective)
    return ledger


def delete_learning_experience(
    ledger: dict[str, Any],
    *,
    experience_id: str,
    requested_by: str,
    reason: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    removed: dict[str, Any] | None = None
    removed_bucket = ""
    for bucket in ("promoted_experiences", "quarantined_experiences"):
        remaining = []
        for entry in ledger.get(bucket, []):
            if entry.get("id") == experience_id and removed is None:
                removed = entry
                removed_bucket = bucket
            else:
                remaining.append(entry)
        ledger[bucket] = remaining
    if removed is None:
        raise ValueError(f"learning experience not found: {experience_id}")

    tombstone = {
        "schema": "paideia-memory-deletion-tombstone/v1",
        "deleted_at_utc": datetime.now(timezone.utc).isoformat(),
        "experience_id": experience_id,
        "source_bucket": removed_bucket,
        "source": removed.get("source"),
        "summary": removed.get("summary"),
        "removed_promoted_skills": removed.get("promoted_skills", []),
        "requested_by": requested_by,
        "reason": reason,
        "safe_reference_removed": True,
        "policy": "manual_delete_request_with_audit_log_required",
    }
    ledger.setdefault("memory_deletion_log", []).append(tombstone)
    return refresh_learning_ledger(ledger), tombstone


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
        "memory_lifecycle": audit_learning_ledger(ledger, objective=objective),
    }
