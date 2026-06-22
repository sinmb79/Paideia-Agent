import json
from pathlib import Path

from ai22b.kibo_reuse.fingerprint import build_task_fingerprint
from ai22b.kibo_reuse.retriever import build_kibo_index, search_kibo


def _write_records(path: Path) -> None:
    promoted = {
        "schema": "paideia-kibo-record/v1",
        "kibo_id": "kibo_promoted",
        "source_run_id": "run-1",
        "owner": "Boss",
        "domain": "software_agent_engineering",
        "task_type": "implementation",
        "problem_signature": "Implement CLI command with tests.",
        "solution_steps": ["inspect CLI", "add parser", "add tests"],
        "reusable_logic": ["code_inspection", "test_execution"],
        "failure_modes": [],
        "required_inputs": ["code_inspection", "test_execution"],
        "output_template": "patch",
        "evidence_refs": ["reviewed-run"],
        "success_score": 92,
        "promotion_status": "promoted",
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-01T00:00:00Z",
    }
    quarantined = {**promoted, "kibo_id": "kibo_quarantine", "promotion_status": "quarantine"}
    path.write_text(
        "\n".join(json.dumps(row) for row in [promoted, quarantined]) + "\n",
        encoding="utf-8",
    )


def test_search_excludes_quarantined_records(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_records(kibo_path)
    task = build_task_fingerprint("Implement a CLI command and run pytest.", owner="Boss")

    matches = search_kibo(task, kibo_paths=[kibo_path])

    assert [match.record.kibo_id for match in matches] == ["kibo_promoted"]


def test_index_counts_eligible_records(tmp_path):
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    _write_records(kibo_path)

    index = build_kibo_index(tmp_path)

    assert index["record_count"] == 2
    assert index["eligible_record_count"] == 1
