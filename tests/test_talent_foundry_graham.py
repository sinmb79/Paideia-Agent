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


if __name__ == "__main__":
    unittest.main()
