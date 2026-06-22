from ai22b.kibo_reuse.models import KiboRecord
from ai22b.kibo_reuse.promotion_adapter import apply_kibo_outcome


def _record():
    return KiboRecord(
        kibo_id="kibo-1",
        source_run_id="run-1",
        owner="Boss",
        domain="software_agent_engineering",
        task_type="implementation",
        problem_signature="Implement command.",
        solution_steps=("inspect", "patch", "test"),
        reusable_logic=("code_inspection", "test_execution"),
        failure_modes=(),
        required_inputs=("code_inspection", "test_execution"),
        output_template="patch",
        evidence_refs=("reviewed-run",),
        success_score=88,
        promotion_status="promoted",
        created_at="2026-06-01T00:00:00Z",
        updated_at="2026-06-01T00:00:00Z",
    )


def test_success_outcome_increases_score_and_records_evidence():
    result = apply_kibo_outcome(_record(), outcome="success", evidence_ref="run-2")

    assert result["kibo_record"]["success_score"] == 91
    assert "run-2" in result["kibo_record"]["evidence_refs"]


def test_failure_outcome_moves_record_to_quarantine():
    result = apply_kibo_outcome(
        _record(),
        outcome="failure",
        evidence_ref="failed-run",
        caveat="validation failed",
    )

    assert result["kibo_record"]["promotion_status"] == "quarantine"
    assert "validation failed" in result["kibo_record"]["failure_modes"]
    assert result["governance"]["quarantine_required"] is True
