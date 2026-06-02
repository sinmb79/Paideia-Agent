from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


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

    def test_developmental_ecology_and_life_trace_are_reviewable_records(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.developmental_ecology import build_developmental_ecology
        from ai22b.talent_foundry.growth_profile import build_growth_profile
        from ai22b.talent_foundry.life_trace import build_life_trace

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Raise a securities research AI talent through Graham's learning process.",
            talent_name="graham-junior",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
        )
        ecology = build_developmental_ecology(blueprint)
        trace = build_life_trace(blueprint, ecology, density="monthly")
        growth_profile = build_growth_profile(blueprint, ecology, trace)

        self.assertEqual(ecology["schema"], "ai22b-paideia-developmental-ecology/v1")
        self.assertEqual(ecology["seed"]["role_model_birth_seed_use"], "symbolic_initial_condition_only")
        self.assertIn("personality_injection", ecology["seed"]["forbidden_use"])
        self.assertEqual(trace["manifest"]["schema"], "ai22b-paideia-life-trace/v1")
        self.assertEqual(trace["manifest"]["event_count"], 252)
        self.assertEqual(trace["events"][0]["schema"], "ai22b-paideia-life-trace-event/v1")
        self.assertEqual(trace["events"][0]["safety"]["private_reasoning_trace"], "not_stored")
        self.assertEqual(growth_profile["schema"], "ai22b-paideia-growth-profile/v1")
        self.assertIn("relationship_memory", growth_profile)
        self.assertIn("emotional_memory", growth_profile)
        self.assertEqual(growth_profile["policy"]["personality_injection"], "forbidden")
        with self.assertRaises(ValueError):
            build_life_trace(blueprint, ecology, density="hourly")

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
            substrate = json.loads(artifacts["memory_substrate"].read_text(encoding="utf-8"))
            life_trace_lines = artifacts["life_trace"].read_text(encoding="utf-8").splitlines()

            self.assertTrue(artifacts["role_model_profile"].exists())
            self.assertTrue(artifacts["saju_narrative_seed"].exists())
            self.assertTrue(artifacts["curriculum_manifest"].exists())
            self.assertTrue(artifacts["reasoning_kibo"].exists())
            self.assertTrue(artifacts["developmental_ecology"].exists())
            self.assertTrue(artifacts["life_trace"].exists())
            self.assertTrue(artifacts["growth_profile"].exists())
            self.assertTrue(artifacts["employment_record"].exists())
            self.assertEqual(run["status"], "employment_ready")
            self.assertTrue(run["verification"]["developmental_ecology_created"])
            self.assertTrue(run["verification"]["life_trace_created"])
            self.assertTrue(run["verification"]["growth_profile_created"])
            self.assertEqual(len(life_trace_lines), 253)
            self.assertGreaterEqual(len(transcript["results"]), 9)
            self.assertTrue(transcript["graduation_ready"])
            self.assertTrue(transcript["v2_assessment"]["passed"])
            self.assertEqual(
                manifest["identity_source"]["role_model_inspiration"]["role_model_id"],
                "graham_value_investing",
            )
            self.assertEqual(
                manifest["identity_source"]["developmental_ecology"]["schema"],
                "ai22b-paideia-developmental-ecology/v1",
            )
            self.assertEqual(manifest["identity_source"]["life_trace"]["event_count"], 252)
            self.assertEqual(
                manifest["identity_source"]["growth_profile"]["schema"],
                "ai22b-paideia-growth-profile/v1",
            )
            self.assertEqual(substrate["source_counts"]["life_trace_events"], 252)
            self.assertGreaterEqual(substrate["source_counts"]["developmental_ecology_layers"], 7)
            self.assertGreaterEqual(substrate["source_counts"]["growth_profile_nodes"], 5)
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
            ecology_output = Path(tmp) / "ecology.json"
            trace_output = Path(tmp) / "life_trace.jsonl"
            growth_output = Path(tmp) / "growth_profile.json"
            self.assertEqual(
                cli_main(
                    [
                        "build-developmental-ecology",
                        "--blueprint",
                        str(output),
                        "--output",
                        str(ecology_output),
                    ]
                ),
                0,
            )
            self.assertEqual(
                cli_main(
                    [
                        "build-life-trace",
                        "--blueprint",
                        str(output),
                        "--ecology",
                        str(ecology_output),
                        "--density",
                        "monthly",
                        "--output",
                        str(trace_output),
                    ]
                ),
                0,
            )
            self.assertTrue(ecology_output.exists())
            self.assertEqual(len(trace_output.read_text(encoding="utf-8").splitlines()), 253)
            self.assertEqual(
                cli_main(
                    [
                        "build-growth-profile",
                        "--blueprint",
                        str(output),
                        "--ecology",
                        str(ecology_output),
                        "--life-trace",
                        str(trace_output),
                        "--output",
                        str(growth_output),
                    ]
                ),
                0,
            )
            self.assertTrue(growth_output.exists())
            self.assertEqual(
                json.loads(growth_output.read_text(encoding="utf-8"))["schema"],
                "ai22b-paideia-growth-profile/v1",
            )

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
        from ai22b.talent_foundry.onboarding_choices import llm_service_ids

        self.assertIn("ollama_local", llm_service_ids())
        self.assertIn("openrouter_api", llm_service_ids())
        questions = questions_with_choices()
        role_question = next(item for item in questions if item["id"] == "role_model_id")
        llm_question = next(item for item in questions if item["id"] == "llm_service")
        self.assertIn("hopper_software_tooling", {item["id"] for item in role_question["choices"]})
        self.assertIn("anthropic_claude_api", {item["id"] for item in llm_question["choices"]})

        config = build_llm_runtime_config(engine="openrouter_api", model="user-selected-model")
        result = invoke_llm_application_engine(
            config,
            manifest={"agent": {"name": "sample", "major_goal": "test"}},
            task="test adapter manifest",
        )

        self.assertEqual(config["network_access"], "external_api_selected_data_minimized")
        self.assertEqual(result["status"], "adapter_manifest_ready")

    def test_openclaw_style_onboarding_questions_are_step_based(self) -> None:
        from ai22b.talent_foundry.console import WIZARD_STEPS, questions_with_choices

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

        self.assertEqual(session["wizard"]["schema"], "ai22b-paideia-openclaw-style-onboarding/v1")
        self.assertEqual(config["schema"], "ai22b-paideia-openclaw-style-config/v1")
        self.assertEqual(config["gateway"]["mode"], "local_loopback")
        self.assertEqual(config["channels"]["external_channels"], "disabled_until_explicit_configuration")
        self.assertEqual(identity_payload["schema"], "ai-talent-agent-id-card-payload/v1")
        self.assertFalse(identity_payload["network_action_performed"])
        self.assertEqual(rollouts["schema"], "ai-talent-simulation-rollouts/v1")
        self.assertGreaterEqual(rollouts["summary"]["episode_count"], 4)

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
