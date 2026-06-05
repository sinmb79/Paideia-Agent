from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any


MEMORY_LIFECYCLE_SCHEMA = "paideia-memory-lifecycle/v1"

WINDOWS_ABSOLUTE_PATH = re.compile(r"[A-Za-z]:\\")
POSIX_HOME_PATH = re.compile(r"(/home/|/Users/)[^\s\"']+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\d{2,4}[-.\s]?){2,3}\d{3,4}(?!\d)")
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
    if WINDOWS_ABSOLUTE_PATH.search(safe_reference_blob) or POSIX_HOME_PATH.search(safe_reference_blob):
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
            "local_absolute_paths_redacted": not (WINDOWS_ABSOLUTE_PATH.search(safe_reference_blob) or POSIX_HOME_PATH.search(safe_reference_blob)),
            "secret_like_values_absent": not bool(SECRET_RE.search(safe_reference_blob)),
            "quarantined_excluded_from_active_context": True,
            "deletion_requires_manual_audit": True,
        },
        "issues": issues,
    }
