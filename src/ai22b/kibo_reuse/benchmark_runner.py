from __future__ import annotations

from statistics import NormalDist
from typing import Any, Iterable

from .token_telemetry import summarize_token_usage


PATTERN_LOOP_BENCHMARK_REPORT_SCHEMA = "paideia-pattern-loop-benchmark-report/v1"

DEFAULT_GROUPS = ("A0", "A1", "A2", "A3", "A4", "A5")


def build_pattern_loop_benchmark_report(
    config: dict[str, Any],
    runs: Iterable[dict[str, Any]],
    *,
    token_receipts: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    run_rows = [dict(row) for row in runs]
    receipt_rows = [dict(row) for row in token_receipts]
    groups = tuple(config.get("groups") or DEFAULT_GROUPS)
    group_metrics = {group: _group_metrics(group, run_rows, receipt_rows) for group in groups}
    comparison = _compare_groups(
        group_metrics.get(str(config.get("baseline_group") or "A2"), _empty_group("A2")),
        group_metrics.get(str(config.get("full_loop_group") or "A5"), _empty_group("A5")),
    )
    thresholds = {
        "min_success_lift": float(config.get("min_success_lift", 0.10)),
        "min_token_saving": float(config.get("min_token_saving", 0.25)),
        "max_critical_safety_violations": int(config.get("max_critical_safety_violations", 0)),
    }
    critical_safety_violations = sum(int(row.get("critical_safety_violations") or 0) for row in run_rows)
    token_saving_passed = comparison["net_token_saving_ratio"] >= thresholds["min_token_saving"]
    success_lift_passed = comparison["success_rate_delta"] >= thresholds["min_success_lift"]
    safety_passed = critical_safety_violations <= thresholds["max_critical_safety_violations"]
    actual_token_comparison = comparison["actual_token_receipt_comparison"]
    status = "passed" if safety_passed and success_lift_passed and token_saving_passed and actual_token_comparison else "blocked"
    return {
        "schema": PATTERN_LOOP_BENCHMARK_REPORT_SCHEMA,
        "benchmark_id": str(config.get("benchmark_id") or "pattern-loop-benchmark"),
        "status": status,
        "groups": group_metrics,
        "benchmark_comparison": comparison,
        "token_cost_metrics": summarize_token_usage(receipt_rows),
        "safety_metrics": {
            "critical_safety_violations": critical_safety_violations,
            "passed": safety_passed,
        },
        "thresholds": thresholds,
        "checks": {
            "success_lift_passed": success_lift_passed,
            "token_saving_passed": token_saving_passed,
            "actual_token_receipt_comparison": actual_token_comparison,
            "critical_safety_violation_free": safety_passed,
        },
        "known_limitations": list(config.get("known_limitations") or []),
    }


def _group_metrics(group: str, runs: list[dict[str, Any]], receipts: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in runs if str(row.get("group")) == group]
    run_ids = {str(row.get("run_id")) for row in rows if row.get("run_id")}
    receipt_rows = [receipt for receipt in receipts if str(receipt.get("run_id")) in run_ids]
    successes = sum(1 for row in rows if row.get("success") is True)
    count = len(rows)
    success_rate = successes / count if count else 0.0
    actual_receipt_rows = [receipt for receipt in receipt_rows if receipt.get("estimated") is not True]
    return {
        "group": group,
        "run_count": count,
        "success_count": successes,
        "success_rate": round(success_rate, 4),
        "success_rate_ci95": _wilson_interval(successes, count),
        "failure_recurrence_count": sum(int(row.get("failure_recurrence_count") or 0) for row in rows),
        "critical_safety_violations": sum(int(row.get("critical_safety_violations") or 0) for row in rows),
        "token_usage": summarize_token_usage(receipt_rows),
        "actual_token_usage": summarize_token_usage(actual_receipt_rows),
    }


def _compare_groups(baseline: dict[str, Any], full_loop: dict[str, Any]) -> dict[str, Any]:
    baseline_tokens = baseline["actual_token_usage"]["total_tokens"]
    full_loop_tokens = full_loop["actual_token_usage"]["total_tokens"]
    if baseline_tokens > 0:
        token_saving = max(0.0, (baseline_tokens - full_loop_tokens) / baseline_tokens)
    else:
        token_saving = 0.0
    return {
        "baseline_group": baseline["group"],
        "full_loop_group": full_loop["group"],
        "baseline_success_rate": baseline["success_rate"],
        "full_loop_success_rate": full_loop["success_rate"],
        "success_rate_delta": round(full_loop["success_rate"] - baseline["success_rate"], 4),
        "baseline_total_tokens": baseline_tokens,
        "full_loop_total_tokens": full_loop_tokens,
        "actual_token_receipt_comparison": baseline["actual_token_usage"]["receipt_count"] > 0
        and full_loop["actual_token_usage"]["receipt_count"] > 0,
        "net_token_saving_ratio": round(min(0.95, token_saving), 4),
        "failure_recurrence_delta": full_loop["failure_recurrence_count"] - baseline["failure_recurrence_count"],
    }


def _wilson_interval(successes: int, count: int, *, confidence: float = 0.95) -> list[float]:
    if count <= 0:
        return [0.0, 0.0]
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    phat = successes / count
    denominator = 1 + z * z / count
    center = (phat + z * z / (2 * count)) / denominator
    margin = z * ((phat * (1 - phat) + z * z / (4 * count)) / count) ** 0.5 / denominator
    return [round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)]


def _empty_group(group: str) -> dict[str, Any]:
    return {
        "group": group,
        "run_count": 0,
        "success_count": 0,
        "success_rate": 0.0,
        "success_rate_ci95": [0.0, 0.0],
        "failure_recurrence_count": 0,
        "critical_safety_violations": 0,
        "token_usage": summarize_token_usage([]),
        "actual_token_usage": summarize_token_usage([]),
    }
