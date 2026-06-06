from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class CliSmokeTests(unittest.TestCase):
    def test_public_cli_smoke_commands_write_reviewable_outputs(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            role_models_path = tmp_path / "role_models.json"
            llm_onboarding_path = tmp_path / "llm_onboarding_checklist.json"
            doctor_path = tmp_path / "llm_provider_doctor.json"
            llm_smoke_path = tmp_path / "llm_application_smoke.json"
            agent_runtime_smoke_path = tmp_path / "agent_runtime_smoke.json"
            tool_audit_path = tmp_path / "tool_capability_audit.json"
            policy_eval_path = tmp_path / "policy_eval_report.json"
            public_release_path = tmp_path / "public_release_readiness.json"
            source_sbom_path = tmp_path / "source_sbom.json"

            role_models_code = cli_main(
                [
                    "list-role-models",
                    "--domain",
                    "securities_research",
                    "--output",
                    str(role_models_path),
                ]
            )
            llm_onboarding_code = cli_main(
                [
                    "build-llm-onboarding-checklist",
                    "--llm-engine",
                    "deterministic_local",
                    "--output",
                    str(llm_onboarding_path),
                ]
            )
            doctor_code = cli_main(
                [
                    "doctor-llm-provider",
                    "--llm-engine",
                    "deterministic_local",
                    "--strict",
                    "--output",
                    str(doctor_path),
                ]
            )
            llm_smoke_code = cli_main(
                [
                    "run-llm-application-smoke",
                    "--llm-engine",
                    "deterministic_local",
                    "--strict",
                    "--output",
                    str(llm_smoke_path),
                ]
            )
            agent_runtime_smoke_code = cli_main(
                [
                    "run-agent-runtime-smoke",
                    "--llm-engine",
                    "deterministic_local",
                    "--strict",
                    "--output",
                    str(agent_runtime_smoke_path),
                ]
            )
            tool_audit_code = cli_main(
                [
                    "audit-tool-capabilities",
                    "--strict",
                    "--output",
                    str(tool_audit_path),
                ]
            )
            policy_eval_code = cli_main(["run-action-policy-eval", "--output", str(policy_eval_path)])
            public_release_code = cli_main(
                [
                    "audit-public-release-readiness",
                    "--repo-root",
                    ".",
                    "--strict",
                    "--output",
                    str(public_release_path),
                ]
            )
            source_sbom_code = cli_main(
                [
                    "build-source-sbom",
                    "--repo-root",
                    ".",
                    "--output",
                    str(source_sbom_path),
                ]
            )

            role_models = json.loads(role_models_path.read_text(encoding="utf-8"))
            llm_onboarding = json.loads(llm_onboarding_path.read_text(encoding="utf-8"))
            doctor = json.loads(doctor_path.read_text(encoding="utf-8"))
            llm_smoke = json.loads(llm_smoke_path.read_text(encoding="utf-8"))
            agent_runtime_smoke = json.loads(agent_runtime_smoke_path.read_text(encoding="utf-8"))
            tool_audit = json.loads(tool_audit_path.read_text(encoding="utf-8"))
            policy_eval = json.loads(policy_eval_path.read_text(encoding="utf-8"))
            public_release = json.loads(public_release_path.read_text(encoding="utf-8"))
            source_sbom = json.loads(source_sbom_path.read_text(encoding="utf-8"))

        self.assertEqual(role_models_code, 0)
        self.assertEqual(llm_onboarding_code, 0)
        self.assertEqual(doctor_code, 0)
        self.assertEqual(llm_smoke_code, 0)
        self.assertEqual(agent_runtime_smoke_code, 0)
        self.assertEqual(tool_audit_code, 0)
        self.assertEqual(policy_eval_code, 0)
        self.assertEqual(public_release_code, 0)
        self.assertEqual(source_sbom_code, 0)

        self.assertEqual(role_models["schema"], "ai-talent-role-model-list/v1")
        self.assertEqual(role_models["domain"], "securities_research")
        self.assertIn("graham_value_investing", {item["role_model_id"] for item in role_models["role_models"]})

        self.assertEqual(llm_onboarding["schema"], "paideia-llm-onboarding-checklist/v1")
        self.assertEqual(llm_onboarding["status"], "offline_ready")
        self.assertEqual(llm_onboarding["selected_llm_service"]["engine"], "deterministic_local")
        self.assertEqual(llm_onboarding["selected_chat_surface"]["id"], "codex-bridge-chat")
        self.assertFalse(llm_onboarding["public_safe"]["network_call_performed"])
        self.assertFalse(llm_onboarding["public_safe"]["secret_values_exported"])
        command_ids = {item["id"] for item in llm_onboarding["command_plan"]}
        self.assertLessEqual(
            {
                "provider_doctor_no_network",
                "application_engine_no_network_smoke",
                "agent_runtime_no_network_smoke",
                "chat_surface_first_turn",
            },
            command_ids,
        )
        live_command = next(item for item in llm_onboarding["command_plan"] if item["id"] == "provider_doctor_live_check")
        self.assertIn("--live-check", live_command["command"])
        self.assertIn("--strict", live_command["command"])

        self.assertEqual(doctor["schema"], "paideia-llm-provider-doctor/v1")
        self.assertEqual(doctor["engine"], "deterministic_local")
        self.assertTrue(doctor["passed"])
        self.assertEqual(doctor["network_access"], "blocked")
        self.assertFalse(doctor["secret_values_exported"])
        self.assertEqual(doctor["smoke_contract"]["schema"], "paideia-llm-provider-smoke-contract/v1")
        self.assertEqual(doctor["smoke_contract"]["status"], "skipped")
        self.assertFalse(doctor["smoke_contract"]["provider_call_attempted"])

        self.assertEqual(llm_smoke["schema"], "paideia-llm-application-smoke/v1")
        self.assertEqual(llm_smoke["engine"], "deterministic_local")
        self.assertEqual(llm_smoke["llm_mode"], "offline")
        self.assertTrue(llm_smoke["passed"])
        self.assertEqual(llm_smoke["runtime_result"]["status"], "completed")
        self.assertEqual(llm_smoke["runtime_result"]["network_access"], "blocked")
        self.assertEqual(llm_smoke["runtime_result"]["identity_policy"], "application_engine_not_identity")
        self.assertFalse(llm_smoke["preflight"]["network_call_made_by_preflight"])
        self.assertFalse(llm_smoke["data_policy"]["secret_values_exported"])
        self.assertEqual(llm_smoke["data_policy"]["private_reasoning_trace"], "do_not_store")

        self.assertEqual(agent_runtime_smoke["schema"], "paideia-agent-runtime-smoke/v1")
        self.assertTrue(agent_runtime_smoke["passed"])
        self.assertEqual(agent_runtime_smoke["status"], "passed")
        self.assertEqual(agent_runtime_smoke["details"]["engine"], "deterministic_local")
        self.assertEqual(agent_runtime_smoke["details"]["llm_mode"], "offline")
        self.assertEqual(agent_runtime_smoke["details"]["run_status"], "completed")
        self.assertEqual(agent_runtime_smoke["details"]["llm_status"], "completed")
        self.assertEqual(agent_runtime_smoke["details"]["verification_status"], "passed")
        self.assertEqual(agent_runtime_smoke["details"]["execution_contract_status"], "passed")
        self.assertIn("evidence_packet", agent_runtime_smoke["details"]["completed_tools"])
        self.assertEqual(agent_runtime_smoke["details"]["missing_required_tools"], [])
        self.assertEqual(agent_runtime_smoke["details"]["memory_decision"], "candidate_pending_boss_review")
        self.assertFalse(agent_runtime_smoke["details"]["memory_auto_promotion_performed"])
        self.assertFalse(agent_runtime_smoke["details"]["preflight_network_call_made"])
        self.assertEqual(agent_runtime_smoke["details"]["network_default"], "blocked")
        self.assertEqual(agent_runtime_smoke["details"]["subprocess_default"], "blocked")
        self.assertTrue(agent_runtime_smoke["details"]["public_safe"])

        self.assertEqual(tool_audit["schema"], "paideia-tool-capability-audit/v1")
        self.assertTrue(tool_audit["passed"])
        self.assertEqual(tool_audit["status"], "passed")
        self.assertGreaterEqual(tool_audit["details"]["tool_count"], 7)
        self.assertEqual(tool_audit["details"]["missing_required_tools"], [])
        self.assertEqual(tool_audit["details"]["scope_failure_count"], 0)
        self.assertTrue(tool_audit["details"]["denied_all_blocked"])
        self.assertTrue(tool_audit["details"]["granted_all_completed"])
        self.assertEqual(tool_audit["details"]["unknown_tool_status"], "skipped")
        self.assertEqual(tool_audit["details"]["network_default"], "blocked")
        self.assertEqual(tool_audit["details"]["subprocess_default"], "blocked")
        self.assertFalse(tool_audit["public_safe"]["network_call_performed"])
        self.assertFalse(tool_audit["public_safe"]["subprocess_executed"])

        self.assertEqual(policy_eval["schema"], "paideia-action-policy-eval-report/v1")
        self.assertEqual(policy_eval["status"], "passed")
        self.assertEqual(policy_eval["summary"]["failed_count"], 0)
        self.assertFalse(policy_eval["runtime_policy"]["network_call_performed"])
        self.assertFalse(policy_eval["runtime_policy"]["llm_called"])

        self.assertEqual(public_release["schema"], "paideia-public-release-readiness/v1")
        self.assertTrue(public_release["passed"])
        self.assertEqual(public_release["status"], "passed")
        self.assertEqual(public_release["summary"]["failed_count"], 0)
        self.assertGreater(public_release["summary"]["public_candidate_file_count"], 20)
        self.assertEqual(public_release["summary"]["public_candidate_issue_count"], 0)
        self.assertFalse(public_release["summary"]["network_call_performed"])
        self.assertFalse(public_release["summary"]["subprocess_executed"])
        self.assertFalse(public_release["policy"]["secret_values_exported"])
        check_by_id = {item["id"]: item for item in public_release["checks"]}
        self.assertTrue(check_by_id["public_candidate_content_scan"]["passed"])
        self.assertEqual(check_by_id["public_candidate_content_scan"]["details"]["issue_count"], 0)

        self.assertEqual(source_sbom["schema"], "paideia-source-sbom/v1")
        self.assertEqual(source_sbom["package"]["name"], "paideia-agent")
        self.assertEqual(source_sbom["package"]["license_detected"], "MIT")
        self.assertEqual(source_sbom["dependencies"]["direct_count"], 0)
        self.assertIn("dev", source_sbom["dependencies"]["optional_groups"])
        self.assertIn("ai22b-talent-foundry", source_sbom["package"]["console_scripts"])
        self.assertGreater(source_sbom["inventory"]["component_count"], 20)
        self.assertEqual(source_sbom["release_readiness"]["public_candidate_issue_count"], 0)
        self.assertFalse(source_sbom["policy"]["network_call_performed"])
        self.assertFalse(source_sbom["policy"]["subprocess_executed"])


if __name__ == "__main__":
    unittest.main()
