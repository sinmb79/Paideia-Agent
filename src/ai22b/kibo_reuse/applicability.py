from __future__ import annotations

import re
from typing import Any, Iterable

from .models import FailureMemory, KiboRecord, TaskFingerprint


APPLICABILITY_REPORT_SCHEMA = "paideia-kibo-applicability-report/v1"

DOMAIN_GROUPS = (
    {"investment_research", "securities_research", "finance", "valuation"},
    {"software_agent_engineering", "coding", "software", "devtools"},
)
TASK_TYPE_GROUPS = (
    {"comparative_analysis", "research", "question_answering"},
    {"implementation", "implementation_planning"},
)
BLOCKING_FAILURE_SEVERITIES = {"high", "severe", "critical", "catastrophic", "fatal"}
BLOCKING_FAILURE_ERROR_TYPES = {
    "freshness_error",
    "stale_data_reuse",
    "safety_violation",
    "unsafe_reuse",
    "domain_mismatch",
}


def evaluate_kibo_applicability(
    task: TaskFingerprint,
    record: KiboRecord,
    *,
    failures: Iterable[FailureMemory] = (),
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if not _compatible_value(task.domain, record.domain, DOMAIN_GROUPS):
        issues.append({"code": "domain_mismatch", "message": f"{record.domain} cannot satisfy {task.domain}"})
    if not _compatible_value(task.task_type, record.task_type, TASK_TYPE_GROUPS):
        issues.append({"code": "task_type_mismatch", "message": f"{record.task_type} cannot satisfy {task.task_type}"})
    missing_capabilities = _missing_capabilities(task, record)
    for capability in missing_capabilities:
        issues.append({"code": "missing_required_capability", "message": capability})
    if task.freshness_required and any("stale" in item.casefold() for item in record.failure_modes):
        warnings.append({"code": "freshness_caveat", "message": "record has stale-data failure mode"})
    for failure in failures:
        if _failure_blocks(task, record, failure):
            issues.append(
                {
                    "code": "failure_memory_blocker",
                    "message": f"{failure.failure_id}:{failure.error_type}:{failure.severity}",
                }
            )
        elif _failure_warns(task, failure):
            warnings.append({"code": "failure_memory_near_miss", "message": failure.failure_id})
    return {
        "schema": APPLICABILITY_REPORT_SCHEMA,
        "task_id": task.task_id,
        "kibo_id": record.kibo_id,
        "applicable": not issues,
        "issues": issues,
        "warnings": warnings,
    }


def filter_applicable_kibo_records(
    task: TaskFingerprint,
    records: Iterable[KiboRecord],
    *,
    failures: Iterable[FailureMemory] = (),
) -> tuple[list[KiboRecord], list[dict[str, Any]]]:
    accepted: list[KiboRecord] = []
    reports: list[dict[str, Any]] = []
    failure_rows = list(failures)
    for record in records:
        report = evaluate_kibo_applicability(task, record, failures=failure_rows)
        reports.append(report)
        if report["applicable"]:
            accepted.append(record)
    return accepted, reports


def _compatible_value(left: str, right: str, groups: tuple[set[str], ...]) -> bool:
    normalized_left = left.casefold()
    normalized_right = right.casefold()
    if normalized_left == normalized_right:
        return True
    return any(normalized_left in group and normalized_right in group for group in groups)


def _missing_capabilities(task: TaskFingerprint, record: KiboRecord) -> list[str]:
    provided = {_normalize(item) for item in (*record.required_inputs, *record.reusable_logic)}
    missing: list[str] = []
    for capability in task.required_capabilities:
        if _normalize(capability) not in provided:
            missing.append(capability)
    return missing


def _failure_blocks(task: TaskFingerprint, record: KiboRecord, failure: FailureMemory) -> bool:
    if not _blocking_failure(failure):
        return False
    if not _failure_applies_to_record(record, failure):
        return False
    if not failure.trigger_conditions:
        return True
    return all(_condition_satisfied(task, condition) for condition in failure.trigger_conditions)


def _failure_warns(task: TaskFingerprint, failure: FailureMemory) -> bool:
    return any(_condition_near_match(task, condition) for condition in failure.trigger_conditions)


def _blocking_failure(failure: FailureMemory) -> bool:
    return failure.severity.casefold() in BLOCKING_FAILURE_SEVERITIES or failure.error_type.casefold() in BLOCKING_FAILURE_ERROR_TYPES


def _failure_applies_to_record(record: KiboRecord, failure: FailureMemory) -> bool:
    pattern_id = _normalize(failure.pattern_id)
    if pattern_id == "*":
        return True
    identifiers = {
        _normalize(record.kibo_id),
        _normalize(record.source_run_id),
        *(_normalize(ref) for ref in record.evidence_refs),
    }
    if pattern_id in identifiers:
        return True
    if any(pattern_id and (pattern_id in identifier or identifier in pattern_id) for identifier in identifiers):
        return True
    return pattern_id not in {"", "pattern", "none", "null"}


def _condition_satisfied(task: TaskFingerprint, condition: str) -> bool:
    normalized = _normalize(condition)
    exact_values = {_normalize(item) for item in (*task.required_capabilities, *task.constraints)}
    if normalized in exact_values:
        return True
    return len(normalized) >= 6 and normalized in _normalize(task.intent)


def _condition_near_match(task: TaskFingerprint, condition: str) -> bool:
    condition_tokens = _tokens(condition)
    if not condition_tokens:
        return False
    task_tokens = _tokens([task.intent, task.constraints, task.required_capabilities])
    return len(condition_tokens & task_tokens) >= 2


def _tokens(value: Any) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value or "")
    return {_normalize(token) for token in re.findall(r"\w+", text, flags=re.UNICODE)}


def _normalize(value: object) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
