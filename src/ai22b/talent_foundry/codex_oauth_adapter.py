from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


CODEX_OAUTH_ENGINE = "chatgpt_codex_oauth"
CODEX_OAUTH_PROVIDER = "openai-codex"


def _ensure_hermes_import_path(hermes_root: Path) -> None:
    root_text = str(hermes_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def resolve_codex_oauth_credentials(
    hermes_root: Path,
    *,
    refresh_if_expiring: bool = True,
) -> dict[str, Any]:
    """Resolve Hermes Codex OAuth credentials without returning token values."""

    _ensure_hermes_import_path(hermes_root)
    from hermes_cli.auth import resolve_codex_runtime_credentials

    credentials = resolve_codex_runtime_credentials(refresh_if_expiring=refresh_if_expiring)
    return {
        "authenticated": bool(str(credentials.get("api_key") or "").strip()),
        "provider": credentials.get("provider") or CODEX_OAUTH_PROVIDER,
        "base_url": credentials.get("base_url"),
        "source": credentials.get("source"),
        "auth_mode": credentials.get("auth_mode"),
    }


def call_codex_oauth_llm(
    hermes_root: Path,
    *,
    task: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: float,
) -> str:
    """Call Hermes' Codex LLM adapter and return only generated text."""

    _ensure_hermes_import_path(hermes_root)
    from agent.auxiliary_client import call_llm

    response = call_llm(
        task=task,
        provider=CODEX_OAUTH_PROVIDER,
        model=model,
        messages=messages,
        temperature=None,
        max_tokens=None,
        tools=[],
        timeout=timeout_seconds,
    )
    choice = response.choices[0]
    return str(choice.message.content or "")
