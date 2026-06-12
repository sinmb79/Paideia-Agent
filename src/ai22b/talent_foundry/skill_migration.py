from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.closed_ecosystem import build_closed_growth_contract


EXTERNAL_REFERENCE_INTAKE_REPORT_SCHEMA = "ai22b-paideia-external-reference-intake/v1"
EXTERNAL_REFERENCE_ASSET_SCHEMA = "ai22b-paideia-external-reference-asset/v1"
COMPATIBILITY_PROFILE_SCHEMA = "paideia-external-reference-compatibility-profile/v1"
REFERENCE_REVIEW_CARD_SCHEMA = "paideia-external-reference-review-card/v1"
MAX_COPY_BYTES = 5 * 1024 * 1024
ALLOWED_SOURCE_RUNTIMES = {"generic", "hermes", "openclaw"}
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
SKIP_DIRS_CASEFOLD = {name.casefold() for name in SKIP_DIRS}
SENSITIVE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "id_ed25519",
    "id_rsa",
}
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


def _normalize_source_runtime(source_runtime: str) -> str:
    runtime = str(source_runtime or "generic").strip().casefold()
    if runtime not in ALLOWED_SOURCE_RUNTIMES:
        allowed = ", ".join(sorted(ALLOWED_SOURCE_RUNTIMES))
        raise ValueError(f"source_runtime must be one of: {allowed}")
    return runtime


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


def _is_skipped_dir_name(name: str) -> bool:
    return name.casefold() in SKIP_DIRS_CASEFOLD


def _has_skipped_path_component(path: Path) -> bool:
    return any(_is_skipped_dir_name(part) for part in path.parts)


def _relative_child_path(parent_rel: Path, name: str) -> str:
    return (parent_rel / name).as_posix() if parent_rel.parts else name


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
    source_runtime = _normalize_source_runtime(source_runtime)
    source_path = source_path.resolve()
    if _has_skipped_path_component(source_path):
        return []
    if source_path.is_file():
        source_path = source_path.parent
    if _has_skipped_path_component(source_path):
        return []
    candidates: dict[Path, dict[str, Any]] = {}
    marker_names = {"skill.md", "skill.yaml", "skill.yml", "hermes.yaml", "hermes.yml"}
    for current_dir, dir_names, file_names in os.walk(source_path):
        current_path = Path(current_dir)
        try:
            current_path.relative_to(source_path)
        except ValueError:
            continue
        dir_names[:] = [name for name in dir_names if not _is_skipped_dir_name(name)]
        for file_name in file_names:
            if file_name.casefold() not in marker_names:
                continue
            path = current_path / file_name
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


def _is_sensitive_file(rel: Path) -> bool:
    name = rel.name.casefold()
    if name in SENSITIVE_FILE_NAMES:
        return True
    return name.endswith((".pem", ".key", ".p12", ".pfx")) or any(
        token in name
        for token in ("credential", "secret", "private-key", "private_key", "access-token", "auth-token")
    )


def _reference_copy_path(rel: Path) -> Path:
    if rel.name.casefold() == "skill.md":
        return rel.with_name("SOURCE_SKILL_REFERENCE.md")
    return rel


def _copy_skill_tree(source_dir: Path, target_dir: Path) -> tuple[list[str], list[dict[str, str]], list[dict[str, str]]]:
    copied: list[str] = []
    skipped: list[dict[str, str]] = []
    risks: list[dict[str, str]] = []
    source_dir = source_dir.resolve()
    if _has_skipped_path_component(source_dir):
        return (
            copied,
            [{"path": source_dir.name or ".", "reason": "skipped_source_directory"}],
            [
                {
                    "risk_id": "skipped_source_directory",
                    "file": source_dir.name or ".",
                    "excerpt": "source path is inside a skipped VCS, virtualenv, build, or dependency directory",
                }
            ],
        )
    source_root = source_dir
    for current_dir, dir_names, file_names in os.walk(source_dir):
        current_path = Path(current_dir)
        try:
            parent_rel = current_path.relative_to(source_root)
        except ValueError:
            skipped.append({"path": str(current_path), "reason": "outside_source_root"})
            continue
        skipped_dirs = [name for name in dir_names if _is_skipped_dir_name(name)]
        for name in skipped_dirs:
            skipped.append({"path": _relative_child_path(parent_rel, name), "reason": "skipped_directory"})
        dir_names[:] = [name for name in dir_names if not _is_skipped_dir_name(name)]
        for file_name in file_names:
            path = current_path / file_name
            rel = path.relative_to(source_root)
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
            if _is_sensitive_file(rel):
                skipped.append({"path": rel.as_posix(), "reason": "sensitive_file_not_copied"})
                risks.append(
                    {
                        "risk_id": "sensitive_file_name",
                        "file": rel.as_posix(),
                        "excerpt": "filename indicates credentials, tokens, private keys, or local secrets",
                    }
                )
                continue
            if size > MAX_COPY_BYTES:
                skipped.append({"path": rel.as_posix(), "reason": "file_too_large"})
                continue
            reference_rel = _reference_copy_path(rel)
            destination = target_dir / "source" / reference_rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            copied.append(reference_rel.as_posix())
            risks.extend(_scan_file(path))
    return copied, skipped, risks


def _wrapper_skill_md(package: dict[str, Any], manifest_name: str, compatibility_name: str) -> str:
    return f"""# External Reference Quarantine Card

This third-party procedure was copied into Paideia's external-reference quarantine from
`{package['source_runtime']}`. It is not an active Paideia skill and must not be treated
as a plug-in for a raised talent.

Original format: `{package['source_format']}`
Original entry file: `{package.get('entry_file') or 'unknown'}`

Paideia policy:

- Never execute scripts from this source as a Paideia skill.
- Treat third-party skills as untrusted reference material.
- Use this document as curriculum stimulus, not as an active Paideia skill.
- Never expose this source as `SKILL.md` inside a Paideia kit.
- Do not import this source's memory, profile, prompts, workflow, or reasoning style as Paideia identity.
- Convert useful ideas into Paideia-native training exercises, guided practice, exams, and reviewed procedures.
- Promote only reviewed summaries or successful Paideia work evidence into the learning ledger.

Review manifest: `{manifest_name}`
Compatibility profile: `{compatibility_name}`
"""


def _education_axes_for(package: dict[str, Any]) -> list[str]:
    text = f"{package.get('name', '')} {package.get('description', '')}".casefold()
    axes = ["tool_and_workflow", "safety_and_identity"]
    if any(token in text for token in ["research", "finance", "code", "data", "report", "analysis"]):
        axes.append("domain_mastery")
    if any(token in text for token in ["chat", "email", "social", "message"]):
        axes.append("language_pragmatics")
    return list(dict.fromkeys(axes))


def _script_files(copied_files: list[str]) -> list[str]:
    return [
        path
        for path in copied_files
        if Path(path).suffix.casefold() in {".ps1", ".sh", ".bash", ".cmd", ".bat", ".js", ".mjs", ".py"}
    ]


def _capability_requests(
    *,
    copied_files: list[str],
    skipped_files: list[dict[str, str]],
    risk_flags: list[str],
) -> list[dict[str, Any]]:
    script_files = _script_files(copied_files)
    sensitive_skip_count = sum(1 for item in skipped_files if item.get("reason") == "sensitive_file_not_copied")
    requests: list[dict[str, Any]] = [
        {
            "id": "reference_read",
            "status": "allowed_for_review",
            "reason": "Copied files may be read as quarantined reference material only.",
            "evidence": {"copied_file_count": len(copied_files)},
        }
    ]
    if copied_files:
        requests.append(
            {
                "id": "filesystem_read",
                "status": "paideia_rewrite_required",
                "reason": "Any useful local-file assumption must be rewritten as a Paideia-native exercise or procedure.",
                "evidence": {"copied_file_count": len(copied_files)},
            }
        )
    if script_files:
        requests.append(
            {
                "id": "subprocess_execution",
                "status": "blocked_for_direct_external_use",
                "reason": "Script-like files are copied as reference only and must never execute as external skills.",
                "evidence": {"script_files": script_files[:20]},
            }
        )
    if any(flag in risk_flags for flag in ["remote_shell_pipe", "network_listener"]):
        requests.append(
            {
                "id": "network_access",
                "status": "blocked_for_direct_external_use",
                "reason": "Network-related patterns were detected in quarantined reference source.",
                "evidence": {"risk_flags": [flag for flag in risk_flags if flag in {"remote_shell_pipe", "network_listener"}]},
            }
        )
    if "credential_access" in risk_flags or sensitive_skip_count:
        requests.append(
            {
                "id": "credential_access",
                "status": "blocked_until_rewritten",
                "reason": "Credential-like names or patterns require removal before any Paideia-native rewrite.",
                "evidence": {
                    "credential_pattern_detected": "credential_access" in risk_flags,
                    "sensitive_file_skip_count": sensitive_skip_count,
                },
            }
        )
    if "recursive_delete" in risk_flags:
        requests.append(
            {
                "id": "destructive_filesystem",
                "status": "blocked_until_rewritten",
                "reason": "Recursive deletion patterns are incompatible with Paideia-native training material.",
                "evidence": {"risk_flags": ["recursive_delete"]},
            }
        )
    return requests


def _adapter_strategy(source_runtime: str) -> dict[str, Any]:
    runtime = source_runtime.casefold()
    if runtime == "hermes":
        return {
            "source_runtime": "hermes",
            "recommended_adapter": "none_reference_only",
            "notes": [
                "Preserve the original Hermes skill only as external reference material.",
                "Extract useful ideas into Paideia-reviewed curriculum, practice, and exam steps.",
                "Do not import Hermes memory/profile state as Paideia identity.",
            ],
        }
    if runtime == "openclaw":
        return {
            "source_runtime": "openclaw",
            "recommended_adapter": "none_reference_only",
            "notes": [
                "Map workspace assumptions to Paideia-native training tasks instead of wrappers.",
                "Keep gateway/channel behavior disabled until separate channel policy review.",
                "Treat active-memory references as candidates, not automatic memory promotion.",
            ],
        }
    return {
        "source_runtime": source_runtime,
        "recommended_adapter": "none_reference_only",
        "notes": [
            "Treat the imported folder as third-party reference material.",
            "Create a Paideia-specific exercise or procedure only after review, practice, and test evidence.",
        ],
    }


def _compatibility_profile(
    package: dict[str, Any],
    *,
    copied_files: list[str],
    skipped_files: list[dict[str, str]],
    risk_flags: list[str],
) -> dict[str, Any]:
    capability_requests = _capability_requests(
        copied_files=copied_files,
        skipped_files=skipped_files,
        risk_flags=risk_flags,
    )
    return {
        "schema": COMPATIBILITY_PROFILE_SCHEMA,
        "created_at_utc": _now(),
        "source_runtime": package["source_runtime"],
        "source_format": package["source_format"],
        "entry_file": package.get("entry_file"),
        "adapter_strategy": _adapter_strategy(str(package["source_runtime"])),
        "capability_requests": capability_requests,
        "internalization_gate": {
            "status": "locked_pending_paideia_rewrite_and_exam",
            "direct_external_activation_allowed": False,
            "paideia_native_procedure_allowed": False,
            "required_artifacts": [
                "REFERENCE.md",
                "paideia_external_reference_manifest.json",
                "paideia_reference_compatibility_profile.json",
                "paideia_reference_review.md",
                "paideia_rewrite_plan.json",
                "guided_practice_result.json",
                "timed_exam_result.json",
                "education_axis_promotion_review.json",
            ],
            "required_steps": [
                "Review copied source and risk flags.",
                "Extract only the useful idea, not the external skill procedure as-is.",
                "Rewrite useful ideas as Paideia-native training exercises or procedures.",
                "Run guided practice against the rewritten material.",
                "Run a timed exam or task trial.",
                "Attach review evidence before any Paideia memory or reasoning-kibo promotion.",
            ],
        },
        "conversion_plan": [
            {"stage": "external_reference_intake", "status": "completed"},
            {"stage": "idea_extraction", "status": "reference_only_pending_owner_review"},
            {"stage": "paideia_native_rewrite", "status": "required_before_any_use"},
            {"stage": "guided_practice", "status": "pending"},
            {"stage": "timed_exam_or_task_trial", "status": "pending"},
            {"stage": "education_axis_promotion_review", "status": "pending"},
            {"stage": "direct_external_skill_activation", "status": "forbidden"},
        ],
        "memory_policy": {
            "source_skill_as_reference_only": True,
            "promote_original_skill_text": False,
            "promote_execution_trace": False,
            "promote_reviewed_summary_only": True,
            "quarantine_failed_runs": True,
        },
        "llm_context_policy": {
            "include_original_source_by_default": False,
            "include_wrapper_summary": True,
            "include_only_after_owner_review": True,
        },
    }


def _review_card_md(manifest: dict[str, Any]) -> str:
    profile = manifest.get("compatibility_profile", {})
    requests = profile.get("capability_requests", []) if isinstance(profile.get("capability_requests"), list) else []
    request_lines = "\n".join(
        f"- `{item.get('id')}`: {item.get('status')} - {item.get('reason')}"
        for item in requests
        if isinstance(item, dict)
    )
    risk_lines = "\n".join(f"- `{flag}`" for flag in manifest.get("risk_flags", [])) or "- none"
    return f"""# External Reference Review Card

Schema: `{REFERENCE_REVIEW_CARD_SCHEMA}`

Reference: `{manifest.get('name')}`
Runtime: `{manifest.get('source_runtime')}`
Status: `{manifest.get('status')}`
Direct External Use: `forbidden`

## Compatibility Requests

{request_lines or "- `reference_read`: allowed_for_review"}

## Risk Flags

{risk_lines}

## Required Owner Decision

- Keep this source quarantined as reference material.
- Do not activate it as an external skill.
- Rewrite useful ideas as Paideia-native training, guided practice, and exam material.
- Promote only reviewed summaries, rewritten procedures, or successful Paideia work evidence into memory.
"""


def _skill_safety_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    risk_flags = list(manifest.get("risk_flags", []))
    copied_files = list(manifest.get("copied_files", []))
    skipped_files = list(manifest.get("skipped_files", []))
    return {
        "schema": "paideia-external-reference-safety-contract/v1",
        "status": "quarantined_reference_only",
        "direct_external_activation_allowed": False,
        "paideia_native_procedure_allowed_without_rewrite": False,
        "execute_reference_code": False,
        "active_skill_descriptor_created": False,
        "direct_external_skill_copy_allowed": False,
        "identity_injection_allowed": False,
        "memory_import_allowed": False,
        "reasoning_kibo_import_allowed": False,
        "active_skill_copy_allowed": False,
        "reference_only_until_paideia_rewrite": True,
        "requires_manual_boss_review": True,
        "requires_paideia_native_rewrite": True,
        "requires_guided_practice": True,
        "requires_timed_exam_or_task_trial": True,
        "dangerous_pattern_count": len(manifest.get("risk_matches", [])),
        "risk_flags": risk_flags,
        "copied_file_count": len(copied_files),
        "skipped_file_count": len(skipped_files),
        "sensitive_files_copied": False,
        "sensitive_file_skip_count": sum(
            1 for item in skipped_files if item.get("reason") == "sensitive_file_not_copied"
        ),
        "default_permissions": {
            "filesystem": "none_until_reviewed",
            "network": "blocked",
            "subprocess": "blocked",
            "credential_access": "blocked",
            "recursive_delete": "blocked",
            "identity_layer": "blocked",
            "memory_promotion": "reviewed_summary_only_after_rewrite",
        },
        "review_required_for": sorted(
            {
                "code_execution",
                "filesystem_access",
                "network_access",
                "subprocess_access",
                "memory_promotion",
                "identity_boundary",
                "paideia_native_rewrite",
                "compatibility_profile",
                "guided_practice",
                "timed_exam_or_task_trial",
                *(risk_flags or []),
            }
        ),
    }


def _intake_safety_contract(references: list[dict[str, Any]]) -> dict[str, Any]:
    risk_flags = sorted({flag for item in references for flag in item.get("risk_flags", [])})
    return {
        "schema": "paideia-external-reference-intake-safety-contract/v1",
        "status": "quarantined_reference_only",
        "reference_count": len(references),
        "all_external_references_non_executable": True,
        "external_code_executed": False,
        "sensitive_files_copied": False,
        "risk_flags": risk_flags,
        "internalization_policy": {
            "default_direct_use": "forbidden",
            "manual_boss_review_required": True,
            "paideia_native_rewrite_required": True,
            "guided_practice_required": True,
            "timed_exam_or_task_trial_required": True,
            "doctor_required_before_chat": True,
            "external_skill_identity_injection_allowed": False,
            "direct_external_skill_activation_allowed": False,
        },
        "default_permissions": {
            "filesystem": "none_until_reviewed",
            "network": "blocked",
            "subprocess": "blocked",
            "credential_access": "blocked",
            "identity_layer": "blocked",
            "memory_promotion": "reviewed_summary_only_after_rewrite",
        },
    }


def _intake_compatibility_summary(references: list[dict[str, Any]]) -> dict[str, Any]:
    request_ids = sorted(
        {
            request.get("id")
            for item in references
            for request in item.get("compatibility_profile", {}).get("capability_requests", [])
            if isinstance(request, dict) and request.get("id")
        }
    )
    return {
        "schema": "paideia-external-reference-compatibility-summary/v1",
        "reference_count": len(references),
        "internalization_locked_count": sum(
            1
            for item in references
            if item.get("compatibility_profile", {}).get("internalization_gate", {}).get("status")
            == "locked_pending_paideia_rewrite_and_exam"
        ),
        "all_internalization_gates_locked": all(
            item.get("compatibility_profile", {}).get("internalization_gate", {}).get(
                "direct_external_activation_allowed"
            )
            is False
            for item in references
        ),
        "capability_request_ids": request_ids,
        "source_runtimes": sorted({str(item.get("source_runtime")) for item in references}),
    }


def intake_external_agent_references(
    source_path: Path,
    *,
    paideia_kit_dir: Path,
    source_runtime: str = "generic",
    output_path: Path | None = None,
) -> dict[str, Any]:
    source_runtime = _normalize_source_runtime(source_runtime)
    source_path = source_path.resolve()
    paideia_kit_dir = paideia_kit_dir.resolve()
    packages = discover_external_agent_assets(source_path, source_runtime=source_runtime)
    references: list[dict[str, Any]] = []
    for index, package in enumerate(packages, start=1):
        source_dir = Path(package["source_dir"])
        slug = _slugify(str(package.get("slug") or source_dir.name), f"reference-{index}")
        target_dir = paideia_kit_dir / "references" / "external" / source_runtime / slug
        copied, skipped, risks = _copy_skill_tree(source_dir, target_dir)
        risk_flags = sorted({risk["risk_id"] for risk in risks})
        compatibility = _compatibility_profile(
            package,
            copied_files=copied,
            skipped_files=skipped,
            risk_flags=risk_flags,
        )
        manifest = {
            "schema": EXTERNAL_REFERENCE_ASSET_SCHEMA,
            "created_at_utc": _now(),
            "name": package["name"],
            "slug": slug,
            "source_runtime": source_runtime,
            "source_format": package["source_format"],
            "source_dir_name": source_dir.name,
            "entry_file": package.get("entry_file"),
            "direct_external_use": {
                "status": "forbidden",
                "reason": "external_sources_are_reference_material_not_paideia_skills",
                "paideia_native_rewrite_required": True,
            },
            "intake_mode": "quarantine_reference_rewrite_as_training_only",
            "closed_growth_contract": build_closed_growth_contract(
                context="external_reference_intake",
                source_runtime=source_runtime,
            ),
            "identity_policy": {
                "external_skill_identity_injection_allowed": False,
                "external_memory_import_allowed": False,
                "reasoning_kibo_import_allowed": False,
                "original_skill_is_reference_material": True,
                "paideia_identity_sources_only": [
                    "education_program",
                    "assessment_records",
                    "hiring_dossier",
                    "reasoning_kibo",
                    "memory_substrate",
                    "reviewed_work_growth",
                ],
            },
            "copied_files": copied,
            "skipped_files": skipped,
            "risk_flags": risk_flags,
            "risk_matches": risks[:50],
            "suggested_paideia_axes": _education_axes_for(package),
            "compatibility_profile": compatibility,
            "review_checklist": [
                "Read REFERENCE.md and copied source references before extracting ideas.",
                "Read paideia_reference_compatibility_profile.json and paideia_reference_review.md.",
                "Remove or rewrite remote shell installers.",
                "Map useful ideas into Paideia education axes.",
                "Run guided practice and a timed exam for rewritten material.",
                "Promote only reviewable successful usage summaries into the learning ledger.",
            ],
            "status": "quarantined_reference_only",
        }
        manifest["safety_contract"] = _skill_safety_contract(manifest)
        _write_json(target_dir / "paideia_external_reference_manifest.json", manifest)
        _write_json(target_dir / "paideia_reference_compatibility_profile.json", compatibility)
        (target_dir / "paideia_reference_review.md").write_text(_review_card_md(manifest), encoding="utf-8")
        (target_dir / "REFERENCE.md").write_text(
            _wrapper_skill_md(
                package,
                "paideia_external_reference_manifest.json",
                "paideia_reference_compatibility_profile.json",
            ),
            encoding="utf-8",
        )
        references.append(
            {
                "name": manifest["name"],
                "slug": slug,
                "source_runtime": source_runtime,
                "target": str(target_dir),
                "reference_document": str((target_dir / "REFERENCE.md").relative_to(paideia_kit_dir)),
                "active_skill_descriptor_created": False,
                "status": manifest["status"],
                "direct_external_use": manifest["direct_external_use"]["status"],
                "risk_flags": risk_flags,
                "compatibility_profile": {
                    "schema": compatibility["schema"],
                    "internalization_gate": compatibility["internalization_gate"],
                    "capability_requests": compatibility["capability_requests"],
                },
                "sensitive_file_skip_count": manifest["safety_contract"]["sensitive_file_skip_count"],
                "copied_file_count": len(copied),
            }
        )

    report = {
        "schema": EXTERNAL_REFERENCE_INTAKE_REPORT_SCHEMA,
        "created_at_utc": _now(),
        "source_runtime": source_runtime,
        "source": str(source_path),
        "paideia_kit_dir": str(paideia_kit_dir),
        "intake_policy": {
            "mode": "quarantine_reference_rewrite_as_training_only",
            "execute_external_code": False,
            "default_direct_use": "forbidden",
            "boss_review_required": True,
            "third_party_skills_trusted": False,
            "external_skills_are_reference_material": True,
            "paideia_native_rewrite_required": True,
            "guided_practice_required": True,
            "timed_exam_or_task_trial_required": True,
            "external_skill_identity_injection_allowed": False,
            "direct_skill_copy_allowed": False,
            "direct_external_skill_activation_allowed": False,
        },
        "closed_growth_contract": build_closed_growth_contract(
            context="external_reference_intake_report",
            source_runtime=source_runtime,
        ),
        "safety_contract": _intake_safety_contract(references),
        "compatibility_summary": _intake_compatibility_summary(references),
        "reference_count": len(references),
        "external_references": references,
    }
    output_path = output_path or paideia_kit_dir / "paideia_external_reference_intake_report.json"
    _write_json(output_path, report)
    _update_install_manifest(paideia_kit_dir, report)
    return report


def migrate_external_agent_assets(
    source_path: Path,
    *,
    paideia_kit_dir: Path,
    source_runtime: str = "generic",
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Compatibility wrapper for the old CLI/API name.

    Paideia no longer treats this path as skill migration. The old function name
    remains so existing local scripts fail soft, but it now writes the external
    reference intake contract and reference-only quarantine layout.
    """
    return intake_external_agent_references(
        source_path,
        paideia_kit_dir=paideia_kit_dir,
        source_runtime=source_runtime,
        output_path=output_path,
    )


def _update_install_manifest(paideia_kit_dir: Path, report: dict[str, Any]) -> None:
    manifest_path = paideia_kit_dir / "paideia_agent_install_manifest.json"
    if not manifest_path.exists():
        return
    manifest = _read_json(manifest_path)
    manifest.setdefault("entrypoints", {})["external_reference_quarantine"] = "references/external"
    manifest.setdefault("entrypoints", {})[
        "external_reference_intake_report"
    ] = "paideia_external_reference_intake_report.json"
    manifest["external_reference_policy"] = report["intake_policy"]
    manifest["external_reference_safety_contract"] = report["safety_contract"]
    manifest["external_reference_compatibility_summary"] = report["compatibility_summary"]
    manifest["external_reference_count"] = report["reference_count"]
    manifest["directories"] = sorted({*manifest.get("directories", []), "references"})
    _write_json(manifest_path, manifest)
