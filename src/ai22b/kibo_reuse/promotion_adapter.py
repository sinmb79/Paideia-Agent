from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import KiboRecord


PROMOTION_ADAPTER_SCHEMA = "paideia-kibo-promotion-adapter-result/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply_kibo_outcome(
    record: KiboRecord | dict[str, Any],
    *,
    outcome: str,
    evidence_ref: str,
    reviewed_by: str = "Boss",
    caveat: str | None = None,
) -> dict[str, Any]:
    kibo = KiboRecord.from_dict(record) if isinstance(record, dict) else record
    timestamp = _now()
    failure_modes = list(kibo.failure_modes)
    caveats = list(kibo.caveats)
    status = kibo.promotion_status
    score = kibo.success_score

    if outcome == "success":
        score = min(100, score + 3)
        status = "promoted"
    elif outcome == "partial_success":
        score = max(0, min(100, score + 1))
        status = "promoted" if kibo.is_runtime_eligible else "reviewed"
        if caveat:
            caveats.append(caveat)
        failure_modes.append(caveat or "partial_reuse_required_llm_or_manual_completion")
    elif outcome == "failure":
        score = max(0, score - 20)
        status = "quarantine"
        failure_modes.append(caveat or "reuse_failed_validation")
    else:
        raise ValueError("outcome must be one of: success, partial_success, failure")

    updated = replace(
        kibo,
        success_score=score,
        promotion_status=status,
        updated_at=timestamp,
        last_used_at=timestamp,
        failure_modes=tuple(dict.fromkeys(failure_modes)),
        caveats=tuple(dict.fromkeys(caveats)),
        evidence_refs=tuple(dict.fromkeys([*kibo.evidence_refs, evidence_ref])),
    )
    return {
        "schema": PROMOTION_ADAPTER_SCHEMA,
        "outcome": outcome,
        "reviewed_by": reviewed_by,
        "evidence_ref": evidence_ref,
        "kibo_record": updated.to_dict(),
        "governance": {
            "quarantine_required": outcome == "failure",
            "promotion_requires_review": True,
            "private_reasoning_trace": "do_not_store",
        },
    }


def update_kibo_jsonl_record(
    path: Path,
    *,
    kibo_id: str,
    outcome: str,
    evidence_ref: str,
    reviewed_by: str = "Boss",
    caveat: str | None = None,
) -> dict[str, Any]:
    rows = []
    updated_result: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        record = KiboRecord.from_dict(row)
        if record.kibo_id == kibo_id:
            updated_result = apply_kibo_outcome(
                record,
                outcome=outcome,
                evidence_ref=evidence_ref,
                reviewed_by=reviewed_by,
                caveat=caveat,
            )
            rows.append(updated_result["kibo_record"])
        else:
            rows.append(row)
    if updated_result is None:
        raise KeyError(f"kibo_id not found: {kibo_id}")
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
    return updated_result
