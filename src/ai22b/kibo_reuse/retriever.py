from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import BLOCKED_PROMOTION_STATUSES, KiboRecord
from .scorer import KiboScore, score_kibo_record
from .models import TaskFingerprint


KIBO_INDEX_SCHEMA = "paideia-kibo-index/v1"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"JSONL row must be an object at {path}:{line_number}")
        rows.append(item)
    return rows


def _record_from_row(row: dict, *, source_path: Path | None = None) -> KiboRecord:
    enriched = dict(row)
    if source_path is not None:
        enriched.setdefault("evidence_refs", [str(source_path)])
    return KiboRecord.from_dict(enriched)


def load_kibo_records(path: Path) -> list[KiboRecord]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("records", []) if isinstance(payload, dict) else []
        return [_record_from_row(row, source_path=path) for row in rows if isinstance(row, dict)]
    return [_record_from_row(row, source_path=path) for row in _read_jsonl(path)]


def discover_kibo_sources(repo_root: Path) -> list[Path]:
    patterns = [
        "*reasoning_kibo*.jsonl",
        "*kibo*.jsonl",
        "*kibo_index*.json",
    ]
    sources: list[Path] = []
    for pattern in patterns:
        for path in repo_root.rglob(pattern):
            if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
                continue
            if path.is_file() and path not in sources:
                sources.append(path)
    return sorted(sources)


def eligible_records(records: Iterable[KiboRecord]) -> list[KiboRecord]:
    eligible: list[KiboRecord] = []
    for record in records:
        status = record.promotion_status.casefold()
        if status in BLOCKED_PROMOTION_STATUSES:
            continue
        if record.is_runtime_eligible:
            eligible.append(record)
    return eligible


def build_kibo_index(repo_root: Path, *, output_path: Path | None = None) -> dict:
    sources = discover_kibo_sources(repo_root)
    records: list[KiboRecord] = []
    for source in sources:
        records.extend(load_kibo_records(source))
    payload = {
        "schema": KIBO_INDEX_SCHEMA,
        "repo_root": str(repo_root),
        "source_count": len(sources),
        "record_count": len(records),
        "eligible_record_count": len(eligible_records(records)),
        "sources": [str(path) for path in sources],
        "records": [record.to_dict() for record in records],
        "policy": {
            "quarantined_records_excluded_at_search": True,
            "unreviewed_records_excluded_at_search": True,
            "hidden_chain_of_thought_reused": False,
        },
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def search_kibo(
    task: TaskFingerprint,
    *,
    repo_root: Path | None = None,
    kibo_paths: Iterable[Path] | None = None,
    limit: int = 5,
) -> list[KiboScore]:
    sources = list(kibo_paths or [])
    if repo_root is not None and not sources:
        sources = discover_kibo_sources(repo_root)
    records: list[KiboRecord] = []
    for source in sources:
        records.extend(load_kibo_records(source))
    scores = [score_kibo_record(task, record) for record in eligible_records(records)]
    scores.sort(key=lambda item: (item.reuse_score, item.record.success_score, item.record.updated_at), reverse=True)
    return scores[: max(0, limit)]
