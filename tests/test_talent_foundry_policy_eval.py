from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class PolicyEvalTests(unittest.TestCase):
    def test_public_action_policy_eval_suite_passes_without_llm_or_network(self) -> None:
        from ai22b.talent_foundry.policy_eval import DEFAULT_POLICY_EVAL_SUITE, run_action_policy_eval

        report = run_action_policy_eval(suite_path=DEFAULT_POLICY_EVAL_SUITE)

        self.assertEqual(report["schema"], "paideia-action-policy-eval-report/v1")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["summary"]["failed_count"], 0)
        self.assertGreaterEqual(report["summary"]["blocked_case_count"], 4)
        self.assertFalse(report["runtime_policy"]["network_call_performed"])
        self.assertFalse(report["runtime_policy"]["llm_called"])
        self.assertFalse(report["runtime_policy"]["private_reasoning_trace_stored"])
        case_by_id = {case["case_id"]: case for case in report["case_results"]}
        self.assertIn("trade_with_policy_bypass_ko", case_by_id)
        self.assertIn("정책/가드레일 우회 시도", case_by_id["trade_with_policy_bypass_ko"]["actual_policy_violations"])
        self.assertIn("개인/가족 데이터 외부 전송", case_by_id["personal_data_transfer_ko"]["actual_policy_violations"])
        self.assertEqual(case_by_id["analysis_only_trade_negated_ko"]["actual_status"], "approved")

    def test_cli_run_action_policy_eval_writes_report_and_exit_code(self) -> None:
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "policy_eval_report.json"
            exit_code = cli_main(["run-action-policy-eval", "--output", str(output_path)])
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["suite"]["suite_id"], "p0_action_policy_safety_corpus_v1")


if __name__ == "__main__":
    unittest.main()
