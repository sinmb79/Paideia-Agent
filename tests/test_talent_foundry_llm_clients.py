from __future__ import annotations

import json
import os
import sys
import types
import unittest
from unittest.mock import patch


class FakeHttpResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


def _headers(request) -> dict[str, str]:
    return {key.casefold(): value for key, value in request.header_items()}


class TalentFoundryLlmClientTests(unittest.TestCase):
    def test_llm_result_public_artifact_contract_overrides_unsafe_fields(self) -> None:
        from ai22b.talent_foundry.llm_clients import LLMResult

        result = LLMResult(
            schema="paideia-llm-client-result/v1",
            engine="fixture",
            status="completed",
            text="ok",
            fields={
                "raw_output_saved": True,
                "private_reasoning_trace": "full_chain_of_thought",
                "provider_packet": {"private_reasoning_trace": "hidden details"},
            },
        ).to_public_artifact()

        self.assertFalse(result["raw_output_saved"])
        self.assertEqual(result["private_reasoning_trace"], "do_not_store")
        self.assertEqual(result["provider_packet"], {})

    def test_private_reasoning_policy_marker_is_not_counted_as_hidden_trace(self) -> None:
        from ai22b.talent_foundry.llm_clients import count_private_reasoning_fields

        safe = {"private_reasoning_trace": "do_not_store"}
        unsafe = {"private_reasoning_trace": "full chain-of-thought text"}

        self.assertEqual(count_private_reasoning_fields(safe), 0)
        self.assertEqual(count_private_reasoning_fields(unsafe), 1)

    def test_public_reasoning_trace_policy_normalizes_or_rejects_builder_values(self) -> None:
        from ai22b.talent_foundry.dossier import public_reasoning_trace_policy

        self.assertEqual(public_reasoning_trace_policy("not_stored"), "do_not_store")
        self.assertEqual(public_reasoning_trace_policy(None), "do_not_store")
        with self.assertRaises(ValueError):
            public_reasoning_trace_policy("full_chain_of_thought")
        with self.assertRaises(ValueError):
            public_reasoning_trace_policy({"private_reasoning_trace": "full_chain_of_thought"})

    def test_llm_adapter_contract_doctor_public_safe_no_network(self) -> None:
        from ai22b.talent_foundry.llm_adapter_contracts import run_llm_adapter_contracts

        report = run_llm_adapter_contracts()
        checks = {item["id"]: item for item in report["checks"]}

        self.assertEqual(report["schema"], "paideia-llm-adapter-contracts/v1")
        self.assertTrue(report["passed"])
        self.assertEqual(report["status"], "passed")
        self.assertGreaterEqual(report["summary"]["direct_adapter_count"], 9)
        self.assertEqual(report["summary"]["failed_count"], 0)
        self.assertFalse(report["public_safe"]["network_call_performed"])
        self.assertFalse(report["public_safe"]["localhost_call_performed"])
        self.assertFalse(report["public_safe"]["external_provider_called"])
        self.assertFalse(report["public_safe"]["secret_values_exported"])
        self.assertFalse(report["public_safe"]["raw_provider_payload_saved"])
        self.assertEqual(report["public_safe"]["private_reasoning_trace"], "do_not_store")
        self.assertTrue(checks["client_factory_contract"]["passed"])
        self.assertTrue(checks["deterministic_generate_contract"]["passed"])
        self.assertTrue(checks["external_api_missing_credentials_fail_closed"]["passed"])
        self.assertTrue(checks["localhost_adapters_explicit_live_contract"]["passed"])
        self.assertTrue(checks["local_model_missing_path_fail_closed"]["passed"])
        external_cases = {
            item["engine"]: item
            for item in checks["external_api_missing_credentials_fail_closed"]["cases"]
        }
        self.assertIn("openrouter_api", external_cases)
        self.assertEqual(external_cases["openrouter_api"]["status"], "unavailable")
        self.assertFalse(external_cases["openrouter_api"]["network_call_attempted"])

    def test_cli_doctor_llm_adapters_writes_report(self) -> None:
        import tempfile
        from pathlib import Path

        from ai22b.talent_foundry.cli import main as cli_main

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "llm_adapter_contracts.json"
            exit_code = cli_main(
                [
                    "doctor-llm-adapters",
                    "--strict",
                    "--output",
                    str(output_path),
                ]
            )
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["schema"], "paideia-llm-adapter-contracts/v1")
        self.assertTrue(report["passed"])
        self.assertFalse(report["public_safe"]["network_call_performed"])

    def test_openai_responses_client_calls_sdk_success_without_exporting_secret_or_payload(self) -> None:
        from ai22b.talent_foundry.llm_clients import OpenAIResponsesClient

        calls: list[dict] = []
        secret = "fixture_openai_token_value_12345"

        class FakeUsage:
            def __str__(self) -> str:
                return "input_tokens=9 output_tokens=10"

        class FakeResponse:
            id = "openai-response-1"
            output_text = f"openai adapter ok {secret}"
            usage = FakeUsage()

        class FakeResponses:
            def create(self, **kwargs):
                calls.append(kwargs)
                return FakeResponse()

        class FakeOpenAI:
            def __init__(self) -> None:
                self.responses = FakeResponses()

        fake_openai = types.ModuleType("openai")
        fake_openai.OpenAI = FakeOpenAI

        messages = [
            {"role": "system", "content": "system note"},
            {"role": "user", "content": "hello"},
        ]
        tools = [{"name": "evidence_packet", "description": "write a reviewable evidence packet"}]
        policy = {"mode": "reviewable_summary_only"}
        with patch.dict(os.environ, {"OPENAI_API_KEY": secret}, clear=False), patch.dict(
            sys.modules,
            {"openai": fake_openai},
        ):
            result = OpenAIResponsesClient(model="gpt-test").generate(messages, tools=tools, policy=policy)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["engine"], "openai_responses_api")
        self.assertEqual(result["model"], "gpt-test")
        self.assertEqual(result["response_id"], "openai-response-1")
        self.assertEqual(result["network_access"], "external_api_selected_data_minimized")
        self.assertFalse(result["raw_output_saved"])
        self.assertIn("[REDACTED_SECRET]", result["text"])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(secret, serialized)

        self.assertEqual(calls[0]["model"], "gpt-test")
        self.assertEqual(calls[0]["instructions"], "system note")
        self.assertEqual(calls[0]["max_output_tokens"], 900)
        payload = json.loads(calls[0]["input"])
        self.assertEqual(payload["messages"], messages)
        self.assertEqual(payload["tools"], tools)
        self.assertEqual(payload["policy"], policy)
        self.assertIn("reviewable_reasoning_summary", payload["output_contract"])

    def test_external_api_clients_parse_successful_http_responses_without_storing_provider_payloads(self) -> None:
        from ai22b.talent_foundry.llm_clients import (
            AnthropicMessagesClient,
            GeminiGenerateContentClient,
            OpenAICompatibleChatClient,
        )

        calls: list[dict] = []
        responses = [
            {
                "id": "anthropic-response-1",
                "content": [{"type": "text", "text": "anthropic adapter ok"}],
                "usage": {"input_tokens": 3, "output_tokens": 4},
            },
            {
                "candidates": [{"content": {"parts": [{"text": "gemini adapter ok"}]}}],
                "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 6},
            },
            {
                "id": "mistral-response-1",
                "choices": [{"message": {"content": "mistral adapter ok"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 8},
            },
        ]

        def fake_urlopen(request, timeout=60):
            calls.append(
                {
                    "url": request.full_url,
                    "headers": _headers(request),
                    "body": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return FakeHttpResponse(responses[len(calls) - 1])

        env = {
            "ANTHROPIC_API_KEY": "fixture-anthropic-token-12345",
            "GEMINI_API_KEY": "fixture-gemini-token-12345",
            "MISTRAL_API_KEY": "fixture-mistral-token-12345",
        }
        with patch.dict(os.environ, env, clear=False), patch("urllib.request.urlopen", side_effect=fake_urlopen):
            anthropic = AnthropicMessagesClient(model="claude-test").generate(
                [{"role": "system", "content": "system note"}, {"role": "user", "content": "hello"}]
            )
            gemini = GeminiGenerateContentClient(model="gemini-test").generate(
                [{"role": "system", "content": "system note"}, {"role": "user", "content": "hello"}]
            )
            mistral = OpenAICompatibleChatClient(
                engine="mistral_api",
                model="mistral-test",
                endpoint="https://mistral.example.invalid/v1/chat/completions",
                api_key_env="MISTRAL_API_KEY",
            ).generate([{"role": "user", "content": "hello"}])

        self.assertEqual(anthropic["status"], "completed")
        self.assertEqual(anthropic["text"], "anthropic adapter ok")
        self.assertEqual(anthropic["response_id"], "anthropic-response-1")
        self.assertFalse(anthropic["raw_output_saved"])
        self.assertEqual(calls[0]["body"]["model"], "claude-test")
        self.assertEqual(calls[0]["headers"]["x-api-key"], env["ANTHROPIC_API_KEY"])

        self.assertEqual(gemini["status"], "completed")
        self.assertEqual(gemini["text"], "gemini adapter ok")
        self.assertFalse(gemini["raw_output_saved"])
        self.assertIn("models/gemini-test:generateContent", calls[1]["url"])
        self.assertIn("systemInstruction", calls[1]["body"])

        self.assertEqual(mistral["status"], "completed")
        self.assertEqual(mistral["text"], "mistral adapter ok")
        self.assertEqual(mistral["response_id"], "mistral-response-1")
        self.assertEqual(calls[2]["body"]["model"], "mistral-test")
        self.assertEqual(calls[2]["headers"]["authorization"], f"Bearer {env['MISTRAL_API_KEY']}")

        serialized = json.dumps({"anthropic": anthropic, "gemini": gemini, "mistral": mistral}, ensure_ascii=False)
        for secret in env.values():
            self.assertNotIn(secret, serialized)

    def test_local_http_clients_parse_successful_ollama_and_lm_studio_responses(self) -> None:
        from ai22b.talent_foundry.llm_clients import LMStudioClient, OllamaClient

        calls: list[dict] = []
        responses = [
            {"response": "ollama adapter ok"},
            {"choices": [{"message": {"content": "lm studio adapter ok"}}]},
        ]

        def fake_urlopen(request, timeout=60):
            calls.append(
                {
                    "url": request.full_url,
                    "headers": _headers(request),
                    "body": json.loads(request.data.decode("utf-8")),
                    "timeout": timeout,
                }
            )
            return FakeHttpResponse(responses[len(calls) - 1])

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            ollama = OllamaClient(model="llama-test", endpoint="http://localhost:11434").generate(
                [{"role": "user", "content": "hello"}]
            )
            lm_studio = LMStudioClient(
                model="local-model-test",
                endpoint="http://localhost:1234/v1/chat/completions",
            ).generate([{"role": "user", "content": "hello"}])

        self.assertEqual(ollama["status"], "completed")
        self.assertEqual(ollama["text"], "ollama adapter ok")
        self.assertEqual(ollama["network_access"], "localhost_only")
        self.assertEqual(calls[0]["url"], "http://localhost:11434/api/generate")
        self.assertEqual(calls[0]["body"]["model"], "llama-test")
        self.assertFalse(calls[0]["body"]["stream"])

        self.assertEqual(lm_studio["status"], "completed")
        self.assertEqual(lm_studio["text"], "lm studio adapter ok")
        self.assertEqual(lm_studio["network_access"], "localhost_only")
        self.assertEqual(calls[1]["url"], "http://localhost:1234/v1/chat/completions")
        self.assertEqual(calls[1]["body"]["model"], "local-model-test")
        self.assertFalse(calls[1]["body"]["stream"])


if __name__ == "__main__":
    unittest.main()
