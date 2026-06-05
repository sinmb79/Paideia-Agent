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

REQUIRED_SECURITY_FRAGMENTS = [
    "data/private/**",
    "runs/**",
    ".env*",
    "check_public_repo_hygiene.ps1",
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
