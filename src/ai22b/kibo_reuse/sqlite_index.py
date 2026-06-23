from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import KiboRecord


def build_sqlite_kibo_index(records: Iterable[KiboRecord], db_path: Path) -> dict:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS kibo_records (kibo_id TEXT PRIMARY KEY, payload TEXT NOT NULL, content TEXT NOT NULL)"
        )
        try:
            connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS kibo_fts USING fts5(kibo_id, content)")
            fts_enabled = True
        except sqlite3.OperationalError:
            fts_enabled = False
        connection.execute("DELETE FROM kibo_records")
        if fts_enabled:
            connection.execute("DELETE FROM kibo_fts")
        count = 0
        for record in records:
            payload = record.to_dict()
            content = _content(record)
            connection.execute(
                "INSERT OR REPLACE INTO kibo_records (kibo_id, payload, content) VALUES (?, ?, ?)",
                (record.kibo_id, json.dumps(payload, ensure_ascii=False, sort_keys=True), content),
            )
            if fts_enabled:
                connection.execute(
                    "INSERT INTO kibo_fts (kibo_id, content) VALUES (?, ?)",
                    (record.kibo_id, content),
                )
            count += 1
    return {"schema": "paideia-kibo-sqlite-index/v1", "db_path": str(db_path), "record_count": count, "fts5_enabled": fts_enabled}


def search_sqlite_kibo_index(db_path: Path, query: str, *, limit: int = 5) -> list[dict]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        if _fts_exists(connection):
            rows = connection.execute(
                """
                SELECT r.payload
                FROM kibo_fts f
                JOIN kibo_records r ON r.kibo_id = f.kibo_id
                WHERE kibo_fts MATCH ?
                ORDER BY bm25(kibo_fts)
                LIMIT ?
                """,
                (_fts_query(query), max(0, int(limit))),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT payload FROM kibo_records WHERE content LIKE ? LIMIT ?",
                (f"%{query}%", max(0, int(limit))),
            ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def _fts_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'kibo_fts'").fetchone()
    return row is not None


def _fts_query(query: str) -> str:
    terms = [term.replace('"', "") for term in query.split() if term.strip()]
    return " OR ".join(f'"{term}"' for term in terms) or '""'


def _content(record: KiboRecord) -> str:
    return " ".join(
        [
            record.domain,
            record.task_type,
            record.problem_signature,
            " ".join(record.solution_steps),
            " ".join(record.reusable_logic),
            " ".join(record.required_inputs),
            record.output_template,
        ]
    )
