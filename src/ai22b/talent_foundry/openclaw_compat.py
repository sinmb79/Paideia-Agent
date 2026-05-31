from __future__ import annotations

from copy import deepcopy
from typing import Any


OPENCLAW_PROVIDER_CATALOG_SCHEMA = "ai22b-openclaw-provider-catalog/v1"
OPENCLAW_CHANNEL_CATALOG_SCHEMA = "ai22b-openclaw-channel-catalog/v1"
OPENCLAW_CATALOG_SOURCE_VERSION = "official_openclaw_docs_checked_2026-06-01_current_provider_channel_directory"


OPENCLAW_MODEL_PROVIDERS: list[dict[str, Any]] = [
    {
        "provider_id": "openai",
        "service_id": "openai_chatgpt_codex",
        "label": "OpenAI (API + Codex)",
        "engine": "openai_chatgpt_codex",
        "api_protocol": "openai_responses",
        "base_url": "https://api.openai.com/v1",
        "secret_env_vars": ["OPENAI_API_KEY"],
        "aliases": ["openai", "codex"],
        "status": "ready",
    },
    {
        "provider_id": "anthropic",
        "service_id": "anthropic_claude_api",
        "label": "Anthropic (API + Claude CLI)",
        "engine": "anthropic_claude_api",
        "api_protocol": "anthropic_messages",
        "base_url": "https://api.anthropic.com/v1",
        "secret_env_vars": ["ANTHROPIC_API_KEY"],
        "aliases": ["anthropic", "claude"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "google",
        "service_id": "google_gemini_api",
        "label": "Google Gemini",
        "engine": "google_gemini_api",
        "api_protocol": "gemini_generate_content",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "secret_env_vars": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "aliases": ["google", "gemini"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "mistral",
        "service_id": "mistral_api",
        "label": "Mistral",
        "engine": "mistral_api",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.mistral.ai/v1",
        "secret_env_vars": ["MISTRAL_API_KEY"],
        "aliases": ["mistral"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "openrouter",
        "service_id": "openrouter_api",
        "label": "OpenRouter",
        "engine": "openrouter_api",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://openrouter.ai/api/v1",
        "secret_env_vars": ["OPENROUTER_API_KEY"],
        "aliases": ["openrouter"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "ollama",
        "service_id": "ollama_local",
        "label": "Ollama (cloud + local models)",
        "engine": "ollama_local_http",
        "api_protocol": "ollama_chat",
        "base_url": "http://localhost:11434",
        "secret_env_vars": [],
        "aliases": ["ollama"],
        "status": "ready_when_local_server_running",
    },
    {
        "provider_id": "lmstudio",
        "service_id": "lm_studio_local",
        "label": "LM Studio local models",
        "engine": "lm_studio_local_http",
        "api_protocol": "openai_chat_completions",
        "base_url": "http://localhost:1234/v1",
        "secret_env_vars": [],
        "aliases": ["lm-studio", "lm_studio", "lmstudio"],
        "status": "ready_when_local_server_running",
    },
    {
        "provider_id": "arcee",
        "service_id": "arcee_api",
        "label": "Arcee AI",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.arcee.ai/api/v1",
        "secret_env_vars": ["OPENCLAW_LIVE_ARCEE_KEY", "ARCEEAI_API_KEY", "OPENROUTER_API_KEY"],
        "aliases": ["arcee", "arcee-ai", "arcee_ai"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "chutes",
        "service_id": "chutes_api",
        "label": "Chutes",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://llm.chutes.ai/v1",
        "secret_env_vars": ["OPENCLAW_LIVE_CHUTES_KEY", "CHUTES_API_KEY", "CHUTES_OAUTH_TOKEN"],
        "aliases": ["chutes", "chutes-ai", "chutes_ai"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "inferrs",
        "service_id": "inferrs_local",
        "label": "Inferrs local OpenAI-compatible server",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "http://127.0.0.1:8080/v1",
        "secret_env_vars": [],
        "aliases": ["inferrs"],
        "status": "ready_when_local_server_running",
    },
    {
        "provider_id": "minimax",
        "service_id": "minimax_api",
        "label": "MiniMax",
        "engine": "openclaw_anthropic_compatible",
        "api_protocol": "anthropic_messages",
        "base_url": "https://api.minimax.io/anthropic",
        "secret_env_vars": ["OPENCLAW_LIVE_MINIMAX_KEY", "MINIMAX_API_KEY"],
        "aliases": ["minimax"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "qianfan",
        "service_id": "qianfan_api",
        "label": "Qianfan",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://qianfan.baidubce.com/v2",
        "secret_env_vars": ["OPENCLAW_LIVE_QIANFAN_KEY", "QIANFAN_API_KEY"],
        "aliases": ["qianfan", "baidu-qianfan"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "stepfun",
        "service_id": "stepfun_api",
        "label": "StepFun",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.stepfun.ai/v1",
        "secret_env_vars": ["OPENCLAW_LIVE_STEPFUN_KEY", "STEPFUN_API_KEY"],
        "aliases": ["stepfun", "stepfun-standard"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "stepfun-plan",
        "service_id": "stepfun_plan_api",
        "label": "StepFun Plan",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.stepfun.ai/step_plan/v1",
        "secret_env_vars": ["OPENCLAW_LIVE_STEPFUN_KEY", "STEPFUN_API_KEY"],
        "aliases": ["stepfun-plan", "stepfun_plan"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "volcengine",
        "service_id": "volcengine_api",
        "label": "Volcengine / Doubao",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "secret_env_vars": ["OPENCLAW_LIVE_VOLCENGINE_KEY", "VOLCANO_ENGINE_API_KEY"],
        "aliases": ["volcengine", "volcano-engine", "doubao"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "volcengine-plan",
        "service_id": "volcengine_plan_api",
        "label": "Volcengine Plan / Ark Coding",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "secret_env_vars": ["OPENCLAW_LIVE_VOLCENGINE_KEY", "VOLCANO_ENGINE_API_KEY"],
        "aliases": ["volcengine-plan", "volcengine_plan", "ark-code"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "xiaomi",
        "service_id": "xiaomi_api",
        "label": "Xiaomi MiMo",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.xiaomimimo.com/v1",
        "secret_env_vars": ["OPENCLAW_LIVE_XIAOMI_KEY", "XIAOMI_API_KEY"],
        "aliases": ["xiaomi", "xiaomi-mimo", "mimo"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "xiaomi-token-plan",
        "service_id": "xiaomi_token_plan_api",
        "label": "Xiaomi MiMo Token Plan",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://token-plan-sgp.xiaomimimo.com/v1",
        "secret_env_vars": ["OPENCLAW_LIVE_XIAOMI_KEY", "XIAOMI_TOKEN_PLAN_API_KEY"],
        "aliases": ["xiaomi-token-plan", "xiaomi_token_plan"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "gmi",
        "service_id": "gmi_api",
        "label": "GMI Cloud",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.gmi-serving.com/v1",
        "secret_env_vars": ["GMI_API_KEY"],
        "aliases": ["gmi", "gmi-cloud", "gmicloud"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "novita",
        "service_id": "novita_api",
        "label": "NovitaAI",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.novita.ai/openai/v1",
        "secret_env_vars": ["NOVITA_API_KEY"],
        "aliases": ["novita", "novita-ai", "novitaai"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "huggingface",
        "service_id": "huggingface_api",
        "label": "Hugging Face Inference Providers",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://router.huggingface.co/v1",
        "secret_env_vars": ["HUGGINGFACE_HUB_TOKEN", "HF_TOKEN"],
        "aliases": ["huggingface", "huggingface-inference", "hf"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "kilocode",
        "service_id": "kilocode_gateway",
        "label": "Kilo Gateway",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.kilo.ai/api/gateway",
        "secret_env_vars": ["KILOCODE_API_KEY"],
        "aliases": ["kilocode", "kilo-gateway", "kilo_gateway"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "deepseek",
        "service_id": "deepseek_api",
        "label": "DeepSeek",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.deepseek.com/v1",
        "secret_env_vars": ["DEEPSEEK_API_KEY"],
        "aliases": ["deepseek"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "groq",
        "service_id": "groq_api",
        "label": "Groq",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.groq.com/openai/v1",
        "secret_env_vars": ["GROQ_API_KEY"],
        "aliases": ["groq"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "xai",
        "service_id": "xai_api",
        "label": "xAI",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.x.ai/v1",
        "secret_env_vars": ["XAI_API_KEY"],
        "aliases": ["xai", "x.ai"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "perplexity",
        "service_id": "perplexity_api",
        "label": "Perplexity",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.perplexity.ai",
        "secret_env_vars": ["PERPLEXITY_API_KEY"],
        "aliases": ["perplexity"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "together",
        "service_id": "together_ai",
        "label": "Together AI",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.together.xyz/v1",
        "secret_env_vars": ["TOGETHER_API_KEY"],
        "aliases": ["together", "together-ai"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "fireworks",
        "service_id": "fireworks_api",
        "label": "Fireworks",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "secret_env_vars": ["FIREWORKS_API_KEY"],
        "aliases": ["fireworks"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "deepinfra",
        "service_id": "deepinfra_api",
        "label": "DeepInfra",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "secret_env_vars": ["DEEPINFRA_API_KEY"],
        "aliases": ["deepinfra"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "cerebras",
        "service_id": "cerebras_api",
        "label": "Cerebras",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.cerebras.ai/v1",
        "secret_env_vars": ["CEREBRAS_API_KEY"],
        "aliases": ["cerebras"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "moonshot",
        "service_id": "moonshot_api",
        "label": "Moonshot AI / Kimi",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.moonshot.ai/v1",
        "secret_env_vars": ["MOONSHOT_API_KEY"],
        "aliases": ["moonshot", "kimi"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "qwen",
        "service_id": "qwen_api",
        "label": "Qwen Cloud",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "secret_env_vars": ["DASHSCOPE_API_KEY", "QWEN_API_KEY"],
        "aliases": ["qwen", "dashscope"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "zai",
        "service_id": "z_ai_api",
        "label": "Z.AI / GLM",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "secret_env_vars": ["ZAI_API_KEY", "ZHIPUAI_API_KEY"],
        "aliases": ["zai", "z-ai", "z_ai", "glm", "zhipu"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "synthetic",
        "service_id": "synthetic_api",
        "label": "Synthetic",
        "engine": "openclaw_anthropic_compatible",
        "api_protocol": "anthropic_messages",
        "base_url": "https://api.synthetic.new/anthropic",
        "secret_env_vars": ["SYNTHETIC_API_KEY"],
        "aliases": ["synthetic"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "ollama-cloud",
        "service_id": "ollama_cloud",
        "label": "Ollama Cloud",
        "engine": "ollama_cloud_http",
        "api_protocol": "ollama_chat",
        "base_url": "https://ollama.com",
        "secret_env_vars": ["OLLAMA_API_KEY"],
        "aliases": ["ollama-cloud", "ollama_cloud"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "venice",
        "service_id": "venice_api",
        "label": "Venice AI",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://api.venice.ai/api/v1",
        "secret_env_vars": ["VENICE_API_KEY"],
        "aliases": ["venice"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "nvidia",
        "service_id": "nvidia_api",
        "label": "NVIDIA",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "secret_env_vars": ["NVIDIA_API_KEY"],
        "aliases": ["nvidia"],
        "status": "ready_when_key_configured",
    },
    {
        "provider_id": "vllm",
        "service_id": "vllm_local",
        "label": "vLLM local or private server",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "http://localhost:8000/v1",
        "secret_env_vars": [],
        "aliases": ["vllm"],
        "status": "ready_when_local_server_running",
    },
    {
        "provider_id": "sglang",
        "service_id": "sglang_local",
        "label": "SGLang local model server",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "http://localhost:30000/v1",
        "secret_env_vars": [],
        "aliases": ["sglang"],
        "status": "ready_when_local_server_running",
    },
    {
        "provider_id": "litellm",
        "service_id": "litellm_gateway",
        "label": "LiteLLM gateway",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "http://localhost:4000/v1",
        "secret_env_vars": ["LITELLM_API_KEY"],
        "aliases": ["litellm"],
        "status": "ready_when_gateway_configured",
    },
    {
        "provider_id": "vercel-ai-gateway",
        "service_id": "vercel_ai_gateway",
        "label": "Vercel AI Gateway",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://ai-gateway.vercel.sh/v1",
        "secret_env_vars": ["AI_GATEWAY_API_KEY", "VERCEL_OIDC_TOKEN"],
        "aliases": ["vercel-ai-gateway", "vercel_ai_gateway"],
        "status": "ready_when_key_configured",
    },
]

OPENCLAW_MANIFEST_ONLY_PROVIDERS = [
    "alibaba",
    "amazon-bedrock",
    "amazon-bedrock-mantle",
    "anthropic-vertex",
    "azure-speech",
    "byteplus-plan",
    "byteplus",
    "claude-max-api-proxy",
    "cloudflare-ai-gateway",
    "comfyui",
    "deepgram",
    "ds4",
    "elevenlabs",
    "fal",
    "github-copilot",
    "google-gemini-cli",
    "google-vertex",
    "gradium",
    "inworld",
    "minimax-portal",
    "opencode",
    "opencode-go",
    "pixverse",
    "qwen-oauth",
    "runway",
    "senseaudio",
    "tencent-tokenhub",
    "vydra",
]

OPENCLAW_MANIFEST_ONLY_PROVIDER_ALIASES: dict[str, list[str]] = {
    "alibaba": ["alibaba-model-studio", "modelstudio"],
    "tencent-tokenhub": ["tencent-cloud-tokenhub"],
}


def openclaw_secret_env_candidates(provider_id: str, explicit: list[str] | None = None) -> list[str]:
    prefix = provider_id.upper().replace("-", "_").replace(".", "_")
    candidates = [
        f"OPENCLAW_LIVE_{prefix}_KEY",
        f"{prefix}_API_KEYS",
        f"{prefix}_API_KEY",
        *(explicit or []),
    ]
    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def normalize_openclaw_provider_id(identifier: str) -> str:
    return identifier.strip().casefold().replace("_", "-")


def external_openclaw_provider_descriptor(provider_id: str) -> dict[str, Any]:
    normalized = normalize_openclaw_provider_id(provider_id)
    return {
        "provider_id": normalized,
        "service_id": "openclaw_gateway_http",
        "label": f"External OpenClaw provider ({normalized})",
        "engine": "openclaw_gateway_http",
        "api_protocol": "openclaw_gateway_openai_chat_completions",
        "base_url": None,
        "secret_env_vars": [],
        "aliases": [normalized, normalized.replace("-", "_")],
        "status": "openclaw_gateway_owned_unverified_provider",
        "external_openclaw_provider": True,
        "claim_boundary": (
            "Paideia does not claim a direct adapter for this provider; it preserves the provider/model selector "
            "so an installed OpenClaw Gateway can own provider authentication and execution."
        ),
    }


OPENCLAW_CHANNELS: list[dict[str, Any]] = [
    {"channel_id": "bluebubbles", "label": "BlueBubbles migration", "transport": "legacy config migration to imessage/imsg"},
    {"channel_id": "clickclack", "label": "ClickClack", "transport": "bot-token channel"},
    {"channel_id": "discord", "label": "Discord", "transport": "Discord Bot API + Gateway"},
    {"channel_id": "slack", "label": "Slack", "transport": "Bolt SDK"},
    {"channel_id": "telegram", "label": "Telegram", "transport": "Bot API via grammY"},
    {"channel_id": "whatsapp", "label": "WhatsApp", "transport": "Baileys + QR pairing"},
    {"channel_id": "signal", "label": "Signal", "transport": "signal-cli"},
    {"channel_id": "microsoft-teams", "label": "Microsoft Teams", "transport": "Bot Framework"},
    {"channel_id": "google-chat", "label": "Google Chat", "transport": "HTTP webhook"},
    {"channel_id": "imessage", "label": "iMessage", "transport": "bundled imsg JSON-RPC bridge"},
    {"channel_id": "irc", "label": "IRC", "transport": "IRC server"},
    {"channel_id": "line", "label": "LINE", "transport": "LINE Messaging API"},
    {"channel_id": "matrix", "label": "Matrix", "transport": "Matrix protocol"},
    {"channel_id": "mattermost", "label": "Mattermost", "transport": "Bot API + WebSocket"},
    {"channel_id": "nextcloud-talk", "label": "Nextcloud Talk", "transport": "Nextcloud Talk"},
    {"channel_id": "nostr", "label": "Nostr", "transport": "NIP-04 DM"},
    {"channel_id": "qa-channel", "label": "QA Channel", "transport": "synthetic Slack-class QA plugin"},
    {"channel_id": "qq-bot", "label": "QQ Bot", "transport": "QQ Bot API"},
    {"channel_id": "sms", "label": "SMS", "transport": "Twilio-backed Gateway webhook"},
    {"channel_id": "synology-chat", "label": "Synology Chat", "transport": "webhooks"},
    {"channel_id": "tlon", "label": "Tlon", "transport": "Urbit messenger"},
    {"channel_id": "twitch", "label": "Twitch", "transport": "IRC"},
    {"channel_id": "voice-call", "label": "Voice Call", "transport": "Plivo or Twilio plugin"},
    {"channel_id": "webchat", "label": "WebChat", "transport": "Gateway WebSocket UI"},
    {"channel_id": "wechat", "label": "WeChat", "transport": "Tencent iLink bot plugin"},
    {"channel_id": "yuanbao", "label": "Yuanbao", "transport": "Tencent Yuanbao bot"},
    {"channel_id": "zalo", "label": "Zalo", "transport": "Zalo Bot API"},
    {"channel_id": "zalo-personal", "label": "Zalo Personal", "transport": "QR login personal account"},
    {"channel_id": "feishu", "label": "Feishu/Lark", "transport": "WebSocket bot"},
]

OPENCLAW_CHANNEL_ALIASES: dict[str, str] = {
    "googlechat": "google-chat",
    "google_chat": "google-chat",
    "gchat": "google-chat",
    "click-clack": "clickclack",
    "click_clack": "clickclack",
    "teams": "microsoft-teams",
    "microsoftteams": "microsoft-teams",
    "microsoft_teams": "microsoft-teams",
    "msteams": "microsoft-teams",
    "ms-teams": "microsoft-teams",
    "qa": "qa-channel",
    "qachannel": "qa-channel",
    "qa_channel": "qa-channel",
    "qq": "qq-bot",
    "qqbot": "qq-bot",
    "synology": "synology-chat",
    "synologychat": "synology-chat",
    "nextcloud": "nextcloud-talk",
    "nextcloudtalk": "nextcloud-talk",
    "voice": "voice-call",
    "voicecall": "voice-call",
    "zalo_personal": "zalo-personal",
    "zalopersonal": "zalo-personal",
    "zalouser": "zalo-personal",
}


def openclaw_provider_manifest() -> dict[str, Any]:
    return {
        "schema": OPENCLAW_PROVIDER_CATALOG_SCHEMA,
        "source_version": OPENCLAW_CATALOG_SOURCE_VERSION,
        "selection_model": "provider/model",
        "providers": deepcopy(OPENCLAW_MODEL_PROVIDERS),
        "manifest_only_providers": list(OPENCLAW_MANIFEST_ONLY_PROVIDERS),
        "manifest_only_provider_aliases": deepcopy(OPENCLAW_MANIFEST_ONLY_PROVIDER_ALIASES),
        "source_urls": [
            "https://docs.openclaw.ai/providers",
            "https://docs.openclaw.ai/providers/index",
            "https://docs.openclaw.ai/concepts/model-providers",
        ],
        "notes": [
            "Providers with api_protocol=openai_chat_completions use Paideia's generic OpenAI-compatible adapter.",
            "Providers with api_protocol=anthropic_messages use Paideia's Anthropic-compatible adapter shape.",
            "Providers with api_protocol=ollama_chat use Paideia's Ollama-native adapter shape.",
            "Manifest-only providers are represented for onboarding/config parity and need provider-specific plugins before live calls.",
        ],
    }


def openclaw_channel_manifest() -> dict[str, Any]:
    return {
        "schema": OPENCLAW_CHANNEL_CATALOG_SCHEMA,
        "source_version": OPENCLAW_CATALOG_SOURCE_VERSION,
        "gateway_model": "openclaw_gateway_channel",
        "channels": deepcopy(OPENCLAW_CHANNELS),
        "default_policy": "disabled_until_explicit_gateway_configuration",
        "source_urls": [
            "https://docs.openclaw.ai/channels",
            "https://docs.openclaw.ai/gateway/config-channels",
            "https://docs.openclaw.ai/announcements/bluebubbles-imessage",
            "https://docs.openclaw.ai/channels/bluebubbles",
        ],
    }


def openclaw_llm_service_entries() -> list[dict[str, Any]]:
    entries = []
    for provider in OPENCLAW_MODEL_PROVIDERS:
        service_id = provider["service_id"]
        if service_id in {
            "openai_chatgpt_codex",
            "anthropic_claude_api",
            "google_gemini_api",
            "mistral_api",
            "openrouter_api",
            "ollama_local",
            "lm_studio_local",
        }:
            continue
        entries.append(
            {
                "id": service_id,
                "label": provider["label"],
                "engine": provider["engine"],
                "status": provider["status"],
                "default_chat_mode": "live_when_configured",
                "model_policy": "Use OpenClaw-style provider/model names, e.g. provider/model.",
                "requires": [
                    *openclaw_secret_env_candidates(provider["provider_id"], provider.get("secret_env_vars", [])),
                    "network access or local server",
                ],
                "researcher_fit": "openclaw_provider_choice",
                "privacy_note": "Sends selected memory summaries only when live mode is explicitly used.",
                "openclaw_provider_id": provider["provider_id"],
                "api_protocol": provider["api_protocol"],
                "base_url": provider["base_url"],
                "secret_env_vars": openclaw_secret_env_candidates(provider["provider_id"], provider.get("secret_env_vars", [])),
                "aliases": provider.get("aliases", []),
            }
        )
    for provider_id in OPENCLAW_MANIFEST_ONLY_PROVIDERS:
        entries.append(
            {
                "id": f"openclaw_{provider_id.replace('-', '_')}",
                "label": provider_id.replace("-", " ").title(),
                "engine": "openclaw_manifest_only",
                "status": "manifest_only_needs_provider_plugin",
                "default_chat_mode": "disabled_until_configured",
                "model_policy": "OpenClaw-compatible catalog entry; provider-specific plugin/config is required before live use.",
                "requires": ["provider-specific OpenClaw-compatible plugin or gateway configuration"],
                "researcher_fit": "openclaw_manifest_choice",
                "privacy_note": "No network call is made by Paideia until the owner configures a concrete adapter.",
                "openclaw_provider_id": provider_id,
                "api_protocol": "manifest_only",
                "base_url": None,
                "secret_env_vars": [],
                "aliases": [
                    provider_id,
                    provider_id.replace("-", "_"),
                    *OPENCLAW_MANIFEST_ONLY_PROVIDER_ALIASES.get(provider_id, []),
                ],
            }
        )
    return entries


def openclaw_chat_surface_entries() -> list[dict[str, Any]]:
    return [
        {
            "id": f"openclaw-channel-{channel['channel_id']}",
            "label": f"OpenClaw {channel['label']} channel",
            "status": "gateway_manifest_only_disabled_by_default",
            "entrypoint": "adapter_manifests/openclaw_style.json",
            "best_for": f"{channel['label']} through {channel['transport']}",
            "channel_policy": "external_channel_disabled_until_pairing_and_allowlist_review",
            "openclaw_channel_id": channel["channel_id"],
            "transport": channel["transport"],
        }
        for channel in OPENCLAW_CHANNELS
    ]


def normalize_openclaw_channel_id(identifier: str) -> str:
    value = identifier.strip()
    if value.startswith("openclaw-channel-"):
        value = value.removeprefix("openclaw-channel-")
    normalized = value.casefold().replace("_", "-")
    return OPENCLAW_CHANNEL_ALIASES.get(normalized, normalized)


def external_openclaw_channel_descriptor(identifier: str) -> dict[str, Any]:
    channel_id = normalize_openclaw_channel_id(identifier)
    return {
        "channel_id": channel_id,
        "label": f"External OpenClaw channel ({channel_id})",
        "transport": "OpenClaw Gateway external channel",
        "external_openclaw_channel": True,
        "status": "openclaw_gateway_owned_unverified_channel",
        "claim_boundary": (
            "Paideia can preserve and route a normalized channel envelope for this id, but the installed "
            "OpenClaw channel plugin remains responsible for platform auth, pairing, and delivery."
        ),
    }


def find_openclaw_channel(identifier: str) -> dict[str, Any] | None:
    value = normalize_openclaw_channel_id(identifier)
    for channel in OPENCLAW_CHANNELS:
        ids = {
            channel["channel_id"].casefold(),
            channel["channel_id"].replace("-", "_").casefold(),
            f"openclaw-channel-{channel['channel_id']}".casefold(),
        }
        if value in ids:
            return deepcopy(channel)
    return None


def find_openclaw_provider(identifier: str) -> dict[str, Any] | None:
    value = identifier.strip().casefold()
    if not value:
        return None
    for provider in OPENCLAW_MODEL_PROVIDERS:
        ids = {
            provider["provider_id"].casefold(),
            provider["service_id"].casefold(),
            *{str(alias).casefold() for alias in provider.get("aliases", [])},
        }
        if value in ids:
            resolved = deepcopy(provider)
            resolved["secret_env_vars"] = openclaw_secret_env_candidates(
                resolved["provider_id"],
                resolved.get("secret_env_vars", []),
            )
            return resolved
    for provider_id in OPENCLAW_MANIFEST_ONLY_PROVIDERS:
        aliases = OPENCLAW_MANIFEST_ONLY_PROVIDER_ALIASES.get(provider_id, [])
        ids = {
            provider_id.casefold(),
            provider_id.replace("-", "_").casefold(),
            f"openclaw_{provider_id.replace('-', '_')}",
            *{alias.casefold() for alias in aliases},
            *{alias.replace("-", "_").casefold() for alias in aliases},
        }
        if value in ids:
            return {
                "provider_id": provider_id,
                "service_id": f"openclaw_{provider_id.replace('-', '_')}",
                "label": provider_id.replace("-", " ").title(),
                "engine": "openclaw_manifest_only",
                "api_protocol": "manifest_only",
                "base_url": None,
                "secret_env_vars": [],
                "aliases": [provider_id, provider_id.replace("-", "_"), *aliases],
                "status": "manifest_only_needs_provider_plugin",
            }
    return None
