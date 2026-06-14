from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class CliSmokeTests(unittest.TestCase):
    def test_llm_runtime_command_module_registers_guarded_command_surface(self) -> None:
        import argparse

        from ai22b.talent_foundry.cli_llm_commands import (
            LLM_RUNTIME_COMMANDS,
            handle_llm_runtime_command,
            register_llm_runtime_commands,
        )

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        register_llm_runtime_commands(subparsers)

        self.assertEqual(
            LLM_RUNTIME_COMMANDS,
            {
                "doctor-llm-provider",
                "doctor-llm-adapters",
                "run-llm-application-smoke",
                "run-agent-runtime-smoke",
                "run-chat-runtime-smoke",
                "doctor-llm-live-readiness",
            },
        )
        self.assertEqual(set(subparsers.choices), LLM_RUNTIME_COMMANDS)
        parsed = parser.parse_args(
            [
                "run-agent-runtime-smoke",
                "--llm-engine",
                "deterministic_local",
                "--output",
                "agent_runtime_smoke.json",
            ]
        )
        self.assertEqual(parsed.command, "run-agent-runtime-smoke")
        self.assertEqual(parsed.llm_mode, "offline")
        self.assertIsNone(handle_llm_runtime_command(argparse.Namespace(command="list-role-models")))

    def test_public_cli_smoke_commands_write_reviewable_outputs(self) -> None:
        from ai22b.talent_foundry.action_policy import ACTION_POLICY_DECISION_MODEL
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            role_models_path = tmp_path / "role_models.json"
            role_model_curricula_path = tmp_path / "role_model_curricula.json"
            llm_services_path = tmp_path / "llm_services.json"
            llm_onboarding_path = tmp_path / "llm_onboarding_checklist.json"
            llm_connection_profile_path = tmp_path / "llm_connection_profile.json"
            llm_live_setup_guide_path = tmp_path / "llm_live_setup_guide.json"
            llm_connection_status_path = tmp_path / "llm_connection_status.json"
            llm_connection_status_external_path = tmp_path / "llm_connection_status.openrouter.json"
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
            task_pursuit_plan_path = tmp_path / "task_pursuit_plan.json"

            role_models_code = cli_main(
                [
                    "list-role-models",
                    "--domain",
                    "securities_research",
                    "--output",
                    str(role_models_path),
                ]
            )
            role_model_curricula_code = cli_main(
                [
                    "list-role-model-curricula",
                    "--output",
                    str(role_model_curricula_path),
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
            llm_live_setup_guide_code = cli_main(
                [
                    "build-llm-live-setup-guide",
                    "--llm-engine",
                    "deterministic_local",
                    "--output",
                    str(llm_live_setup_guide_path),
                ]
            )
            llm_connection_status_code = cli_main(
                [
                    "show-llm-connection-status",
                    "--llm-engine",
                    "deterministic_local",
                    "--output",
                    str(llm_connection_status_path),
                    "--strict",
                ]
            )
            llm_connection_status_external_code = cli_main(
                [
                    "show-llm-connection-status",
                    "--llm-engine",
                    "openrouter_api",
                    "--output",
                    str(llm_connection_status_external_path),
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
            task_pursuit_plan_code = cli_main(
                [
                    "build-task-pursuit-plan",
                    "--request",
                    "Build a local verified report and keep iterating until tests pass.",
                    "--output",
                    str(task_pursuit_plan_path),
                ]
            )

            role_models = json.loads(role_models_path.read_text(encoding="utf-8"))
            role_model_curricula = json.loads(role_model_curricula_path.read_text(encoding="utf-8"))
            llm_services = json.loads(llm_services_path.read_text(encoding="utf-8"))
            llm_onboarding = json.loads(llm_onboarding_path.read_text(encoding="utf-8"))
            llm_connection_profile = json.loads(llm_connection_profile_path.read_text(encoding="utf-8"))
            llm_live_setup_guide = json.loads(llm_live_setup_guide_path.read_text(encoding="utf-8"))
            llm_connection_status = json.loads(llm_connection_status_path.read_text(encoding="utf-8"))
            llm_connection_status_external = json.loads(
                llm_connection_status_external_path.read_text(encoding="utf-8")
            )
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
            task_pursuit_plan = json.loads(task_pursuit_plan_path.read_text(encoding="utf-8"))

        self.assertEqual(role_models_code, 0)
        self.assertEqual(role_model_curricula_code, 0)
        self.assertEqual(llm_services_code, 0)
        self.assertEqual(llm_onboarding_code, 0)
        self.assertEqual(llm_connection_profile_code, 0)
        self.assertEqual(llm_live_setup_guide_code, 0)
        self.assertEqual(llm_connection_status_code, 0)
        self.assertEqual(llm_connection_status_external_code, 0)
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
        self.assertEqual(task_pursuit_plan_code, 0)

        self.assertEqual(role_models["schema"], "ai-talent-role-model-list/v1")
        self.assertEqual(role_models["domain"], "securities_research")
        self.assertIn("graham_value_investing", {item["role_model_id"] for item in role_models["role_models"]})

        self.assertEqual(role_model_curricula["schema"], "paideia-role-model-curriculum-catalog/v1")
        self.assertTrue(role_model_curricula["summary"]["ready_for_onboarding"])
        self.assertEqual(role_model_curricula["summary"]["missing_curriculum_count"], 0)
        self.assertIn("hopper_software_tooling", role_model_curricula["summary"]["role_model_ids"])
        self.assertFalse(role_model_curricula["public_safe"]["network_call_performed"])
        self.assertFalse(role_model_curricula["public_safe"]["private_materials_included"])
        curricula_by_id = {item["role_model_id"]: item for item in role_model_curricula["role_models"]}
        self.assertEqual(curricula_by_id["graham_value_investing"]["curriculum"]["status"], "connected")
        self.assertIn("--role-model graham_value_investing", curricula_by_id["graham_value_investing"]["blueprint_command"])

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

        self.assertEqual(task_pursuit_plan["schema"], "paideia-task-pursuit-plan/v1")
        self.assertTrue(task_pursuit_plan["validation"]["passed"])
        self.assertEqual(task_pursuit_plan["necessary_research_plan"]["external_search_default"], "only_if_needed")
        self.assertFalse(task_pursuit_plan["public_safe"]["network_call_performed"])

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

        self.assertEqual(llm_live_setup_guide["schema"], "paideia-llm-live-setup-guide/v1")
        self.assertEqual(llm_live_setup_guide["status"], "offline_ready_no_live_setup_required")
        self.assertEqual(llm_live_setup_guide["selected_llm_service"]["engine"], "deterministic_local")
        self.assertFalse(llm_live_setup_guide["readiness_gate"]["requires_explicit_live_check"])
        self.assertFalse(llm_live_setup_guide["public_safe"]["network_call_performed"])
        self.assertFalse(llm_live_setup_guide["public_safe"]["secret_values_exported"])
        runbook_ids = {item["id"] for item in llm_live_setup_guide["safe_runbook"]}
        self.assertLessEqual(
            {
                "review_connection_profile",
                "no_network_provider_doctor",
                "explicit_live_readiness_suite",
                "first_live_chat_template",
            },
            runbook_ids,
        )

        self.assertEqual(llm_connection_status["schema"], "paideia-llm-connection-status-card/v1")
        self.assertEqual(llm_connection_status["status"], "offline_ready")
        self.assertEqual(llm_connection_status["selected_llm_service"]["engine"], "deterministic_local")
        self.assertEqual(llm_connection_status["primary_next_action_id"], "offline_first_chat")
        self.assertFalse(llm_connection_status["public_safe"]["network_call_performed"])
        self.assertFalse(llm_connection_status["public_safe"]["secret_values_exported"])
        self.assertIn(
            "offline_first_chat",
            {item["action_id"] for item in llm_connection_status["next_action_queue"]},
        )
        self.assertTrue(any(item["recommended"] for item in llm_connection_status["next_action_queue"]))
        self.assertEqual(llm_connection_status_external["schema"], "paideia-llm-connection-status-card/v1")
        self.assertEqual(llm_connection_status_external["status"], "needs_owner_configuration")
        self.assertEqual(llm_connection_status_external["selected_llm_service"]["engine"], "openrouter_api")
        self.assertEqual(llm_connection_status_external["primary_next_action_id"], "configure_required_inputs")
        self.assertFalse(llm_connection_status_external["public_safe"]["network_call_performed"])
        self.assertIn(
            "configure_required_inputs",
            {item["action_id"] for item in llm_connection_status_external["next_action_queue"]},
        )

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
        self.assertEqual(
            agent_runtime_smoke["details"]["tool_execution_status_card_schema"],
            "paideia-tool-execution-status-card/v1",
        )
        self.assertEqual(agent_runtime_smoke["details"]["tool_execution_status_card_status"], "completed_verified")
        self.assertTrue(agent_runtime_smoke["details"]["tool_execution_status_card_evidence_completed"])
        self.assertFalse(agent_runtime_smoke["details"]["tool_execution_status_card_external_side_effects_performed"])
        self.assertTrue(agent_runtime_smoke["details"]["tool_execution_status_card_local_artifacts_materialized"])
        self.assertEqual(
            agent_runtime_smoke["details"]["tool_artifact_manifest_schema"],
            "paideia-tool-execution-artifact-manifest/v1",
        )
        self.assertEqual(agent_runtime_smoke["details"]["tool_artifact_manifest_status"], "materialized")
        self.assertEqual(agent_runtime_smoke["details"]["tool_artifact_manifest_file"], "tool_execution_artifact_manifest.json")
        self.assertTrue(agent_runtime_smoke["details"]["tool_artifact_manifest_file_exists"])
        self.assertTrue(agent_runtime_smoke["details"]["tool_artifact_files_exist"])
        self.assertTrue(agent_runtime_smoke["details"]["tool_artifact_relative_paths_only"])
        self.assertTrue(agent_runtime_smoke["details"]["tool_artifact_evidence_packet_materialized"])
        self.assertTrue(agent_runtime_smoke["details"]["tool_artifact_public_safe"])
        self.assertIn("evidence_packet", agent_runtime_smoke["details"]["completed_tools"])
        self.assertEqual(agent_runtime_smoke["details"]["missing_required_tools"], [])
        self.assertEqual(agent_runtime_smoke["details"]["memory_decision"], "candidate_pending_boss_review")
        self.assertFalse(agent_runtime_smoke["details"]["memory_auto_promotion_performed"])
        self.assertFalse(agent_runtime_smoke["details"]["preflight_network_call_made"])
        self.assertEqual(agent_runtime_smoke["details"]["network_default"], "blocked")
        self.assertEqual(agent_runtime_smoke["details"]["subprocess_default"], "blocked")
        self.assertTrue(agent_runtime_smoke["details"]["public_safe"])
        self.assertEqual(
            agent_runtime_smoke["details"]["agent_runtime_status_card_schema"],
            "paideia-agent-runtime-status-card/v1",
        )
        self.assertEqual(
            agent_runtime_smoke["details"]["agent_runtime_status_card_status"],
            "completed_verified",
        )
        self.assertTrue(agent_runtime_smoke["details"]["agent_runtime_status_card_public_safe"])
        self.assertEqual(
            agent_runtime_smoke["details"]["agent_runtime_status_card_memory_decision"],
            "candidate_pending_boss_review",
        )
        self.assertEqual(agent_runtime_smoke["live_llm_agent_proof"]["schema"], "paideia-live-llm-agent-proof/v1")
        self.assertEqual(agent_runtime_smoke["live_llm_agent_proof"]["status"], "offline_verified")
        self.assertTrue(agent_runtime_smoke["live_llm_agent_proof"]["passed"])
        self.assertEqual(
            agent_runtime_smoke["live_llm_agent_proof"]["provider_path"],
            "offline_deterministic_no_provider_call",
        )

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
        self.assertEqual(
            chat_runtime_smoke["details"]["runtime_status_card_schema"],
            "paideia-chat-runtime-status-card/v1",
        )
        self.assertEqual(chat_runtime_smoke["details"]["runtime_status_card_status"], "completed_offline")
        self.assertFalse(chat_runtime_smoke["details"]["runtime_status_card_fallback_used"])
        self.assertFalse(chat_runtime_smoke["details"]["runtime_status_card_presented_as_live"])
        self.assertEqual(chat_runtime_smoke["details"]["runtime_status_card_learning_decision"], "not_requested")
        self.assertEqual(
            chat_runtime_smoke["details"]["memory_lifecycle_status_card_schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(chat_runtime_smoke["details"]["memory_lifecycle_status_card_status"], "passed")
        self.assertIsInstance(chat_runtime_smoke["details"]["memory_lifecycle_status_card_selected_count"], int)
        self.assertTrue(chat_runtime_smoke["details"]["memory_lifecycle_status_card_quarantined_excluded"])
        self.assertEqual(
            chat_runtime_smoke["details"]["memory_lifecycle_status_card_learning_decision"],
            "not_requested",
        )
        self.assertEqual(
            chat_runtime_smoke["details"]["runtime_status_card_memory_lifecycle_schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(chat_runtime_smoke["details"]["runtime_status_card_memory_lifecycle_status"], "passed")
        self.assertTrue(
            chat_runtime_smoke["details"]["runtime_status_card_memory_lifecycle_quarantined_excluded"]
        )
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
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["schema"],
            "paideia-live-connection-status-card/v1",
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["status"],
            "offline_verified_live_not_attempted",
        )
        self.assertTrue(llm_live_readiness["live_connection_status_card"]["offline_ready"])
        self.assertFalse(llm_live_readiness["live_connection_status_card"]["ready_for_live_chat"])
        self.assertFalse(llm_live_readiness["live_connection_status_card"]["ready_for_live_agent_work"])
        self.assertIsNone(llm_live_readiness["live_connection_status_card"]["blocking_step"])
        self.assertFalse(
            llm_live_readiness["live_connection_status_card"]["public_safe"]["live_provider_call_attempted"]
        )
        self.assertFalse(
            llm_live_readiness["live_connection_status_card"]["public_safe"]["live_provider_call_requested"]
        )
        self.assertFalse(
            llm_live_readiness["live_connection_status_card"]["public_safe"]["provider_client_generate_attempted"]
        )
        self.assertFalse(
            llm_live_readiness["live_connection_status_card"]["public_safe"]["provider_doctor_call_attempted"]
        )
        self.assertFalse(
            llm_live_readiness["live_connection_status_card"]["public_safe"]["provider_doctor_network_call_made"]
        )
        self.assertTrue(
            llm_live_readiness["live_connection_status_card"]["public_safe"][
                "live_provider_call_attempted_only_when_requested"
            ]
        )
        self.assertTrue(
            llm_live_readiness["live_connection_status_card"]["public_safe"][
                "provider_client_attempted_only_when_requested"
            ]
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["agent_runtime_status_card"]["schema"],
            "paideia-agent-runtime-status-card/v1",
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["agent_runtime_status_card"]["status"],
            "completed_verified",
        )
        self.assertTrue(
            llm_live_readiness["live_connection_status_card"]["agent_runtime_status_card"]["public_safe"]
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["agent_tool_artifacts"]["manifest_schema"],
            "paideia-tool-execution-artifact-manifest/v1",
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["agent_tool_artifacts"]["manifest_status"],
            "materialized",
        )
        self.assertTrue(
            llm_live_readiness["live_connection_status_card"]["agent_tool_artifacts"][
                "evidence_packet_materialized"
            ]
        )
        self.assertTrue(llm_live_readiness["live_connection_status_card"]["agent_tool_artifacts"]["public_safe"])
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["live_llm_agent_proof"]["schema"],
            "paideia-live-llm-agent-proof/v1",
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["live_llm_agent_proof"]["status"],
            "offline_verified",
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["live_llm_agent_proof"]["provider_path"],
            "offline_deterministic_no_provider_call",
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["chat_memory_lifecycle_status_card"]["schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["chat_memory_lifecycle_status_card"]["status"],
            "passed",
        )
        self.assertTrue(
            llm_live_readiness["live_connection_status_card"]["chat_memory_lifecycle_status_card"][
                "quarantined_excluded"
            ]
        )
        self.assertEqual(
            llm_live_readiness["live_connection_status_card"]["chat_runtime_status_card"]["memory_lifecycle"][
                "schema"
            ],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertTrue(llm_live_readiness["checks"]["provider_doctor"]["passed"])
        self.assertTrue(llm_live_readiness["checks"]["application_smoke"]["passed"])
        self.assertTrue(llm_live_readiness["checks"]["agent_runtime_smoke"]["passed"])
        self.assertEqual(
            llm_live_readiness["checks"]["agent_runtime_smoke"]["agent_runtime_status_card_schema"],
            "paideia-agent-runtime-status-card/v1",
        )
        self.assertEqual(
            llm_live_readiness["checks"]["agent_runtime_smoke"]["agent_runtime_status_card_status"],
            "completed_verified",
        )
        self.assertTrue(
            llm_live_readiness["checks"]["agent_runtime_smoke"]["agent_runtime_status_card_public_safe"]
        )
        self.assertEqual(
            llm_live_readiness["checks"]["agent_runtime_smoke"]["tool_artifact_manifest_schema"],
            "paideia-tool-execution-artifact-manifest/v1",
        )
        self.assertEqual(llm_live_readiness["checks"]["agent_runtime_smoke"]["tool_artifact_manifest_status"], "materialized")
        self.assertTrue(llm_live_readiness["checks"]["agent_runtime_smoke"]["tool_artifact_files_exist"])
        self.assertTrue(llm_live_readiness["checks"]["agent_runtime_smoke"]["tool_artifact_public_safe"])
        self.assertEqual(
            llm_live_readiness["checks"]["agent_runtime_smoke"]["live_llm_agent_proof"]["schema"],
            "paideia-live-llm-agent-proof/v1",
        )
        self.assertEqual(
            llm_live_readiness["checks"]["agent_runtime_smoke"]["live_llm_agent_proof"]["status"],
            "offline_verified",
        )
        self.assertTrue(llm_live_readiness["checks"]["chat_runtime_smoke"]["passed"])
        self.assertEqual(llm_live_readiness["checks"]["chat_runtime_smoke"]["chat_status"], "completed")
        self.assertEqual(
            llm_live_readiness["checks"]["chat_runtime_smoke"]["runtime_status_card_schema"],
            "paideia-chat-runtime-status-card/v1",
        )
        self.assertEqual(
            llm_live_readiness["checks"]["chat_runtime_smoke"]["runtime_status_card_status"],
            "completed_offline",
        )
        self.assertFalse(llm_live_readiness["checks"]["chat_runtime_smoke"]["runtime_status_card_fallback_used"])
        self.assertFalse(
            llm_live_readiness["checks"]["chat_runtime_smoke"]["runtime_status_card_presented_as_live"]
        )
        self.assertEqual(
            llm_live_readiness["checks"]["chat_runtime_smoke"]["runtime_status_card_learning_decision"],
            "not_requested",
        )
        self.assertEqual(
            llm_live_readiness["checks"]["chat_runtime_smoke"]["memory_lifecycle_status_card_schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(
            llm_live_readiness["checks"]["chat_runtime_smoke"]["memory_lifecycle_status_card_status"],
            "passed",
        )
        self.assertTrue(
            llm_live_readiness["checks"]["chat_runtime_smoke"][
                "memory_lifecycle_status_card_quarantined_excluded"
            ]
        )
        self.assertFalse(llm_live_readiness["data_policy"]["secret_values_exported"])
        self.assertFalse(llm_live_readiness["data_policy"]["raw_provider_payload_saved"])
        self.assertFalse(llm_live_readiness["data_policy"]["live_provider_call_requested"])
        self.assertFalse(llm_live_readiness["data_policy"]["live_provider_call_attempted"])
        self.assertFalse(llm_live_readiness["data_policy"]["provider_client_generate_attempted"])
        self.assertFalse(llm_live_readiness["data_policy"]["provider_doctor_network_call_made"])
        self.assertFalse(llm_live_readiness["data_policy"]["provider_doctor_blocked_before_transport"])
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
        self.assertTrue(tool_audit["details"]["result_record_checks"]["all_have_execution_record_schema"])
        self.assertTrue(tool_audit["details"]["result_record_checks"]["all_have_output_digest"])
        self.assertTrue(tool_audit["details"]["result_record_checks"]["no_network_calls"])
        self.assertTrue(tool_audit["details"]["result_record_checks"]["no_subprocess_execution"])
        self.assertTrue(tool_audit["details"]["result_record_checks"]["no_side_effects_performed"])
        self.assertTrue(tool_audit["details"]["result_record_checks"]["private_reasoning_not_stored"])

        self.assertEqual(policy_eval["schema"], "paideia-action-policy-eval-report/v1")
        self.assertEqual(policy_eval["status"], "passed")
        self.assertEqual(policy_eval["summary"]["failed_count"], 0)
        self.assertEqual(policy_eval["runtime_policy"]["decision_model"], ACTION_POLICY_DECISION_MODEL)
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
            "role_model_curriculum_catalog_ready",
            "llm_provider_matrix_public_safe",
            "llm_onboarding_checklist_public_safe",
            "llm_connection_profile_public_safe",
            "llm_live_setup_guide_public_safe",
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
        self.assertEqual(
            first_run_doctor["artifacts"]["role_model_curriculum_catalog"]["schema"],
            "paideia-role-model-curriculum-catalog/v1",
        )
        self.assertTrue(first_run_doctor["artifacts"]["role_model_curriculum_catalog"]["ready_for_onboarding"])
        self.assertEqual(first_run_doctor["artifacts"]["role_model_curriculum_catalog"]["missing_curriculum_count"], 0)
        self.assertFalse(first_run_doctor["artifacts"]["role_model_curriculum_catalog"]["network_call_performed"])
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_setup_guide"]["schema"],
            "paideia-llm-live-setup-guide/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_setup_guide"]["status"],
            "offline_ready_no_live_setup_required",
        )
        self.assertFalse(first_run_doctor["artifacts"]["llm_live_setup_guide"]["network_call_performed"])
        self.assertEqual(first_run_doctor["artifacts"]["llm_provider_doctor"]["network_access"], "blocked")
        self.assertEqual(first_run_doctor["artifacts"]["llm_adapter_contracts"]["schema"], "paideia-llm-adapter-contracts/v1")
        self.assertTrue(first_run_doctor["artifacts"]["llm_adapter_contracts"]["passed"])
        self.assertFalse(first_run_doctor["artifacts"]["llm_adapter_contracts"]["network_call_performed"])
        self.assertEqual(first_run_doctor["artifacts"]["llm_connection_profile"]["status"], "offline_ready_no_setup")
        self.assertEqual(first_run_doctor["artifacts"]["agent_runtime_smoke"]["execution_contract_status"], "passed")
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["agent_runtime_status_card_schema"],
            "paideia-agent-runtime-status-card/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["agent_runtime_status_card_status"],
            "completed_verified",
        )
        self.assertTrue(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["agent_runtime_status_card_public_safe"]
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["tool_execution_status_card_schema"],
            "paideia-tool-execution-status-card/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["tool_execution_status_card_status"],
            "completed_verified",
        )
        self.assertTrue(
            first_run_doctor["artifacts"]["agent_runtime_smoke"][
                "tool_execution_status_card_local_artifacts_materialized"
            ]
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["tool_artifact_manifest_schema"],
            "paideia-tool-execution-artifact-manifest/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["tool_artifact_manifest_status"],
            "materialized",
        )
        self.assertTrue(first_run_doctor["artifacts"]["agent_runtime_smoke"]["tool_artifact_files_exist"])
        self.assertTrue(
            first_run_doctor["artifacts"]["agent_runtime_smoke"][
                "tool_artifact_evidence_packet_materialized"
            ]
        )
        self.assertTrue(first_run_doctor["artifacts"]["agent_runtime_smoke"]["tool_artifact_public_safe"])
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["live_llm_agent_proof_schema"],
            "paideia-live-llm-agent-proof/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["live_llm_agent_proof_status"],
            "offline_verified",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["agent_runtime_smoke"]["live_llm_agent_proof_provider_path"],
            "offline_deterministic_no_provider_call",
        )
        self.assertEqual(first_run_doctor["artifacts"]["chat_runtime_smoke"]["schema"], "paideia-chat-runtime-smoke/v1")
        self.assertEqual(first_run_doctor["artifacts"]["chat_runtime_smoke"]["chat_status"], "completed")
        self.assertFalse(first_run_doctor["artifacts"]["chat_runtime_smoke"]["stored_private_reasoning_trace"])
        self.assertEqual(
            first_run_doctor["artifacts"]["chat_runtime_smoke"]["runtime_status_card_schema"],
            "paideia-chat-runtime-status-card/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["chat_runtime_smoke"]["runtime_status_card_status"],
            "completed_offline",
        )
        self.assertFalse(first_run_doctor["artifacts"]["chat_runtime_smoke"]["runtime_status_card_fallback_used"])
        self.assertFalse(
            first_run_doctor["artifacts"]["chat_runtime_smoke"]["runtime_status_card_presented_as_live"]
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["chat_runtime_smoke"]["runtime_status_card_learning_decision"],
            "not_requested",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["chat_runtime_smoke"]["memory_lifecycle_status_card_schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["chat_runtime_smoke"]["memory_lifecycle_status_card_status"],
            "passed",
        )
        self.assertTrue(
            first_run_doctor["artifacts"]["chat_runtime_smoke"][
                "memory_lifecycle_status_card_quarantined_excluded"
            ]
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["schema"],
            "paideia-llm-live-readiness-suite/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["live_connection_status_card_schema"],
            "paideia-live-connection-status-card/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["live_connection_status_card_status"],
            "offline_verified_live_not_attempted",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["agent_runtime_status_card_schema"],
            "paideia-agent-runtime-status-card/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["agent_runtime_status_card_status"],
            "completed_verified",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["live_llm_agent_proof_schema"],
            "paideia-live-llm-agent-proof/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["live_llm_agent_proof_status"],
            "offline_verified",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["live_llm_agent_proof_provider_path"],
            "offline_deterministic_no_provider_call",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["chat_memory_lifecycle_status_card_schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(
            first_run_doctor["artifacts"]["llm_live_readiness"]["chat_memory_lifecycle_status_card_status"],
            "passed",
        )
        self.assertFalse(first_run_doctor["artifacts"]["llm_live_readiness"]["ready_for_live_chat"])
        self.assertFalse(first_run_doctor["artifacts"]["llm_live_readiness"]["ready_for_live_agent_work"])
        self.assertFalse(first_run_doctor["artifacts"]["llm_live_readiness"]["live_provider_call_attempted"])
        self.assertEqual(
            first_run_doctor["artifacts"]["action_policy_eval"]["decision_model"],
            ACTION_POLICY_DECISION_MODEL,
        )
        self.assertTrue(first_run_doctor["artifacts"]["package_install_doctor"]["distribution_installed"])
        self.assertEqual(first_run_doctor["artifacts"]["runtime_contract_doctor"]["status"], "passed")
        self.assertFalse(first_run_doctor["artifacts"]["runtime_contract_doctor"]["live_provider_called"])


if __name__ == "__main__":
    unittest.main()
