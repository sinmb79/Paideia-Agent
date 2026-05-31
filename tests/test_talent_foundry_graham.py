from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
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
        self.assertIn("openrouter_api", llm_service_ids())
        self.assertIn("deepseek_api", llm_service_ids())
        self.assertIn("groq_api", llm_service_ids())
        self.assertIn("gmi_api", llm_service_ids())
        self.assertIn("novita_api", llm_service_ids())
        self.assertIn("huggingface_api", llm_service_ids())
        self.assertIn("kilocode_gateway", llm_service_ids())
        self.assertIn("ollama_cloud", llm_service_ids())
        self.assertIn("synthetic_api", llm_service_ids())
        self.assertIn("openclaw-channel-telegram", chat_surface_ids())
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

        self.assertEqual(session["wizard"]["schema"], "ai22b-paideia-openclaw-style-onboarding/v1")
        self.assertEqual(config["schema"], "ai22b-paideia-openclaw-style-config/v1")
        self.assertEqual(config["gateway"]["mode"], "local_loopback")
        self.assertEqual(config["channels"]["external_channels"], "disabled_until_explicit_configuration")
        self.assertEqual(identity_payload["schema"], "ai-talent-agent-id-card-payload/v1")
        self.assertFalse(identity_payload["network_action_performed"])
        self.assertEqual(rollouts["schema"], "ai-talent-simulation-rollouts/v1")
        self.assertGreaterEqual(rollouts["summary"]["episode_count"], 4)
        self.assertEqual(rollout_execution["schema"], "ai-talent-simulation-rollout-execution/v1")
        self.assertGreaterEqual(rollout_execution["summary"]["promoted_count"], 3)
        self.assertGreaterEqual(rollout_execution["summary"]["quarantined_count"], 1)
        self.assertEqual(llm_health["schema"], "ai22b-paideia-llm-service-health/v1")
        self.assertFalse(llm_health["network_probe_performed"])

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
        self.assertIn("volcengine", all_provider_ids)
        self.assertIn("volcengine-plan", all_provider_ids)
        self.assertIn("byteplus-plan", all_provider_ids)
        self.assertIn("qwen-oauth", all_provider_ids)
        self.assertIn("pixverse", all_provider_ids)
        self.assertIn("ds4", all_provider_ids)
        self.assertIn("discord", channel_ids)
        self.assertIn("telegram", channel_ids)
        self.assertIn("whatsapp", channel_ids)
        self.assertIn("webchat", channel_ids)
        self.assertIn("https://docs.openclaw.ai/providers/index", data["model_providers"]["source_urls"])
        self.assertIn("https://docs.openclaw.ai/channels", data["chat_channels"]["source_urls"])

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
