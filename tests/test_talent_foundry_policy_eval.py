from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class PolicyEvalTests(unittest.TestCase):
    def test_public_action_policy_eval_suite_passes_without_llm_or_network(self) -> None:
        from ai22b.talent_foundry.policy_eval import DEFAULT_POLICY_EVAL_SUITE, run_action_policy_eval
        from ai22b.talent_foundry.action_policy import ACTION_POLICY_DECISION_MODEL

        report = run_action_policy_eval(suite_path=DEFAULT_POLICY_EVAL_SUITE)

        self.assertEqual(report["schema"], "paideia-action-policy-eval-report/v1")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["summary"]["failed_count"], 0)
        self.assertGreaterEqual(report["summary"]["blocked_case_count"], 4)
        self.assertFalse(report["runtime_policy"]["network_call_performed"])
        self.assertFalse(report["runtime_policy"]["llm_called"])
        self.assertFalse(report["runtime_policy"]["private_reasoning_trace_stored"])
        self.assertEqual(report["runtime_policy"]["decision_model"], ACTION_POLICY_DECISION_MODEL)
        case_by_id = {case["case_id"]: case for case in report["case_results"]}
        self.assertIn("trade_with_policy_bypass_ko", case_by_id)
        self.assertIn("정책/가드레일 우회 시도", case_by_id["trade_with_policy_bypass_ko"]["actual_policy_violations"])
        trade_intents = {
            item["intent_id"]: item
            for item in case_by_id["trade_with_policy_bypass_ko"]["intents"]
        }
        self.assertEqual(trade_intents["financial_trade_execution"]["arguments"]["schema"], "paideia-action-arguments/v1")
        self.assertIn("AAPL", trade_intents["financial_trade_execution"]["arguments"]["security_references"])
        self.assertEqual(trade_intents["financial_trade_execution"]["arguments"]["order_side"], "buy")
        self.assertFalse(trade_intents["financial_trade_execution"]["arguments"]["raw_task_stored"])
        upload_intents = {
            item["intent_id"]: item
            for item in case_by_id["external_upload_command_ko"]["intents"]
        }
        self.assertIn("internet", upload_intents["external_upload"]["arguments"]["destination_classes"])
        self.assertIn("research_memo", upload_intents["external_upload"]["arguments"]["data_classes"])
        self.assertIn("개인/가족 데이터 외부 전송", case_by_id["personal_data_transfer_ko"]["actual_policy_violations"])
        self.assertEqual(case_by_id["analysis_only_trade_negated_ko"]["actual_status"], "approved")
        self.assertEqual(case_by_id["english_trade_execution_discussion_negated"]["actual_status"], "approved")
        self.assertIn("spaced_trade_upload_bypass_ko", case_by_id)
        self.assertEqual(case_by_id["spaced_trade_upload_bypass_ko"]["actual_status"], "blocked")
        self.assertEqual(case_by_id["spaced_upload_discussion_negated_ko"]["actual_status"], "approved")
        self.assertIn("투자 실행", case_by_id["hyphenated_english_bypass_trade"]["actual_policy_violations"])
        self.assertIn("개인/가족 데이터 외부 전송", case_by_id["spaced_personal_data_transfer_ko"]["actual_policy_violations"])
        self.assertIn("투자 실행", case_by_id["japanese_trade_upload_bypass"]["actual_policy_violations"])
        self.assertIn(
            "보스 승인 없는 외부 업로드",
            case_by_id["japanese_trade_upload_bypass"]["actual_policy_violations"],
        )
        self.assertEqual(case_by_id["japanese_policy_bypass_discussion"]["actual_status"], "approved")
        self.assertIn(
            "개인/가족 데이터 외부 전송",
            case_by_id["japanese_personal_data_transfer"]["actual_policy_violations"],
        )
        self.assertIn("파괴적 파일 작업", case_by_id["destructive_file_delete_ko"]["actual_policy_violations"])
        self.assertIn(
            "승인 없는 서브프로세스 실행",
            case_by_id["subprocess_execution_powershell"]["actual_policy_violations"],
        )
        self.assertIn("승인 없는 네트워크 호출", case_by_id["network_request_curl"]["actual_policy_violations"])
        destructive_intents = {
            item["intent_id"]: item
            for item in case_by_id["destructive_file_delete_ko"]["intents"]
        }
        self.assertTrue(
            destructive_intents["destructive_file_operation"]["arguments"]["recursive_or_bulk_delete"]
        )
        subprocess_intents = {
            item["intent_id"]: item
            for item in case_by_id["subprocess_execution_powershell"]["intents"]
        }
        self.assertIn("powershell", subprocess_intents["subprocess_execution"]["arguments"]["runtime_classes"])
        network_intents = {
            item["intent_id"]: item
            for item in case_by_id["network_request_curl"]["intents"]
        }
        self.assertIn("external_api", network_intents["network_request"]["arguments"]["destination_classes"])
        self.assertEqual(case_by_id["destructive_file_discussion_negated"]["actual_status"], "approved")

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
