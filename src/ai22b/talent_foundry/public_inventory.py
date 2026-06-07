from __future__ import annotations

import unicodedata
import re
from pathlib import Path
from typing import Any


PUBLIC_SCAN_DIRS = [
    ".github",
    "data/public",
    "docs",
    "evals",
    "examples",
    "schemas",
    "scripts",
    "src",
    "tests",
]

PUBLIC_SCAN_ROOT_FILES = [
    "LICENSE",
    "README.md",
    "README.ko.md",
    "ROADMAP.md",
    "ROADMAP.ko.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.ko.md",
    "SECURITY.md",
    "pyproject.toml",
]

PUBLIC_SCAN_EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "build",
    "node_modules",
    "dist",
    "target",
}

PUBLIC_SCAN_TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".jsonl",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}

PATH_BLOCKLIST_PATTERNS = [
    re.compile(r"^AGENTS\.md$"),
    re.compile(r"^docs/log\.md$"),
    re.compile(r"^data/private/"),
    re.compile(r"^data/processed/"),
    re.compile(r"^models/"),
    re.compile(r"^runs/"),
    re.compile(r"^apps/[^/]+/runs/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)build/"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)target/"),
]

_PRIVATE_USER = "sin" + "mb"
_PLACEHOLDER_USER_SEGMENTS = r"(?:<[^\\/]+>|your[-_ ]?(?:user|name)|user|username|example|sample|placeholder)"
_REAL_WINDOWS_USER_HOME_RE = r"C:[\\/]+Users[\\/]+(?!" + _PLACEHOLDER_USER_SEGMENTS + r"(?:[\\/]|$))[^\\/\s\"'<>]+"
_REAL_POSIX_USER_HOME_RE = (
    r"(?:^|[\s=:\"'])(?:[\\/]Users|[\\/]home)[\\/]+(?!"
    + _PLACEHOLDER_USER_SEGMENTS
    + r"(?:[\\/]|$))[^\\/\s\"'<>]+"
)
_PROVIDER_SECRET_ENV_KEYS = (
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AZURE_OPENAI_API_KEY",
)
_SECRET_VALUE_PREFIX_ALLOWLIST = r"(?:<|\$\{|your|example|sample|placeholder|changeme|replace_me|test_|fixture_)"
_PROVIDER_SECRET_ASSIGNMENT_RE = re.compile(
    r"\b("
    + "|".join(re.escape(key) for key in _PROVIDER_SECRET_ENV_KEYS)
    + r")\b\s*[:=]\s*['\"]?(?!"
    + _SECRET_VALUE_PREFIX_ALLOWLIST
    + r")[^'\",\s]{12,}",
    re.I,
)
CONTENT_BLOCKLIST_PATTERNS = [
    ("local_windows_user_path", re.compile(r"C:[\\/]+Users[\\/]+" + re.escape(_PRIVATE_USER), re.I)),
    ("local_posix_user_path", re.compile(r"[\\/]Users[\\/]+" + re.escape(_PRIVATE_USER), re.I)),
    ("generic_local_windows_user_path", re.compile(_REAL_WINDOWS_USER_HOME_RE, re.I)),
    ("generic_local_posix_user_path", re.compile(_REAL_POSIX_USER_HOME_RE, re.I)),
    ("openai_key_assignment", re.compile(r"OPENAI_API_KEY\s*=\s*['\"]?[^'\",\s]{8,}", re.I)),
    ("provider_secret_assignment", _PROVIDER_SECRET_ASSIGNMENT_RE),
    ("generic_openai_secret", re.compile(r"sk-[A-Za-z0-9_-]{32,}")),
    ("github_pat", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("private_key", re.compile(r"BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY")),
    ("refresh_token", re.compile(r"refresh_token\s*[:=]", re.I)),
    ("auth_token", re.compile(r"auth_token\s*[:=]", re.I)),
]

HIDDEN_UNICODE_BIDI_CONTROLS = tuple(
    chr(codepoint)
    for codepoint in (
        0x202A,
        0x202B,
        0x202C,
        0x202D,
        0x202E,
        0x2066,
        0x2067,
        0x2068,
        0x2069,
    )
)
HIDDEN_UNICODE_BIDI_PATTERN = re.compile("[" + re.escape("".join(HIDDEN_UNICODE_BIDI_CONTROLS)) + "]")
ALLOWED_CONTROL_CHARACTERS = {"\n", "\r", "\t"}


def _line_column(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    line_start = text.rfind("\n", 0, index) + 1
    return line, index - line_start + 1


def _escaped_surrounding_snippet(text: str, index: int, *, radius: int = 24) -> str:
    start = max(0, index - radius)
    end = min(len(text), index + radius + 1)
    return text[start:end].encode("unicode_escape").decode("ascii")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_excluded_scan_path(path: Path) -> bool:
    return any(part in PUBLIC_SCAN_EXCLUDED_DIR_NAMES for part in path.parts)


def public_candidate_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for root_file in PUBLIC_SCAN_ROOT_FILES:
        path = root / root_file
        if path.is_file():
            candidates.append(path)
    for scan_dir in PUBLIC_SCAN_DIRS:
        directory = root / scan_dir
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or is_excluded_scan_path(path.relative_to(root)):
                continue
            if path.suffix.casefold() not in PUBLIC_SCAN_TEXT_SUFFIXES:
                continue
            candidates.append(path)
    return sorted(set(candidates), key=lambda item: safe_rel(item, root))


def hidden_unicode_bidi_matches(text: str) -> list[dict[str, Any]]:
    matches = []
    for match in HIDDEN_UNICODE_BIDI_PATTERN.finditer(text):
        codepoint = ord(match.group(0))
        line, column = _line_column(text, match.start())
        matches.append(
            {
                "index": match.start(),
                "line": line,
                "column": column,
                "codepoint": f"U+{codepoint:04X}",
                "name": unicodedata.name(match.group(0), "UNKNOWN"),
                "category": unicodedata.category(match.group(0)),
                "escaped_surrounding_snippet": _escaped_surrounding_snippet(text, match.start()),
                "rule": "hidden_unicode_bidi_control",
            }
        )
    return matches


def hidden_control_character_matches(text: str) -> list[dict[str, Any]]:
    """Report non-printing Unicode controls without failing the public gate.

    Bidi controls remain blocking because they can visually reorder reviewed
    text. This broader report helps diagnose GitHub hidden-Unicode warnings
    before deciding whether a specific category should become a hard gate.
    """

    matches = []
    for index, character in enumerate(text):
        if character in ALLOWED_CONTROL_CHARACTERS or character in HIDDEN_UNICODE_BIDI_CONTROLS:
            continue
        category = unicodedata.category(character)
        if category not in {"Cc", "Cf"}:
            continue
        line, column = _line_column(text, index)
        matches.append(
            {
                "index": index,
                "line": line,
                "column": column,
                "codepoint": f"U+{ord(character):04X}",
                "name": unicodedata.name(character, "UNKNOWN"),
                "category": category,
                "escaped_surrounding_snippet": _escaped_surrounding_snippet(text, index),
                "rule": "hidden_control_character_observation",
            }
        )
    return matches


def scan_public_candidate_files(root: Path) -> dict[str, Any]:
    candidate_files = public_candidate_files(root)
    issues: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    for path in candidate_files:
        rel = safe_rel(path, root)
        normalized = rel.replace("\\", "/")
        for pattern in PATH_BLOCKLIST_PATTERNS:
            if pattern.search(normalized):
                issues.append(
                    {
                        "type": "blocked_path",
                        "file": rel,
                        "rule": pattern.pattern,
                    }
                )

        try:
            text = read_text(path)
        except (OSError, UnicodeDecodeError):
            continue

        for name, pattern in CONTENT_BLOCKLIST_PATTERNS:
            if pattern.search(text):
                issues.append(
                    {
                        "type": "blocked_content",
                        "file": rel,
                        "rule": name,
                    }
                )
        hidden_matches = hidden_unicode_bidi_matches(text)
        if hidden_matches:
            issues.append(
                {
                    "type": "blocked_content",
                    "file": rel,
                    "rule": "hidden_unicode_bidi_control",
                    "match_count": len(hidden_matches),
                    "matches": hidden_matches[:10],
                }
            )
        hidden_control_matches = hidden_control_character_matches(text)
        if hidden_control_matches:
            observations.append(
                {
                    "type": "hidden_control_character_observation",
                    "file": rel,
                    "rule": "hidden_control_character_observation",
                    "match_count": len(hidden_control_matches),
                    "matches": hidden_control_matches[:10],
                }
            )

    return {
        "candidate_file_count": len(candidate_files),
        "candidate_roots": PUBLIC_SCAN_ROOT_FILES + PUBLIC_SCAN_DIRS,
        "issue_count": len(issues),
        "issues": issues,
        "observation_count": len(observations),
        "observations": observations,
    }


def load_pyproject(path: Path) -> dict[str, Any]:
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError:
            return load_pyproject_minimal(path)
    return tomllib.loads(read_text(path))


def load_pyproject_minimal(path: Path) -> dict[str, Any]:
    """Fallback parser for the small pyproject subset Paideia publishes."""

    text = read_text(path)
    data: dict[str, Any] = {"project": {"optional-dependencies": {}, "scripts": {}, "urls": {}}}
    section = ""
    current_array: tuple[str, str] | None = None
    array_items: list[str] = []

    def commit_array() -> None:
        nonlocal current_array, array_items
        if current_array is None:
            return
        group, key = current_array
        if group == "project":
            data["project"][key] = array_items
        elif group == "optional":
            data["project"]["optional-dependencies"][key] = array_items
        current_array = None
        array_items = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            commit_array()
            section = line.strip("[]")
            continue
        if current_array is not None:
            if line == "]":
                commit_array()
                continue
            value = line.rstrip(",").strip().strip('"').strip("'")
            if value:
                array_items.append(value)
            continue
        if "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if value == "[":
            if section == "project.optional-dependencies":
                current_array = ("optional", key)
            elif section == "project":
                current_array = ("project", key)
            array_items = []
            continue
        value = value.rstrip(",")
        if value == "[]":
            parsed: Any = []
        elif value.startswith('"') and value.endswith('"'):
            parsed = value.strip('"')
        elif value.startswith("{") and value.endswith("}"):
            parsed = _parse_inline_table(value)
        else:
            parsed = value
        if section == "project":
            data["project"][key] = parsed
        elif section == "project.scripts":
            data["project"]["scripts"][key] = str(parsed)
        elif section == "project.urls":
            data["project"]["urls"][key] = str(parsed)
        elif section == "project.optional-dependencies":
            data["project"]["optional-dependencies"][key] = parsed if isinstance(parsed, list) else [str(parsed)]
    commit_array()
    return data


def _parse_inline_table(value: str) -> dict[str, str]:
    inner = value.strip("{} ")
    parsed: dict[str, str] = {}
    for item in inner.split(","):
        if "=" not in item:
            continue
        key, raw = [part.strip() for part in item.split("=", 1)]
        parsed[key] = raw.strip('"').strip("'")
    return parsed


def optional_dependency_groups(pyproject_data: dict[str, Any]) -> list[str]:
    project = pyproject_data.get("project", {})
    optional = project.get("optional-dependencies", {}) if isinstance(project, dict) else {}
    if not isinstance(optional, dict):
        return []
    return sorted(str(key) for key in optional)
