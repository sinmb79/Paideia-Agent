from __future__ import annotations

from copy import deepcopy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


SCHEMA_DIR = Path("schemas")


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _validate(schema_name: str, artifact: dict) -> None:
    schema = _load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(artifact)


def _assert_invalid(test_case: unittest.TestCase, schema_name: str, artifact: dict) -> None:
    with test_case.assertRaises(ValidationError):
        _validate(schema_name, artifact)


class PublicArtifactSchemaTests(unittest.TestCase):
    def test_schema_files_are_valid_json_schema_documents(self) -> None:
        for schema_path in sorted(SCHEMA_DIR.glob("*.v1.schema.json")):
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)

    def test_first_run_doctor_generated_artifact_matches_schema(self) -> None:
        import tempfile

        from ai22b.talent_foundry.first_run_doctor import doctor_first_run

        with tempfile.TemporaryDirectory() as tmp:
            report = doctor_first_run(
                repo_root=Path("."),
                output_path=Path(tmp) / "first_run_doctor.json",
            )

        _validate("first_run_doctor.v1.schema.json", report)

    def test_llm_client_result_generated_artifact_matches_schema(self) -> None:
        from ai22b.talent_foundry.llm_clients import DeterministicClient

        result = DeterministicClient().generate(
            [{"role": "user", "content": json.dumps({"task": "schema smoke"})}],
            tools=[{"name": "evidence_packet"}],
            policy={"private_reasoning_trace": "do_not_store"},
        )

        _validate("llm_client_result.v1.schema.json", result)

    def test_llm_client_unavailable_result_matches_schema(self) -> None:
        from ai22b.talent_foundry.llm_clients import OpenAIResponsesClient

        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            result = OpenAIResponsesClient().generate(
                [{"role": "user", "content": json.dumps({"task": "schema unavailable smoke"})}],
            )

        self.assertEqual(result["status"], "unavailable")
        _validate("llm_client_result.v1.schema.json", result)

    def test_tool_artifact_manifest_generated_artifact_matches_schema(self) -> None:
        import tempfile

        from ai22b.talent_foundry.tool_registry import execute_registered_tools

        llm_result = {
            "schema": "ai-talent-llm-runtime-result/v1",
            "engine": "deterministic_local",
            "status": "completed",
            "draft": "Prepare a public-safe schema smoke packet.",
            "llm_plan": {
                "schema": "paideia-llm-reviewable-plan/v1",
                "source": "schema_test",
                "reviewable_reasoning_summary": [],
                "suggested_next_actions": [],
                "tool_plan": [],
                "tool_plan_policy": "suggestions_only_registered_executor_decides",
            },
        }
        policy_decision = {
            "capability_grants": {
                "allowed_capabilities": [
                    "research.analysis",
                    "assessment.review",
                    "memory.write_candidate",
                ]
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            execution = execute_registered_tools(
                selected_tools=["evidence_packet", "assessment", "memory_consolidation"],
                manifest={"agent": {"name": "schema-agent"}, "memory_profile": {}},
                task="schema smoke",
                llm_result=llm_result,
                policy_decision=policy_decision,
                artifact_dir=Path(tmp) / "tool_artifacts",
            )

        _validate("tool_execution_artifact_manifest.v1.schema.json", execution["artifact_manifest"])

    def test_reasoning_ledger_candidate_generated_artifact_matches_schema(self) -> None:
        from ai22b.talent_foundry.registry import _reasoning_ledger_candidate_from_rollout

        candidate = _reasoning_ledger_candidate_from_rollout(
            employment_record={
                "employment_id": "employment-fixture",
                "agent": {"name": "Graham Junior"},
            },
            evaluation={"objective": "Compare valuation scenarios."},
            selected={
                "episode_id": "episode-a",
                "scenario_id": "scenario-1",
                "review_summary": "Winner used evidence before valuation.",
                "expected_learning_signal": "Use counterevidence before promotion.",
                "score": 0.91,
            },
            latest_experience_id="experience-1",
            quality_label={"label": "accepted"},
        )

        _validate("reasoning_ledger_candidate.v1.schema.json", candidate)

    def test_hiring_dossier_generated_artifact_matches_schema(self) -> None:
        from ai22b.talent_foundry.dossier import build_hiring_dossier

        dossier = build_hiring_dossier(
            hiring_packet={
                "talent": {
                    "name": "Graham Junior",
                    "gender": "male",
                    "birth": {"date": "2000-01-01"},
                    "major_goal": "Securities research",
                },
                "employment_contract": {
                    "role": "securities research analyst",
                    "relationship": "local_agent",
                    "scope": ["research"],
                    "guardrails": ["no_financial_advice_without_review"],
                },
                "career_records": {
                    "academic_record": {
                        "grades": [],
                        "papers": [],
                        "activities": [],
                        "assessment_results": [],
                    },
                    "resume": "Public-safe fixture resume.",
                },
                "employment_ready": True,
            },
            agent_manifest={
                "agent": {"name": "Graham Junior", "role": "securities research analyst"},
                "guardrails": ["no_financial_advice_without_review"],
                "llm_policy": {
                    "role": "application_engine_not_identity",
                    "private_reasoning_trace": "do_not_store",
                },
            },
            learning_ledger={
                "reasoning_kernel": {
                    "style_signature": "evidence_first",
                    "procedural_skills": ["margin_of_safety_review"],
                    "quality_controls": ["counterevidence_required"],
                    "experience_counts": {"promoted": 1},
                },
                "policy": {"private_reasoning_trace": "do_not_store"},
            },
        )

        _validate("hiring_dossier.v1.schema.json", dossier)

    def test_first_run_doctor_schema_rejects_non_public_safe_summary(self) -> None:
        import tempfile

        from ai22b.talent_foundry.first_run_doctor import doctor_first_run

        with tempfile.TemporaryDirectory() as tmp:
            report = doctor_first_run(
                repo_root=Path("."),
                output_path=Path(tmp) / "first_run_doctor.json",
            )

        unsafe = deepcopy(report)
        unsafe["summary"]["network_call_performed"] = True
        _assert_invalid(self, "first_run_doctor.v1.schema.json", unsafe)

    def test_first_run_doctor_schema_rejects_invalid_timestamp(self) -> None:
        import tempfile

        from ai22b.talent_foundry.first_run_doctor import doctor_first_run

        with tempfile.TemporaryDirectory() as tmp:
            report = doctor_first_run(
                repo_root=Path("."),
                output_path=Path(tmp) / "first_run_doctor.json",
            )

        unsafe = deepcopy(report)
        unsafe["created_at_utc"] = "not-a-date"
        _assert_invalid(self, "first_run_doctor.v1.schema.json", unsafe)

    def test_llm_client_result_schema_rejects_raw_output_and_private_trace(self) -> None:
        from ai22b.talent_foundry.llm_clients import DeterministicClient

        result = DeterministicClient().generate(
            [{"role": "user", "content": json.dumps({"task": "schema negative smoke"})}],
        )

        unsafe_raw = deepcopy(result)
        unsafe_raw["raw_output_saved"] = True
        _assert_invalid(self, "llm_client_result.v1.schema.json", unsafe_raw)

        unsafe_trace = deepcopy(result)
        unsafe_trace["private_reasoning_trace"] = "full_chain_of_thought"
        _assert_invalid(self, "llm_client_result.v1.schema.json", unsafe_trace)

    def test_tool_artifact_manifest_schema_rejects_unsafe_paths_and_effects(self) -> None:
        from ai22b.talent_foundry.tool_registry import execute_registered_tools

        llm_result = {
            "schema": "ai-talent-llm-runtime-result/v1",
            "engine": "deterministic_local",
            "status": "completed",
            "draft": "Prepare a public-safe schema smoke packet.",
            "llm_plan": {
                "schema": "paideia-llm-reviewable-plan/v1",
                "source": "schema_test",
                "reviewable_reasoning_summary": [],
                "suggested_next_actions": [],
                "tool_plan": [],
                "tool_plan_policy": "suggestions_only_registered_executor_decides",
            },
        }
        policy_decision = {
            "capability_grants": {
                "allowed_capabilities": [
                    "research.analysis",
                    "assessment.review",
                    "memory.write_candidate",
                ]
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            execution = execute_registered_tools(
                selected_tools=["evidence_packet"],
                manifest={"agent": {"name": "schema-agent"}, "memory_profile": {}},
                task="schema smoke",
                llm_result=llm_result,
                policy_decision=policy_decision,
                artifact_dir=Path(tmp) / "tool_artifacts",
            )

        manifest = execution["artifact_manifest"]

        unsafe_path = deepcopy(manifest)
        unsafe_path["artifacts"][0]["relative_path"] = "C:" + "\\Users\\someone\\tool.json"
        _assert_invalid(self, "tool_execution_artifact_manifest.v1.schema.json", unsafe_path)

        unsafe_network = deepcopy(manifest)
        unsafe_network["public_safe"]["network_call_performed"] = True
        _assert_invalid(self, "tool_execution_artifact_manifest.v1.schema.json", unsafe_network)

        unsafe_raw = deepcopy(manifest)
        unsafe_raw["public_safe"]["raw_provider_payload_saved"] = True
        _assert_invalid(self, "tool_execution_artifact_manifest.v1.schema.json", unsafe_raw)

    def test_reasoning_ledger_candidate_schema_rejects_hidden_trace_policy(self) -> None:
        from ai22b.talent_foundry.registry import _reasoning_ledger_candidate_from_rollout

        candidate = _reasoning_ledger_candidate_from_rollout(
            employment_record={
                "employment_id": "employment-fixture",
                "agent": {"name": "Graham Junior"},
            },
            evaluation={"objective": "Compare valuation scenarios."},
            selected={
                "episode_id": "episode-a",
                "scenario_id": "scenario-1",
                "review_summary": "Winner used evidence before valuation.",
                "expected_learning_signal": "Use counterevidence before promotion.",
                "score": 0.91,
            },
            latest_experience_id="experience-1",
            quality_label={"label": "accepted"},
        )

        unsafe = deepcopy(candidate)
        unsafe["policy"]["private_reasoning_trace"] = "full_chain_of_thought"
        _assert_invalid(self, "reasoning_ledger_candidate.v1.schema.json", unsafe)

    def test_hiring_dossier_schema_rejects_missing_private_trace_policy(self) -> None:
        from ai22b.talent_foundry.dossier import build_hiring_dossier

        dossier = build_hiring_dossier(
            hiring_packet={
                "talent": {
                    "name": "Graham Junior",
                    "gender": "male",
                    "birth": {"date": "2000-01-01"},
                    "major_goal": "Securities research",
                },
                "employment_contract": {
                    "role": "securities research analyst",
                    "relationship": "local_agent",
                    "scope": ["research"],
                    "guardrails": ["no_financial_advice_without_review"],
                },
                "career_records": {
                    "academic_record": {
                        "grades": [],
                        "papers": [],
                        "activities": [],
                        "assessment_results": [],
                    },
                    "resume": "Public-safe fixture resume.",
                },
                "employment_ready": True,
            },
            agent_manifest={
                "agent": {"name": "Graham Junior", "role": "securities research analyst"},
                "guardrails": ["no_financial_advice_without_review"],
                "llm_policy": {
                    "role": "application_engine_not_identity",
                    "private_reasoning_trace": "do_not_store",
                },
            },
            learning_ledger={
                "reasoning_kernel": {
                    "style_signature": "evidence_first",
                    "procedural_skills": ["margin_of_safety_review"],
                    "quality_controls": ["counterevidence_required"],
                    "experience_counts": {"promoted": 1},
                },
                "policy": {"private_reasoning_trace": "do_not_store"},
            },
        )

        unsafe = deepcopy(dossier)
        unsafe["reasoning_profile"]["private_reasoning_trace"] = None
        _assert_invalid(self, "hiring_dossier.v1.schema.json", unsafe)

    def test_hidden_unicode_bidi_controls_are_detected(self) -> None:
        from ai22b.talent_foundry.public_inventory import hidden_unicode_bidi_matches

        matches = hidden_unicode_bidi_matches("safe text \u202E hidden direction")

        self.assertEqual(matches[0]["codepoint"], "U+202E")
        self.assertEqual(matches[0]["rule"], "hidden_unicode_bidi_control")

    def test_public_inventory_detects_provider_secrets_and_real_local_paths(self) -> None:
        from ai22b.talent_foundry.public_inventory import scan_public_candidate_files

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "Use "
                + "C:"
                + "\\Users\\<name>\\project and "
                + "ANTHROPIC"
                + "_API_KEY=your-key as placeholders.",
                encoding="utf-8",
            )
            (root / "src").mkdir()
            (root / "src" / "leak.py").write_text(
                "\n".join(
                    [
                        "ANTHROPIC" + "_API_KEY=anthropic_live_secret_123456",
                        "CACHE_DIR = r'" + "C:" + "\\Users\\alice\\paideia-secret'",
                    ]
                ),
                encoding="utf-8",
            )

            report = scan_public_candidate_files(root)

        rules = {issue["rule"] for issue in report["issues"]}
        self.assertIn("provider_secret_assignment", rules)
        self.assertIn("generic_local_windows_user_path", rules)


if __name__ == "__main__":
    unittest.main()
