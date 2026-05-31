from __future__ import annotations

import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.openclaw_compat import (
    external_openclaw_channel_descriptor,
    external_openclaw_provider_descriptor,
    find_openclaw_channel,
    find_openclaw_provider,
    normalize_openclaw_channel_id,
    normalize_openclaw_provider_id,
    openclaw_secret_env_candidates,
    openclaw_channel_manifest,
    openclaw_chat_surface_entries,
    openclaw_llm_service_entries,
    openclaw_provider_manifest,
)


LLM_SERVICE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "openai_chatgpt_codex",
        "label": "OpenAI ChatGPT/Codex bridge",
        "engine": "openai_chatgpt_codex",
        "status": "ready",
        "default_chat_mode": "auto",
        "model_policy": "Use --llm-model, AI22B_OPENAI_MODEL, OPENAI_MODEL, or the built-in default.",
        "requires": ["Codex/ChatGPT runtime for bridge context", "OPENAI_API_KEY only for live Responses API chat"],
        "researcher_fit": "recommended",
        "privacy_note": "Sends selected memory summaries only when live mode is explicitly used.",
        "openclaw_provider_id": "openai",
        "api_protocol": "openai_responses",
        "base_url": "https://api.openai.com/v1",
        "secret_env_vars": ["OPENAI_API_KEY"],
        "aliases": ["openai", "codex"],
    },
    {
        "id": "openclaw_gateway_http",
        "label": "OpenClaw Gateway HTTP bridge",
        "engine": "openclaw_gateway_http",
        "status": "ready_when_openclaw_gateway_chat_completions_enabled",
        "default_chat_mode": "live_when_gateway_running",
        "model_policy": (
            "Use --llm-model as the OpenClaw backend provider/model override. "
            "The OpenAI-compatible model target stays openclaw/default unless configured otherwise."
        ),
        "requires": [
            "OpenClaw Gateway",
            "gateway.http.endpoints.chatCompletions.enabled=true",
            "OPENCLAW_GATEWAY_TOKEN or OPENCLAW_GATEWAY_PASSWORD when Gateway auth is enabled",
        ],
        "researcher_fit": "openclaw_native_full_provider_bridge",
        "privacy_note": "Sends selected Paideia memory summaries to a trusted local/private OpenClaw Gateway.",
        "openclaw_provider_id": "openclaw-gateway",
        "openclaw_agent_target": "openclaw/default",
        "api_protocol": "openclaw_gateway_openai_chat_completions",
        "base_url": "http://127.0.0.1:18789/v1",
        "secret_env_vars": ["OPENCLAW_GATEWAY_TOKEN", "OPENCLAW_GATEWAY_PASSWORD"],
        "auth_optional_on_loopback": True,
        "aliases": ["openclaw", "openclaw-gateway", "openclaw_gateway", "openclaw_gateway_http"],
    },
    {
        "id": "openclaw_cli_local",
        "label": "OpenClaw CLI local agent bridge",
        "engine": "openclaw_cli_local",
        "status": "ready_when_openclaw_cli_and_provider_auth_configured",
        "default_chat_mode": "live_when_openclaw_cli_configured",
        "model_policy": (
            "Use --llm-model as any OpenClaw provider/model accepted by "
            "`openclaw agent --local --model`."
        ),
        "requires": [
            "installed OpenClaw CLI",
            "OpenClaw provider auth or provider API keys available to the shell",
        ],
        "researcher_fit": "openclaw_native_cli_provider_and_channel_bridge",
        "privacy_note": "Sends selected Paideia memory summaries through the installed OpenClaw CLI local agent runtime.",
        "api_protocol": "openclaw_cli_agent_local",
        "secret_env_vars": [],
        "aliases": ["openclaw-cli", "openclaw_cli", "openclaw_agent_local", "openclaw_cli_local"],
    },
    {
        "id": "deterministic_local",
        "label": "Offline deterministic local engine",
        "engine": "deterministic_local",
        "status": "ready",
        "default_chat_mode": "offline",
        "model_policy": "No model path required.",
        "requires": [],
        "researcher_fit": "smoke_test_only",
        "privacy_note": "No network call.",
    },
    {
        "id": "anthropic_claude_api",
        "label": "Anthropic Claude API adapter",
        "engine": "anthropic_claude_api",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "live_when_configured",
        "model_policy": "Requires --llm-model and an Anthropic API key in the user's own environment.",
        "requires": ["ANTHROPIC_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External API choice; send only selected memory summaries after explicit configuration.",
        "openclaw_provider_id": "anthropic",
        "api_protocol": "anthropic_messages",
        "base_url": "https://api.anthropic.com/v1",
        "secret_env_vars": ["ANTHROPIC_API_KEY"],
        "aliases": ["anthropic", "claude"],
    },
    {
        "id": "google_gemini_api",
        "label": "Google Gemini API adapter",
        "engine": "google_gemini_api",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "live_when_configured",
        "model_policy": "Requires --llm-model and a Gemini API key in the user's own environment.",
        "requires": ["GEMINI_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External API choice; send only selected memory summaries after explicit configuration.",
        "openclaw_provider_id": "google",
        "api_protocol": "gemini_generate_content",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "secret_env_vars": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "aliases": ["google", "gemini"],
    },
    {
        "id": "mistral_api",
        "label": "Mistral API adapter",
        "engine": "mistral_api",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "live_when_configured",
        "model_policy": "Requires --llm-model and a Mistral API key in the user's own environment.",
        "requires": ["MISTRAL_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External API choice; send only selected memory summaries after explicit configuration.",
        "openclaw_provider_id": "mistral",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.mistral.ai/v1",
        "secret_env_vars": ["MISTRAL_API_KEY"],
        "aliases": ["mistral"],
    },
    {
        "id": "openrouter_api",
        "label": "OpenRouter multi-provider adapter",
        "engine": "openrouter_api",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "live_when_configured",
        "model_policy": "Requires --llm-model and OPENROUTER_API_KEY in the user's own environment.",
        "requires": ["OPENROUTER_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External router choice; send only selected memory summaries after explicit configuration.",
        "openclaw_provider_id": "openrouter",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://openrouter.ai/api/v1",
        "secret_env_vars": ["OPENROUTER_API_KEY"],
        "aliases": ["openrouter"],
    },
    {
        "id": "ollama_local",
        "label": "Ollama local model server",
        "engine": "ollama_local_http",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "local_http_when_running",
        "model_policy": "Use --llm-model for an installed Ollama model; --llm-model-path can hold the localhost URL.",
        "requires": ["local Ollama server"],
        "researcher_fit": "local_private_model",
        "privacy_note": "Localhost-only adapter; no external API by default.",
        "openclaw_provider_id": "ollama",
        "api_protocol": "ollama_chat",
        "base_url": "http://localhost:11434",
        "secret_env_vars": [],
        "aliases": ["ollama"],
    },
    {
        "id": "lm_studio_local",
        "label": "LM Studio local server",
        "engine": "lm_studio_local_http",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "local_http_when_running",
        "model_policy": "Use --llm-model for the loaded local model; --llm-model-path can hold the localhost URL.",
        "requires": ["local LM Studio server"],
        "researcher_fit": "local_private_model",
        "privacy_note": "Localhost-only adapter; no external API by default.",
        "openclaw_provider_id": "lmstudio",
        "api_protocol": "openai_chat_completions",
        "base_url": "http://localhost:1234/v1",
        "secret_env_vars": [],
        "aliases": ["lm-studio", "lm_studio", "lmstudio"],
    },
    {
        "id": "bigram_local",
        "label": "From-scratch local bigram checkpoint",
        "engine": "bigram_local",
        "status": "ready_when_model_path_exists",
        "default_chat_mode": "offline",
        "model_policy": "Requires --llm-model-path pointing to a saved bigram checkpoint.",
        "requires": ["local model checkpoint"],
        "researcher_fit": "educational_demo",
        "privacy_note": "No network call.",
    },
    {
        "id": "transformers_local",
        "label": "Local Hugging Face Transformers model",
        "engine": "transformers_local",
        "status": "adapter_ready_when_dependencies_and_model_exist",
        "default_chat_mode": "offline",
        "model_policy": "Requires --llm-model-path pointing to a local model folder.",
        "requires": ["torch", "transformers", "local model files"],
        "researcher_fit": "local_private_model",
        "privacy_note": "Local files only.",
    },
    {
        "id": "llama_cpp_local",
        "label": "Local llama.cpp / GGUF model",
        "engine": "llama_cpp_local",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "offline",
        "model_policy": "Requires --llm-model-path pointing to a .gguf file or folder.",
        "requires": ["local GGUF model"],
        "researcher_fit": "local_private_model",
        "privacy_note": "Local files only.",
    },
] + openclaw_llm_service_entries()

CHAT_SURFACE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "codex-bridge-chat",
        "label": "Codex bridge chat script",
        "status": "ready",
        "entrypoint": "start_paideia_chat.ps1",
        "best_for": "interactive local chat that reads the trained talent records first",
        "channel_policy": "local_terminal_only",
    },
    {
        "id": "cli-console",
        "label": "Paideia guided CLI console",
        "status": "ready",
        "entrypoint": "ai22b-talent-foundry start-console",
        "best_for": "first-time onboarding, role-model selection, and education-to-hiring runs",
        "channel_policy": "local_terminal_only",
    },
    {
        "id": "dataflow-job",
        "label": "Local dataflow job runner",
        "status": "ready",
        "entrypoint": "ai22b-talent-foundry run-hired-dataflow-job",
        "best_for": "structured work tests after the talent is hired",
        "channel_policy": "local_filesystem_only",
    },
    {
        "id": "openclaw-style-gateway",
        "label": "OpenClaw-style gateway adapter",
        "status": "adapter_manifest_only_disabled_by_default",
        "entrypoint": "adapter_manifests/openclaw_style.json",
        "best_for": "future messaging-channel integration after explicit review",
        "channel_policy": "external_channels_disabled_until_configured",
    },
] + openclaw_chat_surface_entries()

DEFAULT_LLM_SERVICE_ID = "openai_chatgpt_codex"
DEFAULT_CHAT_SURFACE_ID = "codex-bridge-chat"
EXTERNAL_API_ENGINES = {
    "openai_chatgpt_codex",
    "anthropic_claude_api",
    "google_gemini_api",
    "mistral_api",
    "openrouter_api",
    "openclaw_openai_compatible",
    "openclaw_anthropic_compatible",
    "openclaw_gateway_http",
    "openclaw_cli_local",
    "ollama_cloud_http",
    "openclaw_manifest_only",
}
LOCAL_HTTP_ENGINES = {"ollama_local_http", "lm_studio_local_http"}
LLM_HEALTH_SCHEMA = "ai22b-paideia-llm-service-health/v1"
SERVICE_SECRET_ENV_VARS = {
    "openai_chatgpt_codex": ["OPENAI_API_KEY"],
    "anthropic_claude_api": ["ANTHROPIC_API_KEY"],
    "google_gemini_api": ["GEMINI_API_KEY"],
    "mistral_api": ["MISTRAL_API_KEY"],
    "openrouter_api": ["OPENROUTER_API_KEY"],
}
LOCAL_HTTP_DEFAULT_URLS = {
    "ollama_local": "http://localhost:11434",
    "lm_studio_local": "http://localhost:1234/v1",
}


def _catalog_by_id(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog}


def llm_service_ids() -> list[str]:
    return [item["id"] for item in LLM_SERVICE_CATALOG]


def chat_surface_ids() -> list[str]:
    return [item["id"] for item in CHAT_SURFACE_CATALOG]


def resolve_llm_service(
    *,
    llm_service: str | None = None,
    llm_engine: str | None = None,
    llm_model: str | None = None,
    llm_model_path: str | None = None,
) -> dict[str, Any]:
    requested = (llm_service or llm_engine or DEFAULT_LLM_SERVICE_ID).strip()
    provider_model: str | None = None
    provider_from_model: dict[str, Any] | None = None
    gateway_agent_target: str | None = None
    auto_routed_manifest_provider = False
    gateway_prefixes = {"openclaw-gateway", "openclaw_gateway", "openclaw_gateway_http"}
    cli_prefixes = {"openclaw-cli", "openclaw_cli", "openclaw_cli_local"}
    if "/" in requested and requested.split("/", 1)[0].casefold() in gateway_prefixes:
        _prefix, remainder = requested.split("/", 1)
        requested = "openclaw_gateway_http"
        llm_model = llm_model or remainder
    elif "/" in requested and requested.split("/", 1)[0].casefold() in cli_prefixes:
        _prefix, remainder = requested.split("/", 1)
        requested = "openclaw_cli_local"
        llm_model = llm_model or remainder
    elif requested.casefold() in {"openclaw", "openclaw/default"}:
        requested = "openclaw_gateway_http"
        gateway_agent_target = "openclaw/default"
    if "/" in requested and requested not in _catalog_by_id(LLM_SERVICE_CATALOG):
        provider_id, model_id = requested.split("/", 1)
        provider_from_model = find_openclaw_provider(provider_id)
        if provider_from_model:
            provider_model = requested
            if provider_from_model.get("engine") == "openclaw_manifest_only":
                requested = "openclaw_gateway_http"
                llm_model = llm_model or provider_model
                gateway_agent_target = gateway_agent_target or "openclaw/default"
                auto_routed_manifest_provider = True
            else:
                requested = provider_from_model["service_id"]
                llm_model = llm_model or model_id
        elif provider_id.strip() and model_id.strip():
            provider_model = f"{normalize_openclaw_provider_id(provider_id)}/{model_id.strip()}"
            provider_from_model = external_openclaw_provider_descriptor(provider_id)
            requested = "openclaw_gateway_http"
            llm_model = llm_model or provider_model
            gateway_agent_target = gateway_agent_target or "openclaw/default"
            auto_routed_manifest_provider = True
    by_id = _catalog_by_id(LLM_SERVICE_CATALOG)
    service = by_id.get(requested)
    if service is None:
        service = next((item for item in LLM_SERVICE_CATALOG if item["engine"] == requested), None)
    if service is None:
        provider = find_openclaw_provider(requested)
        if provider is not None:
            service = {
                "id": provider["service_id"],
                "label": provider["label"],
                "engine": provider["engine"],
                "status": provider["status"],
                "default_chat_mode": "live_when_configured",
                "model_policy": "Use OpenClaw-style provider/model names, e.g. provider/model.",
                "requires": [*provider.get("secret_env_vars", []), "network access or local server"],
                "researcher_fit": "openclaw_provider_choice",
                "privacy_note": "Sends selected memory summaries only when live mode is explicitly used.",
                "openclaw_provider_id": provider["provider_id"],
                "api_protocol": provider["api_protocol"],
                "base_url": provider.get("base_url"),
                "secret_env_vars": provider.get("secret_env_vars", []),
                "aliases": provider.get("aliases", []),
            }
    if service is None:
        raise ValueError(f"Unsupported LLM service: {requested}")

    if service.get("engine") == "openclaw_manifest_only" and llm_model and service.get("openclaw_provider_id"):
        provider_model = f"{service['openclaw_provider_id']}/{llm_model}"
        provider_from_model = provider_from_model or find_openclaw_provider(str(service["openclaw_provider_id"]))
        service = by_id["openclaw_gateway_http"]
        llm_model = provider_model
        gateway_agent_target = gateway_agent_target or "openclaw/default"
        auto_routed_manifest_provider = True

    resolved = deepcopy(service)
    resolved["service_id"] = resolved["id"]
    resolved["selected_model"] = llm_model or None
    resolved["selected_model_path"] = llm_model_path or None
    if gateway_agent_target:
        resolved["openclaw_agent_target"] = gateway_agent_target
    if provider_model:
        resolved["openclaw_model"] = provider_model
    elif resolved.get("engine") == "openclaw_gateway_http" and llm_model:
        resolved["openclaw_model"] = llm_model
    elif resolved.get("engine") == "openclaw_cli_local" and llm_model:
        resolved["openclaw_model"] = llm_model
    elif resolved.get("openclaw_provider_id") and llm_model:
        resolved["openclaw_model"] = f"{resolved['openclaw_provider_id']}/{llm_model}"
    if resolved.get("engine") == "openclaw_cli_local" and llm_model and "/" in llm_model:
        provider_id = normalize_openclaw_provider_id(llm_model.split("/", 1)[0])
        provider = find_openclaw_provider(provider_id)
        resolved["openclaw_provider_id"] = provider_id
        resolved["openclaw_provider"] = provider or external_openclaw_provider_descriptor(provider_id)
        if provider is None:
            resolved["openclaw_provider_unverified"] = True
    if provider_from_model:
        resolved["openclaw_provider"] = provider_from_model
        if provider_from_model.get("external_openclaw_provider"):
            resolved["openclaw_provider_id"] = provider_from_model["provider_id"]
            resolved["openclaw_provider_unverified"] = True
    if auto_routed_manifest_provider:
        resolved["openclaw_gateway_auto_routed"] = True
        resolved["openclaw_gateway_route_reason"] = (
            "unknown_provider_model_deferred_to_openclaw_gateway"
            if provider_from_model and provider_from_model.get("external_openclaw_provider")
            else "manifest_only_provider_requires_openclaw_plugin_or_oauth"
        )
    if resolved.get("openclaw_provider_id") and resolved.get("engine") not in {
        "openclaw_gateway_http",
        "openclaw_cli_local",
    }:
        resolved["secret_env_vars"] = openclaw_secret_env_candidates(
            str(resolved["openclaw_provider_id"]),
            list(resolved.get("secret_env_vars", [])),
        )
        resolved["requires"] = [
            *resolved["secret_env_vars"],
            *[item for item in resolved.get("requires", []) if "API_KEY" not in str(item) and "OPENCLAW_LIVE" not in str(item)],
        ]
    engine = resolved["engine"]
    base_url = str(resolved.get("selected_model_path") or resolved.get("base_url") or "")
    if engine == "openai_chatgpt_codex":
        network_access = "codex_or_openai_data_minimized"
    elif engine == "openclaw_manifest_only":
        network_access = "disabled_until_provider_plugin_configured"
    elif engine == "openclaw_cli_local":
        network_access = "openclaw_cli_managed_provider_network_when_live"
    elif engine == "openclaw_gateway_http" and base_url.startswith(("http://localhost", "http://127.0.0.1")):
        network_access = "localhost_only"
    elif engine == "openclaw_openai_compatible" and base_url.startswith(("http://localhost", "http://127.0.0.1")):
        network_access = "localhost_only"
    elif engine in EXTERNAL_API_ENGINES:
        network_access = "external_api_selected_data_minimized"
    elif engine in LOCAL_HTTP_ENGINES:
        network_access = "localhost_only"
    else:
        network_access = "blocked"
    resolved["network_access"] = network_access
    return resolved


def resolve_chat_surface(chat_surface: str | None = None) -> dict[str, Any]:
    requested = (chat_surface or DEFAULT_CHAT_SURFACE_ID).strip()
    by_id = _catalog_by_id(CHAT_SURFACE_CATALOG)
    if requested not in by_id:
        channel = find_openclaw_channel(requested)
        if channel is not None:
            requested = f"openclaw-channel-{channel['channel_id']}"
    if requested not in by_id:
        if requested.startswith("openclaw-channel-"):
            channel = external_openclaw_channel_descriptor(requested)
            channel_id = normalize_openclaw_channel_id(requested)
            return {
                "id": f"openclaw-channel-{channel_id}",
                "label": f"OpenClaw {channel['label']}",
                "status": "openclaw_gateway_owned_unverified_channel",
                "entrypoint": "adapter_manifests/openclaw_style.json",
                "best_for": "OpenClaw Gateway-owned external channel route",
                "channel_policy": "external_openclaw_channel_disabled_until_gateway_plugin_review",
                "openclaw_channel_id": channel_id,
                "transport": channel["transport"],
                "external_openclaw_channel": True,
            }
        raise ValueError(f"Unsupported chat surface: {requested}")
    return deepcopy(by_id[requested])


def build_llm_service_health(llm_service: dict[str, Any]) -> dict[str, Any]:
    service_id = str(llm_service.get("service_id") or llm_service.get("id") or "")
    engine = str(llm_service.get("engine") or "")
    selected_model = llm_service.get("selected_model")
    selected_model_path = llm_service.get("selected_model_path")
    checks: list[dict[str, Any]] = []

    env_vars = llm_service.get("secret_env_vars") or SERVICE_SECRET_ENV_VARS.get(service_id, [])
    for env_var in env_vars:
        present = bool(os.environ.get(env_var))
        optional_loopback_auth = bool(
            llm_service.get("auth_optional_on_loopback")
            and str(llm_service.get("selected_model_path") or llm_service.get("base_url") or "").startswith(
                ("http://localhost", "http://127.0.0.1")
            )
        )
        checks.append(
            {
                "id": f"env:{env_var}",
                "kind": "environment_secret",
                "passed": present or optional_loopback_auth,
                "secret_value_stored": False,
                "optional_on_loopback": optional_loopback_auth,
                "message": (
                    "configured"
                    if present
                    else (
                        f"{env_var} is not set; allowed only if the local OpenClaw Gateway auth mode is none."
                        if optional_loopback_auth
                        else f"{env_var} is not set in this shell."
                    )
                ),
            }
        )

    if engine in LOCAL_HTTP_ENGINES or (
        engine == "openclaw_openai_compatible"
        and str(llm_service.get("base_url") or "").startswith(("http://localhost", "http://127.0.0.1"))
    ) or (
        engine == "openclaw_gateway_http"
        and str(llm_service.get("selected_model_path") or llm_service.get("base_url") or "").startswith(
            ("http://localhost", "http://127.0.0.1")
        )
    ):
        checks.append(
            {
                "id": "local_model_name",
                "kind": "local_model_selection",
                "passed": True if engine == "openclaw_gateway_http" else bool(selected_model),
                "message": (
                    "OpenClaw Gateway can use the agent default model or x-openclaw-model override"
                    if engine == "openclaw_gateway_http"
                    else ("model selected" if selected_model else "local model name was not provided")
                ),
            }
        )
        checks.append(
            {
                "id": "local_http_url",
                "kind": "local_server_manifest",
                "passed": bool(selected_model_path or llm_service.get("base_url") or LOCAL_HTTP_DEFAULT_URLS.get(service_id)),
                "url": selected_model_path or llm_service.get("base_url") or LOCAL_HTTP_DEFAULT_URLS.get(service_id),
                "network_probe_performed": False,
                "message": "URL recorded for later local probe; no network call performed.",
            }
        )

    if engine == "openclaw_cli_local":
        checks.append(
            {
                "id": "openclaw_cli_on_path",
                "kind": "installed_cli",
                "passed": bool(shutil.which("openclaw")),
                "binary_name": "openclaw",
                "secret_value_stored": False,
                "message": "OpenClaw CLI found on PATH" if shutil.which("openclaw") else "OpenClaw CLI was not found on PATH",
            }
        )
        checks.append(
            {
                "id": "openclaw_provider_model_selector",
                "kind": "provider_model_selection",
                "passed": bool(selected_model or llm_service.get("openclaw_model")),
                "model": selected_model or llm_service.get("openclaw_model"),
                "message": "provider/model selector ready" if (selected_model or llm_service.get("openclaw_model")) else "Select an OpenClaw provider/model.",
            }
        )

    if engine in {"bigram_local", "transformers_local", "llama_cpp_local"}:
        path = Path(str(selected_model_path)).expanduser() if selected_model_path else None
        checks.append(
            {
                "id": "local_model_path",
                "kind": "local_filesystem",
                "passed": bool(path and path.exists()),
                "path_recorded": bool(selected_model_path),
                "absolute_path_public_safe": False,
                "message": "local model path exists" if path and path.exists() else "local model path is missing or not set",
            }
        )

    if engine == "openclaw_manifest_only":
        status = "manifest_only_needs_provider_plugin"
    elif engine == "openclaw_cli_local":
        status = "ready_for_openclaw_cli_live" if checks and all(check["passed"] for check in checks) else "needs_openclaw_cli_or_model"
    elif engine == "openclaw_gateway_http":
        status = "configured_gateway_manifest_only" if all(check["passed"] for check in checks) else "needs_gateway_auth_or_url"
    elif service_id == "openai_chatgpt_codex":
        # Codex bridge can still prepare local context without a live API key.
        live_secret = next((check for check in checks if check["id"] == "env:OPENAI_API_KEY"), None)
        status = "ready_for_codex_bridge" if live_secret and not live_secret["passed"] else "ready_for_live_or_bridge"
    elif engine in EXTERNAL_API_ENGINES:
        status = "configured_no_network_probe" if checks and all(check["passed"] for check in checks) else "needs_secret"
    elif engine in LOCAL_HTTP_ENGINES:
        status = "configured_manifest_only" if all(check["passed"] for check in checks) else "needs_local_model_or_server"
    elif engine in {"deterministic_local"}:
        status = "ready_offline"
    else:
        status = "configured" if checks and all(check["passed"] for check in checks) else "needs_model_path"

    return {
        "schema": LLM_HEALTH_SCHEMA,
        "service_id": service_id,
        "engine": engine,
        "selected_model": selected_model,
        "openclaw_provider_id": llm_service.get("openclaw_provider_id"),
        "openclaw_model": llm_service.get("openclaw_model"),
        "openclaw_agent_target": llm_service.get("openclaw_agent_target"),
        "api_protocol": llm_service.get("api_protocol"),
        "base_url_recorded": bool(llm_service.get("base_url") or selected_model_path),
        "selected_model_path_recorded": bool(selected_model_path),
        "status": status,
        "network_probe_performed": False,
        "secret_values_stored": False,
        "checks": checks,
        "operator_note": (
            "The selected LLM is an application engine only. Paideia identity and growth records stay in local artifacts."
        ),
    }


def build_researcher_intake(
    *,
    owner: str,
    request: str,
    talent_name: str,
    domain: str | None,
    role_model_id: str | None,
    llm_service: dict[str, Any],
    chat_surface: dict[str, Any],
) -> dict[str, Any]:
    from ai22b.talent_foundry.role_models import list_role_models, summarize_role_model

    available_role_models = [summarize_role_model(item) for item in list_role_models(domain)]
    return {
        "schema": "ai22b-paideia-researcher-intake/v1",
        "owner": owner,
        "request": request,
        "talent_name": talent_name,
        "selected_llm_service": llm_service,
        "selected_chat_surface": chat_surface,
        "available_role_models": available_role_models,
        "available_llm_services": LLM_SERVICE_CATALOG,
        "openclaw_model_provider_catalog": openclaw_provider_manifest(),
        "openclaw_chat_channel_catalog": openclaw_channel_manifest(),
        "researcher_contract": {
            "role": "curriculum_researcher_and_growth_program_operator",
            "llm_is_identity": False,
            "llm_job": "turn owner requests into role-model research, curriculum, assessment, and onboarding inputs",
            "local_artifacts_are_identity": True,
            "private_reasoning_trace": "do_not_store",
        },
        "intake_order": [
            "detect_existing_config",
            "choose_quickstart_or_advanced",
            "choose_llm_service",
            "check_model_auth",
            "choose_workspace",
            "choose_gateway_and_channels",
            "choose_skill_import_policy",
            "choose_chat_surface",
            "capture_owner_request",
            "choose_talent_source",
            "select_domain_and_role_model",
            "build_blueprint",
            "raise_and_assess_talent",
            "review_hiring_dossier",
            "prepare_agent_id_card_payload",
            "run_health_check",
            "start_chat_or_job_surface",
        ],
        "role_model_selection": {
            "domain": domain or "auto_from_request",
            "role_model_id": role_model_id or "auto_or_default_available_track",
            "first_public_sample": "graham_value_investing",
            "custom_future_flow": "owner selects or adds a sourced role-model profile, then the researcher builds the matching curriculum manifest",
        },
        "direct_test_sample": {
            "talent_name": "grham-junior",
            "domain": "securities_research",
            "role_model_id": "graham_value_investing",
            "answers_file": "examples/graham_junior_onboarding.answers.json",
            "command": (
                "ai22b-talent-foundry start-console "
                "--answers examples/graham_junior_onboarding.answers.json"
            ),
        },
    }
