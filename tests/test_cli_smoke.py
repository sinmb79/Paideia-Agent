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
            doctor_path = tmp_path / "llm_provider_doctor.json"
            policy_eval_path = tmp_path / "policy_eval_report.json"

            role_models_code = cli_main(
                [
                    "list-role-models",
                    "--domain",
                    "securities_research",
                    "--output",
                    str(role_models_path),
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
            policy_eval_code = cli_main(["run-action-policy-eval", "--output", str(policy_eval_path)])

            role_models = json.loads(role_models_path.read_text(encoding="utf-8"))
            doctor = json.loads(doctor_path.read_text(encoding="utf-8"))
            policy_eval = json.loads(policy_eval_path.read_text(encoding="utf-8"))

        self.assertEqual(role_models_code, 0)
        self.assertEqual(doctor_code, 0)
        self.assertEqual(policy_eval_code, 0)

        self.assertEqual(role_models["schema"], "ai-talent-role-model-list/v1")
        self.assertEqual(role_models["domain"], "securities_research")
        self.assertIn("graham_value_investing", {item["role_model_id"] for item in role_models["role_models"]})

        self.assertEqual(doctor["schema"], "paideia-llm-provider-doctor/v1")
        self.assertEqual(doctor["engine"], "deterministic_local")
        self.assertTrue(doctor["passed"])
        self.assertEqual(doctor["network_access"], "blocked")
        self.assertFalse(doctor["secret_values_exported"])
        self.assertEqual(doctor["smoke_contract"]["schema"], "paideia-llm-provider-smoke-contract/v1")
        self.assertEqual(doctor["smoke_contract"]["status"], "skipped")
        self.assertFalse(doctor["smoke_contract"]["provider_call_attempted"])

        self.assertEqual(policy_eval["schema"], "paideia-action-policy-eval-report/v1")
        self.assertEqual(policy_eval["status"], "passed")
        self.assertEqual(policy_eval["summary"]["failed_count"], 0)
        self.assertFalse(policy_eval["runtime_policy"]["network_call_performed"])
        self.assertFalse(policy_eval["runtime_policy"]["llm_called"])


if __name__ == "__main__":
    unittest.main()
