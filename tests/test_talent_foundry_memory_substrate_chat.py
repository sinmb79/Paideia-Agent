from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TalentFoundryMemorySubstrateChatTests(unittest.TestCase):
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

        self.assertEqual(substrate["schema"], "ai-talent-memory-substrate/v1")
        self.assertEqual(substrate["agent"]["name"], "grham-쥬니어")
        self.assertGreater(substrate["source_counts"]["reasoning_kibo_entries"], 20)
        self.assertGreaterEqual(substrate["source_counts"]["language_development_stages"], 8)
        self.assertEqual(substrate["source_counts"]["life_trace_events"], 252)
        self.assertGreaterEqual(substrate["source_counts"]["developmental_ecology_layers"], 7)
        self.assertGreaterEqual(substrate["source_counts"]["growth_profile_nodes"], 5)
        self.assertIn("procedural_operator_store", substrate["boards"])
        self.assertIn("conversation_development", substrate["boards"])
        self.assertIn("developmental_ecology", substrate["boards"])
        self.assertIn("life_trace", substrate["boards"])
        self.assertIn("growth_profile", substrate["boards"])
        self.assertEqual(bundle_manifest["included_artifacts"]["memory_substrate"], "memory_substrate.json")
        self.assertEqual(
            bundle_manifest["included_artifacts"]["language_development_program"],
            "language_development_program.json",
        )
        self.assertEqual(bundle_manifest["included_artifacts"]["developmental_ecology"], "developmental_ecology.json")
        self.assertEqual(bundle_manifest["included_artifacts"]["life_trace"], "life_trace.jsonl")
        self.assertEqual(bundle_manifest["included_artifacts"]["growth_profile"], "growth_profile.json")
        self.assertIn("memory_substrate", installed_manifest["entrypoints"])
        self.assertIn("language_development_program", installed_manifest["entrypoints"])
        self.assertIn("developmental_ecology", installed_manifest["entrypoints"])
        self.assertIn("life_trace", installed_manifest["entrypoints"])
        self.assertIn("growth_profile", installed_manifest["entrypoints"])
        self.assertEqual(employment_record["agent"]["name"], "grham-쥬니어")
        self.assertIn("last_chat", employment_record["entrypoints"])
        self.assertIn("developmental_ecology", employment_record["entrypoints"])
        self.assertIn("life_trace", employment_record["entrypoints"])
        self.assertIn("growth_profile", employment_record["entrypoints"])
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
        self.assertEqual(agent_id_payload["schema"], "ai-talent-agent-id-card-payload/v1")
        self.assertEqual(agent_identity_envelope["version"], "ail.v1")
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

    def test_live_llm_chat_uses_local_context_and_promotes_chat_learning(self) -> None:
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
            target_root = Path(hiring["employment_record"]).parent
            ledger = json.loads((target_root / "learning_ledger.json").read_text(encoding="utf-8"))
            substrate = json.loads((target_root / "memory_substrate.json").read_text(encoding="utf-8"))

        self.assertEqual(captured["model"], "gpt-test")
        context = captured["context"]
        self.assertEqual(context["agent"]["name"], "grham-쥬니어")
        self.assertIn("identity_record", context)
        self.assertIn("learning_profile", context)
        self.assertEqual(chat["reply_generation_mode"], "live_openai_responses")
        self.assertEqual(chat["active_operator"], "llm.dynamic_context_conversation")
        self.assertIn("그때그때 맥락을 해석", chat["assistant_answer"])
        self.assertTrue(any(item["action"] == "live_llm_attempt" for item in chat["chat_execution_trace"]))
        self.assertEqual(chat["chat_learning_update"]["decision"], "promoted")
        self.assertEqual(chat["chat_execution_trace"][-2]["action"], "chat_learning_update")
        self.assertEqual(chat["chat_execution_trace"][-1]["action"], "chat_runtime_status_card_recorded")
        self.assertEqual(chat["chat_runtime_status_card"]["status"], "completed_live")
        self.assertEqual(chat["chat_runtime_status_card"]["learning"]["decision"], "promoted")
        self.assertEqual(
            chat["memory_lifecycle_status_card"]["schema"],
            "paideia-memory-lifecycle-status-card/v1",
        )
        self.assertEqual(chat["memory_lifecycle_status_card"]["source"], "chat_turn")
        self.assertEqual(chat["memory_lifecycle_status_card"]["learning"]["decision"], "promoted")
        self.assertTrue(chat["memory_lifecycle_status_card"]["active_context"]["quarantined_excluded"])
        self.assertEqual(
            chat["chat_runtime_status_card"]["memory_lifecycle"]["status"],
            chat["memory_lifecycle_status_card"]["status"],
        )
        self.assertEqual(ledger["promoted_experiences"][-1]["source"], "chat_turn")
        self.assertIn("conversation_context_learning", ledger["promoted_experiences"][-1]["promoted_skills"])
        self.assertTrue(
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
                )

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
        self.assertEqual(captured["policy"]["response_format"], "json_object")
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


if __name__ == "__main__":
    unittest.main()
