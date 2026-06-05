from __future__ import annotations

import unittest


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


if __name__ == "__main__":
    unittest.main()
