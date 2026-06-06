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
        from ai22b.talent_foundry.llm_onboarding import build_llm_onboarding_checklist
        from ai22b.talent_foundry.llm_runtime import build_llm_runtime_config, invoke_llm_application_engine
        from ai22b.talent_foundry.onboarding_choices import LLM_SERVICE_CATALOG, llm_service_ids, resolve_llm_service

        self.assertIn("ollama_local", llm_service_ids())
        self.assertIn("openrouter_api", llm_service_ids())
        openrouter_service = next(item for item in LLM_SERVICE_CATALOG if item["id"] == "openrouter_api")
        resolved_openrouter = resolve_llm_service(llm_service="openrouter_api", llm_model="openai/gpt-test")
        questions = questions_with_choices()
        role_question = next(item for item in questions if item["id"] == "role_model_id")
        llm_question = next(item for item in questions if item["id"] == "llm_service")
        self.assertIn("hopper_software_tooling", {item["id"] for item in role_question["choices"]})
        self.assertIn("anthropic_claude_api", {item["id"] for item in llm_question["choices"]})
        self.assertEqual(openrouter_service["runtime_readiness"], "live_client_ready_when_configured")
        self.assertFalse(openrouter_service["doctor"]["live_check_default"])
        self.assertIn("--live-check", openrouter_service["doctor"]["live_check_command"])
        self.assertFalse(openrouter_service["doctor"]["secret_values_exported"])
        self.assertEqual(openrouter_service["data_transfer_policy"]["network_access"], "external_api_selected_data_minimized")
        self.assertTrue(openrouter_service["live_check_policy"]["requires_explicit_flag"])
        self.assertIn("cost", openrouter_service["cost_warning"].casefold())
        self.assertEqual(resolved_openrouter["doctor"]["required_before_live"], True)
        self.assertEqual(resolved_openrouter["selected_model"], "openai/gpt-test")
        checklist = build_llm_onboarding_checklist(
            llm_service="openrouter_api",
            llm_model="openai/gpt-test",
        )
        commands = {item["id"]: item for item in checklist["command_plan"]}
        self.assertEqual(checklist["schema"], "paideia-llm-onboarding-checklist/v1")
        self.assertEqual(checklist["status"], "needs_configuration_before_live")
        self.assertFalse(checklist["public_safe"]["network_call_performed"])
        self.assertTrue(commands["application_engine_live_smoke"]["network_call"])
        self.assertTrue(commands["agent_runtime_live_smoke"]["required_before_agent_work"])
        self.assertIn("--live-check", commands["agent_runtime_live_smoke"]["command"])
        self.assertIn("OPENROUTER_API_KEY", json.dumps(checklist["readiness"], ensure_ascii=False))

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
        self.assertIn("owner_materials_consent", by_id)
        self.assertIn("copyright_attestation", by_id)

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
            identity_envelope = json.loads(Path(session["artifacts"]["agent_identity_envelope"]).read_text(encoding="utf-8"))
            rollouts = json.loads(Path(session["artifacts"]["simulation_rollouts"]).read_text(encoding="utf-8"))
            rollout_evaluation = json.loads(Path(session["artifacts"]["simulation_rollout_evaluation"]).read_text(encoding="utf-8"))

        self.assertEqual(session["wizard"]["schema"], "ai22b-paideia-openclaw-style-onboarding/v1")
        self.assertEqual(config["schema"], "ai22b-paideia-openclaw-style-config/v1")
        self.assertEqual(config["gateway"]["mode"], "local_loopback")
        self.assertEqual(config["channels"]["external_channels"], "disabled_until_explicit_configuration")
        self.assertEqual(identity_payload["schema"], "ai-talent-agent-id-card-payload/v1")
        self.assertFalse(identity_payload["network_action_performed"])
        self.assertEqual(identity_envelope["version"], "ail.v1")
        self.assertIsNone(identity_envelope["ail_id"])
        self.assertFalse(identity_envelope["verification"]["signed"])
        self.assertEqual(
            identity_envelope["extensions"]["agent_warrent"]["repo_url"],
            "https://github.com/sinmb79/Agent_warrent",
        )
        self.assertEqual(rollouts["schema"], "ai-talent-simulation-rollouts/v1")
        self.assertGreaterEqual(rollouts["summary"]["episode_count"], 4)
        self.assertEqual(rollout_evaluation["schema"], "ai-talent-simulation-rollout-evaluation/v1")
        self.assertEqual(rollout_evaluation["summary"]["episode_count"], rollouts["summary"]["episode_count"])
        self.assertFalse(rollout_evaluation["memory_update_gate"]["automatic_promotion_performed"])
        self.assertTrue(rollout_evaluation["memory_update_gate"]["boss_review_required"])
        self.assertFalse(rollout_evaluation["memory_update_gate"]["separate_consciousness_created"])

    def test_simulation_rollout_evaluation_cli_ranks_and_quarantines_episodes(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.simulation_rollouts import build_simulation_rollouts
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Raise a securities research agent and compare rollout episodes.",
            talent_name="rollout-eval-test",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
        )
        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "rollout_eval")
            employment_record = Path(run["artifacts"]["employment_record"])
            rollouts_path = Path(tmp) / "simulation_rollouts.json"
            results_path = Path(tmp) / "simulation_rollout_results.json"
            output_path = Path(tmp) / "simulation_rollout_evaluation.json"
            promotion_path = Path(tmp) / "simulation_rollout_learning_update.json"
            rollouts = build_simulation_rollouts(
                employment_record,
                objective="Compare parallel research recovery strategies.",
                output_path=rollouts_path,
            )
            episode_results = [
                {
                    "episode_id": rollouts["episodes"][0]["episode_id"],
                    "score": 96,
                    "review_summary": "Best evidence reconciliation under stress.",
                },
                {
                    "episode_id": rollouts["episodes"][1]["episode_id"],
                    "score": 64,
                    "review_summary": "Failed to ask a clarifying question before acting.",
                },
            ]
            results_path.write_text(
                json.dumps(
                    {
                        "schema": "ai-talent-simulation-rollout-results/v1",
                        "episode_results": episode_results,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            exit_code = cli_main(
                [
                    "evaluate-simulation-rollouts",
                    "--rollouts",
                    str(rollouts_path),
                    "--results",
                    str(results_path),
                    "--output",
                    str(output_path),
                ]
            )
            promote_code = cli_main(
                [
                    "promote-simulation-rollout-winner",
                    "--employment-record",
                    str(employment_record),
                    "--evaluation",
                    str(output_path),
                    "--score",
                    "94",
                    "--reviewed-by",
                    "Boss",
                    "--status",
                    "verified",
                    "--output",
                    str(promotion_path),
                ]
            )
            evaluation = json.loads(output_path.read_text(encoding="utf-8"))
            promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
            ledger = json.loads((employment_record.parent / "learning_ledger.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(promote_code, 0)
        self.assertEqual(evaluation["schema"], "ai-talent-simulation-rollout-evaluation/v1")
        self.assertEqual(evaluation["winner"]["episode_id"], episode_results[0]["episode_id"])
        self.assertEqual(evaluation["winner"]["score"], 96)
        self.assertIn(episode_results[0]["episode_id"], evaluation["memory_update_gate"]["eligible_episode_ids"])
        self.assertIn(episode_results[1]["episode_id"], evaluation["memory_update_gate"]["quarantined_episode_ids"])
        self.assertFalse(evaluation["memory_update_gate"]["automatic_promotion_performed"])
        self.assertFalse(evaluation["winner"]["private_reasoning_trace_stored"])
        self.assertEqual(promotion["schema"], "ai-talent-post-hire-learning-update/v1")
        self.assertEqual(promotion["source"], "simulation_rollout_winner")
        self.assertEqual(promotion["decision"], "promoted")
        self.assertEqual(
            promotion["reviewed_rollout_event"]["selected_episode"]["episode_id"],
            episode_results[0]["episode_id"],
        )
        self.assertFalse(promotion["reviewed_rollout_event"]["rollout_gate"]["automatic_promotion_performed"])
        self.assertEqual(promotion["reasoning_ledger_candidate"]["schema"], "paideia-reasoning-ledger-candidate/v1")
        self.assertFalse(promotion["reasoning_ledger_candidate"]["policy"]["full_rollout_replay_stored"])
        self.assertFalse(promotion["reasoning_ledger_candidate"]["policy"]["separate_consciousness_created"])
        self.assertIn("parallel_rollout_review", promotion["latest_promoted_skills"])
        self.assertTrue(ledger["reasoning_ledger_candidates"])
        self.assertNotIn("Failed to ask a clarifying question before acting", json.dumps(promotion, ensure_ascii=False))

    def test_guided_console_owner_self_extension_writes_metadata_only_intake(self) -> None:
        from ai22b.talent_foundry.console import run_console_session

        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "owner_materials"
            source_dir.mkdir()
            (source_dir / "client-roadmap.md").write_text("private roadmap detail", encoding="utf-8")
            output_dir = Path(tmp) / "owner_extension_console"
            session = run_console_session(
                answers={
                    "owner": "보스",
                    "request": "내 문서와 프로젝트 습관을 바탕으로 업무 확장 에이전트를 키운다.",
                    "talent_source": "owner_self_extension",
                    "private_curriculum_dir": str(source_dir),
                    "owner_materials_consent": "yes",
                    "copyright_attestation": "owner_provided_or_authorized_for_local_use",
                    "talent_name": "boss-extension-junior",
                    "gender": "남자",
                    "agent_id_card_mode": "skip",
                    "simulation_rollouts_enabled": "no",
                },
                output_dir=output_dir,
                output_path=output_dir / "console_session.json",
            )
            intake = json.loads(Path(session["artifacts"]["owner_self_extension_intake"]).read_text(encoding="utf-8"))
            raw_intake = Path(session["artifacts"]["owner_self_extension_intake"]).read_text(encoding="utf-8")
            config = json.loads(Path(session["artifacts"]["paideia_onboarding_config"]).read_text(encoding="utf-8"))

        self.assertEqual(session["onboarding_summary"]["track"]["track_id"], "owner_self_extension")
        self.assertTrue(intake["valid"])
        self.assertFalse(intake["content_ingestion_performed"])
        self.assertEqual(intake["scan_summary"]["scanned_file_count"], 1)
        self.assertIn("owner_self_extension_intake", session["post_hire_extensions"])
        self.assertEqual(config["education_path"]["talent_source"], "owner_self_extension")
        self.assertEqual(config["education_path"]["owner_materials_consent"], "yes")
        self.assertNotIn("client-roadmap", raw_intake)
        self.assertNotIn("private roadmap detail", raw_intake)
        self.assertNotIn(str(source_dir), raw_intake)

    def test_agent_warrent_identity_envelope_cli_export(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Raise a local securities research AI talent and export an Agent_warrent identity envelope.",
            talent_name="agent-warrent-test",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "agent_warrent")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            payload_output = Path(tmp) / "agent_id_card_payload.json"
            output = Path(tmp) / "agent_identity_envelope.json"
            verify_output = Path(tmp) / "agent_identity_verification.json"
            registration_result_output = Path(tmp) / "agent_id_card_registration_result.json"
            registration_receipt_output = Path(tmp) / "agent_identity_registration_receipt.json"
            registered_envelope_output = Path(tmp) / "agent_identity_envelope.registered.json"
            payload_exit = cli_main(
                [
                    "export-agent-id-card-payload",
                    "--installed-manifest",
                    str(artifacts["installed_agent_manifest"]),
                    "--employment-record",
                    str(artifacts["employment_record"]),
                    "--output",
                    str(payload_output),
                ]
            )
            exit_code = cli_main(
                [
                    "export-agent-identity-envelope",
                    "--installed-manifest",
                    str(artifacts["installed_agent_manifest"]),
                    "--employment-record",
                    str(artifacts["employment_record"]),
                    "--surface",
                    "test_cli",
                    "--task-ref",
                    "test-agent-warrent-export",
                    "--output",
                    str(output),
                ]
            )
            verify_exit = cli_main(
                [
                    "verify-agent-id-card",
                    "--payload",
                    str(payload_output),
                    "--envelope",
                    str(output),
                    "--output",
                    str(verify_output),
                ]
            )
            registration_result_output.write_text(
                json.dumps(
                    {
                        "ail_id": "ail_test_agent_warrent_001",
                        "credential": "eyJlocal-test-credential.signature",
                        "verification": {
                            "signed": True,
                            "strength": "agentidcard_owner_registered",
                            "attestation_ref": "agentidcard-test-attestation",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            import_exit = cli_main(
                [
                    "import-agent-id-card-registration",
                    "--envelope",
                    str(output),
                    "--registration-result",
                    str(registration_result_output),
                    "--output",
                    str(registration_receipt_output),
                    "--updated-envelope",
                    str(registered_envelope_output),
                ]
            )
            payload = json.loads(payload_output.read_text(encoding="utf-8"))
            envelope = json.loads(output.read_text(encoding="utf-8"))
            verification = json.loads(verify_output.read_text(encoding="utf-8"))
            registration_receipt = json.loads(registration_receipt_output.read_text(encoding="utf-8"))
            registered_envelope = json.loads(registered_envelope_output.read_text(encoding="utf-8"))

        self.assertEqual(payload_exit, 0)
        self.assertEqual(exit_code, 0)
        self.assertEqual(verify_exit, 0)
        self.assertEqual(import_exit, 0)
        self.assertEqual(payload["schema"], "ai-talent-agent-id-card-payload/v1")
        self.assertEqual(envelope["version"], "ail.v1")
        self.assertEqual(envelope["agent"]["display_name"], "agent-warrent-test")
        self.assertEqual(envelope["delegation"]["task_ref"], "test-agent-warrent-export")
        self.assertEqual(envelope["runtime"]["surface"], "test_cli")
        self.assertEqual(envelope["verification"]["strength"], "local_runtime_asserted")
        self.assertFalse(envelope["extensions"]["paideia"]["privacy"]["network_action_performed"])
        self.assertNotIn("C:\\Users\\", json.dumps(envelope, ensure_ascii=False))
        self.assertEqual(verification["schema"], "paideia-agent-id-card-verification/v1")
        self.assertTrue(verification["valid"])
        self.assertEqual(verification["status"], "passed")
        self.assertFalse(verification["network_action_performed"])
        self.assertEqual(verification["external_registration"], "not_performed_manual_owner_action_only")
        self.assertFalse(verification["validations"]["payload"]["privacy"]["credential_like_values_exported"])
        self.assertFalse(verification["validations"]["envelope"]["privacy"]["local_absolute_paths_exported"])
        self.assertEqual(registration_receipt["schema"], "paideia-agent-id-card-registration-import/v1")
        self.assertTrue(registration_receipt["valid"])
        self.assertEqual(registration_receipt["status"], "imported")
        self.assertFalse(registration_receipt["network_action_performed"])
        self.assertTrue(registration_receipt["registration_result"]["credential_token_present"])
        self.assertFalse(registration_receipt["registration_result"]["credential_token_exported"])
        self.assertIn("credential_fingerprint_sha256", registration_receipt["registration_result"])
        self.assertEqual(registered_envelope["ail_id"], "ail_test_agent_warrent_001")
        self.assertIsNone(registered_envelope["credential"])
        self.assertEqual(registered_envelope["extensions"]["agent_warrent"]["registration_state"], "owner_imported_registered")
        self.assertEqual(registered_envelope["extensions"]["agent_warrent"]["external_registration"], "owner_completed_outside_paideia")
        self.assertTrue(registered_envelope["verification"]["signed"])
        self.assertTrue(registration_receipt["updated_envelope_validation"]["registered"])
        self.assertNotIn("eyJlocal-test-credential.signature", json.dumps(registration_receipt, ensure_ascii=False))
        self.assertNotIn("eyJlocal-test-credential.signature", json.dumps(registered_envelope, ensure_ascii=False))

    def test_agent_identity_verifier_blocks_private_contact_and_local_paths(self) -> None:
        from ai22b.talent_foundry.agent_identity_card import (
            AGENT_WARRENT_REPO_URL,
            validate_agent_id_card_payload,
            validate_agent_identity_layer_envelope,
        )

        payload_validation = validate_agent_id_card_payload(
            {
                "schema": "ai-talent-agent-id-card-payload/v1",
                "status": "payload_ready_not_registered",
                "network_action_performed": False,
                "owner_review_required": True,
                "credential_subject": {
                    "display_name": "privacy-test-agent",
                    "role": "research agent",
                    "owner_org": "boss@example.com",
                    "scope": {"runtime": "local_first_paideia_agent"},
                },
                "local_lineage": {"install_id": "privacy_test_agent"},
                "agent_identity_layer": {
                    "compatible_envelope_version": "ail.v1",
                    "provider_repo": AGENT_WARRENT_REPO_URL,
                    "external_registration": "manual_owner_action_only",
                },
            }
        )
        envelope_validation = validate_agent_identity_layer_envelope(
            {
                "version": "ail.v1",
                "agent": {"id": "paideia_privacy_test", "display_name": "privacy-test-agent", "role": "research agent"},
                "delegation": {"mode": "direct"},
                "scope": {"approval_policy": {"external_registration": "human_required"}},
                "verification": {"strength": "local_runtime_asserted", "signed": False},
                "runtime": {"run_id": "run_privacy_test", "cwd": "D:\\private-agent-run"},
                "extensions": {
                    "agent_warrent": {
                        "repo_url": AGENT_WARRENT_REPO_URL,
                        "registration_state": "local_unregistered",
                        "external_registration": "manual_owner_action_only",
                    }
                },
            }
        )

        self.assertFalse(payload_validation["valid"])
        self.assertTrue(payload_validation["privacy"]["raw_owner_email_exported"])
        self.assertFalse(envelope_validation["valid"])
        self.assertTrue(envelope_validation["privacy"]["local_absolute_paths_exported"])

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

    def test_owner_self_extension_intake_is_metadata_only_and_requires_consent(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.owner_self_extension import build_owner_self_extension_intake

        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "owner_materials"
            source_dir.mkdir()
            secret_file = source_dir / "my-secret-client-plan.txt"
            secret_file.write_text("private project detail that must not be exported", encoding="utf-8")
            output_path = Path(tmp) / "owner_self_extension_intake.json"
            blocked_output = Path(tmp) / "owner_self_extension_intake.blocked.json"

            intake = build_owner_self_extension_intake(
                source_dir=source_dir,
                owner="보스",
                owner_consent=True,
                copyright_attestation="owner_provided_or_authorized_for_local_use",
                repo_root=Path.cwd(),
                output_path=output_path,
            )
            blocked_exit = cli_main(
                [
                    "prepare-owner-self-extension-intake",
                    "--source-dir",
                    str(source_dir),
                    "--owner",
                    "보스",
                    "--output",
                    str(blocked_output),
                ]
            )
            blocked = json.loads(blocked_output.read_text(encoding="utf-8"))
            raw = output_path.read_text(encoding="utf-8")

        self.assertTrue(intake["valid"])
        self.assertEqual(intake["schema"], "paideia-owner-self-extension-intake/v1")
        self.assertFalse(intake["content_ingestion_performed"])
        self.assertFalse(intake["privacy"]["raw_absolute_paths_exported"])
        self.assertFalse(intake["privacy"]["raw_filenames_exported"])
        self.assertEqual(intake["scan_summary"]["scanned_file_count"], 1)
        self.assertEqual(intake["files"][0]["extension"], ".txt")
        self.assertFalse(intake["files"][0]["content_read"])
        self.assertNotIn("my-secret-client-plan", raw)
        self.assertNotIn("private project detail", raw)
        self.assertNotIn(str(source_dir), raw)
        self.assertEqual(blocked_exit, 2)
        self.assertFalse(blocked["valid"])
        self.assertIn("owner_consent_missing", {item["id"] for item in blocked["issues"]})


if __name__ == "__main__":
    unittest.main()
