from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any


MEMORY_LIFECYCLE_SCHEMA = "paideia-memory-lifecycle/v1"
MEMORY_LIFECYCLE_STATUS_CARD_SCHEMA = "paideia-memory-lifecycle-status-card/v1"

WINDOWS_ABSOLUTE_PATH = re.compile(r"[A-Za-z]:\\")
POSIX_LOCAL_PATH = re.compile(r"(/home/|/Users/|/tmp/|/var/folders/|/private/var/folders/)[^\s\"']+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[-.\s])?(?:\d{2,4}[-.\s]){2,3}\d{3,4}(?!\d)")
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]+|api[_-]?key\s*[:=])", re.I)
PRIVATE_REASONING_KEYS = {
    "chain_of_thought",
    "private_reasoning_trace",
    "hidden_reasoning",
    "reasoning_trace",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entry_text(entries: list[dict[str, Any]]) -> str:
    return json.dumps(entries, ensure_ascii=False, sort_keys=True)


def _safe_references(entries: list[dict[str, Any]]) -> list[Any]:
    return [entry.get("safe_reference", {}) for entry in entries]


def _contains_private_reasoning(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in PRIVATE_REASONING_KEYS:
                return True
            if _contains_private_reasoning(item):
                return True
    if isinstance(value, list):
        return any(_contains_private_reasoning(item) for item in value)
    return False


def _keyword_set(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9가-힣_]+", text.lower())
    return {word for word in words if len(word) >= 2}


def _retrieval_quality(ledger: dict[str, Any], objective: str | None) -> dict[str, Any]:
    promoted = ledger.get("promoted_experiences", [])
    if not objective:
        return {
            "objective_supplied": False,
            "selected_candidate_count": 0,
            "route_is_degraded": len(promoted) == 0,
            "quality_note": "supply_objective_to_score_retrieval_quality",
        }
    objective_terms = _keyword_set(objective)
    scored = []
    for entry in promoted:
        haystack = " ".join(
            [
                str(entry.get("summary", "")),
                json.dumps(entry.get("safe_reference", {}), ensure_ascii=False),
                " ".join(entry.get("promoted_skills", [])),
            ]
        )
        score = len(objective_terms & _keyword_set(haystack))
        if score:
            scored.append({"experience_id": entry.get("id"), "score": score})
    return {
        "objective_supplied": True,
        "selected_candidate_count": len(scored),
        "route_is_degraded": not scored,
        "top_scores": sorted(scored, key=lambda item: item["score"], reverse=True)[:3],
    }


def audit_learning_ledger(ledger: dict[str, Any], *, objective: str | None = None) -> dict[str, Any]:
    promoted = ledger.get("promoted_experiences", [])
    quarantined = ledger.get("quarantined_experiences", [])
    safe_reference_blob = _entry_text(_safe_references(promoted + quarantined))
    issues: list[dict[str, Any]] = []

    if _contains_private_reasoning(_safe_references(promoted + quarantined)):
        issues.append(
            {
                "id": "private_reasoning_in_safe_reference",
                "severity": "error",
                "message": "safe_reference must not store hidden chain-of-thought or private reasoning traces.",
            }
        )
    if WINDOWS_ABSOLUTE_PATH.search(safe_reference_blob) or POSIX_LOCAL_PATH.search(safe_reference_blob):
        issues.append(
            {
                "id": "local_absolute_path_unredacted",
                "severity": "error",
                "message": "local absolute paths must be redacted before memory promotion or quarantine.",
            }
        )
    if SECRET_RE.search(safe_reference_blob):
        issues.append(
            {
                "id": "secret_like_value_in_memory",
                "severity": "error",
                "message": "API keys, bearer tokens, or credential-like values must not be stored in memory.",
            }
        )
    pii_hits = []
    if EMAIL_RE.search(safe_reference_blob):
        pii_hits.append("email")
    if PHONE_RE.search(safe_reference_blob):
        pii_hits.append("phone_like_number")
    if pii_hits:
        issues.append(
            {
                "id": "possible_pii_in_memory",
                "severity": "warning",
                "message": "possible personal data requires owner review before public export.",
                "matches": pii_hits,
            }
        )

    blocking = [issue for issue in issues if issue["severity"] == "error"]
    return {
        "schema": MEMORY_LIFECYCLE_SCHEMA,
        "created_at_utc": _now(),
        "owner": ledger.get("owner"),
        "policy_version": "memory_lifecycle_p0_v1",
        "status": "passed" if not blocking else "failed",
        "write_policy": {
            "raw_private_reasoning": "forbidden",
            "stored_form": "reviewed_summary_safe_reference_and_promoted_skills",
            "full_session_replay": "forbidden",
            "local_storage": "ledger_json_and_jsonl_logs",
        },
        "promotion_policy": {
            "minimum_score": 80,
            "allowed_review_status": ["verified", "passed", "approved"],
            "requires_boss_or_committee_review": True,
            "failed_or_low_quality_destination": "quarantine",
        },
        "retention_policy": {
            "promoted": "retain_until_owner_deletion_or_migration",
            "quarantined": "retain_for_local_review_not_active_context",
            "deletion": "manual_delete_request_with_audit_log_required",
            "public_export": "summary_only_after_hygiene_check",
        },
        "recovery_policy": {
            "source_of_truth": "learning_ledger.json",
            "append_logs": ["post_hire_learning_log.jsonl", "employment_goal_log.jsonl"],
            "corruption_recovery": "restore_last_valid_ledger_then_replay_reviewed_logs",
            "migration": "schema_versioned_summary_only_migration",
        },
        "retrieval_policy": {
            "active_context": "promoted_experiences_only",
            "quarantine": "excluded_from_active_context",
            "selection_basis": "objective_keywords_promoted_skills_and_reviewed_summaries",
            "max_default_selected_memories": 3,
        },
        "counts": {
            "promoted": len(promoted),
            "quarantined": len(quarantined),
            "skill_candidates": len(ledger.get("skill_candidates", [])),
            "issues": len(issues),
        },
        "retrieval_quality": _retrieval_quality(ledger, objective),
        "checks": {
            "private_reasoning_trace_not_stored": not _contains_private_reasoning(_safe_references(promoted + quarantined)),
            "local_absolute_paths_redacted": not (WINDOWS_ABSOLUTE_PATH.search(safe_reference_blob) or POSIX_LOCAL_PATH.search(safe_reference_blob)),
            "secret_like_values_absent": not bool(SECRET_RE.search(safe_reference_blob)),
            "quarantined_excluded_from_active_context": True,
            "deletion_requires_manual_audit": True,
        },
        "issues": issues,
    }


def _selected_active_context_ids(active_memory_route: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(active_memory_route, dict):
        return {
            "selected_experience_ids": [],
            "selected_node_ids": [],
            "selected_count": 0,
            "route_is_degraded": True,
        }
    selected_memories = active_memory_route.get("selected_memories", [])
    selected_nodes = active_memory_route.get("selected_nodes", [])
    selected_experience_ids = [
        str(item.get("experience_id"))
        for item in selected_memories
        if isinstance(item, dict) and item.get("experience_id")
    ]
    selected_node_ids = [
        str(item.get("id"))
        for item in selected_nodes
        if isinstance(item, dict) and item.get("id")
    ]
    selected_node_ids.extend(str(item) for item in active_memory_route.get("selected_node_ids", []) if item)
    selected_node_ids = list(dict.fromkeys(selected_node_ids))
    selected_count = max(
        len(selected_experience_ids),
        len(selected_node_ids),
        len(selected_memories) if isinstance(selected_memories, list) else 0,
        len(selected_nodes) if isinstance(selected_nodes, list) else 0,
    )
    memory_health = active_memory_route.get("memory_health", {})
    route_is_degraded = (
        bool(memory_health.get("route_is_degraded"))
        if isinstance(memory_health, dict) and "route_is_degraded" in memory_health
        else selected_count == 0
    )
    return {
        "selected_experience_ids": selected_experience_ids,
        "selected_node_ids": selected_node_ids,
        "selected_count": selected_count,
        "route_is_degraded": route_is_degraded,
    }


def build_memory_lifecycle_status_card(
    ledger: dict[str, Any],
    *,
    active_memory_route: dict[str, Any] | None = None,
    objective: str | None = None,
    learning_update: dict[str, Any] | None = None,
    source: str = "active_memory_route",
) -> dict[str, Any]:
    """Build a compact operator card for memory routing and write safety."""

    route_lifecycle = (
        active_memory_route.get("memory_lifecycle", {})
        if isinstance(active_memory_route, dict) and isinstance(active_memory_route.get("memory_lifecycle"), dict)
        else {}
    )
    lifecycle = route_lifecycle if route_lifecycle.get("schema") == MEMORY_LIFECYCLE_SCHEMA else audit_learning_ledger(ledger, objective=objective)
    selected = _selected_active_context_ids(active_memory_route)
    checks = lifecycle.get("checks", {}) if isinstance(lifecycle.get("checks"), dict) else {}
    retrieval_quality = (
        lifecycle.get("retrieval_quality", {}) if isinstance(lifecycle.get("retrieval_quality"), dict) else {}
    )
    issues = lifecycle.get("issues", []) if isinstance(lifecycle.get("issues"), list) else []
    blocking = [issue for issue in issues if isinstance(issue, dict) and issue.get("severity") == "error"]
    learning = learning_update if isinstance(learning_update, dict) else {}
    quarantined_excluded = checks.get("quarantined_excluded_from_active_context") is True
    if lifecycle.get("status") == "failed" or blocking or not quarantined_excluded:
        status = "failed"
    elif issues or selected["route_is_degraded"]:
        status = "needs_review"
    else:
        status = "passed"

    return {
        "schema": MEMORY_LIFECYCLE_STATUS_CARD_SCHEMA,
        "status": status,
        "source": source,
        "owner": ledger.get("owner"),
        "created_at_utc": _now(),
        "objective_supplied": bool(objective),
        "counts": {
            "promoted": lifecycle.get("counts", {}).get("promoted", len(ledger.get("promoted_experiences", [])))
            if isinstance(lifecycle.get("counts"), dict)
            else len(ledger.get("promoted_experiences", [])),
            "quarantined": lifecycle.get("counts", {}).get("quarantined", len(ledger.get("quarantined_experiences", [])))
            if isinstance(lifecycle.get("counts"), dict)
            else len(ledger.get("quarantined_experiences", [])),
            "selected": selected["selected_count"],
            "issues": len(issues),
        },
        "active_context": {
            "selected_experience_ids": selected["selected_experience_ids"],
            "selected_node_ids": selected["selected_node_ids"],
            "selected_count": selected["selected_count"],
            "quarantined_excluded": quarantined_excluded,
            "compression_policy": (
                active_memory_route.get("compression_policy")
                if isinstance(active_memory_route, dict)
                else None
            )
            or "summaries_and_skills_only",
            "route_is_degraded": selected["route_is_degraded"],
        },
        "learning": {
            "decision": learning.get("decision", "not_requested"),
            "ledger_write_performed": bool(learning.get("ledger_write_performed", False)),
            "latest_experience_id": learning.get("latest_experience_id"),
            "automatic_promotion_performed": bool(learning.get("automatic_promotion_performed", False)),
            "promotion_gate": "explicit_review_or_learn_from_chat_request_required",
        },
        "hygiene": {
            "private_reasoning_trace_not_stored": checks.get("private_reasoning_trace_not_stored"),
            "local_absolute_paths_redacted": checks.get("local_absolute_paths_redacted"),
            "secret_like_values_absent": checks.get("secret_like_values_absent"),
            "raw_provider_payload_saved": False,
            "full_session_replay_stored": False,
        },
        "retrieval_quality": retrieval_quality,
        "issues": issues,
        "user_visible_summary": {
            "ko": (
                "기억 경로가 통과했습니다. 검증된 요약 기억만 active context에 들어갔고 격리 기억은 제외됐습니다."
                if status == "passed"
                else "기억 경로 검토가 필요합니다. 선택된 기억, 격리 제외, 개인정보/secret 위생을 확인하세요."
                if status == "needs_review"
                else "기억 생명주기 검사가 실패했습니다. 오류가 해결되기 전에는 이 기억 경로를 사용하지 마세요."
            ),
            "en": (
                "Memory routing passed. Only reviewed summary memory entered active context, while quarantined memory stayed excluded."
                if status == "passed"
                else "Memory routing needs review. Inspect selected memory, quarantine exclusion, and privacy/secret hygiene."
                if status == "needs_review"
                else "Memory lifecycle checks failed. Do not use this memory route until the errors are resolved."
            ),
        },
        "next_actions": (
            ["Use this active memory route for the current task and keep future writes review-gated."]
            if status == "passed"
            else [
                "Review lifecycle issues before promoting or exporting memory.",
                "Run memory lifecycle maintenance if quarantine, deletion, or recovery evidence is stale.",
            ]
            if status == "needs_review"
            else [
                "Remove or redact unsafe memory fields, then rebuild the active route.",
                "Do not promote new memory until lifecycle checks pass.",
            ]
        ),
    }
