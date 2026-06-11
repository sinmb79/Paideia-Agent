from __future__ import annotations

import json
import re
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
    ".github/workflows/optional-dependency-audit.yml",
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

REQUIRED_CI_JOBS = {"test", "security", "release-gates"}
REQUIRED_CI_JOB_COMMAND_MARKERS = {
    "test": [
        'python -m pip install -e ".[dev]"',
        "python -m compileall src/ai22b/talent_foundry",
        "ruff check src tests",
        "python -B -m pytest tests -q",
    ],
    "security": [
        'python -m pip install -e ".[security]"',
        "python -m bandit -q -r src",
        "python -m pip_audit . --skip-editable",
    ],
    "release-gates": [
        'python -m pip install -e ".[dev]"',
        "python -m build",
        "python -m compileall src/ai22b/talent_foundry",
        "ruff check src tests",
        ".\\scripts\\check_public_repo_hygiene.ps1",
        "ai22b-talent-foundry build-llm-connection-profile",
        "ai22b-talent-foundry doctor-llm-adapters",
        "ai22b-talent-foundry run-chat-runtime-smoke",
        "ai22b-talent-foundry doctor-llm-live-readiness",
        "ai22b-talent-foundry audit-public-release-readiness",
        "ai22b-talent-foundry build-source-sbom",
        "ai22b-talent-foundry doctor-package-install",
        "ai22b-talent-foundry doctor-first-run",
        "ai22b-talent-foundry doctor-runtime-contract",
    ],
}
REQUIRED_CI_JOB_ARTIFACT_NAMES = {
    "security": ["security-reports"],
    "release-gates": ["public-release-gate-reports"],
}
REQUIRED_CI_MARKERS = sorted(
    {
        marker
        for markers in REQUIRED_CI_JOB_COMMAND_MARKERS.values()
        for marker in markers
    }
    | {
        artifact
        for artifacts in REQUIRED_CI_JOB_ARTIFACT_NAMES.values()
        for artifact in artifacts
    }
)
REQUIRED_CI_ACTION_MAJOR_MINIMUMS = {
    "actions/checkout": 6,
    "actions/setup-python": 6,
    "actions/upload-artifact": 7,
}
REQUIRED_RELEASE_GATE_NEEDS = {"test", "security"}
REQUIRED_RELEASE_GATE_OS = {"windows-latest", "ubuntu-latest"}
REQUIRED_RELEASE_GATE_PYTHON = {"3.11", "3.12"}
REQUIRED_OPTIONAL_AUDIT_EXTRAS = {"live-llm", "local-llm", "rag", "fine-tune", "all"}
REQUIRED_ARTIFACT_RETENTION_DAYS = 14
REQUIRED_OPTIONAL_AUDIT_TRIGGERS = {"workflow_dispatch", "schedule"}
REQUIRED_OPTIONAL_AUDIT_JOB = "optional-dependency-audit"
REQUIRED_OPTIONAL_AUDIT_COMMAND_MARKERS = [
    'python -m pip install pip-audit',
    'python -m pip install -e ".[${{ matrix.extra }}]"',
    "python -m pip_audit --local --format json",
]
REQUIRED_OPTIONAL_AUDIT_ARTIFACT_NAMES = [
    "optional-dependency-audit-${{ matrix.extra }}",
]
REQUIRED_OPTIONAL_AUDIT_MARKERS = sorted(
    REQUIRED_OPTIONAL_AUDIT_COMMAND_MARKERS
    + REQUIRED_OPTIONAL_AUDIT_ARTIFACT_NAMES
    + [f"{trigger}:" for trigger in REQUIRED_OPTIONAL_AUDIT_TRIGGERS]
)

REQUIRED_HYGIENE_MARKERS = [
    "missing_required_release_file",
    "missing_package_license_metadata",
    "local_windows_user_path",
    "generic_local_windows_user_path",
    "generic_local_posix_user_path",
    "(^|/)build/",
    "provider_secret_assignment",
    "hardcoded_password_assignment",
    "generic_openai_secret",
    "private_key",
    "hidden_unicode_bidi_control",
    "hidden_control_character_observation",
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


def _text_has_marker(text: str, needle: str) -> bool:
    return needle.replace("\\", "/") in text.replace("\\", "/")


def _strip_inline_shell_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    result: list[str] = []
    for character in line:
        if escaped:
            result.append(character)
            escaped = False
            continue
        if character == "`" and not in_single:
            result.append(character)
            escaped = True
            continue
        if character == "'" and not in_double:
            in_single = not in_single
            result.append(character)
            continue
        if character == '"' and not in_single:
            in_double = not in_double
            result.append(character)
            continue
        if character == "#" and not in_single and not in_double:
            break
        result.append(character)
    return "".join(result).strip()


def _line_matches_command_marker(line: str, marker: str) -> bool:
    command = _strip_inline_shell_comment(line).replace("\\", "/").strip()
    required = marker.replace("\\", "/").strip()
    if not command:
        return False
    return command == required or command.startswith(f"{required} ")


def _run_text_has_command_marker(run_text: str, marker: str) -> bool:
    return any(_line_matches_command_marker(line, marker) for line in run_text.splitlines())


def _load_workflow_document(text: str) -> tuple[dict[str, Any], str | None]:
    if not text.strip():
        return {}, "workflow_empty"
    try:
        import yaml
    except ModuleNotFoundError:
        return {}, "pyyaml_not_installed"
    class GithubActionsLoader(yaml.SafeLoader):
        pass

    GithubActionsLoader.yaml_implicit_resolvers = {
        first: [
            (tag, regexp)
            for tag, regexp in resolvers
            if tag != "tag:yaml.org,2002:bool"
        ]
        for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    try:
        # Custom SafeLoader preserves the GitHub Actions "on" key without enabling arbitrary object loading.
        loaded = yaml.load(text, Loader=GithubActionsLoader)  # nosec B506
    except Exception as exc:
        return {}, f"workflow_yaml_parse_failed:{type(exc).__name__}"
    if loaded is None:
        return {}, "workflow_empty"
    if not isinstance(loaded, dict):
        return {}, "workflow_root_not_mapping"
    return loaded, None


def _workflow_jobs(workflow: dict[str, Any]) -> dict[str, Any]:
    jobs = workflow.get("jobs", {})
    return jobs if isinstance(jobs, dict) else {}


def _workflow_steps(workflow: dict[str, Any], job_id: str | None = None) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if job_id is None:
        jobs = list(_workflow_jobs(workflow).values())
    else:
        job = _workflow_jobs(workflow).get(job_id)
        jobs = [job] if isinstance(job, dict) else []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_steps = job.get("steps", [])
        if not isinstance(job_steps, list):
            continue
        steps.extend(step for step in job_steps if isinstance(step, dict))
    return steps


def _as_string_set(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(item) for item in value}
    if isinstance(value, tuple):
        return {str(item) for item in value}
    if isinstance(value, str):
        return {value}
    return set()


def _workflow_uses_entries(workflow: dict[str, Any] | str) -> list[str]:
    if isinstance(workflow, str):
        workflow, _ = _load_workflow_document(workflow)
    entries = []
    for step in _workflow_steps(workflow):
        uses = step.get("uses")
        if isinstance(uses, str):
            entries.append(uses.strip("'\""))
    return entries


def _workflow_job_run_text(workflow: dict[str, Any], job_id: str) -> str:
    lines: list[str] = []
    for step in _workflow_steps(workflow, job_id):
        run = step.get("run")
        if not isinstance(run, str):
            continue
        for raw in run.splitlines():
            if raw.strip().startswith("#"):
                continue
            lines.append(raw)
    return "\n".join(lines)


def _workflow_job_upload_artifact_names(workflow: dict[str, Any], job_id: str) -> list[str]:
    names = []
    for step in _workflow_steps(workflow, job_id):
        uses = str(step.get("uses", ""))
        if not uses.startswith("actions/upload-artifact@"):
            continue
        with_block = step.get("with", {})
        if not isinstance(with_block, dict):
            continue
        name = with_block.get("name")
        if name is not None:
            names.append(str(name))
    return names


def _artifact_name_matches(actual: str, required: str) -> bool:
    return actual == required or actual.startswith(f"{required}-")


def _missing_job_command_markers(workflow: dict[str, Any], required: dict[str, list[str]]) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for job_id, markers in required.items():
        run_text = _workflow_job_run_text(workflow, job_id)
        job_missing = [marker for marker in markers if not _run_text_has_command_marker(run_text, marker)]
        if job_missing:
            missing[job_id] = job_missing
    return missing


def _missing_job_artifact_names(workflow: dict[str, Any], required: dict[str, list[str]]) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for job_id, artifacts in required.items():
        names = _workflow_job_upload_artifact_names(workflow, job_id)
        job_missing = [
            artifact
            for artifact in artifacts
            if not any(_artifact_name_matches(name, artifact) for name in names)
        ]
        if job_missing:
            missing[job_id] = job_missing
    return missing


def _workflow_upload_artifact_retention(workflow: dict[str, Any]) -> dict[str, Any]:
    steps = []
    missing_or_invalid = []
    for index, step in enumerate(_workflow_steps(workflow)):
        uses = str(step.get("uses", ""))
        if not uses.startswith("actions/upload-artifact@"):
            continue
        with_block = step.get("with", {})
        if not isinstance(with_block, dict):
            with_block = {}
        raw_retention = with_block.get("retention-days")
        try:
            retention_days = int(raw_retention)
        except (TypeError, ValueError):
            retention_days = None
        step_name = str(step.get("name") or f"upload-artifact-step-{index}")
        item = {
            "name": step_name,
            "retention_days": retention_days,
            "required_retention_days": REQUIRED_ARTIFACT_RETENTION_DAYS,
            "passed": retention_days == REQUIRED_ARTIFACT_RETENTION_DAYS,
        }
        steps.append(item)
        if not item["passed"]:
            missing_or_invalid.append(step_name)
    return {
        "upload_artifact_steps": steps,
        "upload_artifact_steps_missing_retention_days": missing_or_invalid,
    }


def _workflow_permissions_contents_read_yaml(workflow: dict[str, Any]) -> bool:
    permissions = workflow.get("permissions")
    if not isinstance(permissions, dict):
        return False
    return str(permissions.get("contents", "")).casefold() == "read"


def _workflow_job_permission_issues(workflow: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for job_id, job in _workflow_jobs(workflow).items():
        if not isinstance(job, dict) or "permissions" not in job:
            continue
        permissions = job.get("permissions")
        if not isinstance(permissions, dict):
            issues.append({"job": str(job_id), "issue": "job_permissions_not_mapping"})
            continue
        for permission, value in permissions.items():
            permission_name = str(permission)
            value_text = str(value).casefold()
            if permission_name == "contents" and value_text == "read":
                continue
            if value_text in {"none", ""}:
                continue
            issues.append(
                {
                    "job": str(job_id),
                    "permission": permission_name,
                    "value": str(value),
                    "issue": "job_permission_grants_more_than_read",
                }
            )
    return issues


def _workflow_checkout_status(workflow: dict[str, Any], required_jobs: set[str]) -> dict[str, Any]:
    missing_checkout_jobs: list[str] = []
    jobs_missing_persist_credentials_false: list[str] = []
    checkout_steps_without_persist_credentials_false = 0
    for job_id in sorted(required_jobs):
        checkout_steps = [
            step
            for step in _workflow_steps(workflow, job_id)
            if str(step.get("uses", "")).startswith("actions/checkout@")
        ]
        if not checkout_steps:
            missing_checkout_jobs.append(job_id)
            continue
        for step in checkout_steps:
            with_block = step.get("with", {})
            if not isinstance(with_block, dict):
                with_block = {}
            value = with_block.get("persist-credentials")
            if value is not False and str(value).casefold() != "false":
                checkout_steps_without_persist_credentials_false += 1
                if job_id not in jobs_missing_persist_credentials_false:
                    jobs_missing_persist_credentials_false.append(job_id)
    return {
        "missing_checkout_jobs": missing_checkout_jobs,
        "jobs_missing_checkout_persist_credentials_false": jobs_missing_persist_credentials_false,
        "checkout_steps_without_persist_credentials_false": checkout_steps_without_persist_credentials_false,
    }


def _workflow_checkout_steps_missing_persist_credentials_false(workflow: dict[str, Any]) -> int:
    missing = 0
    for step in _workflow_steps(workflow):
        uses = str(step.get("uses", ""))
        if not uses.startswith("actions/checkout@"):
            continue
        with_block = step.get("with", {})
        if not isinstance(with_block, dict):
            with_block = {}
        value = with_block.get("persist-credentials")
        if value is not False and str(value).casefold() != "false":
            missing += 1
    return missing


def _workflow_matrix_values(job: dict[str, Any], key: str) -> set[str]:
    strategy = job.get("strategy", {})
    if not isinstance(strategy, dict):
        return set()
    matrix = strategy.get("matrix", {})
    if not isinstance(matrix, dict):
        return set()
    return _as_string_set(matrix.get(key))


def _workflow_legacy_uses_entries(text: str) -> list[str]:
    entries = []
    for raw in text.splitlines():
        match = re.match(r"^\s*uses:\s*([^\s#]+)", raw)
        if match:
            entries.append(match.group(1).strip("'\""))
    return entries


def _action_major_version(uses_entry: str, action: str) -> int | None:
    prefix = f"{action}@"
    if not uses_entry.startswith(prefix):
        return None
    ref = uses_entry.removeprefix(prefix)
    match = re.match(r"v(\d+)(?:\D|$)", ref)
    return int(match.group(1)) if match else None


def _job_block(text: str, job_id: str) -> str:
    pattern = re.compile(rf"^  {re.escape(job_id)}:\s*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    next_job = re.search(r"^  [A-Za-z0-9_-]+:\s*$", text[match.end() :], re.M)
    end = match.end() + next_job.start() if next_job else len(text)
    return text[match.start() : end]


def _top_level_job_ids(text: str) -> set[str]:
    if "\njobs:" in text:
        jobs_block = text.split("\njobs:", 1)[1]
    elif text.startswith("jobs:"):
        jobs_block = text.removeprefix("jobs:")
    else:
        return set()
    return set(re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", jobs_block, re.M))


def _workflow_permissions_contents_read(text: str) -> bool:
    permissions_match = re.search(r"^permissions:\s*$", text, re.M)
    if not permissions_match:
        return False
    following = text[permissions_match.end() :]
    end_match = re.search(r"^[A-Za-z0-9_-]+:\s*$", following, re.M)
    block = following[: end_match.start()] if end_match else following
    return re.search(r"^\s{2}contents:\s*read\s*$", block, re.M) is not None


def _checkout_steps_missing_persist_credentials_false(text: str) -> int:
    lines = text.splitlines()
    missing = 0
    for index, raw in enumerate(lines):
        if not re.match(r"^\s*uses:\s*actions/checkout@", raw):
            continue
        indent = len(raw) - len(raw.lstrip())
        block: list[str] = []
        for following in lines[index + 1 :]:
            stripped = following.strip()
            following_indent = len(following) - len(following.lstrip())
            if stripped and following_indent <= indent and following.lstrip().startswith("- "):
                break
            block.append(following)
        if not any(re.match(r"^\s*persist-credentials:\s*false\s*$", line) for line in block):
            missing += 1
    return missing


def _workflow_values(block: str, *, key: str) -> set[str]:
    values: set[str] = set()
    lines = block.splitlines()
    for index, raw in enumerate(lines):
        if not re.match(rf"^\s*{re.escape(key)}:\s*$", raw):
            continue
        indent = len(raw) - len(raw.lstrip())
        for following in lines[index + 1 :]:
            stripped = following.strip()
            if not stripped:
                continue
            following_indent = len(following) - len(following.lstrip())
            if following_indent <= indent:
                break
            item_match = re.match(r"^\s*-\s*['\"]?([^'\"\s#]+)", following)
            if item_match:
                values.add(item_match.group(1))
    return values


def _workflow_triggers(workflow: dict[str, Any]) -> set[str]:
    on_block = workflow.get("on")
    if isinstance(on_block, dict):
        return {str(key) for key in on_block}
    if isinstance(on_block, list):
        return {str(item) for item in on_block}
    if isinstance(on_block, str):
        return {on_block}
    return set()


def _workflow_marker_check(text: str) -> dict[str, Any]:
    workflow, parse_error = _load_workflow_document(text)
    uses_entries = _workflow_uses_entries(workflow) if not parse_error else _workflow_legacy_uses_entries(text)
    action_versions = {
        action: sorted(
            version
            for entry in uses_entries
            if (version := _action_major_version(entry, action)) is not None
        )
        for action in REQUIRED_CI_ACTION_MAJOR_MINIMUMS
    }
    missing_or_old_actions = [
        action
        for action, minimum in REQUIRED_CI_ACTION_MAJOR_MINIMUMS.items()
        if not action_versions[action] or min(action_versions[action]) < minimum
    ]
    jobs_map = _workflow_jobs(workflow)
    jobs = set(str(key) for key in jobs_map) if not parse_error else _top_level_job_ids(text)
    release_job = jobs_map.get("release-gates", {}) if isinstance(jobs_map.get("release-gates"), dict) else {}
    release_block = _job_block(text, "release-gates")
    release_needs = _as_string_set(release_job.get("needs")) if release_job else _workflow_values(release_block, key="needs")
    release_os = _workflow_matrix_values(release_job, "os") if release_job else _workflow_values(release_block, key="os")
    release_python = (
        _workflow_matrix_values(release_job, "python-version")
        if release_job
        else _workflow_values(release_block, key="python-version")
    )
    missing_job_command_markers = (
        _missing_job_command_markers(workflow, REQUIRED_CI_JOB_COMMAND_MARKERS)
        if not parse_error
        else {"workflow": REQUIRED_CI_MARKERS}
    )
    missing_job_artifact_names = (
        _missing_job_artifact_names(workflow, REQUIRED_CI_JOB_ARTIFACT_NAMES)
        if not parse_error
        else {"workflow": [artifact for artifacts in REQUIRED_CI_JOB_ARTIFACT_NAMES.values() for artifact in artifacts]}
    )
    checkout_status = (
        _workflow_checkout_status(workflow, REQUIRED_CI_JOBS)
        if not parse_error
        else {
            "missing_checkout_jobs": [],
            "jobs_missing_checkout_persist_credentials_false": [],
            "checkout_steps_without_persist_credentials_false": _checkout_steps_missing_persist_credentials_false(text),
        }
    )
    job_permission_issues = _workflow_job_permission_issues(workflow) if not parse_error else []
    retention = _workflow_upload_artifact_retention(workflow) if not parse_error else {
        "upload_artifact_steps": [],
        "upload_artifact_steps_missing_retention_days": ["workflow_yaml_unavailable"],
    }
    details = {
        "workflow_yaml_parse_error": parse_error,
        "workflow_yaml_top_level_keys": sorted(str(key) for key in workflow),
        "missing_jobs": sorted(REQUIRED_CI_JOBS - jobs),
        "permissions_contents_read": _workflow_permissions_contents_read_yaml(workflow)
        if not parse_error
        else _workflow_permissions_contents_read(text),
        "job_permission_issues": job_permission_issues,
        "action_major_versions": action_versions,
        "missing_or_old_actions": missing_or_old_actions,
        **checkout_status,
        **retention,
        "release_gates_needs": sorted(release_needs),
        "missing_release_gates_needs": sorted(REQUIRED_RELEASE_GATE_NEEDS - release_needs),
        "release_gates_os": sorted(release_os),
        "missing_release_gates_os": sorted(REQUIRED_RELEASE_GATE_OS - release_os),
        "release_gates_python": sorted(release_python),
        "missing_release_gates_python": sorted(REQUIRED_RELEASE_GATE_PYTHON - release_python),
        "missing_job_command_markers": missing_job_command_markers,
        "missing_job_artifact_names": missing_job_artifact_names,
    }
    passed = (
        not parse_error
        and not details["missing_jobs"]
        and details["permissions_contents_read"]
        and not job_permission_issues
        and not missing_or_old_actions
        and not details["missing_checkout_jobs"]
        and details["checkout_steps_without_persist_credentials_false"] == 0
        and not details["upload_artifact_steps_missing_retention_days"]
        and not details["missing_release_gates_needs"]
        and not details["missing_release_gates_os"]
        and not details["missing_release_gates_python"]
        and not missing_job_command_markers
        and not missing_job_artifact_names
    )
    return {"passed": passed, "details": details}


def _optional_dependency_audit_check(text: str) -> dict[str, Any]:
    workflow, parse_error = _load_workflow_document(text)
    uses_entries = _workflow_uses_entries(workflow) if not parse_error else _workflow_legacy_uses_entries(text)
    action_versions = {
        action: sorted(
            version
            for entry in uses_entries
            if (version := _action_major_version(entry, action)) is not None
        )
        for action in REQUIRED_CI_ACTION_MAJOR_MINIMUMS
    }
    missing_or_old_actions = [
        action
        for action, minimum in REQUIRED_CI_ACTION_MAJOR_MINIMUMS.items()
        if not action_versions[action] or min(action_versions[action]) < minimum
    ]
    jobs_map = _workflow_jobs(workflow)
    optional_job = (
        jobs_map.get(REQUIRED_OPTIONAL_AUDIT_JOB, {})
        if isinstance(jobs_map.get(REQUIRED_OPTIONAL_AUDIT_JOB), dict)
        else {}
    )
    extras = _workflow_matrix_values(optional_job, "extra") if optional_job else _workflow_values(text, key="extra")
    triggers = _workflow_triggers(workflow) if not parse_error else set()
    missing_triggers = sorted(REQUIRED_OPTIONAL_AUDIT_TRIGGERS - triggers)
    optional_run_text = _workflow_job_run_text(workflow, REQUIRED_OPTIONAL_AUDIT_JOB) if not parse_error else ""
    missing_command_markers = [
        marker
        for marker in REQUIRED_OPTIONAL_AUDIT_COMMAND_MARKERS
        if not _run_text_has_command_marker(optional_run_text, marker)
    ] if not parse_error else REQUIRED_OPTIONAL_AUDIT_COMMAND_MARKERS
    artifact_names = (
        _workflow_job_upload_artifact_names(workflow, REQUIRED_OPTIONAL_AUDIT_JOB)
        if not parse_error
        else []
    )
    missing_artifact_names = [
        artifact
        for artifact in REQUIRED_OPTIONAL_AUDIT_ARTIFACT_NAMES
        if not any(_artifact_name_matches(name, artifact) for name in artifact_names)
    ]
    checkout_status = (
        _workflow_checkout_status(workflow, {REQUIRED_OPTIONAL_AUDIT_JOB})
        if not parse_error
        else {
            "missing_checkout_jobs": [],
            "jobs_missing_checkout_persist_credentials_false": [],
            "checkout_steps_without_persist_credentials_false": _checkout_steps_missing_persist_credentials_false(text),
        }
    )
    job_permission_issues = _workflow_job_permission_issues(workflow) if not parse_error else []
    retention = _workflow_upload_artifact_retention(workflow) if not parse_error else {
        "upload_artifact_steps": [],
        "upload_artifact_steps_missing_retention_days": ["workflow_yaml_unavailable"],
    }
    details = {
        "workflow_yaml_parse_error": parse_error,
        "workflow_yaml_top_level_keys": sorted(str(key) for key in workflow),
        "permissions_contents_read": _workflow_permissions_contents_read_yaml(workflow)
        if not parse_error
        else _workflow_permissions_contents_read(text),
        "job_permission_issues": job_permission_issues,
        "action_major_versions": action_versions,
        "missing_or_old_actions": missing_or_old_actions,
        "triggers": sorted(triggers),
        "missing_triggers": missing_triggers,
        "extras": sorted(extras),
        "missing_extras": sorted(REQUIRED_OPTIONAL_AUDIT_EXTRAS - extras),
        "missing_command_markers": missing_command_markers,
        "missing_artifact_names": missing_artifact_names,
        **checkout_status,
        **retention,
    }
    passed = (
        not parse_error
        and details["permissions_contents_read"]
        and not job_permission_issues
        and not missing_or_old_actions
        and not missing_triggers
        and not details["missing_extras"]
        and not missing_command_markers
        and not missing_artifact_names
        and not details["missing_checkout_jobs"]
        and details["checkout_steps_without_persist_credentials_false"] == 0
        and not details["upload_artifact_steps_missing_retention_days"]
    )
    return {"passed": passed, "details": details}


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
    license_field = project.get("license")
    license_files = project.get("license-files", [])
    license_declared = license_field == "MIT" or (
        isinstance(license_field, dict) and license_field.get("file") == "LICENSE"
    )
    license_file_included = "LICENSE" in license_files or (
        isinstance(license_field, dict) and license_field.get("file") == "LICENSE"
    )
    dependencies = project.get("dependencies", [])
    optional_groups = optional_dependency_groups(pyproject)
    required_optional_groups = {"dev", "security", "live-llm", "local-llm", "rag", "fine-tune", "all"}
    _check(
        checks,
        issues,
        check_id="package_metadata",
        passed=(
            project.get("name") == "paideia-agent"
            and license_declared
            and license_file_included
            and dependencies == []
            and required_optional_groups <= set(optional_groups)
        ),
        details={
            "package_name": project.get("name"),
            "license_declared": license_declared,
            "license_file_declared": license_file_included,
            "license_metadata": license_field,
            "license_files": license_files,
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
    ci_check = _workflow_marker_check(ci_text)
    _check(
        checks,
        issues,
        check_id="ci_release_gates",
        passed=ci_check["passed"],
        details={
            **ci_check["details"],
            "required_jobs": sorted(REQUIRED_CI_JOBS),
            "required_action_major_minimums": REQUIRED_CI_ACTION_MAJOR_MINIMUMS,
            "required_artifact_retention_days": REQUIRED_ARTIFACT_RETENTION_DAYS,
            "required_command_markers": REQUIRED_CI_MARKERS,
            "required_job_command_markers": REQUIRED_CI_JOB_COMMAND_MARKERS,
            "required_job_artifact_names": REQUIRED_CI_JOB_ARTIFACT_NAMES,
        },
        issue="ci_release_gate_missing",
    )

    optional_audit_path = root / ".github" / "workflows" / "optional-dependency-audit.yml"
    optional_audit_text = _read_text(optional_audit_path) if optional_audit_path.is_file() else ""
    optional_audit_check = _optional_dependency_audit_check(optional_audit_text)
    _check(
        checks,
        issues,
        check_id="optional_dependency_audit_workflow",
        passed=optional_audit_check["passed"],
        details={
            **optional_audit_check["details"],
            "required_extras": sorted(REQUIRED_OPTIONAL_AUDIT_EXTRAS),
            "required_triggers": sorted(REQUIRED_OPTIONAL_AUDIT_TRIGGERS),
            "required_artifact_retention_days": REQUIRED_ARTIFACT_RETENTION_DAYS,
            "required_markers": REQUIRED_OPTIONAL_AUDIT_MARKERS,
            "required_command_markers": REQUIRED_OPTIONAL_AUDIT_COMMAND_MARKERS,
            "required_artifact_names": REQUIRED_OPTIONAL_AUDIT_ARTIFACT_NAMES,
        },
        issue="optional_dependency_audit_workflow_missing",
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
            "observation_count": public_scan.get("observation_count", 0),
            "observations": public_scan.get("observations", []),
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
            "public_candidate_observation_count": public_scan.get("observation_count", 0),
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
