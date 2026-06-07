from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.public_inventory import (
    PUBLIC_SCAN_DIRS,
    PUBLIC_SCAN_ROOT_FILES,
    load_pyproject,
    optional_dependency_groups,
    public_candidate_files,
    read_text,
    safe_rel,
    scan_public_candidate_files,
)


PUBLIC_RELEASE_READINESS_SCHEMA = "paideia-public-release-readiness/v1"

REQUIRED_PUBLIC_FILES = [
    "README.md",
    "README.ko.md",
    "ROADMAP.md",
    "ROADMAP.ko.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.ko.md",
    "SECURITY.md",
    "LICENSE",
    "pyproject.toml",
    ".github/dependabot.yml",
    ".github/workflows/ci.yml",
    "scripts/check_public_repo_hygiene.ps1",
    "docs/security_threat_model.md",
    "docs/security_threat_model.ko.md",
    "docs/public_release_readiness.md",
    "docs/public_release_readiness.ko.md",
    "schemas/README.md",
    "schemas/first_run_doctor.v1.schema.json",
    "schemas/llm_client_result.v1.schema.json",
    "schemas/tool_execution_artifact_manifest.v1.schema.json",
    "schemas/reasoning_ledger_candidate.v1.schema.json",
    "schemas/hiring_dossier.v1.schema.json",
]

REQUIRED_CI_MARKERS = [
    "permissions:",
    "contents: read",
    "uses: actions/checkout@v5",
    "uses: actions/setup-python@v6",
    "uses: actions/upload-artifact@v6",
    'python -m pip install -e ".[dev]"',
    'python -m pip install -e ".[security]"',
    "python -m compileall src/ai22b/talent_foundry",
    "python -B -m pytest tests -q",
    "python -m build",
    "python -m bandit -q -r src",
    "python -m pip_audit . --skip-editable",
    "public-release-gate-reports",
    "security-reports",
    "ruff check src tests",
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
    "generic_local_windows_user_path",
    "generic_local_posix_user_path",
    "provider_secret_assignment",
    "generic_openai_secret",
    "private_key",
    "hidden_unicode_bidi_control",
]

REQUIRED_README_LINKS = [
    "docs/public_release_readiness.md",
    "docs/public_release_readiness.ko.md",
    "README.ko.md",
    "ROADMAP.md",
    "CONTRIBUTING.md",
    "docs/security_threat_model.md",
    "schemas/README.md",
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
    "docs/security_threat_model.md",
]

def _read_text(path: Path) -> str:
    return read_text(path)


def _missing_files(repo_root: Path) -> list[str]:
    return [path for path in REQUIRED_PUBLIC_FILES if not (repo_root / path).is_file()]


def _line_has(text: str, needle: str) -> bool:
    normalized = text.replace("/", "\\") if "\\" in needle else text
    return needle in normalized


def _safe_rel(path: Path, root: Path) -> str:
    return safe_rel(path, root)


def _public_candidate_files(root: Path) -> list[Path]:
    return public_candidate_files(root)


def _scan_public_candidate_files(root: Path) -> dict[str, Any]:
    return scan_public_candidate_files(root)


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
    pyproject = load_pyproject(pyproject_path) if pyproject_path.is_file() else {}
    project = pyproject.get("project", {}) if isinstance(pyproject.get("project"), dict) else {}
    license_field = project.get("license", {}) if isinstance(project.get("license"), dict) else {}
    dependencies = project.get("dependencies", [])
    classifiers = project.get("classifiers", [])
    optional_groups = optional_dependency_groups(pyproject)
    required_optional_groups = {"dev", "security", "live-llm", "local-llm", "rag", "fine-tune", "all"}
    _check(
        checks,
        issues,
        check_id="package_metadata",
        passed=(
            project.get("name") == "paideia-agent"
            and license_field.get("file") == "LICENSE"
            and "License :: OSI Approved :: MIT License" in classifiers
            and dependencies == []
            and required_optional_groups <= set(optional_groups)
        ),
        details={
            "package_name": project.get("name"),
            "license_file_declared": license_field.get("file") == "LICENSE",
            "direct_dependencies_empty": dependencies == [],
            "optional_dependency_groups": optional_groups,
            "missing_optional_dependency_groups": sorted(required_optional_groups - set(optional_groups)),
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
