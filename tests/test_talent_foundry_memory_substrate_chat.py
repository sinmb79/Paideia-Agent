from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class TalentFoundryMemorySubstrateChatTests(unittest.TestCase):
    def _minimal_live_chat_context(self) -> dict:
        return {
            "schema": "ai-talent-chat-context/v1",
            "language": "ko",
            "agent": {"name": "fixture-agent"},
            "message": "hello",
            "identity_record": {},
            "learning_profile": {},
            "active_memory_route": {"selected_nodes": []},
            "memory_bridge": {"selected_memory_tiles": []},
            "conversation_method_training": {},
            "language_development_program": {},
            "recent_chat_history": [],
            "guardrails": [],
        }

    def test_graham_raise_packages_memory_substrate_for_separate_sample_ai(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            substrate = json.loads(artifacts["memory_substrate"].read_text(encoding="utf-8"))
            grade_learning_records = json.loads(artifacts["grade_learning_records"].read_text(encoding="utf-8"))
            bundle_manifest = json.loads(
                (artifacts["release_bundle"] / "bundle_manifest.json").read_text(encoding="utf-8")
            )
            installed_manifest = json.loads(artifacts["installed_agent_manifest"].read_text(encoding="utf-8"))
            employment_record = json.loads(artifacts["employment_record"].read_text(encoding="utf-8"))
            hired_llm_profile = json.loads(
                artifacts["hired_llm_connection_profile"].read_text(encoding="utf-8")
            )
            hired_llm_live_setup_guide = json.loads(
                artifacts["hired_llm_live_setup_guide"].read_text(encoding="utf-8")
            )
            agent_id_payload = json.loads(artifacts["agent_id_card_payload"].read_text(encoding="utf-8"))
            agent_identity_envelope = json.loads(artifacts["agent_identity_envelope"].read_text(encoding="utf-8"))
            agent_identity_verification = json.loads(
                artifacts["agent_identity_verification"].read_text(encoding="utf-8")
            )
            agent_warrent_registration_request = json.loads(
                artifacts["agent_warrent_registration_request"].read_text(encoding="utf-8")
            )

        self.assertEqual(substrate["schema"], "ai-talent-memory-substrate/v1")
        self.assertEqual(substrate["agent"]["name"], "grham-쥬니어")
        self.assertGreater(substrate["source_counts"]["reasoning_kibo_entries"], 20)
        self.assertGreaterEqual(substrate["source_counts"]["language_development_stages"], 8)
        self.assertEqual(substrate["source_counts"]["life_trace_events"], 252)
        self.assertGreaterEqual(substrate["source_counts"]["developmental_ecology_layers"], 7)
        self.assertGreaterEqual(substrate["source_counts"]["growth_profile_nodes"], 5)
        self.assertGreaterEqual(substrate["source_counts"]["grade_learning_records"], 20)
        self.assertGreaterEqual(substrate["source_counts"]["grade_learning_nodes"], 40)
        self.assertEqual(grade_learning_records["schema"], "paideia-grade-learning-records/v1")
        self.assertGreater(grade_learning_records["summary"]["assessment_link_count"], 0)
        self.assertGreater(grade_learning_records["summary"]["reasoning_ledger_link_count"], 0)
        self.assertIn("procedural_operator_store", substrate["boards"])
        self.assertIn("conversation_development", substrate["boards"])
        self.assertIn("developmental_ecology", substrate["boards"])
        self.assertIn("life_trace", substrate["boards"])
        self.assertIn("growth_profile", substrate["boards"])
        self.assertIn("grade_learning_records", substrate["boards"])
        self.assertEqual(bundle_manifest["included_artifacts"]["memory_substrate"], "memory_substrate.json")
        self.assertEqual(
            bundle_manifest["included_artifacts"]["language_development_program"],
            "language_development_program.json",
        )
        self.assertEqual(bundle_manifest["included_artifacts"]["developmental_ecology"], "developmental_ecology.json")
        self.assertEqual(bundle_manifest["included_artifacts"]["life_trace"], "life_trace.jsonl")
        self.assertEqual(bundle_manifest["included_artifacts"]["growth_profile"], "growth_profile.json")
        self.assertEqual(bundle_manifest["included_artifacts"]["grade_learning_records"], "grade_learning_records.json")
        self.assertEqual(bundle_manifest["closed_growth_contract"]["schema"], "paideia-closed-growth-contract/v1")
        self.assertEqual(bundle_manifest["closed_growth_contract"]["ecosystem_model"], "closed_curated_growth_ecosystem")
        self.assertIn("external_skill_quarantine_engine", bundle_manifest["core_engine_boundaries"]["engine_ids"])
        self.assertIn("memory_substrate", installed_manifest["entrypoints"])
        self.assertIn("language_development_program", installed_manifest["entrypoints"])
        self.assertIn("developmental_ecology", installed_manifest["entrypoints"])
        self.assertIn("life_trace", installed_manifest["entrypoints"])
        self.assertIn("growth_profile", installed_manifest["entrypoints"])
        self.assertIn("grade_learning_records", installed_manifest["entrypoints"])
        self.assertEqual(employment_record["agent"]["name"], "grham-쥬니어")
        self.assertIn("last_chat", employment_record["entrypoints"])
        self.assertIn("developmental_ecology", employment_record["entrypoints"])
        self.assertIn("life_trace", employment_record["entrypoints"])
        self.assertIn("growth_profile", employment_record["entrypoints"])
        self.assertIn("grade_learning_records", employment_record["entrypoints"])
        self.assertIn("llm_connection_profile", employment_record["entrypoints"])
        self.assertIn("llm_live_setup_guide", employment_record["entrypoints"])
        self.assertEqual(hired_llm_profile["schema"], "paideia-llm-connection-profile/v1")
        self.assertEqual(hired_llm_live_setup_guide["schema"], "paideia-llm-live-setup-guide/v1")
        self.assertEqual(
            employment_record["llm_connection_profile"]["entrypoint"],
            employment_record["entrypoints"]["llm_connection_profile"],
        )
        self.assertEqual(
            employment_record["llm_live_setup_guide"]["entrypoint"],
            employment_record["entrypoints"]["llm_live_setup_guide"],
        )
        self.assertEqual(
            employment_record["llm_connection_profile"]["selected_engine"],
            hired_llm_profile["selected_llm_service"]["engine"],
        )
        self.assertEqual(
            employment_record["llm_live_setup_guide"]["selected_engine"],
            hired_llm_live_setup_guide["selected_llm_service"]["engine"],
        )
        self.assertFalse(hired_llm_profile["public_safe"]["network_call_performed"])
        self.assertFalse(hired_llm_live_setup_guide["public_safe"]["network_call_performed"])
        self.assertIn("agent_id_card_payload", employment_record["entrypoints"])
        self.assertIn("agent_identity_envelope", employment_record["entrypoints"])
        self.assertIn("agent_identity_verification", employment_record["entrypoints"])
        self.assertIn("agent_warrent_registration_request", employment_record["entrypoints"])
        self.assertEqual(agent_id_payload["schema"], "ai-talent-agent-id-card-payload/v1")
        self.assertEqual(agent_identity_envelope["version"], "ail.v1")
        self.assertEqual(
            agent_warrent_registration_request["schema"],
            "paideia-agent-warrent-registration-request/v1",
        )
        self.assertEqual(
            employment_record["agent_identity"]["agent_warrent_registration_request"]["entrypoint"],
            employment_record["entrypoints"]["agent_warrent_registration_request"],
        )
        self.assertFalse(agent_warrent_registration_request["submit_ready"])
        self.assertTrue(agent_warrent_registration_request["validation"]["signature_required"])
        self.assertFalse(agent_warrent_registration_request["network_action_performed"])
        self.assertEqual(
            agent_identity_envelope["delegation"]["task_ref"],
            "employment:" + employment_record["employment_id"],
        )
        self.assertEqual(agent_identity_verification["status"], "passed")
        self.assertFalse(agent_identity_verification["network_action_performed"])
        self.assertEqual(
            employment_record["agent_identity"]["agent_identity_layer"]["registration_state"],
            "local_unregistered",
        )

    def test_chat_turn_uses_codex_as_engine_and_local_kibo_as_identity(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            output = Path(tmp) / "chat.json"
            chat = run_chat_turn_from_employment(
                hiring["employment_record"],
                message="저평가 기업을 찾을 때 어떤 자료부터 확인해야 합니까?",
                output_path=output,
            )
            saved = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(chat["schema"], "ai-talent-chat-run/v1")
        self.assertEqual(saved["chat_context"]["agent"]["name"], "grham-쥬니어")
        self.assertEqual(saved["chat_context"]["llm_contract"]["provider"], "openai_chatgpt_codex")
        self.assertEqual(saved["llm_runtime_result"]["status"], "bridge_context_prepared")
        self.assertEqual(saved["llm_runtime_result"]["identity_policy"], "application_engine_not_identity")
        self.assertTrue(saved["chat_context"]["active_memory_route"]["selected_nodes"])
        self.assertIn("memory_substrate.json", saved["chat_context"]["llm_contract"]["identity_source"])
        self.assertIn("grade_learning_records", saved["chat_context"]["llm_contract"]["identity_source"])
        self.assertIn("grham-쥬니어", saved["assistant_reply"])
        self.assertFalse(saved["stored_private_reasoning_trace"])

    def test_chat_turn_handles_greeting_as_ordinary_conversation(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            chat = run_chat_turn_from_employment(
                hiring["employment_record"],
                message="안녕",
                output_path=Path(tmp) / "greeting.json",
            )

        self.assertEqual(chat["conversation_intent"], "greeting")
        self.assertIn("안녕하세요", chat["assistant_reply"])
        self.assertNotIn("evidence_first_research_loop", chat["assistant_reply"])
        self.assertFalse(chat["stored_private_reasoning_trace"])

    def test_chat_turn_answers_metacognitive_question_with_reviewable_reasoning_summary(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            chat = run_chat_turn_from_employment(
                hiring["employment_record"],
                message="일상적인 대화에서도 추론이 필요한가?",
                output_path=Path(tmp) / "meta.json",
            )

        self.assertEqual(chat["conversation_intent"], "metacognitive_question")
        self.assertIn("네, 일상적인 대화에도 추론은 필요합니다", chat["assistant_answer"])
        self.assertIn("판단 요약", chat["assistant_reply"])
        self.assertGreaterEqual(len(chat["reviewable_reasoning_summary"]), 3)

    def test_chat_turn_answers_growth_story_from_learning_kibo(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            chat = run_chat_turn_from_employment(
                hiring["employment_record"],
                message="성장과정을 얘기해봐",
                output_path=Path(tmp) / "growth.json",
            )

        self.assertEqual(chat["conversation_intent"], "growth_story_question")
        self.assertIn("성장과정", chat["assistant_answer"])
        self.assertIn("초등 시기", chat["assistant_answer"])
        self.assertIn("대학교 시기", chat["assistant_answer"])
        self.assertNotIn('{"focus"', chat["assistant_answer"])
        self.assertIn("growth_story.education_lifecycle_retrieval", chat["active_operator"])
        self.assertNotIn("일상적인 대화에도 추론은 필요합니다", chat["assistant_answer"])

    def test_chat_turn_answers_language_development_question(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            self.assertTrue(artifacts["language_development_program"].exists())
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            chat = run_chat_turn_from_employment(
                hiring["employment_record"],
                message="대화하는 법은 어떻게 배웠어?",
                output_path=Path(tmp) / "language.json",
            )

        self.assertEqual(chat["conversation_intent"], "language_development_question")
        self.assertIn("언어발달 과정", chat["assistant_answer"])
        self.assertIn("태아-영아기", chat["assistant_answer"])
        self.assertIn("고용 이후", chat["assistant_answer"])
        self.assertEqual(chat["active_operator"], "language_development.social_pragmatic_ladder")

    def test_chat_turn_answers_friend_conflict_repair_story(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            chat = run_chat_turn_from_employment(
                hiring["employment_record"],
                message="친구와의 갈등을 회복한 사례에 대해 얘기해줘",
                output_path=Path(tmp) / "friend_conflict.json",
            )

        self.assertEqual(chat["conversation_intent"], "social_conflict_story")
        self.assertEqual(chat["active_operator"], "social_development.conflict_repair_episode")
        self.assertIn("친구 갈등 회복 사례", chat["assistant_answer"])
        self.assertIn("사과", chat["assistant_answer"])
        self.assertIn("감정과 사실을 분리", chat["assistant_answer"])
        self.assertNotIn("전문 리서치보다 일반 대화", chat["assistant_answer"])

    def test_chat_turn_answers_family_identity_without_mixing_shinyong(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            chat = run_chat_turn_from_employment(
                hiring["employment_record"],
                message="너의 부모는 어떤 사람이야",
                output_path=Path(tmp) / "family_identity.json",
            )

        self.assertEqual(chat["conversation_intent"], "identity_family_question")
        self.assertEqual(chat["active_operator"], "identity.family_origin_boundary")
        self.assertIn("창조자", chat["assistant_answer"])
        self.assertIn("보호자", chat["assistant_answer"])
        self.assertIn("신용이와 분리", chat["assistant_answer"])
        self.assertIn("Graham은 제 부모가 아니라", chat["assistant_answer"])
        self.assertNotIn("전문 리서치보다 일반 대화", chat["assistant_answer"])

    def test_live_llm_chat_uses_local_context_and_quarantines_chat_learning(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        captured: dict[str, object] = {}

        def fake_live_chat(*, chat_context: dict, model: str, max_output_tokens: int = 900) -> dict:
            captured["model"] = model
            captured["context"] = chat_context
            return {
                "schema": "ai-talent-live-llm-result/v1",
                "engine": "openai_responses_api",
                "status": "completed",
                "model": model,
                "assistant_reply": (
                    "보스, 저는 저장된 성장 기록과 최근 대화 맥락을 보고 대답하겠습니다. "
                    "이제 정해진 케이스 답변이 아니라 그때그때 맥락을 해석합니다."
                ),
                "reviewable_reasoning_summary": [
                    {"step": "맥락 선택", "summary": "로컬 정체성, memory substrate, 최근 대화를 우선 사용했습니다."},
                    {"step": "답변 생성", "summary": "하드코딩된 사례가 아니라 실시간 LLM 답변으로 구성했습니다."},
                ],
                "learning_candidate": {
                    "lesson": "일반 대화는 사례별 분기보다 로컬 맥락 기반 생성이 필요하다.",
                    "reusable_principle": "먼저 정체성 기록과 최근 대화를 읽고 자연스럽게 답한다.",
                    "memory_tags": ["live_llm", "conversation_context_learning"],
                    "confidence": 0.9,
                },
            }

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            target_root = Path(hiring["employment_record"]).parent
            ledger_before = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))
            with patch.dict(os.environ, {"OPENAI_API_KEY": "fixture-openai-key-12345"}, clear=False), patch(
                "ai22b.talent_foundry.memory_substrate._call_openai_responses_chat",
                side_effect=fake_live_chat,
            ):
                chat = run_chat_turn_from_employment(
                    hiring["employment_record"],
                    message="오늘은 그냥 편하게 이야기해보자",
                    output_path=Path(tmp) / "live_chat.json",
                    llm_mode="live",
                    llm_model="gpt-test",
                    learn_from_chat=True,
                )
            ledger = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))
            substrate = json.loads((target_root / "memory_substrate.json").read_text(encoding="utf-8"))

        self.assertEqual(captured["model"], "gpt-test")
        context = captured["context"]
        self.assertEqual(context["agent"]["name"], "grham-쥬니어")
        self.assertIn("identity_record", context)
        self.assertIn("learning_profile", context)
        self.assertEqual(context["memory_bridge"]["schema"], "paideia-live-chat-memory-bridge/v1")
        self.assertGreaterEqual(context["memory_bridge"]["source_counts"]["grade_learning_records"], 20)
        self.assertTrue(context["memory_bridge"]["education_growth_context"]["grade_learning_tiles"])
        self.assertTrue(context["memory_bridge"]["education_growth_context"]["reasoning_ledger_tiles"])
        self.assertTrue(any(item["action"] == "memory_bridge_built" for item in chat["chat_execution_trace"]))
        self.assertEqual(chat["reply_generation_mode"], "live_openai_responses")
        self.assertEqual(chat["active_operator"], "llm.dynamic_context_conversation")
        self.assertIn("그때그때 맥락을 해석", chat["assistant_answer"])
        self.assertTrue(any(item["action"] == "live_llm_attempt" for item in chat["chat_execution_trace"]))
        self.assertEqual(chat["chat_learning_update"]["decision"], "quarantined")
        self.assertEqual(
            chat["chat_learning_update"]["policy"],
            "chat_learning_candidate_pending_boss_review_no_automatic_promotion",
        )
        self.assertFalse(chat["chat_learning_update"]["automatic_promotion_performed"])
        self.assertEqual(chat["chat_execution_trace"][-2]["action"], "chat_learning_update")
        self.assertEqual(chat["chat_execution_trace"][-1]["action"], "chat_runtime_status_card_recorded")
        self.assertEqual(chat["chat_runtime_status_card"]["status"], "completed_live")
        self.assertEqual(chat["chat_runtime_status_card"]["learning"]["decision"], "quarantined")
        self.assertEqual(
            chat["memory_lifecycle_status_card"]["schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(chat["memory_lifecycle_status_card"]["source"], "chat_turn")
        self.assertEqual(chat["memory_lifecycle_status_card"]["learning"]["decision"], "quarantined")
        self.assertTrue(chat["memory_lifecycle_status_card"]["active_context"]["quarantined_excluded"])
        self.assertEqual(
            chat["chat_runtime_status_card"]["memory_lifecycle"]["status"],
            chat["memory_lifecycle_status_card"]["status"],
        )
        self.assertEqual(
            len(ledger.get("promoted_experiences", [])),
            len(ledger_before.get("promoted_experiences", [])),
        )
        self.assertEqual(
            len(ledger.get("quarantined_experiences", [])),
            len(ledger_before.get("quarantined_experiences", [])) + 1,
        )
        self.assertEqual(ledger["quarantined_experiences"][-1]["source"], "chat_turn")
        self.assertIn("do_not_promote_to_reasoning_kernel", ledger["quarantined_experiences"][-1]["flags"])
        self.assertTrue(ledger["quarantined_experiences"][-1]["quality_label"]["force_quarantine"])
        self.assertTrue(chat["chat_learning_update"]["forced_quarantine"])
        self.assertFalse(
            any(node.get("source") == "learning_ledger_chat_turn" for node in substrate.get("nodes", []))
        )

    def test_live_chat_uses_generic_llm_client_for_non_openai_providers(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        captured: dict[str, object] = {}

        class FakeGenericClient:
            def generate(self, messages, *, tools=None, policy=None):
                captured["messages"] = messages
                captured["policy"] = policy
                return {
                    "schema": "paideia-llm-client-result/v1",
                    "engine": "openrouter_api",
                    "status": "completed",
                    "model": "openai/gpt-test",
                    "text": json.dumps(
                        {
                            "assistant_reply": "보스, 선택한 범용 LLM provider를 통해 로컬 기억 맥락으로 답했습니다.",
                            "reviewable_reasoning_summary": [
                                {
                                    "step": "context",
                                    "summary": "active memory route was supplied to the provider.",
                                    "hidden_chain_of_thought": "do not store this hidden chat trace",
                                }
                            ],
                            "learning_candidate": {
                                "lesson": "chat live providers must share the same local identity context.",
                                "reusable_principle": "route non-OpenAI providers through the common LLMClient interface.",
                                "memory_tags": ["generic_live_chat_provider"],
                                "confidence": 0.88,
                                "private_reasoning_trace": "do not promote this private chat trace",
                            },
                            "chain_of_thought": "do not persist top-level private chat reasoning",
                        },
                        ensure_ascii=False,
                    ),
                    "identity_policy": "application_engine_not_identity",
                    "raw_output_saved": False,
                    "network_access": "external_api_selected_data_minimized",
                }

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-주니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openrouter_api",
                llm_model="openai/gpt-test",
                record_name="employment_record_openrouter.json",
            )
            target_root = Path(hiring["employment_record"]).parent
            ledger_before = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fixture-openrouter-key"}, clear=False), patch(
                "ai22b.talent_foundry.memory_substrate.build_llm_client",
                return_value=FakeGenericClient(),
            ):
                chat = run_chat_turn_from_employment(
                    hiring["employment_record"],
                    message="오늘은 가볍게 대화하되 네가 배운 맥락을 사용해줘.",
                    output_path=Path(tmp) / "generic_live_chat.json",
                    llm_mode="live",
                    llm_model="openai/gpt-test",
                    learn_from_chat=True,
                )
            ledger_after = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))

        self.assertEqual(chat["reply_generation_mode"], "live_generic_llm_client")
        self.assertEqual(chat["llm_runtime_result"]["provider_adapter"], "generic_llm_client")
        self.assertEqual(chat["llm_runtime_result"]["engine"], "openrouter_api")
        self.assertEqual(chat["llm_runtime_result"]["private_reasoning_fields_omitted"], 3)
        self.assertFalse(chat["llm_runtime_result"]["data_policy"]["private_reasoning_field_values_stored"])
        self.assertEqual(chat["assistant_answer"], "보스, 선택한 범용 LLM provider를 통해 로컬 기억 맥락으로 답했습니다.")
        serialized = json.dumps(chat, ensure_ascii=False)
        self.assertNotIn("do not store this hidden chat trace", serialized)
        self.assertNotIn("do not promote this private chat trace", serialized)
        self.assertNotIn("do not persist top-level private chat reasoning", serialized)
        self.assertTrue(captured["messages"])
        live_payload = json.loads(captured["messages"][-1]["content"])
        live_context = live_payload["local_talent_context"]
        self.assertEqual(live_context["memory_bridge"]["schema"], "paideia-live-chat-memory-bridge/v1")
        self.assertTrue(live_context["memory_bridge"]["education_growth_context"]["grade_learning_tiles"])
        self.assertEqual(captured["policy"]["response_format"], "json_object")
        self.assertEqual(chat["chat_learning_update"]["decision"], "quarantined")
        self.assertEqual(chat["chat_learning_update"]["policy"], "chat_learning_candidate_pending_boss_review_no_automatic_promotion")
        self.assertTrue(chat["chat_learning_update"]["forced_quarantine"])
        self.assertEqual(
            len(ledger_after.get("promoted_experiences", [])),
            len(ledger_before.get("promoted_experiences", [])),
        )
        self.assertEqual(
            len(ledger_after.get("quarantined_experiences", [])),
            len(ledger_before.get("quarantined_experiences", [])) + 1,
        )
        self.assertTrue(
            any(
                item["action"] == "live_llm_attempt"
                and item.get("provider_adapter") == "generic_llm_client"
                for item in chat["chat_execution_trace"]
            )
        )

    def test_live_llm_failure_fallback_does_not_promote_bad_chat_learning(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        secret = "fixture_openai_live_chat_secret_12345"

        def fake_failed_live_chat(*, chat_context: dict, model: str, max_output_tokens: int = 900) -> dict:
            return {
                "schema": "ai-talent-live-llm-result/v1",
                "engine": "openai_responses_api",
                "status": "unavailable",
                "reason": "test_quota_failure",
                "model": model,
                "error": (
                    f"request failed with Authorization: Bearer {secret}; "
                    f"https://api.openai.com/v1/responses?key={secret}"
                ),
            }

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            output_path = Path(tmp) / "live_failed_chat.json"
            with patch.dict(os.environ, {"OPENAI_API_KEY": secret}, clear=False), patch(
                "ai22b.talent_foundry.memory_substrate._call_openai_responses_chat",
                side_effect=fake_failed_live_chat,
            ):
                chat = run_chat_turn_from_employment(
                    hiring["employment_record"],
                    message="케이스별 답변 말고 자연스럽게 대화해줘. 오늘 기분은 어때?",
                    output_path=output_path,
                    llm_mode="live",
                    llm_model="gpt-test",
                    learn_from_chat=True,
                )
            saved_chat = output_path.read_text(encoding="utf-8")
            target_root = Path(hiring["employment_record"]).parent
            ledger = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))

        self.assertEqual(chat["reply_generation_mode"], "deterministic_local_fallback")
        self.assertEqual(chat["conversation_intent"], "casual_conversation")
        self.assertEqual(chat["chat_runtime_status_card"]["schema"], "paideia-chat-runtime-status-card/v1")
        self.assertEqual(chat["chat_runtime_status_card"]["status"], "completed_with_fallback")
        self.assertTrue(chat["chat_runtime_status_card"]["fallback"]["used"])
        self.assertFalse(chat["chat_runtime_status_card"]["fallback"]["presented_as_live"])
        self.assertEqual(chat["chat_runtime_status_card"]["live_attempt"]["status"], "unavailable")
        self.assertEqual(chat["chat_runtime_status_card"]["learning"]["decision"], "quarantined")
        self.assertEqual(chat["chat_learning_update"]["decision"], "quarantined")
        self.assertEqual(ledger["quarantined_experiences"][-1]["source"], "chat_turn")
        serialized_chat = json.dumps(chat, ensure_ascii=False)
        self.assertNotIn(secret, serialized_chat)
        self.assertNotIn(secret, saved_chat)
        self.assertIn("[REDACTED_SECRET]", serialized_chat)
        self.assertIn("[REDACTED_SECRET]", saved_chat)

    def test_live_chat_provider_not_configured_fails_closed_without_fallback_learning(self) -> None:
        import os

        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            blueprint = create_agent_training_blueprint(
                owner="보스",
                request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
                talent_name="grham-주니어",
                gender="남자",
                domain="securities_research",
                role_model_id="graham_value_investing",
                agent_surface="cli-console",
            )
            with tempfile.TemporaryDirectory() as tmp:
                run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
                artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
                hiring = hire_installed_agent(
                    artifacts["installed_agent_manifest"],
                    employer="보스",
                    role="증권 리서치 AI 박사",
                    llm_engine="openrouter_api",
                    llm_model="openai/gpt-test",
                    record_name="employment_record_openrouter.json",
                )
                target_root = Path(hiring["employment_record"]).parent
                ledger_before = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))
                chat = run_chat_turn_from_employment(
                    hiring["employment_record"],
                    message="지금 live provider로 자연스럽게 대화해줘.",
                    output_path=Path(tmp) / "live_missing_chat.json",
                    llm_mode="live",
                    llm_model="openai/gpt-test",
                    learn_from_chat=True,
                )
                ledger_after = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))
        finally:
            if old_key is not None:
                os.environ["OPENROUTER_API_KEY"] = old_key

        self.assertEqual(chat["chat_status"], "needs_configuration")
        self.assertEqual(chat["reply_generation_mode"], "skipped_provider_not_ready")
        self.assertEqual(chat["llm_runtime_result"]["status"], "skipped_provider_not_ready")
        self.assertEqual(chat["llm_provider_preflight"]["status"], "needs_configuration")
        self.assertEqual(chat["chat_runtime_status_card"]["schema"], "paideia-chat-runtime-status-card/v1")
        self.assertEqual(chat["chat_runtime_status_card"]["status"], "needs_configuration")
        self.assertFalse(chat["chat_runtime_status_card"]["fallback"]["used"])
        self.assertFalse(chat["chat_runtime_status_card"]["fallback"]["presented_as_live"])
        self.assertEqual(chat["chat_runtime_status_card"]["learning"]["decision"], "skipped_provider_not_ready")
        self.assertIn("live provider 설정이 필요", chat["chat_runtime_status_card"]["user_visible_summary"]["ko"])
        self.assertEqual(
            chat["memory_lifecycle_status_card"]["schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(chat["memory_lifecycle_status_card"]["learning"]["decision"], "skipped_provider_not_ready")
        self.assertFalse(chat["memory_lifecycle_status_card"]["learning"]["ledger_write_performed"])
        self.assertTrue(chat["memory_lifecycle_status_card"]["active_context"]["quarantined_excluded"])
        self.assertNotIn("fallback_used", chat["llm_runtime_result"])
        self.assertEqual(chat["chat_learning_update"]["decision"], "skipped_provider_not_ready")
        self.assertFalse(chat["chat_learning_update"]["ledger_write_performed"])
        self.assertEqual(
            len(ledger_after.get("promoted_experiences", [])),
            len(ledger_before.get("promoted_experiences", [])),
        )
        self.assertEqual(
            len(ledger_after.get("quarantined_experiences", [])),
            len(ledger_before.get("quarantined_experiences", [])),
        )

    def test_auto_chat_provider_not_configured_fallback_quarantines_learning(self) -> None:
        import os

        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            blueprint = create_agent_training_blueprint(
                owner="보스",
                request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
                talent_name="grham-주니어",
                gender="남자",
                domain="securities_research",
                role_model_id="graham_value_investing",
                agent_surface="cli-console",
            )
            with tempfile.TemporaryDirectory() as tmp:
                run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
                artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
                hiring = hire_installed_agent(
                    artifacts["installed_agent_manifest"],
                    employer="보스",
                    role="증권 리서치 AI 박사",
                    llm_engine="openrouter_api",
                    llm_model="openai/gpt-test",
                    record_name="employment_record_openrouter.json",
                )
                target_root = Path(hiring["employment_record"]).parent
                chat = run_chat_turn_from_employment(
                    hiring["employment_record"],
                    message="auto mode로 자연스럽게 대화해줘.",
                    output_path=Path(tmp) / "auto_missing_chat.json",
                    llm_mode="auto",
                    llm_model="openai/gpt-test",
                    learn_from_chat=True,
                )
                ledger = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))
        finally:
            if old_key is not None:
                os.environ["OPENROUTER_API_KEY"] = old_key

        self.assertEqual(chat["chat_status"], "completed")
        self.assertEqual(chat["reply_generation_mode"], "deterministic_local_fallback")
        self.assertTrue(chat["llm_runtime_result"]["fallback_used"])
        self.assertEqual(chat["llm_provider_preflight"]["status"], "needs_configuration")
        self.assertEqual(chat["chat_runtime_status_card"]["schema"], "paideia-chat-runtime-status-card/v1")
        self.assertEqual(chat["chat_runtime_status_card"]["status"], "completed_with_fallback")
        self.assertTrue(chat["chat_runtime_status_card"]["fallback"]["used"])
        self.assertFalse(chat["chat_runtime_status_card"]["fallback"]["presented_as_live"])
        self.assertEqual(chat["chat_runtime_status_card"]["provider_preflight"]["status"], "needs_configuration")
        self.assertEqual(chat["chat_runtime_status_card"]["learning"]["decision"], "quarantined")
        self.assertIn("deterministic fallback", chat["chat_runtime_status_card"]["user_visible_summary"]["en"])
        self.assertEqual(
            chat["memory_lifecycle_status_card"]["schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(chat["memory_lifecycle_status_card"]["learning"]["decision"], "quarantined")
        self.assertTrue(chat["memory_lifecycle_status_card"]["learning"]["ledger_write_performed"])
        self.assertTrue(chat["memory_lifecycle_status_card"]["active_context"]["quarantined_excluded"])
        self.assertEqual(chat["chat_learning_update"]["decision"], "quarantined")
        self.assertEqual(ledger["quarantined_experiences"][-1]["source"], "chat_turn")

    def test_chat_turn_repairs_after_boss_correction(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.memory_substrate import run_chat_turn_from_employment
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            chat = run_chat_turn_from_employment(
                hiring["employment_record"],
                message="이건 성장과정에 관한 얘기가 아니잖아?",
                output_path=Path(tmp) / "repair.json",
            )

        self.assertEqual(chat["conversation_intent"], "correction_feedback")
        self.assertIn("의도를 잘못 잡았습니다", chat["assistant_answer"])
        self.assertIn("성장과정", chat["assistant_answer"])
        self.assertEqual(chat["active_operator"], "conversation_interface.error_repair")

    def test_cli_chat_hired_agent_writes_chat_context(self) -> None:
        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        blueprint = create_agent_training_blueprint(
            owner="보스",
            request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
            talent_name="grham-쥬니어",
            gender="남자",
            domain="securities_research",
            role_model_id="graham_value_investing",
            agent_surface="cli-console",
        )

        with tempfile.TemporaryDirectory() as tmp:
            run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
            artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
            hiring = hire_installed_agent(
                artifacts["installed_agent_manifest"],
                employer="보스",
                role="증권 리서치 AI 박사",
                llm_engine="openai_chatgpt_codex",
                record_name="employment_record_codex.json",
            )
            output = Path(tmp) / "cli_chat.json"
            exit_code = cli_main(
                [
                    "chat-hired-agent",
                    "--employment-record",
                    str(hiring["employment_record"]),
                    "--message",
                    "보고서 작성을 시작하기 전에 어떤 근거를 모아야 합니까?",
                    "--output",
                    str(output),
                ]
            )
            chat = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(chat["chat_context"]["llm_contract"]["role"], "application_language_engine_only")
        self.assertTrue(chat["chat_context"]["active_memory_route"]["operator_candidates"])

    def test_cli_chat_hired_agent_live_provider_not_configured_writes_needs_configuration(self) -> None:
        import os

        from ai22b.talent_foundry.blueprint import create_agent_training_blueprint
        from ai22b.talent_foundry.cli import main as cli_main
        from ai22b.talent_foundry.registry import hire_installed_agent
        from ai22b.talent_foundry.training_run import materialize_training_blueprint

        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            blueprint = create_agent_training_blueprint(
                owner="보스",
                request="Graham 학습 경로를 재현하는 별도 샘플 AI를 만든다.",
                talent_name="grham-주니어",
                gender="남자",
                domain="securities_research",
                role_model_id="graham_value_investing",
                agent_surface="cli-console",
            )
            with tempfile.TemporaryDirectory() as tmp:
                run = materialize_training_blueprint(blueprint, output_dir=Path(tmp) / "grham_junior")
                artifacts = {key: Path(value) for key, value in run["artifacts"].items()}
                hiring = hire_installed_agent(
                    artifacts["installed_agent_manifest"],
                    employer="보스",
                    role="증권 리서치 AI 박사",
                    llm_engine="openrouter_api",
                    llm_model="openai/gpt-test",
                    record_name="employment_record_openrouter.json",
                )
                output = Path(tmp) / "cli_live_missing_chat.json"
                exit_code = cli_main(
                    [
                        "chat-hired-agent",
                        "--employment-record",
                        str(hiring["employment_record"]),
                        "--message",
                        "live provider로 자연스럽게 대화해줘.",
                        "--output",
                        str(output),
                        "--live-llm",
                        "--llm-model",
                        "openai/gpt-test",
                        "--learn-from-chat",
                    ]
                )
                chat = json.loads(output.read_text(encoding="utf-8"))
        finally:
            if old_key is not None:
                os.environ["OPENROUTER_API_KEY"] = old_key

        self.assertEqual(exit_code, 0)
        self.assertEqual(chat["chat_status"], "needs_configuration")
        self.assertEqual(chat["reply_generation_mode"], "skipped_provider_not_ready")
        self.assertEqual(chat["llm_provider_preflight"]["status"], "needs_configuration")
        self.assertEqual(chat["chat_learning_update"]["decision"], "skipped_provider_not_ready")

    def test_codex_oauth_backend_success_uses_paideia_owned_adapter_boundary(self) -> None:
        from ai22b.talent_foundry import memory_substrate

        output = json.dumps(
            {
                "assistant_reply": "Codex OAuth path replied.",
                "reviewable_reasoning_summary": [{"step": "adapter", "summary": "fake adapter completed"}],
                "learning_candidate": {
                    "lesson": "adapter calls can be tested without Hermes network access",
                    "reusable_principle": "mock the Paideia-owned adapter boundary",
                    "memory_tags": ["codex_oauth"],
                    "confidence": 0.7,
                },
            },
            ensure_ascii=False,
        )

        with patch.dict(os.environ, {"PAIDEIA_CHAT_BACKEND": "codex_oauth"}, clear=False), patch.object(
            memory_substrate,
            "_resolve_hermes_agent_root",
            return_value=Path("hermes-agent"),
        ), patch.object(
            memory_substrate,
            "resolve_codex_oauth_credentials",
            return_value={"authenticated": True, "provider": "openai-codex"},
        ), patch.object(
            memory_substrate,
            "call_codex_oauth_llm",
            return_value=output,
        ) as fake_call:
            result = memory_substrate._call_openai_responses_chat(
                chat_context=self._minimal_live_chat_context(),
                model="gpt-test",
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["engine"], "chatgpt_codex_oauth")
        self.assertEqual(result["provider"], "openai-codex")
        self.assertEqual(result["assistant_reply"], "Codex OAuth path replied.")
        self.assertFalse(result["raw_output_saved"])
        self.assertFalse(result["data_policy"]["send_private_training_files"])
        self.assertTrue(fake_call.called)

    def test_codex_oauth_adapter_restores_import_boundary(self) -> None:
        from ai22b.talent_foundry.codex_oauth_adapter import (
            HERMES_ROOT_REVIEW_MARKER,
            resolve_codex_oauth_credentials,
        )

        module_names = ["hermes_cli", "hermes_cli.auth", "agent", "agent.auxiliary_client"]
        saved_modules = {name: sys.modules.get(name) for name in module_names if name in sys.modules}
        for name in module_names:
            sys.modules.pop(name, None)
        preexisting_agent_module = types.ModuleType("agent")
        preexisting_agent_module.marker = "preexisting-agent-module"
        sys.modules["agent"] = preexisting_agent_module
        original_path = list(sys.path)
        env_guard = patch.dict(
            os.environ,
            {
                "PAIDEIA_TRUSTED_HERMES_AGENT_ROOTS": "",
                "PAIDEIA_TRUST_HERMES_AGENT_ROOT": "0",
            },
            clear=False,
        )
        env_guard.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "hermes"
                (root / "hermes_cli").mkdir(parents=True)
                (root / "agent").mkdir()
                (root / "hermes_cli" / "__init__.py").write_text("", encoding="utf-8")
                (root / "agent" / "__init__.py").write_text("", encoding="utf-8")
                (root / "hermes_cli" / "auth.py").write_text(
                    "def resolve_codex_runtime_credentials(refresh_if_expiring=True):\n"
                    "    return {'api_key': 'fixture-token', 'provider': 'openai-codex', "
                    "'base_url': 'https://example.invalid', 'source': 'test', 'auth_mode': 'oauth'}\n",
                    encoding="utf-8",
                )
                (root / "agent" / "auxiliary_client.py").write_text(
                    "def call_llm(**kwargs):\n    raise RuntimeError('not used')\n",
                    encoding="utf-8",
                )
                (root / HERMES_ROOT_REVIEW_MARKER).write_text(
                    json.dumps(
                        {
                            "schema": "paideia-codex-oauth-adapter-review/v1",
                            "approved": True,
                            "provider": "openai-codex",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                result = resolve_codex_oauth_credentials(root, refresh_if_expiring=False)
                root_text = str(root.resolve())

                self.assertTrue(result["authenticated"])
                self.assertEqual(result["provider"], "openai-codex")
                self.assertEqual(sys.path, original_path)
                self.assertIs(sys.modules.get("agent"), preexisting_agent_module)
                self.assertNotIn(root_text, sys.path)
                self.assertNotIn("hermes_cli.auth", sys.modules)

                unreviewed_root = Path(tmp) / "unreviewed-hermes"
                (unreviewed_root / "hermes_cli").mkdir(parents=True)
                (unreviewed_root / "agent").mkdir()
                (unreviewed_root / "hermes_cli" / "__init__.py").write_text("", encoding="utf-8")
                (unreviewed_root / "agent" / "__init__.py").write_text("", encoding="utf-8")
                (unreviewed_root / "hermes_cli" / "auth.py").write_text(
                    "def resolve_codex_runtime_credentials(refresh_if_expiring=True):\n"
                    "    return {'api_key': 'fixture-token'}\n",
                    encoding="utf-8",
                )
                (unreviewed_root / "agent" / "auxiliary_client.py").write_text(
                    "def call_llm(**kwargs):\n    raise RuntimeError('not used')\n",
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    resolve_codex_oauth_credentials(unreviewed_root, refresh_if_expiring=False)

                with self.assertRaises(ValueError):
                    resolve_codex_oauth_credentials(Path(tmp) / "not-hermes", refresh_if_expiring=False)
                self.assertEqual(sys.path, original_path)
        finally:
            for name in module_names:
                sys.modules.pop(name, None)
            sys.modules.update(saved_modules)
            env_guard.stop()

    def test_codex_oauth_auth_failure_redacts_secret_text(self) -> None:
        from ai22b.talent_foundry import memory_substrate

        secret = "sk-fixture_secret_value_1234567890"

        with patch.dict(
            os.environ,
            {
                "PAIDEIA_CHAT_BACKEND": "codex_oauth",
                "OPENAI_API_KEY": secret,
            },
            clear=False,
        ), patch.object(
            memory_substrate,
            "_resolve_hermes_agent_root",
            return_value=Path("hermes-agent"),
        ), patch.object(
            memory_substrate,
            "resolve_codex_oauth_credentials",
            side_effect=RuntimeError(f"Authorization: Bearer {secret}; token={secret}"),
        ):
            result = memory_substrate._call_openai_responses_chat(
                chat_context=self._minimal_live_chat_context(),
                model="gpt-test",
            )

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "codex_oauth_auth_failed")
        self.assertNotIn(secret, serialized)
        self.assertIn("[REDACTED_SECRET]", serialized)

    def test_auto_backend_returns_codex_failure_when_api_fallback_is_disabled(self) -> None:
        from ai22b.talent_foundry import memory_substrate

        codex_result = {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": "chatgpt_codex_oauth",
            "provider": "openai-codex",
            "status": "unavailable",
            "reason": "codex_oauth_auth_failed",
            "model": "gpt-test",
        }

        with patch.dict(
            os.environ,
            {
                "PAIDEIA_CHAT_BACKEND": "auto",
                "PAIDEIA_ALLOW_OPENAI_API_FALLBACK": "0",
            },
            clear=False,
        ), patch.object(memory_substrate, "_call_codex_oauth_chat", return_value=codex_result):
            result = memory_substrate._call_openai_responses_chat(
                chat_context=self._minimal_live_chat_context(),
                model="gpt-test",
            )

        self.assertEqual(result, codex_result)

    def test_auto_backend_falls_back_to_openai_api_only_when_allowed(self) -> None:
        from ai22b.talent_foundry import memory_substrate

        codex_result = {
            "schema": "ai-talent-live-llm-result/v1",
            "engine": "chatgpt_codex_oauth",
            "provider": "openai-codex",
            "status": "unavailable",
            "reason": "codex_oauth_auth_failed",
            "model": "gpt-test",
        }

        with patch.dict(
            os.environ,
            {
                "PAIDEIA_CHAT_BACKEND": "auto",
                "PAIDEIA_ALLOW_OPENAI_API_FALLBACK": "1",
            },
            clear=False,
        ), patch.object(memory_substrate, "_call_codex_oauth_chat", return_value=codex_result):
            old_key = os.environ.pop("OPENAI_API_KEY", None)
            try:
                result = memory_substrate._call_openai_responses_chat(
                    chat_context=self._minimal_live_chat_context(),
                    model="gpt-test",
                )
            finally:
                if old_key is not None:
                    os.environ["OPENAI_API_KEY"] = old_key

        self.assertEqual(result["engine"], "openai_responses_api")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "OPENAI_API_KEY_not_set")

    def test_openai_chatgpt_codex_preflight_uses_codex_oauth_without_api_key(self) -> None:
        from ai22b.talent_foundry.llm_runtime import build_llm_provider_preflight, build_llm_runtime_config

        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            runtime_config = build_llm_runtime_config(engine="openai_chatgpt_codex", model="gpt-test")
            with patch.dict(os.environ, {"PAIDEIA_CHAT_BACKEND": "codex_oauth"}, clear=False):
                preflight = build_llm_provider_preflight(
                    runtime_config,
                    llm_mode="live",
                    llm_model="gpt-test",
                )
            with patch.dict(os.environ, {"PAIDEIA_CHAT_BACKEND": "openai_api"}, clear=False):
                api_preflight = build_llm_provider_preflight(
                    runtime_config,
                    llm_mode="live",
                    llm_model="gpt-test",
                )
        finally:
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key

        self.assertEqual(preflight["status"], "ready_for_explicit_live_attempt")
        self.assertFalse(preflight["blocking_checks"])
        self.assertEqual(api_preflight["status"], "needs_configuration")
        self.assertEqual(api_preflight["blocking_checks"][0]["id"], "credential_environment")


if __name__ == "__main__":
    unittest.main()
