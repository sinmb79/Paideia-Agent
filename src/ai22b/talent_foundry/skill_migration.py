from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MIGRATION_REPORT_SCHEMA = "ai22b-paideia-external-skill-migration/v1"
IMPORTED_SKILL_SCHEMA = "ai22b-paideia-imported-skill/v1"
MAX_COPY_BYTES = 5 * 1024 * 1024
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
DANGEROUS_PATTERNS = {
    "remote_shell_pipe": re.compile(r"(curl|wget|irm|iwr|Invoke-WebRequest|Invoke-RestMethod).{0,120}(\|\s*(bash|sh|iex|Invoke-Expression))", re.I | re.S),
    "powershell_execute_expression": re.compile(r"\b(iex|Invoke-Expression)\b", re.I),
    "recursive_delete": re.compile(r"\b(rm\s+-rf|Remove-Item\b.{0,80}-Recurse)\b", re.I | re.S),
    "credential_access": re.compile(r"(OPENAI_API_KEY|api[_-]?key|secret|token|wallet|private[_-]?key|cookies?|browser\s+data)", re.I),
    "network_listener": re.compile(r"(listen\(|createServer\(|0\.0\.0\.0|localhost:\d+|127\.0\.0\.1:\d+)", re.I),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(value: str, fallback: str) -> str:
    text = re.sub(r"[^A-Za-z0-9가-힣._-]+", "-", value.strip()).strip("-._")
    return text[:80] or fallback


def _read_text_limited(path: Path, limit: int = 200_000) -> str:
    try:
        data = path.read_bytes()[:limit]
    except OSError:
        return ""
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _frontmatter(markdown: str) -> dict[str, str]:
    if not markdown.startswith("---"):
        return {}
    end = markdown.find("\n---", 3)
    if end == -1:
        return {}
    block = markdown[3:end].strip()
    parsed: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip().strip("\"'")
    return parsed


def _detect_format(skill_dir: Path) -> tuple[str, Path]:
    for name in ["SKILL.md", "skill.md"]:
        path = skill_dir / name
        if path.exists():
            return "skill_md", path
    for name in ["skill.yaml", "skill.yml", "hermes.yaml", "hermes.yml"]:
        path = skill_dir / name
        if path.exists():
            return "skill_yaml", path
    for name in ["README.md", "readme.md"]:
        path = skill_dir / name
        if path.exists():
            return "generic_folder", path
    return "generic_folder", skill_dir


def discover_external_agent_assets(source_path: Path, *, source_runtime: str = "generic") -> list[dict[str, Any]]:
    source_path = source_path.resolve()
    if source_path.is_file():
        source_path = source_path.parent
    candidates: dict[Path, dict[str, Any]] = {}
    marker_names = {"skill.md", "skill.yaml", "skill.yml", "hermes.yaml", "hermes.yml"}
    for path in source_path.rglob("*"):
        if not path.is_file():
            continue
        if path.name.casefold() not in marker_names:
            continue
        skill_dir = path.parent.resolve()
        if skill_dir in candidates:
            continue
        source_format, entry = _detect_format(skill_dir)
        text = _read_text_limited(entry) if entry.is_file() else ""
        meta = _frontmatter(text)
        title = meta.get("name") or meta.get("title") or skill_dir.name
        description = meta.get("description") or meta.get("summary") or ""
        candidates[skill_dir] = {
            "source_runtime": source_runtime,
            "source_dir": str(skill_dir),
            "source_format": source_format,
            "entry_file": entry.name if entry.is_file() else None,
            "name": title,
            "slug": _slugify(title, skill_dir.name),
            "description": description,
        }
    if not candidates and source_path.exists():
        source_format, entry = _detect_format(source_path)
        text = _read_text_limited(entry) if entry.is_file() else ""
        meta = _frontmatter(text)
        title = meta.get("name") or meta.get("title") or source_path.name
        candidates[source_path] = {
            "source_runtime": source_runtime,
            "source_dir": str(source_path),
            "source_format": source_format,
            "entry_file": entry.name if entry.is_file() else None,
            "name": title,
            "slug": _slugify(title, source_path.name),
            "description": meta.get("description") or meta.get("summary") or "",
        }
    return sorted(candidates.values(), key=lambda item: item["slug"])


def _scan_file(path: Path) -> list[dict[str, str]]:
    text = _read_text_limited(path)
    matches: list[dict[str, str]] = []
    if not text:
        return matches
    for risk_id, pattern in DANGEROUS_PATTERNS.items():
        for match in pattern.finditer(text):
            matches.append(
                {
                    "risk_id": risk_id,
                    "file": path.name,
                    "excerpt": match.group(0)[:160],
                }
            )
    return matches


def _copy_skill_tree(source_dir: Path, target_dir: Path) -> tuple[list[str], list[dict[str, str]], list[dict[str, str]]]:
    copied: list[str] = []
    skipped: list[dict[str, str]] = []
    risks: list[dict[str, str]] = []
    source_dir = source_dir.resolve()
    source_root = source_dir
    for path in source_dir.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(source_root).parts):
            if path.is_dir():
                skipped.append({"path": str(path.relative_to(source_root)), "reason": "skipped_directory"})
            continue
        if not path.is_file():
            continue
        try:
            resolved = path.resolve()
        except OSError:
            skipped.append({"path": str(path), "reason": "resolve_failed"})
            continue
        if source_root not in [resolved, *resolved.parents]:
            skipped.append({"path": str(path), "reason": "symlink_or_realpath_outside_skill"})
            continue
        try:
            size = path.stat().st_size
        except OSError:
            skipped.append({"path": str(path.relative_to(source_root)), "reason": "stat_failed"})
            continue
        rel = path.relative_to(source_root)
        if size > MAX_COPY_BYTES:
            skipped.append({"path": rel.as_posix(), "reason": "file_too_large"})
            continue
        destination = target_dir / "source" / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied.append(rel.as_posix())
        risks.extend(_scan_file(path))
    return copied, skipped, risks


def _wrapper_skill_md(package: dict[str, Any], manifest_name: str) -> str:
    return f"""---
name: "Imported {package['name']}"
description: "Wrapped external {package['source_runtime']} skill. Disabled until Boss review."
---

# Imported Skill Wrapper

This skill was imported from `{package['source_runtime']}` and is not active by default.

Original format: `{package['source_format']}`
Original entry file: `{package.get('entry_file') or 'unknown'}`

Paideia policy:

- Do not execute scripts from this skill until `paideia_skill_manifest.json` is reviewed.
- Treat third-party skills as untrusted local code.
- Use this wrapper as a reference document until the Boss explicitly enables it.
- Convert useful procedures into Paideia education axes or reviewed procedural skills after testing.

Review manifest: `{manifest_name}`
"""


def _education_axes_for(package: dict[str, Any]) -> list[str]:
    text = f"{package.get('name', '')} {package.get('description', '')}".casefold()
    axes = ["tool_and_workflow", "safety_and_identity"]
    if any(token in text for token in ["research", "finance", "code", "data", "report", "analysis"]):
        axes.append("domain_mastery")
    if any(token in text for token in ["chat", "email", "social", "message"]):
        axes.append("language_pragmatics")
    return list(dict.fromkeys(axes))


def migrate_external_agent_assets(
    source_path: Path,
    *,
    paideia_kit_dir: Path,
    source_runtime: str = "generic",
    output_path: Path | None = None,
) -> dict[str, Any]:
    source_path = source_path.resolve()
    paideia_kit_dir = paideia_kit_dir.resolve()
    packages = discover_external_agent_assets(source_path, source_runtime=source_runtime)
    imported: list[dict[str, Any]] = []
    for index, package in enumerate(packages, start=1):
        source_dir = Path(package["source_dir"])
        slug = _slugify(str(package.get("slug") or source_dir.name), f"skill-{index}")
        target_dir = paideia_kit_dir / "skills" / "imported" / source_runtime / slug
        copied, skipped, risks = _copy_skill_tree(source_dir, target_dir)
        risk_flags = sorted({risk["risk_id"] for risk in risks})
        manifest = {
            "schema": IMPORTED_SKILL_SCHEMA,
            "created_at_utc": _now(),
            "name": package["name"],
            "slug": slug,
            "source_runtime": source_runtime,
            "source_format": package["source_format"],
            "source_dir_name": source_dir.name,
            "entry_file": package.get("entry_file"),
            "activation": {
                "status": "disabled",
                "reason": "imported_external_skill_requires_boss_review",
                "allowlist_required": True,
            },
            "migration_mode": "wrap_quarantine_doctor_then_allowlist",
            "copied_files": copied,
            "skipped_files": skipped,
            "risk_flags": risk_flags,
            "risk_matches": risks[:50],
            "suggested_paideia_axes": _education_axes_for(package),
            "review_checklist": [
                "Read SKILL.md and scripts before enabling.",
                "Remove or rewrite remote shell installers.",
                "Confirm file/network permissions needed by the skill.",
                "Run inside a disposable workspace before promotion.",
                "Promote only reviewable successful usage summaries into the learning ledger.",
            ],
            "status": "quarantined_pending_boss_review",
        }
        _write_json(target_dir / "paideia_skill_manifest.json", manifest)
        (target_dir / "SKILL.md").write_text(
            _wrapper_skill_md(package, "paideia_skill_manifest.json"),
            encoding="utf-8",
        )
        imported.append(
            {
                "name": manifest["name"],
                "slug": slug,
                "target": str(target_dir),
                "status": manifest["status"],
                "activation": manifest["activation"]["status"],
                "risk_flags": risk_flags,
                "copied_file_count": len(copied),
            }
        )

    report = {
        "schema": MIGRATION_REPORT_SCHEMA,
        "created_at_utc": _now(),
        "source_runtime": source_runtime,
        "source": str(source_path),
        "paideia_kit_dir": str(paideia_kit_dir),
        "migration_policy": {
            "mode": "wrap_quarantine_doctor_then_allowlist",
            "execute_imported_code": False,
            "default_activation": "disabled",
            "boss_review_required": True,
            "third_party_skills_trusted": False,
        },
        "imported_count": len(imported),
        "imported_skills": imported,
    }
    output_path = output_path or paideia_kit_dir / "paideia_skill_migration_report.json"
    _write_json(output_path, report)
    _update_install_manifest(paideia_kit_dir, report)
    return report


def _update_install_manifest(paideia_kit_dir: Path, report: dict[str, Any]) -> None:
    manifest_path = paideia_kit_dir / "paideia_agent_install_manifest.json"
    if not manifest_path.exists():
        return
    manifest = _read_json(manifest_path)
    manifest.setdefault("entrypoints", {})["imported_skills"] = "skills/imported"
    manifest.setdefault("entrypoints", {})["skill_migration_report"] = "paideia_skill_migration_report.json"
    manifest["imported_skill_policy"] = report["migration_policy"]
    manifest["imported_skill_count"] = report["imported_count"]
    manifest["directories"] = sorted({*manifest.get("directories", []), "skills"})
    _write_json(manifest_path, manifest)
