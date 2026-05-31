from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "22b-ai.default.json"
DEFAULT_STORAGE_ROOT = PROJECT_ROOT.parent / "22B-AI-local-storage"
STORAGE_ROOT = Path(os.environ.get("AI22B_STORAGE_ROOT", DEFAULT_STORAGE_ROOT)).expanduser()
TALENT_FOUNDRY_STORAGE_ROOT = STORAGE_ROOT / "talent-foundry"
DEFAULT_SHARED_VOICES_ROOT = Path.home() / "workspace" / "shared-voices"


def _expand_placeholders(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_placeholders(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_placeholders(item) for item in value]
    if isinstance(value, str):
        replacements = {
            "%AI22B_STORAGE_ROOT%": str(STORAGE_ROOT),
            "%SHARED_VOICES_ROOT%": str(Path(os.environ.get("SHARED_VOICES_ROOT", DEFAULT_SHARED_VOICES_ROOT))),
        }
        for placeholder, replacement in replacements.items():
            value = value.replace(placeholder, replacement)
        return os.path.expandvars(value)
    return value


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as f:
        return _expand_placeholders(json.load(f))


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def storage_path(*parts: str) -> Path:
    return STORAGE_ROOT.joinpath(*parts)


def talent_foundry_storage_path(*parts: str) -> Path:
    return TALENT_FOUNDRY_STORAGE_ROOT.joinpath(*parts)
