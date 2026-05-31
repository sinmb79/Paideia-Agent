from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

from ai22b.config import DEFAULT_CONFIG_PATH, PROJECT_ROOT, load_config


REQUIRED_DIRS = [
    "config",
    "corpus",
    "data/private",
    "data/public",
    "data/processed",
    "docs",
    "evals",
    "models/base",
    "models/adapters",
    "models/checkpoints",
    "runs",
    "scripts",
    "src/ai22b",
    "tests",
]

OPTIONAL_MODULES = [
    "torch",
    "transformers",
    "peft",
    "sentence_transformers",
    "chromadb",
    "ragas",
]

OPTIONAL_COMMANDS = ["git", "ffmpeg", "ffprobe"]


def _line(status: str, message: str) -> str:
    return f"[{status}] {message}"


def _section(config: dict, korean_key: str, english_key: str) -> dict:
    value = config.get(korean_key, config.get(english_key, {}))
    return value if isinstance(value, dict) else {}


def _value(data: dict, korean_key: str, english_key: str, default: object = "") -> object:
    return data.get(korean_key, data.get(english_key, default))


def run_checks() -> tuple[int, list[str]]:
    messages: list[str] = []
    failed = 0

    messages.append(_line("INFO", f"Project root: {PROJECT_ROOT}"))
    messages.append(_line("INFO", f"Python: {sys.version.split()[0]}"))

    if sys.version_info < (3, 10):
        failed += 1
        messages.append(_line("FAIL", "Python 3.10 이상이 필요합니다."))
    else:
        messages.append(_line("OK", "Python 버전이 적합합니다."))

    if DEFAULT_CONFIG_PATH.exists():
        messages.append(_line("OK", f"Config found: {DEFAULT_CONFIG_PATH}"))
        config = load_config()
    else:
        failed += 1
        messages.append(_line("FAIL", f"Config missing: {DEFAULT_CONFIG_PATH}"))
        config = {}

    for rel in REQUIRED_DIRS:
        path = PROJECT_ROOT / rel
        if path.exists():
            messages.append(_line("OK", f"Directory: {rel}"))
        else:
            failed += 1
            messages.append(_line("FAIL", f"Missing directory: {rel}"))

    voice = _section(config, "음성", "voice")
    default_voice = Path(str(_value(voice, "기본_음성_경로", "default_voice_path")))
    shared_root = Path(str(_value(voice, "공유_음성_루트", "shared_voice_root")))

    if shared_root.exists():
        messages.append(_line("OK", f"Shared voice root exists: {shared_root}"))
    else:
        messages.append(_line("WARN", f"Shared voice root missing: {shared_root}"))

    if default_voice.exists():
        messages.append(_line("OK", f"Default voice exists: {default_voice}"))
    else:
        messages.append(_line("WARN", f"Default voice missing: {default_voice}"))
        candidates = _value(voice, "후보_음성_경로들", "candidate_voice_paths", [])
        if not isinstance(candidates, list):
            candidates = []
        for candidate in candidates:
            candidate_path = Path(candidate)
            if candidate_path.exists():
                messages.append(_line("INFO", f"Voice candidate found: {candidate_path}"))

    for command in OPTIONAL_COMMANDS:
        resolved = shutil.which(command)
        if resolved:
            messages.append(_line("OK", f"Command available: {command} -> {resolved}"))
        else:
            messages.append(_line("WARN", f"Optional command missing: {command}"))

    for module in OPTIONAL_MODULES:
        if importlib.util.find_spec(module):
            messages.append(_line("OK", f"Python module available: {module}"))
        else:
            messages.append(_line("WARN", f"Optional module not installed: {module}"))

    return failed, messages


def main() -> int:
    failed, messages = run_checks()
    print("\n".join(messages))
    if failed:
        print(_line("FAIL", f"{failed} required check(s) failed."))
        return 1
    print(_line("OK", "Required checks passed. Optional warnings are safe for the first step."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
