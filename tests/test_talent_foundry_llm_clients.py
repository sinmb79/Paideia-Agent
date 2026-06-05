from __future__ import annotations

import json
import os
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
