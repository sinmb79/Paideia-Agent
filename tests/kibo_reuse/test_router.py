import json
from pathlib import Path

from jsonschema import Draft202012Validator

from ai22b.kibo_reuse.router import build_kibo_reuse_plan_from_file


ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _write_kibo(path: Path) -> None:
    row = {
        "schema": "paideia-kibo-record/v1",
        "kibo_id": "kibo_xxx",
        "source_run_id": "run-1",
        "owner": "Boss",
        "domain": "investment_research",
        "task_type": "comparative_analysis",
        "problem_signature": "Assess buy opportunity with valuation, risk, technical chart, and theme analysis.",
        "solution_steps": ["market structure analysis", "profitability comparison", "risk matrix"],
        "reusable_logic": ["valuation", "risk_analysis", "chart_analysis", "theme_analysis", "risk_vs_return"],
        "failure_modes": ["stale current data"],
        "required_inputs": ["web_research", "valuation", "risk_analysis", "chart_analysis", "theme_analysis"],
        "output_template": "conclusion_first risk_vs_return report",
        "evidence_refs": ["reviewed-run"],
        "success_score": 94,
        "promotion_status": "promoted",
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-10T00:00:00Z",
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_kibo_plan_splits_reused_steps_from_llm_required_parts_and_validates_schema(tmp_path):
    task_path = tmp_path / "task.json"
    kibo_path = tmp_path / "reasoning_kibo.jsonl"
    output_path = tmp_path / "kibo_plan.json"
    task_path.write_text(
        json.dumps(
            {
                "task_id": "task-invest",
                "owner": "Boss",
                "request": "Assess buy opportunity using current market price, technical chart analysis, theme analysis, conclusion first, and risk return framing.",
            }
        ),
        encoding="utf-8",
    )
    _write_kibo(kibo_path)

    plan = build_kibo_reuse_plan_from_file(
        task_path,
        kibo_paths=[kibo_path],
        output_path=output_path,
    )

    assert plan["reuse_mode"] == "partial_reuse"
    assert plan["selected_kibo_ids"] == ["kibo_xxx"]
    assert plan["reused_steps"]
    assert "fresh_external_data" in plan["llm_required_parts"]
    assert "high_risk_task_direct_reuse_forbidden" in plan["risk_warnings"]
    assert output_path.exists()
    Draft202012Validator.check_schema(_schema("task_fingerprint.v1.schema.json"))
    Draft202012Validator(_schema("task_fingerprint.v1.schema.json")).validate(plan["task_fingerprint"])
    Draft202012Validator(_schema("reuse_decision.v1.schema.json")).validate(plan["reuse_decision"])
    Draft202012Validator(_schema("kibo_reuse_plan.v1.schema.json")).validate(plan)
