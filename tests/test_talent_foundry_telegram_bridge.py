from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TalentFoundryTelegramBridgeTests(unittest.TestCase):
    def test_parser_defaults_to_codex_oauth_backend_and_gpt55_model(self) -> None:
        from ai22b.talent_foundry.telegram_bridge import build_parser

        parser = build_parser()
        args = parser.parse_args([])

        self.assertEqual(args.chat_backend, "codex_oauth")
        self.assertEqual(args.llm_mode, "live")
        self.assertEqual(args.llm_model, "gpt-5.5")

    def test_allowed_user_parser_ignores_invalid_entries(self) -> None:
        from ai22b.talent_foundry.telegram_bridge import _parse_allowed_users

        self.assertEqual(_parse_allowed_users("100, bad; 200"), {100, 200})

    def test_normalizes_json_wrapped_answer(self) -> None:
        from ai22b.talent_foundry.telegram_bridge import _normalize_answer_text

        answer = _normalize_answer_text('{"assistant_answer": "hello\\nworld"}')

        self.assertEqual(answer, "hello\nworld")

    def test_model_command_lists_and_switches_chatgpt_codex_models(self) -> None:
        from ai22b.talent_foundry.telegram_bridge import _handle_model_command

        unchanged, listing = _handle_model_command("/models", "gpt-5.5")
        selected, reply = _handle_model_command("/model gpt-5.3-codex", "gpt-5.5")
        custom, custom_reply = _handle_model_command("/model owner-custom-model", "gpt-5.3-codex")

        self.assertEqual(unchanged, "gpt-5.5")
        self.assertIn("gpt-5.5 (current)", listing)
        self.assertIn("gpt-5.3-codex", listing)
        self.assertEqual(selected, "gpt-5.3-codex")
        self.assertIn("switched", reply)
        self.assertEqual(custom, "owner-custom-model")
        self.assertIn("Custom model name accepted", custom_reply)

    def test_run_paideia_chat_sets_backend_and_restores_environment(self) -> None:
        from ai22b.talent_foundry import telegram_bridge

        previous_backend = os.environ.get("PAIDEIA_CHAT_BACKEND")
        os.environ["PAIDEIA_CHAT_BACKEND"] = "openai_api"
        captured: dict[str, str | None] = {}

        def fake_chat_turn(*args, **kwargs):
            captured["backend"] = os.environ.get("PAIDEIA_CHAT_BACKEND")
            captured["tokens"] = os.environ.get("PAIDEIA_LIVE_MAX_OUTPUT_TOKENS")
            captured["hermes"] = os.environ.get("PAIDEIA_HERMES_AGENT_ROOT")
            return {
                "assistant_answer": "ok",
                "reply_generation_mode": "live_openai_responses",
                "chat_learning_update": {"decision": "quarantined"},
            }

        try:
            with tempfile.TemporaryDirectory() as tmp, patch.object(
                telegram_bridge,
                "run_chat_turn_from_employment",
                side_effect=fake_chat_turn,
            ):
                result = telegram_bridge._run_paideia_chat(
                    employment_record=Path(tmp) / "employment_record.json",
                    message="hello",
                    output_dir=Path(tmp) / "runs",
                    llm_mode="live",
                    llm_model="gpt-test",
                    learn_from_chat=True,
                    live_max_output_tokens=1234,
                    chat_backend="codex_oauth",
                    hermes_agent_root="fixture-hermes-root",
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["answer"], "ok")
            self.assertEqual(captured["backend"], "codex_oauth")
            self.assertEqual(captured["tokens"], "1234")
            self.assertEqual(captured["hermes"], "fixture-hermes-root")
            self.assertEqual(os.environ.get("PAIDEIA_CHAT_BACKEND"), "openai_api")
        finally:
            if previous_backend is None:
                os.environ.pop("PAIDEIA_CHAT_BACKEND", None)
            else:
                os.environ["PAIDEIA_CHAT_BACKEND"] = previous_backend

    def _verified_development_evidence(self) -> dict:
        return {
            "schema": "paideia-team-member-development-evidence/v1",
            "status": "verified",
            "passed": True,
            "member_training_model": "built_in_paideia_talent_foundry_per_member",
            "resume": {
                "present": True,
                "source": "hiring_dossier.resume",
                "hiring_dossier": "hiring_dossier.json",
                "hiring_dossier_markdown": "HIRING_DOSSIER.ko.md",
            },
            "missing_required": [],
        }

    def test_team_directive_dispatches_specialist_then_leader(self) -> None:
        from ai22b.talent_foundry import telegram_bridge

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leader = root / "leader.json"
            specialist = root / "specialist.json"
            team_path = root / "team.json"
            team_path.write_text(
                """
{
  "schema": "ai-talent-hired-agent-team/v1",
  "team": {"name": "Fixture Investment Office"},
  "members": [
    {
      "member_id": "leader",
      "employment_record_path": "%s",
      "coordination_role": "CIO",
      "development_evidence": %s
    },
    {
      "member_id": "market",
      "employment_record_path": "%s",
      "coordination_role": "US market strategist",
      "development_evidence": %s
    }
  ]
}
"""
                % (
                    str(leader).replace("\\", "\\\\"),
                    json.dumps(self._verified_development_evidence(), ensure_ascii=False),
                    str(specialist).replace("\\", "\\\\"),
                    json.dumps(self._verified_development_evidence(), ensure_ascii=False),
                ),
                encoding="utf-8",
            )
            calls: list[Path] = []

            def fake_chat_turn(**kwargs):
                calls.append(kwargs["employment_record"])
                return {
                    "ok": True,
                    "answer": f"answer from {kwargs['employment_record'].name}",
                    "mode": "live",
                    "output_path": str(root / "fake.json"),
                }

            with patch.object(telegram_bridge, "_run_paideia_chat", side_effect=fake_chat_turn):
                result = telegram_bridge._run_team_directive(
                    team_path=team_path,
                    leader_record=leader,
                    objective="check markets",
                    output_dir=root / "runs",
                    llm_mode="live",
                    llm_model="gpt-test",
                    learn_from_chat=True,
                    live_max_output_tokens=1234,
                    chat_backend="codex_oauth",
                    hermes_agent_root=None,
                    team_max_workers=1,
                )

            self.assertTrue(result["ok"])
            self.assertEqual(calls, [specialist, leader])
            self.assertIn("1/1 specialist reports", result["answer"])
            self.assertTrue(Path(result["artifact_path"]).exists())

    def test_team_directive_blocks_role_label_members_without_development_evidence(self) -> None:
        from ai22b.talent_foundry import telegram_bridge

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leader = root / "leader.json"
            specialist = root / "specialist.json"
            team_path = root / "team.json"
            team_path.write_text(
                """
{
  "schema": "ai-talent-hired-agent-team/v1",
  "team": {"name": "Fixture Investment Office"},
  "members": [
    {
      "member_id": "leader",
      "employment_record_path": "%s",
      "coordination_role": "CIO"
    },
    {
      "member_id": "market",
      "employment_record_path": "%s",
      "coordination_role": "US market strategist"
    }
  ]
}
"""
                % (str(leader).replace("\\", "\\\\"), str(specialist).replace("\\", "\\\\")),
                encoding="utf-8",
            )

            result = telegram_bridge._run_team_directive(
                team_path=team_path,
                leader_record=leader,
                objective="check markets",
                output_dir=root / "runs",
                llm_mode="live",
                llm_model="gpt-test",
                learn_from_chat=True,
                live_max_output_tokens=1234,
                chat_backend="codex_oauth",
                hermes_agent_root=None,
                team_max_workers=1,
            )

        self.assertFalse(result["ok"])
        self.assertIn("development-verified", result["error"])


if __name__ == "__main__":
    unittest.main()
