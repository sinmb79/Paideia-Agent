from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path


class TalentFoundryExecutionProofTests(unittest.TestCase):
    def test_hired_agent_job_execution_proof_passes_and_redacts_paths(self) -> None:
        from ai22b.talent_foundry.demo import run_demo
        from ai22b.talent_foundry.execution_proof import build_workspace_execution_proof
        from ai22b.talent_foundry.registry import run_hired_agent_job

        job_spec = {
            "schema": "ai-talent-workspace-agent-job/v1",
            "objective": "Verify that a hired research agent leaves reviewable workspace evidence.",
            "deliverables": [{"id": "evidence_note", "description": "Reviewable local evidence note"}],
            "acceptance_criteria": ["Workspace outputs, rollback, and checklist are present."],
            "input_files": [
                {
                    "path": "local_research_note.txt",
                    "description": "Declared local input note",
                    "purpose": "proof_context",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            outputs = run_demo(output_dir=tmp_path / "runs")
            run_path = tmp_path / "hired_agent_job_run.json"
            proof_path = tmp_path / "workspace_execution_proof.json"
            workspace = tmp_path / "workspace"
            workspace.mkdir(parents=True)
            (workspace / "local_research_note.txt").write_text(
                "Declared input evidence for the workspace proof.",
                encoding="utf-8",
            )
            run = run_hired_agent_job(
                outputs["local_employment_record"],
                job_spec=job_spec,
                workspace_dir=workspace,
                output_path=run_path,
            )
            proof = build_workspace_execution_proof(run, run_path=run_path, output_path=proof_path)
            saved = json.loads(proof_path.read_text(encoding="utf-8"))
            serialized = json.dumps(saved, ensure_ascii=False)

        self.assertTrue(proof["passed"])
        self.assertEqual(saved["schema"], "paideia-workspace-execution-proof/v1")
        self.assertEqual(saved["status"], "passed")
        self.assertIn("job_acceptance_checklist_passed", {item["id"] for item in saved["checks"]})
        self.assertIn("job_input_review_verified", {item["id"] for item in saved["checks"]})
        self.assertIn("workspace_tool_artifacts_materialized", {item["id"] for item in saved["checks"]})
        self.assertIn("llm_provider_preflight_present", {item["id"] for item in saved["checks"]})
        self.assertTrue(saved["artifact_summary"]["absolute_paths_redacted"])
        self.assertNotIn(str(tmp_path), serialized)

    def test_execution_proof_fails_when_workspace_rollback_manifest_is_missing(self) -> None:
        from ai22b.talent_foundry.demo import run_demo
        from ai22b.talent_foundry.execution_proof import build_workspace_execution_proof
        from ai22b.talent_foundry.registry import run_hired_agent_job

        job_spec = {
            "schema": "ai-talent-workspace-agent-job/v1",
            "objective": "Create a run that will be tampered for proof validation.",
            "deliverables": [{"id": "report", "description": "Report"}],
            "acceptance_criteria": ["Rollback manifest exists before proof validation."],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            outputs = run_demo(output_dir=tmp_path / "runs")
            run = run_hired_agent_job(
                outputs["local_employment_record"],
                job_spec=job_spec,
                workspace_dir=tmp_path / "workspace",
                output_path=tmp_path / "hired_agent_job_run.json",
            )
            tampered = copy.deepcopy(run)
            tampered["workspace_run"]["workspace_outputs"].pop("rollback_manifest", None)
            proof = build_workspace_execution_proof(tampered)

        self.assertFalse(proof["passed"])
        self.assertEqual(proof["status"], "failed")
        self.assertIn("workspace_required_outputs_present", proof["issues"])
        self.assertIn("workspace_rollback_manifest_schema", proof["issues"])

    def test_cli_verify_workspace_execution_for_dataflow_run(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.demo import run_demo
        from ai22b.talent_foundry.registry import run_hired_dataflow_job

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            outputs = run_demo(output_dir=tmp_path / "runs")
            run_path = tmp_path / "dataflow_run.json"
            proof_path = tmp_path / "dataflow_execution_proof.json"
            run_hired_dataflow_job(
                outputs["local_employment_record"],
                job_spec={"objective": "Verify dataflow execution proof for local research work."},
                workspace_dir=tmp_path / "dataflow_workspace",
                review_label={"score": 91, "status": "verified", "reviewed_by": "Boss"},
                output_path=run_path,
            )
            exit_code = cli_main(
                [
                    "verify-workspace-execution",
                    "--run",
                    str(run_path),
                    "--output",
                    str(proof_path),
                ]
            )
            proof = json.loads(proof_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(proof["passed"])
        self.assertIn("dataflow_transpose_verification_passed", {item["id"] for item in proof["checks"]})
        self.assertIn("dataflow_active_memory_cache_summary_only", {item["id"] for item in proof["checks"]})


if __name__ == "__main__":
    unittest.main()
