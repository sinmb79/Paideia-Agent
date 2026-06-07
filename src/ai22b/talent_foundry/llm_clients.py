from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


LLM_CLIENT_RESULT_SCHEMA = "paideia-llm-client-result/v1"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
DEFAULT_LM_STUDIO_ENDPOINT = "http://localhost:1234/v1/chat/completions"
ANTHROPIC_MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"
GEMINI_GENERATE_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/{model}:generateContent"
MISTRAL_CHAT_COMPLETIONS_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
OPENROUTER_CHAT_COMPLETIONS_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
SECRET_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
)
SECRET_QUERY_RE = re.compile(r"([?&](?:key|api_key|access_token|auth_token|refresh_token|token)=)([^&\s]+)", re.I)
BEARER_RE = re.compile(r"((?:Authorization:\s*)?Bearer\s+)([A-Za-z0-9._\-]+)", re.I)
OPENAI_SECRET_RE = re.compile(r"sk-[A-Za-z0-9_-]{16,}")
PRIVATE_REASONING_KEY_MARKERS = (
    "chainofthought",
    "cottrace",
    "hiddenchain",
    "hiddenthought",
    "hiddentrace",
    "privatereasoning",
    "reasoningtrace",
)
SAFE_PRIVATE_REASONING_METADATA_KEYS = {
    "privatereasoningfieldsomitted",
    "privatereasoningfieldvaluesstored",
}
SAFE_PRIVATE_REASONING_POLICY_VALUES = {"do_not_store", "not_stored", "omitted"}


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


def _system_and_chat_messages(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts: list[str] = []
    chat: list[dict[str, str]] = []
    for item in messages:
        role = item.get("role", "user")
        content = str(item.get("content", ""))
        if role == "system":
            system_parts.append(content)
        else:
            chat.append({"role": role if role in {"user", "assistant"} else "user", "content": content})
    if not chat:
        chat.append({"role": "user", "content": _messages_text(messages)})
    return "\n\n".join(system_parts), chat


def _secret_values() -> list[str]:
    values = []
    for key in SECRET_ENV_KEYS:
        value = os.environ.get(key)
        if value and len(value) >= 8:
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


def _redact_secret_text(text: str) -> str:
    redacted = text
    for value in _secret_values():
        redacted = redacted.replace(value, "[REDACTED_SECRET]")
    redacted = SECRET_QUERY_RE.sub(r"\1[REDACTED_SECRET]", redacted)
    redacted = BEARER_RE.sub(r"\1[REDACTED_SECRET]", redacted)
    return OPENAI_SECRET_RE.sub("[REDACTED_SECRET]", redacted)


def _normalized_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(key).casefold())


def _is_private_reasoning_key(key: Any) -> bool:
    normalized = _normalized_key(key)
    if normalized in SAFE_PRIVATE_REASONING_METADATA_KEYS:
        return False
    return any(marker in normalized for marker in PRIVATE_REASONING_KEY_MARKERS)


def count_private_reasoning_fields(value: Any) -> int:
    if isinstance(value, dict):
        total = 0
        for key, item in value.items():
            if _is_private_reasoning_key(key):
                if str(item) in SAFE_PRIVATE_REASONING_POLICY_VALUES:
                    continue
                total += 1
                continue
            total += count_private_reasoning_fields(item)
        return total
    if isinstance(value, (list, tuple)):
        return sum(count_private_reasoning_fields(item) for item in value)
    return 0


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_secret_text(value)
    if isinstance(value, dict):
        return {
            str(key): _sanitize_value(item)
            for key, item in value.items()
            if not _is_private_reasoning_key(key)
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item) for item in value)
    return value


def sanitize_llm_result_packet(value: Any) -> Any:
    """Return an LLM result packet with provider credentials redacted."""

    return _sanitize_value(value)


def _ok(engine: str, text: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema": LLM_CLIENT_RESULT_SCHEMA,
        "engine": engine,
        "status": "completed",
        "text": _redact_secret_text(text.strip()),
        "identity_policy": "application_engine_not_identity",
        "raw_output_saved": False,
        "private_reasoning_trace": "do_not_store",
        **_sanitize_value(fields),
    }


def _unavailable(engine: str, reason: str, **fields: Any) -> dict[str, Any]:
    return {
        "schema": LLM_CLIENT_RESULT_SCHEMA,
        "engine": engine,
        "status": "unavailable",
        "reason": reason,
        "identity_policy": "application_engine_not_identity",
        "raw_output_saved": False,
        "private_reasoning_trace": "do_not_store",
        **_sanitize_value(fields),
    }


def _post_json(
    *,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 60,
) -> dict[str, Any]:
    safe_url = _validated_http_url(url)
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(safe_url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST")
    # URL scheme is validated before the request is built.
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def _validated_http_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Only http/https LLM endpoints are supported")
    return url


def _extract_openai_compatible_text(data: dict[str, Any]) -> str:
    return str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))


def _model_required(engine: str, model: str | None) -> dict[str, Any] | None:
    if model:
        return None
    return _unavailable(engine, "model_required_for_live_provider")


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
class AnthropicMessagesClient:
    model: str | None
    endpoint: str = ANTHROPIC_MESSAGES_ENDPOINT
    api_key_env: str = "ANTHROPIC_API_KEY"

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        required = _model_required("anthropic_claude_api", self.model)
        if required:
            return required
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            return _unavailable("anthropic_claude_api", f"{self.api_key_env}_not_set", model=self.model)
        system, chat = _system_and_chat_messages(messages)
        body = {
            "model": self.model,
            "max_tokens": 900,
            "messages": chat,
        }
        if system:
            body["system"] = system
        try:
            data = _post_json(
                url=self.endpoint,
                body=body,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
            text = "".join(str(block.get("text", "")) for block in data.get("content", []) if block.get("type") == "text")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            return _unavailable(
                "anthropic_claude_api",
                "anthropic_messages_call_failed",
                model=self.model,
                error_type=type(exc).__name__,
                error=str(exc)[:800],
                network_access="external_api_selected_data_minimized",
            )
        return _ok(
            "anthropic_claude_api",
            text,
            model=self.model,
            response_id=data.get("id"),
            usage=data.get("usage"),
            network_access="external_api_selected_data_minimized",
        )


@dataclass
class GeminiGenerateContentClient:
    model: str | None
    endpoint_template: str = GEMINI_GENERATE_ENDPOINT

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        required = _model_required("google_gemini_api", self.model)
        if required:
            return required
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return _unavailable("google_gemini_api", "GEMINI_API_KEY_or_GOOGLE_API_KEY_not_set", model=self.model)
        system, chat = _system_and_chat_messages(messages)
        model_name = str(self.model)
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        url = self.endpoint_template.format(model=model_name) + f"?key={api_key}"
        contents = [
            {
                "role": "model" if item["role"] == "assistant" else "user",
                "parts": [{"text": item["content"]}],
            }
            for item in chat
        ]
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": 0, "maxOutputTokens": 900},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            data = _post_json(url=url, body=body, headers={})
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            text = "".join(str(part.get("text", "")) for part in parts)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as exc:
            return _unavailable(
                "google_gemini_api",
                "gemini_generate_content_call_failed",
                model=self.model,
                error_type=type(exc).__name__,
                error=str(exc)[:800],
                network_access="external_api_selected_data_minimized",
            )
        return _ok(
            "google_gemini_api",
            text,
            model=self.model,
            usage=data.get("usageMetadata"),
            network_access="external_api_selected_data_minimized",
        )


@dataclass
class OpenAICompatibleChatClient:
    engine: str
    model: str | None
    endpoint: str
    api_key_env: str
    extra_headers: dict[str, str] | None = None

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        required = _model_required(self.engine, self.model)
        if required:
            return required
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            return _unavailable(self.engine, f"{self.api_key_env}_not_set", model=self.model)
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            **(self.extra_headers or {}),
        }
        try:
            data = _post_json(url=self.endpoint, body=body, headers=headers)
            text = _extract_openai_compatible_text(data)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as exc:
            return _unavailable(
                self.engine,
                f"{self.engine}_chat_completions_call_failed",
                model=self.model,
                error_type=type(exc).__name__,
                error=str(exc)[:800],
                network_access="external_api_selected_data_minimized",
            )
        return _ok(
            self.engine,
            text,
            model=self.model,
            response_id=data.get("id"),
            usage=data.get("usage"),
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
        safe_url = _validated_http_url(url)
        request = urllib.request.Request(safe_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            # URL scheme is validated before the request is built.
            with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310
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
        safe_url = _validated_http_url(self.endpoint)
        request = urllib.request.Request(safe_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            # URL scheme is validated before the request is built.
            with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310
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
            return _unavailable(
                "transformers_local",
                "local_model_path_not_found",
                model_path=str(path),
                local_files_only=True,
                network_access="blocked",
            )
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
    if engine == "anthropic_claude_api":
        return AnthropicMessagesClient(model=model)
    if engine == "google_gemini_api":
        return GeminiGenerateContentClient(model=model)
    if engine == "mistral_api":
        return OpenAICompatibleChatClient(
            engine="mistral_api",
            model=model,
            endpoint=model_path or MISTRAL_CHAT_COMPLETIONS_ENDPOINT,
            api_key_env="MISTRAL_API_KEY",
        )
    if engine == "openrouter_api":
        extra_headers = {}
        if os.environ.get("OPENROUTER_SITE_URL"):
            extra_headers["HTTP-Referer"] = os.environ["OPENROUTER_SITE_URL"]
        if os.environ.get("OPENROUTER_APP_NAME"):
            extra_headers["X-Title"] = os.environ["OPENROUTER_APP_NAME"]
        return OpenAICompatibleChatClient(
            engine="openrouter_api",
            model=model,
            endpoint=model_path or OPENROUTER_CHAT_COMPLETIONS_ENDPOINT,
            api_key_env="OPENROUTER_API_KEY",
            extra_headers=extra_headers,
        )
    if engine == "ollama_local_http":
        return OllamaClient(model=model or DEFAULT_OLLAMA_MODEL, endpoint=model_path or DEFAULT_OLLAMA_ENDPOINT)
    if engine == "lm_studio_local_http":
        return LMStudioClient(model=model or "local-model", endpoint=model_path or DEFAULT_LM_STUDIO_ENDPOINT)
    if engine == "transformers_local":
        return TransformersLocalClient(model_path=str(model_path or ""))
    return DeterministicClient(engine=engine)
