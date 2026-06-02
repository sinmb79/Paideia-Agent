from __future__ import annotations

from copy import deepcopy
from typing import Any


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
    by_id = _catalog_by_id(LLM_SERVICE_CATALOG)
    service = by_id.get(requested)
    if service is None:
        service = next((item for item in LLM_SERVICE_CATALOG if item["engine"] == requested), None)
    if service is None:
        raise ValueError(f"Unsupported LLM service: {requested}")

    resolved = deepcopy(service)
    resolved["service_id"] = resolved["id"]
    resolved["selected_model"] = llm_model or None
    resolved["selected_model_path"] = llm_model_path or None
    engine = resolved["engine"]
    if engine == "openai_chatgpt_codex":
        network_access = "codex_or_openai_data_minimized"
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
