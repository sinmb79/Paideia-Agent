from __future__ import annotations

from copy import deepcopy
from typing import Any


OPENCLAW_PROVIDER_CATALOG_SCHEMA = "ai22b-openclaw-provider-catalog/v1"
OPENCLAW_CHANNEL_CATALOG_SCHEMA = "ai22b-openclaw-channel-catalog/v1"


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
        "provider_id": "lm-studio",
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
        "provider_id": "z-ai",
        "service_id": "z_ai_api",
        "label": "Z.AI / GLM",
        "engine": "openclaw_openai_compatible",
        "api_protocol": "openai_chat_completions",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "secret_env_vars": ["ZAI_API_KEY", "ZHIPUAI_API_KEY"],
        "aliases": ["z-ai", "glm", "zhipu"],
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
    "alibaba-model-studio",
    "amazon-bedrock",
    "amazon-bedrock-mantle",
    "anthropic-vertex",
    "arcee-ai",
    "azure-speech",
    "byteplus",
    "chutes",
    "claude-max-api-proxy",
    "cloudflare-ai-gateway",
    "comfyui",
    "deepgram",
    "elevenlabs",
    "fal",
    "github-copilot",
    "google-gemini-cli",
    "google-vertex",
    "gradium",
    "huggingface-inference",
    "inferrs",
    "inworld",
    "kilo-gateway",
    "minimax",
    "opencode",
    "opencode-go",
    "qianfan",
    "runway",
    "senseaudio",
    "stepfun",
    "synthetic",
    "tencent-tokenhub",
    "volcengine-doubao",
    "vydra",
    "xiaomi-mimo",
]


OPENCLAW_CHANNELS: list[dict[str, Any]] = [
    {"channel_id": "discord", "label": "Discord", "transport": "Discord Bot API + Gateway"},
    {"channel_id": "slack", "label": "Slack", "transport": "Bolt SDK"},
    {"channel_id": "telegram", "label": "Telegram", "transport": "Bot API via grammY"},
    {"channel_id": "whatsapp", "label": "WhatsApp", "transport": "Baileys + QR pairing"},
    {"channel_id": "signal", "label": "Signal", "transport": "signal-cli"},
    {"channel_id": "microsoft-teams", "label": "Microsoft Teams", "transport": "Bot Framework"},
    {"channel_id": "google-chat", "label": "Google Chat", "transport": "HTTP webhook"},
    {"channel_id": "imessage", "label": "iMessage", "transport": "macOS imsg bridge"},
    {"channel_id": "irc", "label": "IRC", "transport": "IRC server"},
    {"channel_id": "line", "label": "LINE", "transport": "LINE Messaging API"},
    {"channel_id": "matrix", "label": "Matrix", "transport": "Matrix protocol"},
    {"channel_id": "mattermost", "label": "Mattermost", "transport": "Bot API + WebSocket"},
    {"channel_id": "nextcloud-talk", "label": "Nextcloud Talk", "transport": "Nextcloud Talk"},
    {"channel_id": "nostr", "label": "Nostr", "transport": "NIP-04 DM"},
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


def openclaw_provider_manifest() -> dict[str, Any]:
    return {
        "schema": OPENCLAW_PROVIDER_CATALOG_SCHEMA,
        "selection_model": "provider/model",
        "providers": deepcopy(OPENCLAW_MODEL_PROVIDERS),
        "manifest_only_providers": list(OPENCLAW_MANIFEST_ONLY_PROVIDERS),
        "notes": [
            "Providers with api_protocol=openai_chat_completions use Paideia's generic OpenAI-compatible adapter.",
            "Manifest-only providers are represented for onboarding/config parity and need provider-specific plugins before live calls.",
        ],
    }


def openclaw_channel_manifest() -> dict[str, Any]:
    return {
        "schema": OPENCLAW_CHANNEL_CATALOG_SCHEMA,
        "gateway_model": "openclaw_gateway_channel",
        "channels": deepcopy(OPENCLAW_CHANNELS),
        "default_policy": "disabled_until_explicit_gateway_configuration",
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
                "requires": [*provider.get("secret_env_vars", []), "network access or local server"],
                "researcher_fit": "openclaw_provider_choice",
                "privacy_note": "Sends selected memory summaries only when live mode is explicitly used.",
                "openclaw_provider_id": provider["provider_id"],
                "api_protocol": provider["api_protocol"],
                "base_url": provider["base_url"],
                "secret_env_vars": provider.get("secret_env_vars", []),
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
                "aliases": [provider_id, provider_id.replace("-", "_")],
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
    return value.casefold().replace("_", "-")


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
            return deepcopy(provider)
    for provider_id in OPENCLAW_MANIFEST_ONLY_PROVIDERS:
        ids = {provider_id.casefold(), provider_id.replace("-", "_").casefold(), f"openclaw_{provider_id.replace('-', '_')}"}
        if value in ids:
            return {
                "provider_id": provider_id,
                "service_id": f"openclaw_{provider_id.replace('-', '_')}",
                "label": provider_id.replace("-", " ").title(),
                "engine": "openclaw_manifest_only",
                "api_protocol": "manifest_only",
                "base_url": None,
                "secret_env_vars": [],
                "aliases": [provider_id, provider_id.replace("-", "_")],
                "status": "manifest_only_needs_provider_plugin",
            }
    return None
