from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


def _manifest() -> dict:
    return {
        "schema": "ai-talent-agent-manifest/v1",
        "agent": {
            "name": "benchmark-test-agent",
            "role": "local research agent",
            "major_goal": "Verify runtime observability comparison.",
        },
        "memory_profile": {
            "semantic_themes": ["memory-board", "bounded context"],
            "procedural_principles": ["Select only relevant memory.", "Keep evidence reviewable."],
            "chain_of_thought_policy": "do_not_store_private_trace",
        },
        "llm_policy": {
            "role": "application_engine_not_identity",
            "private_reasoning_trace": "do_not_store",
        },
        "tool_policy": {
            "allowed_tools": ["work_session", "evidence_packet"],
            "blocked_tools": [],
        },
    }


class TalentFoundryRuntimeBenchmarkTests(unittest.TestCase):
    def test_compare_runtime_observability_cli_writes_public_safe_baseline_report(self) -> None:
        from ai22b.talent_foundry.agent_runner import run_agent_from_manifest
        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_path = root / "agent_run.json"
            report_path = root / "runtime_observability_comparison.json"
            run = run_agent_from_manifest(
                _manifest(),
                task="보스 검토용 리서치 메모리 경로를 비교해줘.",
            )
            run_path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")

            exit_code = cli_main(
                [
                    "compare-runtime-observability",
                    "--run",
                    str(run_path),
                    "--output",
                    str(report_path),
                ]
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            serialized = json.dumps(report, ensure_ascii=False)

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["schema"], "paideia-runtime-observability-comparison/v1")
        self.assertEqual(report["summary"]["record_count"], 1)
        self.assertEqual(report["summary"]["missing_observability_count"], 0)
        self.assertTrue(report["summary"]["public_safe"])
        self.assertTrue(report["summary"]["privacy_ok"])
        self.assertGreater(report["summary"]["generic_prompt_wrapper_replay_estimated_tokens"], 0)
        self.assertGreater(report["summary"]["paideia_prompt_context_estimated_tokens"], 0)
        self.assertGreater(report["summary"]["context_reduction_ratio"], 1)
        self.assertTrue(report["records"][0]["comparison"]["paideia_uses_less_context_than_replay_baseline"])
        self.assertFalse(report["records"][0]["privacy"]["private_reasoning_trace_stored"])
        self.assertIn("source_path_fingerprint_sha256", report["records"][0])
        self.assertNotIn(str(Path(tmp)), serialized)
        self.assertNotIn("C:\\Users\\", serialized)


if __name__ == "__main__":
    unittest.main()
