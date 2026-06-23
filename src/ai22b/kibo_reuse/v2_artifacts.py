from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .schema_compat import validate_compatibility_manifest


def schema_id_for(contract_name: str) -> str:
    return f"paideia-kibo-v2-{contract_name.replace('_', '-')}/v2"


def v2_header(contract_name: str, manifest: dict[str, Any]) -> dict[str, str]:
    validate_compatibility_manifest(manifest)
    hashes = manifest["contract_hashes"]
    contract_hash = hashes.get(contract_name)
    if not isinstance(contract_hash, str) or len(contract_hash) != 64:
        raise ValueError(f"Compatibility manifest has no valid hash for {contract_name}")
    return {
        "schema": schema_id_for(contract_name),
        "schema_version": manifest["contracts_release"],
        "contract_hash": contract_hash,
    }


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def evidence_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row must be an object at {path}:{line_number}")
        rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
