from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_CHATGPT_CODEX_MODEL = "gpt-5.5"
DEFAULT_OPENAI_API_MODEL = "gpt-5.2"

CHATGPT_CODEX_OAUTH_MODEL_CHOICES: list[dict[str, Any]] = [
    {
        "id": "gpt-5.5",
        "label": "GPT-5.5",
        "provider": "openai-codex",
        "auth_mode": "codex_oauth",
        "default": True,
        "status": "operator_default",
        "live_verification": "deferred_until_explicit_live_check",
    },
    {
        "id": "gpt-5.4",
        "label": "GPT-5.4",
        "provider": "openai-codex",
        "auth_mode": "codex_oauth",
        "default": False,
        "status": "known_local_hermes_option",
        "live_verification": "deferred_until_explicit_live_check",
    },
    {
        "id": "gpt-5.3-codex",
        "label": "GPT-5.3 Codex",
        "provider": "openai-codex",
        "auth_mode": "codex_oauth",
        "default": False,
        "status": "known_local_hermes_option",
        "live_verification": "deferred_until_explicit_live_check",
    },
    {
        "id": "gpt-5.2-codex",
        "label": "GPT-5.2 Codex",
        "provider": "openai-codex",
        "auth_mode": "codex_oauth",
        "default": False,
        "status": "known_local_hermes_option",
        "live_verification": "deferred_until_explicit_live_check",
    },
    {
        "id": "gpt-5.2",
        "label": "GPT-5.2",
        "provider": "openai-codex",
        "auth_mode": "codex_oauth",
        "default": False,
        "status": "paideia_runtime_default_compatible",
        "live_verification": "deferred_until_explicit_live_check",
    },
]

OPENAI_API_MODEL_CHOICES: list[dict[str, Any]] = [
    {
        "id": "gpt-5.2",
        "label": "GPT-5.2",
        "provider": "openai",
        "auth_mode": "api_key",
        "default": True,
        "status": "recommended_default",
        "live_verification": "deferred_until_explicit_live_check",
    },
    {
        "id": "gpt-4.1-mini",
        "label": "GPT-4.1 mini",
        "provider": "openai",
        "auth_mode": "api_key",
        "default": False,
        "status": "low_cost_smoke_option",
        "live_verification": "deferred_until_explicit_live_check",
    },
]

API_LLM_MODEL_CHOICES: dict[str, list[dict[str, Any]]] = {
    "anthropic_claude_api": [
        {"id": "claude-3-5-sonnet-latest", "label": "Claude Sonnet", "status": "example_model"},
        {"id": "claude-3-5-haiku-latest", "label": "Claude Haiku", "status": "example_model"},
    ],
    "google_gemini_api": [
        {"id": "gemini-1.5-pro", "label": "Gemini 1.5 Pro", "status": "example_model"},
        {"id": "gemini-1.5-flash", "label": "Gemini 1.5 Flash", "status": "example_model"},
    ],
    "mistral_api": [
        {"id": "mistral-large-latest", "label": "Mistral Large", "status": "example_model"},
        {"id": "mistral-small-latest", "label": "Mistral Small", "status": "example_model"},
    ],
    "openrouter_api": [
        {"id": "openai/gpt-5.2", "label": "OpenAI GPT via OpenRouter", "status": "example_model"},
        {"id": "anthropic/claude-3.5-sonnet", "label": "Claude via OpenRouter", "status": "example_model"},
    ],
    "ollama_local": [
        {"id": "llama3.1", "label": "llama3.1", "status": "example_local_model"},
        {"id": "qwen2.5", "label": "qwen2.5", "status": "example_local_model"},
    ],
    "lm_studio_local": [
        {"id": "loaded-local-model", "label": "Loaded LM Studio model", "status": "placeholder_for_loaded_model"},
    ],
}


LLM_SERVICE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "openai_chatgpt_codex",
        "label": "OpenAI ChatGPT/Codex bridge",
        "engine": "openai_chatgpt_codex",
        "status": "ready",
        "default_chat_mode": "auto",
        "default_model": DEFAULT_CHATGPT_CODEX_MODEL,
        "model_choices": CHATGPT_CODEX_OAUTH_MODEL_CHOICES,
        "model_policy": "Select a ChatGPT/Codex model from the catalog or override with --llm-model, PAIDEIA_LLM_MODEL, AI22B_OPENAI_MODEL, or OPENAI_MODEL.",
        "auth_modes": ["codex_oauth", "openai_api_fallback"],
        "chat_backend_default": "codex_oauth",
        "oauth_provider": "openai-codex",
        "requires": ["Hermes/ChatGPT Codex OAuth by default", "OPENAI_API_KEY only when PAIDEIA_CHAT_BACKEND=openai_api"],
        "researcher_fit": "recommended",
        "privacy_note": "Sends selected memory summaries only when live mode is explicitly used; raw OAuth tokens are never stored in Paideia artifacts.",
    },
    {
        "id": "openai_responses_api",
        "label": "OpenAI Responses API key adapter",
        "engine": "openai_chatgpt_codex",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "live_when_configured",
        "default_model": DEFAULT_OPENAI_API_MODEL,
        "model_choices": OPENAI_API_MODEL_CHOICES,
        "model_policy": "Uses OPENAI_API_KEY and a selectable OpenAI model; run live checks only after owner configuration.",
        "auth_modes": ["api_key"],
        "chat_backend_default": "openai_api",
        "api_provider": "openai",
        "requires": ["OPENAI_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External API choice; raw API keys and raw provider payloads are not stored in Paideia artifacts.",
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
        "model_choices": API_LLM_MODEL_CHOICES["anthropic_claude_api"],
        "model_policy": "Requires --llm-model and an Anthropic API key in the user's own environment.",
        "requires": ["ANTHROPIC_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External API choice; send only selected memory summaries after explicit configuration.",
    },
    {
        "id": "google_gemini_api",
        "label": "Google Gemini API adapter",
        "engine": "google_gemini_api",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "live_when_configured",
        "model_choices": API_LLM_MODEL_CHOICES["google_gemini_api"],
        "model_policy": "Requires --llm-model and a Gemini API key in the user's own environment.",
        "requires": ["GEMINI_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External API choice; send only selected memory summaries after explicit configuration.",
    },
    {
        "id": "mistral_api",
        "label": "Mistral API adapter",
        "engine": "mistral_api",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "live_when_configured",
        "model_choices": API_LLM_MODEL_CHOICES["mistral_api"],
        "model_policy": "Requires --llm-model and a Mistral API key in the user's own environment.",
        "requires": ["MISTRAL_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External API choice; send only selected memory summaries after explicit configuration.",
    },
    {
        "id": "openrouter_api",
        "label": "OpenRouter multi-provider adapter",
        "engine": "openrouter_api",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "live_when_configured",
        "model_choices": API_LLM_MODEL_CHOICES["openrouter_api"],
        "model_policy": "Requires --llm-model and OPENROUTER_API_KEY in the user's own environment.",
        "requires": ["OPENROUTER_API_KEY", "network access"],
        "researcher_fit": "external_api_choice",
        "privacy_note": "External router choice; send only selected memory summaries after explicit configuration.",
    },
    {
        "id": "ollama_local",
        "label": "Ollama local model server",
        "engine": "ollama_local_http",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "local_http_when_running",
        "model_choices": API_LLM_MODEL_CHOICES["ollama_local"],
        "model_policy": "Use --llm-model for an installed Ollama model; --llm-model-path can hold the localhost URL.",
        "requires": ["local Ollama server"],
        "researcher_fit": "local_private_model",
        "privacy_note": "Localhost-only adapter; no external API by default.",
    },
    {
        "id": "lm_studio_local",
        "label": "LM Studio local server",
        "engine": "lm_studio_local_http",
        "status": "adapter_manifest_ready",
        "default_chat_mode": "local_http_when_running",
        "model_choices": API_LLM_MODEL_CHOICES["lm_studio_local"],
        "model_policy": "Use --llm-model for the loaded local model; --llm-model-path can hold the localhost URL.",
        "requires": ["local LM Studio server"],
        "researcher_fit": "local_private_model",
        "privacy_note": "Localhost-only adapter; no external API by default.",
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
]

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
    {
        "id": "telegram-bridge",
        "label": "Telegram private bridge",
        "status": "ready_when_owner_configured",
        "entrypoint": "ai22b-paideia-telegram",
        "best_for": "owner-controlled mobile chat with the hired Paideia agent",
        "channel_policy": "private_allowlist_required",
        "requires": ["PAIDEIA_TELEGRAM_BOT_TOKEN", "PAIDEIA_TELEGRAM_ALLOWED_USERS"],
        "setup_command": "ai22b-paideia-telegram --employment-record <employment_record.json>",
        "network_access": "telegram_bot_api_after_owner_config",
        "default_enabled": False,
        "openclaw_pattern": "channel_adapter_disabled_until_token_and_allowlist_are_configured",
        "safety": {
            "allowlist_required": True,
            "stores_bot_token": False,
            "learning_promotion": "review_gated",
            "external_channel_enabled_by_default": False,
        },
    },
    {
        "id": "external-chat-gateway",
        "label": "External chat gateway manifest",
        "status": "adapter_manifest_only_disabled_by_default",
        "entrypoint": "adapter_manifests/external_chat_gateway.json",
        "best_for": "future Slack, Discord, webhook, or other channel adapters after explicit owner review",
        "channel_policy": "external_channels_disabled_until_configured",
        "requires": ["channel-specific bot token", "owner allowlist", "webhook signing secret"],
        "default_enabled": False,
        "openclaw_pattern": "gateway_manifest_first_then_owner_approval",
        "safety": {
            "allowlist_required": True,
            "stores_bot_token": False,
            "learning_promotion": "review_gated",
            "external_channel_enabled_by_default": False,
        },
    },
]

DEFAULT_LLM_SERVICE_ID = "openai_chatgpt_codex"
DEFAULT_CHAT_SURFACE_ID = "codex-bridge-chat"
EXTERNAL_API_ENGINES = {
    "openai_chatgpt_codex",
    "anthropic_claude_api",
    "google_gemini_api",
    "mistral_api",
    "openrouter_api",
}
LOCAL_HTTP_ENGINES = {"ollama_local_http", "lm_studio_local_http"}
LOCAL_MODEL_ENGINES = {"bigram_local", "transformers_local", "llama_cpp_local"}
OPENAI_API_SERVICE_IDS = {"openai_responses_api"}


def _network_access_for_engine(engine: str) -> str:
    if engine == "openai_chatgpt_codex":
        return "codex_or_openai_data_minimized"
    if engine in EXTERNAL_API_ENGINES:
        return "external_api_selected_data_minimized"
    if engine in LOCAL_HTTP_ENGINES:
        return "localhost_only"
    return "blocked"


def _network_access_for_service(item: dict[str, Any]) -> str:
    if item.get("id") in OPENAI_API_SERVICE_IDS:
        return "external_api_selected_data_minimized"
    return _network_access_for_engine(str(item.get("engine", "")))


def _runtime_readiness_for_engine(engine: str, status: str) -> str:
    if engine == "deterministic_local":
        return "offline_ready"
    if engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES:
        return "live_client_ready_when_configured"
    if engine in LOCAL_MODEL_ENGINES:
        return "ready_when_local_model_files_exist"
    return status


def _doctor_command_for(item: dict[str, Any], *, live_check: bool = False) -> str:
    engine = item["engine"]
    command = f"ai22b-talent-foundry doctor-llm-provider --llm-engine {engine} --llm-service {item['id']}"
    if item.get("default_model"):
        command += f" --llm-model {item['default_model']}"
    elif (engine in EXTERNAL_API_ENGINES and engine != "openai_chatgpt_codex") or engine in LOCAL_HTTP_ENGINES:
        command += " --llm-model <model>"
    if engine in LOCAL_HTTP_ENGINES:
        command += " --llm-model-path <localhost-url>"
    if engine in LOCAL_MODEL_ENGINES:
        command += " --llm-model-path <local-model-path>"
    if live_check:
        command += " --live-check"
    return command


def _enrich_llm_service_catalog() -> None:
    for item in LLM_SERVICE_CATALOG:
        engine = item["engine"]
        external_api = engine in EXTERNAL_API_ENGINES
        local_http = engine in LOCAL_HTTP_ENGINES
        local_model = engine in LOCAL_MODEL_ENGINES
        network_access = _network_access_for_service(item)
        item.setdefault("runtime_readiness", _runtime_readiness_for_engine(engine, item.get("status", "unknown")))
        item.setdefault(
            "doctor",
            {
                "required_before_live": external_api or local_http or local_model,
                "command": _doctor_command_for(item),
                "live_check_command": _doctor_command_for(item, live_check=True),
                "live_check_default": False,
                "secret_values_exported": False,
            },
        )
        item.setdefault(
            "live_check_policy",
            {
                "default": False,
                "requires_explicit_flag": True,
                "network_call_made_by_default": False,
            },
        )
        item.setdefault(
            "data_transfer_policy",
            {
                "network_access": network_access,
                "external_api": external_api,
                "codex_bridge": engine == "openai_chatgpt_codex" and item.get("id") not in OPENAI_API_SERVICE_IDS,
                "api_key_provider": item.get("id") in OPENAI_API_SERVICE_IDS,
                "localhost_only": local_http,
                "local_files_only": local_model,
                "payload": (
                    "selected_memory_summaries_only_when_live_mode_is_explicit"
                    if external_api or local_http
                    else "local_runtime_context_only"
                ),
            },
        )
        item.setdefault(
            "failure_policy",
            {
                "live_mode": "fail_closed_with_public_safe_error_packet",
                "auto_mode": (
                    "attempt_live_then_fallback_to_local_bridge_or_adapter_manifest"
                    if external_api or local_http
                    else "run_offline_or_report_missing_local_model"
                ),
            },
        )
        item.setdefault(
            "cost_warning",
            (
                "External API or hosted model costs may apply; Paideia never calls it unless live mode/live-check is explicitly selected."
                if external_api
                else "Local server or local model resource usage may apply."
                if local_http or local_model
                else "No provider billing in the deterministic offline engine."
            ),
        )


_enrich_llm_service_catalog()


def _catalog_by_id(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog}


def llm_service_ids() -> list[str]:
    return [item["id"] for item in LLM_SERVICE_CATALOG]


def chat_surface_ids() -> list[str]:
    return [item["id"] for item in CHAT_SURFACE_CATALOG]


def chatgpt_codex_model_ids() -> list[str]:
    return [item["id"] for item in CHATGPT_CODEX_OAUTH_MODEL_CHOICES]


def resolve_llm_service(
    *,
    llm_service: str | None = None,
    llm_engine: str | None = None,
    llm_model: str | None = None,
    llm_model_path: str | None = None,
) -> dict[str, Any]:
    requested = (llm_service or llm_engine or DEFAULT_LLM_SERVICE_ID).strip()
    by_id = _catalog_by_id(LLM_SERVICE_CATALOG)
    service = by_id.get(requested)
    if service is None:
        service = next((item for item in LLM_SERVICE_CATALOG if item["engine"] == requested), None)
    if service is None:
        raise ValueError(f"Unsupported LLM service: {requested}")

    resolved = deepcopy(service)
    resolved["service_id"] = resolved["id"]
    resolved["selected_model"] = llm_model or resolved.get("default_model") or None
    resolved["selected_model_path"] = llm_model_path or None
    engine = resolved["engine"]
    resolved["network_access"] = _network_access_for_service(resolved)
    resolved["model_selection"] = {
        "selected_model": resolved.get("selected_model"),
        "default_model": resolved.get("default_model"),
        "available_models": resolved.get("model_choices", []),
        "custom_model_allowed": True,
        "live_verification_required": engine in EXTERNAL_API_ENGINES or engine in LOCAL_HTTP_ENGINES,
    }
    return resolved


def resolve_chat_surface(chat_surface: str | None = None) -> dict[str, Any]:
    requested = (chat_surface or DEFAULT_CHAT_SURFACE_ID).strip()
    by_id = _catalog_by_id(CHAT_SURFACE_CATALOG)
    if requested not in by_id:
        raise ValueError(f"Unsupported chat surface: {requested}")
    return deepcopy(by_id[requested])


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
