# Codex OAuth Telegram Bridge Handoff

## Summary

Paideia Telegram chat was changed from the original OpenAI Responses API key path to a Hermes-style ChatGPT/Codex OAuth path. The repo now has a Codex OAuth backend for hired-agent chat turns and an official Telegram bridge console script.

The intent is to make the hired Paideia agent behave like the local Hermes agent: Telegram messages are routed through the local Paideia identity and memory context, while final language generation can use the user's ChatGPT/Codex OAuth session.

## Changed Files

- `src/ai22b/talent_foundry/memory_substrate.py`
  - Adds `PAIDEIA_CHAT_BACKEND` routing.
  - Adds `codex_oauth` / `openai-codex` live chat backend.
  - Discovers Hermes agent root via `PAIDEIA_HERMES_AGENT_ROOT`, `HERMES_AGENT_ROOT`, and the default local Hermes install path.
  - Uses Paideia's `codex_oauth_adapter.py` boundary to validate Hermes OAuth credentials and call Hermes' `openai-codex` adapter without exposing token values.
  - Preserves the old OpenAI API Responses path as `PAIDEIA_CHAT_BACKEND=openai_api`.
  - Supports `PAIDEIA_CHAT_BACKEND=auto` / `codex_then_openai`: try Codex OAuth first, then OpenAI API fallback only when `PAIDEIA_ALLOW_OPENAI_API_FALLBACK` is truthy.
  - Adds optional OpenAI API web search tool wiring when fallback API path is used and `PAIDEIA_ENABLE_WEB_SEARCH=1`.

- `src/ai22b/talent_foundry/codex_oauth_adapter.py`
  - Paideia-owned adapter boundary for Hermes `openai-codex` credential resolution and LLM calls.
  - Returns only public-safe credential status fields.
  - Does not return or store raw OAuth token values.

- `src/ai22b/talent_foundry/telegram_bridge.py`
  - Official repo-owned Telegram bridge module.
  - Console script: `ai22b-paideia-telegram`.
  - Default model: `gpt-5.5`.
  - Default max output tokens: `2400`.
  - Default backend: `codex_oauth`.
  - Accepts `--hermes-agent-root` or `PAIDEIA_HERMES_AGENT_ROOT` for operator-specific Hermes installs.
  - `/status` shows `Chat backend`.
  - Runtime commands:
    - `/codex` switches to `codex_oauth`.
    - `/api` switches to `openai_api`.
    - `/backend codex_oauth | openai_api | auto` switches explicitly.
    - `/models` lists known ChatGPT/Codex OAuth model choices.
    - `/model <name>` switches the model for later Telegram chat turns.
  - Normalizes JSON-wrapped assistant replies and suppresses internal mode footers unless `--show-mode-footer` is enabled.

- `src/ai22b/talent_foundry/onboarding_choices.py`
  - Adds a selectable ChatGPT/Codex OAuth model catalog:
    - `gpt-5.5`
    - `gpt-5.4`
    - `gpt-5.3-codex`
    - `gpt-5.2-codex`
    - `gpt-5.2`
  - Adds a separate `openai_responses_api` service for the `OPENAI_API_KEY` path so the owner can choose OAuth or API key mode intentionally.
  - Keeps Anthropic, Gemini, Mistral, OpenRouter, Ollama, LM Studio, and local-model choices visible as API/local alternatives.
  - Adds `telegram-bridge` and `external-chat-gateway` chat surfaces. External channels stay disabled until token, allowlist, and owner review are configured.

- `src/ai22b/talent_foundry/llm_runtime.py` and `src/ai22b/talent_foundry/llm_onboarding.py`
  - Preserve `openai_chatgpt_codex` as the default OAuth service.
  - Treat `openai_responses_api` as the explicit API-key service and require `OPENAI_API_KEY` during provider doctor/preflight checks.
  - Emit selected/default model choices, auth mode, chat backend, and service ID in connection profiles, live setup guides, and provider matrices.

- `pyproject.toml`
  - Adds `ai22b-paideia-telegram = "ai22b.talent_foundry.telegram_bridge:main"`.

- Private operator files outside the repo
  - A private launcher and recovery helper may remain under the local storage root.
  - These files are operator utilities, not upstream-ready source files.
  - Do not commit local env files, token stores, or machine-specific absolute paths.

## Authentication Recovery Performed

The normal Hermes OAuth refresh initially failed because the stored refresh token had already been consumed by another client. A new device-code flow also hit OpenAI/Cloudflare `429` from the device-code endpoint.

The machine already had a valid Codex CLI OAuth session at:

- `%USERPROFILE%\.codex\auth.json`

The tokens were imported into Hermes' `openai-codex` auth store using Hermes' private token-save helper. Token values were never printed or committed.

After import, `resolve_codex_runtime_credentials(refresh_if_expiring=False)` returned public-safe status equivalent to:

- `provider=openai-codex`
- `base_url=https://chatgpt.com/backend-api/codex`
- `source=hermes-auth-store`
- `auth_mode=chatgpt`

## Runtime Status

The private Paideia Telegram bridge was restarted and observed with:

- `Chat backend: codex_oauth`
- `Runtime engine: openai_chatgpt_codex`
- `Model: gpt-5.5`
- Telegram bot connected
- Active employment record: latest active `employment_record.json` under `%AI22B_STORAGE_ROOT%\talent-foundry\runs`

Expected Windows process shape:

- Python launcher process for the bridge.
- Child Python process or direct in-process Paideia chat call depending on the bridge version.

## Owner-Facing Selection Flow

No-network provider matrix:

```powershell
ai22b-talent-foundry list-llm-services --output llm_services.json
```

OAuth default connection profile:

```powershell
ai22b-talent-foundry build-llm-connection-profile `
  --llm-service openai_chatgpt_codex `
  --llm-model gpt-5.5 `
  --output llm_connection_profile.json
```

OpenAI API-key connection profile:

```powershell
ai22b-talent-foundry build-llm-connection-profile `
  --llm-service openai_responses_api `
  --llm-model gpt-5.2 `
  --output llm_connection_profile.openai_api.json
```

Telegram bridge:

```powershell
ai22b-paideia-telegram --employment-record <employment_record.json>
```

Telegram runtime controls:

- `/codex`: use ChatGPT/Codex OAuth.
- `/api`: use OpenAI API key Responses path.
- `/backend auto`: try Codex OAuth, then API fallback if fallback is explicitly allowed.
- `/models`: show known ChatGPT/Codex OAuth model choices.
- `/model gpt-5.3-codex`: switch model for later turns.

## Verification

Syntax checks:

```powershell
python -m py_compile `
  src\ai22b\talent_foundry\memory_substrate.py `
  src\ai22b\talent_foundry\codex_oauth_adapter.py `
  src\ai22b\talent_foundry\telegram_bridge.py
```

Focused tests:

```powershell
python -m pytest `
  tests\test_talent_foundry_memory_substrate_chat.py `
  tests\test_talent_foundry_telegram_bridge.py -q
```

Live Codex OAuth probe observed before this handoff:

- `live_attempt_engine=chatgpt_codex_oauth`
- `live_attempt_provider=openai-codex`
- `live_attempt_status=completed`
- `chat_runtime_status_card.status=completed_live`

Telegram notification was sent successfully in the private operator environment.

## Follow-Up Work for Development Codex

1. Add a first-run doctor check for:
   - Hermes agent root exists.
   - `openai-codex` credentials are available.
   - Codex OAuth live smoke can complete without exposing token values.
2. Keep the product-level model policy explicit:
   - `gpt-5.5` is the current default.
   - Owners can switch with `--llm-model` or Telegram `/model <name>`.
   - Hermes has historical warnings that some Codex accounts may silently reject some `gpt-5.5` family requests, so keep model override support and verify with an explicit live check.
3. Avoid committing or logging:
   - `OPENAI_API_KEY`
   - Telegram bot tokens
   - Hermes OAuth tokens
   - `%USERPROFILE%\.codex\auth.json`
   - `~\.hermes\auth.json`
