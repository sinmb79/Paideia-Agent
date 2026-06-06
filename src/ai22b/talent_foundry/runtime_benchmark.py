from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.runtime_observability import (
    RUNTIME_OBSERVABILITY_SCHEMA,
    estimate_tokens,
)


RUNTIME_OBSERVABILITY_COMPARISON_SCHEMA = "paideia-runtime-observability-comparison/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _path_fingerprint(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).casefold().encode("utf-8")).hexdigest()


def _iter_observability_sources(run: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    sources: list[tuple[str, dict[str, Any]]] = []

    def add(label: str, candidate: Any) -> None:
        if isinstance(candidate, dict) and candidate.get("schema") == RUNTIME_OBSERVABILITY_SCHEMA:
            sources.append((label, candidate))

    add("run.runtime_observability", run.get("runtime_observability"))
    base = run.get("base_agent_run") if isinstance(run.get("base_agent_run"), dict) else {}
    add("base_agent_run.runtime_observability", base.get("runtime_observability"))
    workspace = run.get("workspace_run") if isinstance(run.get("workspace_run"), dict) else {}
    add("workspace_run.runtime_observability", workspace.get("runtime_observability"))
    workspace_base = (
        workspace.get("base_agent_run")
        if isinstance(workspace.get("base_agent_run"), dict)
        else {}
    )
    add("workspace_run.base_agent_run.runtime_observability", workspace_base.get("runtime_observability"))
    return sources


def _privacy_flags(observability: dict[str, Any]) -> dict[str, bool]:
    context = observability.get("context", {}) if isinstance(observability.get("context"), dict) else {}
    privacy = observability.get("privacy", {}) if isinstance(observability.get("privacy"), dict) else {}
    return {
        "full_session_replay_used": bool(context.get("full_session_replay_used")),
        "selected_memory_only": bool(context.get("selected_memory_only")),
        "private_reasoning_trace_stored": bool(privacy.get("private_reasoning_trace_stored")),
        "full_chat_or_session_replay_stored": bool(privacy.get("full_chat_or_session_replay_stored")),
        "local_absolute_paths_exported": bool(privacy.get("local_absolute_paths_exported")),
    }


def _run_status(run: dict[str, Any]) -> str | None:
    for key in ("run_status", "job_status", "cycle_status", "status"):
        value = run.get(key)
        if value:
            return str(value)
    return None


def _generic_prompt_wrapper_baseline_tokens(run: dict[str, Any]) -> int:
    """Estimate a prompt-wrapper baseline that replays the whole run artifact."""

    replay_packet = {
        "agent": run.get("agent") or run.get("employment_context") or {},
        "task": run.get("task") or run.get("objective") or run.get("job_spec") or {},
        "full_run_replay": run,
    }
    return estimate_tokens(replay_packet)


def _comparison_record(path: Path, run: dict[str, Any], source_label: str, observability: dict[str, Any]) -> dict[str, Any]:
    context = observability.get("context", {}) if isinstance(observability.get("context"), dict) else {}
    performance = (
        observability.get("performance_proxy", {})
        if isinstance(observability.get("performance_proxy"), dict)
        else {}
    )
    learning = (
        observability.get("learning_flow", {})
        if isinstance(observability.get("learning_flow"), dict)
        else {}
    )
    paideia_tokens = int(context.get("prompt_context_estimated_tokens") or 0)
    selected_memory_tokens = int(context.get("selected_memory_estimated_tokens") or 0)
    baseline_tokens = _generic_prompt_wrapper_baseline_tokens(run)
    savings = max(0, baseline_tokens - paideia_tokens)
    ratio = round(baseline_tokens / max(1, paideia_tokens), 3)
    return {
        "source_file_name": path.name,
        "source_path_fingerprint_sha256": _path_fingerprint(path),
        "source_label": source_label,
        "source_run_schema": run.get("schema"),
        "source_status": _run_status(run),
        "observability_digest_sha256": _digest(observability),
        "paideia_memory_board": {
            "prompt_context_estimated_tokens": paideia_tokens,
            "selected_memory_estimated_tokens": selected_memory_tokens,
            "selected_memory_count": int(context.get("selected_memory_count") or 0),
            "selected_memory_only": bool(context.get("selected_memory_only")),
            "full_session_replay_used": bool(context.get("full_session_replay_used")),
            "verification_status": performance.get("verification_status"),
            "llm_status": performance.get("llm_status"),
            "fallback_used": bool(performance.get("fallback_used")),
            "memory_write_decision": learning.get("memory_write_decision"),
        },
        "generic_prompt_wrapper_baseline": {
            "baseline_model": "whole_run_replay_into_prompt_proxy",
            "estimated_tokens": baseline_tokens,
            "assumed_full_session_replay": True,
            "assumed_selected_memory_routing": False,
        },
        "comparison": {
            "estimated_token_savings": savings,
            "context_reduction_ratio": ratio,
            "paideia_uses_less_context_than_replay_baseline": paideia_tokens < baseline_tokens,
        },
        "privacy": _privacy_flags(observability),
    }


def build_runtime_observability_comparison(
    run_paths: list[Path],
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    missing_observability: list[dict[str, str]] = []
    for path in run_paths:
        run = _read_json(path)
        sources = _iter_observability_sources(run)
        if not sources:
            missing_observability.append(
                {
                    "source_file_name": path.name,
                    "source_path_fingerprint_sha256": _path_fingerprint(path),
                    "reason": "runtime_observability_missing",
                }
            )
            continue
        for source_label, observability in sources:
            records.append(_comparison_record(path, run, source_label, observability))

    total_paideia = sum(
        item["paideia_memory_board"]["prompt_context_estimated_tokens"]
        for item in records
    )
    total_baseline = sum(
        item["generic_prompt_wrapper_baseline"]["estimated_tokens"]
        for item in records
    )
    privacy_ok = all(
        item["privacy"]["selected_memory_only"]
        and not item["privacy"]["full_session_replay_used"]
        and not item["privacy"]["private_reasoning_trace_stored"]
        and not item["privacy"]["full_chat_or_session_replay_stored"]
        and not item["privacy"]["local_absolute_paths_exported"]
        for item in records
    )
    comparison = {
        "schema": RUNTIME_OBSERVABILITY_COMPARISON_SCHEMA,
        "created_at_utc": _now(),
        "comparison_policy": {
            "purpose": "Compare Paideia memory-board runtime observability against a generic prompt-wrapper full-run replay proxy.",
            "baseline_is_proxy_not_provider_bill": True,
            "token_estimate": "ceil(characters/4)",
            "private_paths_stored": False,
            "private_reasoning_trace": "do_not_store",
        },
        "summary": {
            "record_count": len(records),
            "missing_observability_count": len(missing_observability),
            "paideia_prompt_context_estimated_tokens": total_paideia,
            "generic_prompt_wrapper_replay_estimated_tokens": total_baseline,
            "estimated_token_savings": max(0, total_baseline - total_paideia),
            "context_reduction_ratio": round(total_baseline / max(1, total_paideia), 3),
            "all_records_use_selected_memory_only": all(
                item["paideia_memory_board"]["selected_memory_only"] for item in records
            ),
            "all_records_avoid_full_session_replay": all(
                not item["paideia_memory_board"]["full_session_replay_used"] for item in records
            ),
            "privacy_ok": privacy_ok,
            "public_safe": privacy_ok and not missing_observability and bool(records),
        },
        "records": records,
        "missing_observability": missing_observability,
    }
    if output_path is not None:
        _write_json(output_path, comparison)
    return comparison
