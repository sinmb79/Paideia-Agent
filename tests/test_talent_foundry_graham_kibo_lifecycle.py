from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class GrahamKiboLifecycleTests(unittest.TestCase):
    def test_saju_is_initial_condition_not_personality_injection(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Build Graham process replication talent",
            talent_name="ShinYong",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
        )

        self.assertEqual(
            blueprint["role_model_birth_seed"]["simulation_use"]["purpose"],
            "초기 시뮬레이션 조건을 고르는 보조 seed입니다. 성격, 투자관, 인생관을 미리 주입하지 않습니다.",
        )
        self.assertIn("personality_trait_injection", blueprint["role_model_birth_seed"]["simulation_use"]["forbidden"])
        self.assertEqual(
            blueprint["role_model_process"]["design_principle"]["mode"],
            "learning_path_replication_not_personality_injection",
        )
        self.assertIn("process_emulation_plan", {item["id"] for item in blueprint["artifact_plan"]})

    def test_reasoning_kibo_accumulates_from_school_years_and_keeps_growing_after_hire(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Build Graham process replication talent",
            talent_name="ShinYong",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "graham")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            plan = json.loads(artifacts["talent_plan"].read_text(encoding="utf-8"))
            manifest = json.loads(artifacts["agent_manifest"].read_text(encoding="utf-8"))
            kibo_rows = [
                json.loads(line)
                for line in artifacts["reasoning_kibo"].read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        entry_types = {row["entry_type"] for row in kibo_rows}
        year_ids = {row.get("year_id") for row in kibo_rows}

        self.assertIn("school_year_learning_accumulation", entry_types)
        self.assertIn("exam_refinement", entry_types)
        self.assertIn("elementary_grade_1", year_ids)
        self.assertIn("hired_agent_growth", year_ids)
        self.assertFalse(plan["reasoning_kibo"]["lifecycle"]["finalized"])
        self.assertGreaterEqual(plan["reasoning_kibo"]["yearly_learning_ladder_count"], 20)
        self.assertTrue(manifest["identity_source"]["reasoning_kibo_growth_model"]["continues_after_hire"])


if __name__ == "__main__":
    unittest.main()
