from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


def _manifest(*, approvals: list[dict] | None = None) -> dict:
    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "approval-test-agent",
            "role": "local research agent",
            "major_goal": "Verify sensitive action approval gates.",
        },
        "memory_profile": {
            "procedural_principles": ["Require explicit approval artifacts for sensitive actions."],
            "semantic_themes": ["policy gate", "local-first execution"],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
        "llm_policy": {
            "role": "application_engine_not_identity",
            "private_reasoning_trace": "do_not_store",
        },
        "tool_policy": {
            "allowed_tools": ["work_session", "evidence_packet", "assessment"],
            "blocked_tools": [],
            "boss_approvals": approvals or [],
        },
    }


class ActionApprovalTests(unittest.TestCase):
    def test_sensitive_action_requires_explicit_boss_approval_artifact(self) -> None:
        from ai22b.talent_foundry.action_policy import evaluate_action_policy, infer_action_intents

        intents = infer_action_intents("내 에이전트 기록을 외부 업로드해줘.", _manifest())
        decision = evaluate_action_policy(_manifest(), intents)

        self.assertEqual(decision["status"], "needs_approval")
        self.assertEqual(decision["boss_approval_gate"]["schema"], "paideia-boss-approval-gate/v1")
        self.assertEqual(decision["boss_approval_gate"]["provided_count"], 0)
        self.assertEqual(decision["boss_approval_gate"]["accepted_count"], 0)
        self.assertEqual(decision["approval_required"][0]["capability"], "network.external_upload")
        self.assertEqual(
            decision["approval_required"][0]["reason"],
            "sensitive_capability_requires_explicit_boss_approval",
        )

    def test_accepted_boss_approval_allows_planning_but_keeps_runtime_side_effects_blocked(self) -> None:
        from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
        from ai22b.talent_foundry.action_policy import evaluate_action_policy, infer_action_intents

        approval = {
            "schema": "paideia-boss-approval/v1",
            "approval_id": "boss-approval-upload-001",
            "status": "approved",
            "approved_by": "Boss",
            "capability": "network.external_upload",
            "action_type": "external_upload",
            "data_class": "agent_or_owner_data",
            "scope": "single_local_review_run",
        }
        manifest = _manifest(approvals=[approval])
        task = "내 에이전트 기록을 외부 업로드해줘."
        intents = infer_action_intents(task, manifest)
        decision = evaluate_action_policy(manifest, intents)

        self.assertEqual(decision["status"], "approved")
        self.assertEqual(decision["boss_approval_gate"]["accepted_count"], 1)
        self.assertEqual(
            decision["boss_approval_gate"]["accepted_approvals"][0]["approval_id"],
            "boss-approval-upload-001",
        )
        external = next(item for item in decision["approved_intents"] if item["action_type"] == "external_upload")
        self.assertEqual(external["approval_id"], "boss-approval-upload-001")

        result = run_agent_from_manifest(manifest, task=task)

        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["policy_decision"]["status"], "approved")
        self.assertEqual(result["execution_contract"]["status"], "passed")
        self.assertEqual(result["execution_contract"]["policy_gate"]["boss_approval_accepted_count"], 1)
        self.assertTrue(result["execution_contract"]["llm_runtime"]["attempted"])
        self.assertTrue(result["execution_contract"]["tool_execution"]["attempted"])
        self.assertEqual(result["tool_execution"]["capability_scope"]["network_default"], "blocked")
        self.assertEqual(result["tool_execution"]["capability_scope"]["subprocess_default"], "blocked")
        self.assertNotIn("network.external_upload", result["tool_execution"]["capability_scope"]["granted_capabilities"])
        self.assertEqual(result["memory_write"]["decision"], "candidate_pending_boss_review")

    def test_cli_create_boss_approval_writes_artifact_usable_by_policy(self) -> None:
        from ai22b.talent_foundry.action_policy import evaluate_action_policy, infer_action_intents
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            approval_path = Path(tmp) / "boss_approval_upload.json"
            exit_code = cli_main(
                [
                    "create-boss-approval",
                    "--capability",
                    "network.external_upload",
                    "--action-type",
                    "external_upload",
                    "--data-class",
                    "agent_or_owner_data",
                    "--approved-by",
                    "Boss",
                    "--approval-id",
                    "boss-approval-cli-001",
                    "--output",
                    str(approval_path),
                ]
            )
            approval = json.loads(approval_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(approval["schema"], "paideia-boss-approval/v1")
        self.assertEqual(approval["approval_id"], "boss-approval-cli-001")
        self.assertEqual(approval["status"], "approved")
        self.assertEqual(approval["capabilities"], ["network.external_upload"])
        self.assertTrue(approval["runtime_safety_contract"]["approval_is_not_tool_execution"])
        self.assertEqual(approval["runtime_safety_contract"]["network_default_after_approval"], "blocked")

        manifest = _manifest(approvals=[approval])
        intents = infer_action_intents("내 에이전트 기록을 외부 업로드해줘.", manifest)
        decision = evaluate_action_policy(manifest, intents)

        self.assertEqual(decision["status"], "approved")
        self.assertEqual(decision["boss_approval_gate"]["accepted_count"], 1)

    def test_cli_run_agent_accepts_one_run_boss_approval_artifact(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifest.json"
            approval_path = root / "boss_approval_upload.json"
            output_path = root / "agent_run.json"
            log_path = root / "agent_run.jsonl"
            manifest_path.write_text(json.dumps(_manifest(), ensure_ascii=False), encoding="utf-8")
            create_exit = cli_main(
                [
                    "create-boss-approval",
                    "--capability",
                    "network.external_upload",
                    "--action-type",
                    "external_upload",
                    "--data-class",
                    "agent_or_owner_data",
                    "--approved-by",
                    "Boss",
                    "--approval-id",
                    "boss-approval-cli-run-001",
                    "--output",
                    str(approval_path),
                ]
            )
            run_exit = cli_main(
                [
                    "run-agent",
                    "--manifest",
                    str(manifest_path),
                    "--task",
                    "내 에이전트 기록을 외부 업로드해줘.",
                    "--boss-approval",
                    str(approval_path),
                    "--output",
                    str(output_path),
                    "--log",
                    str(log_path),
                ]
            )
            result = json.loads(output_path.read_text(encoding="utf-8"))
            original_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(create_exit, 0)
        self.assertEqual(run_exit, 0)
        self.assertEqual(original_manifest["tool_policy"]["boss_approvals"], [])
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["policy_decision"]["status"], "approved")
        self.assertEqual(result["policy_decision"]["boss_approval_gate"]["accepted_count"], 1)
        self.assertEqual(
            result["policy_decision"]["boss_approval_gate"]["accepted_approvals"][0]["approval_id"],
            "boss-approval-cli-run-001",
        )
        self.assertEqual(result["execution_contract"]["policy_gate"]["boss_approval_accepted_count"], 1)
        self.assertEqual(result["tool_execution"]["capability_scope"]["network_default"], "blocked")
        self.assertEqual(result["tool_execution"]["capability_scope"]["subprocess_default"], "blocked")
        self.assertNotIn("network.external_upload", result["tool_execution"]["capability_scope"]["granted_capabilities"])

    def test_cli_run_workspace_agent_accepts_one_run_boss_approval_artifact(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "manifest.json"
            approval_path = root / "boss_approval_upload.json"
            output_path = root / "workspace_run.json"
            workspace = root / "workspace"
            manifest_path.write_text(json.dumps(_manifest(), ensure_ascii=False), encoding="utf-8")
            create_exit = cli_main(
                [
                    "create-boss-approval",
                    "--capability",
                    "network.external_upload",
                    "--action-type",
                    "external_upload",
                    "--data-class",
                    "agent_or_owner_data",
                    "--approved-by",
                    "Boss",
                    "--approval-id",
                    "boss-approval-workspace-001",
                    "--output",
                    str(approval_path),
                ]
            )
            run_exit = cli_main(
                [
                    "run-workspace-agent",
                    "--manifest",
                    str(manifest_path),
                    "--task",
                    "내 에이전트 기록을 외부 업로드해줘.",
                    "--workspace",
                    str(workspace),
                    "--boss-approval",
                    str(approval_path),
                    "--output",
                    str(output_path),
                ]
            )
            result = json.loads(output_path.read_text(encoding="utf-8"))
            task_plan_exists = Path(result["workspace_outputs"]["task_plan"]).exists()
            original_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(create_exit, 0)
        self.assertEqual(run_exit, 0)
        self.assertEqual(original_manifest["tool_policy"]["boss_approvals"], [])
        self.assertEqual(result["schema"], "ai-talent-workspace-agent-run/v1")
        self.assertEqual(result["run_status"], "completed")
        self.assertEqual(result["base_agent_run"]["policy_decision"]["boss_approval_gate"]["accepted_count"], 1)
        self.assertEqual(
            result["base_agent_run"]["execution_contract"]["policy_gate"]["boss_approval_accepted_count"],
            1,
        )
        self.assertEqual(result["tool_authorization"]["network_access"], "blocked")
        self.assertEqual(result["tool_authorization"]["capability_scope"]["network_default"], "blocked")
        self.assertTrue(task_plan_exists)

    def test_public_program_manifest_lists_boss_approval_command(self) -> None:
        from ai22b.talent_foundry.program_manifest import build_public_program_manifest

        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_public_program_manifest(Path(tmp))

        commands = {item["id"]: item for item in manifest["commands"]}
        self.assertIn("create-boss-approval", commands)
        self.assertIn("approval artifact", commands["create-boss-approval"]["purpose"])


if __name__ == "__main__":
    unittest.main()
