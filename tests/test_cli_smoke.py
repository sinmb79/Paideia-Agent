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
            llm_services_path = tmp_path / "llm_services.json"
            llm_onboarding_path = tmp_path / "llm_onboarding_checklist.json"
            llm_connection_profile_path = tmp_path / "llm_connection_profile.json"
            doctor_path = tmp_path / "llm_provider_doctor.json"
            adapter_contracts_path = tmp_path / "llm_adapter_contracts.json"
            llm_smoke_path = tmp_path / "llm_application_smoke.json"
            agent_runtime_smoke_path = tmp_path / "agent_runtime_smoke.json"
            chat_runtime_smoke_path = tmp_path / "chat_runtime_smoke.json"
            llm_live_readiness_dir = tmp_path / "llm_live_readiness"
            tool_audit_path = tmp_path / "tool_capability_audit.json"
            policy_eval_path = tmp_path / "policy_eval_report.json"
            public_release_path = tmp_path / "public_release_readiness.json"
            source_sbom_path = tmp_path / "source_sbom.json"
            first_run_doctor_path = tmp_path / "first_run_doctor.json"
            package_install_doctor_path = tmp_path / "package_install_doctor.json"
            runtime_contract_doctor_path = tmp_path / "runtime_contract_doctor.json"

            role_models_code = cli_main(
                [
                    "list-role-models",
                    "--domain",
                    "securities_research",
                    "--output",
                    str(role_models_path),
                ]
            )
            llm_services_code = cli_main(
                [
                    "list-llm-services",
                    "--output",
                    str(llm_services_path),
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
            llm_connection_profile_code = cli_main(
                [
                    "build-llm-connection-profile",
                    "--llm-engine",
                    "deterministic_local",
                    "--output",
                    str(llm_connection_profile_path),
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
            adapter_contracts_code = cli_main(
                [
                    "doctor-llm-adapters",
                    "--strict",
                    "--output",
                    str(adapter_contracts_path),
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
            chat_runtime_smoke_code = cli_main(
                [
                    "run-chat-runtime-smoke",
                    "--llm-engine",
                    "deterministic_local",
                    "--strict",
                    "--output",
                    str(chat_runtime_smoke_path),
                ]
            )
            llm_live_readiness_code = cli_main(
                [
                    "doctor-llm-live-readiness",
                    "--llm-engine",
                    "deterministic_local",
                    "--strict",
                    "--output-dir",
                    str(llm_live_readiness_dir),
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
            first_run_doctor_code = cli_main(
                [
                    "doctor-first-run",
                    "--repo-root",
                    ".",
                    "--strict",
                    "--output",
                    str(first_run_doctor_path),
                ]
            )
            package_install_doctor_code = cli_main(
                [
                    "doctor-package-install",
                    "--repo-root",
                    ".",
                    "--strict",
                    "--output",
                    str(package_install_doctor_path),
                ]
            )
            runtime_contract_doctor_code = cli_main(
                [
                    "doctor-runtime-contract",
                    "--repo-root",
                    ".",
                    "--strict",
                    "--output",
                    str(runtime_contract_doctor_path),
                ]
            )

            role_models = json.loads(role_models_path.read_text(encoding="utf-8"))
            llm_services = json.loads(llm_services_path.read_text(encoding="utf-8"))
            llm_onboarding = json.loads(llm_onboarding_path.read_text(encoding="utf-8"))
            llm_connection_profile = json.loads(llm_connection_profile_path.read_text(encoding="utf-8"))
            doctor = json.loads(doctor_path.read_text(encoding="utf-8"))
            adapter_contracts = json.loads(adapter_contracts_path.read_text(encoding="utf-8"))
            llm_smoke = json.loads(llm_smoke_path.read_text(encoding="utf-8"))
            agent_runtime_smoke = json.loads(agent_runtime_smoke_path.read_text(encoding="utf-8"))
            chat_runtime_smoke = json.loads(chat_runtime_smoke_path.read_text(encoding="utf-8"))
            chat_runtime_smoke_artifact_exists = {
                name: Path(artifact_path).exists()
                for name, artifact_path in chat_runtime_smoke["artifacts"].items()
            }
            llm_live_readiness = json.loads(
                (llm_live_readiness_dir / "llm_live_readiness_suite.json").read_text(encoding="utf-8")
            )
            llm_live_readiness_artifact_exists = {
                name: Path(artifact_path).exists()
                for name, artifact_path in llm_live_readiness["artifacts"].items()
            }
            tool_audit = json.loads(tool_audit_path.read_text(encoding="utf-8"))
            policy_eval = json.loads(policy_eval_path.read_text(encoding="utf-8"))
            public_release = json.loads(public_release_path.read_text(encoding="utf-8"))
            source_sbom = json.loads(source_sbom_path.read_text(encoding="utf-8"))
            first_run_doctor = json.loads(first_run_doctor_path.read_text(encoding="utf-8"))
            package_install_doctor = json.loads(package_install_doctor_path.read_text(encoding="utf-8"))
            runtime_contract_doctor = json.loads(runtime_contract_doctor_path.read_text(encoding="utf-8"))

        self.assertEqual(role_models_code, 0)
        self.assertEqual(llm_services_code, 0)
        self.assertEqual(llm_onboarding_code, 0)
        self.assertEqual(llm_connection_profile_code, 0)
        self.assertEqual(doctor_code, 0)
        self.assertEqual(adapter_contracts_code, 0)
        self.assertEqual(llm_smoke_code, 0)
        self.assertEqual(agent_runtime_smoke_code, 0)
        self.assertEqual(chat_runtime_smoke_code, 0)
        self.assertEqual(llm_live_readiness_code, 0)
        self.assertEqual(tool_audit_code, 0)
        self.assertEqual(policy_eval_code, 0)
        self.assertEqual(public_release_code, 0)
        self.assertEqual(source_sbom_code, 0)
        self.assertEqual(first_run_doctor_code, 0)
        self.assertEqual(package_install_doctor_code, 0)
        self.assertEqual(runtime_contract_doctor_code, 0)

        self.assertEqual(role_models["schema"], "ai-talent-role-model-list/v1")
        self.assertEqual(role_models["domain"], "securities_research")
        self.assertIn("graham_value_investing", {item["role_model_id"] for item in role_models["role_models"]})

        self.assertEqual(llm_services["schema"], "paideia-llm-provider-matrix/v1")
        self.assertEqual(llm_services["selected_chat_surface"]["id"], "codex-bridge-chat")
        self.assertGreaterEqual(llm_services["summary"]["service_count"], 10)
        self.assertIn("openrouter_api", llm_services["summary"]["external_api_service_ids"])
        self.assertIn("ollama_local", llm_services["summary"]["localhost_service_ids"])
        self.assertIn("deterministic_local", llm_services["summary"]["no_network_service_ids"])
        self.assertFalse(llm_services["public_safe"]["network_call_performed"])
        self.assertFalse(llm_services["selection_policy"]["llm_is_identity"])
        self.assertTrue(llm_services["selection_policy"]["live_checks_require_explicit_command"])
        service_by_id = {item["service_id"]: item for item in llm_services["services"]}
        self.assertIn("--live-check", service_by_id["openrouter_api"]["agent_runtime_live_smoke_command"])
        self.assertTrue(service_by_id["openrouter_api"]["live_required_before_agent_work"])
        self.assertIn("chat-hired-agent", service_by_id["deterministic_local"]["chat_command"])

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
                "llm_live_readiness_suite",
                "chat_runtime_smoke",
                "chat_surface_first_turn",
            },
            command_ids,
        )
        live_command = next(item for item in llm_onboarding["command_plan"] if item["id"] == "provider_doctor_live_check")
        self.assertIn("--live-check", live_command["command"])
        self.assertIn("--strict", live_command["command"])
        readiness_command = next(
            item for item in llm_onboarding["command_plan"] if item["id"] == "llm_live_readiness_suite"
        )
        self.assertIn("doctor-llm-live-readiness", readiness_command["command"])
        self.assertIn("--output-dir", readiness_command["command"])
        chat_smoke_command = next(item for item in llm_onboarding["command_plan"] if item["id"] == "chat_runtime_smoke")
        self.assertIn("run-chat-runtime-smoke", chat_smoke_command["command"])
        self.assertIn("--chat-surface codex-bridge-chat", chat_smoke_command["command"])

        self.assertEqual(llm_connection_profile["schema"], "paideia-llm-connection-profile/v1")
        self.assertEqual(llm_connection_profile["status"], "offline_ready_no_setup")
        self.assertEqual(llm_connection_profile["selected_llm_service"]["engine"], "deterministic_local")
        self.assertFalse(llm_connection_profile["setup_requirements"]["requires_live_check_before_agent_work"])
        self.assertFalse(llm_connection_profile["setup_requirements"]["requires_model_argument"])
        self.assertFalse(llm_connection_profile["public_safe"]["network_call_performed"])
        self.assertFalse(llm_connection_profile["public_safe"]["secret_values_exported"])
        profile_sequence_ids = {item["id"] for item in llm_connection_profile["verification_sequence"]}
        self.assertLessEqual(
            {
                "no_network_doctor",
                "explicit_live_provider_check",
                "live_application_engine_smoke",
                "live_agent_runtime_smoke",
                "chat_runtime_smoke",
            },
            profile_sequence_ids,
        )
        self.assertIn("run-chat-runtime-smoke", llm_connection_profile["daily_use_commands"]["chat_runtime_smoke"])

        self.assertEqual(doctor["schema"], "paideia-llm-provider-doctor/v1")
        self.assertEqual(doctor["engine"], "deterministic_local")
        self.assertTrue(doctor["passed"])
        self.assertEqual(doctor["network_access"], "blocked")
        self.assertFalse(doctor["secret_values_exported"])
        self.assertEqual(doctor["smoke_contract"]["schema"], "paideia-llm-provider-smoke-contract/v1")
        self.assertEqual(doctor["smoke_contract"]["status"], "skipped")
        self.assertFalse(doctor["smoke_contract"]["provider_call_attempted"])

        self.assertEqual(adapter_contracts["schema"], "paideia-llm-adapter-contracts/v1")
        self.assertTrue(adapter_contracts["passed"])
        self.assertEqual(adapter_contracts["status"], "passed")
        self.assertGreaterEqual(adapter_contracts["summary"]["direct_adapter_count"], 9)
        self.assertEqual(adapter_contracts["summary"]["failed_count"], 0)
        self.assertFalse(adapter_contracts["public_safe"]["network_call_performed"])
        self.assertFalse(adapter_contracts["public_safe"]["localhost_call_performed"])
        self.assertFalse(adapter_contracts["public_safe"]["external_provider_called"])
        self.assertFalse(adapter_contracts["public_safe"]["secret_values_exported"])
        self.assertFalse(adapter_contracts["public_safe"]["raw_provider_payload_saved"])

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

        self.assertEqual(chat_runtime_smoke["schema"], "paideia-chat-runtime-smoke/v1")
        self.assertTrue(chat_runtime_smoke["passed"])
        self.assertEqual(chat_runtime_smoke["status"], "passed")
        self.assertEqual(chat_runtime_smoke["engine"], "deterministic_local")
        self.assertEqual(chat_runtime_smoke["llm_mode"], "offline")
        self.assertEqual(chat_runtime_smoke["chat_surface"]["id"], "codex-bridge-chat")
        self.assertEqual(chat_runtime_smoke["details"]["chat_status"], "completed")
        self.assertEqual(chat_runtime_smoke["details"]["llm_status"], "completed")
        self.assertFalse(chat_runtime_smoke["details"]["preflight_network_call_made"])
        self.assertFalse(chat_runtime_smoke["details"]["stored_private_reasoning_trace"])
        self.assertFalse(chat_runtime_smoke["details"]["learning_update_performed"])
        self.assertFalse(chat_runtime_smoke["details"]["provider_not_ready"])
        self.assertFalse(chat_runtime_smoke["data_policy"]["secret_values_exported"])
        self.assertFalse(chat_runtime_smoke["data_policy"]["raw_provider_payload_saved"])
        self.assertEqual(chat_runtime_smoke["data_policy"]["private_reasoning_trace"], "do_not_store")
        self.assertFalse(chat_runtime_smoke["data_policy"]["learning_auto_promotion_performed"])
        self.assertTrue(all(chat_runtime_smoke_artifact_exists.values()), chat_runtime_smoke_artifact_exists)

        self.assertEqual(llm_live_readiness["schema"], "paideia-llm-live-readiness-suite/v1")
        self.assertTrue(llm_live_readiness["passed"])
        self.assertFalse(llm_live_readiness["live_ready"])
        self.assertEqual(llm_live_readiness["engine"], "deterministic_local")
        self.assertEqual(llm_live_readiness["llm_mode"], "offline")
        self.assertFalse(llm_live_readiness["live_check_requested"])
        self.assertEqual(
            llm_live_readiness["summary_path"],
            str(llm_live_readiness_dir / "llm_live_readiness_suite.json"),
        )
        self.assertTrue(llm_live_readiness["checks"]["provider_doctor"]["passed"])
        self.assertTrue(llm_live_readiness["checks"]["application_smoke"]["passed"])
        self.assertTrue(llm_live_readiness["checks"]["agent_runtime_smoke"]["passed"])
        self.assertTrue(llm_live_readiness["checks"]["chat_runtime_smoke"]["passed"])
        self.assertEqual(llm_live_readiness["checks"]["chat_runtime_smoke"]["chat_status"], "completed")
        self.assertFalse(llm_live_readiness["data_policy"]["secret_values_exported"])
        self.assertFalse(llm_live_readiness["data_policy"]["raw_provider_payload_saved"])
        self.assertFalse(llm_live_readiness["data_policy"]["live_provider_call_attempted"])
        self.assertEqual(llm_live_readiness["data_policy"]["private_reasoning_trace"], "do_not_store")
        self.assertTrue(all(llm_live_readiness_artifact_exists.values()), llm_live_readiness_artifact_exists)

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

        self.assertEqual(package_install_doctor["schema"], "paideia-package-install-doctor/v1")
        self.assertTrue(package_install_doctor["passed"])
        self.assertEqual(package_install_doctor["status"], "passed")
        self.assertTrue(package_install_doctor["summary"]["distribution_installed"])
        self.assertGreaterEqual(package_install_doctor["summary"]["console_script_count"], 3)
        self.assertFalse(package_install_doctor["public_safe"]["network_call_performed"])
        self.assertFalse(package_install_doctor["public_safe"]["subprocess_executed"])
        self.assertFalse(package_install_doctor["public_safe"]["local_absolute_paths_exported"])
        package_checks = {item["id"]: item for item in package_install_doctor["checks"]}
        self.assertTrue(package_checks["installed_distribution_metadata_matches_pyproject"]["passed"])
        self.assertTrue(package_checks["distribution_console_scripts_match_pyproject"]["passed"])
        self.assertTrue(package_checks["console_script_targets_importable_callables"]["passed"])

        self.assertEqual(runtime_contract_doctor["schema"], "paideia-runtime-contract-doctor/v1")
        self.assertTrue(runtime_contract_doctor["passed"])
        self.assertEqual(runtime_contract_doctor["status"], "passed")
        self.assertEqual(runtime_contract_doctor["summary"]["failed_count"], 0)
        self.assertFalse(runtime_contract_doctor["summary"]["network_call_performed"])
        self.assertFalse(runtime_contract_doctor["summary"]["subprocess_executed"])
        self.assertFalse(runtime_contract_doctor["summary"]["live_provider_called"])
        runtime_checks = {item["id"]: item for item in runtime_contract_doctor["checks"]}
        self.assertTrue(runtime_checks["live_agent_loop_contract_passed"]["passed"])
        self.assertTrue(runtime_checks["fail_closed_runtime_contract_passed"]["passed"])
        self.assertEqual(
            runtime_contract_doctor["artifacts"]["live_agent_loop_contract"]["details"]["run_status"],
            "completed",
        )
        self.assertEqual(
            runtime_contract_doctor["artifacts"]["fail_closed_runtime_contract"]["details"]["direct_agent_run_status"],
            "needs_configuration",
        )
        self.assertFalse(runtime_contract_doctor["public_safe"]["network_call_performed"])
        self.assertFalse(runtime_contract_doctor["public_safe"]["subprocess_executed"])
        self.assertFalse(runtime_contract_doctor["public_safe"]["live_provider_called"])

        self.assertEqual(first_run_doctor["schema"], "paideia-first-run-doctor/v1")
        self.assertTrue(first_run_doctor["passed"])
        self.assertEqual(first_run_doctor["status"], "passed")
        self.assertEqual(first_run_doctor["summary"]["failed_count"], 0)
        self.assertFalse(first_run_doctor["summary"]["network_call_performed"])
        self.assertFalse(first_run_doctor["summary"]["subprocess_executed"])
        self.assertFalse(first_run_doctor["summary"]["live_provider_called"])
        self.assertEqual(first_run_doctor["public_safe"]["private_reasoning_trace"], "do_not_store")
        first_run_checks = {item["id"]: item for item in first_run_doctor["checks"]}
        for check_id in {
            "role_model_catalog_available",
            "llm_provider_matrix_public_safe",
            "llm_onboarding_checklist_public_safe",
            "llm_connection_profile_public_safe",
            "deterministic_provider_doctor_ready",
            "llm_adapter_contracts_passed",
            "application_engine_smoke_passed",
            "agent_runtime_smoke_passed",
            "chat_runtime_smoke_passed",
            "llm_live_readiness_suite_public_safe",
            "tool_capability_audit_passed",
            "action_policy_eval_passed",
            "public_release_readiness_passed",
            "source_sbom_public_safe",
            "package_install_doctor_passed",
            "runtime_contract_doctor_passed",
            "no_network_or_llm_by_default",
        }:
            self.assertTrue(first_run_checks[check_id]["passed"], check_id)
        self.assertIn("graham_value_investing", first_run_doctor["artifacts"]["role_models"]["role_model_ids"])
        self.assertEqual(first_run_doctor["artifacts"]["llm_provider_doctor"]["network_access"], "blocked")
        self.assertEqual(first_run_doctor["artifacts"]["llm_adapter_contracts"]["schema"], "paideia-llm-adapter-contracts/v1")
        self.assertTrue(first_run_doctor["artifacts"]["llm_adapter_contracts"]["passed"])
        self.assertFalse(first_run_doctor["artifacts"]["llm_adapter_contracts"]["network_call_performed"])
        self.assertEqual(first_run_doctor["artifacts"]["llm_connection_profile"]["status"], "offline_ready_no_setup")
        self.assertEqual(first_run_doctor["artifacts"]["agent_runtime_smoke"]["execution_contract_status"], "passed")
        self.assertEqual(first_run_doctor["artifacts"]["chat_runtime_smoke"]["schema"], "paideia-chat-runtime-smoke/v1")
        self.assertEqual(first_run_doctor["artifacts"]["chat_runtime_smoke"]["chat_status"], "completed")
        self.assertFalse(first_run_doctor["artifacts"]["chat_runtime_smoke"]["stored_private_reasoning_trace"])
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["schema"],
            "paideia-llm-live-readiness-suite/v1",
        )
        self.assertFalse(first_run_doctor["artifacts"]["llm_live_readiness"]["live_provider_call_attempted"])
        self.assertTrue(first_run_doctor["artifacts"]["package_install_doctor"]["distribution_installed"])
        self.assertEqual(first_run_doctor["artifacts"]["runtime_contract_doctor"]["status"], "passed")
        self.assertFalse(first_run_doctor["artifacts"]["runtime_contract_doctor"]["live_provider_called"])


if __name__ == "__main__":
    unittest.main()
