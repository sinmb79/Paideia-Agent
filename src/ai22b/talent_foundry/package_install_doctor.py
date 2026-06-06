from __future__ import annotations

import importlib
import json
import re
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from ai22b.config import PROJECT_ROOT
from ai22b.talent_foundry.source_sbom import _load_pyproject


PACKAGE_INSTALL_DOCTOR_SCHEMA = "paideia-package-install-doctor/v1"
REQUIRED_OPTIONAL_GROUPS = {"dev", "live-llm", "local-llm", "rag", "fine-tune", "all"}
FORBIDDEN_METADATA_FRAGMENTS = (
    "C:\\Users\\",
    "/Users/",
    "file://",
    "../",
    "data/private",
    "models/",
    ".env",
)
METADATA_SECRET_PATTERNS = {
    "openai_api_key_assignment": re.compile(r"OPENAI_API_KEY\s*=", re.I),
    "anthropic_api_key_assignment": re.compile(r"ANTHROPIC_API_KEY\s*=", re.I),
    "openai_secret_key_pattern": re.compile(r"sk-[A-Za-z0-9_-]{16,}", re.I),
}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    *,
    details: dict[str, Any] | None = None,
    severity: str = "error",
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": "passed" if passed else "failed",
            "passed": passed,
            "severity": severity,
            "details": details or {},
        }
    )


def _project(root: Path) -> dict[str, Any]:
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        return {}
    return _load_pyproject(pyproject_path).get("project", {})


def _entry_points_for_distribution(distribution: metadata.Distribution | None) -> dict[str, str]:
    if distribution is None:
        return {}
    return {
        entry.name: entry.value
        for entry in distribution.entry_points
        if entry.group == "console_scripts"
    }


def _installed_console_scripts(script_names: set[str]) -> dict[str, str]:
    return {
        entry.name: entry.value
        for entry in metadata.entry_points(group="console_scripts")
        if entry.name in script_names
    }


def _callable_targets(scripts: dict[str, str]) -> tuple[bool, list[dict[str, str]]]:
    failures: list[dict[str, str]] = []
    for name, target in scripts.items():
        if ":" not in target:
            failures.append({"script": name, "target": target, "reason": "missing_colon"})
            continue
        module_name, function_name = target.split(":", 1)
        try:
            function = getattr(importlib.import_module(module_name), function_name)
        except Exception as exc:
            failures.append(
                {
                    "script": name,
                    "target": target,
                    "reason": type(exc).__name__,
                }
            )
            continue
        if not callable(function):
            failures.append({"script": name, "target": target, "reason": "target_not_callable"})
    return not failures, failures


def _metadata_hygiene(pyproject_text: str, distribution: metadata.Distribution | None) -> dict[str, Any]:
    metadata_text = ""
    if distribution is not None:
        metadata_text = "\n".join(f"{key}: {value}" for key, value in distribution.metadata.items())
    pyproject_hits = [fragment for fragment in FORBIDDEN_METADATA_FRAGMENTS if fragment in pyproject_text]
    metadata_local_hits = [
        fragment
        for fragment in ("C:\\Users\\", "/Users/", "file://")
        if fragment in metadata_text
    ]
    metadata_secret_hits = [
        name
        for name, pattern in METADATA_SECRET_PATTERNS.items()
        if pattern.search(metadata_text)
    ]
    return {
        "forbidden_fragment_count": len(pyproject_hits) + len(metadata_local_hits) + len(metadata_secret_hits),
        "pyproject_forbidden_fragments": pyproject_hits,
        "metadata_local_path_fragments": metadata_local_hits,
        "metadata_secret_fragments": metadata_secret_hits,
        "metadata_policy_path_mentions_allowed": True,
        "local_absolute_paths_exported": bool(metadata_local_hits),
    }


def doctor_package_install(
    repo_root: Path | None = None,
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Verify the current environment's Paideia package install without subprocesses."""

    root = (repo_root or PROJECT_ROOT).resolve()
    project = _project(root)
    package_name = str(project.get("name", "paideia-agent"))
    pyproject_path = root / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8") if pyproject_path.exists() else ""
    scripts = project.get("scripts", {}) if isinstance(project.get("scripts"), dict) else {}
    optional = project.get("optional-dependencies", {}) if isinstance(project.get("optional-dependencies"), dict) else {}
    checks: list[dict[str, Any]] = []

    try:
        distribution = metadata.distribution(package_name)
        distribution_error = None
    except metadata.PackageNotFoundError as exc:
        distribution = None
        distribution_error = type(exc).__name__

    distribution_scripts = _entry_points_for_distribution(distribution)
    installed_scripts = _installed_console_scripts(set(scripts))
    targets_callable, callable_failures = _callable_targets(scripts)
    hygiene = _metadata_hygiene(pyproject_text, distribution)

    _check(
        checks,
        "pyproject_package_metadata_readable",
        bool(project)
        and project.get("name") == "paideia-agent"
        and isinstance(project.get("version"), str)
        and project.get("requires-python") == ">=3.10"
        and project.get("dependencies", []) == []
        and bool(scripts),
        details={
            "name": project.get("name"),
            "version": project.get("version"),
            "requires_python": project.get("requires-python"),
            "direct_dependency_count": len(project.get("dependencies", []))
            if isinstance(project.get("dependencies"), list)
            else None,
            "console_script_names": sorted(scripts),
        },
    )
    _check(
        checks,
        "installed_distribution_metadata_matches_pyproject",
        distribution is not None
        and distribution.metadata.get("Name") == project.get("name")
        and distribution.version == project.get("version"),
        details={
            "package": package_name,
            "installed": distribution is not None,
            "error": distribution_error,
            "installed_name": distribution.metadata.get("Name") if distribution is not None else None,
            "installed_version": distribution.version if distribution is not None else None,
            "pyproject_version": project.get("version"),
        },
    )
    _check(
        checks,
        "distribution_console_scripts_match_pyproject",
        distribution_scripts == scripts and installed_scripts == scripts,
        details={
            "pyproject_scripts": scripts,
            "distribution_scripts": distribution_scripts,
            "installed_console_scripts": installed_scripts,
            "missing_from_distribution": sorted(set(scripts) - set(distribution_scripts)),
            "missing_from_global_entry_points": sorted(set(scripts) - set(installed_scripts)),
        },
    )
    _check(
        checks,
        "console_script_targets_importable_callables",
        targets_callable,
        details={"failure_count": len(callable_failures), "failures": callable_failures},
    )
    _check(
        checks,
        "optional_dependency_groups_split_by_capability",
        REQUIRED_OPTIONAL_GROUPS <= set(optional)
        and set().union(*(set(optional.get(group, [])) for group in REQUIRED_OPTIONAL_GROUPS - {"all"}))
        <= set(optional.get("all", [])),
        details={
            "required_groups": sorted(REQUIRED_OPTIONAL_GROUPS),
            "present_groups": sorted(optional),
            "direct_dependencies_empty": project.get("dependencies", []) == [],
        },
    )
    _check(
        checks,
        "package_metadata_public_safe",
        hygiene["forbidden_fragment_count"] == 0,
        details=hygiene,
    )

    failed = [check for check in checks if not check["passed"] and check["severity"] == "error"]
    report = {
        "schema": PACKAGE_INSTALL_DOCTOR_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "summary": {
            "package": package_name,
            "version": project.get("version"),
            "check_count": len(checks),
            "failed_count": len(failed),
            "console_script_count": len(scripts),
            "optional_group_count": len(optional),
            "distribution_installed": distribution is not None,
            "network_call_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "local_paths_exported": hygiene["local_absolute_paths_exported"],
        },
        "checks": checks,
        "public_safe": {
            "network_call_performed": False,
            "subprocess_executed": False,
            "secret_values_exported": False,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace": "do_not_store",
            "private_runtime_outputs_scanned": False,
            "local_absolute_paths_exported": hygiene["local_absolute_paths_exported"],
        },
    }
    if output_path is not None:
        _write_json(output_path, report)
    return report
