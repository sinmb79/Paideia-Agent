from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT


PUBLIC_RELEASE_READINESS_SCHEMA = "paideia-public-release-readiness/v1"

REQUIRED_PUBLIC_FILES = [
    "README.md",
    "README.ko.md",
    "SECURITY.md",
    "LICENSE",
    "pyproject.toml",
    ".github/workflows/ci.yml",
    "scripts/check_public_repo_hygiene.ps1",
    "docs/public_release_readiness.md",
    "docs/public_release_readiness.ko.md",
]

REQUIRED_CI_MARKERS = [
    'python -m pip install -e ".[dev]"',
    "python -m compileall src\\ai22b\\talent_foundry",
    "tests\\test_cli_smoke.py",
    "tests\\test_package_smoke.py",
    ".\\scripts\\check_public_repo_hygiene.ps1",
    "ai22b-talent-foundry build-llm-connection-profile",
    "ai22b-talent-foundry doctor-llm-adapters",
    "ai22b-talent-foundry run-chat-runtime-smoke",
    "ai22b-talent-foundry doctor-llm-live-readiness",
    "ai22b-talent-foundry doctor-package-install",
    "ai22b-talent-foundry doctor-first-run",
    "ai22b-talent-foundry doctor-runtime-contract",
]

REQUIRED_HYGIENE_MARKERS = [
    "missing_required_release_file",
    "missing_package_license_metadata",
    "local_windows_user_path",
    "generic_openai_secret",
    "private_key",
]

REQUIRED_README_LINKS = [
    "docs/public_release_readiness.md",
    "docs/public_release_readiness.ko.md",
    "README.ko.md",
]

REQUIRED_PACKAGE_SMOKE_MARKERS = [
    'metadata.distribution("paideia-agent")',
    'metadata.entry_points(group="console_scripts")',
]

REQUIRED_SECURITY_FRAGMENTS = [
    "data/private/**",
    "runs/**",
    ".env*",
    "check_public_repo_hygiene.ps1",
]

PUBLIC_SCAN_DIRS = [
    ".github",
    "data/public",
    "docs",
    "evals",
    "examples",
    "scripts",
    "src",
    "tests",
]

PUBLIC_SCAN_ROOT_FILES = [
    "LICENSE",
    "README.md",
    "README.ko.md",
    "SECURITY.md",
    "pyproject.toml",
]

PUBLIC_SCAN_EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
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
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)target/"),
]

_PRIVATE_USER = "sin" + "mb"
CONTENT_BLOCKLIST_PATTERNS = [
    ("local_windows_user_path", re.compile(r"C:[\\/]+Users[\\/]+" + re.escape(_PRIVATE_USER), re.I)),
    ("local_posix_user_path", re.compile(r"[\\/]Users[\\/]+" + re.escape(_PRIVATE_USER), re.I)),
    ("openai_key_assignment", re.compile(r"OPENAI_API_KEY\s*=\s*['\"]?[^'\",\s]{8,}", re.I)),
    ("generic_openai_secret", re.compile(r"sk-[A-Za-z0-9_-]{32,}")),
    ("github_pat", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("private_key", re.compile(r"BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY")),
    ("refresh_token", re.compile(r"refresh_token\s*[:=]", re.I)),
    ("auth_token", re.compile(r"auth_token\s*[:=]", re.I)),
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def _missing_files(repo_root: Path) -> list[str]:
    return [path for path in REQUIRED_PUBLIC_FILES if not (repo_root / path).is_file()]


def _line_has(text: str, needle: str) -> bool:
    normalized = text.replace("/", "\\") if "\\" in needle else text
    return needle in normalized


def _optional_dependency_groups(pyproject_text: str) -> list[str]:
    groups: list[str] = []
    in_optional = False
    for raw_line in pyproject_text.splitlines():
        line = raw_line.strip()
        if line == "[project.optional-dependencies]":
            in_optional = True
            continue
        if in_optional and line.startswith("[") and line.endswith("]"):
            break
        if in_optional:
            match = re.match(r"([A-Za-z0-9_-]+)\s*=", line)
            if match:
                groups.append(match.group(1))
    return groups


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_excluded_scan_path(path: Path) -> bool:
    return any(part in PUBLIC_SCAN_EXCLUDED_DIR_NAMES for part in path.parts)


def _public_candidate_files(root: Path) -> list[Path]:
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
            if not path.is_file() or _is_excluded_scan_path(path.relative_to(root)):
                continue
            if path.suffix.casefold() not in PUBLIC_SCAN_TEXT_SUFFIXES:
                continue
            candidates.append(path)
    return sorted(set(candidates), key=lambda item: _safe_rel(item, root))


def _scan_public_candidate_files(root: Path) -> dict[str, Any]:
    candidate_files = _public_candidate_files(root)
    issues: list[dict[str, Any]] = []

    for path in candidate_files:
        rel = _safe_rel(path, root)
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
            text = _read_text(path)
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

    return {
        "candidate_file_count": len(candidate_files),
        "candidate_roots": PUBLIC_SCAN_ROOT_FILES + PUBLIC_SCAN_DIRS,
        "issue_count": len(issues),
        "issues": issues,
    }


def _check(
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    details: dict[str, Any] | None = None,
    issue: str | None = None,
) -> None:
    checks.append({"id": check_id, "passed": passed, "details": details or {}})
    if not passed:
        issues.append(
            {
                "check": check_id,
                "issue": issue or "check_failed",
                "details": details or {},
            }
        )


def audit_public_release_readiness(
    repo_root: Path | None = None,
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Audit source-repository readiness for public preview release.

    This local file/metadata audit does not call the network, execute
    subprocesses, inspect private runtime outputs, or read ignored private data.
    """

    root = (repo_root or PROJECT_ROOT).resolve()
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    missing = _missing_files(root)
    _check(
        checks,
        issues,
        check_id="required_public_files",
        passed=not missing,
        details={"missing": missing, "required": REQUIRED_PUBLIC_FILES},
        issue="missing_required_public_release_file",
    )

    pyproject_path = root / "pyproject.toml"
    pyproject_text = _read_text(pyproject_path) if pyproject_path.is_file() else ""
    optional_groups = _optional_dependency_groups(pyproject_text)
    _check(
        checks,
        issues,
        check_id="package_metadata",
        passed=(
            'name = "paideia-agent"' in pyproject_text
            and 'license = { file = "LICENSE" }' in pyproject_text
            and "License :: OSI Approved :: MIT License" in pyproject_text
            and "dependencies = []" in pyproject_text
            and {"dev", "live-llm", "local-llm", "rag", "fine-tune", "all"} <= set(optional_groups)
        ),
        details={
            "license_file_declared": 'license = { file = "LICENSE" }' in pyproject_text,
            "direct_dependencies_empty": "dependencies = []" in pyproject_text,
            "optional_dependency_groups": optional_groups,
        },
        issue="package_metadata_not_release_ready",
    )

    license_text = _read_text(root / "LICENSE") if (root / "LICENSE").is_file() else ""
    _check(
        checks,
        issues,
        check_id="license_file",
        passed="MIT License" in license_text and "THE SOFTWARE IS PROVIDED" in license_text,
        details={"license": "MIT" if "MIT License" in license_text else "missing_or_unknown"},
        issue="license_file_missing_or_unrecognized",
    )

    package_smoke_path = root / "tests" / "test_package_smoke.py"
    package_smoke_text = _read_text(package_smoke_path) if package_smoke_path.is_file() else ""
    missing_package_smoke = [
        marker for marker in REQUIRED_PACKAGE_SMOKE_MARKERS if marker not in package_smoke_text
    ]
    _check(
        checks,
        issues,
        check_id="installed_package_metadata_smoke",
        passed=not missing_package_smoke,
        details={
            "test_path": "tests/test_package_smoke.py",
            "missing_markers": missing_package_smoke,
            "required_markers": REQUIRED_PACKAGE_SMOKE_MARKERS,
        },
        issue="installed_package_metadata_smoke_missing",
    )

    ci_path = root / ".github" / "workflows" / "ci.yml"
    ci_text = _read_text(ci_path) if ci_path.is_file() else ""
    missing_ci = [marker for marker in REQUIRED_CI_MARKERS if not _line_has(ci_text, marker)]
    _check(
        checks,
        issues,
        check_id="ci_release_gates",
        passed=not missing_ci,
        details={"missing_markers": missing_ci, "required_markers": REQUIRED_CI_MARKERS},
        issue="ci_release_gate_missing",
    )

    hygiene_path = root / "scripts" / "check_public_repo_hygiene.ps1"
    hygiene_text = _read_text(hygiene_path) if hygiene_path.is_file() else ""
    missing_hygiene = [marker for marker in REQUIRED_HYGIENE_MARKERS if marker not in hygiene_text]
    _check(
        checks,
        issues,
        check_id="public_hygiene_policy",
        passed=not missing_hygiene,
        details={"missing_markers": missing_hygiene, "required_markers": REQUIRED_HYGIENE_MARKERS},
        issue="public_hygiene_policy_missing",
    )

    readme_text = _read_text(root / "README.md") if (root / "README.md").is_file() else ""
    missing_readme_links = [link for link in REQUIRED_README_LINKS if link not in readme_text]
    _check(
        checks,
        issues,
        check_id="readme_release_links",
        passed=not missing_readme_links,
        details={"missing_links": missing_readme_links, "required_links": REQUIRED_README_LINKS},
        issue="readme_release_link_missing",
    )

    security_text = _read_text(root / "SECURITY.md") if (root / "SECURITY.md").is_file() else ""
    missing_security = [fragment for fragment in REQUIRED_SECURITY_FRAGMENTS if fragment not in security_text]
    _check(
        checks,
        issues,
        check_id="security_private_by_default_policy",
        passed=not missing_security,
        details={"missing_fragments": missing_security, "required_fragments": REQUIRED_SECURITY_FRAGMENTS},
        issue="security_policy_fragment_missing",
    )

    public_scan = _scan_public_candidate_files(root)
    _check(
        checks,
        issues,
        check_id="public_candidate_content_scan",
        passed=public_scan["issue_count"] == 0,
        details={
            "candidate_file_count": public_scan["candidate_file_count"],
            "candidate_roots": public_scan["candidate_roots"],
            "issue_count": public_scan["issue_count"],
            "issues": public_scan["issues"],
        },
        issue="public_candidate_content_or_path_issue",
    )

    report = {
        "schema": PUBLIC_RELEASE_READINESS_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root_name": root.name,
        "status": "passed" if not issues else "failed",
        "passed": not issues,
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "failed_count": len(issues),
            "required_public_file_count": len(REQUIRED_PUBLIC_FILES),
            "public_candidate_file_count": public_scan["candidate_file_count"],
            "public_candidate_issue_count": public_scan["issue_count"],
            "network_call_performed": False,
            "subprocess_executed": False,
            "private_runtime_outputs_scanned": False,
        },
        "issues": issues,
        "policy": {
            "scope": "source_repository_public_preview_readiness",
            "private_data_policy": "do_not_scan_or_export_private_runtime_state",
            "generated_agent_bundle_policy": "separate_bundle_doctor_and_checksum_gate",
            "secret_values_exported": False,
        },
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
