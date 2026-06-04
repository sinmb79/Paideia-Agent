from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


LLM_CLIENT_RESULT_SCHEMA = "paideia-llm-client-result/v1"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
DEFAULT_LM_STUDIO_ENDPOINT = "http://localhost:1234/v1/chat/completions"


class LLMClient(Protocol):
    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a language result without becoming the agent identity."""


def build_runtime_messages(*, manifest: dict[str, Any], task: str, policy_context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    agent = manifest.get("agent", {})
    memory = manifest.get("memory_profile", {})
    principles = memory.get("procedural_principles", [])
    themes = memory.get("semantic_themes", [])
    policy = policy_context or {}
    return [
        {
            "role": "system",
            "content": (
                "You are the language and planning engine for a local Paideia Agent. "
                "The agent identity comes from local records, not from this model. "
                "Do not expose hidden chain-of-thought. Return a concise answer, a reviewable reasoning summary, "
                "and suggested next actions."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "agent": {
                        "name": agent.get("name"),
                        "role": agent.get("role"),
                        "major_goal": agent.get("major_goal"),
                    },
                    "task": task,
                    "memory": {
                        "procedural_principles": principles[:8],
                        "semantic_themes": themes[:8],
                        "chain_of_thought_policy": memory.get("chain_of_thought_policy", "do_not_store_private_trace"),
                    },
                    "policy_context": policy,
                },
                ensure_ascii=False,
            ),
        },
    ]


def _messages_text(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in messages)


def _ok(engine: str, text: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema": LLM_CLIENT_RESULT_SCHEMA,
        "engine": engine,
        "status": "completed",
        "text": text.strip(),
        "identity_policy": "application_engine_not_identity",
        "raw_output_saved": False,
        **fields,
    }


def _unavailable(engine: str, reason: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema": LLM_CLIENT_RESULT_SCHEMA,
        "engine": engine,
        "status": "unavailable",
        "reason": reason,
        "identity_policy": "application_engine_not_identity",
        **fields,
    }


@dataclass
class DeterministicClient:
    engine: str = "deterministic_local"

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task_payload = messages[-1].get("content", "{}") if messages else "{}"
        try:
            task = json.loads(task_payload).get("task", "requested task")
        except Exception:
            task = "requested task"
        tool_names = [str(item.get("name", item.get("id", "tool"))) for item in (tools or [])]
        text = (
            f"로컬 결정론 엔진은 '{task}' 요청을 정책, 기억 원칙, 허용 도구 순서로 처리했습니다. "
            f"사용 후보 도구는 {', '.join(tool_names) if tool_names else '없음'}입니다."
        )
        return _ok(self.engine, text, model=None, network_access="blocked")


@dataclass
class OpenAIResponsesClient:
    model: str = DEFAULT_OPENAI_MODEL

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not os.environ.get("OPENAI_API_KEY"):
            return _unavailable("openai_responses_api", "OPENAI_API_KEY_not_set", model=self.model)
        try:
            from openai import OpenAI
        except Exception as exc:
            return _unavailable(
                "openai_responses_api",
                "openai_sdk_import_failed",
                model=self.model,
                error_type=type(exc).__name__,
                error=str(exc)[:500],
            )

        payload = {
            "messages": messages,
            "tools": tools or [],
            "policy": policy or {},
            "output_contract": {
                "assistant_reply": "string",
                "reviewable_reasoning_summary": ["short evidence-facing steps"],
                "suggested_next_actions": ["safe next actions"],
            },
        }
        try:
            response = OpenAI().responses.create(
                model=self.model,
                instructions=messages[0].get("content", "") if messages else None,
                input=json.dumps(payload, ensure_ascii=False),
                max_output_tokens=900,
            )
        except Exception as exc:
            return _unavailable(
                "openai_responses_api",
                "openai_responses_call_failed",
                model=self.model,
                error_type=type(exc).__name__,
                error=str(exc)[:800],
            )
        return _ok(
            "openai_responses_api",
            str(getattr(response, "output_text", "") or ""),
            model=self.model,
            response_id=getattr(response, "id", None),
            usage=str(getattr(response, "usage", ""))[:500],
            network_access="external_api_selected_data_minimized",
        )


@dataclass
class OllamaClient:
    model: str = DEFAULT_OLLAMA_MODEL
    endpoint: str = DEFAULT_OLLAMA_ENDPOINT

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self.endpoint.rstrip("/") + "/api/generate"
        body = json.dumps(
            {
                "model": self.model,
                "prompt": _messages_text(messages),
                "stream": False,
                "options": {"temperature": 0},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return _unavailable(
                "ollama_local_http",
                "ollama_local_http_call_failed",
                model=self.model,
                endpoint=self.endpoint,
                error_type=type(exc).__name__,
                error=str(exc)[:500],
                network_access="localhost_only",
            )
        return _ok(
            "ollama_local_http",
            str(data.get("response", "")),
            model=self.model,
            endpoint=self.endpoint,
            network_access="localhost_only",
        )


@dataclass
class LMStudioClient:
    model: str = "local-model"
    endpoint: str = DEFAULT_LM_STUDIO_ENDPOINT

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0,
                "stream": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(self.endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as exc:
            return _unavailable(
                "lm_studio_local_http",
                "lm_studio_local_http_call_failed",
                model=self.model,
                endpoint=self.endpoint,
                error_type=type(exc).__name__,
                error=str(exc)[:500],
                network_access="localhost_only",
            )
        return _ok("lm_studio_local_http", str(text), model=self.model, endpoint=self.endpoint, network_access="localhost_only")


@dataclass
class TransformersLocalClient:
    model_path: str

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = Path(self.model_path)
        if not path.exists():
            return _unavailable("transformers_local", "local_model_path_not_found", model_path=str(path), local_files_only=True)
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
            model = AutoModelForCausalLM.from_pretrained(str(path), local_files_only=True)
            inputs = tokenizer(_messages_text(messages), return_tensors="pt")
            outputs = model.generate(**inputs, max_new_tokens=128, do_sample=False)
            text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as exc:
            return _unavailable(
                "transformers_local",
                "transformers_local_load_failed",
                model_path=str(path),
                error_type=type(exc).__name__,
                error=str(exc)[:500],
                local_files_only=True,
                network_access="blocked",
            )
        return _ok("transformers_local", text, model_path=str(path), local_files_only=True, network_access="blocked")


def build_llm_client(runtime_config: dict[str, Any], *, model_override: str | None = None) -> LLMClient:
    engine = runtime_config.get("engine", "deterministic_local")
    model = model_override or runtime_config.get("model")
    model_path = runtime_config.get("model_path")
    if engine == "openai_chatgpt_codex":
        return OpenAIResponsesClient(model=model or DEFAULT_OPENAI_MODEL)
    if engine == "ollama_local_http":
        return OllamaClient(model=model or DEFAULT_OLLAMA_MODEL, endpoint=model_path or DEFAULT_OLLAMA_ENDPOINT)
    if engine == "lm_studio_local_http":
        return LMStudioClient(model=model or "local-model", endpoint=model_path or DEFAULT_LM_STUDIO_ENDPOINT)
    if engine == "transformers_local":
        return TransformersLocalClient(model_path=str(model_path or ""))
    return DeterministicClient(engine=engine)
