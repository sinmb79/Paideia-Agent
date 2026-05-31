from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OWNER_SELF_EXTENSION_MANIFEST_SCHEMA = "ai22b-owner-self-extension-manifest/v1"

DEFAULT_ALLOWED_EXTENSIONS = {
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PRIVATE_SNIPPET_BYTES = 640


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _category_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".py", ".ps1"}:
        return "code"
    if suffix in {".json", ".csv", ".yaml", ".yml", ".toml", ".ini", ".cfg"}:
        return "structured_data_or_config"
    if suffix in {".md", ".txt"}:
        return "documents_or_notes"
    return "other"


def _learning_signals(path: Path, text_sample: str) -> list[str]:
    haystack = f"{path.as_posix()} {text_sample}".casefold()
    signals: list[str] = []
    checks = [
        ("project_memory", ["handoff", "memory", "log", "retrospective", "교훈", "기억"]),
        ("coding_style", ["def ", "class ", "import ", "pytest", "powershell", "script"]),
        ("owner_preference", ["preference", "rule", "boss", "보스", "원칙", "설정"]),
        ("workflow_pattern", ["workflow", "pipeline", "onboarding", "automation", "프로세스"]),
        ("domain_knowledge", ["research", "analysis", "finance", "ai", "model", "학습"]),
    ]
    for signal, needles in checks:
        if any(needle.casefold() in haystack for needle in needles):
            signals.append(signal)
    return signals or ["private_reference_material"]


def _keyword_sample(path: Path, max_bytes: int = PRIVATE_SNIPPET_BYTES) -> tuple[str, list[str]]:
    try:
        raw = path.read_bytes()[:max_bytes]
        text = raw.decode("utf-8", errors="ignore")
    except OSError:
        text = ""
    words = re.findall(r"[A-Za-z0-9가-힣_]{3,}", text.casefold())
    keywords = list(dict.fromkeys(words))[:12]
    return text, keywords


def _manifest_item(root: Path, path: Path, *, include_review_snippets: bool) -> dict[str, Any]:
    text_sample, keywords = _keyword_sample(path)
    item: dict[str, Any] = {
        "relative_path": path.relative_to(root).as_posix(),
        "extension": path.suffix.lower(),
        "byte_count": path.stat().st_size,
        "sha256": _sha256(path),
        "category": _category_for(path),
        "learning_signals": _learning_signals(path.relative_to(root), text_sample),
        "keyword_sample": keywords,
        "content_policy": "metadata_hash_and_short_keywords_only",
    }
    if include_review_snippets:
        item["private_review_snippet"] = text_sample[:PRIVATE_SNIPPET_BYTES]
        item["content_policy"] = "private_review_snippet_local_only_not_for_public_release"
    return item


def build_owner_self_extension_manifest(
    source_dir: Path,
    *,
    output_path: Path | None = None,
    include_review_snippets: bool = False,
    max_files: int = 200,
    allowed_extensions: set[str] | None = None,
) -> dict[str, Any]:
    """Create a local-only manifest for owner self-extension training material.

    The manifest intentionally avoids absolute source paths and full file bodies by
    default. It is meant to tell the researcher engine what local materials exist
    without making those materials safe for public release.
    """

    root = source_dir.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Owner self-extension source directory does not exist: {source_dir}")
    if not root.is_dir():
        raise NotADirectoryError(f"Owner self-extension source is not a directory: {source_dir}")

    extensions = {item.lower() for item in (allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS)}
    all_files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in extensions
        and not any(part in {".git", "__pycache__", ".venv", "node_modules"} for part in path.parts)
    ]
    all_files = sorted(all_files, key=lambda item: item.relative_to(root).as_posix())
    files = all_files[: max(0, max_files)]

    items = [_manifest_item(root, path, include_review_snippets=include_review_snippets) for path in files]
    category_counts: dict[str, int] = {}
    extension_counts: dict[str, int] = {}
    total_bytes = 0
    for item in items:
        category_counts[item["category"]] = category_counts.get(item["category"], 0) + 1
        extension_counts[item["extension"]] = extension_counts.get(item["extension"], 0) + 1
        total_bytes += int(item["byte_count"])

    manifest = {
        "schema": OWNER_SELF_EXTENSION_MANIFEST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "root_label": root.name,
            "absolute_path_stored": False,
            "source_fingerprint_sha256": hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        },
        "policy": {
            "local_only": True,
            "public_release_safe_by_default": not include_review_snippets,
            "private_data_upload": "forbidden_without_explicit_owner_approval",
            "full_content_ingest": "not_performed_by_default",
            "absolute_paths": "redacted",
        },
        "scan": {
            "max_files": max_files,
            "allowed_extensions": sorted(extensions),
            "file_count": len(items),
            "total_bytes": total_bytes,
            "category_counts": category_counts,
            "extension_counts": extension_counts,
            "truncated": len(all_files) > len(files),
        },
        "items": items,
    }
    if output_path is not None:
        _write_json(output_path, manifest)
    return manifest
