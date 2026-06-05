from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class PaideiaGrowthPackageTests(unittest.TestCase):
    def test_graduate_package_and_same_sky_cli_use_growth_profile(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="Boss",
            request="Raise a securities research AI talent through Graham's learning process.",
            talent_name="graham-junior",
            gender="male",
            domain="securities_research",
            role_model_id="graham_value_investing",
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = materialize_training_blueprint(blueprint, output_dir=root / "graham")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            release_audit = json.loads(artifacts["release_audit"].read_text(encoding="utf-8"))
            runtime_benchmark = json.loads(
                artifacts["runtime_observability_comparison"].read_text(encoding="utf-8")
            )

            graduate_dir = root / "graduate_package"
            self.assertEqual(
                cli_main(
                    [
                        "build-graduate-package",
                        "--training-run",
                        str(artifacts["training_run"]),
                        "--output-dir",
                        str(graduate_dir),
                    ]
                ),
                0,
            )
            graduate_manifest = json.loads(
                (graduate_dir / "graduate_package_manifest.json").read_text(encoding="utf-8")
            )
            runtime_manifest = json.loads((graduate_dir / "runtime_manifest.json").read_text(encoding="utf-8"))
            self.assertTrue((graduate_dir / "agent_resume.md").exists())
            self.assertTrue((graduate_dir / "memory_pack" / "episodic_memory.jsonl").exists())

            scene = root / "scene.json"
            scene.write_text(
                json.dumps(
                    {
                        "id": "same_sky_market_note",
                        "prompt": "One company missed earnings, but cash flow stayed strong. What matters first?",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            same_sky_output = root / "same_sky_eval.json"
            self.assertEqual(
                cli_main(
                    [
                        "run-same-sky-eval",
                        "--agent",
                        str(artifacts["employment_record"]),
                        "--scene",
                        str(scene),
                        "--output",
                        str(same_sky_output),
                    ]
                ),
                0,
            )
            same_sky = json.loads(same_sky_output.read_text(encoding="utf-8"))

        self.assertEqual(graduate_manifest["schema"], "ai22b-paideia-graduate-package/v1")
        self.assertEqual(runtime_manifest["llm_contract"]["identity_source"], "graduate_package_memory_pack")
        self.assertTrue(run["verification"]["hired_agent_run_created"])
        self.assertTrue(run["verification"]["hired_dataflow_run_created"])
        self.assertTrue(run["verification"]["runtime_observability_comparison_created"])
        self.assertTrue(run["verification"]["release_audit_public_ready"])
        self.assertTrue(release_audit["public_release_ready"])
        self.assertTrue(release_audit["checkpoints"]["action_policy_safety"]["passed"])
        self.assertTrue(release_audit["checkpoints"]["learning_ledger_replay_safety"]["passed"])
        self.assertTrue(release_audit["checkpoints"]["runtime_observability_comparison"]["passed"])
        self.assertTrue(release_audit["checkpoints"]["role_model_runtime"]["details"]["agent_run_p0_runtime_ready"])
        self.assertTrue(release_audit["checkpoints"]["role_model_runtime"]["details"]["dataflow_p0_runtime_ready"])
        policy_details = release_audit["checkpoints"]["action_policy_safety"]["details"]
        self.assertEqual(policy_details["failed_count"], 0)
        self.assertGreaterEqual(policy_details["blocked_case_count"], 8)
        self.assertFalse(policy_details["network_call_performed"])
        self.assertFalse(policy_details["llm_called"])
        replay_details = release_audit["checkpoints"]["learning_ledger_replay_safety"]["details"]
        self.assertGreater(replay_details["entry_count"], 0)
        self.assertTrue(replay_details["installed_ledger_present"])
        self.assertTrue(replay_details["all_safe_references_bounded"])
        self.assertTrue(replay_details["all_safe_references_avoid_full_session_replay"])
        self.assertTrue(replay_details["all_private_reasoning_trace_policy_do_not_store"])
        self.assertEqual(runtime_benchmark["schema"], "paideia-runtime-observability-comparison/v1")
        self.assertTrue(runtime_benchmark["summary"]["public_safe"])
        self.assertGreater(runtime_benchmark["summary"]["context_reduction_ratio"], 1)
        self.assertEqual(
            release_audit["checkpoints"]["runtime_observability_comparison"]["details"]["schema"],
            runtime_benchmark["schema"],
        )
        self.assertEqual(
            release_audit["checkpoints"]["runtime_observability_comparison"]["details"]["record_count"],
            runtime_benchmark["summary"]["record_count"],
        )
        self.assertEqual(same_sky["schema"], "ai22b-paideia-same-sky-eval/v1")
        self.assertEqual(same_sky["agent_count"], 1)
        self.assertIn("growth_profile", same_sky["agent_views"][0]["response"]["evidence_links"])


if __name__ == "__main__":
    unittest.main()
