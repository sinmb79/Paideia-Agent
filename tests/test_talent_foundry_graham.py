from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen


class GrahamTalentFoundryTests(unittest.TestCase):
    def test_role_model_catalog_lists_graham(self) -> None:
        from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model

        models = list_role_models("securities_research")
        summaries = [summarize_role_model(model) for model in models]

        self.assertIn("graham_value_investing", {item["role_model_id"] for item in summaries})
        graham = next(item for item in summaries if item["role_model_id"] == "graham_value_investing")
        self.assertEqual(graham["birth_date"], "1894-05-09")
        self.assertEqual(graham["copyright_policy"], "metadata_and_reading_plan_only")

    def test_role_model_catalog_lists_agent_use_case_tracks(self) -> None:
        from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model

        software_models = [summarize_role_model(model) for model in list_role_models("software_agent_engineering")]
        all_models = [summarize_role_model(model) for model in list_role_models()]

        self.assertIn("hopper_software_tooling", {item["role_model_id"] for item in software_models})
        self.assertIn("dijkstra_verified_programming", {item["role_model_id"] for item in software_models})
        self.assertIn("tukey_data_analysis", {item["role_model_id"] for item in all_models})
        self.assertGreaterEqual(len(all_models), 10)
        hopper = next(item for item in software_models if item["role_model_id"] == "hopper_software_tooling")
        self.assertEqual(hopper["status"], "ready_public_metadata")
        self.assertIn("debugging", hopper["primary_agent_use_case"])

    def test_graham_blueprint_contains_role_model_saju_curriculum_and_artifacts(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="증권 리서치 AI 박사를 Graham 방식으로 육성",
            talent_name="신용",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        self.assertEqual(blueprint["track"]["track_id"], "securities_research_phd")
        self.assertEqual(blueprint["role_model"]["role_model_id"], "graham_value_investing")
        self.assertEqual(blueprint["role_model_birth_seed"]["pillars"]["year"]["label"], "갑오")
        self.assertEqual(blueprint["curriculum_manifest"]["curriculum_id"], "graham_securities_research")
        self.assertEqual(blueprint["agent_surface"], "cli-console")
        self.assertLessEqual(
            {"role_model_profile", "saju_narrative_seed", "curriculum_manifest", "assessment_transcript", "reasoning_kibo"},
            {item["id"] for item in blueprint["artifact_plan"]},
        )

    def test_graham_raise_writes_dedicated_training_outputs(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="증권 리서치 AI 박사를 Graham 방식으로 육성",
            talent_name="신용",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "graham")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            transcript = json.loads(artifacts["assessment_transcript"].read_text(encoding="utf-8"))
            manifest = json.loads(artifacts["agent_manifest"].read_text(encoding="utf-8"))

            self.assertTrue(artifacts["role_model_profile"].exists())
            self.assertTrue(artifacts["saju_narrative_seed"].exists())
            self.assertTrue(artifacts["curriculum_manifest"].exists())
            self.assertTrue(artifacts["reasoning_kibo"].exists())
            self.assertTrue(artifacts["employment_record"].exists())
            self.assertEqual(run["status"], "employment_ready")
            self.assertGreaterEqual(len(transcript["results"]), 9)
            self.assertTrue(transcript["graduation_ready"])
            self.assertEqual(
                manifest["identity_source"]["role_model_inspiration"]["role_model_id"],
                "graham_value_investing",
            )
            self.assertIn("openclaw_style_agent_manifest", manifest["compatible_targets"])

    def test_cli_list_role_models_and_blueprint_alias(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "blueprint.json"
            self.assertEqual(cli_main(["list-role-models", "--domain", "securities_research"]), 0)
            self.assertEqual(
                cli_main(
                    [
                        "blueprint",
                        "--request",
                        "증권 리서치 AI 박사를 Graham 방식으로 육성",
                        "--talent-name",
                        "신용",
                        "--gender",
                        "남자",
                        "--owner",
                        "보스",
                        "--domain",
                        "securities_research",
                        "--role-model",
                        "graham_value_investing",
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["identity"]["name"], "신용")
            self.assertEqual(data["role_model"]["role_model_id"], "graham_value_investing")

    def test_non_graham_role_model_blueprint_and_raise_use_generic_assessment_ladder(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Raise a developer-tool AI talent through debugging, compiler, and testing projects.",
            talent_name="hopper-junior",
            gender="male",
            domain="software_agent_engineering",
            role_model_id="hopper_software_tooling",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "hopper")
            transcript = json.loads(Path(run["artifacts"]["assessment_transcript"]).read_text(encoding="utf-8"))
            plan = json.loads(Path(run["artifacts"]["talent_plan"]).read_text(encoding="utf-8"))

        self.assertEqual(blueprint["role_model"]["role_model_id"], "hopper_software_tooling")
        self.assertEqual(blueprint["track"]["track_id"], "software_tooling_hopper_track")
        gate_ids = {item["gate_id"] for item in transcript["results"]}
        self.assertIn("compiler_project", gate_ids)
        self.assertIn("systems_debugging_project", gate_ids)
        self.assertTrue(transcript["graduation_ready"])
        self.assertEqual(plan["curriculum_manifest"]["role_model_id"], "hopper_software_tooling")

    def test_onboarding_exposes_multi_provider_llms_and_role_model_choices(self) -> None:
        from ai22b.talent_foundry.console import questions_with_choices
        from ai22b.talent_foundry.llm_runtime import build_llm_runtime_config, invoke_llm_application_engine
        from ai22b.talent_foundry.onboarding_choices import chat_surface_ids, llm_service_ids, resolve_llm_service

        self.assertIn("ollama_local", llm_service_ids())
        self.assertIn("openclaw_gateway_http", llm_service_ids())
        self.assertIn("openrouter_api", llm_service_ids())
        self.assertIn("deepseek_api", llm_service_ids())
        self.assertIn("groq_api", llm_service_ids())
        self.assertIn("gmi_api", llm_service_ids())
        self.assertIn("novita_api", llm_service_ids())
        self.assertIn("huggingface_api", llm_service_ids())
        self.assertIn("kilocode_gateway", llm_service_ids())
        self.assertIn("ollama_cloud", llm_service_ids())
        self.assertIn("synthetic_api", llm_service_ids())
        self.assertIn("arcee_api", llm_service_ids())
        self.assertIn("chutes_api", llm_service_ids())
        self.assertIn("qianfan_api", llm_service_ids())
        self.assertIn("inferrs_local", llm_service_ids())
        self.assertIn("stepfun_api", llm_service_ids())
        self.assertIn("volcengine_plan_api", llm_service_ids())
        self.assertIn("xiaomi_api", llm_service_ids())
        self.assertIn("openclaw-channel-telegram", chat_surface_ids())
        self.assertIn("openclaw-channel-bluebubbles", chat_surface_ids())
        self.assertIn("openclaw-channel-whatsapp", chat_surface_ids())
        questions = questions_with_choices()
        role_question = next(item for item in questions if item["id"] == "role_model_id")
        llm_question = next(item for item in questions if item["id"] == "llm_service")
        chat_question = next(item for item in questions if item["id"] == "chat_surface")
        self.assertIn("hopper_software_tooling", {item["id"] for item in role_question["choices"]})
        self.assertIn("anthropic_claude_api", {item["id"] for item in llm_question["choices"]})
        self.assertIn("openclaw-channel-telegram", {item["id"] for item in chat_question["choices"]})

        config = build_llm_runtime_config(engine="openrouter_api", model="user-selected-model")
        result = invoke_llm_application_engine(
            config,
            manifest={"agent": {"name": "sample", "major_goal": "test"}},
            task="test adapter manifest",
        )

        self.assertEqual(config["network_access"], "external_api_selected_data_minimized")
        self.assertEqual(result["status"], "adapter_manifest_ready")

        selected = resolve_llm_service(llm_service="openrouter/meta-llama/llama-3.1-8b")
        self.assertEqual(selected["service_id"], "openrouter_api")
        self.assertEqual(selected["openclaw_provider_id"], "openrouter")
        self.assertEqual(selected["openclaw_model"], "openrouter/meta-llama/llama-3.1-8b")
        self.assertEqual(selected["selected_model"], "meta-llama/llama-3.1-8b")

        gateway = resolve_llm_service(
            llm_service="openclaw-gateway/openrouter/meta-llama/llama-3.1-8b"
        )
        self.assertEqual(gateway["service_id"], "openclaw_gateway_http")
        self.assertEqual(gateway["api_protocol"], "openclaw_gateway_openai_chat_completions")
        self.assertEqual(gateway["openclaw_agent_target"], "openclaw/default")
        self.assertEqual(gateway["openclaw_model"], "openrouter/meta-llama/llama-3.1-8b")
        self.assertEqual(gateway["network_access"], "localhost_only")

        local_vllm = resolve_llm_service(llm_service="vllm/Qwen3-8B")
        self.assertEqual(local_vllm["service_id"], "vllm_local")
        self.assertEqual(local_vllm["network_access"], "localhost_only")

        kilo = resolve_llm_service(llm_service="kilocode/kilo/auto")
        self.assertEqual(kilo["service_id"], "kilocode_gateway")
        self.assertEqual(kilo["selected_model"], "kilo/auto")
        self.assertEqual(kilo["openclaw_provider_id"], "kilocode")
        self.assertEqual(kilo["api_protocol"], "openai_chat_completions")

        ollama_cloud = resolve_llm_service(llm_service="ollama-cloud/kimi-k2.6")
        self.assertEqual(ollama_cloud["service_id"], "ollama_cloud")
        self.assertEqual(ollama_cloud["api_protocol"], "ollama_chat")
        self.assertEqual(ollama_cloud["network_access"], "external_api_selected_data_minimized")

        arcee = resolve_llm_service(llm_service="arcee/trinity-large-thinking")
        self.assertEqual(arcee["service_id"], "arcee_api")
        self.assertEqual(arcee["api_protocol"], "openai_chat_completions")

        minimax = resolve_llm_service(llm_service="minimax/MiniMax-M2.7")
        self.assertEqual(minimax["service_id"], "minimax_api")
        self.assertEqual(minimax["api_protocol"], "anthropic_messages")

        stepfun_plan = resolve_llm_service(llm_service="stepfun-plan/step-3.5-flash")
        self.assertEqual(stepfun_plan["service_id"], "stepfun_plan_api")
        self.assertEqual(stepfun_plan["api_protocol"], "openai_chat_completions")

        qwen_oauth_gateway = resolve_llm_service(llm_service="qwen-oauth/qwen3-coder-plus")
        self.assertEqual(qwen_oauth_gateway["service_id"], "openclaw_gateway_http")
        self.assertEqual(qwen_oauth_gateway["api_protocol"], "openclaw_gateway_openai_chat_completions")
        self.assertEqual(qwen_oauth_gateway["openclaw_model"], "qwen-oauth/qwen3-coder-plus")
        self.assertEqual(qwen_oauth_gateway["openclaw_provider"]["provider_id"], "qwen-oauth")
        self.assertTrue(qwen_oauth_gateway["openclaw_gateway_auto_routed"])
        self.assertEqual(qwen_oauth_gateway["network_access"], "localhost_only")

        copilot_gateway = resolve_llm_service(llm_service="openclaw_github_copilot", llm_model="gpt-5-copilot")
        self.assertEqual(copilot_gateway["service_id"], "openclaw_gateway_http")
        self.assertEqual(copilot_gateway["openclaw_model"], "github-copilot/gpt-5-copilot")
        self.assertTrue(copilot_gateway["openclaw_gateway_auto_routed"])

    def test_openclaw_style_onboarding_questions_are_step_based(self) -> None:
        from ai22b.talent_foundry.console import WIZARD_STEPS, questions_with_choices
        from ai22b.talent_foundry.onboarding_choices import resolve_chat_surface

        questions = questions_with_choices()
        by_id = {item["id"]: item for item in questions}
        step_ids = {step[0] for step in WIZARD_STEPS}

        self.assertIn("existing_config_action", by_id)
        self.assertIn("onboarding_mode", by_id)
        self.assertIn("gateway_mode", by_id)
        self.assertIn("talent_source", by_id)
        self.assertIn("agent_id_card_mode", by_id)
        self.assertIn("health", step_ids)
        self.assertIn("finish", step_ids)
        self.assertEqual(by_id["onboarding_mode"]["default"], "quickstart")
        self.assertIn("quickstart", {item["id"] for item in by_id["onboarding_mode"]["choices"]})
        self.assertIn("owner_self_extension", {item["id"] for item in by_id["talent_source"]["choices"]})
        self.assertEqual(resolve_chat_surface("telegram")["id"], "openclaw-channel-telegram")

    def test_guided_console_writes_openclaw_style_config_identity_payload_and_rollouts(self) -> None:
        from ai22b.talent_foundry.console import run_console_session

        answers = {
            "owner": "보스",
            "request": "Graham 방식으로 증권 리서치 에이전트를 육성하고 첫 대화까지 준비한다.",
            "talent_name": "paideia-test-junior",
            "gender": "남자",
            "initial_goal": "근거 우선 리서치 루틴을 만든다.",
            "cycle_note": "첫 주: 근거, 반례, 안전 경계를 나눈다.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "openclaw_style_console"
            session = run_console_session(
                answers=answers,
                output_dir=output_dir,
                output_path=output_dir / "console_session.json",
            )
            config = json.loads(Path(session["artifacts"]["paideia_onboarding_config"]).read_text(encoding="utf-8"))
            identity_payload = json.loads(Path(session["artifacts"]["agent_id_card_payload"]).read_text(encoding="utf-8"))
            rollouts = json.loads(Path(session["artifacts"]["simulation_rollouts"]).read_text(encoding="utf-8"))
            rollout_execution = json.loads(
                Path(session["artifacts"]["simulation_rollout_execution"]).read_text(encoding="utf-8")
            )
            llm_health = json.loads(Path(session["artifacts"]["llm_service_health"]).read_text(encoding="utf-8"))
            openclaw_runtime = json.loads(Path(session["artifacts"]["openclaw_runtime_bundle"]).read_text(encoding="utf-8"))
            provider_doctor = json.loads(Path(session["artifacts"]["openclaw_provider_doctor"]).read_text(encoding="utf-8"))
            channel_doctor = json.loads(Path(session["artifacts"]["openclaw_channel_doctor"]).read_text(encoding="utf-8"))
            support_matrix = json.loads(Path(session["artifacts"]["openclaw_support_matrix"]).read_text(encoding="utf-8"))
            selection_doctor = json.loads(Path(session["artifacts"]["openclaw_selection_doctor"]).read_text(encoding="utf-8"))
            selection_summary = Path(session["artifacts"]["openclaw_selection_summary"]).read_text(encoding="utf-8")
            selection_bridge_kit = json.loads(
                Path(session["artifacts"]["openclaw_selection_bridge_setup_kit"]).read_text(encoding="utf-8")
            )
            selection_channel_plan = json.loads(
                Path(session["artifacts"]["openclaw_selection_channel_plugin_plan"]).read_text(encoding="utf-8")
            )

        self.assertEqual(session["wizard"]["schema"], "ai22b-paideia-openclaw-style-onboarding/v1")
        self.assertEqual(config["schema"], "ai22b-paideia-openclaw-style-config/v1")
        self.assertIn("openclaw_selection_doctor.json", config["model_auth"]["selection_doctor"])
        self.assertIn("openclaw_bridge_setup_kit.json", config["model_auth"]["selection_bridge_setup_kit"])
        self.assertEqual(config["gateway"]["mode"], "local_loopback")
        self.assertEqual(config["channels"]["external_channels"], "disabled_until_explicit_configuration")
        self.assertIn("openclaw_channel_plugin_plan.json", config["channels"]["selection_channel_plugin_plan"])
        self.assertEqual(identity_payload["schema"], "ai-talent-agent-id-card-payload/v1")
        self.assertFalse(identity_payload["network_action_performed"])
        self.assertEqual(rollouts["schema"], "ai-talent-simulation-rollouts/v1")
        self.assertGreaterEqual(rollouts["summary"]["episode_count"], 4)
        self.assertEqual(rollout_execution["schema"], "ai-talent-simulation-rollout-execution/v1")
        self.assertGreaterEqual(rollout_execution["summary"]["promoted_count"], 3)
        self.assertGreaterEqual(rollout_execution["summary"]["quarantined_count"], 1)
        self.assertEqual(llm_health["schema"], "ai22b-paideia-llm-service-health/v1")
        self.assertEqual(openclaw_runtime["schema"], "ai22b-openclaw-runtime-bundle/v1")
        self.assertEqual(provider_doctor["schema"], "ai22b-openclaw-provider-connector-doctor/v1")
        self.assertEqual(channel_doctor["schema"], "ai22b-openclaw-channel-connector-doctor/v1")
        self.assertEqual(support_matrix["schema"], "ai22b-openclaw-support-matrix/v1")
        self.assertEqual(support_matrix["status"], "pass")
        self.assertEqual(selection_doctor["schema"], "ai22b-openclaw-selection-doctor/v1")
        self.assertEqual(selection_doctor["status"], "ready_for_onboarding")
        self.assertEqual(session["openclaw_selection_doctor"]["status"], "ready_for_onboarding")
        self.assertFalse(selection_doctor["claim_boundary"]["external_network_call_performed"])
        self.assertIn("# OpenClaw Selection Summary", selection_summary)
        self.assertIn("Status: `ready_for_onboarding`", selection_summary)
        self.assertIn("Bridge Setup Kit", selection_summary)
        self.assertIn("OpenClaw selection: ready_for_onboarding", session["openclaw_selection_preview"]["lines"])
        self.assertTrue(any("Bridge setup kit:" in line for line in session["openclaw_selection_preview"]["lines"]))
        self.assertTrue(session["openclaw_selection_preview"]["summary_path"].endswith("OPENCLAW_SELECTION_SUMMARY.md"))
        self.assertEqual(selection_bridge_kit["schema"], "ai22b-openclaw-bridge-setup-kit/v1")
        self.assertIn("webchat", selection_bridge_kit["selection"]["channels"])
        self.assertEqual(selection_channel_plan["schema"], "ai22b-openclaw-channel-plugin-plan/v1")
        self.assertEqual(session["openclaw_runtime"]["selected_support"]["matrix_status"], "pass")
        self.assertFalse(llm_health["network_probe_performed"])

    def test_onboarding_with_openclaw_gateway_writes_runtime_and_gateway_llm_doctor(self) -> None:
        from ai22b.talent_foundry.onboarding import run_agent_onboarding

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "gateway_onboarding"
            session = run_agent_onboarding(
                owner="Boss",
                request="Raise a gateway-connected Paideia securities research agent.",
                talent_name="gateway-onboarding-junior",
                gender="male",
                output_dir=output_dir,
                domain="securities_research",
                role_model_id="graham_value_investing",
                llm_service="openclaw-gateway/openrouter/meta-llama/llama-3.1-8b",
                llm_model_path="http://127.0.0.1:18789",
                chat_surface="openclaw-channel-webchat",
                initial_goal="Verify OpenClaw Gateway readiness.",
                cycle_note="Check Gateway LLM and WebChat follow-up commands.",
            )
            runtime_bundle = json.loads(Path(session["artifacts"]["openclaw_runtime_bundle"]).read_text(encoding="utf-8"))
            gateway_doctor = json.loads(Path(session["artifacts"]["openclaw_gateway_llm_doctor"]).read_text(encoding="utf-8"))
            support_matrix = json.loads(Path(session["artifacts"]["openclaw_support_matrix"]).read_text(encoding="utf-8"))

        self.assertEqual(session["selected_llm_service"]["service_id"], "openclaw_gateway_http")
        self.assertEqual(session["openclaw_runtime"]["selection"]["provider_id"], "openrouter")
        self.assertEqual(session["openclaw_runtime"]["selection"]["channels"], ["webchat"])
        self.assertEqual(session["openclaw_runtime"]["selected_support"]["provider_id"], "openrouter")
        self.assertEqual(
            session["openclaw_runtime"]["selected_support"]["provider_support"]["support_level"],
            "paideia_direct_or_openclaw_gateway_ready",
        )
        self.assertEqual(
            session["openclaw_runtime"]["selected_support"]["channels"][0]["support"]["support_level"],
            "loopback_chat_ready",
        )
        self.assertEqual(support_matrix["status"], "pass")
        self.assertEqual(runtime_bundle["readiness"]["gateway_llm_doctor"]["status"], "ready_for_gateway_start")
        self.assertEqual(gateway_doctor["gateway_contract"]["agent_target"], "openclaw/default")
        self.assertEqual(gateway_doctor["gateway_contract"]["backend_model_header"], "openrouter/meta-llama/llama-3.1-8b")
        self.assertIn("doctor-openclaw-gateway-llm", "\n".join(session["next_commands"]))
        self.assertIn("build-openclaw-support-matrix", "\n".join(session["next_commands"]))

    def test_graham_junior_quickstart_links_chat_dossier_transcript_and_openclaw_doctors(self) -> None:
        from ai22b.config import PROJECT_ROOT
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "graham_quickstart"
            output = output_dir / "quickstart.json"
            result = cli_main(
                [
                    "run-graham-junior-quickstart",
                    "--answers",
                    str(PROJECT_ROOT / "examples" / "graham_junior_onboarding.answers.json"),
                    "--output-dir",
                    str(output_dir),
                    "--output",
                    str(output),
                    "--llm-service",
                    "openclaw-gateway/openrouter/meta-llama/llama-3.1-8b",
                    "--llm-model-path",
                    "http://127.0.0.1:18789",
                    "--chat-surface",
                    "openclaw-channel-webchat",
                    "--channel",
                    "webchat",
                ]
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            artifacts = {key: Path(value) for key, value in report["artifacts"].items() if value}
            gateway_doctor = json.loads(artifacts["openclaw_gateway_llm_doctor"].read_text(encoding="utf-8"))
            first_chat = json.loads(artifacts["first_chat"].read_text(encoding="utf-8"))
            assessment_exists = artifacts["assessment_transcript"].exists()
            dossier_exists = artifacts["hiring_dossier"].exists()
            dossier_markdown_exists = artifacts["hiring_dossier_markdown"].exists()
            runtime_bundle_exists = artifacts["openclaw_runtime_bundle"].exists()
            support_matrix_exists = artifacts["openclaw_support_matrix"].exists()

        self.assertEqual(result, 0)
        self.assertEqual(report["schema"], "ai22b-graham-junior-quickstart/v1")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["selected_llm_service"], "openclaw-gateway/openrouter/meta-llama/llama-3.1-8b")
        self.assertTrue(assessment_exists)
        self.assertTrue(dossier_exists)
        self.assertTrue(dossier_markdown_exists)
        self.assertTrue(runtime_bundle_exists)
        self.assertTrue(support_matrix_exists)
        self.assertEqual(report["openclaw_support"]["matrix_status"], "pass")
        self.assertEqual(report["openclaw_support"]["selected_support"]["provider_id"], "openrouter")
        self.assertEqual(gateway_doctor["status"], "ready_for_gateway_start")
        self.assertEqual(report["openclaw_channel_flow"]["status"], "pass")
        self.assertEqual(first_chat["reply_generation_mode"], "deterministic_local_fallback")
        self.assertFalse(report["security"]["external_network_delivery_performed"])

    def test_owner_self_extension_manifest_redacts_paths_and_content_by_default(self) -> None:
        from ai22b.talent_foundry.self_extension import build_owner_self_extension_manifest

        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "private_owner_materials"
            source_dir.mkdir()
            (source_dir / "preferences.md").write_text("보스 rule: keep work local and verify results.", encoding="utf-8")
            (source_dir / "script.py").write_text("def helper():\n    return 'workflow'\n", encoding="utf-8")
            output = Path(tmp) / "manifest.json"

            manifest = build_owner_self_extension_manifest(source_dir, output_path=output)
            rendered = json.dumps(manifest, ensure_ascii=False)

        self.assertEqual(manifest["schema"], "ai22b-owner-self-extension-manifest/v1")
        self.assertEqual(manifest["scan"]["file_count"], 2)
        self.assertFalse(manifest["source"]["absolute_path_stored"])
        self.assertNotIn(str(source_dir), rendered)
        self.assertNotIn("keep work local", rendered)
        self.assertIn("owner_preference", {signal for item in manifest["items"] for signal in item["learning_signals"]})

    def test_cli_ingest_owner_self_extension_and_llm_health(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "owner"
            source_dir.mkdir()
            (source_dir / "note.md").write_text("workflow memory and project preference", encoding="utf-8")
            owner_manifest = Path(tmp) / "owner_manifest.json"
            health_path = Path(tmp) / "llm_health.json"

            self.assertEqual(
                cli_main(
                    [
                        "ingest-owner-self-extension",
                        "--source-dir",
                        str(source_dir),
                        "--output",
                        str(owner_manifest),
                    ]
                ),
                0,
            )
            self.assertEqual(
                cli_main(
                    [
                        "check-llm-service",
                        "--llm-service",
                        "bigram_local",
                        "--llm-model-path",
                        str(Path(tmp) / "missing_bigram.json"),
                        "--output",
                        str(health_path),
                    ]
                ),
                0,
            )
            owner_data = json.loads(owner_manifest.read_text(encoding="utf-8"))
            health = json.loads(health_path.read_text(encoding="utf-8"))

        self.assertEqual(owner_data["scan"]["file_count"], 1)
        self.assertEqual(health["status"], "needs_model_path")
        self.assertFalse(health["network_probe_performed"])

    def test_cli_lists_openclaw_compatible_providers_and_channels(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "openclaw_compat.json"
            self.assertEqual(cli_main(["list-openclaw-compat", "--output", str(output)]), 0)
            data = json.loads(output.read_text(encoding="utf-8"))
            provider_connectors_output = Path(tmp) / "provider_connectors.json"
            provider_doctor_output = Path(tmp) / "provider_doctor.json"
            self.assertEqual(
                cli_main(["list-openclaw-provider-connectors", "--output", str(provider_connectors_output)]),
                0,
            )
            self.assertEqual(
                cli_main(
                    [
                        "doctor-openclaw-provider-connectors",
                        "--provider",
                        "arcee",
                        "--output",
                        str(provider_doctor_output),
                    ]
                ),
                0,
            )
            connectors_output = Path(tmp) / "channel_connectors.json"
            doctor_output = Path(tmp) / "channel_doctor.json"
            self.assertEqual(
                cli_main(["list-openclaw-channel-connectors", "--output", str(connectors_output)]),
                0,
            )
            self.assertEqual(
                cli_main(["doctor-openclaw-channel-connectors", "--channel", "telegram", "--output", str(doctor_output)]),
                0,
            )
            provider_connectors = json.loads(provider_connectors_output.read_text(encoding="utf-8"))
            provider_doctor = json.loads(provider_doctor_output.read_text(encoding="utf-8"))
            connectors = json.loads(connectors_output.read_text(encoding="utf-8"))
            channel_doctor = json.loads(doctor_output.read_text(encoding="utf-8"))

        provider_ids = {item["provider_id"] for item in data["model_providers"]["providers"]}
        all_provider_ids = provider_ids | set(data["model_providers"]["manifest_only_providers"])
        channel_ids = {item["channel_id"] for item in data["chat_channels"]["channels"]}
        self.assertIn("openai", provider_ids)
        self.assertIn("openrouter", provider_ids)
        self.assertIn("ollama", provider_ids)
        self.assertIn("lmstudio", provider_ids)
        self.assertIn("zai", provider_ids)
        self.assertIn("gmi", provider_ids)
        self.assertIn("novita", provider_ids)
        self.assertIn("huggingface", provider_ids)
        self.assertIn("kilocode", provider_ids)
        self.assertIn("ollama-cloud", provider_ids)
        self.assertIn("arcee", provider_ids)
        self.assertIn("chutes", provider_ids)
        self.assertIn("qianfan", provider_ids)
        self.assertIn("inferrs", provider_ids)
        self.assertIn("minimax", provider_ids)
        self.assertIn("stepfun", provider_ids)
        self.assertIn("stepfun-plan", provider_ids)
        self.assertIn("volcengine", provider_ids)
        self.assertIn("volcengine-plan", provider_ids)
        self.assertIn("xiaomi", provider_ids)
        self.assertIn("xiaomi-token-plan", provider_ids)
        self.assertIn("volcengine", all_provider_ids)
        self.assertIn("volcengine-plan", all_provider_ids)
        self.assertIn("byteplus-plan", all_provider_ids)
        self.assertIn("qwen-oauth", all_provider_ids)
        self.assertIn("pixverse", all_provider_ids)
        self.assertIn("ds4", all_provider_ids)
        self.assertIn("google-gemini-cli", all_provider_ids)
        self.assertIn("claude-max-api-proxy", all_provider_ids)
        self.assertIn("discord", channel_ids)
        self.assertIn("bluebubbles", channel_ids)
        self.assertIn("clickclack", channel_ids)
        self.assertIn("qa-channel", channel_ids)
        self.assertIn("telegram", channel_ids)
        self.assertIn("whatsapp", channel_ids)
        self.assertIn("webchat", channel_ids)
        self.assertIn("https://docs.openclaw.ai/providers", data["model_providers"]["source_urls"])
        self.assertIn("https://docs.openclaw.ai/providers/index", data["model_providers"]["source_urls"])
        self.assertIn("https://docs.openclaw.ai/channels", data["chat_channels"]["source_urls"])
        self.assertEqual(provider_connectors["schema"], "ai22b-openclaw-provider-connector-catalog/v1")
        self.assertGreaterEqual(provider_connectors["summary"]["live_adapter_ready_count"], 35)
        self.assertEqual(provider_doctor["schema"], "ai22b-openclaw-provider-connector-doctor/v1")
        self.assertEqual(provider_doctor["results"][0]["provider_id"], "arcee")
        self.assertFalse(provider_doctor["secret_values_stored"])
        self.assertEqual(connectors["schema"], "ai22b-openclaw-channel-connector-catalog/v1")
        self.assertGreaterEqual(connectors["summary"]["channel_count"], 26)
        self.assertEqual(channel_doctor["schema"], "ai22b-openclaw-channel-connector-doctor/v1")
        self.assertEqual(channel_doctor["results"][0]["channel_id"], "telegram")

    def test_openclaw_parity_audit_covers_current_docs_snapshot(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.openclaw_compat import find_openclaw_channel, find_openclaw_provider
        from ai22b.talent_foundry.openclaw_parity import (
            _channel_ids_from_doc_texts,
            _provider_ids_from_doc_texts,
            audit_openclaw_parity,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "openclaw_parity.json"
            audit = audit_openclaw_parity(output_path=output)
            cli_output = Path(tmp) / "openclaw_parity_cli.json"
            cli_result = cli_main(["audit-openclaw-parity", "--output", str(cli_output), "--fail-on-missing"])
            cli_audit = json.loads(cli_output.read_text(encoding="utf-8"))
            sample_provider_docs = (
                "https://docs.openclaw.ai/providers/openai "
                "https://docs.openclaw.ai/plugins/reference/byteplus "
                "https://docs.openclaw.ai/plugins/reference/google "
                "https://docs.openclaw.ai/providers/qwen-oauth"
            )
            sample_channel_docs = (
                "https://docs.openclaw.ai/channels/telegram "
                "https://docs.openclaw.ai/channels/msteams "
                "https://docs.openclaw.ai/channels/imessage-from-bluebubbles "
                "https://docs.openclaw.ai/web/webchat WebChat"
            )
            live_output = Path(tmp) / "openclaw_parity_live.json"
            with patch(
                "ai22b.talent_foundry.openclaw_parity._fetch_openclaw_doc_text",
                side_effect=[sample_provider_docs + " https://docs.openclaw.ai/providers/mistral", sample_channel_docs, ""],
            ):
                live_audit = audit_openclaw_parity(output_path=live_output, refresh_docs=True)

        self.assertEqual(audit["schema"], "ai22b-openclaw-parity-audit/v1")
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["source_mode"], "checked_snapshot")
        self.assertEqual(audit["coverage"]["providers"]["missing_ids"], [])
        self.assertEqual(audit["coverage"]["channels"]["missing_ids"], [])
        self.assertIn("https://docs.openclaw.ai/providers", audit["source_snapshots"]["providers"]["source_urls"])
        self.assertIn("https://docs.openclaw.ai/llms.txt", audit["source_snapshots"]["channels"]["source_urls"])
        self.assertEqual(find_openclaw_provider("google-gemini-cli")["provider_id"], "google-gemini-cli")
        self.assertEqual(find_openclaw_channel("click-clack")["channel_id"], "clickclack")
        self.assertEqual(find_openclaw_channel("qa_channel")["channel_id"], "qa-channel")
        self.assertEqual(cli_result, 0)
        self.assertEqual(cli_audit["status"], "pass")
        self.assertEqual(live_audit["source_mode"], "live_docs")
        self.assertEqual(live_audit["status"], "pass")
        self.assertIn("byteplus-plan", _provider_ids_from_doc_texts([sample_provider_docs]))
        self.assertIn("google-vertex", _provider_ids_from_doc_texts([sample_provider_docs]))
        self.assertIn("mistral", _provider_ids_from_doc_texts(["https://docs.openclaw.ai/providers/mistral"]))
        self.assertIn("microsoft-teams", _channel_ids_from_doc_texts([sample_channel_docs]))
        self.assertIn("bluebubbles", _channel_ids_from_doc_texts([sample_channel_docs]))

    def test_openclaw_support_matrix_summarizes_onboarding_readiness(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.openclaw_support_matrix import build_openclaw_support_matrix

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "openclaw_support_matrix.json"
            matrix = build_openclaw_support_matrix(output_path=output)
            cli_output = Path(tmp) / "openclaw_support_matrix_cli.json"
            cli_result = cli_main(["build-openclaw-support-matrix", "--output", str(cli_output)])
            cli_matrix = json.loads(cli_output.read_text(encoding="utf-8"))

        provider_by_id = {item["provider_id"]: item for item in matrix["provider_support"]}
        channel_by_id = {item["channel_id"]: item for item in matrix["channel_support"]}

        self.assertEqual(matrix["schema"], "ai22b-openclaw-support-matrix/v1")
        self.assertEqual(matrix["status"], "pass")
        self.assertEqual(matrix["coverage"]["providers"]["parity_missing_count"], 0)
        self.assertEqual(matrix["coverage"]["channels"]["parity_missing_count"], 0)
        self.assertGreaterEqual(matrix["coverage"]["providers"]["paideia_direct_adapter_ready_count"], 35)
        self.assertGreaterEqual(matrix["coverage"]["channels"]["normalized_gateway_ready_count"], 26)
        self.assertTrue(provider_by_id["openrouter"]["openclaw_gateway_route_ready"])
        self.assertEqual(provider_by_id["openrouter"]["support_level"], "paideia_direct_or_openclaw_gateway_ready")
        self.assertEqual(provider_by_id["qwen-oauth"]["support_level"], "openclaw_plugin_or_oauth_required")
        self.assertEqual(channel_by_id["telegram"]["support_level"], "paideia_direct_flow_ready")
        self.assertEqual(channel_by_id["webchat"]["support_level"], "loopback_chat_ready")
        self.assertEqual(channel_by_id["whatsapp"]["support_level"], "normalized_gateway_ready_plugin_delivery_required")
        self.assertIn("run-graham-junior-quickstart", matrix["operator_paths"]["first_sample_agent"])
        self.assertFalse(matrix["claim_boundary"]["secret_values_stored"])
        self.assertEqual(cli_result, 0)
        self.assertEqual(cli_matrix["schema"], "ai22b-openclaw-support-matrix/v1")
        self.assertEqual(cli_matrix["status"], "pass")

    def test_openclaw_selection_doctor_previews_provider_model_and_channel_path(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.openclaw_selection_doctor import (
            build_openclaw_selection_console_preview,
            doctor_openclaw_selection,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "openclaw_selection_doctor.json"
            bridge_setup_dir = Path(tmp) / "selection_bridge_setup"
            doctor = doctor_openclaw_selection(
                llm_service="openclaw-gateway/openrouter/meta-llama/llama-3.1-8b",
                llm_model_path="http://127.0.0.1:18789/v1",
                chat_surface="openclaw-channel-webchat",
                channels=["telegram"],
                output_path=output,
                bridge_setup_dir=bridge_setup_dir,
            )
            cli_output = Path(tmp) / "openclaw_selection_doctor_cli.json"
            cli_summary = Path(tmp) / "OPENCLAW_SELECTION_SUMMARY.md"
            cli_bridge_setup_dir = Path(tmp) / "selection_bridge_setup_cli"
            cli_result = cli_main(
                [
                    "doctor-openclaw-selection",
                    "--llm-service",
                    "openclaw-gateway/openrouter/meta-llama/llama-3.1-8b",
                    "--llm-model-path",
                    "http://127.0.0.1:18789/v1",
                    "--chat-surface",
                    "openclaw-channel-webchat",
                    "--channel",
                    "telegram",
                    "--output",
                    str(cli_output),
                    "--summary-output",
                    str(cli_summary),
                    "--bridge-setup-dir",
                    str(cli_bridge_setup_dir),
                ]
            )
            cli_doctor = json.loads(cli_output.read_text(encoding="utf-8"))
            cli_summary_text = cli_summary.read_text(encoding="utf-8")
            cli_bridge_manifest_exists = (cli_bridge_setup_dir / "openclaw_bridge_setup_kit.json").exists()
            bridge_kit = json.loads(Path(doctor["artifacts"]["bridge_setup_kit"]).read_text(encoding="utf-8"))
            bridge_channel_plan = json.loads(Path(doctor["artifacts"]["channel_plugin_plan"]).read_text(encoding="utf-8"))
            manifest_provider_doctor = doctor_openclaw_selection(
                llm_service="qwen-oauth/qwen3-coder-plus",
                chat_surface="openclaw-channel-webchat",
            )

        channel_support = {item["channel_id"]: item["support"] for item in doctor["openclaw_selection"]["channels"]}
        preview_lines = build_openclaw_selection_console_preview(doctor)
        self.assertEqual(doctor["schema"], "ai22b-openclaw-selection-doctor/v1")
        self.assertEqual(doctor["status"], "ready_for_onboarding")
        self.assertEqual(doctor["openclaw_selection"]["provider_id"], "openrouter")
        self.assertEqual(
            doctor["openclaw_selection"]["provider_support"]["support_level"],
            "paideia_direct_or_openclaw_gateway_ready",
        )
        self.assertEqual(channel_support["webchat"]["support_level"], "loopback_chat_ready")
        self.assertEqual(channel_support["telegram"]["support_level"], "paideia_direct_flow_ready")
        self.assertEqual(doctor["llm_service_health"]["status"], "configured_gateway_manifest_only")
        self.assertFalse(doctor["claim_boundary"]["secret_values_stored"])
        self.assertFalse(doctor["claim_boundary"]["external_network_call_performed"])
        self.assertIn("doctor-openclaw-gateway-llm", doctor["next_commands"]["gateway_llm_after_hire"])
        self.assertIn("build-openclaw-bridge-setup-kit", doctor["next_commands"]["bridge_setup_kit"])
        self.assertEqual(bridge_kit["schema"], "ai22b-openclaw-bridge-setup-kit/v1")
        self.assertEqual(set(bridge_kit["selection"]["channels"]), {"telegram", "webchat"})
        self.assertIn("telegram", {item["channel_id"] for item in bridge_channel_plan["channels"]})
        self.assertIn("OpenClaw selection: ready_for_onboarding", preview_lines)
        self.assertIn("Provider: openrouter (paideia_direct_or_openclaw_gateway_ready)", preview_lines)
        self.assertTrue(any("Bridge setup kit:" in line for line in preview_lines))
        self.assertEqual(cli_result, 0)
        self.assertEqual(cli_doctor["schema"], "ai22b-openclaw-selection-doctor/v1")
        self.assertEqual(cli_doctor["openclaw_selection"]["provider_id"], "openrouter")
        self.assertTrue(cli_bridge_manifest_exists)
        self.assertIn("OpenClaw Selection Summary", cli_summary_text)
        self.assertIn("Bridge Setup Kit", cli_summary_text)
        self.assertIn("paideia_direct_or_openclaw_gateway_ready", cli_summary_text)
        self.assertEqual(manifest_provider_doctor["status"], "needs_openclaw_provider_plugin")
        self.assertEqual(manifest_provider_doctor["selected_llm_service"]["service_id"], "openclaw_gateway_http")
        self.assertEqual(manifest_provider_doctor["selected_llm_service"]["openclaw_model"], "qwen-oauth/qwen3-coder-plus")
        self.assertEqual(
            manifest_provider_doctor["selected_llm_service"]["openclaw_gateway_route_reason"],
            "manifest_only_provider_requires_openclaw_plugin_or_oauth",
        )
        self.assertEqual(manifest_provider_doctor["openclaw_selection"]["provider_id"], "qwen-oauth")

    def test_channel_connector_catalog_covers_every_openclaw_channel(self) -> None:
        from ai22b.talent_foundry.channel_connectors import (
            build_openclaw_channel_connector_catalog,
            doctor_openclaw_channel_connectors,
        )
        from ai22b.talent_foundry.openclaw_compat import openclaw_channel_manifest

        catalog = build_openclaw_channel_connector_catalog()
        doctor = doctor_openclaw_channel_connectors(channels=["telegram", "whatsapp", "matrix", "webchat"])

        manifest_ids = {item["channel_id"] for item in openclaw_channel_manifest()["channels"]}
        catalog_ids = {item["channel_id"] for item in catalog["channels"]}
        by_id = {item["channel_id"]: item for item in catalog["channels"]}
        doctor_by_id = {item["channel_id"]: item for item in doctor["results"]}

        self.assertEqual(catalog["schema"], "ai22b-openclaw-channel-connector-catalog/v1")
        self.assertEqual(manifest_ids, catalog_ids)
        self.assertEqual(catalog["summary"]["generic_normalized_gateway_ready_count"], len(manifest_ids))
        self.assertEqual(by_id["bluebubbles"]["connector_status"], "legacy_openclaw_config_migration_required")
        self.assertEqual(by_id["imessage"]["connector_status"], "openclaw_bundled_imsg_bridge_required")
        self.assertEqual(by_id["clickclack"]["connector_status"], "external_plugin_required")
        self.assertEqual(by_id["qa-channel"]["connector_status"], "openclaw_synthetic_qa_plugin_required")
        self.assertTrue(by_id["telegram"]["direct_raw_ingress_ready"])
        self.assertTrue(by_id["telegram"]["direct_delivery_ready"])
        self.assertEqual(by_id["whatsapp"]["connector_status"], "external_plugin_required_qr_pairing")
        self.assertEqual(by_id["matrix"]["connector_status"], "external_plugin_required")
        self.assertEqual(by_id["signal"]["connector_status"], "local_bridge_required")
        self.assertEqual(by_id["webchat"]["connector_status"], "paideia_loopback_ready")
        self.assertFalse(doctor_by_id["whatsapp"]["ready_for_live_delivery"])
        self.assertTrue(doctor_by_id["webchat"]["ready_for_live_delivery"])
        self.assertFalse(doctor["secret_values_stored"])

    def test_provider_connector_catalog_covers_openclaw_provider_manifest(self) -> None:
        from ai22b.talent_foundry.openclaw_compat import openclaw_provider_manifest
        from ai22b.talent_foundry.provider_connectors import (
            build_openclaw_provider_connector_catalog,
            doctor_openclaw_provider_connectors,
        )

        catalog = build_openclaw_provider_connector_catalog()
        doctor = doctor_openclaw_provider_connectors(providers=["arcee", "minimax", "inferrs", "alibaba"])

        manifest = openclaw_provider_manifest()
        manifest_ids = {item["provider_id"] for item in manifest["providers"]} | set(manifest["manifest_only_providers"])
        catalog_ids = {item["provider_id"] for item in catalog["providers"]}
        by_id = {item["provider_id"]: item for item in catalog["providers"]}
        doctor_by_id = {item["provider_id"]: item for item in doctor["results"]}

        self.assertEqual(catalog["schema"], "ai22b-openclaw-provider-connector-catalog/v1")
        self.assertEqual(manifest_ids, catalog_ids)
        self.assertTrue(by_id["arcee"]["live_adapter_ready"])
        self.assertEqual(by_id["arcee"]["api_protocol"], "openai_chat_completions")
        self.assertTrue(by_id["minimax"]["live_adapter_ready"])
        self.assertEqual(by_id["minimax"]["api_protocol"], "anthropic_messages")
        self.assertTrue(by_id["inferrs"]["local_endpoint"])
        self.assertTrue(doctor_by_id["inferrs"]["ready_for_live_llm"])
        self.assertEqual(by_id["alibaba"]["connector_status"], "provider_plugin_required")
        self.assertFalse(doctor["secret_values_stored"])

        with patch.dict(os.environ, {"OPENCLAW_LIVE_ARCEE_KEY": "test-arcee-key"}, clear=False):
            arcee_ready = doctor_openclaw_provider_connectors(providers=["arcee"])
        self.assertTrue(arcee_ready["results"][0]["ready_for_live_llm"])
        self.assertEqual(arcee_ready["results"][0]["checks"][0]["id"], "env:OPENCLAW_LIVE_ARCEE_KEY")

    def test_openclaw_gateway_llm_doctor_validates_static_config_and_live_probe_contract(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.llm_runtime import build_llm_runtime_config
        from ai22b.talent_foundry.onboarding_choices import resolve_llm_service
        from ai22b.talent_foundry.openclaw_gateway_llm import doctor_openclaw_gateway_llm

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            selected = resolve_llm_service(
                llm_service="openclaw-gateway/openrouter/meta-llama/llama-3.1-8b",
                llm_model_path="http://127.0.0.1:18789",
            )
            employment = {
                "schema": "ai-talent-local-employment/v1",
                "employment_id": "gateway-doctor-test",
                "status": "active",
                "employer": "Boss",
                "agent": {
                    "name": "gateway-junior",
                    "role": "OpenClaw Gateway test agent",
                    "major_goal": "Verify gateway LLM bridge",
                },
                "llm_service": selected,
                "llm_runtime": build_llm_runtime_config(
                    engine=selected["engine"],
                    model_path=selected["selected_model_path"],
                    model=selected["selected_model"],
                    service=selected["service_id"],
                    provider_config=selected,
                ),
                "chat_surface": {"id": "openclaw-channel-webchat"},
                "entrypoints": {},
            }
            employment_path = tmp_path / "employment_record.json"
            employment_path.write_text(json.dumps(employment, ensure_ascii=False, indent=2), encoding="utf-8")
            config_patch = {
                "schema": "ai22b-openclaw-config-patch/v1",
                "openclaw_json_patch": {
                    "gateway": {
                        "http": {
                            "endpoints": {
                                "chatCompletions": {
                                    "enabled": True,
                                }
                            }
                        }
                    }
                },
            }
            config_patch_path = tmp_path / "openclaw_config_patch.json"
            config_patch_path.write_text(json.dumps(config_patch, ensure_ascii=False, indent=2), encoding="utf-8")
            runtime_bundle_path = tmp_path / "openclaw_runtime_bundle.json"
            runtime_bundle_path.write_text(
                json.dumps(
                    {
                        "schema": "ai22b-openclaw-runtime-bundle/v1",
                        "artifacts": {
                            "openclaw_config_patch": "openclaw_config_patch.json",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            static_output = tmp_path / "gateway_doctor_static.json"
            static_report = doctor_openclaw_gateway_llm(
                employment_path,
                runtime_bundle_path=runtime_bundle_path,
                output_path=static_output,
            )
            cli_output = tmp_path / "gateway_doctor_cli.json"
            cli_result = cli_main(
                [
                    "doctor-openclaw-gateway-llm",
                    "--employment-record",
                    str(employment_path),
                    "--config-patch",
                    str(config_patch_path),
                    "--output",
                    str(cli_output),
                ]
            )
            calls: list[dict[str, object]] = []

            def fake_http_json(**kwargs: object) -> dict[str, object]:
                calls.append(dict(kwargs))
                if kwargs["method"] == "GET":
                    return {"data": [{"id": "openclaw/default"}]}
                return {
                    "choices": [{"message": {"content": "Gateway ok"}}],
                    "usage": {"total_tokens": 3},
                }

            live_output = tmp_path / "gateway_doctor_live.json"
            with patch.dict(os.environ, {"OPENCLAW_GATEWAY_TOKEN": "secret-gateway-token"}, clear=False):
                with patch(
                    "ai22b.talent_foundry.openclaw_gateway_llm._http_json",
                    side_effect=fake_http_json,
                ):
                    live_report = doctor_openclaw_gateway_llm(
                        employment_path,
                        runtime_bundle_path=runtime_bundle_path,
                        probe_gateway=True,
                        probe_chat=True,
                        model_override="openrouter/meta-llama/llama-3.1-70b",
                        output_path=live_output,
                    )
            static_output_exists = static_output.exists()
            cli_output_exists = cli_output.exists()
            live_output_exists = live_output.exists()

        live_report_text = json.dumps(live_report, ensure_ascii=False)
        post_call = next(item for item in calls if item["method"] == "POST")

        self.assertEqual(static_report["schema"], "ai22b-openclaw-gateway-llm-doctor/v1")
        self.assertEqual(static_report["status"], "ready_for_gateway_start")
        self.assertEqual(static_report["gateway_contract"]["base_url"], "http://127.0.0.1:18789/v1")
        self.assertTrue(static_output_exists)
        self.assertEqual(cli_result, 0)
        self.assertTrue(cli_output_exists)
        self.assertTrue(live_output_exists)
        self.assertEqual(live_report["status"], "pass")
        self.assertEqual(post_call["payload"]["model"], "openclaw/default")
        self.assertEqual(post_call["headers"]["x-openclaw-model"], "openrouter/meta-llama/llama-3.1-70b")
        self.assertEqual(post_call["headers"]["Authorization"], "Bearer secret-gateway-token")
        self.assertNotIn("secret-gateway-token", live_report_text)

    def test_openclaw_runtime_bundle_exports_config_patch_env_template_and_doctors(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.openclaw_native_handoff import (
            doctor_openclaw_native_handoff,
            prepare_openclaw_native_config,
        )
        from ai22b.talent_foundry.openclaw_runtime_bundle import build_openclaw_runtime_bundle
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Prepare an OpenClaw-style runtime bundle for a hired Paideia talent.",
            talent_name="runtime-junior",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="openclaw-channel-bluebubbles",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "runtime_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="Boss",
                role="OpenClaw runtime setup test agent",
                llm_service="arcee/trinity-large-thinking",
                chat_surface="openclaw-channel-bluebubbles",
                record_name="employment_record_runtime.json",
            )
            existing_config_path = Path(tmp) / ".openclaw" / "openclaw.json"
            existing_config_path.parent.mkdir(parents=True, exist_ok=True)
            existing_config_path.write_text(
                json.dumps(
                    {
                        "agents": {"list": [{"id": "support", "name": "Support"}]},
                        "models": {"default": {"provider": "openai", "apiKey": "do-not-store-this-key"}},
                        "channels": {"telegram": {"botToken": "do-not-store-this-token"}},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            output_dir = Path(tmp) / "runtime_bundle"
            bundle = build_openclaw_runtime_bundle(
                hiring["employment_record"],
                channels=["bluebubbles", "webchat"],
                channel_models=["webchat=openrouter/meta-llama/llama-3.1-8b"],
                bindings=["webchat=paideia-runtime-junior"],
                output_dir=output_dir,
                port=9123,
                existing_openclaw_config_path=existing_config_path,
                config_action="modify",
            )
            manifest_path = Path(bundle["artifacts"]["manifest"])
            manifest_exists = manifest_path.exists()
            config_patch = json.loads(Path(bundle["artifacts"]["openclaw_config_patch"]).read_text(encoding="utf-8"))
            native_handoff = json.loads(Path(bundle["artifacts"]["openclaw_native_handoff"]).read_text(encoding="utf-8"))
            env_template = Path(bundle["artifacts"]["openclaw_env_template"]).read_text(encoding="utf-8")
            provider_doctor = json.loads(Path(bundle["artifacts"]["provider_doctor"]).read_text(encoding="utf-8"))
            channel_doctor = json.loads(Path(bundle["artifacts"]["channel_doctor"]).read_text(encoding="utf-8"))
            config_review = json.loads(
                Path(bundle["artifacts"]["existing_openclaw_config_review"]).read_text(encoding="utf-8")
            )
            merge_preview = Path(bundle["artifacts"]["existing_openclaw_config_merge_preview"]).read_text(encoding="utf-8")
            cli_output_dir = Path(tmp) / "runtime_bundle_cli"
            cli_result = cli_main(
                [
                    "build-openclaw-runtime-bundle",
                    "--employment-record",
                    str(hiring["employment_record"]),
                    "--channel",
                    "webchat",
                    "--channel-model",
                    "webchat=arcee/trinity-large-thinking",
                    "--binding",
                    "webchat=paideia-runtime-junior",
                    "--existing-openclaw-config",
                    str(existing_config_path),
                    "--config-action",
                    "keep",
                    "--output-dir",
                    str(cli_output_dir),
                ]
            )
            cli_manifest_exists = (cli_output_dir / "openclaw_runtime_bundle.json").exists()
            reset_output_dir = Path(tmp) / "runtime_bundle_reset"
            reset_bundle = build_openclaw_runtime_bundle(
                hiring["employment_record"],
                channels=["webchat"],
                output_dir=reset_output_dir,
                existing_openclaw_config_path=existing_config_path,
                config_action="reset",
            )
            reset_plan = Path(reset_bundle["artifacts"]["existing_openclaw_config_reset_plan"]).read_text(encoding="utf-8")
            handoff_doctor_path = Path(tmp) / "native_handoff_doctor.json"
            handoff_doctor = doctor_openclaw_native_handoff(
                Path(bundle["artifacts"]["openclaw_native_handoff"]),
                output_path=handoff_doctor_path,
            )
            cli_handoff_doctor_path = Path(tmp) / "native_handoff_doctor_cli.json"
            cli_handoff_doctor_result = cli_main(
                [
                    "doctor-openclaw-native-handoff",
                    "--handoff",
                    str(bundle["artifacts"]["openclaw_native_handoff"]),
                    "--output",
                    str(cli_handoff_doctor_path),
                ]
            )
            cli_handoff_doctor_exists = cli_handoff_doctor_path.exists()
            native_config_plan_path = Path(tmp) / "native_config_plan.json"
            native_config_plan = prepare_openclaw_native_config(
                Path(bundle["artifacts"]["openclaw_native_handoff"]),
                output_path=native_config_plan_path,
            )
            native_config_copy_report_path = Path(tmp) / "native_config_copy_report.json"
            native_config_copy_path = Path(tmp) / "openclaw_config.merged.local.json"
            native_config_copy = prepare_openclaw_native_config(
                Path(bundle["artifacts"]["openclaw_native_handoff"]),
                output_path=native_config_copy_report_path,
                mode="write-copy",
                merged_output_path=native_config_copy_path,
            )
            apply_target_path = Path(tmp) / ".openclaw" / "openclaw.apply.json"
            apply_target_path.write_text(existing_config_path.read_text(encoding="utf-8"), encoding="utf-8")
            native_config_apply_report_path = Path(tmp) / "native_config_apply_report.json"
            native_config_apply = prepare_openclaw_native_config(
                Path(bundle["artifacts"]["openclaw_native_handoff"]),
                output_path=native_config_apply_report_path,
                mode="apply",
                target_config_path=apply_target_path,
                backup_dir=Path(tmp) / "openclaw_backups",
                confirm_apply=True,
            )
            cli_native_config_plan_path = Path(tmp) / "native_config_plan_cli.json"
            cli_native_config_plan_result = cli_main(
                [
                    "prepare-openclaw-native-config",
                    "--handoff",
                    str(bundle["artifacts"]["openclaw_native_handoff"]),
                    "--output",
                    str(cli_native_config_plan_path),
                ]
            )
            cli_native_config_plan_exists = cli_native_config_plan_path.exists()
            native_config_copy_text = native_config_copy_path.read_text(encoding="utf-8")
            native_config_copy_exists = native_config_copy_path.exists()
            native_config_copy_report_text = json.dumps(native_config_copy, ensure_ascii=False)
            native_config_apply_report_text = json.dumps(native_config_apply, ensure_ascii=False)
            native_config_apply_backup_exists = Path(native_config_apply["target_config"]["backup_path"]).exists()
            applied_config = json.loads(apply_target_path.read_text(encoding="utf-8"))

        self.assertEqual(bundle["schema"], "ai22b-openclaw-runtime-bundle/v1")
        self.assertTrue(manifest_exists)
        self.assertEqual(config_patch["schema"], "ai22b-openclaw-config-patch/v1")
        self.assertEqual(bundle["selection"]["provider_id"], "arcee")
        self.assertEqual(bundle["selection"]["model"], "arcee/trinity-large-thinking")
        self.assertEqual(bundle["selection"]["channels"], ["bluebubbles", "webchat"])
        self.assertEqual(
            bundle["selection"]["channel_model_map"]["webchat"]["*"],
            "openrouter/meta-llama/llama-3.1-8b",
        )
        self.assertEqual(
            config_patch["openclaw_json_patch"]["channels"]["modelByChannel"]["webchat"]["*"],
            "openrouter/meta-llama/llama-3.1-8b",
        )
        self.assertEqual(config_patch["openclaw_json_patch"]["bindings"][0]["match"]["channel"], "webchat")
        self.assertEqual(config_patch["openclaw_json_patch"]["bindings"][0]["agentId"], "paideia-runtime-junior")
        self.assertEqual(config_patch["openclaw_json_patch"]["agents"]["list"][0]["default"], True)
        self.assertEqual(config_patch["openclaw_json_patch"]["agents"]["defaults"]["workspace"], str(hiring["employment_record"].parent))
        self.assertEqual(config_patch["openclaw_json_patch"]["gateway"]["mode"], "local")
        self.assertTrue(
            config_patch["openclaw_json_patch"]["gateway"]["http"]["endpoints"]["chatCompletions"]["enabled"]
        )
        self.assertEqual(native_handoff["schema"], "ai22b-openclaw-native-handoff/v1")
        self.assertEqual(native_handoff["native_openclaw_selection"]["model"], "arcee/trinity-large-thinking")
        self.assertIn("openclaw setup --workspace", native_handoff["operator_commands"]["setup_workspace"])
        self.assertIn("openclaw gateway run", native_handoff["operator_commands"]["run_gateway"])
        self.assertIn("openclaw channels add --channel bluebubbles --help", native_handoff["operator_commands"]["channel_add_help"]["bluebubbles"])
        self.assertFalse(native_handoff["security"]["secret_values_stored"])
        self.assertEqual(handoff_doctor["schema"], "ai22b-openclaw-native-handoff-doctor/v1")
        self.assertIn(handoff_doctor["status"], {"pass", "ready_for_openclaw_install"})
        self.assertTrue(next(item for item in handoff_doctor["static_checks"] if item["id"] == "patch:models.providers")["passed"])
        self.assertTrue(next(item for item in handoff_doctor["static_checks"] if item["id"] == "patch:bindings")["passed"])
        self.assertFalse(handoff_doctor["secret_values_stored"])
        self.assertEqual(cli_handoff_doctor_result, 0)
        self.assertTrue(cli_handoff_doctor_exists)
        self.assertEqual(native_config_plan["schema"], "ai22b-openclaw-native-config-merge/v1")
        self.assertEqual(native_config_plan["status"], "planned")
        self.assertFalse(native_config_plan["merge"]["direct_openclaw_config_write_performed"])
        self.assertIn("arcee", native_config_plan["merge"]["merged_config_redacted_preview"]["models"]["providers"])
        self.assertNotIn("do-not-store-this-key", json.dumps(native_config_plan, ensure_ascii=False))
        self.assertEqual(native_config_copy["status"], "copy_written")
        self.assertTrue(native_config_copy_exists)
        self.assertIn("do-not-store-this-key", native_config_copy_text)
        self.assertNotIn("do-not-store-this-key", native_config_copy_report_text)
        self.assertNotIn("do-not-store-this-token", native_config_copy_report_text)
        self.assertEqual(native_config_apply["status"], "applied")
        self.assertTrue(native_config_apply_backup_exists)
        self.assertTrue(native_config_apply["merge"]["direct_openclaw_config_write_performed"])
        self.assertNotIn("do-not-store-this-key", native_config_apply_report_text)
        self.assertEqual(applied_config["models"]["providers"]["arcee"]["model"], "arcee/trinity-large-thinking")
        self.assertTrue(applied_config["channels"]["webchat"]["enabled"])
        self.assertEqual(cli_native_config_plan_result, 0)
        self.assertTrue(cli_native_config_plan_exists)
        self.assertEqual(bundle["selection"]["config_action"], "modify")
        self.assertEqual(config_review["status"], "modify_preview_written")
        self.assertEqual(
            config_patch["openclaw_json_patch"]["models"]["providers"]["arcee"]["model"],
            "arcee/trinity-large-thinking",
        )
        self.assertIn("bluebubbles", config_patch["openclaw_json_patch"]["channels"])
        self.assertIn("OPENCLAW_LIVE_ARCEE_KEY", env_template)
        self.assertNotIn("BLUEBUBBLES_SERVER_URL", env_template)
        self.assertEqual(
            next(item for item in channel_doctor["results"] if item["channel_id"] == "bluebubbles")["connector_status"],
            "legacy_openclaw_config_migration_required",
        )
        self.assertNotIn("test-arcee-key", env_template)
        self.assertIn("<redacted>", merge_preview)
        self.assertNotIn("do-not-store-this-key", merge_preview)
        self.assertNotIn("do-not-store-this-token", merge_preview)
        self.assertFalse(provider_doctor["secret_values_stored"])
        self.assertFalse(channel_doctor["secret_values_stored"])
        self.assertFalse(config_review["secret_values_stored"])
        self.assertFalse(config_review["destructive_reset_performed"])
        self.assertIn("run-openclaw-channel-gateway-server", bundle["next_commands"]["run_channel_gateway"])
        self.assertIn("doctor-openclaw-channel-flow", bundle["next_commands"]["doctor_channel_flow"])
        self.assertIn("openclaw gateway run", bundle["next_commands"]["openclaw_native_gateway"])
        self.assertEqual(cli_result, 0)
        self.assertTrue(cli_manifest_exists)
        self.assertEqual(reset_bundle["readiness"]["existing_openclaw_config"]["status"], "reset_plan_written")
        self.assertIn("destructive_reset_performed", reset_plan)
        self.assertNotIn("do-not-store-this-key", reset_plan)

    def test_openclaw_bridge_setup_kit_exports_env_plans_and_smoke_tests(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.openclaw_bridge_setup import build_openclaw_bridge_setup_kit
        from ai22b.talent_foundry.openclaw_config_import import import_openclaw_config

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / ".openclaw" / "openclaw.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(
                    {
                        "models": {"default": {"provider": "arcee", "model": "arcee/trinity-large-thinking"}},
                        "channels": {
                            "telegram": {"botToken": "do-not-store-telegram-token"},
                            "whatsapp": {"sessionDir": "do-not-store-whatsapp-session"},
                            "webchat": {"enabled": True},
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            import_dir = Path(tmp) / "import"
            imported = import_openclaw_config(config_path, output_dir=import_dir)
            kit_dir = Path(tmp) / "bridge_kit"
            kit = build_openclaw_bridge_setup_kit(
                output_dir=kit_dir,
                providers=["qwen-oauth"],
                import_manifest_path=Path(imported["artifacts"]["manifest"]),
                bind_host="127.0.0.1",
                port=9888,
            )

            env_template = Path(kit["artifacts"]["env_template"]).read_text(encoding="utf-8")
            provider_plan = json.loads(Path(kit["artifacts"]["provider_plugin_plan"]).read_text(encoding="utf-8"))
            channel_plan = json.loads(Path(kit["artifacts"]["channel_plugin_plan"]).read_text(encoding="utf-8"))
            smoke_tests = json.loads(Path(kit["artifacts"]["smoke_tests"]).read_text(encoding="utf-8"))
            cli_dir = Path(tmp) / "bridge_kit_cli"
            cli_result = cli_main(
                [
                    "build-openclaw-bridge-setup-kit",
                    "--provider",
                    "arcee",
                    "--channel",
                    "telegram",
                    "--output-dir",
                    str(cli_dir),
                ]
            )
            cli_manifest_exists = (cli_dir / "openclaw_bridge_setup_kit.json").exists()

        provider_by_id = {item["provider_id"]: item for item in provider_plan["providers"]}
        channel_by_id = {item["channel_id"]: item for item in channel_plan["channels"]}

        self.assertEqual(kit["schema"], "ai22b-openclaw-bridge-setup-kit/v1")
        self.assertEqual(set(kit["selection"]["providers"]), {"qwen-oauth", "arcee"})
        self.assertEqual(set(kit["selection"]["channels"]), {"telegram", "whatsapp", "webchat"})
        self.assertIn("OPENCLAW_LIVE_ARCEE_KEY", env_template)
        self.assertIn("TELEGRAM_BOT_TOKEN", env_template)
        self.assertIn("WHATSAPP_SESSION_DIR", env_template)
        self.assertNotIn("do-not-store-telegram-token", env_template)
        self.assertNotIn("do-not-store-whatsapp-session", json.dumps(kit, ensure_ascii=False))
        self.assertEqual(provider_by_id["qwen-oauth"]["adapter_path"], "openclaw_provider_plugin_or_oauth_required")
        self.assertEqual(provider_by_id["arcee"]["adapter_path"], "paideia_live_adapter")
        self.assertEqual(channel_by_id["telegram"]["direct_raw_ingress_ready"], True)
        self.assertEqual(channel_by_id["whatsapp"]["connector_status"], "external_plugin_required_qr_pairing")
        self.assertIn("telegram", smoke_tests["payloads"])
        self.assertIn("telegram", smoke_tests["platform_events"])
        self.assertIn("run-openclaw-channel-gateway-server", smoke_tests["commands"]["start_gateway"])
        self.assertIn("translate-openclaw-platform-event", smoke_tests["commands"]["translate_supported_platform_event"])
        self.assertEqual(cli_result, 0)
        self.assertTrue(cli_manifest_exists)

    def test_import_openclaw_config_maps_provider_model_channels_and_redacts_secrets(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.openclaw_config_import import import_openclaw_config
        from ai22b.talent_foundry.openclaw_compat import find_openclaw_channel

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / ".openclaw" / "openclaw.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(
                    {
                        "agents": {
                            "defaults": {"model": {"primary": "anthropic/claude-sonnet-4.5"}},
                            "list": [{"id": "researcher", "name": "Researcher"}],
                        },
                        "models": {
                            "providers": {
                                "anthropic": {"apiKey": "source-anthropic-key"},
                                "openrouter": {"apiKey": "source-openrouter-key"},
                            }
                        },
                        "channels": {
                            "telegram": {"botToken": "source-telegram-token"},
                            "googlechat": {"webhookUrl": "source-google-chat-webhook"},
                            "discord": {"token": "source-discord-token"},
                            "modelByChannel": {
                                "telegram": {"boss-thread": "openrouter/meta-llama/llama-3.1-8b"},
                                "whatsapp": {"family": "arcee/trinity-large-thinking"},
                            },
                            "defaults": {"model": "anthropic/claude-sonnet-4.5"},
                        },
                        "bindings": [
                            {"match": {"channel": "whatsapp", "conversation": "family"}, "agentId": "researcher"},
                            {"match": {"channel": "telegram", "peer": {"kind": "user", "id": "boss"}}, "agentId": "researcher"},
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            output_dir = Path(tmp) / "imported"
            imported = import_openclaw_config(config_path, output_dir=output_dir)
            redacted_snapshot = Path(imported["artifacts"]["redacted_snapshot"]).read_text(encoding="utf-8")
            setup_plan = json.loads(Path(imported["artifacts"]["setup_plan"]).read_text(encoding="utf-8"))
            suggested_answers = json.loads(Path(imported["artifacts"]["suggested_answers"]).read_text(encoding="utf-8"))
            cli_output_dir = Path(tmp) / "imported_cli"
            cli_result = cli_main(
                [
                    "import-openclaw-config",
                    "--config",
                    str(config_path),
                    "--output-dir",
                    str(cli_output_dir),
                ]
            )
            cli_manifest_exists = (cli_output_dir / "paideia_openclaw_config_import.json").exists()

        self.assertEqual(imported["schema"], "ai22b-openclaw-config-import/v1")
        self.assertEqual(imported["status"], "import_ready")
        self.assertEqual(imported["detected"]["primary_provider_id"], "anthropic")
        self.assertEqual(imported["paideia_selection"]["llm_service"], "anthropic/claude-sonnet-4.5")
        self.assertEqual(
            imported["detected"]["channel_ids"],
            ["telegram", "google-chat", "discord", "whatsapp"],
        )
        self.assertEqual(
            imported["detected"]["model_by_channel"]["telegram"]["boss-thread"],
            "openrouter/meta-llama/llama-3.1-8b",
        )
        self.assertEqual(imported["detected"]["bindings"][0]["match"]["conversation"], "family")
        self.assertEqual(imported["paideia_selection"]["bindings"][1]["match"]["peer"]["id"], "boss")
        self.assertIsNotNone(find_openclaw_channel("googlechat"))
        self.assertTrue(imported["paideia_selection"]["provider_supported"])
        self.assertTrue(imported["paideia_selection"]["all_detected_channels_supported"])
        self.assertGreaterEqual(len(imported["detected"]["secret_references"]), 4)
        self.assertIn("<redacted>", redacted_snapshot)
        self.assertNotIn("source-anthropic-key", redacted_snapshot)
        self.assertNotIn("source-telegram-token", redacted_snapshot)
        self.assertEqual(setup_plan["schema"], "ai22b-openclaw-config-import-setup-plan/v1")
        self.assertIn("anthropic", {item["provider_id"] for item in setup_plan["provider_setup"]})
        self.assertIn("whatsapp", {item["channel_id"] for item in setup_plan["channel_setup"]})
        self.assertEqual(
            setup_plan["selection"]["model_by_channel"]["whatsapp"]["family"],
            "arcee/trinity-large-thinking",
        )
        self.assertEqual(suggested_answers["chat_surface"], "openclaw-channel-telegram")
        self.assertEqual(
            suggested_answers["openclaw_model_by_channel"]["telegram"]["boss-thread"],
            "openrouter/meta-llama/llama-3.1-8b",
        )
        self.assertEqual(cli_result, 0)
        self.assertTrue(cli_manifest_exists)

    def test_start_console_prefills_llm_and_chat_from_openclaw_config(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / ".openclaw" / "openclaw.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(
                    {
                        "agents": {"defaults": {"model": {"primary": "arcee/trinity-large-thinking"}}},
                        "models": {"providers": {"arcee": {"apiKey": "source-arcee-key"}}},
                        "channels": {"telegram": {"botToken": "source-telegram-token"}},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            answers_path = Path(tmp) / "answers.json"
            answers_path.write_text(
                json.dumps(
                    {
                        "owner": "Boss",
                        "request": "Raise an OpenClaw-prefilled Paideia securities research talent.",
                        "talent_name": "prefill-junior",
                        "gender": "male",
                        "domain": "securities_research",
                        "role_model_id": "graham_value_investing",
                        "initial_goal": "Run a first imported OpenClaw configuration smoke test.",
                        "cycle_note": "Check that imported provider and chat channel choices are used.",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            output_dir = Path(tmp) / "console_prefill"
            session_path = output_dir / "console_session.json"
            self.assertEqual(
                cli_main(
                    [
                        "start-console",
                        "--answers",
                        str(answers_path),
                        "--openclaw-config",
                        str(config_path),
                        "--output-dir",
                        str(output_dir),
                        "--output",
                        str(session_path),
                    ]
                ),
                0,
            )
            session = json.loads(session_path.read_text(encoding="utf-8"))
            health = json.loads(Path(session["artifacts"]["llm_service_health"]).read_text(encoding="utf-8"))
            import_manifest = json.loads(Path(session["artifacts"]["openclaw_import_manifest"]).read_text(encoding="utf-8"))
            redacted = Path(session["artifacts"]["openclaw_import_redacted_snapshot"]).read_text(encoding="utf-8")

        self.assertEqual(session["prefill"]["schema"], "ai22b-paideia-openclaw-config-prefill/v1")
        self.assertEqual(session["prefill"]["import_status"], "import_ready")
        self.assertEqual(session["answers"]["llm_service"], "arcee/trinity-large-thinking")
        self.assertEqual(session["answers"]["chat_surface"], "openclaw-channel-telegram")
        self.assertEqual(health["openclaw_provider_id"], "arcee")
        self.assertEqual(health["openclaw_model"], "arcee/trinity-large-thinking")
        self.assertEqual(import_manifest["detected"]["channel_ids"], ["telegram"])
        self.assertIn("<redacted>", redacted)
        self.assertNotIn("source-arcee-key", redacted)
        self.assertNotIn("source-telegram-token", redacted)

    def test_openclaw_channel_gateway_routes_message_to_paideia_chat(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.channel_gateway import (
            build_openclaw_gateway_config,
            run_openclaw_channel_message,
        )
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="OpenClaw 채널 메시지를 Paideia 채팅으로 라우팅한다.",
            talent_name="channel-junior",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "channel_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="OpenClaw 채널 테스트 에이전트",
                chat_surface="telegram",
                record_name="employment_record_channel.json",
            )
            config_path = Path(tmp) / "gateway_config.json"
            run_path = Path(tmp) / "telegram_channel_run.json"
            config = build_openclaw_gateway_config(
                hiring["employment_record"],
                channels=["telegram", "webchat"],
                output_path=config_path,
            )
            channel_run = run_openclaw_channel_message(
                hiring["employment_record"],
                channel_id="openclaw-channel-telegram",
                message="안녕, 지금 대화 채널이 연결됐는지 확인해줘",
                sender_id="boss-telegram",
                conversation_id="telegram-test",
                output_path=run_path,
            )
            chat_turn_exists = Path(channel_run["paideia_chat_turn"]["path"]).exists()

        self.assertEqual(config["schema"], "ai22b-openclaw-channel-gateway-config/v1")
        self.assertEqual(config["allowed_channels"][0]["channel_id"], "telegram")
        self.assertEqual(channel_run["schema"], "ai22b-openclaw-channel-run/v1")
        self.assertEqual(channel_run["status"], "reply_ready")
        self.assertEqual(channel_run["inbound"]["channel"]["channel_id"], "telegram")
        self.assertEqual(channel_run["outbound"]["send_policy"], "return_to_gateway_plugin_not_sent_by_paideia_core")
        self.assertFalse(channel_run["security"]["external_send_performed_by_core"])
        self.assertTrue(chat_turn_exists)
        self.assertGreater(len(channel_run["outbound"]["text"]), 5)

    def test_openclaw_channel_flow_doctor_dry_runs_chat_and_delivery_preparation(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.openclaw_channel_flow import doctor_openclaw_channel_flow
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Dry-run OpenClaw channel flow through Paideia chat and delivery preparation.",
            talent_name="channel-flow-junior",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="openclaw-channel-telegram",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "channel_flow_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="Boss",
                role="OpenClaw channel flow test agent",
                chat_surface="telegram",
                record_name="employment_record_channel_flow.json",
            )
            output = Path(tmp) / "channel_flow_doctor.json"
            report = doctor_openclaw_channel_flow(
                hiring["employment_record"],
                channels=["telegram", "webchat"],
                output_path=output,
            )
            cli_output = Path(tmp) / "channel_flow_doctor_cli.json"
            cli_result = cli_main(
                [
                    "doctor-openclaw-channel-flow",
                    "--employment-record",
                    str(hiring["employment_record"]),
                    "--channel",
                    "telegram",
                    "--output",
                    str(cli_output),
                ]
            )
            output_exists = output.exists()
            cli_output_exists = cli_output.exists()
            telegram_delivery = json.loads(Path(report["channels"][0]["delivery_dry_run"]).read_text(encoding="utf-8"))

        self.assertEqual(report["schema"], "ai22b-openclaw-channel-flow-doctor/v1")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["channel_count"], 2)
        self.assertEqual(report["summary"]["reply_ready_count"], 2)
        self.assertTrue(output_exists)
        self.assertEqual(cli_result, 0)
        self.assertTrue(cli_output_exists)
        self.assertEqual(report["channels"][0]["channel_id"], "telegram")
        self.assertTrue(report["channels"][0]["delivery"]["target_valid"])
        self.assertFalse(report["channels"][0]["delivery"]["network_call_performed"])
        self.assertEqual(telegram_delivery["schema"], "ai22b-openclaw-channel-delivery-run/v1")
        self.assertEqual(telegram_delivery["mode"], "dry-run")
        self.assertFalse(report["security"]["secret_values_stored"])

    def test_openclaw_webchat_server_routes_browser_message_locally(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint
        from ai22b.talent_foundry.webchat_server import make_openclaw_webchat_server

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Route a local WebChat message through the Paideia OpenClaw gateway.",
            talent_name="webchat-junior",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="openclaw-channel-webchat",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "webchat_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="Boss",
                role="Local WebChat test agent",
                chat_surface="openclaw-channel-webchat",
                record_name="employment_record_webchat.json",
            )
            output_dir = Path(tmp) / "webchat_runs"
            server = make_openclaw_webchat_server(
                hiring["employment_record"],
                port=0,
                output_dir=output_dir,
            )
            host, port = server.server_address
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(f"http://{host}:{port}/health", timeout=10) as response:
                    health = json.loads(response.read().decode("utf-8"))
                body = json.dumps(
                    {
                        "message": "Can you answer through local WebChat?",
                        "conversation_id": "webchat-test",
                        "sender_id": "boss-browser",
                    }
                ).encode("utf-8")
                request = Request(
                    f"http://{host}:{port}/api/message",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=10) as response:
                    webchat = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            channel_run_exists = Path(webchat["channel_run_path"]).exists()

        self.assertEqual(health["schema"], "ai22b-openclaw-webchat-server/v1")
        self.assertEqual(health["channel_id"], "webchat")
        self.assertEqual(webchat["schema"], "ai22b-openclaw-webchat-response/v1")
        self.assertEqual(webchat["status"], "reply_ready")
        self.assertEqual(webchat["channel_run"]["outbound"]["channel_id"], "webchat")
        self.assertFalse(webchat["security"]["external_send_performed_by_core"])
        self.assertTrue(channel_run_exists)
        self.assertGreater(len(webchat["reply_text"]), 5)

    def test_openclaw_channel_gateway_server_accepts_external_plugin_envelope(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.channel_gateway_server import make_openclaw_channel_gateway_server
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Route a Telegram plugin envelope through the Paideia OpenClaw channel gateway.",
            talent_name="gateway-junior",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="openclaw-channel-telegram",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "gateway_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="Boss",
                role="Local channel gateway test agent",
                chat_surface="openclaw-channel-telegram",
                record_name="employment_record_gateway.json",
            )
            output_dir = Path(tmp) / "gateway_runs"
            server = make_openclaw_channel_gateway_server(
                hiring["employment_record"],
                channels=["telegram", "discord"],
                port=0,
                output_dir=output_dir,
            )
            host, port = server.server_address
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(f"http://{host}:{port}/health", timeout=10) as response:
                    health = json.loads(response.read().decode("utf-8"))
                body = json.dumps(
                    {
                        "schema": "ai22b-openclaw-channel-message/v1",
                        "channel": {"channel_id": "telegram"},
                        "conversation_id": "agent:main:telegram:group:-100123:topic:42",
                        "sender": {"sender_id": "boss-telegram"},
                        "message": {"text": "Answer this through the HTTP channel gateway."},
                        "metadata": {"display_name": "Boss"},
                    }
                ).encode("utf-8")
                request = Request(
                    f"http://{host}:{port}/openclaw/channel-message",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=10) as response:
                    gateway = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            channel_run_exists = Path(gateway["channel_run_path"]).exists()

        self.assertEqual(health["schema"], "ai22b-openclaw-channel-gateway-server/v1")
        self.assertEqual(health["paths"]["message"], "/openclaw/channel-message")
        self.assertEqual(gateway["schema"], "ai22b-openclaw-channel-gateway-response/v1")
        self.assertEqual(gateway["status"], "reply_ready")
        self.assertEqual(gateway["outbound"]["channel_id"], "telegram")
        self.assertEqual(gateway["outbound"]["conversation_id"], "agent:main:telegram:group:-100123:topic:42")
        self.assertEqual(gateway["outbound"]["send_policy"], "return_to_gateway_plugin_not_sent_by_paideia_core")
        self.assertFalse(gateway["security"]["external_send_performed_by_core"])
        self.assertTrue(channel_run_exists)
        self.assertGreater(len(gateway["outbound"]["text"]), 5)

    def test_channel_delivery_dry_run_parses_telegram_discord_and_config(self) -> None:
        from ai22b.talent_foundry.channel_delivery import (
            build_openclaw_channel_delivery_config,
            send_openclaw_channel_outbound,
        )

        telegram_run = {
            "schema": "ai22b-openclaw-channel-run/v1",
            "outbound": {
                "channel_id": "telegram",
                "conversation_id": "agent:main:telegram:group:-1001234567890:topic:42",
                "reply_to_message_id": "openclaw_msg_test",
                "text": "Telegram dry-run reply",
            },
        }
        discord_run = {
            "schema": "ai22b-openclaw-channel-run/v1",
            "outbound": {
                "channel_id": "discord",
                "conversation_id": "agent:main:discord:channel:123456:thread:987654",
                "reply_to_message_id": "openclaw_msg_test",
                "text": "Discord dry-run reply",
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "delivery_config.json"
            telegram_path = Path(tmp) / "telegram_delivery.json"
            config = build_openclaw_channel_delivery_config(output_path=config_path)
            telegram = send_openclaw_channel_outbound(
                telegram_run,
                mode="dry-run",
                output_path=telegram_path,
            )
            discord = send_openclaw_channel_outbound(
                discord_run,
                mode="dry-run",
                delivery_method="bot",
                token_env_var="PAIDEIA_TEST_DISCORD_TOKEN",
            )
            config_exists = config_path.exists()
            telegram_delivery_exists = telegram_path.exists()

        self.assertEqual(config["schema"], "ai22b-openclaw-channel-delivery-config/v1")
        self.assertTrue(config_exists)
        self.assertEqual(telegram["status"], "prepared_not_sent")
        self.assertFalse(telegram["network_call_performed"])
        self.assertEqual(telegram["payload"]["chat_id"], "-1001234567890")
        self.assertEqual(telegram["payload"]["message_thread_id"], 42)
        self.assertTrue(telegram_delivery_exists)
        self.assertEqual(discord["endpoint"], "https://discord.com/api/v10/channels/<channel_id>/messages")
        self.assertEqual(discord["payload"]["content"], "Discord dry-run reply")
        self.assertTrue(discord["target_valid"])
        self.assertFalse(discord["auth"]["token_present"])

    def test_channel_ingress_translates_platform_events_with_allowlist(self) -> None:
        from ai22b.talent_foundry.channel_ingress import (
            build_openclaw_channel_access_config,
            translate_openclaw_platform_event,
        )

        telegram_update = {
            "update_id": 9001,
            "message": {
                "message_id": 77,
                "message_thread_id": 42,
                "from": {"id": 12345, "username": "boss"},
                "chat": {"id": -1001234567890, "type": "supergroup", "title": "Research Room"},
                "text": "Gateway inbound test",
            },
        }
        slack_event = {
            "type": "event_callback",
            "team_id": "T123",
            "event_id": "Ev123",
            "event": {
                "type": "message",
                "channel": "C123456",
                "user": "U123",
                "text": "Slack inbound test",
                "ts": "1717171717.000100",
            },
        }
        access = build_openclaw_channel_access_config(
            channels=["telegram", "slack"],
            allowed_senders=["telegram:12345"],
        )

        telegram = translate_openclaw_platform_event(
            channel_id="telegram",
            payload=telegram_update,
            access_config=access,
        )
        slack = translate_openclaw_platform_event(
            channel_id="slack",
            payload=slack_event,
            access_config=access,
        )

        self.assertEqual(telegram["schema"], "ai22b-openclaw-platform-event-translation/v1")
        self.assertTrue(telegram["access"]["allowed"])
        self.assertEqual(telegram["channel_message"]["channel"]["channel_id"], "telegram")
        self.assertEqual(
            telegram["channel_message"]["conversation_id"],
            "agent:main:telegram:group:-1001234567890:topic:42",
        )
        self.assertEqual(telegram["channel_message"]["sender"]["sender_id"], "telegram:12345")
        self.assertEqual(telegram["channel_message"]["message"]["text"], "Gateway inbound test")
        self.assertFalse(telegram["security"]["raw_external_payload_saved"])
        self.assertFalse(slack["access"]["allowed"])
        self.assertEqual(slack["access"]["decision"], "blocked_sender_or_conversation_not_allowed")
        self.assertEqual(
            slack["channel_message"]["conversation_id"],
            "agent:main:slack:channel:C123456:thread:1717171717.000100",
        )

    def test_channel_gateway_server_routes_allowed_platform_event(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.channel_ingress import build_openclaw_channel_access_config
        from ai22b.talent_foundry.channel_gateway_server import make_openclaw_channel_gateway_server
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Route an allowed Telegram platform event through the Paideia OpenClaw channel gateway.",
            talent_name="ingress-junior",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="openclaw-channel-telegram",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "ingress_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="Boss",
                role="Local platform ingress test agent",
                chat_surface="openclaw-channel-telegram",
                record_name="employment_record_ingress.json",
            )
            access_path = Path(tmp) / "channel_access.json"
            build_openclaw_channel_access_config(
                channels=["telegram"],
                allowed_senders=["telegram:12345"],
                output_path=access_path,
            )
            server = make_openclaw_channel_gateway_server(
                hiring["employment_record"],
                channels=["telegram"],
                access_config_path=access_path,
                port=0,
                output_dir=Path(tmp) / "ingress_runs",
            )
            host, port = server.server_address
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                telegram_update = {
                    "update_id": 9002,
                    "message": {
                        "message_id": 88,
                        "message_thread_id": 42,
                        "from": {"id": 12345, "username": "boss"},
                        "chat": {"id": -1001234567890, "type": "supergroup", "title": "Research Room"},
                        "text": "Allowed platform event should route.",
                    },
                }
                request = Request(
                    f"http://{host}:{port}/openclaw/platform-event/telegram",
                    data=json.dumps(telegram_update).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=10) as response:
                    gateway = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            channel_run_exists = Path(gateway["channel_run_path"]).exists()

        self.assertEqual(gateway["schema"], "ai22b-openclaw-channel-gateway-response/v1")
        self.assertTrue(gateway["platform_event_translation"]["access"]["allowed"])
        self.assertEqual(gateway["outbound"]["channel_id"], "telegram")
        self.assertEqual(
            gateway["outbound"]["conversation_id"],
            "agent:main:telegram:group:-1001234567890:topic:42",
        )
        self.assertTrue(channel_run_exists)

    def test_channel_delivery_live_slack_uses_chat_post_message_without_storing_token(self) -> None:
        from ai22b.talent_foundry.channel_delivery import send_openclaw_channel_outbound

        captured: dict[str, object] = {}
        slack_run = {
            "schema": "ai22b-openclaw-channel-run/v1",
            "outbound": {
                "channel_id": "slack",
                "conversation_id": "agent:main:slack:channel:C123456:thread:1717171717.000100",
                "reply_to_message_id": "openclaw_msg_test",
                "text": "Slack live adapter test",
            },
        }

        def fake_request_json(*, url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
            captured["url"] = url
            captured["payload"] = payload
            captured["headers"] = headers
            return {"ok": True, "channel": payload["channel"], "ts": "1717171718.000200"}

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}), patch(
            "ai22b.talent_foundry.channel_delivery._request_json",
            side_effect=fake_request_json,
        ):
            delivery = send_openclaw_channel_outbound(slack_run, mode="live")

        self.assertEqual(delivery["status"], "sent")
        self.assertTrue(delivery["network_call_performed"])
        self.assertEqual(captured["url"], "https://slack.com/api/chat.postMessage")
        self.assertEqual(captured["payload"]["channel"], "C123456")
        self.assertEqual(captured["payload"]["thread_ts"], "1717171717.000100")
        self.assertEqual(captured["headers"], {"Authorization": "Bearer xoxb-test-token"})
        self.assertEqual(delivery["headers"], {"Authorization": "<redacted>"})
        self.assertTrue(delivery["auth"]["token_present"])
        self.assertFalse(delivery["security"]["secret_values_stored"])

    def test_channel_delivery_live_telegram_uses_send_message_without_storing_token(self) -> None:
        from ai22b.talent_foundry.channel_delivery import send_openclaw_channel_outbound

        captured: dict[str, object] = {}
        telegram_run = {
            "schema": "ai22b-openclaw-channel-run/v1",
            "outbound": {
                "channel_id": "telegram",
                "conversation_id": "agent:main:telegram:group:-1001234567890:topic:42",
                "reply_to_message_id": "openclaw_msg_test",
                "text": "Telegram live adapter test",
            },
        }

        def fake_request_json(*, url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
            captured["url"] = url
            captured["payload"] = payload
            captured["headers"] = headers
            return {"ok": True, "result": {"message_id": 123}}

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "telegram-test-token"}), patch(
            "ai22b.talent_foundry.channel_delivery._request_json",
            side_effect=fake_request_json,
        ):
            delivery = send_openclaw_channel_outbound(telegram_run, mode="live")

        self.assertEqual(delivery["status"], "sent")
        self.assertEqual(captured["url"], "https://api.telegram.org/bottelegram-test-token/sendMessage")
        self.assertEqual(captured["payload"]["chat_id"], "-1001234567890")
        self.assertEqual(captured["payload"]["message_thread_id"], 42)
        self.assertEqual(captured["headers"], {})
        self.assertEqual(delivery["endpoint"], "https://api.telegram.org/bot<redacted>/sendMessage")
        self.assertNotIn("telegram-test-token", json.dumps(delivery, ensure_ascii=False))
        self.assertFalse(delivery["security"]["secret_values_stored"])

    def test_owner_self_extension_blueprint_uses_private_local_track_without_role_model(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="나 자신의 문서와 프로젝트 기억을 바탕으로 개인 업무 확장 에이전트를 키운다.",
            talent_name="boss-extension-junior",
            gender="남자",
            domain="owner_self_extension",
        )

        self.assertEqual(blueprint["track"]["track_id"], "owner_self_extension")
        self.assertIsNone(blueprint["role_model"])
        self.assertEqual(blueprint["local_policy"]["private_data_upload"], "forbidden_without_boss_approval")


if __name__ == "__main__":
    unittest.main()
