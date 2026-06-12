from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any


CODEX_OAUTH_ENGINE = "chatgpt_codex_oauth"
CODEX_OAUTH_PROVIDER = "openai-codex"
HERMES_ROOT_REVIEW_MARKER = ".paideia_codex_oauth_adapter_review.json"


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() not in {"", "0", "false", "no", "off"}


def _approved_by_marker(root: Path) -> bool:
    marker = root / HERMES_ROOT_REVIEW_MARKER
    if not marker.is_file():
        return False
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        payload.get("schema") == "paideia-codex-oauth-adapter-review/v1"
        and payload.get("approved") is True
        and payload.get("provider") == CODEX_OAUTH_PROVIDER
    )


def _approved_by_env_allowlist(root: Path) -> bool:
    raw = os.environ.get("PAIDEIA_TRUSTED_HERMES_AGENT_ROOTS", "")
    for item in raw.split(os.pathsep):
        if not item.strip():
            continue
        try:
            if Path(item).expanduser().resolve() == root:
                return True
        except OSError:
            continue
    return _truthy(os.environ.get("PAIDEIA_TRUST_HERMES_AGENT_ROOT"))


def _validate_hermes_root(hermes_root: Path) -> Path:
    root = hermes_root.expanduser().resolve()
    required_files = [
        root / "hermes_cli" / "auth.py",
        root / "agent" / "auxiliary_client.py",
    ]
    if not all(path.is_file() for path in required_files):
        raise ValueError("Hermes root does not expose the required Codex OAuth adapter files")
    if not (_approved_by_marker(root) or _approved_by_env_allowlist(root)):
        raise ValueError(
            "Hermes root is not Paideia-reviewed; add "
            f"{HERMES_ROOT_REVIEW_MARKER} or PAIDEIA_TRUSTED_HERMES_AGENT_ROOTS"
        )
    return root


@contextmanager
def _temporary_hermes_import_path(hermes_root: Path):
    root = _validate_hermes_root(hermes_root)
    root_text = str(root)
    original_path = list(sys.path)
    target_module_prefixes = ("hermes_cli", "agent")
    saved_target_modules = {
        name: sys.modules.pop(name)
        for name in list(sys.modules)
        if any(name == prefix or name.startswith(prefix + ".") for prefix in target_module_prefixes)
    }
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    try:
        yield root
    finally:
        for name, module in list(sys.modules.items()):
            is_target_module = any(name == prefix or name.startswith(prefix + ".") for prefix in target_module_prefixes)
            module_file = getattr(module, "__file__", None)
            imported_from_hermes = False
            if module_file:
                try:
                    module_path = Path(module_file).resolve()
                    imported_from_hermes = root in [module_path, *module_path.parents]
                except OSError:
                    imported_from_hermes = False
            if is_target_module or imported_from_hermes:
                sys.modules.pop(name, None)
        sys.modules.update(saved_target_modules)
        sys.path[:] = original_path


def resolve_codex_oauth_credentials(
    hermes_root: Path,
    *,
    refresh_if_expiring: bool = True,
) -> dict[str, Any]:
    """Resolve Hermes Codex OAuth credentials without returning token values."""

    with _temporary_hermes_import_path(hermes_root):
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

    with _temporary_hermes_import_path(hermes_root):
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
