from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai22b.talent_foundry.runtime_observability import RUNTIME_OBSERVABILITY_SCHEMA
from ai22b.talent_foundry.workspace_sandbox import (
    WORKSPACE_ROLLBACK_MANIFEST_SCHEMA,
    WORKSPACE_SANDBOX_SCHEMA,
)


WORKSPACE_EXECUTION_PROOF_SCHEMA = "paideia-workspace-execution-proof/v1"
SUPPORTED_RUN_SCHEMAS = {
    "ai-talent-workspace-agent-run/v1",
    "ai-talent-hired-agent-job-run/v1",
    "ai-talent-dataflow-run/v1",
}
LLM_PROVIDER_PREFLIGHT_SCHEMA = "paideia-llm-provider-preflight/v1"
DATAFLOW_TRANSPOSE_VERIFICATION_SCHEMA = "ai-talent-dataflow-transpose-verification/v1"
WORKSPACE_TOOL_ARTIFACTS_SCHEMA = "paideia-workspace-tool-artifacts/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    try:
        return Path(str(value))
    except TypeError:
        return None


def _artifact_record(key: str, value: Any) -> dict[str, Any]:
    path = _path(value)
    if path is None:
        return {
            "key": key,
            "exists": False,
            "missing_reason": "path_not_declared",
        }
    exists = path.exists()
    record: dict[str, Any] = {
        "key": key,
        "file_name": path.name,
        "path_fingerprint_sha256": _fingerprint(str(path.resolve()).casefold()),
        "exists": exists,
    }
    if exists and path.is_file():
        stat = path.stat()
        record["size_bytes"] = stat.st_size
        record["content_sha256"] = _file_sha256(path)
        if path.suffix.casefold() == ".json":
            data = _read_json(path)
            if isinstance(data, dict):
                record["json_schema"] = data.get("schema")
    return record


def _load_declared_json(outputs: dict[str, Any], key: str) -> dict[str, Any] | None:
    path = _path(outputs.get(key))
    if path is None or not path.exists():
        return None
    return _read_json(path)


def _workspace_run_for(run: dict[str, Any]) -> dict[str, Any]:
    if run.get("schema") == "ai-talent-hired-agent-job-run/v1":
        nested = run.get("workspace_run")
        return nested if isinstance(nested, dict) else {}
    return run


def _source_status(run: dict[str, Any]) -> str | None:
    if run.get("schema") == "ai-talent-hired-agent-job-run/v1":
        return run.get("job_status")
    return run.get("run_status")


def _base_agent_run(workspace_run: dict[str, Any]) -> dict[str, Any]:
    base = workspace_run.get("base_agent_run")
    return base if isinstance(base, dict) else {}


def _runtime_observability(run: dict[str, Any], workspace_run: dict[str, Any]) -> dict[str, Any]:
    for candidate in (
        run.get("runtime_observability"),
        workspace_run.get("runtime_observability"),
        _base_agent_run(workspace_run).get("runtime_observability"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _llm_result(run: dict[str, Any], workspace_run: dict[str, Any]) -> dict[str, Any]:
    for candidate in (
        run.get("llm_runtime_result"),
        workspace_run.get("llm_runtime_result"),
        _base_agent_run(workspace_run).get("llm_runtime_result"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _llm_preflight(run: dict[str, Any], workspace_run: dict[str, Any]) -> dict[str, Any]:
    llm_result = _llm_result(run, workspace_run)
    for candidate in (
        run.get("llm_provider_preflight"),
        workspace_run.get("llm_provider_preflight"),
        llm_result.get("llm_provider_preflight"),
        _base_agent_run(workspace_run).get("llm_provider_preflight"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _policy_decision(workspace_run: dict[str, Any]) -> dict[str, Any]:
    for candidate in (
        workspace_run.get("policy_decision"),
        _base_agent_run(workspace_run).get("policy_decision"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _sandbox_snapshot(workspace_run: dict[str, Any], workspace_outputs: dict[str, Any]) -> dict[str, Any] | None:
    candidate = workspace_run.get("workspace_sandbox")
    if isinstance(candidate, dict):
        return candidate
    return _load_declared_json(workspace_outputs, "workspace_sandbox")


def _rollback_paths_inside_root(rollback: dict[str, Any]) -> bool:
    root_raw = rollback.get("workspace_root")
    if not root_raw:
        return False
    root = Path(str(root_raw)).resolve()
    for item in rollback.get("delete_order", []):
        if not isinstance(item, dict):
            return False
        path_raw = item.get("path")
        if not path_raw:
            return False
        if not _is_relative_to(Path(str(path_raw)), root):
            return False
        if item.get("safe_to_delete_within_workspace_root") is not True:
            return False
    return True


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    *,
    evidence: dict[str, Any] | None = None,
    severity: str = "error",
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": "passed" if passed else "failed",
            "passed": passed,
            "severity": severity,
            "evidence": evidence or {},
        }
    )


def _required_workspace_outputs(schema: str) -> list[str]:
    if schema == "ai-talent-dataflow-run/v1":
        return [
            "formatted_job",
            "active_memory_cache",
            "tile_matrix",
            "shadow_buffers",
            "synthesis_report",
            "synthesis",
            "transpose_verification",
            "growth_commit_candidate",
            "runtime_observability",
            "rollback_manifest",
            "workspace_sandbox",
            "dataflow_run",
        ]
    return [
        "task_plan",
        "result_summary",
        "trace",
        "runtime_execution",
        "workspace_tool_results",
        "rollback_manifest",
        "workspace_sandbox",
    ]


def _required_job_outputs() -> list[str]:
    return [
        "job_spec",
        "job_report",
        "acceptance_checklist",
        "trace",
        "rollback_manifest",
    ]


def build_workspace_execution_proof(
    run: dict[str, Any],
    *,
    run_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a reviewable proof that a workspace/dataflow run used the P0 safety path."""

    schema = str(run.get("schema", ""))
    workspace_run = _workspace_run_for(run)
    workspace_outputs = workspace_run.get("workspace_outputs", {})
    if not isinstance(workspace_outputs, dict):
        workspace_outputs = {}
    job_outputs = run.get("job_outputs", {})
    if not isinstance(job_outputs, dict):
        job_outputs = {}

    checks: list[dict[str, Any]] = []
    _check(
        checks,
        "supported_run_schema",
        schema in SUPPORTED_RUN_SCHEMAS,
        evidence={"schema": schema, "supported": sorted(SUPPORTED_RUN_SCHEMAS)},
    )

    source_status = _source_status(run)
    completed = source_status == "completed"
    _check(
        checks,
        "run_completed",
        completed,
        evidence={"source_status": source_status},
    )

    required_workspace = _required_workspace_outputs(schema)
    workspace_artifacts = {
        key: _artifact_record(key, workspace_outputs.get(key))
        for key in required_workspace
    }
    missing_workspace = [
        key
        for key, record in workspace_artifacts.items()
        if not record.get("exists")
    ]
    _check(
        checks,
        "workspace_required_outputs_present",
        not missing_workspace,
        evidence={"missing": missing_workspace, "required": required_workspace},
    )

    if schema == "ai-talent-hired-agent-job-run/v1":
        required_job = _required_job_outputs()
        job_artifacts = {
            key: _artifact_record(key, job_outputs.get(key))
            for key in required_job
        }
        missing_job = [
            key
            for key, record in job_artifacts.items()
            if not record.get("exists")
        ]
        _check(
            checks,
            "job_required_outputs_present",
            not missing_job,
            evidence={"missing": missing_job, "required": required_job},
        )
    else:
        job_artifacts = {}

    sandbox = _sandbox_snapshot(workspace_run, workspace_outputs) or {}
    _check(
        checks,
        "workspace_sandbox_schema",
        sandbox.get("schema") == WORKSPACE_SANDBOX_SCHEMA,
        evidence={"schema": sandbox.get("schema")},
    )
    _check(
        checks,
        "workspace_sandbox_enforced",
        sandbox.get("enforcement", {}).get("enabled") is True,
        evidence={"enforcement": sandbox.get("enforcement", {})},
    )
    _check(
        checks,
        "filesystem_allowlist_enforced",
        sandbox.get("filesystem", {}).get("mode") == "allowlist"
        and sandbox.get("filesystem", {}).get("path_traversal_guard") is True,
        evidence={
            "mode": sandbox.get("filesystem", {}).get("mode"),
            "path_traversal_guard": sandbox.get("filesystem", {}).get("path_traversal_guard"),
            "allowed_root_count": len(sandbox.get("filesystem", {}).get("allowed_roots", [])),
        },
    )
    _check(
        checks,
        "network_default_blocked",
        sandbox.get("network", {}).get("default") == "blocked",
        evidence={"network": sandbox.get("network", {})},
    )
    _check(
        checks,
        "subprocess_default_blocked",
        sandbox.get("subprocess", {}).get("default") == "blocked",
        evidence={"subprocess": sandbox.get("subprocess", {})},
    )
    _check(
        checks,
        "declared_outputs_recorded",
        bool(sandbox.get("declared_outputs")),
        evidence={"declared_output_count": len(sandbox.get("declared_outputs", []))},
    )
    _check(
        checks,
        "workspace_resource_budget_ok",
        sandbox.get("resource_usage", {}).get("within_budget") is True,
        evidence={"resource_usage": sandbox.get("resource_usage", {})},
    )

    workspace_rollback = _load_declared_json(workspace_outputs, "rollback_manifest") or {}
    _check(
        checks,
        "workspace_rollback_manifest_schema",
        workspace_rollback.get("schema") == WORKSPACE_ROLLBACK_MANIFEST_SCHEMA,
        evidence={"schema": workspace_rollback.get("schema")},
    )
    _check(
        checks,
        "workspace_rollback_stays_inside_root",
        workspace_rollback.get("never_delete_outside_workspace_root") is True
        and _rollback_paths_inside_root(workspace_rollback),
        evidence={
            "never_delete_outside_workspace_root": workspace_rollback.get("never_delete_outside_workspace_root"),
            "delete_order_count": len(workspace_rollback.get("delete_order", [])),
        },
    )

    if schema == "ai-talent-hired-agent-job-run/v1":
        job_rollback = _load_declared_json(job_outputs, "rollback_manifest") or {}
        _check(
            checks,
            "job_rollback_manifest_schema",
            job_rollback.get("schema") == WORKSPACE_ROLLBACK_MANIFEST_SCHEMA,
            evidence={"schema": job_rollback.get("schema")},
        )
        _check(
            checks,
            "job_rollback_stays_inside_root",
            job_rollback.get("never_delete_outside_workspace_root") is True
            and _rollback_paths_inside_root(job_rollback),
            evidence={
                "never_delete_outside_workspace_root": job_rollback.get("never_delete_outside_workspace_root"),
                "delete_order_count": len(job_rollback.get("delete_order", [])),
            },
        )
        checklist = _load_declared_json(job_outputs, "acceptance_checklist") or {}
        criteria = checklist.get("criteria", [])
        _check(
            checks,
            "job_acceptance_checklist_passed",
            checklist.get("schema") == "ai-talent-agent-job-acceptance-checklist/v1"
            and bool(criteria)
            and all(isinstance(item, dict) and item.get("status") == "satisfied_by_workspace_artifact" for item in criteria),
            evidence={"schema": checklist.get("schema"), "criterion_count": len(criteria)},
        )

    observability = _runtime_observability(run, workspace_run)
    _check(
        checks,
        "runtime_observability_present",
        observability.get("schema") == RUNTIME_OBSERVABILITY_SCHEMA,
        evidence={"schema": observability.get("schema")},
    )
    _check(
        checks,
        "private_reasoning_trace_not_stored",
        observability.get("privacy", {}).get("private_reasoning_trace_stored") is False
        and observability.get("context", {}).get("full_session_replay_used") is False,
        evidence={
            "privacy": observability.get("privacy", {}),
            "context_privacy": {
                "full_session_replay_used": observability.get("context", {}).get("full_session_replay_used"),
                "selected_memory_only": observability.get("context", {}).get("selected_memory_only"),
            },
        },
    )

    llm_result = _llm_result(run, workspace_run)
    _check(
        checks,
        "llm_identity_boundary_preserved",
        llm_result.get("identity_policy") == "application_engine_not_identity",
        evidence={
            "engine": llm_result.get("engine"),
            "status": llm_result.get("status"),
            "identity_policy": llm_result.get("identity_policy"),
        },
    )
    preflight = _llm_preflight(run, workspace_run)
    preflight_required = schema != "ai-talent-dataflow-run/v1" or bool(run.get("employment_context"))
    _check(
        checks,
        "llm_provider_preflight_present",
        (not preflight_required) or preflight.get("schema") == LLM_PROVIDER_PREFLIGHT_SCHEMA,
        evidence={
            "required": preflight_required,
            "schema": preflight.get("schema"),
            "network_call_made_by_preflight": preflight.get("network_call_made_by_preflight"),
        },
    )

    policy = _policy_decision(workspace_run)
    if schema != "ai-talent-dataflow-run/v1":
        _check(
            checks,
            "action_policy_approved_before_tools",
            policy.get("schema") == "paideia-action-policy/v1"
            and policy.get("status") == "approved",
            evidence={"schema": policy.get("schema"), "status": policy.get("status")},
        )
        base = _base_agent_run(workspace_run)
        tool_execution = base.get("tool_execution", {})
        _check(
            checks,
            "registered_tool_capabilities_enforced",
            tool_execution.get("execution_model") == "registered_capability_checked_local_tools_v1",
            evidence={
                "execution_model": tool_execution.get("execution_model"),
                "tool_count": len(tool_execution.get("tool_results", [])) if isinstance(tool_execution, dict) else 0,
            },
        )
        workspace_tool_results = _load_declared_json(workspace_outputs, "workspace_tool_results") or {}
        artifacts = workspace_tool_results.get("artifacts", [])
        _check(
            checks,
            "workspace_tool_artifacts_materialized",
            workspace_tool_results.get("schema") == WORKSPACE_TOOL_ARTIFACTS_SCHEMA
            and workspace_tool_results.get("execution_model") == "registered_capability_checked_local_tools_v1"
            and bool(artifacts)
            and all(
                isinstance(item, dict)
                and item.get("workspace_side_effect") == "materialized_review_artifact_only"
                and item.get("private_reasoning_trace_stored") is False
                for item in artifacts
            ),
            evidence={
                "schema": workspace_tool_results.get("schema"),
                "artifact_count": workspace_tool_results.get("artifact_count"),
                "network_call_performed": workspace_tool_results.get("adapter_policy", {}).get("network_call_performed"),
                "subprocess_executed": workspace_tool_results.get("adapter_policy", {}).get("subprocess_executed"),
            },
        )

    if schema == "ai-talent-dataflow-run/v1":
        transpose = run.get("transpose_verification")
        if not isinstance(transpose, dict):
            transpose = _load_declared_json(workspace_outputs, "transpose_verification") or {}
        _check(
            checks,
            "dataflow_transpose_verification_passed",
            transpose.get("schema") == DATAFLOW_TRANSPOSE_VERIFICATION_SCHEMA
            and transpose.get("status") == "passed",
            evidence={"schema": transpose.get("schema"), "status": transpose.get("status")},
        )
        active_cache = _load_declared_json(workspace_outputs, "active_memory_cache") or {}
        _check(
            checks,
            "dataflow_active_memory_cache_summary_only",
            active_cache.get("cache_policy", {}).get("safe_reference_detail") == "summary_keys_only"
            and '"safe_reference":' not in json.dumps(active_cache, ensure_ascii=False),
            evidence={"cache_policy": active_cache.get("cache_policy", {})},
        )

    failed = [check for check in checks if not check["passed"] and check["severity"] == "error"]
    proof = {
        "schema": WORKSPACE_EXECUTION_PROOF_SCHEMA,
        "created_at_utc": _now(),
        "status": "passed" if not failed else "failed",
        "passed": not failed,
        "source": {
            "run_schema": schema,
            "run_status": source_status,
            "run_path_fingerprint_sha256": _fingerprint(str(run_path.resolve()).casefold()) if run_path else None,
            "run_file_name": run_path.name if run_path else None,
        },
        "artifact_summary": {
            "workspace_outputs": workspace_artifacts,
            "job_outputs": job_artifacts,
            "absolute_paths_redacted": True,
        },
        "checks": checks,
        "issues": [check["id"] for check in failed],
        "public_safe_retention": {
            "absolute_paths_are_fingerprinted": True,
            "raw_provider_payload_saved": False,
            "private_reasoning_trace_saved": False,
        },
    }
    if output_path is not None:
        _write_json(output_path, proof)
    return proof


def verify_workspace_execution_file(run_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    run = _read_json(run_path)
    if run is None:
        proof = {
            "schema": WORKSPACE_EXECUTION_PROOF_SCHEMA,
            "created_at_utc": _now(),
            "status": "failed",
            "passed": False,
            "source": {
                "run_path_fingerprint_sha256": _fingerprint(str(run_path.resolve()).casefold()),
                "run_file_name": run_path.name,
            },
            "artifact_summary": {"workspace_outputs": {}, "job_outputs": {}, "absolute_paths_redacted": True},
            "checks": [
                {
                    "id": "run_json_readable",
                    "status": "failed",
                    "passed": False,
                    "severity": "error",
                    "evidence": {"file_name": run_path.name},
                }
            ],
            "issues": ["run_json_readable"],
            "public_safe_retention": {
                "absolute_paths_are_fingerprinted": True,
                "raw_provider_payload_saved": False,
                "private_reasoning_trace_saved": False,
            },
        }
        if output_path is not None:
            _write_json(output_path, proof)
        return proof
    return build_workspace_execution_proof(run, run_path=run_path, output_path=output_path)
