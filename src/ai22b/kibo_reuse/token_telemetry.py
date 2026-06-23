from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

from .token_meter import estimate_tokens
from .v2_artifacts import stable_id, v2_header


TOKEN_USAGE_RECEIPT_BUILD_RESULT_SCHEMA = "paideia-token-usage-receipt-build-result/v1"


def build_token_usage_receipt(
    manifest: dict[str, Any],
    *,
    run_id: str,
    provider: str,
    model: str,
    call_purpose: str,
    usage: dict[str, Any] | None = None,
    prompt: Any = None,
    completion: Any = None,
    monetary_cost: float | None = None,
    latency_ms: int | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    usage_row = dict(usage or {})
    input_tokens = _optional_int(usage_row.get("input_tokens") or usage_row.get("prompt_tokens"))
    output_tokens = _optional_int(usage_row.get("output_tokens") or usage_row.get("completion_tokens"))
    cached_input_tokens = _optional_int(usage_row.get("cached_input_tokens") or usage_row.get("cached_tokens"))
    estimated = usage_row.get("estimated")
    if input_tokens is None and prompt is not None:
        input_tokens = estimate_tokens(prompt)
        estimated = True
    if output_tokens is None and completion is not None:
        output_tokens = estimate_tokens(completion)
        estimated = True
    if estimated is None:
        estimated = input_tokens is None and output_tokens is None
    estimation_method = usage_row.get("estimation_method")
    if estimated and not estimation_method:
        estimation_method = "paideia_local_token_estimate"
    cost = _optional_float(usage_row.get("monetary_cost") if "monetary_cost" in usage_row else monetary_cost)
    latency = _optional_int(usage_row.get("latency_ms") if "latency_ms" in usage_row else latency_ms)
    created = created_at or str(usage_row.get("created_at") or "") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt_id = stable_id(
        "token-usage",
        run_id,
        provider,
        model,
        call_purpose,
        input_tokens,
        output_tokens,
        cached_input_tokens,
        created,
    )
    return {
        **v2_header("token_usage_receipt", manifest),
        "receipt_id": receipt_id,
        "run_id": _required_string(run_id, "run_id"),
        "provider": _required_string(provider, "provider"),
        "model": _required_string(model, "model"),
        "call_purpose": _required_string(call_purpose, "call_purpose"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached_input_tokens,
        "estimated": bool(estimated),
        "estimation_method": estimation_method if estimation_method is None else str(estimation_method),
        "monetary_cost": cost,
        "latency_ms": latency,
        "created_at": created,
    }


def build_token_usage_receipt_result(manifest: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    receipt = build_token_usage_receipt(manifest, **kwargs)
    return {
        "schema": TOKEN_USAGE_RECEIPT_BUILD_RESULT_SCHEMA,
        "token_usage_receipt": receipt,
        "actual_usage_available": not receipt["estimated"],
    }


def summarize_token_usage(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    total_input = sum(item.get("input_tokens") or 0 for item in receipts)
    total_output = sum(item.get("output_tokens") or 0 for item in receipts)
    total_cached = sum(item.get("cached_input_tokens") or 0 for item in receipts)
    total_cost = sum(item.get("monetary_cost") or 0.0 for item in receipts)
    estimated_count = sum(1 for item in receipts if item.get("estimated") is True)
    actual_count = len(receipts) - estimated_count
    return {
        "receipt_count": len(receipts),
        "actual_receipt_count": actual_count,
        "estimated_receipt_count": estimated_count,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cached_input_tokens": total_cached,
        "total_tokens": total_input + total_output,
        "monetary_cost": round(total_cost, 6),
    }


def _required_string(value: object, field: str) -> str:
    text = str(value or "")
    if not text:
        raise ValueError(f"{field} must be a non-empty string")
    return text


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric >= 0 else None


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0:
        return None
    return numeric
